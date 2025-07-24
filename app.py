# app.py
# Version: 1.2.33
# Note: Fixed JSON response issue in /vote route to prevent HTML redirects causing SyntaxError on client. Added CSRF validation and server-side logging for debugging. Ensured compatibility with incentive.html (1.2.17), admin_manage.html (1.2.16), quick_adjust.html (1.2.7), incentive_service.py (1.2.8), forms.py (1.2.2), script.js (1.2.28), style.css (1.2.11). Maintained all fixes from version 1.2.32 (total_payout calculation, startup logging, pause_voting SyntaxError, admin_manage.html UndefinedError, admin_edit_rule TypeError, week_options computation, admin_export_payout enhancements). No changes to core functionality.

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory, flash
from werkzeug.security import check_password_hash, generate_password_hash
from flask_wtf.csrf import CSRFProtect, CSRFError
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, edit_rule, remove_rule, get_pot_info, update_pot_info, close_voting_session, pause_voting_session, get_voting_results, master_reset_all, get_roles, add_role, edit_role, remove_role, edit_employee, reorder_rules, retire_employee, reactivate_employee, delete_employee, set_point_decay, get_point_decay, deduct_points_daily, get_latest_voting_results, add_feedback, get_unread_feedback_count, get_feedback, mark_feedback_read, delete_feedback, get_settings, set_settings
from forms import VoteForm, AdminLoginForm, StartVotingForm, AddEmployeeForm, AdjustPointsForm, AddRuleForm, EditRuleForm, RemoveRuleForm, EditEmployeeForm, RetireEmployeeForm, ReactivateEmployeeForm, DeleteEmployeeForm, UpdatePotForm, UpdatePriorYearSalesForm, SetPointDecayForm, UpdateAdminForm, AddRoleForm, EditRoleForm, RemoveRoleForm, MasterResetForm, FeedbackForm
import logging
import time
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

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config.from_object('config.Config')
csrf = CSRFProtect(app)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logging.getLogger('gunicorn.error').setLevel(logging.DEBUG)
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.debug("Application starting, initializing Flask app")

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
                        time.sleep(3600)
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
                last_checked = current_date
            except Exception as e:
                logging.error(f"Point decay error: {str(e)}\n{traceback.format_exc()}")
            time.sleep(86400)
        else:
            time.sleep(3600)
    logging.debug("Point_decay_thread terminated unexpectedly")

threading.Thread(target=point_decay_thread, daemon=True).start()
logging.debug("Point_decay_thread started")

def get_score_class(score):
    if score <= 5: return 'score-low-0'
    if score <= 10: return 'score-low-5'
    if score <= 15: return 'score-low-10'
    if score <= 20: return 'score-low-15'
    if score <= 25: return 'score-low-20'
    if score <= 30: return 'score-low-25'
    if score <= 35: return 'score-low-30'
    if score <= 40: return 'score-low-35'
    if score <= 45: return 'score-low-40'
    if score <= 50: return 'score-low-45'
    if score <= 55: return 'score-mid-50'
    if score <= 60: return 'score-mid-55'
    if score <= 65: return 'score-mid-60'
    if score <= 70: return 'score-mid-65'
    if score <= 75: return 'score-mid-70'
    if score <= 80: return 'score-high-75'
    if score <= 85: return 'score-high-80'
    if score <= 90: return 'score-high-85'
    if score <= 95: return 'score-high-90'
    if score <= 100: return 'score-high-95'
    return 'score-high-100'

@app.before_request
def make_session_permanent():
    session.permanent = True
    if 'admin_id' in session and request.endpoint in ['admin', 'admin_add', 'admin_adjust_points', 'admin_quick_adjust_points', 'admin_retire_employee', 'admin_reactivate_employee', 'admin_delete_employee', 'admin_edit_employee', 'admin_reset', 'admin_master_reset', 'admin_update_admin', 'admin_add_rule', 'admin_edit_rule', 'admin_remove_rule', 'admin_reorder_rules', 'admin_add_role', 'admin_edit_role', 'admin_remove_role', 'admin_update_pot', 'admin_update_prior_year_sales', 'admin_set_point_decay', 'admin_mark_feedback_read', 'admin_delete_feedback', 'admin_settings', 'quick_adjust', 'export_payout']:
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
            week_number = request.args.get("week", None, type=int)
            voting_results = get_voting_results(conn, is_admin=False, week_number=week_number)
            unread_feedback = get_unread_feedback_count(conn) if session.get("admin_id") else 0
            feedback = []
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            week_options = [('', 'All Weeks')] + [(str(i), f"Week {i}") for i in range(1, 53)]
        current_month = datetime.now().strftime("%B %Y")
        logging.debug(f"Rendering incentive.html: voting_active={voting_active}, results_count={len(voting_results)}")
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
            week_options=week_options
        )
    except Exception as e:
        logging.error(f"Error in show_incentive: {str(e)}\n{traceback.format_exc()}")
        flash("Internal server error", "danger")
        return render_template("error.html", error="Internal Server Error"), 500

@app.route("/favicon.ico")
def favicon():
    return send_from_directory(app.static_folder, 'favicon.ico')

@app.route("/data", methods=["GET"])
def incentive_data():
    try:
        with DatabaseConnection() as conn:
            scoreboard = [dict(row) for row in get_scoreboard(conn)]
            voting_active = is_voting_active(conn)
            pot_info = get_pot_info(conn)
        logging.debug(f"Serving /data: scoreboard_size={len(scoreboard)}, voting_active={voting_active}")
        return jsonify({"scoreboard": scoreboard, "voting_active": voting_active, "pot_info": pot_info})
    except Exception as e:
        logging.error(f"Error in incentive_data: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": "Internal Server Error"}), 500

@app.route("/start_voting", methods=["GET", "POST"])
def start_voting():
    if request.method == "GET":
        logging.debug("Rendering start_voting.html")
        return render_template("start_voting.html", is_master=session.get("admin_id") == "master", import_time=int(time.time()))
    form = StartVotingForm(request.form)
    if not form.validate_on_submit():
        logging.error("Start voting form validation failed: %s", form.errors)
        flash("Invalid form data: " + str(form.errors), "danger")
        return render_template("start_voting.html", is_master=session.get("admin_id") == "master", import_time=int(time.time()))
    username = form.username.data
    password = form.password.data
    try:
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
            if admin and check_password_hash(admin["password"], password):
                success, message = start_voting_session(conn, admin["admin_id"])
                if success:
                    session['admin_id'] = admin["admin_id"]
                    session['last_activity'] = datetime.now().isoformat()
                    flash(message, "success")
                    return redirect(url_for('show_incentive'))
                flash(message, "danger")
            else:
                flash("Invalid admin credentials", "danger")
        return redirect(url_for('start_voting'))
    except Exception as e:
        logging.error(f"Error in start_voting: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('start_voting'))

@app.route("/close_voting", methods=["POST"])
def close_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = MasterResetForm(request.form)
    if not form.validate_on_submit():
        logging.error("Close voting form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    password = form.password.data
    try:
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE admin_id = ?", (session["admin_id"],)).fetchone()
            if not admin or not check_password_hash(admin["password"], password):
                return jsonify({'success': False, 'message': 'Invalid password'}), 403
            success, message = close_voting_session(conn, session["admin_id"])
            return jsonify({'success': success, 'message': message})
    except Exception as e:
        logging.error(f"Error in close_voting: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route("/pause_voting", methods=["POST"])
def pause_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
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
    votes = {key.split("_")[1]: int(value) for key, value in request.form.items() if key.startswith("vote_")}
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
    if request.method == "POST" and "username" in request.form:
        form = AdminLoginForm(request.form)
        if not form.validate_on_submit():
            logging.error("Admin login form validation failed: %s", form.errors)
            flash("Invalid form data: " + str(form.errors), "danger")
            return render_template("admin_login.html", import_time=int(time.time()))
        username = form.username.data
        password = form.password.data
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    session["admin_id"] = admin["admin_id"]
                    session['last_activity'] = datetime.now().isoformat()
                    logging.debug(f"Admin login successful: {username}")
                    return redirect(url_for("admin"))
                flash("Invalid credentials", "danger")
        except Exception as e:
            logging.error(f"Error in admin login: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
        logging.debug("Rendering admin_login.html due to failed login or GET request")
        return render_template("admin_login.html", import_time=int(time.time()))
    if "admin_id" not in session:
        logging.debug("Rendering admin_login.html: no admin_id in session")
        return render_template("admin_login.html", import_time=int(time.time()))
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
            roles = get_roles(conn)
            decay = get_point_decay(conn)
            admins = conn.execute("SELECT admin_id, username FROM admins").fetchall() if session.get("admin_id") == "master" else []
            voting_results = []
            history = [dict(row) for row in get_history(conn, datetime.now().strftime("%Y-%m"))]
            total_payout = 0
            for emp in employees:
                if emp["active"] == 1 and emp["score"] >= 50:
                    point_value = pot_info.get(emp["role"].lower().replace(" ", "_") + '_point_value', 0)
                    total_payout += emp["score"] * point_value
            if session.get("admin_id") == "master":
                results = conn.execute("""
                    SELECT vs.session_id, v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, COALESCE(vr.points, 0) AS points
                    FROM votes v
                    JOIN employees e ON v.recipient_id = e.employee_id
                    JOIN voting_sessions vs ON v.vote_date >= vs.start_time AND (v.vote_date <= vs.end_time OR vs.end_time IS NULL)
                    LEFT JOIN voting_results vr ON v.recipient_id = vr.employee_id AND vr.session_id = vs.session_id
                    ORDER BY vs.session_id DESC, v.vote_date DESC
                """).fetchall()
                voting_results = [dict(row) for row in results]
            unread_feedback = get_unread_feedback_count(conn)
            feedback = get_feedback(conn) if session.get("admin_id") == "master" else []
            settings = get_settings(conn)
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            role_options = [(role["role_name"], role["role_name"]) for role in roles]
            admin_options = [(admin["username"], f"{admin['username']} ({admin['admin_id']})") for admin in admins] if session.get("admin_id") == "master" else []
            decay_role_options = [(role["role_name"], f"{role['role_name']} (Current: {decay.get(role['role_name'], {'points': 1, 'days': []})['points']} points, {', '.join(decay.get(role['role_name'], {'days': []})['days'])})") for role in roles]
        current_month = datetime.now().strftime("%Y-%m")
        logging.debug(f"Rendering admin_manage.html: employees_count={len(employees)}, roles_count={len(roles)}, voting_results_count={len(voting_results)}")
        return render_template(
            "admin_manage.html",
            employees=employees,
            rules=rules,
            pot_info=pot_info,
            roles=roles,
            decay=decay,
            admins=admins,
            voting_results=voting_results,
            is_admin=True,
            is_master=session.get("admin_id") == "master",
            import_time=int(time.time()),
            unread_feedback=unread_feedback,
            feedback=feedback,
            settings=settings,
            current_month=current_month,
            employee_options=employee_options,
            role_options=role_options,
            admin_options=admin_options,
            decay_role_options=decay_role_options,
            history=history,
            total_payout=total_payout
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
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = AddEmployeeForm(request.form)
    if not form.validate_on_submit():
        logging.error("Add employee form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    name = form.name.data
    initials = form.initials.data
    role = form.role.data
    try:
        with DatabaseConnection() as conn:
            success, message = add_employee(conn, name, initials, role)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_add: {str(e)}\n{traceback.format_exc()}")
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
    if "admin_id" not in session:
        logging.debug("Rendering admin_login.html: no admin_id in session for quick_adjust")
        return render_template("admin_login.html", import_time=int(time.time()))
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            rules = get_rules(conn)
            employee_options = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) - {emp['score']} {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
        logging.debug(f"Rendering quick_adjust.html: employees_count={len(employees)}")
        return render_template("quick_adjust.html", employees=employees, rules=rules, employee_options=employee_options, is_admin=True, import_time=int(time.time()))
    except Exception as e:
        logging.error(f"Error in quick_adjust: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/admin/quick_adjust_points", methods=["POST"])
def admin_quick_adjust_points():
    if "admin_id" in session:
        form = AdjustPointsForm(request.form)
        if not form.validate_on_submit():
            logging.error("Quick adjust points form validation failed: %s", form.errors)
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
            logging.error(f"Error in admin_quick_adjust_points (session): {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    form = AdminLoginForm(request.form)
    if not form.validate_on_submit():
        logging.error("Quick adjust admin login form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid admin credentials: ' + str(form.errors)}), 400
    username = form.username.data
    password = form.password.data
    try:
        with DatabaseConnection() as conn:
            admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
            if not admin or not check_password_hash(admin["password"], password):
                return jsonify({"success": False, "message": "Invalid admin credentials"}), 403
            employee_id = request.form["employee_id"]
            points = int(request.form["points"])
            reason = request.form["reason"]
            notes = request.form.get("notes", "")
            success, message = adjust_points(conn, employee_id, points, admin["admin_id"], reason, notes)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_quick_adjust_points (form): {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/admin/retire_employee", methods=["POST"])
def admin_retire_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = RetireEmployeeForm(request.form)
    if not form.validate_on_submit():
        logging.error("Retire employee form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    employee_id = form.employee_id.data
    try:
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
    form = ReactivateEmployeeForm(request.form)
    if not form.validate_on_submit():
        logging.error("Reactivate employee form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    employee_id = form.employee_id.data
    try:
        with DatabaseConnection() as conn:
            success, Distress Response: {success: false, message: "Admin login required"}essage = reactivate_employee(conn, employee_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_reactivate_employee: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/delete_employee", methods=["POST"])
def admin_delete_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = DeleteEmployeeForm(request.form)
    if not form.validate_on_submit():
        logging.error("Delete employee form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    employee_id = form.employee_id.data
    try:
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
    form = EditEmployeeForm(request.form)
    if not form.validate_on_submit():
        logging.error("Edit employee form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    employee_id = form.employee_id.data
    name = form.name.data
    role = form.role.data
    try:
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
                return jsonify({"success": False, "message": "Invalid master password"}), 403
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
    if not form.validate_on_submit():
        logging.error("Remove rule form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    description = form.description.data
    try:
        with DatabaseConnection() as conn:
            success, message = remove_rule(conn, description)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_remove_rule: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

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
    if not form.validate_on_submit():
        logging.error("Add role form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    role_name = form.role_name.data
    percentage = form.percentage.data
    try:
        with DatabaseConnection() as conn:
            success, message = add_role(conn, role_name, percentage)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_add_role: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/edit_role", methods=["POST"])
def admin_edit_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = EditRoleForm(request.form)
    if not form.validate_on_submit():
        logging.error("Edit role form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    old_role_name = form.old_role_name.data
    new_role_name = form.new_role_name.data
    percentage = form.percentage.data
    try:
        with DatabaseConnection() as conn:
            success, message = edit_role(conn, old_role_name, new_role_name, percentage)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_edit_role: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/remove_role", methods=["POST"])
def admin_remove_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
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

@app.route("/admin/update_pot", methods=["POST"])
def admin_update_pot():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = UpdatePotForm(request.form)
    if not form.validate_on_submit():
        logging.error("Update pot form validation failed: %s", form.errors)
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
    if not form.validate_on_submit():
        logging.error("Update prior year sales form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    prior_year_sales = form.prior_year_sales.data
    try:
        with DatabaseConnection() as conn:
            conn.execute(
                "UPDATE incentive_pot SET prior_year_sales = ? WHERE id = 1",
                (prior_year_sales,)
            )
        return jsonify({"success": True, "message": "Prior year sales updated"})
    except Exception as e:
        logging.error(f"Error in update_prior_year_sales: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/set_point_decay", methods=["POST"])
def admin_set_point_decay():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = SetPointDecayForm(request.form)
    if not form.validate_on_submit():
        logging.error("Set point decay form validation failed: %s", form.errors)
        return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
    role_name = form.role_name.data
    points = form.points.data
    days = form.days.data
    try:
        with DatabaseConnection() as conn:
            success, message = set_point_decay(conn, role_name, points, days)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in set_point_decay: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/delete_feedback", methods=["POST"])
def admin_delete_feedback():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = FeedbackForm(request.form)
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
    month = request.args.get("month")
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
    employee_id = request.args.get("employee_id")
    month = request.args.get("month")
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, month, day=None, employee_id=employee_id)]
        if not history:
            fig, ax = plt.subplots()
            ax.text(0.5, 0.5, 'No data available', horizontalalignment='center', verticalalignment='center')
            output = io.BytesIO()
            canvas = FigureCanvas(fig)
            canvas.print_png(output)
            output.seek(0)
            encoded = base64.b64encode(output.read()).decode('utf-8')
            return f"data:image/png;base64,{encoded}"
        df = pd.DataFrame(history)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        fig, ax = plt.subplots()
        ax.plot(df['date'], df['points'].cumsum(), marker='o')
        ax.set_title(f"Score Trend for {history[0]['name']} in {month}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Cumulative Points")
        output = io.BytesIO()
        canvas = FigureCanvas(fig)
        canvas.print_png(output)
        output.seek(0)
        encoded = base64.b64encode(output.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logging.error(f"Error in history_chart: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('history'))

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
        form = FeedbackForm(request.form)
        if not form.validate_on_submit():
            logging.error("Settings form validation failed: %s", form.errors)
            return jsonify({'success': False, 'message': 'Invalid form data: ' + str(form.errors)}), 400
        key = request.form["key"]
        value = request.form["value"]
        try:
            with DatabaseConnection() as conn:
                success, message = set_settings(conn, key, value)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_settings POST: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    try:
        with DatabaseConnection() as conn:
            settings = get_settings(conn)
        logging.debug("Rendering settings.html")
        return render_template("settings.html", settings=settings, is_master=session.get("admin_id") == "master", import_time=int(time.time()))
    except Exception as e:
        logging.error(f"Error in admin_settings GET: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

if __name__ == "__main__":
    logging.debug("Running Flask app in debug mode")
    app.run(host="0.0.0.0", port=6800, debug=True)
else:
    logging.debug("Running Flask app under Gunicorn")