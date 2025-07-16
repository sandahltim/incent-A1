# app.py
# Version: 1.2.15
# Note: Added instantiation of forms in admin route and passed to template.
#       Ensured unique IDs in forms by prefixing.

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file, send_from_directory, flash
from werkzeug.security import check_password_hash, generate_password_hash
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, edit_rule, remove_rule, get_pot_info, update_pot_info, close_voting_session, pause_voting_session, get_voting_results, master_reset_all, get_roles, add_role, edit_role, remove_role, edit_employee, reorder_rules, retire_employee, reactivate_employee, delete_employee, set_point_decay, get_point_decay, deduct_points_daily, get_latest_voting_results, add_feedback, get_unread_feedback_count, get_feedback, mark_feedback_read, get_settings, set_settings
from flask_wtf.csrf import CSRFProtect
from forms import AdminLoginForm, VoteForm, FeedbackForm, AdjustPointsForm, AddEmployeeForm, EditEmployeeForm, RetireEmployeeForm, ReactivateEmployeeForm, DeleteEmployeeForm, AddRuleForm, EditRuleForm, RemoveRuleForm, UpdatePotForm, UpdatePriorYearSalesForm, SetPointDecayForm, UpdateAdminForm, AddRoleForm, EditRoleForm, RemoveRoleForm, MasterResetForm
import logging
import time
import traceback
from datetime import datetime, timedelta, timezone
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
app.secret_key = "your-secret-key-here"
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)  # Extended session lifetime
csrf = CSRFProtect(app)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logging.getLogger('gunicorn.error').setLevel(logging.DEBUG)

# Background thread for point decay
def point_decay_thread():
    last_checked = None
    while True:
        now = datetime.now(timezone.utc)
        today = now.strftime("%A")
        current_date = now.strftime("%Y-%m-%d")
        if last_checked != current_date:
            try:
                with DatabaseConnection() as conn:
                    decay_settings = get_point_decay(conn)
                    for role_name, decay in decay_settings.items():
                        if today in decay["days"]:
                            success, message = deduct_points_daily(conn)
                            logging.debug(message)
            except Exception as e:
                logging.error(f"Point decay error: {str(e)}\n{traceback.format_exc()}")
            last_checked = current_date
        time.sleep(60)

threading.Thread(target=point_decay_thread, daemon=True).start()

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
    if 'admin_id' in session and request.endpoint in ['admin', 'admin_add', 'admin_adjust_points', 'admin_quick_adjust_points', 'admin_retire_employee', 'admin_reactivate_employee', 'admin_delete_employee', 'admin_edit_employee', 'admin_reset', 'admin_master_reset', 'admin_update_admin', 'admin_add_rule', 'admin_edit_rule', 'admin_remove_rule', 'admin_reorder_rules', 'admin_add_role', 'admin_edit_role', 'admin_remove_role', 'admin_update_pot', 'admin_update_prior_year_sales', 'admin_set_point_decay', 'admin_mark_feedback_read', 'admin_settings']:
        if 'last_activity' not in session:
            session.pop('admin_id', None)
            flash("Session expired. Please log in again.", "danger")
            return redirect(url_for('admin'))
        try:
            last_activity = datetime.fromisoformat(session['last_activity']).replace(tzinfo=timezone.utc)
            if (datetime.now(timezone.utc) - last_activity).total_seconds() > app.config['PERMANENT_SESSION_LIFETIME'].total_seconds():
                session.pop('admin_id', None)
                session.pop('last_activity', None)
                flash("Session expired. Please log in again.", "danger")
                return redirect(url_for('admin'))
            session['last_activity'] = datetime.now(timezone.utc).isoformat()
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
        current_month = datetime.now(timezone.utc).strftime("%B %Y")
        vote_form = VoteForm()
        feedback_form = FeedbackForm()
        adjust_form = AdjustPointsForm()
        adjust_form.employee_id.choices = [(emp['employee_id'], f"{emp['name']} ({emp['initials']})") for emp in scoreboard]
        logging.debug(f"Loaded incentive page: voting_active={voting_active}, results_count={len(voting_results)}")
        return render_template("incentive.html", scoreboard=scoreboard, voting_active=voting_active, rules=rules, pot_info=pot_info, roles=roles, is_admin=bool(session.get("admin_id")), import_time=int(time.time()), voting_results=voting_results, current_month=current_month, selected_week=week_number, get_score_class=get_score_class, vote_form=vote_form, feedback_form=feedback_form, adjust_form=adjust_form, unread_feedback=unread_feedback)
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
    form = AdminLoginForm()
    if request.method == "GET":
        return render_template("start_voting.html", form=form, is_master=session.get("admin_id") == "master", import_time=int(time.time()))
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    success, message = start_voting_session(conn, admin["admin_id"])
                    if success:
                        session['admin_id'] = admin["admin_id"]
                        session['last_activity'] = datetime.now(timezone.utc).isoformat()
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
    flash("Invalid form submission", "danger")
    return render_template("start_voting.html", form=form, is_master=session.get("admin_id") == "master", import_time=int(time.time()))

@app.route("/close_voting", methods=["POST"])
def close_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = AdminLoginForm()
    if form.validate_on_submit() and 'password' in request.form:
        password = form.password.data
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE admin_id = ?", (session["admin_id"],)).fetchone()
                if not admin or not check_password_hash(admin["password"], password):
                    flash("Invalid password", "danger")
                    return redirect(url_for('admin'))
                success, message = close_voting_session(conn, session["admin_id"])
                if success:
                    flash(message, "success")
                    return redirect(url_for('show_incentive'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in close_voting: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Password is required", "danger")
    return redirect(url_for('admin'))

@app.route("/pause_voting", methods=["POST"])
def pause_voting():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    try:
        with DatabaseConnection() as conn:
            success, message = pause_voting_session(conn, session["admin_id"])
            if success:
                flash(message, "success")
                return redirect(url_for('show_incentive'))
            flash(message, "danger")
        return redirect(url_for('admin'))
    except Exception as e:
        logging.error(f"Error in pause_voting: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/vote", methods=["POST"])
def vote():
    form = VoteForm()
    if form.validate_on_submit():
        try:
            voter_initials = form.initials.data
            votes = {key.split("_")[1]: int(value) for key, value in request.form.items() if key.startswith("vote_")}
            logging.debug(f"Vote attempt: initials={voter_initials}, votes={votes}, form_data={request.form}")
            with DatabaseConnection() as conn:
                success, message = cast_votes(conn, voter_initials, votes)
                if success:
                    flash(message, "success")
                    return redirect(url_for('show_incentive'))
                flash(message, "danger")
            return redirect(url_for('show_incentive'))
        except Exception as e:
            logging.error(f"Error in vote: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('show_incentive'))
    flash(f"Invalid form submission: {form.errors}", "danger")
    return redirect(url_for('show_incentive'))

@app.route("/check_vote", methods=["POST"])
def check_vote():
    try:
        initials = request.form.get("initials")
        if initials is None or initials.strip() == '':
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
    if request.method == "POST" and "username" in request.form:
        if form.validate_on_submit():
            username = form.username.data
            password = form.password.data
            try:
                with DatabaseConnection() as conn:
                    admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                    if admin and check_password_hash(admin["password"], password):
                        session["admin_id"] = admin["admin_id"]
                        session['last_activity'] = datetime.now(timezone.utc).isoformat()
                        flash("Logged in successfully", "success")
                        return redirect(url_for("admin"))
                flash("Invalid credentials", "danger")
            except Exception as e:
                logging.error(f"Error in admin login: {str(e)}\n{traceback.format_exc()}")
                flash("Server error", "danger")
            return render_template("admin_login.html", form=form, import_time=int(time.time()))
        flash("Invalid form submission", "danger")
        return render_template("admin_login.html", form=form, import_time=int(time.time()))
    if "admin_id" not in session:
        return render_template("admin_login.html", form=form, import_time=int(time.time()))
    try:
        with DatabaseConnection() as conn:
            employees = conn.execute("SELECT employee_id, name, initials, score, role, active FROM employees").fetchall()
            rules = get_rules(conn)
            pot_info = get_pot_info(conn)
            roles = get_roles(conn)
            decay = get_point_decay(conn)
            admins = conn.execute("SELECT admin_id, username FROM admins").fetchall() if session.get("admin_id") == "master" else []
            unread_feedback = get_unread_feedback_count(conn)
            feedback = get_feedback(conn) if session.get("admin_id") == "master" else []
            voting_results = []
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
        # Instantiate forms with dynamic choices
        adjust_form = AdjustPointsForm()
        adjust_form.employee_id.choices = [(emp['employee_id'], f"{emp['name']} ({emp['initials']})") for emp in employees]
        add_employee_form = AddEmployeeForm()
        add_employee_form.role.choices = [(role['role_name'], role['role_name']) for role in roles]
        edit_employee_form = EditEmployeeForm()
        edit_employee_form.employee_id.choices = [(emp['employee_id'], f"{emp['name']} ({emp['initials']})") for emp in employees]
        edit_employee_form.role.choices = [(role['role_name'], role['role_name']) for role in roles]
        retire_form = RetireEmployeeForm()
        retire_form.employee_id.choices = [(emp['employee_id'], f"{emp['name']} ({emp['initials']})") for emp in employees]
        reactivate_form = ReactivateEmployeeForm()
        reactivate_form.employee_id.choices = [(emp['employee_id'], f"{emp['name']} ({emp['initials']})") for emp in employees]
        delete_form = DeleteEmployeeForm()
        delete_form.employee_id.choices = [(emp['employee_id'], f"{emp['name']} ({emp['initials']})") for emp in employees]
        add_rule_form = AddRuleForm()
        edit_rule_form = EditRuleForm()
        remove_rule_form = RemoveRuleForm()
        update_pot_form = UpdatePotForm()
        update_prior_year_sales_form = UpdatePriorYearSalesForm()
        set_point_decay_form = SetPointDecayForm()
        set_point_decay_form.role_name.choices = [(role['role_name'], role['role_name']) for role in roles]
        update_admin_form = UpdateAdminForm()
        update_admin_form.old_username.choices = [(admin['username'], admin['username'] + f" ({admin['admin_id']})") for admin in admins]
        add_role_form = AddRoleForm()
        edit_role_form = EditRoleForm()
        remove_role_form = RemoveRoleForm()
        master_reset_form = MasterResetForm()
        logging.debug(f"Loaded admin page: employees_count={len(employees)}, roles_count={len(roles)}, voting_results_count={len(voting_results)}")
        return render_template("admin_manage.html", employees=employees, rules=rules, pot_info=pot_info, roles=roles, decay=decay, admins=admins, voting_results=voting_results, is_admin=True, is_master=session.get("admin_id") == "master", import_time=int(time.time()), unread_feedback=unread_feedback, feedback=feedback, adjust_form=adjust_form, add_employee_form=add_employee_form, edit_employee_form=edit_employee_form, retire_form=retire_form, reactivate_form=reactivate_form, delete_form=delete_form, add_rule_form=add_rule_form, edit_rule_form=edit_rule_form, remove_rule_form=remove_rule_form, update_pot_form=update_pot_form, update_prior_year_sales_form=update_prior_year_sales_form, set_point_decay_form=set_point_decay_form, update_admin_form=update_admin_form, add_role_form=add_role_form, edit_role_form=edit_role_form, remove_role_form=remove_role_form, master_reset_form=master_reset_form)
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
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = AddEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = add_employee(conn, form.name.data, form.initials.data, form.role.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_add: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/adjust_points", methods=["POST"])
def admin_adjust_points():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = AdjustPointsForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = adjust_points(conn, form.employee_id.data, form.points.data, session["admin_id"], form.reason.data, form.notes.data or "")
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_adjust_points: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/quick_adjust_points", methods=["POST"])
def admin_quick_adjust_points():
    form = AdminLoginForm()
    if form.validate_on_submit() and 'employee_id' in request.form and 'points' in request.form and 'reason' in request.form:
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (form.username.data,)).fetchone()
                if not admin or not check_password_hash(admin["password"], form.password.data):
                    flash("Invalid admin credentials", "danger")
                    return redirect(url_for('show_incentive'))
                success, message = adjust_points(conn, request.form['employee_id'], int(request.form['points']), admin["admin_id"], request.form['reason'], request.form.get('notes', ""))
                if success:
                    flash(message, "success")
                    return redirect(url_for('show_incentive'))
                flash(message, "danger")
            return redirect(url_for('show_incentive'))
        except ValueError:
            flash("Points must be a valid integer", "danger")
            return redirect(url_for('show_incentive'))
        except Exception as e:
            logging.error(f"Error in quick_adjust_points: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('show_incentive'))
    flash("Invalid form submission or missing fields", "danger")
    return redirect(url_for('show_incentive'))

@app.route("/admin/retire_employee", methods=["POST"])
def admin_retire_employee():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = RetireEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = retire_employee(conn, form.employee_id.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_retire_employee: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission", "danger")
    return redirect(url_for('admin'))

@app.route("/admin/reactivate_employee", methods=["POST"])
def admin_reactivate_employee():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = ReactivateEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = reactivate_employee(conn, form.employee_id.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_reactivate_employee: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission", "danger")
    return redirect(url_for('admin'))

@app.route("/admin/delete_employee", methods=["POST"])
def admin_delete_employee():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = DeleteEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = delete_employee(conn, form.employee_id.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_delete_employee: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission", "danger")
    return redirect(url_for('admin'))

@app.route("/admin/edit_employee", methods=["POST"])
def admin_edit_employee():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = EditEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = edit_employee(conn, form.employee_id.data, form.name.data, form.role.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_edit_employee: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/reset", methods=["POST"])
def admin_reset():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    try:
        with DatabaseConnection() as conn:
            success, message = reset_scores(conn, session["admin_id"], reason="Admin reset to 50")
            if success:
                flash(message, "success")
                return redirect(url_for('show_incentive'))
            flash(message, "danger")
        return redirect(url_for('admin'))
    except Exception as e:
        logging.error(f"Error in admin_reset: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/admin/master_reset", methods=["POST"])
def admin_master_reset():
    if session.get("admin_id") != "master":
        flash("Master account required", "danger")
        return redirect(url_for('admin'))
    form = MasterResetForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE admin_id = 'master'").fetchone()
                if not admin or not check_password_hash(admin["password"], form.password.data):
                    flash("Invalid master password", "danger")
                    return redirect(url_for('admin'))
                success, message = master_reset_all(conn)
                if success:
                    flash(message, "success")
                    return redirect(url_for('show_incentive'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_master_reset: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission", "danger")
    return redirect(url_for('admin'))

@app.route("/admin/update_admin", methods=["POST"])
def admin_update_admin():
    if session.get("admin_id") != "master":
        flash("Master account required", "danger")
        return redirect(url_for('admin'))
    form = UpdateAdminForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (form.old_username.data,)).fetchone()
                if not admin:
                    flash("Admin not found", "danger")
                    return redirect(url_for('admin'))
                conn.execute(
                    "UPDATE admins SET username = ?, password = ? WHERE username = ?",
                    (form.new_username.data, generate_password_hash(form.new_password.data), form.old_username.data)
                )
                flash(f"Admin '{form.old_username.data}' updated to '{form.new_username.data}'", "success")
                return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_update_admin: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/add_rule", methods=["POST"])
def admin_add_rule():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = AddRuleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                existing_rule = conn.execute("SELECT 1 FROM incentive_rules WHERE description = ?", (form.description.data,)).fetchone()
                if existing_rule:
                    flash("Rule already exists", "danger")
                    return redirect(url_for('admin'))
                success, message = add_rule(conn, form.description.data, form.points.data, form.details.data or "")
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_add_rule: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/edit_rule", methods=["POST"])
def admin_edit_rule():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = EditRuleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = edit_rule(conn, form.old_description.data, form.new_description.data, form.points.data, form.details.data or "")
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_edit_rule: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/remove_rule", methods=["POST"])
def admin_remove_rule():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = RemoveRuleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = remove_rule(conn, form.description.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_remove_rule: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission", "danger")
    return redirect(url_for('admin'))

@app.route("/admin/reorder_rules", methods=["POST"])
def admin_reorder_rules():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    order = request.form.getlist("order[]")
    try:
        with DatabaseConnection() as conn:
            success, message = reorder_rules(conn, order)
            if success:
                flash(message, "success")
                return redirect(url_for('admin'))
            flash(message, "danger")
        return redirect(url_for('admin'))
    except Exception as e:
        logging.error(f"Error in admin_reorder_rules: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/admin/add_role", methods=["POST"])
def admin_add_role():
    if session.get("admin_id") != "master":
        flash("Master account required", "danger")
        return redirect(url_for('admin'))
    form = AddRoleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = add_role(conn, form.role_name.data, form.percentage.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_add_role: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/edit_role", methods=["POST"])
def admin_edit_role():
    if session.get("admin_id") != "master":
        flash("Master account required", "danger")
        return redirect(url_for('admin'))
    form = EditRoleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = edit_role(conn, form.old_role_name.data, form.new_role_name.data, form.percentage.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_edit_role: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/remove_role", methods=["POST"])
def admin_remove_role():
    if session.get("admin_id") != "master":
        flash("Master account required", "danger")
        return redirect(url_for('admin'))
    form = RemoveRoleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = remove_role(conn, form.role_name.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_remove_role: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission", "danger")
    return redirect(url_for('admin'))

@app.route("/admin/update_pot", methods=["POST"])
def admin_update_pot():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = UpdatePotForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                conn.execute(
                    "UPDATE incentive_pot SET sales_dollars = ?, bonus_percent = ? WHERE id = 1",
                    (form.sales_dollars.data, form.bonus_percent.data)
                )
                success = True
                message = "Pot sales and bonus updated (role percentages managed via Edit Roles)"
                flash(message, "success")
                return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in admin_update_pot: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/update_prior_year_sales", methods=["POST"])
def admin_update_prior_year_sales():
    if session.get("admin_id") != "master":
        flash("Master account required", "danger")
        return redirect(url_for('admin'))
    form = UpdatePriorYearSalesForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                conn.execute(
                    "UPDATE incentive_pot SET prior_year_sales = ? WHERE id = 1",
                    (form.prior_year_sales.data,)
                )
                flash("Prior year sales updated", "success")
                return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in update_prior_year_sales: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/admin/set_point_decay", methods=["POST"])
def admin_set_point_decay():
    if session.get("admin_id") != "master":
        flash("Master account required", "danger")
        return redirect(url_for('admin'))
    form = SetPointDecayForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = set_point_decay(conn, form.role_name.data, form.points.data, form.days.data)
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in set_point_decay: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission: " + ", ".join([f"{field}: {error[0]}" for field, error in form.errors.items()]), "danger")
    return redirect(url_for('admin'))

@app.route("/voting_results_popup", methods=["GET"])
def voting_results_popup():
    if session.get("admin_id") != "master":
        flash("Master account required", "danger")
        return redirect(url_for('admin'))
    try:
        with DatabaseConnection() as conn:
            results = get_latest_voting_results(conn)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        logging.error(f"Error in voting_results_popup: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

@app.route("/history", methods=["GET"])
def history():
    month_year = request.args.get("month_year")
    day = request.args.get("day")
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, month_year, day)]
            months = conn.execute("SELECT DISTINCT month_year FROM score_history ORDER BY month_year DESC").fetchall()
            if month_year:
                days = conn.execute("SELECT DISTINCT substr(date, 1, 10) as day FROM score_history WHERE month_year = ? ORDER BY day DESC", (month_year,)).fetchall()
            else:
                days = []
        return render_template("history.html", history=history, months=[m["month_year"] for m in months], days=[d["day"] for d in days], is_admin=bool(session.get("admin_id")), import_time=int(time.time()), selected_month=month_year, selected_day=day)
    except Exception as e:
        logging.error(f"Error in history: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('show_incentive'))

@app.route("/admin/export_payout", methods=["GET"])
def export_payout():
    if "admin_id" not in session:
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    month = request.args.get("month")
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, month)]
            if not history:
                flash("No data for selected month", "danger")
                return redirect(url_for('admin'))
            df = pd.DataFrame(history)
            grouped = df.groupby('name')
            output_lines = []
            for name, group in grouped:
                output_lines.append(f"Employee: {name}")
                columns = ['changed_by', 'points', 'reason', 'date']
                if 'notes' in group.columns:
                    columns.insert(3, 'notes')
                output_lines.append(group[columns].to_csv(index=False))
                total_points = group['points'].sum()
                output_lines.append(f"Total Payout for {name}: {total_points}")
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
        flash("Admin login required", "danger")
        return redirect(url_for('admin'))
    form = FeedbackForm()  # Using FeedbackForm for basic validation
    if form.validate_on_submit() and 'feedback_id' in request.form:
        try:
            with DatabaseConnection() as conn:
                success, message = mark_feedback_read(conn, request.form['feedback_id'])
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin'))
                flash(message, "danger")
            return redirect(url_for('admin'))
        except Exception as e:
            logging.error(f"Error in mark_feedback_read: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin'))
    flash("Invalid form submission or missing feedback ID", "danger")
    return redirect(url_for('admin'))

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = add_feedback(conn, form.comment.data, form.initials.data if "admin_id" not in session else session["admin_id"])
                if success:
                    flash(message, "success")
                    return redirect(url_for('show_incentive'))
                flash(message, "danger")
            return redirect(url_for('show_incentive'))
        except Exception as e:
            logging.error(f"Error in submit_feedback: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('show_incentive'))
    flash(f"Invalid form submission: {form.errors}", "danger")
    return redirect(url_for('show_incentive'))

@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if "admin_id" not in session or session.get("admin_id") != "master":
        flash("Master admin required", "danger")
        return redirect(url_for('admin'))
    if request.method == "POST":
        try:
            with DatabaseConnection() as conn:
                success, message = set_settings(conn, request.form['key'], request.form['value'])
                if success:
                    flash(message, "success")
                    return redirect(url_for('admin_settings'))
                flash(message, "danger")
            return redirect(url_for('admin_settings'))
        except Exception as e:
            logging.error(f"Error in admin_settings POST: {str(e)}\n{traceback.format_exc()}")
            flash("Server error", "danger")
            return redirect(url_for('admin_settings'))
    try:
        with DatabaseConnection() as conn:
            settings = get_settings(conn)
        return render_template("settings.html", settings=settings)
    except Exception as e:
        logging.error(f"Error in admin_settings GET: {str(e)}\n{traceback.format_exc()}")
        flash("Server error", "danger")
        return redirect(url_for('admin'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6800, debug=True)