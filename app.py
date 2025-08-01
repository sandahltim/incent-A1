# app.py
# Version: 1.2.98
# Note: Added in-memory caching for /data endpoint to reduce database load. Compatible with forms.py (1.2.11), script.js (1.2.69), incentive_service.py (1.2.22), config.py (1.2.6), admin_manage.html (1.2.33), macros.html (1.2.10).

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf.csrf import CSRFProtect, CSRFError
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, edit_rule, remove_rule, get_pot_info, update_pot_info, close_voting_session, pause_voting_session, get_voting_results, master_reset_all, get_roles, add_role, edit_role, remove_role, edit_employee, reorder_rules, retire_employee, reactivate_employee, delete_employee, set_point_decay, get_point_decay, deduct_points_daily, get_latest_voting_results, add_feedback, get_unread_feedback_count, get_feedback, mark_feedback_read, delete_feedback, get_settings, set_settings
from forms import VoteForm, AdminLoginForm, StartVotingForm, AddEmployeeForm, AdjustPointsForm, AddRuleForm, EditRuleForm, RemoveRuleForm, EditEmployeeForm, RetireEmployeeForm, ReactivateEmployeeForm, DeleteEmployeeForm, UpdatePotForm, UpdatePriorYearSalesForm, SetPointDecayForm, UpdateAdminForm, AddRoleForm, EditRoleForm, RemoveRoleForm, MasterResetForm, FeedbackForm, LogoutForm, PauseVotingForm, CloseVotingForm, ResetScoresForm, VotingThresholdsForm, QuickAdjustForm
import logging
import time
from flask import session, redirect, url_for, render_template, request, jsonify, flash
import traceback
from datetime import datetime, timedelta
import sqlite3
import threading
import io
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import base64
import os
import json
from config import Config

# In-memory cache for /data endpoint
_data_cache = None
_cache_timestamp = None
_CACHE_DURATION = 60  # Cache for 60 seconds

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object('config.Config')
csrf = CSRFProtect(app)
app.jinja_env.filters['zip'] = zip
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logging.getLogger('gunicorn.error').setLevel(logging.DEBUG)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.debug("Application starting, initializing Flask app")

# Validate database file existence
if not os.path.exists(Config.INCENTIVE_DB_FILE):
    logging.error(f"Database file not found: {Config.INCENTIVE_DB_FILE}")
    raise FileNotFoundError(f"Database file not found: {Config.INCENTIVE_DB_FILE}")

# Prevent module reload issues
if not hasattr(app, '_history_chart_defined'):
    app._history_chart_defined = True
else:
    logging.warning("Multiple imports of app.py detected, ensuring single history_chart definition")

# Context processor to inject logout_form globally
@app.context_processor
def inject_logout_form():
    return dict(logout_form=LogoutForm())

# Background thread for point decay
def point_decay_thread():
    logging.debug("Starting point_decay_thread")
    last_checked = None
    while True:
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        if last_checked != current_date:
            try:
                with DatabaseConnection() as conn:
                    last_run = conn.execute("SELECT value FROM settings WHERE key = 'last_decay_run'").fetchone()
                    if last_run and last_run['value'] == current_date:
                        logging.debug(f"Point decay already ran for {current_date}, skipping")
                        time.sleep(3600)  # Sleep for 1 hour before rechecking
                        continue
                    decay_settings = get_point_decay(conn)
                    today = now.strftime("%A")
                    any_decay_scheduled = False
                    for role_name, decay in decay_settings.items():
                        if today in decay["days"]:
                            any_decay_scheduled = True
                            success, message = deduct_points_daily(conn)
                            logging.debug(f"Point decay executed for {role_name}: {message}")
                    if not any_decay_scheduled:
                        logging.debug(f"No decay scheduled for {today}")
                    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('last_decay_run', current_date))
                    logging.debug(f"Updated last_decay_run to {current_date}")
                    conn.commit()
                last_checked = current_date
            except Exception as e:
                logging.error(f"Point decay error: {str(e)}\n{traceback.format_exc()}")
                time.sleep(300)  # Sleep 5 minutes on error to prevent rapid retries
            time.sleep(86400)  # Sleep for 24 hours after successful run
        else:
            time.sleep(3600)  # Sleep for 1 hour if already checked today
    logging.debug("Point_decay_thread terminated unexpectedly")

threading.Thread(target=point_decay_thread, daemon=True).start()
logging.debug("Point_decay_thread started")

def get_score_class(score):
    if score <= 49:
        return 'score-low'
    elif score <= 74:
        return 'score-mid'
    else:
        return 'score-high'

def get_role_key_map(roles):
    """Generate dynamic role key map from roles, normalizing spaces to underscores."""
    role_key_map = {}
    for role in roles:
        role_name = role["role_name"]
        key = role_name.lower().replace(" ", "_")
        role_key_map[role_name] = key
    return role_key_map

@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'admin_id' in session and request.endpoint in ['admin', 'admin_add', 'admin_adjust_points', 'admin_quick_adjust_points', 'admin_retire_employee', 'admin_reactivate_employee', 'admin_delete_employee', 'admin_edit_employee', 'admin_reset', 'admin_master_reset', 'admin_update_admin', 'admin_add_rule', 'admin_edit_rule', 'admin_remove_rule', 'admin_reorder_rules', 'admin_add_role', 'admin_edit_role', 'admin_remove_role', 'admin_update_pot_endpoint', 'admin_update_prior_year_sales', 'admin_set_point_decay', 'admin_mark_feedback_read', 'admin_delete_feedback', 'admin_settings', 'quick_adjust', 'export_payout']:
        if 'last_activity' not in session:
            session.pop('admin_id', None)
            flash("Session expired. Please log in again.", "danger")
            return redirect(url_for('admin'))
        try:
            last_activity = datetime.fromisoformat(session['last_activity'])
            if (datetime.now() - last_activity).total_seconds() > 7200:
                session.pop('admin_id', None)
                session.pop('last_activity', None)
                flash("Session expired. Please log in again.", "danger")
                return redirect(url_for('admin'))
            session['last_activity'] = datetime.now().isoformat()
        except Exception as e:
            logging.error(f"Error in session check: {str(e)}\n{traceback.format_exc()}")
            session.pop('admin_id', None)
            session.pop('last_activity', None)
            flash("Session error. Please log in again.", "danger")
            return redirect(url_for('admin'))

@app.route("/", methods=["GET"])
def show_incentive():
    try:
        with DatabaseConnection() as conn:
            scoreboard = get_scoreboard(conn)
            voting_active = is_voting_active(conn)
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
            roles = get_roles(conn)
            role_key_map = get_role_key_map(roles)
            week_number = request.args.get("week", None, type=int)
            voting_results = get_voting_results(conn, is_admin=False, week_number=week_number)
            unread_feedback = get_unread_feedback_count(conn) if session.get("admin_id") else 0
            feedback = []
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            week_options = [('', 'All Weeks')] + [(str(i), f"Week {i}") for i in range(1, 53)]
            total_pot = sum(pot_info.get(f"{role_key_map.get(role['role_name'], role['role_name'].lower().replace(' ', '_'))}_pot", 0.0) for role in roles)
        current_month = datetime.now().strftime("%B %Y")
        vote_form = VoteForm()
        feedback_form = FeedbackForm()
        adjust_form = AdjustPointsForm()
        adjust_form.employee_id.choices = employee_options
        logout_form = LogoutForm()
        logging.debug(f"Rendering incentive.html: voting_active={voting_active}, results_count={len(voting_results)}, total_pot={total_pot}")
        return render_template(
            "incentive.html",
            scoreboard=scoreboard,
            voting_active=voting_active,
            rules=rules,
            pot_info=pot_info,
            roles=roles,
            is_admin=bool(session.get("admin_id")),
            import_time=int(time.time()),
            voting_results=voting_results,
            current_month=current_month,
            selected_week=week_number,
            get_score_class=get_score_class,
            unread_feedback=unread_feedback,
            feedback=feedback,
            employee_options=employee_options,
            week_options=week_options,
            vote_form=vote_form,
            feedback_form=feedback_form,
            adjust_form=adjust_form,
            logout_form=logout_form,
            role_key_map=role_key_map,
            total_pot=total_pot
        )
    except Exception as e:
        logging.error(f"Error in show_incentive: {str(e)}\n{traceback.format_exc()}")
        flash("Internal server error", "danger")
        return render_template("error.html", error="Internal Server Error"), 500

@app.route("/data", methods=["GET"])
def incentive_data():
    global _data_cache, _cache_timestamp
    try:
        # Check if cache is valid
        if _data_cache and _cache_timestamp and (time.time() - _cache_timestamp) < _CACHE_DURATION:
            logging.debug("Returning cached data for /data endpoint")
            return jsonify(_data_cache)
        
        logging.debug(f"Attempting to access database at: {Config.INCENTIVE_DB_FILE}")
        with DatabaseConnection() as conn:
            logging.debug("Database connection established")
            scoreboard = [dict(row) for row in get_scoreboard(conn)]
            voting_active = is_voting_active(conn)
            pot_info = get_pot_info(conn)
            logging.debug(f"Scoreboard retrieved: {len(scoreboard)} entries")
            logging.debug(f"Voting active: {voting_active}")
            logging.debug(f"Pot info: {pot_info}")
            _data_cache = {"scoreboard": scoreboard, "voting_active": voting_active, "pot_info": pot_info}
            _cache_timestamp = time.time()
        return jsonify(_data_cache)
    except sqlite3.OperationalError as e:
        logging.error(f"Database error in incentive_data: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    except Exception as e:
        logging.error(f"Error in incentive_data: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Internal Server Error: {str(e)}"}), 500

@app.route("/favicon.ico")
def favicon():
    favicon_path = os.path.join(app.static_folder, 'favicon.ico')
    if os.path.exists(favicon_path):
        return send_from_directory(app.static_folder, 'favicon.ico')
    logging.debug("favicon.ico not found in static folder, returning empty response")
    return '', 204

@app.route("/start_voting", methods=["GET", "POST"])
def start_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = StartVotingForm()
    if request.method == "POST":
        try:
            logging.debug("Start voting form data received: %s", {k: '****' if k == 'password' else v for k, v in request.form.items()})
            if not form.validate_on_submit():
                logging.error("Start voting form validation failed: %s", form.errors)
                return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
            username = form.username.data
            password = form.password.data
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    active_session = conn.execute("SELECT * FROM voting_sessions WHERE end_time IS NULL").fetchone()
                    if active_session:
                        logging.warning("Voting session already active")
                        return jsonify({"success": False, "message": "A voting session is already active"}), 400
                    conn.execute("INSERT INTO voting_sessions (start_time, admin_id) VALUES (?, ?)", (datetime.now().isoformat(), session["admin_id"]))
                    conn.commit()
                    logging.debug("Voting session started by admin_id: %s", session["admin_id"])
                    return jsonify({"success": True, "message": "Voting session started"})
                logging.error("Invalid credentials for username: %s", username)
                return jsonify({"success": False, "message": "Invalid credentials"}), 403
        except CSRFError as e:
            logging.error(f"CSRF error in start voting: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "CSRF validation failed. Please try again."}), 400
        except Exception as e:
            logging.error(f"Error in start voting: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return render_template("start_voting.html", form=form, is_master=session.get("admin_id") == "master", import_time=int(time.time()))

@app.route("/close_voting", methods=["POST"])
def close_voting():
    if "admin_id" not in session:
        logging.error("Close voting attempted without admin session")
        flash("Admin access required", "danger")
        return jsonify({"success": False, "message": "Admin access required"}), 403
    form = CloseVotingForm(request.form)
    logging.debug("Raw close voting form data: %s", {k: '****' if k == 'password' else v for k, v in request.form.items()})
    if not form.validate_on_submit():
        logging.error("Close voting form validation failed: %s, form data: %s", form.errors, {k: '****' if k == 'password' else v for k, v in request.form.items()})
        # Attempt to recover password from malformed fields
        for key in request.form.keys():
            if key != 'csrf_token' and key != 'password' and 'password' in key.lower():
                logging.warning("Unexpected form field detected: %s, attempting recovery", key)
                form.password.data = request.form[key]
                if form.validate_on_submit():
                    logging.info("Recovered password validation successful")
                    break
        if not form.validate_on_submit():
            flash("Invalid form data: " + str(form.errors), "danger")
            return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
    try:
        password = form.password.data
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE admin_id = ?", (session["admin_id"],)).fetchone()
            if not admin or not check_password_hash(admin["password"], password):
                logging.error("Invalid admin password for close voting: admin_id=%s", session["admin_id"])
                flash("Invalid admin password", "danger")
                return jsonify({"success": False, "message": "Invalid admin password"}), 403
            success, message = close_voting_session(conn, session["admin_id"])
            if not success:
                logging.error("Close voting failed: %s", message)
                flash(message, "danger")
                return jsonify({"success": False, "message": message}), 400
            conn.commit()
            logging.debug("Voting session closed by admin_id: %s", session["admin_id"])
            flash("Voting session closed", "success")
            return jsonify({"success": True, "message": "Voting session closed"})
    except Exception as e:
        logging.error(f"Error closing voting: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/pause_voting", methods=["POST"])
def pause_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = PauseVotingForm(request.form)
    if not form.validate_on_submit():
        logging.error("Pause voting form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        with DatabaseConnection() as conn:
            success, message = pause_voting_session(conn, session["admin_id"])
            return jsonify({'success': success, 'message': message})
    except Exception as e:
        logging.error(f"Error in pause_voting: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route("/vote", methods=["POST"])
def vote():
    logger = logging.getLogger(__name__)
    logger.debug("Received POST /vote request: %s", request.form)
    form = VoteForm(request.form)
    if not form.validate_on_submit():
        logger.error("Vote form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    voter_initials = form.initials.data.strip().lower()
    votes = {key.split("_")[1]: int(value) for key, value in request.form.items() if key.startswith("vote_") and value in ['-1', '0', '1']}
    try:
        with DatabaseConnection() as conn:
            if not is_voting_active(conn):
                logger.warning("Vote submission failed: Voting is not active")
                return jsonify({'success': False, 'message': 'Voting is not active'}), 400
            if not conn.execute("SELECT 1 FROM employees WHERE LOWER(initials) = ?", (voter_initials,)).fetchone():
                logger.warning("Vote submission failed: Invalid initials %s", voter_initials)
                return jsonify({'success': False, 'message': 'Invalid voter initials'}), 403
            success, message = cast_votes(conn, voter_initials, votes)
            logger.info("Vote result: initials=%s, success=%s, message=%s", voter_initials, success, message)
            return jsonify({'success': success, 'message': message})
    except Exception as e:
        logger.error("Error in vote: %s\n%s", str(e), traceback.format_exc())
        return jsonify({'success': False, 'message': f'Server error: {str(e)}'}), 500

@app.route("/check_vote", methods=["POST"])
def check_vote():
    try:
        initials = request.form.get("initials")
        if not initials or initials.strip() == '':
            return jsonify({"can_vote": False, "message": "Initials required"}), 400
        with DatabaseConnection() as conn:
            session = conn.execute("SELECT start_time FROM voting_sessions WHERE end_time IS NULL").fetchone()
            if not session:
                return jsonify({"can_vote": False, "message": "Voting is not active"}), 400
            existing_vote = conn.execute(
                "SELECT COUNT(*) as count FROM votes WHERE LOWER(voter_initials) = ? AND vote_date >= ?",
                (initials.lower(), session["start_time"])
            ).fetchone()["count"]
            if existing_vote > 0:
                return jsonify({"can_vote": False, "message": "You have already voted in this session"})
            return jsonify({"can_vote": True})
    except Exception as e:
        logging.error(f"Error in check_vote: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"can_vote": False, "message": "Server error"}), 500

@app.route("/admin", methods=["GET", "POST"])
def admin():
    form = AdminLoginForm()
    logging.debug(f"Session state for /admin: {session}")
    logging.debug(f"Form CSRF token: {form.csrf_token.current_token if form.csrf_token else 'No CSRF token'}")
    if request.method == "POST" and "username" in request.form:
        try:
            if not form.validate_on_submit():
                logging.error("Admin login form validation failed: %s", form.errors)
                flash("Invalid form data: " + str(form.errors), "danger")
                return render_template("admin_login.html", form=form, import_time=int(time.time()))
            username = form.username.data
            password = form.password.data
            logging.debug(f"Attempting admin login for username: {username}")
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    session["admin_id"] = admin["admin_id"]
                    session['last_activity'] = datetime.now().isoformat()
                    logging.debug(f"Admin login successful: {username}, session: {session}")
                    return redirect(url_for("admin"))
                flash("Invalid credentials", "danger")
                logging.debug(f"Admin login failed for {username}: Invalid credentials")
        except CSRFError as e:
            logging.error(f"CSRF error in admin login: {str(e)}\n{traceback.format_exc()}")
            flash("CSRF validation failed. Please try again.", "danger")
        except Exception as e:
            logging.error(f"Error in admin login: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
        return render_template("admin_login.html", form=form, import_time=int(time.time()))
    if "admin_id" not in session:
        logging.debug("Rendering admin_login.html: no admin_id in session")
        return render_template("admin_login.html", form=form, import_time=int(time.time()))
    try:
        with DatabaseConnection() as conn:
            logging.debug("Admin route: Opening database connection")
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
            roles = get_roles(conn)
            role_key_map = get_role_key_map(roles)
            # Calculate total pot
            total_pot = sum(pot_info.get(f"{role_key_map.get(role['role_name'], role['role_name'].lower().replace(' ', '_'))}_pot", 0.0) for role in roles)
            decay = get_point_decay(conn)
            admins = conn.execute("SELECT admin_id, username FROM admins").fetchall() if session.get("admin_id") == "master" else []
            voting_results = []
            history = [dict(row) for row in get_history(conn, datetime.now().strftime("%Y-%m"))]
            total_payout = 0
            # Calculate employee payouts
            employee_payouts = []
            for emp in employees:
                if emp["active"] == 1 and emp["score"] >= 50:
                    role_key = role_key_map.get(emp["role"].capitalize(), emp["role"].lower().replace(" ", "_"))
                    point_value = pot_info.get(f"{role_key}_point_value", 0)
                    payout = emp["score"] * point_value
                    total_payout += payout
                    employee_payouts.append({"employee_id": emp["employee_id"], "name": emp["name"], "score": emp["score"], "payout": payout})
            if session.get("admin_id") == "master":
                results = conn.execute(
                    "SELECT vs.session_id, v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, COALESCE(vr.points, 0) AS points "
                    "FROM votes v "
                    "JOIN employees e ON v.recipient_id = e.employee_id "
                    "JOIN voting_sessions vs ON v.vote_date >= vs.start_time AND (v.vote_date <= vs.end_time OR vs.end_time IS NULL) "
                    "LEFT JOIN voting_results vr ON v.recipient_id = vr.employee_id AND vr.session_id = vs.session_id "
                    "ORDER BY vs.session_id DESC, v.vote_date DESC"
                ).fetchall()
                voting_results = [dict(row) for row in results]
            # Voting status
            active_session = conn.execute("SELECT start_time FROM voting_sessions WHERE end_time IS NULL").fetchone()
            voted_initials = set()
            if active_session:
                voted_initials = set(row["voter_initials"] for row in conn.execute(
                    "SELECT DISTINCT voter_initials FROM votes WHERE vote_date >= ?", (active_session["start_time"],)
                ).fetchall())
            active_employees = [emp for emp in employees if emp["active"] == 1]
            voting_status = [{"initials": emp["initials"], "voted": emp["initials"].lower() in voted_initials} for emp in active_employees]
            unread_feedback = get_unread_feedback_count(conn)
            feedback = get_feedback(conn) if session.get("admin_id") == "master" else []
            settings = get_settings(conn)
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
            admin_options = [(admin["username"], f"{admin['username']} ({admin['admin_id']})") for admin in admins] if session.get("admin_id") == "master" else []
            decay_role_options = [(role["role_name"], f"{role['role_name']} (Current: {decay.get(role['role_name'], {'points': 1, 'days': []})['points']} points, {', '.join(decay.get(role['role_name'], {'days': []})['days'])})") for role in roles]
            reason_options = [(r["description"], r["description"]) for r in rules] + [("Other", "Other")]
            voting_active = is_voting_active(conn)
            # Instantiate and populate forms with attributes for macro compatibility
            start_voting_form = StartVotingForm()
            pause_voting_form = PauseVotingForm()
            close_voting_form = CloseVotingForm()
            add_employee_form = AddEmployeeForm()
            add_employee_form.name.data = ''
            add_employee_form.initials.data = ''
            add_employee_form.role.data = 'Driver'
            edit_employee_form = EditEmployeeForm()
            edit_employee_form.employee_id.data = employee_options[0][0] if employee_options else ''
            edit_employee_form.name.data = ''
            edit_employee_form.role.data = 'Driver'
            close_voting_form.password.data = ''
            update_pot_form = UpdatePotForm()
            update_pot_form.sales_dollars.data = pot_info.get('sales_dollars', 100000)
            update_pot_form.bonus_percent.data = pot_info.get('bonus_percent', 10)
            update_prior_year_sales_form = UpdatePriorYearSalesForm()
            update_prior_year_sales_form.prior_year_sales.data = pot_info.get('prior_year_sales', 50000)
            update_admin_form = UpdateAdminForm()
            update_admin_form.old_username.data = admin_options[0][0] if admin_options else ''
            update_admin_form.new_username.data = ''
            update_admin_form.new_password.data = ''
            master_reset_form = MasterResetForm()
            master_reset_form.password.data = ''
            add_rule_form = AddRuleForm()
            add_rule_form.description.data = ''
            add_rule_form.points.data = 0
            add_rule_form.details.data = ''
            add_role_form = AddRoleForm()
            add_role_form.role_name.data = ''
            add_role_form.percentage.data = 0
            edit_role_form = EditRoleForm()
            edit_role_form.old_role_name.data = role_options[0][0] if role_options else ''
            edit_role_form.new_role_name.data = ''
            edit_role_form.percentage.data = 0
            remove_role_form = RemoveRoleForm()
            remove_role_form.role_name.data = role_options[0][0] if role_options else ''
            set_point_decay_form = SetPointDecayForm()
            set_point_decay_form.role_name.data = decay_role_options[0][0] if decay_role_options else ''
            set_point_decay_form.points.data = 0
            set_point_decay_form.days.data = []
            thresholds_form = VotingThresholdsForm()
            thresholds_data = json.loads(settings.get('voting_thresholds', '{"positive":[{"threshold":90,"points":10},{"threshold":60,"points":5},{"threshold":25,"points":2}],"negative":[{"threshold":90,"points":-10},{"threshold":60,"points":-5},{"threshold":25,"points":-2}]}'))
            thresholds_form.pos_threshold_1.data = thresholds_data['positive'][0]['threshold']
            thresholds_form.pos_points_1.data = thresholds_data['positive'][0]['points']
            thresholds_form.pos_threshold_2.data = thresholds_data['positive'][1]['threshold']
            thresholds_form.pos_points_2.data = thresholds_data['positive'][1]['points']
            thresholds_form.pos_threshold_3.data = thresholds_data['positive'][2]['threshold']
            thresholds_form.pos_points_3.data = thresholds_data['positive'][2]['points']
            thresholds_form.neg_threshold_1.data = thresholds_data['negative'][0]['threshold']
            thresholds_form.neg_points_1.data = thresholds_data['negative'][0]['points']
            thresholds_form.neg_threshold_2.data = thresholds_data['negative'][1]['threshold']
            thresholds_form.neg_points_2.data = thresholds_data['negative'][1]['points']
            thresholds_form.neg_threshold_3.data = thresholds_data['negative'][2]['threshold']
            thresholds_form.neg_points_3.data = thresholds_data['negative'][2]['points']
            logging.debug(f"Form data populated: add_rule_form.description={add_rule_form.description.data}, update_pot_form.sales_dollars={update_pot_form.sales_dollars.data}")
        # Clear stale flashes
        session.pop('_flashes', None)
        logging.debug("Admin route: Database connection closed, rendering admin_manage.html")
        return render_template(
            "admin_manage.html",
            employees=employees,
            rules=rules,
            pot_info=pot_info,
            roles=roles,
            decay=decay,
            admins=admins,
            voting_results=voting_results,
            employee_payouts=employee_payouts,
            total_payout=total_payout,
            total_pot=total_pot,
            voting_status=voting_status,
            is_admin=True,
            is_master=session.get("admin_id") == "master",
            import_time=int(time.time()),
            unread_feedback=unread_feedback,
            feedback=feedback,
            settings=settings,
            current_month=datetime.now().strftime("%Y-%m"),
            employee_options=employee_options,
            role_options=role_options,
            admin_options=admin_options,
            decay_role_options=decay_role_options,
            reason_options=reason_options,
            history=history,
            voting_active=voting_active,
            start_voting_form={
                'username': {'name': 'username', 'id': 'start_voting_username', 'label_text': 'Username', 'value': start_voting_form.username.data, 'class': 'form-control', 'required': True},
                'password': {'name': 'password', 'id': 'start_voting_password', 'label_text': 'Password', 'value': start_voting_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True}
            },
            pause_voting_form={'submit': {'text': 'Pause Voting', 'class': 'btn btn-warning'}},
            close_voting_form={
                'password': {'name': 'password', 'id': 'close_voting_password', 'label_text': 'Admin Password', 'value': close_voting_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True},
                'submit': {'text': 'Close Voting', 'class': 'btn btn-danger'}
            },
            add_employee_form={
                'name': {'name': 'name', 'id': 'add_employee_name', 'label_text': 'Name', 'value': add_employee_form.name.data, 'class': 'form-control', 'required': True},
                'initials': {'name': 'initials', 'id': 'add_employee_initials', 'label_text': 'Initials', 'value': add_employee_form.initials.data, 'class': 'form-control', 'required': True},
                'role': {'name': 'role', 'id': 'add_employee_role', 'label_text': 'Role', 'options': role_options, 'selected_value': add_employee_form.role.data, 'class': 'form-control'}
            },
            adjust_points_form=AdjustPointsForm(),
            add_rule_form={
                'description': {'name': 'description', 'id': 'add_rule_description', 'label_text': 'Description', 'value': add_rule_form.description.data, 'class': 'form-control', 'required': True},
                'points': {'name': 'points', 'id': 'add_rule_points', 'label_text': 'Points', 'value': add_rule_form.points.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'details': {'name': 'details', 'id': 'add_rule_details', 'label_text': 'Notes', 'value': add_rule_form.details.data, 'class': 'form-control', 'type': 'textarea'}
            },
            edit_rule_form={
                'old_description': {'name': 'old_description', 'id': 'edit_rule_old_description', 'label_text': 'Old Description', 'value': '', 'class': 'form-control', 'required': True},
                'new_description': {'name': 'new_description', 'id': 'edit_rule_new_description', 'label_text': 'New Description', 'value': '', 'class': 'form-control', 'required': True},
                'points': {'name': 'points', 'id': 'edit_rule_points', 'label_text': 'Points', 'value': 0, 'class': 'form-control', 'type': 'number', 'required': True},
                'details': {'name': 'details', 'id': 'edit_rule_details', 'label_text': 'Notes', 'value': '', 'class': 'form-control', 'type': 'textarea'}
            },
            remove_rule_form=RemoveRuleForm(),
            edit_employee_form={
                'employee_id': {'name': 'employee_id', 'id': 'edit_employee_id', 'label_text': 'Employee', 'options': employee_options, 'selected_value': edit_employee_form.employee_id.data, 'class': 'form-control'},
                'name': {'name': 'name', 'id': 'edit_employee_name', 'label_text': 'Name', 'value': edit_employee_form.name.data, 'class': 'form-control', 'required': True},
                'role': {'name': 'role', 'id': 'edit_employee_role', 'label_text': 'Role', 'options': role_options, 'selected_value': edit_employee_form.role.data, 'class': 'form-control'}
            },
            retire_employee_form=RetireEmployeeForm(),
            reactivate_employee_form=ReactivateEmployeeForm(),
            delete_employee_form=DeleteEmployeeForm(),
            update_pot_form={
                'sales_dollars': {'name': 'sales_dollars', 'id': 'update_pot_sales_dollars', 'label_text': 'Sales Dollars ($)', 'value': update_pot_form.sales_dollars.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'bonus_percent': {'name': 'bonus_percent', 'id': 'update_pot_bonus_percent', 'label_text': 'Bonus Percent (%)', 'value': update_pot_form.bonus_percent.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            update_prior_year_sales_form={
                'prior_year_sales': {'name': 'prior_year_sales', 'id': 'update_prior_year_sales_prior_year_sales', 'label_text': 'Prior Year Sales ($)', 'value': update_prior_year_sales_form.prior_year_sales.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            reset_scores_form={'submit': {'text': 'Reset All Scores', 'class': 'btn btn-danger'}},
            update_admin_form={
                'old_username': {'name': 'old_username', 'id': 'update_admin_old_username', 'label_text': 'Old Username', 'options': admin_options, 'selected_value': update_admin_form.old_username.data, 'class': 'form-control'},
                'new_username': {'name': 'new_username', 'id': 'update_admin_new_username', 'label_text': 'New Username', 'value': update_admin_form.new_username.data, 'class': 'form-control', 'required': True},
                'new_password': {'name': 'new_password', 'id': 'update_admin_new_password', 'label_text': 'New Password', 'value': update_admin_form.new_password.data, 'class': 'form-control', 'type': 'password', 'required': True}
            },
            master_reset_form={
                'password': {'name': 'password', 'id': 'master_reset_password', 'label_text': 'Master Password', 'value': master_reset_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True}
            },
            add_role_form={
                'role_name': {'name': 'role_name', 'id': 'add_role_name', 'label_text': 'Role Name', 'value': add_role_form.role_name.data, 'class': 'form-control', 'required': True},
                'percentage': {'name': 'percentage', 'id': 'add_role_percentage', 'label_text': 'Percentage', 'value': add_role_form.percentage.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            edit_role_form={
                'old_role_name': {'name': 'old_role_name', 'id': 'edit_role_old_role_name', 'label_text': 'Old Role Name', 'options': role_options, 'selected_value': edit_role_form.old_role_name.data, 'class': 'form-control'},
                'new_role_name': {'name': 'new_role_name', 'id': 'edit_role_new_role_name', 'label_text': 'New Role Name', 'value': edit_role_form.new_role_name.data, 'class': 'form-control', 'required': True},
                'percentage': {'name': 'percentage', 'id': 'edit_role_percentage', 'label_text': 'Percentage', 'value': edit_role_form.percentage.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            remove_role_form={
                'role_name': {'name': 'role_name', 'id': 'remove_role_name', 'label_text': 'Role Name', 'options': role_options, 'selected_value': remove_role_form.role_name.data, 'class': 'form-control'}
            },
            set_point_decay_form={
                'role_name': {'name': 'role_name', 'id': 'set_point_decay_role_name', 'label_text': 'Role', 'options': decay_role_options, 'selected_value': set_point_decay_form.role_name.data, 'class': 'form-control'},
                'points': {'name': 'points', 'id': 'set_point_decay_points', 'label_text': 'Points to Deduct Daily', 'value': set_point_decay_form.points.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'days': {'name': 'days', 'id': 'set_point_decay_days', 'label_text': 'Days to Trigger', 'options': [('Monday', 'Monday'), ('Tuesday', 'Tuesday'), ('Wednesday', 'Wednesday'), ('Thursday', 'Thursday'), ('Friday', 'Friday'), ('Saturday', 'Saturday'), ('Sunday', 'Sunday')], 'selected_values': set_point_decay_form.days.data, 'class': 'form-control', 'multiple': True}
            },
            thresholds_form={
                'pos_threshold_1': {'name': 'pos_threshold_1', 'id': 'pos_threshold_1', 'label_text': 'Positive Threshold 1 (%)', 'value': thresholds_form.pos_threshold_1.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_points_1': {'name': 'pos_points_1', 'id': 'pos_points_1', 'label_text': 'Positive Points 1', 'value': thresholds_form.pos_points_1.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_threshold_2': {'name': 'pos_threshold_2', 'id': 'pos_threshold_2', 'label_text': 'Positive Threshold 2 (%)', 'value': thresholds_form.pos_threshold_2.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_points_2': {'name': 'pos_points_2', 'id': 'pos_points_2', 'label_text': 'Positive Points 2', 'value': thresholds_form.pos_points_2.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_threshold_3': {'name': 'pos_threshold_3', 'id': 'pos_threshold_3', 'label_text': 'Positive Threshold 3 (%)', 'value': thresholds_form.pos_threshold_3.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'pos_points_3': {'name': 'pos_points_3', 'id': 'pos_points_3', 'label_text': 'Positive Points 3', 'value': thresholds_form.pos_points_3.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_threshold_1': {'name': 'neg_threshold_1', 'id': 'neg_threshold_1', 'label_text': 'Negative Threshold 1 (%)', 'value': thresholds_form.neg_threshold_1.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_points_1': {'name': 'neg_points_1', 'id': 'neg_points_1', 'label_text': 'Negative Points 1', 'value': thresholds_form.neg_points_1.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_threshold_2': {'name': 'neg_threshold_2', 'id': 'neg_threshold_2', 'label_text': 'Negative Threshold 2 (%)', 'value': thresholds_form.neg_threshold_2.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_points_2': {'name': 'neg_points_2', 'id': 'neg_points_2', 'label_text': 'Negative Points 2', 'value': thresholds_form.neg_points_2.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_threshold_3': {'name': 'neg_threshold_3', 'id': 'neg_threshold_3', 'label_text': 'Negative Threshold 3 (%)', 'value': thresholds_form.neg_threshold_3.data, 'class': 'form-control', 'type': 'number', 'required': True},
                'neg_points_3': {'name': 'neg_points_3', 'id': 'neg_points_3', 'label_text': 'Negative Points 3', 'value': thresholds_form.neg_points_3.data, 'class': 'form-control', 'type': 'number', 'required': True}
            },
            settings_link={'url': url_for('admin_settings'), 'text': 'Settings'},
            role_key_map=role_key_map
        )
    except Exception as e:
        logging.error(f"Error in admin: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_id", None)
    session.pop("last_activity", None)
    flash("Logged out successfully", "success")
    return redirect(url_for("show_incentive"))

@app.route("/admin/add", methods=["POST"])
def admin_add():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    try:
        with DatabaseConnection() as conn:
            roles = get_roles(conn)
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
        form = AddEmployeeForm(request.form)
        form.role.choices = role_options
        logging.debug("Add employee form data received: %s", {k: v for k, v in request.form.items()})
        logging.debug("Role choices: %s", form.role.choices)
        if not form.validate_on_submit():
            logging.error("Add employee form validation failed: %s, form data: %s", form.errors, {k: v for k, v in request.form.items()})
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        name = form.name.data
        initials = form.initials.data
        role = form.role.data
        with DatabaseConnection() as conn:
            success, message = add_employee(conn, name, initials, role)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_add: {str(e)}\n{traceback.format_exc()}, form data: %s", {k: v for k, v in request.form.items()})
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
@app.route("/admin/adjust_points", methods=["POST"])
def admin_adjust_points():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = AdjustPointsForm(request.form)
    if not form.validate_on_submit():
        logging.error("Adjust points form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    employee_id = form.employee_id.data
    points = form.points.data
    reason = form.reason.data
    notes = form.notes.data or ""
    try:
        with DatabaseConnection() as conn:
            success, message = adjust_points(conn, employee_id, points, session["admin_id"], reason, notes)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_adjust_points: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/quick_adjust", methods=["GET"])
def quick_adjust():
    start_time = time.time()
    try:
        points = request.args.get('points', type=int)
        reason = request.args.get('reason', '')
        logging.debug(f"Redirecting /quick_adjust to / with points={points}, reason={reason}")
        session['quick_adjust_data'] = {'points': points, 'reason': reason}
        return redirect(url_for('show_incentive'))
    except Exception as e:
        logging.error(f"Error in quick_adjust: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('show_incentive'))

@app.route("/admin/quick_adjust_points", methods=["POST"])
def admin_quick_adjust_points():
    start_time = time.time()
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
        form = QuickAdjustForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Quick adjust form data received: %s", {k: v if k != 'password' else '****' for k, v in request.form.items()})
        if "admin_id" not in session:
            if not form.validate_on_submit():
                logging.error("Quick adjust form validation failed: %s, form data: %s", form.errors, {k: v if k != 'password' else '****' for k, v in request.form.items()})
                return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
            username = form.username.data
            password = form.password.data
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if not admin or not check_password_hash(admin["password"], password):
                    logging.error("Invalid admin credentials for username: %s", username)
                    return jsonify({"success": False, "message": "Invalid admin credentials"}), 403
                session["admin_id"] = admin["admin_id"]
                session["last_activity"] = datetime.now().isoformat()
        else:
            if not (form.employee_id.data and form.points.data and form.reason.data and form.csrf_token.data):
                logging.error("Quick adjust form validation failed for authenticated admin: %s", form.errors)
                return jsonify({"success": False, "message": "Missing required fields: employee_id, points, reason, csrf_token"}), 400
        employee_id = form.employee_id.data
        points = form.points.data
        reason = form.reason.data
        notes = form.notes.data or ""
        with DatabaseConnection() as conn:
            success, message = adjust_points(conn, employee_id, points, session["admin_id"], reason, notes)
            if not success:
                logging.error("Quick adjust failed: %s", message)
                return jsonify({"success": False, "message": message}), 400
            conn.commit()
        logging.debug(f"Route /admin/quick_adjust_points took {time.time() - start_time:.2f} seconds")
        return jsonify({"success": True, "message": f"Adjusted {points} points for employee {employee_id}"})
    except Exception as e:
        logging.error(f"Error in quick_adjust_points: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/admin/retire_employee", methods=["POST"])
def admin_retire_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, active FROM employees").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
        form = RetireEmployeeForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Retire employee form data: %s", dict(request.form))
        logging.debug("Employee ID choices: %s", form.employee_id.choices)
        if not form.validate_on_submit():
            logging.error("Retire employee form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        with DatabaseConnection() as conn:
            success, message = retire_employee(conn, employee_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_retire_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/reactivate_employee", methods=["POST"])
def admin_reactivate_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, active FROM employees WHERE active = 0").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} (Retired)") for emp in employees]
        form = ReactivateEmployeeForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Reactivate employee form data: %s", dict(request.form))
        logging.debug("Employee ID choices: %s", form.employee_id.choices)
        if not form.validate_on_submit():
            logging.error("Reactivate employee form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        with DatabaseConnection() as conn:
            success, message = reactivate_employee(conn, employee_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_reactivate_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/delete_employee", methods=["POST"])
def admin_delete_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, active FROM employees").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
        form = DeleteEmployeeForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Delete employee form data: %s", dict(request.form))
        logging.debug("Employee ID choices: %s", form.employee_id.choices)
        if not form.validate_on_submit():
            logging.error("Delete employee form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        with DatabaseConnection() as conn:
            success, message = delete_employee(conn, employee_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_delete_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/edit_employee", methods=["POST"])
def admin_edit_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            roles = get_roles(conn)
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
        form = EditEmployeeForm(request.form)
        form.employee_id.choices = employee_options
        form.role.choices = role_options
        logging.debug("Edit employee form data: %s", dict(request.form))
        logging.debug("Employee ID choices: %s", form.employee_id.choices)
        logging.debug("Role choices: %s", form.role.choices)
        if not form.validate_on_submit():
            logging.error("Edit employee form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        name = form.name.data
        role = form.role.data
        with DatabaseConnection() as conn:
            success, message = edit_employee(conn, employee_id, name, role)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_edit_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = ResetScoresForm(request.form)
    if not form.validate_on_submit():
        logging.error("Reset scores form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        with DatabaseConnection() as conn:
            success, message = reset_scores(conn, session["admin_id"], reason="Admin reset to 50")
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_reset: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/master_reset", methods=["POST"])
def admin_master_reset():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = MasterResetForm(request.form)
    if not form.validate_on_submit():
        logging.error("Master reset form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    password = form.password.data
    try:
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE admin_id = 'master'").fetchone()
            if not admin or not check_password_hash(admin["password"], password):
                return jsonify({'success': False, 'message': 'Invalid master password'}), 403
            success, message = master_reset_all(conn)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_master_reset: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/update_admin", methods=["POST"])
def admin_update_admin():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = UpdateAdminForm(request.form)
    if not form.validate_on_submit():
        logging.error("Update admin form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    old_username = form.old_username.data
    new_username = form.new_username.data
    new_password = form.new_password.data
    try:
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE username = ?", (old_username,)).fetchone()
            if not admin:
                return jsonify({"success": False, "message": "Admin not found"}), 404
            conn.execute(
                "UPDATE admins SET username = ?, password = ? WHERE username = ?",
                (new_username, generate_password_hash(new_password), old_username)
            )
        return jsonify({"success": True, "message": f"Admin '{old_username}' updated to '{new_username}'"})
    except Exception as e:
        logging.error(f"Error in admin_update_admin: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/add_rule", methods=["POST"])
def admin_add_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = AddRuleForm(request.form)
    if not form.validate_on_submit():
        logging.error("Add rule form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    description = form.description.data
    points = form.points.data
    details = form.details.data or ""
    try:
        with DatabaseConnection() as conn:
            existing_rule = conn.execute("SELECT 1 FROM incentive_rules WHERE description = ?", (description,)).fetchone()
            if existing_rule:
                return jsonify({"success": False, "message": "Rule already exists"}), 400
            success, message = add_rule(conn, description, points, details)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_add_rule: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/edit_rule", methods=["POST"])
def admin_edit_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = EditRuleForm(request.form)
    if not form.validate_on_submit():
        logging.error("Edit rule form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    old_description = form.old_description.data
    new_description = form.new_description.data
    points = form.points.data
    details = form.details.data or ""
    try:
        with DatabaseConnection() as conn:
            success, message = edit_rule(conn, old_description, new_description, points, details)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_edit_rule: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500
    
@app.route("/admin/remove_rule", methods=["POST"])
def admin_remove_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = RemoveRuleForm(request.form)
    logging.debug("Remove rule form data received: %s", {k: v for k, v in request.form.items()})
    if not form.validate_on_submit():
        logging.error("Remove rule form validation failed: %s, form data: %s", form.errors, {k: v for k, v in request.form.items()})
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    description = form.description.data
    try:
        with DatabaseConnection() as conn:
            success, message = remove_rule(conn, description)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_remove_rule: {str(e)}\n{traceback.format_exc()}, form data: %s", {k: v for k, v in request.form.items()})
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500


@app.route("/admin/reorder_rules", methods=["POST"])
def admin_reorder_rules():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    order = request.form.getlist("order[]")
    try:
        with DatabaseConnection() as conn:
            success, message = reorder_rules(conn, order)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_reorder_rules: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/add_role", methods=["POST"])
def admin_add_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = AddRoleForm(request.form)
    logging.debug("Add role form data: %s", dict(request.form))
    if not form.validate_on_submit():
        logging.error("Add role form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        with DatabaseConnection() as conn:
            roles = get_roles(conn)
            if len(roles) >= 6:
                return jsonify({"success": False, "message": "Maximum of 6 roles reached"}), 400
            role_name = form.role_name.data
            percentage = 0.0 if role_name.lower() == "master" else form.percentage.data
            total_percentage = sum(r["percentage"] for r in roles if r["role_name"].lower() != "master") + percentage
            if total_percentage > 100:
                return jsonify({"success": False, "message": f"Total percentage for non-Master roles cannot exceed 100% (got {total_percentage}%)"}), 400
            success, message = add_role(conn, role_name, percentage)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in add_role: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/edit_role", methods=["POST"])
def admin_edit_role():
    if "admin_id" not in session:
        logging.error("Edit role attempted without admin session")
        return jsonify({"success": False, "message": "Admin access required"}), 403
    form = EditRoleForm(request.form)
    logging.debug("Edit role form data received: %s", {k: v for k, v in request.form.items()})
    if not form.validate_on_submit():
        logging.error("Edit role form validation failed: %s, form data: %s", form.errors, {k: v for k, v in request.form.items()})
        return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
    try:
        old_role_name = form.old_role_name.data
        new_role_name = form.new_role_name.data
        percentage = float(form.percentage.data or 0)  # Handle None case
        with DatabaseConnection() as conn:
            # Check total percentage
            roles = conn.execute("SELECT role_name, percentage FROM roles WHERE role_name != ?", (old_role_name,)).fetchall()
            total_percentage = sum(role["percentage"] for role in roles) + percentage
            if total_percentage > 100:
                logging.error("Total percentage exceeds 100: %s", total_percentage)
                return jsonify({"success": False, "message": f"Total role percentages cannot exceed 100% (got {total_percentage}%)"}), 400
            
            # Verify role exists
            existing_role = conn.execute("SELECT role_name FROM roles WHERE role_name = ?", (old_role_name,)).fetchone()
            if not existing_role:
                logging.error("Role not found: %s", old_role_name)
                return jsonify({"success": False, "message": f"Role {old_role_name} not found"}), 404
            
            # Perform updates in a single transaction
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                "UPDATE roles SET role_name = ?, percentage = ? WHERE role_name = ?",
                (new_role_name, percentage, old_role_name)
            )
            conn.execute(
                "UPDATE employees SET role = ? WHERE role = ?",
                (new_role_name.lower(), old_role_name.lower())
            )
            conn.execute(
                "UPDATE point_decay SET role_name = ? WHERE role_name = ?",
                (new_role_name, old_role_name)
            )
            conn.commit()
            logging.debug("Role updated: old_name=%s, new_name=%s, percentage=%s", old_role_name, new_role_name, percentage)
            return jsonify({"success": True, "message": f"Role {new_role_name} updated"})
    except Exception as e:
        logging.error(f"Error editing role: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
@app.route("/admin/remove_role", methods=["POST"])
def admin_remove_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, 'message': "Master account required"}), 403
    form = RemoveRoleForm(request.form)
    if not form.validate_on_submit():
        logging.error("Remove role form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    role_name = form.role_name.data
    try:
        with DatabaseConnection() as conn:
            success, message = remove_role(conn, role_name)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_remove_role: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/update_pot", methods=["POST"], endpoint="admin_update_pot_endpoint")
def admin_update_pot():
    logging.debug("Registering route: /admin/update_pot")
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = UpdatePotForm(request.form)
    if not form.validate_on_submit():
        logging.error("Update pot form validation failed: %s", form.errors)
        logging.debug("Form data received: %s", dict(request.form))
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    sales_dollars = form.sales_dollars.data
    bonus_percent = form.bonus_percent.data
    try:
        with DatabaseConnection() as conn:
            conn.execute(
                "UPDATE incentive_pot SET sales_dollars = ?, bonus_percent = ? WHERE id = 1",
                (sales_dollars, bonus_percent)
            )
            success = True
            message = "Pot sales and bonus updated"
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_update_pot: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/update_prior_year_sales", methods=["POST"])
def admin_update_prior_year_sales():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = UpdatePriorYearSalesForm(request.form)
    logging.debug("Update prior year sales form data: %s", dict(request.form))
    # Handle malformed keys by explicitly checking for prior_year_sales
    prior_year_sales = request.form.get('prior_year_sales')
    if not prior_year_sales:
        logging.error("Update prior year sales: prior_year_sales field missing in form data")
        return jsonify({'success': False, 'message': 'Invalid form data: prior_year_sales is required'}), 400
    form.prior_year_sales.data = int(prior_year_sales)
    if not form.validate_on_submit():
        logging.error("Update prior year sales form validation failed: %s, form data: %s", form.errors, dict(request.form))
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        with DatabaseConnection() as conn:
            conn.execute(
                "UPDATE incentive_pot SET prior_year_sales = ? WHERE id = 1",
                (form.prior_year_sales.data,)
            )
        logging.debug("Prior year sales updated: %s", form.prior_year_sales.data)
        return jsonify({"success": True, "message": "Prior year sales updated"})
    except Exception as e:
        logging.error(f"Error in update_prior_year_sales: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/set_point_decay", methods=["POST"])
def admin_set_point_decay():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    try:
        with DatabaseConnection() as conn:
            roles = get_roles(conn)
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
        form = SetPointDecayForm(request.form)
        form.role_name.choices = role_options
        days = request.form.getlist('days[]')  # Handle days[] format
        logging.debug("Set point decay form data: %s", {k: v if k != 'password' else '****' for k, v in request.form.items()})
        logging.debug("Role choices: %s", form.role_name.choices)
        logging.debug("Days received: %s", days)
        if not form.validate_on_submit():
            logging.error("Set point decay form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        role_name = form.role_name.data
        points = form.points.data
        with DatabaseConnection() as conn:
            success, message = set_point_decay(conn, role_name, points, days)
            conn.commit()
        return jsonify({"success": success, "message": f"Point decay for {role_name} set to {points} points on {days}"})
    except Exception as e:
        logging.error(f"Error in set_point_decay: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/admin/delete_feedback", methods=["POST"])
def admin_delete_feedback():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    feedback_id = request.form.get("feedback_id")
    try:
        with DatabaseConnection() as conn:
            success, message = delete_feedback(conn, feedback_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_delete_feedback: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/voting_results_popup", methods=["GET"])
def voting_results_popup():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    try:
        with DatabaseConnection() as conn:
            results = get_latest_voting_results(conn)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        logging.error(f"Error in voting_results_popup: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/history", methods=["GET"])
def history():
    month_year = request.args.get("month_year")
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, month_year)]
            months = conn.execute("SELECT DISTINCT month_year FROM score_history ORDER BY month_year DESC").fetchall()
            months_options = [('', 'All Months')] + [(m["month_year"], m["month_year"]) for m in months]
            days = []
            if month_year:
                days = conn.execute("SELECT DISTINCT substr(date, 1, 10) as day FROM score_history WHERE month_year = ? ORDER BY day", (month_year,)).fetchall()
                days = [('', 'All Days')] + [(d["day"], d["day"]) for d in days]
        logging.debug(f"Rendering history.html: history_count={len(history)}, months_count={len(months_options)}")
        return render_template("history.html", history=history, months=months_options, days=days, is_admin=bool(session.get("admin_id")), import_time=int(time.time()), selected_month=month_year, selected_day=request.args.get("day"))
    except Exception as e:
        logging.error(f"Error in history: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('show_incentive'))


@app.route("/export_payout", methods=["GET"])
def export_payout():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    month = request.args.get("month", datetime.now().strftime("%Y-%m"))
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, month)]
            if not history:
                flash("No data for selected month", "danger")
                return redirect(url_for('admin'))
            pot_info = get_pot_info(conn)
            employees = conn.execute("SELECT employee_id, name, role FROM employees WHERE active = 1").fetchall()
            df = pd.DataFrame(history)
            output_lines = []
            grouped = df.groupby(['employee_id', 'name'])
            for (employee_id, name), group in grouped:
                employee = next((emp for emp in employees if emp['employee_id'] == employee_id), None)
                if not employee:
                    logging.warning(f"Employee ID {employee_id} not found in employees table")
                    continue
                role = employee['role'].lower().replace(" ", "_")
                total_points = group['points'].sum()
                point_value = pot_info.get(f"{role}_point_value", 0.0)
                total_dollars = total_points * point_value if total_points > 0 and total_points >= 50 else 0.0
                output_lines.append(f"Employee: {name}")
                output_lines.append(f"Employee ID,Name,Role,Total Points,Total Dollars")
                output_lines.append(f"{employee_id},{name},{role},{total_points},{total_dollars:.2f}")
                output_lines.append("")
                output_lines.append("Date,Reason,Points,Dollar Value,Changed By,Notes")
                for _, row in group.iterrows():
                    dollar_value = row['points'] * point_value if row['points'] > 0 else 0.0
                    notes = row.get('notes', '')
                    output_lines.append(f"{row['date']},\"{row['reason']}\",{row['points']},{dollar_value:.2f},{row['changed_by']},\"{notes}\"")
                output_lines.append("")
            output = io.BytesIO()
            output.write("\n".join(output_lines).encode())
            output.seek(0)
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name=f"payout_{month}.csv")
    except Exception as e:
        logging.error(f"Error in export_payout: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/history_chart", methods=["GET"])
def history_chart():
    try:
        with DatabaseConnection() as conn:
            history = conn.execute("""
                SELECT score_history.employee_id, employees.name, score_history.points, score_history.reason, score_history.date
                FROM score_history
                JOIN employees ON score_history.employee_id = employees.employee_id
                ORDER BY score_history.date DESC
                LIMIT 100
            """).fetchall()
        if not history:
            return jsonify({"success": False, "message": "No history data available"})
        df = pd.DataFrame(history, columns=["employee_id", "name", "points", "reason", "date"])
        df['date'] = pd.to_datetime(df['date'], format='mixed')
        fig, ax = plt.subplots(figsize=(10, 6))
        for name in df['name'].unique():
            emp_data = df[df['name'] == name]
            ax.plot(emp_data['date'], emp_data['points'].cumsum(), label=name)
        ax.set_xlabel('Date')
        ax.set_ylabel('Cumulative Points')
        ax.set_title('Employee Points Over Time')
        ax.legend()
        ax.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        output = io.BytesIO()
        FigureCanvas(fig).print_png(output)
        plt.close(fig)
        encoded = base64.b64encode(output.getvalue()).decode('utf-8')
        return jsonify({"success": True, "image": f"data:image/png;base64,{encoded}"})
    except Exception as e:
        logging.error(f"Error in history_chart: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/admin/mark_feedback_read", methods=["POST"])
def admin_mark_feedback_read():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    feedback_id = request.form.get("feedback_id")
    try:
        with DatabaseConnection() as conn:
            success, message = mark_feedback_read(conn, feedback_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_mark_feedback_read: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    form = FeedbackForm(request.form)
    if not form.validate_on_submit():
        logging.error("Feedback form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    comment = form.comment.data
    submitter = form.initials.data if "admin_id" not in session else session["admin_id"]
    try:
        with DatabaseConnection() as conn:
            success, message = add_feedback(conn, comment, submitter)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in submit_feedback: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if "admin_id" not in session or session.get("admin_id") != "master":
        flash("Master admin required", "danger")
        return redirect(url_for('admin'))
    if request.method == "POST":
        if 'pos_threshold_1' in request.form:  # Handle VotingThresholdsForm
            form = VotingThresholdsForm(request.form)
            if not form.validate_on_submit():
                logging.error("Voting thresholds form validation failed: %s", form.errors)
                flash("Invalid voting thresholds data: " + str(form.errors), "danger")
                return redirect(url_for('admin_settings'))
            thresholds = {
                "positive": [
                    {"threshold": form.pos_threshold_1.data, "points": form.pos_points_1.data},
                    {"threshold": form.pos_threshold_2.data, "points": form.pos_points_2.data},
                    {"threshold": form.pos_threshold_3.data, "points": form.pos_points_3.data}
                ],
                "negative": [
                    {"threshold": form.neg_threshold_1.data, "points": form.neg_points_1.data},
                    {"threshold": form.neg_threshold_2.data, "points": form.neg_points_2.data},
                    {"threshold": form.neg_threshold_3.data, "points": form.neg_points_3.data}
                ]
            }
            try:
                with DatabaseConnection() as conn:
                    success, message = set_settings(conn, 'voting_thresholds', json.dumps(thresholds))
                flash(message, "success")
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating voting thresholds: {str(e)}\n{traceback.format_exc()}")
                flash("Server error updating voting thresholds", "danger")
                return redirect(url_for('admin_settings'))
        else:  # Handle generic settings form
            key = request.form.get("key")
            value = request.form.get("value")
            if not key or not value:
                flash("Key and value are required", "danger")
                return redirect(url_for('admin_settings'))
            try:
                with DatabaseConnection() as conn:
                    success, message = set_settings(conn, key, value)
                flash(message, "success")
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating settings: {str(e)}\n{traceback.format_exc()}")
                flash("Server error updating settings", "danger")
                return redirect(url_for('admin_settings'))
    try:
        with DatabaseConnection() as conn:
            settings = get_settings(conn)
        logging.debug("Rendering settings.html")
        form = VotingThresholdsForm()
        thresholds_data = json.loads(settings.get('voting_thresholds', '{"positive":[{"threshold":90,"points":10},{"threshold":60,"points":5},{"threshold":25,"points":2}],"negative":[{"threshold":90,"points":-10},{"threshold":60,"points":-5},{"threshold":25,"points":-2}]}'))
        form.pos_threshold_1.data = thresholds_data['positive'][0]['threshold']
        form.pos_points_1.data = thresholds_data['positive'][0]['points']
        form.pos_threshold_2.data = thresholds_data['positive'][1]['threshold']
        form.pos_points_2.data = thresholds_data['positive'][1]['points']
        form.pos_threshold_3.data = thresholds_data['positive'][2]['threshold']
        form.pos_points_3.data = thresholds_data['positive'][2]['points']
        form.neg_threshold_1.data = thresholds_data['negative'][0]['threshold']
        form.neg_points_1.data = thresholds_data['negative'][0]['points']
        form.neg_threshold_2.data = thresholds_data['negative'][1]['threshold']
        form.neg_points_2.data = thresholds_data['negative'][1]['points']
        form.neg_threshold_3.data = thresholds_data['negative'][2]['threshold']
        form.neg_points_3.data = thresholds_data['negative'][2]['points']
        return render_template("settings.html", settings=settings, is_master=session.get("admin_id") == "master", import_time=int(time.time()), form=form, thresholds_form=form)
    except Exception as e:
        logging.error(f"Error in admin_settings GET: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

if __name__ == "__main__":
    logging.debug("Running Flask app in debug mode")
    app.run(host="0.0.0.0", port=6800, debug=True)
else:
    logging.debug("Running Flask app under Gunicorn")