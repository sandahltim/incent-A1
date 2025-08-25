
# app.py
# Version: 1.2.114
# Note: Added configurable scoreboard timing settings. Compatible with incentive_service.py (1.2.31), forms.py (1.2.22), settings.html (1.3.1), incentive.html (1.3.2), script.js (1.2.97), init_db.py (1.2.5).

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf.csrf import CSRFProtect, CSRFError
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, edit_rule, remove_rule, get_pot_info, update_pot_info, close_voting_session, pause_voting_session, resume_voting_session, finalize_voting_session, get_voting_results, master_reset_all, get_roles, add_role, edit_role, remove_role, edit_employee, reorder_rules, retire_employee, reactivate_employee, delete_employee, set_point_decay, get_point_decay, deduct_points_daily, get_latest_voting_results, add_feedback, get_unread_feedback_count, get_feedback, mark_feedback_read, delete_feedback, get_settings, set_settings, get_recent_admin_adjustments, award_mini_game, play_mini_game, verify_pin
from config import Config
from forms import VoteForm, AdminLoginForm, StartVotingForm, AddEmployeeForm, AdjustPointsForm, AddRuleForm, EditRuleForm, RemoveRuleForm, EditEmployeeForm, RetireEmployeeForm, ReactivateEmployeeForm, DeleteEmployeeForm, UpdatePotForm, UpdatePriorYearSalesForm, SetPointDecayForm, UpdateAdminForm, AddRoleForm, EditRoleForm, RemoveRoleForm, MasterResetForm, FeedbackForm, LogoutForm, PauseVotingForm, CloseVotingForm, ResetScoresForm, VotingThresholdsForm, VoteLimitsForm, ScoreboardSettingsForm, QuickAdjustForm, AwardGameForm, EmployeeLoginForm, ChangePinForm, PortForm, RestartServiceForm, RebootPiForm
import logging
from logging_config import setup_logging
import time
import traceback
from datetime import datetime, timedelta
import calendar
import sqlite3
import threading
import io
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
import os
import json
import random
import subprocess

# In-memory cache for /data endpoint
_data_cache = None
_cache_timestamp = None
_CACHE_DURATION = 60  # Cache for 60 seconds

setup_logging()
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.debug("Application starting, initializing Flask app")

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object('config.Config')
app.config['TEMPLATES_AUTO_RELOAD'] = True
csrf = CSRFProtect(app)
app.jinja_env.filters['zip'] = zip

# Add JSON parsing filter for templates
def from_json(value):
    try:
        return json.loads(value) if value else {}
    except (json.JSONDecodeError, TypeError):
        return {}

app.jinja_env.filters['from_json'] = from_json

# Validate database file existence
if not os.path.exists(Config.INCENTIVE_DB_FILE):
    logging.error(f"Database file not found: {Config.INCENTIVE_DB_FILE}")
    raise FileNotFoundError(f"Database file not found: {Config.INCENTIVE_DB_FILE}")

# Prevent module reload issues
if not hasattr(app, '_history_chart_defined'):
    app._history_chart_defined = True
else:
    logging.warning("Multiple imports of app.py detected, ensuring single history_chart definition")

# Context processor to inject settings and global forms
@app.context_processor
def inject_globals():
    with DatabaseConnection() as conn:
        settings = get_settings(conn)
    return dict(
        logout_form=LogoutForm(),
        site_name=settings.get('site_name', 'A1 Rent-It'),
        site_title=settings.get('site_title', 'A1 Rent-It'),
        primary_color=settings.get('primary_color', '#D4AF37'),
        secondary_color=settings.get('secondary_color', '#000000'),
        background_color=settings.get('background_color', '#3A3A3A'),
        surface_color=settings.get('surface_color', '#222222'),
        surface_alt_color=settings.get('surface_alt_color', '#1A1A1A'),
        score_top_color=settings.get('score_top_color', '#D4AF37'),
        score_mid_color=settings.get('score_mid_color', '#FFFFFF'),
        score_bottom_color=settings.get('score_bottom_color', '#FF6347'),
        reel_color=settings.get('reel_color', '#FFD700'),
        money_threshold=int(settings.get('money_threshold', 50)),
        scoreboard_spin_duration=int(settings.get('scoreboard_spin_duration', 10)),
        scoreboard_spin_iterations=int(settings.get('scoreboard_spin_iterations', 0)),
        scoreboard_spin_pause=int(settings.get('scoreboard_spin_pause', 0)),
        scoreboard_spin_delay=int(settings.get('scoreboard_spin_delay', 0)),
        scoreboard_refresh_interval=int(settings.get('scoreboard_refresh_interval', 60)),
        sound_on=settings.get('sound_on', '1'),
        strobe_mode=settings.get('strobe_mode', 'on'),
        banner_text=settings.get('banner_text', "JACKPOT TIME! GIVE 'EM THE MONEY! SLOTS SPINNING - WINNERS GRINNING!"),
        current_year=datetime.now().year,
        import_time=int(time.time())
    )

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

def get_score_class(score, index, threshold):
    if index == 0:
        return 'score-top'
    elif score < threshold:
        return 'score-bottom'
    else:
        return 'score-mid'

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
    if 'admin_id' in session and request.endpoint in ['admin', 'admin_add', 'admin_adjust_points', 'admin_quick_adjust_points', 'admin_retire_employee', 'admin_reactivate_employee', 'admin_delete_employee', 'admin_edit_employee', 'admin_reset', 'admin_master_reset', 'admin_update_admin', 'admin_add_rule', 'admin_edit_rule', 'admin_remove_rule', 'admin_reorder_rules', 'admin_add_role', 'admin_edit_role', 'admin_remove_role', 'admin_update_pot_endpoint', 'admin_update_prior_year_sales', 'admin_set_point_decay', 'admin_mark_feedback_read', 'admin_delete_feedback', 'admin_settings', 'quick_adjust', 'export_payout', 'admin_toggle_section']:
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
            scoreboard = [{k: v for k, v in dict(row).items() if k != 'initials'} for row in get_scoreboard(conn)]
            voting_active = is_voting_active(conn)
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
            roles = get_roles(conn)
            role_key_map = get_role_key_map(roles)
            
            # Calculate payouts for each employee
            money_threshold = int(get_settings(conn).get('money_threshold', 50))
            for emp in scoreboard:
                role_key = emp['role'].lower().replace(' ', '_')
                point_value = pot_info.get(f'{role_key}_point_value', 0)
                if emp['score'] >= money_threshold:
                    emp['payout'] = round(emp['score'] * point_value, 2)
                else:
                    emp['payout'] = 0
            week_number = request.args.get("week", None, type=int)
            voting_results = get_voting_results(conn, is_admin=False, week_number=week_number)
            unread_feedback = get_unread_feedback_count(conn) if session.get("admin_id") else 0
            feedback = []
            employees = conn.execute(
                "SELECT employee_id, name, initials, score, role, active FROM employees WHERE LOWER(role) != 'master'"
            ).fetchall()
            employee_options = [
                (
                    emp["employee_id"],
                    f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}"
                )
                for emp in employees
            ]
            reason_options = [(rule["description"], rule["description"]) for rule in rules] + [("Other", "Other")]
            week_options = [('', 'All Weeks')] + [(str(i), f"Week {i}") for i in range(1, 53)]
            total_pot = sum(pot_info[role_key_map.get(role['role_name'], role['role_name'].lower().replace(' ', '_')) + '_pot'] for role in roles)
            settings = get_settings(conn)
            max_plus_votes = int(settings.get('max_plus_votes', 2))
            max_minus_votes = int(settings.get('max_minus_votes', 3))
            max_total_votes = int(settings.get('max_total_votes', 3))
            recent_adjustments = get_recent_admin_adjustments(conn, limit=10)
        current_month = datetime.now().strftime("%B %Y")
        vote_form = VoteForm()
        feedback_form = FeedbackForm()
        adjust_form = QuickAdjustForm()
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
            reason_options=reason_options,
            week_options=week_options,
            vote_form=vote_form,
            feedback_form=feedback_form,
            adjust_form=adjust_form,
            logout_form=logout_form,
            role_key_map=role_key_map,
            total_pot=total_pot,
            max_plus_votes=max_plus_votes,
            max_minus_votes=max_minus_votes,
            max_total_votes=max_total_votes,
            recent_adjustments=recent_adjustments,
            main_page=True
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
            scoreboard = [{k: v for k, v in dict(row).items() if k != 'initials'} for row in get_scoreboard(conn)]
            voting_active = is_voting_active(conn)
            pot_info = get_pot_info(conn)
            if not scoreboard or not pot_info:
                logging.error("Failed to retrieve scoreboard or pot info from database")
                raise ValueError("Incomplete data retrieved")
            logging.debug(f"Scoreboard retrieved: {len(scoreboard)} entries")
            logging.debug(f"Voting active: {voting_active}")
            logging.debug(f"Pot info: {pot_info}")
            _data_cache = {"scoreboard": scoreboard, "voting_active": voting_active, "pot_info": pot_info}
            _cache_timestamp = time.time()
        return jsonify(_data_cache)
    except sqlite3.OperationalError as e:
        logging.error(f"Database operational error in incentive_data: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Database operational error: {str(e)}"}), 500
    except ValueError as ve:
        logging.error(f"Data validation error in incentive_data: {str(ve)}\n{traceback.format_exc()}")
        return jsonify({"error": f"Data validation error: {str(ve)}"}), 500
    except Exception as e:
        logging.error(f"Unexpected error in incentive_data: {str(e)}\n{traceback.format_exc()}")
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
    global _data_cache, _cache_timestamp
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
                    success, message = start_voting_session(conn, session["admin_id"])
                    if not success:
                        logging.warning("start_voting_session failed: %s", message)
                        return jsonify({"success": False, "message": message}), 400
                    _data_cache = None
                    _cache_timestamp = None
                    logging.debug("Voting session started by admin_id: %s", session["admin_id"])
                    return jsonify({"success": True, "message": message})
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
    global _data_cache, _cache_timestamp
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
            global _data_cache, _cache_timestamp
            _data_cache = None
            _cache_timestamp = None
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

@app.route("/resume_voting", methods=["POST"])
def resume_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = PauseVotingForm(request.form)
    if not form.validate_on_submit():
        logging.error("Resume voting form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        with DatabaseConnection() as conn:
            success, message = resume_voting_session(conn, session["admin_id"])
            return jsonify({'success': success, 'message': message})
    except Exception as e:
        logging.error(f"Error in resume_voting: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route("/finalize_voting", methods=["POST"])
def finalize_voting():
    if "admin_id" not in session:
        flash("Admin access required", "danger")
        return jsonify({"success": False, "message": "Admin access required"}), 403
    form = CloseVotingForm(request.form)
    if not form.validate_on_submit():
        logging.error("Finalize voting form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    try:
        password = form.password.data
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE admin_id = ?", (session["admin_id"],)).fetchone()
            if not admin or not check_password_hash(admin["password"], password):
                logging.error("Invalid admin password for finalize voting: admin_id=%s", session["admin_id"])
                flash("Invalid admin password", "danger")
                return jsonify({"success": False, "message": "Invalid admin password"}), 403
            success, message = finalize_voting_session(conn, session["admin_id"])
            if not success:
                logging.error("Finalize voting failed: %s", message)
                flash(message, "danger")
                return jsonify({"success": False, "message": message}), 400
            conn.commit()
            global _data_cache, _cache_timestamp
            _data_cache = None
            _cache_timestamp = None
            logging.debug("Paused voting session finalized by admin_id: %s", session["admin_id"])
            flash("Voting session finalized", "success")
            return jsonify({"success": True, "message": "Voting session finalized"})
    except Exception as e:
        logging.error(f"Error finalizing voting: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/vote", methods=["POST"])
def vote():
    global _data_cache, _cache_timestamp
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
            if success and not is_voting_active(conn):
                close_voting_session(conn, 0)
                message += " Voting session closed."
                _data_cache = None
                _cache_timestamp = None
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
            session = conn.execute("SELECT session_id FROM voting_sessions WHERE end_time IS NULL").fetchone()
            if not session:
                return jsonify({"can_vote": False, "message": "Voting is not active"}), 400
            if not conn.execute("SELECT 1 FROM employees WHERE LOWER(initials) = ?", (initials.lower(),)).fetchone():
                return jsonify({"can_vote": False, "message": "Invalid initials"})
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vote_participants (
                    session_id INTEGER,
                    voter_initials TEXT,
                    PRIMARY KEY (session_id, voter_initials),
                    FOREIGN KEY(session_id) REFERENCES voting_sessions(session_id)
                )
                """
            )
            existing_vote = conn.execute(
                "SELECT 1 FROM vote_participants WHERE session_id = ? AND LOWER(voter_initials) = ?",
                (session["session_id"], initials.lower())
            ).fetchone()
            if existing_vote:
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
            mini_games = [dict(row) for row in conn.execute("SELECT mg.id, e.name, mg.game_type, mg.status, mg.outcome FROM mini_games mg JOIN employees e ON mg.employee_id = e.employee_id").fetchall()]
            voting_results = []
            vote_totals = []
            sessions_list = []
            selected_session_id = None
            raw_votes = []
            now = datetime.now()
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
                sessions_list = [dict(row) for row in conn.execute(
                    "SELECT session_id, start_time, end_time FROM voting_sessions ORDER BY start_time DESC"
                ).fetchall()]
                requested_session = request.args.get("session_id", type=int)
                if requested_session:
                    selected_session = conn.execute(
                        "SELECT session_id, start_time, end_time FROM voting_sessions WHERE session_id = ?",
                        (requested_session,)
                    ).fetchone()
                else:
                    selected_session = sessions_list[0] if sessions_list else None
                if selected_session:
                    selected_session_id = selected_session["session_id"]
                    results = conn.execute(
                        "SELECT vr.employee_id, e.name AS recipient_name, vr.plus_votes, vr.minus_votes, vr.plus_percent, vr.minus_percent, vr.points "
                        "FROM voting_results vr JOIN employees e ON vr.employee_id = e.employee_id "
                        "WHERE vr.session_id = ?",
                        (selected_session_id,),
                    ).fetchall()
                    voting_results = [dict(row) for row in results]
                    vote_totals = [
                        {
                            "recipient_name": row["recipient_name"],
                            "plus": row["plus_votes"],
                            "minus": row["minus_votes"],
                            "points": row["points"],
                        }
                        for row in voting_results
                    ]
                    start_date = selected_session["start_time"]
                    end_date = selected_session["end_time"] or now.strftime("%Y-%m-%d %H:%M:%S")
                    raw_vote_rows = conn.execute(
                        "SELECT v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date "
                        "FROM votes v JOIN employees e ON v.recipient_id = e.employee_id "
                        "WHERE v.vote_date >= ? AND v.vote_date <= ? "
                        "ORDER BY v.vote_date DESC",
                        (start_date, end_date)
                    ).fetchall()
                    raw_votes = [dict(row) for row in raw_vote_rows]
            # Voting status
            active_session = conn.execute("SELECT session_id FROM voting_sessions WHERE end_time IS NULL").fetchone()
            voted_initials = set()
            if active_session:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS vote_participants (
                        session_id INTEGER,
                        voter_initials TEXT,
                        PRIMARY KEY (session_id, voter_initials),
                        FOREIGN KEY(session_id) REFERENCES voting_sessions(session_id)
                    )
                    """
                )
                voted_initials = set(
                    row["voter_initials"].lower()
                    for row in conn.execute(
                        "SELECT voter_initials FROM vote_participants WHERE session_id = ?",
                        (active_session["session_id"],),
                    ).fetchall()
                )
            active_employees = [emp for emp in employees if emp["active"] == 1]
            voting_status = [
                {"initials": emp["initials"], "voted": emp["initials"].lower() in voted_initials}
                for emp in active_employees
            ]
            voting_status.sort(key=lambda x: x["voted"])
            unread_feedback = get_unread_feedback_count(conn)
            feedback = get_feedback(conn) if session.get("admin_id") == "master" else []
            settings = get_settings(conn)
            section_permissions = {section: settings.get(f'allow_section_{section}', '0') == '1' for section in Config.ADMIN_SECTIONS}
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
            admin_options = [(admin["username"], f"{admin['username']} ({admin['admin_id']})") for admin in admins] if session.get("admin_id") == "master" else []
            decay_role_options = [(role["role_name"], f"{role['role_name']} (Current: {decay.get(role['role_name'], {'points': 1, 'days': []})['points']} points, {', '.join(decay.get(role['role_name'], {'days': []})['days'])})") for role in roles]
            reason_options = [(r["description"], r["description"]) for r in rules] + [("Other", "Other")]
            voting_active = is_voting_active(conn)
            paused_session = conn.execute(
                """
                SELECT vs.session_id FROM voting_sessions vs
                LEFT JOIN voting_results vr ON vs.session_id = vr.session_id
                WHERE vs.end_time IS NOT NULL AND vr.session_id IS NULL
                ORDER BY vs.end_time DESC LIMIT 1
                """
            ).fetchone()
            voting_paused = paused_session is not None
            # Instantiate and populate forms with attributes for macro compatibility
            start_voting_form = StartVotingForm()
            pause_voting_form = PauseVotingForm()
            close_voting_form = CloseVotingForm()
            add_employee_form = AddEmployeeForm()
            add_employee_form.name.data = ''
            add_employee_form.initials.data = ''
            add_employee_form.role.data = 'Driver'
            add_employee_form.pin.data = '8101'  # Default PIN
            edit_employee_form = EditEmployeeForm()
            edit_employee_form.employee_id.data = employee_options[0][0] if employee_options else ''
            edit_employee_form.name.data = ''
            edit_employee_form.role.data = 'Driver'
            award_game_form = AwardGameForm()
            award_game_form.employee_id.data = employee_options[0][0] if employee_options else ''
            award_game_form.game_type.data = 'slot'
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
            default_role = decay_role_options[0][0] if decay_role_options else ''
            set_point_decay_form.role_name.data = default_role
            if default_role:
                set_point_decay_form.points.data = decay.get(default_role, {'points': 0})['points']
                set_point_decay_form.days.data = decay.get(default_role, {'days': []})['days']
            else:
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
            mini_games=mini_games,
            voting_results=voting_results,
            vote_totals=vote_totals,
            raw_votes=raw_votes,
            sessions=sessions_list,
            selected_session_id=selected_session_id,
            employee_payouts=employee_payouts,
            total_payout=total_payout,
            total_pot=total_pot,
            voting_status=voting_status,
            is_admin=True,
            is_master=session.get("admin_id") == "master",
            import_time=int(time.time()),
            admin_page=True,
            unread_feedback=unread_feedback,
            feedback=feedback,
            settings=settings,
            section_permissions=section_permissions,
            default_start_date=datetime.now().replace(day=1).strftime("%Y-%m-%d"),
            default_end_date=datetime.now().replace(day=calendar.monthrange(datetime.now().year, datetime.now().month)[1]).strftime("%Y-%m-%d"),
            employee_options=employee_options,
            role_options=role_options,
            admin_options=admin_options,
            decay_role_options=decay_role_options,
            reason_options=reason_options,
            history=history,
            voting_active=voting_active,
            voting_paused=voting_paused,
            start_voting_form={
                'username': {'name': 'username', 'id': 'start_voting_username', 'label_text': 'Username', 'value': start_voting_form.username.data, 'class': 'form-control', 'required': True},
                'password': {'name': 'password', 'id': 'start_voting_password', 'label_text': 'Password', 'value': start_voting_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True}
            },
            pause_voting_form={'submit': {'text': 'Pause Voting', 'class': 'btn btn-warning'}},
            resume_voting_form={'submit': {'text': 'Resume Voting', 'class': 'btn btn-success'}},
            close_voting_form={
                'password': {'name': 'password', 'id': 'close_voting_password', 'label_text': 'Admin Password', 'value': close_voting_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True},
                'submit': {'text': 'Close Voting', 'class': 'btn btn-danger'}
            },
            finalize_voting_form={
                'password': {'name': 'password', 'id': 'finalize_voting_password', 'label_text': 'Admin Password', 'value': close_voting_form.password.data, 'class': 'form-control', 'type': 'password', 'required': True},
                'submit': {'text': 'Finalize Voting', 'class': 'btn btn-danger'}
            },
            add_employee_form={
                'name': {'name': 'name', 'id': 'add_employee_name', 'label_text': 'Name', 'value': add_employee_form.name.data, 'class': 'form-control', 'required': True},
                'initials': {'name': 'initials', 'id': 'add_employee_initials', 'label_text': 'Initials', 'value': add_employee_form.initials.data, 'class': 'form-control', 'required': True},
                'role': {'name': 'role', 'id': 'add_employee_role', 'label_text': 'Role', 'options': role_options, 'selected_value': add_employee_form.role.data, 'class': 'form-control'},
                'pin': {'name': 'pin', 'id': 'add_employee_pin', 'label_text': 'PIN', 'value': '', 'class': 'form-control', 'type': 'password', 'required': True}
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
                'role': {'name': 'role', 'id': 'edit_employee_role', 'label_text': 'Role', 'options': role_options, 'selected_value': edit_employee_form.role.data, 'class': 'form-control'},
                'pin': {'name': 'pin', 'id': 'edit_employee_pin', 'label_text': 'PIN', 'value': '', 'class': 'form-control', 'type': 'password', 'required': True}
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
            update_admin_form={
                'old_username': {'name': 'old_username', 'id': 'update_admin_old_username', 'label_text': 'Old Username', 'options': admin_options, 'selected_value': update_admin_form.old_username.data, 'class': 'form-control'},
                'new_username': {'name': 'new_username', 'id': 'update_admin_new_username', 'label_text': 'New Username', 'value': update_admin_form.new_username.data, 'class': 'form-control', 'required': True},
                'new_password': {'name': 'new_password', 'id': 'update_admin_new_password', 'label_text': 'New Password', 'value': update_admin_form.new_password.data, 'class': 'form-control', 'type': 'password', 'required': True}
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
            award_game_form={
                'employee_id': {'name': 'employee_id', 'id': 'award_game_employee', 'label_text': 'Employee', 'options': employee_options, 'selected_value': award_game_form.employee_id.data, 'class': 'form-control'},
                'game_type': {'name': 'game_type', 'id': 'award_game_type', 'label_text': 'Game Type', 'options': [('slot', 'Slot'), ('scratch', 'Scratch-Off'), ('roulette', 'Roulette')], 'selected_value': award_game_form.game_type.data, 'class': 'form-control'}
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
        pin = form.pin.data
        with DatabaseConnection() as conn:
            success, message = add_employee(conn, name, initials, role, pin)
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
            role_row = conn.execute(
                "SELECT LOWER(role) AS role FROM employees WHERE employee_id = ?",
                (employee_id,)
            ).fetchone()
            if role_row and role_row["role"] == "master":
                logging.warning(
                    "Attempt to adjust points for master account: employee_id=%s", employee_id
                )
                return (
                    jsonify({"success": False, "message": "Cannot adjust points for master account"}),
                    400,
                )
            success, message = adjust_points(
                conn, employee_id, points, session["admin_id"], reason, notes
            )
        script = "playJackpot();" if points and points > 0 else ""
        return jsonify({"success": success, "message": message, "script": script})
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
            employees = conn.execute(
                "SELECT employee_id, name, initials, score, role, active FROM employees WHERE LOWER(role) != 'master'"
            ).fetchall()
            employee_options = [
                (
                    emp["employee_id"],
                    f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}"
                )
                for emp in employees
            ]
        form = QuickAdjustForm(request.form)
        form.employee_id.choices = employee_options
        logging.debug("Quick adjust form data received: %s", {k: v if k != 'password' else '****' for k, v in request.form.items()})
        if not form.validate():
            logging.error("Quick adjust form validation failed: %s, form data: %s", form.errors, {k: v if k != 'password' else '****' for k, v in request.form.items()})
            return jsonify({"success": False, "message": "Invalid form data: " + str(form.errors)}), 400
        if "admin_id" not in session:
            if not form.username.data or not form.password.data:
                logging.error("Quick adjust form missing username or password for non-admin")
                return jsonify({"success": False, "message": "Username and password required for non-admin users"}), 400
            username = form.username.data
            password = form.password.data
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if not admin or not check_password_hash(admin["password"], password):
                    logging.error("Invalid admin credentials for username: %s", username)
                    return jsonify({"success": False, "message": "Invalid admin credentials"}), 403
                session["admin_id"] = admin["admin_id"]
                session["last_activity"] = datetime.now().isoformat()
        employee_id = form.employee_id.data
        points = form.points.data
        reason = form.reason.data
        notes = form.notes.data or ""
        with DatabaseConnection() as conn:
            role_row = conn.execute(
                "SELECT LOWER(role) AS role FROM employees WHERE employee_id = ?",
                (employee_id,)
            ).fetchone()
            if role_row and role_row["role"] == "master":
                logging.warning(
                    "Attempt to quick adjust points for master account: employee_id=%s", employee_id
                )
                return (
                    jsonify({"success": False, "message": "Cannot adjust points for master account"}),
                    400,
                )
            success, message = adjust_points(
                conn, employee_id, points, session["admin_id"], reason, notes
            )
            if not success:
                logging.error("Quick adjust failed: %s", message)
                return jsonify({"success": False, "message": message}), 400
            conn.commit()
        global _data_cache, _cache_timestamp
        _data_cache = None
        _cache_timestamp = None
        logging.debug(f"Route /admin/quick_adjust_points took {time.time() - start_time:.2f} seconds")
        script = "playJackpot();" if points and points > 0 else ""
        return jsonify({"success": True, "message": f"Adjusted {points} points for employee {employee_id}", "script": script})
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
        try:
            valid = form.validate_on_submit()
        except Exception as e:
            logging.error("Reactivate employee form validation exception: %s", str(e))
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(e)}), 400
        if not valid:
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
        pin = form.pin.data
        with DatabaseConnection() as conn:
            success, message = edit_employee(conn, employee_id, name, role, pin)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_edit_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500


@app.route("/admin/award_game", methods=["POST"])
def admin_award_game():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            employee_options = [
                (emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}")
                for emp in employees
            ]
        form = AwardGameForm(request.form)
        form.employee_id.choices = employee_options
        if not form.validate_on_submit():
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        employee_id = form.employee_id.data
        game_type = form.game_type.data
        with DatabaseConnection() as conn:
            success, gt = award_mini_game(conn, employee_id, game_type)
        return jsonify({'success': success, 'message': f'Awarded {gt} game'})
    except Exception as e:
        logging.error(f"Error in admin_award_game: {str(e)}\n{traceback.format_exc()}")
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
    with DatabaseConnection() as conn:
        admins = conn.execute("SELECT username FROM admins").fetchall()
    form.old_username.choices = [(row["username"], row["username"]) for row in admins]
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
    except sqlite3.IntegrityError:
        logging.error("Update admin failed: username '%s' already exists", new_username)
        return jsonify({"success": False, "message": "Username already exists"}), 400
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
    start_time = time.time()
    try:
        form = EditRuleForm()
        logging.debug("Edit rule form data received: %s", {k: v for k, v in request.form.items()})
        if not form.validate_on_submit():
            logging.error("Edit rule form validation failed: %s, form data: %s", form.errors, {k: v for k, v in request.form.items()})
            flash(f"Invalid form data: {form.errors}", "danger")
            return jsonify({"success": False, "message": f"Invalid form data: {form.errors}"}), 400
        with DatabaseConnection() as conn:
            success, message = edit_rule(
                conn,
                form.old_description.data,
                form.new_description.data,
                form.points.data,
                form.details.data or ""
            )
            if not success:
                logging.error("Edit rule failed: %s", message)
                flash(message, "danger")
                return jsonify({"success": False, "message": message}), 400
            conn.commit()
        logging.debug(f"Route /admin/edit_rule took {time.time() - start_time:.2f} seconds")
        flash("Rule updated successfully", "success")
        return jsonify({"success": True, "message": "Rule updated successfully"})
    except Exception as e:
        logging.error(f"Error in admin_edit_rule: {str(e)}\n{traceback.format_exc()}")
        flash(f"Server error: {str(e)}", "danger")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
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

@app.route("/admin/toggle_section", methods=["POST"])
def admin_toggle_section():
    if session.get("admin_id") != "master":
        return redirect(url_for("admin"))
    section = request.form.get("section")
    allow = '1' if request.form.get("allow") == 'on' else '0'
    try:
        with DatabaseConnection() as conn:
            set_settings(conn, f"allow_section_{section}", allow)
        flash("Section permissions updated", "success")
    except Exception as e:
        logging.error(f"Error toggling section permission: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
    return redirect(url_for("admin"))

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
        if not form.validate_on_submit():
            logging.error("Set point decay form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        role_name = form.role_name.data
        points = form.points.data
        days = form.days.data
        logging.debug("Set point decay form data: %s", {k: v if k != 'password' else '****' for k, v in request.form.items()})
        logging.debug("Role choices: %s", form.role_name.choices)
        logging.debug("Days received: %s", days)
        with DatabaseConnection() as conn:
            success, message = set_point_decay(conn, role_name, points, days)
        return jsonify({"success": success, "message": message, "role_name": role_name, "points": points, "days": days})
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

@app.route("/voting_status", methods=["GET"])
def voting_status():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin access required"}), 403
    try:
        with DatabaseConnection() as conn:
            active_session = conn.execute(
                "SELECT session_id FROM voting_sessions WHERE end_time IS NULL"
            ).fetchone()
            if not active_session:
                return jsonify({"success": True, "status": []})
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS vote_participants (
                    session_id INTEGER,
                    voter_initials TEXT,
                    PRIMARY KEY (session_id, voter_initials),
                    FOREIGN KEY(session_id) REFERENCES voting_sessions(session_id)
                )
                """
            )
            voted_initials = set(
                row["voter_initials"].lower()
                for row in conn.execute(
                    "SELECT voter_initials FROM vote_participants WHERE session_id = ?",
                    (active_session["session_id"],),
                ).fetchall()
            )
            active_emps = conn.execute(
                "SELECT initials FROM employees WHERE active = 1 AND LOWER(role) != 'master'"
            ).fetchall()
            status = [
                {"initials": emp["initials"], "voted": emp["initials"].lower() in voted_initials}
                for emp in active_emps
            ]
            status.sort(key=lambda x: x["voted"])
        response = jsonify({"success": True, "status": status})
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response
    except Exception as e:
        logging.error(f"Error in voting_status: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/history", methods=["GET"])
def history():
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None
    employee_id = request.args.get("employee_id") or None
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(
                conn,
                employee_id=employee_id,
                start_date=start_date if start_date and end_date else None,
                end_date=end_date if start_date and end_date else None,
            )]
            employees = conn.execute(
                "SELECT employee_id, name FROM employees ORDER BY name"
            ).fetchall()
            employee_options = [('', 'All Employees')] + [
                (str(e["employee_id"]), e["name"]) for e in employees
            ]
        logging.debug(
            f"Rendering history.html: history_count={len(history)}, employee_count={len(employee_options)}"
        )
        return render_template(
            "history.html",
            history=history,
            employees=employee_options,
            is_admin=bool(session.get("admin_id")),
            import_time=int(time.time()),
            start_date=start_date,
            end_date=end_date,
            selected_employee=employee_id,
        )
    except Exception as e:
        logging.error(f"Error in history: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('show_incentive'))


@app.route("/export_payout", methods=["GET"])
def export_payout():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    if not start_date or not end_date:
        flash("Start and end dates are required", "danger")
        return redirect(url_for('admin'))
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, start_date=start_date, end_date=end_date)]
            pot_info = get_pot_info(conn)
            employees = conn.execute("SELECT employee_id, name, role FROM employees WHERE active = 1").fetchall()
            df = pd.DataFrame(history)
            grouped = {}
            if not df.empty:
                grouped = {emp_id: group for emp_id, group in df.groupby('employee_id')}
            output_lines = []
            for emp in employees:
                employee_id = emp['employee_id']
                name = emp['name']
                role = emp['role'].lower().replace(" ", "_")
                group = grouped.get(employee_id)
                total_points = group['points'].sum() if group is not None else 0
                point_value = pot_info.get(f"{role}_point_value", 0.0)
                total_dollars = total_points * point_value if total_points > 0 and total_points >= 50 else 0.0
                output_lines.append(f"Employee: {name}")
                output_lines.append("Employee ID,Name,Role,Total Points,Total Dollars")
                output_lines.append(f"{employee_id},{name},{role},{total_points},{total_dollars:.2f}")
                output_lines.append("")
                output_lines.append("Date,Reason,Points,Dollar Value,Changed By,Notes")
                if group is not None:
                    for _, row in group.iterrows():
                        dollar_value = row['points'] * point_value if row['points'] > 0 else 0.0
                        notes = row.get('notes', '')
                        output_lines.append(f"{row['date']},\"{row['reason']}\",{row['points']},{dollar_value:.2f},{row['changed_by']},\"{notes}\"")
                output_lines.append("")
            output = io.BytesIO()
            output.write("\n".join(output_lines).encode())
            output.seek(0)
        filename = f"payout_{start_date}_to_{end_date}.csv"
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)
    except Exception as e:
        logging.error(f"Error in export_payout: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/history_chart", methods=["GET"])
def history_chart():
    employee_id = request.args.get("employee_id") or None
    start_date = request.args.get("start_date") or None
    end_date = request.args.get("end_date") or None
    try:
        with DatabaseConnection() as conn:
            history = [
                dict(row)
                for row in get_history(
                    conn,
                    employee_id=employee_id,
                    start_date=start_date if start_date and end_date else None,
                    end_date=end_date if start_date and end_date else None,
                )
            ]
        if not history:
            fig, ax = plt.subplots(figsize=(5, 3))
            ax.text(0.5, 0.5, "No Data", ha="center", va="center")
            ax.axis("off")
            output = io.BytesIO()
            fig.savefig(output, format="png")
            plt.close(fig)
            output.seek(0)
            return send_file(output, mimetype="image/png")
        df = pd.DataFrame(history)
        df["date"] = pd.to_datetime(df["date"], format="mixed")
        df.sort_values("date", inplace=True)
        df["cumulative_points"] = df["points"].cumsum()
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(df["date"], df["cumulative_points"])
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Points")
        emp_name = df.iloc[0]["name"]
        ax.set_title(f"{emp_name} Points Over Time")
        ax.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()
        output = io.BytesIO()
        fig.savefig(output, format="png")
        plt.close(fig)
        output.seek(0)
        return send_file(output, mimetype="image/png")
    except Exception as e:
        logging.error(f"Error in history_chart: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

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
        if 'port' in request.form:
            form = PortForm(request.form)
            if not form.validate_on_submit():
                flash("Invalid port", "danger")
                return redirect(url_for('admin_settings'))
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'port', str(form.port.data))
                try:
                    service_file = f"/etc/systemd/system/{Config.SERVICE_NAME}"
                    try:
                        subprocess.run([
                            "sudo", "bash", "-c",
                            f"sed -i 's/--bind 0\\.0\\.0\\.0:[0-9]\\+/--bind 0.0.0.0:{form.port.data}/' {service_file}"
                        ], check=True)
                        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
                    except Exception as e:
                        logging.warning(f"Failed to update service file port: {str(e)}\n{traceback.format_exc()}")
                    subprocess.run(["sudo", "systemctl", "restart", Config.SERVICE_NAME], check=True)
                    flash('Port updated and service restarted', 'success')
                except Exception as e:
                    logging.error(f"Service restart failed after port update: {str(e)}\n{traceback.format_exc()}")
                    flash('Port updated but failed to restart service', 'warning')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating port: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating port', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'pos_threshold_1' in request.form:  # Handle VotingThresholdsForm
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
        elif 'max_total_votes' in request.form:  # Handle vote limits form
            form = VoteLimitsForm(request.form)
            if not form.validate_on_submit():
                logging.error("Vote limits form validation failed: %s", form.errors)
                flash("Invalid vote limits data: " + str(form.errors), "danger")
                return redirect(url_for('admin_settings'))
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'max_total_votes', str(form.max_total_votes.data))
                    set_settings(conn, 'max_plus_votes', str(form.max_plus_votes.data))
                    set_settings(conn, 'max_minus_votes', str(form.max_minus_votes.data))
                flash('Vote limits updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating vote limits: {str(e)}\n{traceback.format_exc()}")
                flash("Server error updating vote limits", "danger")
                return redirect(url_for('admin_settings'))
        elif 'money_threshold' in request.form:  # Handle scoreboard settings form
            form = ScoreboardSettingsForm(request.form)
            if not form.validate_on_submit():
                logging.error("Scoreboard settings form validation failed: %s", form.errors)
                flash("Invalid scoreboard settings data: " + str(form.errors), "danger")
                return redirect(url_for('admin_settings'))
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'money_threshold', str(form.money_threshold.data))
                    set_settings(conn, 'score_top_color', form.top_color.data)
                    set_settings(conn, 'score_mid_color', form.mid_color.data)
                    set_settings(conn, 'score_bottom_color', form.bottom_color.data)
                    set_settings(conn, 'reel_color', form.reel_color.data)
                    set_settings(conn, 'scoreboard_spin_duration', str(form.spin_duration.data))
                    set_settings(conn, 'scoreboard_spin_iterations', str(form.spin_iterations.data))
                    set_settings(conn, 'scoreboard_spin_pause', str(form.spin_pause.data))
                    set_settings(conn, 'scoreboard_spin_delay', str(form.spin_delay.data))
                    set_settings(conn, 'scoreboard_refresh_interval', str(form.refresh_interval.data))
                flash('Scoreboard settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating scoreboard settings: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating scoreboard settings', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'month_mode' in request.form:  # Handle reporting settings form
            month_mode = request.form.get('month_mode')
            week_start_day = request.form.get('week_start_day')
            auto_vote_day = request.form.get('auto_vote_day')
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'month_mode', month_mode)
                    set_settings(conn, 'week_start_day', week_start_day)
                    set_settings(conn, 'auto_vote_day', auto_vote_day)
                flash('Reporting settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating reporting settings: {str(e)}\n{traceback.format_exc()}")
                flash("Server error updating reporting settings", "danger")
                return redirect(url_for('admin_settings'))
        elif any(key.startswith('role_weight_') for key in request.form.keys()):
            try:
                with DatabaseConnection() as conn:
                    roles = [row['role_name'] for row in conn.execute('SELECT role_name FROM roles').fetchall()]
                    weights = {}
                    for role in roles:
                        field = f'role_weight_{role}'
                        weight_str = request.form.get(field)
                        try:
                            weight = float(weight_str)
                        except (TypeError, ValueError):
                            flash(f"Invalid weight for role {role}", 'danger')
                            return redirect(url_for('admin_settings'))
                        weights[role] = weight
                    set_settings(conn, 'role_vote_weights', json.dumps(weights))
                flash('Role vote weights updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating role vote weights: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating role vote weights', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'theme_settings' in request.form:
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'site_name', request.form.get('site_name', ''))
                    set_settings(conn, 'site_title', request.form.get('site_title', ''))
                    set_settings(conn, 'primary_color', request.form.get('primary_color', '#D4AF37'))
                    set_settings(conn, 'secondary_color', request.form.get('secondary_color', '#000000'))
                    set_settings(conn, 'background_color', request.form.get('background_color', '#3A3A3A'))
                    set_settings(conn, 'surface_color', request.form.get('surface_color', '#222222'))
                    set_settings(conn, 'surface_alt_color', request.form.get('surface_alt_color', '#1A1A1A'))
                    set_settings(conn, 'banner_text', request.form.get('banner_text', "JACKPOT TIME! GIVE 'EM THE MONEY! SLOTS SPINNING - WINNERS GRINNING!"))
                    set_settings(conn, 'strobe_mode', 'on' if request.form.get('strobe_mode') == 'on' else 'off')
                flash('Theme settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating theme settings: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating theme settings', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'mini_game_settings' in request.form:  # Handle mini-game settings form
            try:
                with DatabaseConnection() as conn:
                    # Build mini-game config JSON from form data
                    mini_game_config = {
                        "award_chance_points": int(request.form.get('award_chance_points', 10)),
                        "award_chance_vote": int(request.form.get('award_chance_vote', 15)),
                        "prizes": {
                            "points": {
                                "amount": int(request.form.get('points_prize_amount', 5)),
                                "chance": int(request.form.get('points_prize_chance', 20))
                            },
                            "prize1": {
                                "desc": "Gift Card",
                                "value": int(request.form.get('gift_card_value', 25)),
                                "chance": int(request.form.get('gift_card_chance', 10))
                            },
                            "prize2": {
                                "desc": request.form.get('prize2_desc', 'Extra Break'),
                                "value": 0,
                                "chance": int(request.form.get('prize2_chance', 30))
                            },
                            "prize3": {
                                "desc": request.form.get('prize3_desc', 'Company Swag'),
                                "value": int(request.form.get('prize3_value', 10)),
                                "chance": int(request.form.get('prize3_chance', 5))
                            }
                        },
                        "game_types": ["slot", "scratch", "roulette"]
                    }
                    set_settings(conn, 'mini_game_settings', json.dumps(mini_game_config))
                flash('Mini-game settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating mini-game settings: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating mini-game settings', 'danger')
                return redirect(url_for('admin_settings'))
        elif 'system_settings' in request.form:  # Handle system settings form
            try:
                with DatabaseConnection() as conn:
                    set_settings(conn, 'program_end_date', request.form.get('program_end_date', ''))
                    set_settings(conn, 'sound_on', '1' if request.form.get('sound_on') == '1' else '0')
                    set_settings(conn, 'allow_section_rules', '1' if request.form.get('allow_section_rules') == '1' else '0')
                    set_settings(conn, 'allow_section_manage_roles', '1' if request.form.get('allow_section_manage_roles') == '1' else '0')
                flash('System settings updated', 'success')
                return redirect(url_for('admin_settings'))
            except Exception as e:
                logging.error(f"Error updating system settings: {str(e)}\n{traceback.format_exc()}")
                flash('Server error updating system settings', 'danger')
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
            vote_limits_form = VoteLimitsForm()
            vote_limits_form.max_total_votes.data = int(settings.get('max_total_votes', 3))
            vote_limits_form.max_plus_votes.data = int(settings.get('max_plus_votes', 2))
            vote_limits_form.max_minus_votes.data = int(settings.get('max_minus_votes', 3))
            scoreboard_form = ScoreboardSettingsForm()
            scoreboard_form.money_threshold.data = int(settings.get('money_threshold', 50))
            scoreboard_form.top_color.data = settings.get('score_top_color', '#D4AF37')
            scoreboard_form.mid_color.data = settings.get('score_mid_color', '#FFFFFF')
            scoreboard_form.bottom_color.data = settings.get('score_bottom_color', '#FF6347')
            scoreboard_form.reel_color.data = settings.get('reel_color', '#FFD700')
            scoreboard_form.spin_duration.data = int(settings.get('scoreboard_spin_duration', 10))
            scoreboard_form.spin_iterations.data = int(settings.get('scoreboard_spin_iterations', 0))
            scoreboard_form.spin_pause.data = int(settings.get('scoreboard_spin_pause', 0))
            scoreboard_form.spin_delay.data = int(settings.get('scoreboard_spin_delay', 0))
            scoreboard_form.refresh_interval.data = int(settings.get('scoreboard_refresh_interval', 60))
            roles = [row['role_name'] for row in conn.execute('SELECT role_name FROM roles').fetchall()]
            try:
                role_weights = json.loads(settings.get('role_vote_weights', '{}'))
            except json.JSONDecodeError:
                role_weights = {}
            if not role_weights:
                for role in roles:
                    if role.lower() == 'supervisor':
                        role_weights[role] = 2.0
                    elif role.lower() == 'master':
                        role_weights[role] = 3.0
                    else:
                        role_weights[role] = 1.0
                set_settings(conn, 'role_vote_weights', json.dumps(role_weights))
            master_reset_form = MasterResetForm()
            port_form = PortForm()
            port_form.port.data = int(settings.get('port', 8101))
            restart_service_form = RestartServiceForm()
            reboot_pi_form = RebootPiForm()
            
            # Parse mini-game settings for template
            mini_game_config = {}
            try:
                mini_game_config = json.loads(settings.get('mini_game_settings', '{}'))
            except json.JSONDecodeError:
                mini_game_config = {}

        return render_template(
            "settings.html",
            settings=settings,
            is_master=session.get("admin_id") == "master",
            import_time=int(time.time()),
            admin_page=True,
            form=form,
            thresholds_form=form,
            vote_limits_form=vote_limits_form,
            scoreboard_form=scoreboard_form,
            master_reset_form=master_reset_form,
            port_form=port_form,
            restart_service_form=restart_service_form,
            reboot_pi_form=reboot_pi_form,
            month_mode=settings.get('month_mode', 'calendar'),
            week_start_day=settings.get('week_start_day', 'Monday'),
            auto_vote_day=settings.get('auto_vote_day', ''),
            roles=roles,
            role_weights=role_weights,
            mini_game_config=mini_game_config,
        )
    except Exception as e:
        logging.error(f"Error in admin_settings GET: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))


@app.route("/admin/restart_service", methods=["POST"])
def admin_restart_service():
    if "admin_id" not in session or session.get("admin_id") != "master":
        flash("Master admin required", "danger")
        return redirect(url_for('admin'))
    form = RestartServiceForm()
    if form.validate_on_submit():
        try:
            subprocess.run(["sudo", "systemctl", "restart", Config.SERVICE_NAME], check=True)
            flash("Service restart initiated", "success")
        except Exception as e:
            logging.error(f"Service restart failed: {str(e)}\n{traceback.format_exc()}")
            flash("Failed to restart service", "danger")
    return redirect(url_for('admin_settings'))


@app.route("/admin/reboot_pi", methods=["POST"])
def admin_reboot_pi():
    if "admin_id" not in session or session.get("admin_id") != "master":
        flash("Master admin required", "danger")
        return redirect(url_for('admin'))
    form = RebootPiForm()
    if form.validate_on_submit():
        try:
            subprocess.run(["sudo", "reboot"], check=True)
            flash("Rebooting", "success")
        except Exception as e:
            logging.error(f"Reboot failed: {str(e)}\n{traceback.format_exc()}")
            flash("Failed to reboot", "danger")
    return redirect(url_for('admin_settings'))


@app.route("/employee_portal", methods=["GET", "POST"])
def employee_portal():
    login_form = EmployeeLoginForm()
    if request.method == "POST" and login_form.validate_on_submit():
        employee_id = login_form.employee_id.data
        pin = login_form.pin.data
        with DatabaseConnection() as conn:
            if verify_pin(conn, employee_id, pin):
                session['employee_id'] = employee_id
                flash("Access granted", "success")
                return redirect(url_for('employee_portal'))
            else:
                flash("Invalid ID or PIN", "danger")
    if 'employee_id' in session:
        with DatabaseConnection() as conn:
            emp = conn.execute("SELECT employee_id, name, score FROM employees WHERE employee_id=?", (session['employee_id'],)).fetchone()
            unused = conn.execute("SELECT id, game_type, awarded_date FROM mini_games WHERE employee_id=? AND status='unused'", (session['employee_id'],)).fetchall()
            used = conn.execute("SELECT id, game_type, outcome, played_date FROM mini_games WHERE employee_id=? AND status='played'", (session['employee_id'],)).fetchall()
        change_pin_form = ChangePinForm()
        return render_template('employee_portal.html', login_form=login_form, change_pin_form=change_pin_form, employee=emp, unused_games=unused, used_games=used)
    return render_template('employee_portal.html', login_form=login_form, employee=None)


@app.route("/employee/change_pin", methods=["POST"])
def employee_change_pin():
    if 'employee_id' not in session:
        return redirect(url_for('employee_portal'))
    form = ChangePinForm()
    if form.validate_on_submit():
        with DatabaseConnection() as conn:
            if verify_pin(conn, session['employee_id'], form.current_pin.data):
                new_hash = generate_password_hash(form.new_pin.data)
                conn.execute("UPDATE employees SET pin_hash=? WHERE employee_id=?", (new_hash, session['employee_id']))
                conn.commit()
                flash("PIN updated", "success")
            else:
                flash("Current PIN incorrect", "danger")
    else:
        flash("Invalid form data", "danger")
    return redirect(url_for('employee_portal'))


@app.route("/employee/logout", methods=["POST"])
def employee_logout():
    session.pop('employee_id', None)
    flash("Logged out", "info")
    return redirect(url_for('employee_portal'))


@app.route("/play_game/<int:game_id>", methods=["POST"])
def play_game(game_id):
    """Enhanced Vegas-style mini game with proper casino mechanics"""
    if 'employee_id' not in session:
        return jsonify({'success': False, 'message': 'Authentication required'}), 401
    
    try:
        with DatabaseConnection() as conn:
            # Verify game ownership and status
            game_row = conn.execute(
                "SELECT employee_id, game_type FROM mini_games WHERE id=? AND status='unused'", 
                (game_id,)
            ).fetchone()
            
            if not game_row or game_row['employee_id'] != session['employee_id']:
                return jsonify({'success': False, 'message': 'Invalid or unavailable game'}), 403
            
            game_type = game_row['game_type']
            
            # Get game configuration
            settings = get_settings(conn)
            cfg = json.loads(settings.get('mini_game_settings', '{}'))
            
            # Play the specific game type
            if game_type == 'slot':
                result = play_slot_machine_game(cfg)
            elif game_type == 'scratch':
                result = play_scratch_off_game(cfg)
            elif game_type == 'roulette':
                result = play_roulette_game(cfg)
            else:
                result = play_generic_game(cfg)
            
            # Process the game outcome
            outcome_data = {
                'game_type': game_type,
                'result': result['outcome'],
                'win': result['win'],
                'prize_type': result.get('prize_type'),
                'prize_amount': result.get('prize_amount', 0),
                'timestamp': datetime.now().isoformat()
            }
            
            # Award prizes if won
            if result['win'] and result.get('prize_amount', 0) > 0:
                adjust_points(
                    conn, 
                    session['employee_id'], 
                    result['prize_amount'], 
                    f"Vegas {game_type.title()} Game Win"
                )
            
            # Record the game play
            play_mini_game(conn, game_id, json.dumps(outcome_data))
            conn.commit()
            
            # Format response message
            if result['win']:
                if result.get('prize_amount', 0) >= 50:
                    message = f"🎉 JACKPOT! You won {result['prize_amount']} points! 🎉"
                elif result.get('prize_amount', 0) > 0:
                    message = f"🎰 Winner! You earned {result['prize_amount']} points!"
                else:
                    message = f"🏆 You won: {result.get('prize_description', 'Special Prize')}!"
            else:
                message = "🎲 Better luck next time! Keep spinning!"
            
            return jsonify({
                'success': True,
                'message': message,
                'result': result,
                'jackpot': result.get('prize_amount', 0) >= 50
            })
            
    except Exception as e:
        logging.error(f"Error in play_game: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Casino malfunction! Try again.'}), 500


def play_slot_machine_game(config):
    """Professional 3-reel slot machine with Vegas payouts"""
    symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎', '🔔', '🎰']
    weights = [20, 18, 15, 12, 10, 8, 5, 2]  # Weighted probability
    
    reels = []
    for _ in range(3):
        reel = random.choices(symbols, weights=weights)[0]
        reels.append(reel)
    
    # Calculate winnings
    win = False
    prize_amount = 0
    
    # Three of a kind (JACKPOT!)
    if reels[0] == reels[1] == reels[2]:
        win = True
        payouts = {
            '🍒': 10, '🍋': 15, '🍊': 20, '🍇': 25,
            '⭐': 50, '💎': 100, '🔔': 150, '🎰': 250
        }
        prize_amount = payouts.get(reels[0], 5)
    
    # Two of a kind (partial win)
    elif reels[0] == reels[1] or reels[1] == reels[2] or reels[0] == reels[2]:
        win = True
        prize_amount = 5
    
    return {
        'outcome': {'reels': reels, 'pattern': 'slots'},
        'win': win,
        'prize_type': 'points',
        'prize_amount': prize_amount
    }


def play_scratch_off_game(config):
    """Scratch-off lottery with hidden prizes"""
    prizes = [
        {'type': 'points', 'amount': 5, 'chance': 30, 'desc': '5 Points'},
        {'type': 'points', 'amount': 10, 'chance': 20, 'desc': '10 Points'},
        {'type': 'points', 'amount': 25, 'chance': 15, 'desc': '25 Points'},
        {'type': 'points', 'amount': 50, 'chance': 10, 'desc': '50 Points JACKPOT'},
        {'type': 'bonus', 'amount': 0, 'chance': 15, 'desc': 'Extra Break'},
        {'type': 'bonus', 'amount': 0, 'chance': 10, 'desc': 'Priority Parking'}
    ]
    
    # Generate scratch pattern
    scratch_grid = []
    for _ in range(3):
        row = [random.choice(['💰', '⭐', '🍀', '❌']) for _ in range(3)]
        scratch_grid.append(row)
    
    # Determine if win (3 matching symbols)
    flat_grid = [item for row in scratch_grid for item in row]
    symbol_counts = {symbol: flat_grid.count(symbol) for symbol in set(flat_grid)}
    
    win = any(count >= 3 for count in symbol_counts.values())
    
    if win:
        # Weighted random prize selection
        total_weight = sum(p['chance'] for p in prizes)
        rand_weight = random.uniform(0, total_weight)
        
        cumulative = 0
        selected_prize = prizes[0]  # Default
        
        for prize in prizes:
            cumulative += prize['chance']
            if rand_weight <= cumulative:
                selected_prize = prize
                break
        
        return {
            'outcome': {'grid': scratch_grid, 'winning_symbol': max(symbol_counts, key=symbol_counts.get)},
            'win': True,
            'prize_type': selected_prize['type'],
            'prize_amount': selected_prize['amount'],
            'prize_description': selected_prize['desc']
        }
    
    return {
        'outcome': {'grid': scratch_grid},
        'win': False
    }


def play_roulette_game(config):
    """Mini roulette with 0-36 numbers"""
    winning_number = random.randint(0, 36)
    color = 'green' if winning_number == 0 else ('red' if winning_number % 2 == 1 else 'black')
    
    # Simple betting system - bet on even/odd
    player_bet = random.choice(['even', 'odd', 'red', 'black'])
    
    win = False
    prize_amount = 0
    
    if winning_number == 0:
        # House always wins on 0
        win = False
    elif player_bet == 'even' and winning_number % 2 == 0:
        win = True
        prize_amount = 10
    elif player_bet == 'odd' and winning_number % 2 == 1:
        win = True
        prize_amount = 10
    elif player_bet == 'red' and color == 'red':
        win = True
        prize_amount = 15
    elif player_bet == 'black' and color == 'black':
        win = True
        prize_amount = 15
    
    # Lucky numbers bonus
    if winning_number in [7, 17, 27]:
        win = True
        prize_amount = max(prize_amount, 25)
    
    return {
        'outcome': {
            'number': winning_number,
            'color': color,
            'bet': player_bet
        },
        'win': win,
        'prize_type': 'points',
        'prize_amount': prize_amount
    }


def play_generic_game(config):
    """Fallback generic game"""
    win = random.random() < 0.3  # 30% win chance
    prize_amount = random.choice([5, 10, 15, 25]) if win else 0
    
    return {
        'outcome': {'type': 'generic', 'roll': random.randint(1, 100)},
        'win': win,
        'prize_type': 'points',
        'prize_amount': prize_amount
    }


@app.route("/api/game-config")
def get_game_config():
    """API endpoint for game configuration"""
    try:
        with DatabaseConnection() as conn:
            settings = get_settings(conn)
            config = json.loads(settings.get('mini_game_settings', '{}'))
            return jsonify(config)
    except Exception as e:
        logging.error(f"Error getting game config: {e}")
        return jsonify({'error': 'Configuration unavailable'}), 500


@app.errorhandler(500)
def internal_error(e):
    logging.error(f"500 error: {e}")
    return render_template('error.html', error="🎰 JACKPOT JAM! Tech gremlins invaded the casino—retry your spin! 🎰"), 500


if __name__ == "__main__":
    logging.debug("Running Flask app in debug mode")
    app.run(host="0.0.0.0", port=6800, debug=True)
else:
    logging.debug("Running Flask app under Gunicorn")