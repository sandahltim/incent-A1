# app.py
# Version: 2.0.0
# Description: Main Flask application for A1 Rent-It Incentive Program with CSRF protection.

from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from incentive_service import (
    DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes,
    add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, edit_rule,
    remove_rule, get_pot_info, update_pot_info, close_voting_session, pause_voting_session,
    get_voting_results, master_reset_all, get_roles, add_role, edit_role, remove_role,
    edit_employee, retire_employee, reactivate_employee, delete_employee, set_point_decay,
    get_point_decay, deduct_points_daily, get_latest_voting_results
)
from forms import (
    AdminLoginForm, StartVotingForm, VoteForm, AddEmployeeForm, AdjustPointsForm, AddRuleForm,
    EditRuleForm, RemoveRuleForm, EditEmployeeForm, RetireEmployeeForm, ReactivateEmployeeForm,
    DeleteEmployeeForm, UpdatePotForm, UpdatePriorYearSalesForm, SetPointDecayForm,
    UpdateAdminForm, AddRoleForm, EditRoleForm, RemoveRoleForm, MasterResetForm
)
import logging
import time
import traceback
from datetime import datetime
import sqlite3
import threading
from flask_wtf.csrf import CSRFProtect

# Initialize Flask app and CSRF protection
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "your-secret-key-here"  # TODO: Replace with secure key
csrf = CSRFProtect(app)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')
logging.getLogger('gunicorn.error').setLevel(logging.DEBUG)

# Background thread for point decay
def point_decay_thread():
    last_checked = None
    while True:
        now = datetime.now()
        today = now.strftime("%A")
        current_date = now.strftime("%Y-%m-%d")

        # Check once per day
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

        time.sleep(60)  # Check every minute

# Start the thread
threading.Thread(target=point_decay_thread, daemon=True).start()

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
        current_month = datetime.now().strftime("%B %Y")
        vote_form = VoteForm()
        logging.debug(f"Loaded incentive page: voting_active={voting_active}, results_count={len(voting_results)}")
        return render_template("incentive.html", scoreboard=scoreboard, voting_active=voting_active,
                               rules=rules, pot_info=pot_info, roles=roles,
                               is_admin=bool(session.get("admin_id")), import_time=int(time.time()),
                               voting_results=voting_results, current_month=current_month,
                               selected_week=week_number, vote_form=vote_form)
    except Exception as e:
        logging.error(f"Error in show_incentive: {str(e)}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

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
        return "Internal Server Error", 500

@app.route("/start_voting", methods=["GET", "POST"])
def start_voting():
    form = StartVotingForm()
    if request.method == "GET":
        if "admin_id" not in session:
            return render_template("start_voting.html", form=form, is_master=session.get("admin_id") == "master",
                                   import_time=int(time.time()))
        return render_template("start_voting.html", form=form, is_master=session.get("admin_id") == "master",
                               import_time=int(time.time()))
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if not admin or not check_password_hash(admin["password"], password):
                    return jsonify({"success": False, "message": "Invalid admin credentials"}), 403
                success, message = start_voting_session(conn, admin["admin_id"])
            logging.debug(f"Start voting: success={success}, message={message}")
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in start_voting: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/close_voting", methods=["POST"])
def close_voting():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = StartVotingForm()  # Reusing for password validation
    if form.validate_on_submit():
        password = form.password.data
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE admin_id = ?", (session["admin_id"],)).fetchone()
                if not admin or not check_password_hash(admin["password"], password):
                    return jsonify({"success": False, "message": "Invalid password"}), 403
                success, message = close_voting_session(conn, session["admin_id"])
            logging.debug(f"Close voting: success={success}, message={message}")
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in close_voting: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/pause_voting", methods=["POST"])
def pause_voting():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    try:
        with DatabaseConnection() as conn:
            success, message = pause_voting_session(conn, session["admin_id"])
        logging.debug(f"Pause voting: success={success}, message={message}")
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in pause_voting: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/vote", methods=["POST"])
def vote():
    form = VoteForm()
    if form.validate_on_submit():
        try:
            voter_initials = form.initials.data
            votes = {key.split("_")[1]: int(value) for key, value in request.form.items() if key.startswith("vote_")}
            with DatabaseConnection() as conn:
                success, message = cast_votes(conn, voter_initials, votes)
            logging.debug(f"Vote cast: initials={voter_initials}, votes={votes}, success={success}, message={message}")
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in vote: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/check_vote", methods=["POST"])
def check_vote():
    form = VoteForm()
    if form.validate_on_submit():
        try:
            initials = form.initials.data
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
    return jsonify({"can_vote": False, "message": "Form validation failed"}), 400

@app.route("/admin", methods=["GET", "POST"])
def admin():
    form = AdminLoginForm()
    if request.method == "POST" and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    session["admin_id"] = admin["admin_id"]
                    return redirect(url_for("admin"))
            return render_template("admin_login.html", form=form, error="Invalid credentials",
                                   import_time=int(time.time()))
        except Exception as e:
            logging.error(f"Error in admin login: {str(e)}\n{traceback.format_exc()}")
            return "Internal Server Error", 500
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
            voting_results = []
            if session.get("admin_id") == "master":
                results = conn.execute("""
                    SELECT vs.session_id, v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, vr.points
                    FROM votes v
                    JOIN employees e ON v.recipient_id = e.employee_id
                    JOIN voting_sessions vs ON v.vote_date >= vs.start_time AND (v.vote_date <= vs.end_time OR vs.end_time IS NULL)
                    LEFT JOIN voting_results vr ON v.recipient_id = vr.employee_id AND vr.session_id = vs.session_id
                    ORDER BY vs.session_id DESC, v.vote_date DESC
                """).fetchall()
                voting_results = [dict(row) for row in results]
            # Initialize forms with dynamic choices
            add_employee_form = AddEmployeeForm()
            adjust_points_form = AdjustPointsForm()
            edit_employee_form = EditEmployeeForm()
            retire_employee_form = RetireEmployeeForm()
            reactivate_employee_form = ReactivateEmployeeForm()
            delete_employee_form = DeleteEmployeeForm()
            set_point_decay_form = SetPointDecayForm()
            update_admin_form = UpdateAdminForm()
            employee_choices = [(emp["employee_id"], f"{emp['employee_id']} - {emp['name']} ({emp['initials']}) {'(Retired)' if emp['active'] == 0 else ''}") for emp in employees]
            role_choices = [(role["role_name"].lower(), role["role_name"]) for role in roles]
            admin_choices = [(admin["username"], admin["username"]) for admin in admins]
            add_employee_form.role.choices = role_choices
            adjust_points_form.employee_id.choices = employee_choices
            edit_employee_form.employee_id.choices = employee_choices
            edit_employee_form.role.choices = role_choices
            retire_employee_form.employee_id.choices = employee_choices
            reactivate_employee_form.employee_id.choices = employee_choices
            delete_employee_form.employee_id.choices = employee_choices
            set_point_decay_form.role_name.choices = role_choices
            update_admin_form.old_username.choices = admin_choices
            add_rule_form = AddRuleForm()
            edit_rule_form = EditRuleForm()
            remove_rule_form = RemoveRuleForm()
            update_pot_form = UpdatePotForm()
            update_prior_year_sales_form = UpdatePriorYearSalesForm()
            add_role_form = AddRoleForm()
            edit_role_form = EditRoleForm()
            remove_role_form = RemoveRoleForm()
            master_reset_form = MasterResetForm()
        logging.debug(f"Loaded admin page: employees_count={len(employees)}, roles_count={len(roles)}, voting_results_count={len(voting_results)}")
        return render_template("admin_manage.html", employees=employees, rules=rules, pot_info=pot_info,
                               roles=roles, decay=decay, admins=admins, voting_results=voting_results,
                               is_admin=True, is_master=session.get("admin_id") == "master",
                               import_time=int(time.time()),
                               add_employee_form=add_employee_form, adjust_points_form=adjust_points_form,
                               add_rule_form=add_rule_form, edit_rule_form=edit_rule_form,
                               remove_rule_form=remove_rule_form, edit_employee_form=edit_employee_form,
                               retire_employee_form=retire_employee_form, reactivate_employee_form=reactivate_employee_form,
                               delete_employee_form=delete_employee_form, update_pot_form=update_pot_form,
                               update_prior_year_sales_form=update_prior_year_sales_form,
                               set_point_decay_form=set_point_decay_form, update_admin_form=update_admin_form,
                               add_role_form=add_role_form, edit_role_form=edit_role_form,
                               remove_role_form=remove_role_form, master_reset_form=master_reset_form)
    except Exception as e:
        logging.error(f"Error in admin: {str(e)}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    form = AdminLoginForm()  # CSRF validation
    if form.validate_on_submit():
        session.pop("admin_id", None)
        return redirect(url_for("show_incentive"))
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/add", methods=["POST"])
def admin_add():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = AddEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = add_employee(conn, form.name.data, form.initials.data, form.role.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_add: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/adjust_points", methods=["POST"])
def admin_adjust_points():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = AdjustPointsForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = adjust_points(conn, form.employee_id.data, form.points.data,
                                                session["admin_id"], form.reason.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_adjust_points: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/quick_adjust_points", methods=["POST"])
def admin_quick_adjust_points():
    form = AdjustPointsForm()
    if form.validate_on_submit():
        username = request.form.get("username")
        password = request.form.get("password")
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if not admin or not check_password_hash(admin["password"], password):
                    return jsonify({"success": False, "message": "Invalid admin credentials"}), 403
                success, message = adjust_points(conn, form.employee_id.data, form.points.data,
                                                admin["admin_id"], form.reason.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in quick_adjust_points: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/retire_employee", methods=["POST"])
def admin_retire_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = RetireEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = retire_employee(conn, form.employee_id.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_retire_employee: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/reactivate_employee", methods=["POST"])
def admin_reactivate_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = ReactivateEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = reactivate_employee(conn, form.employee_id.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_reactivate_employee: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/delete_employee", methods=["POST"])
def admin_delete_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = DeleteEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = delete_employee(conn, form.employee_id.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_delete_employee: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/edit_employee", methods=["POST"])
def admin_edit_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = EditEmployeeForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = edit_employee(conn, form.employee_id.data, form.name.data, form.role.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_edit_employee: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

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
    form = MasterResetForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE admin_id = 'master'").fetchone()
                if not admin or not check_password_hash(admin["password"], form.password.data):
                    return jsonify({"success": False, "message": "Invalid master password"}), 403
                success, message = master_reset_all(conn)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_master_reset: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/update_admin", methods=["POST"])
def admin_update_admin():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = UpdateAdminForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (form.old_username.data,)).fetchone()
                if not admin:
                    return jsonify({"success": False, "message": "Admin not found"}), 404
                conn.execute(
                    "UPDATE admins SET username = ?, password = ? WHERE username = ?",
                    (form.new_username.data, generate_password_hash(form.new_password.data), form.old_username.data)
                )
            return jsonify({"success": True, "message": f"Admin '{form.old_username.data}' updated to '{form.new_username.data}'"})
        except Exception as e:
            logging.error(f"Error in admin_update_admin: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/add_rule", methods=["POST"])
def admin_add_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = AddRuleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = add_rule(conn, form.description.data, form.points.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_add_rule: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/edit_rule", methods=["POST"])
def admin_edit_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = EditRuleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = edit_rule(conn, form.old_description.data, form.new_description.data, form.points.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_edit_rule: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/remove_rule", methods=["POST"])
def admin_remove_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = RemoveRuleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = remove_rule(conn, form.description.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_remove_rule: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/reorder_rules", methods=["POST"])
def admin_reorder_rules():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    form = RemoveRuleForm()  # CSRF validation for list submission
    if form.validate_on_submit():
        order = request.form.getlist("order[]")
        try:
            with DatabaseConnection() as conn:
                success, message = reorder_rules(conn, order)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_reorder_rules: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/add_role", methods=["POST"])
def admin_add_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = AddRoleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = add_role(conn, form.role_name.data, form.percentage.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_add_role: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/edit_role", methods=["POST"])
def admin_edit_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = EditRoleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = edit_role(conn, form.old_role_name.data, form.new_role_name.data, form.percentage.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_edit_role: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/remove_role", methods=["POST"])
def admin_remove_role():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = RemoveRoleForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = remove_role(conn, form.role_name.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_remove_role: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/update_pot", methods=["POST"])
def admin_update_pot():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
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
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_update_pot: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/update_prior_year_sales", methods=["POST"])
def admin_update_prior_year_sales():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = UpdatePriorYearSalesForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                conn.execute(
                    "UPDATE incentive_pot SET prior_year_sales = ? WHERE id = 1",
                    (form.prior_year_sales.data,)
                )
            return jsonify({"success": True, "message": "Prior year sales updated"})
        except Exception as e:
            logging.error(f"Error in update_prior_year_sales: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

@app.route("/admin/set_point_decay", methods=["POST"])
def admin_set_point_decay():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    form = SetPointDecayForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = set_point_decay(conn, form.role_name.data, form.points.data, form.days.data)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in set_point_decay: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Form validation failed"}), 400

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
    form = AdminLoginForm()  # CSRF for potential future POST actions
    month_year = request.args.get("month_year")
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, month_year)]
            months = conn.execute("SELECT DISTINCT month_year FROM score_history ORDER BY month_year DESC").fetchall()
        return render_template("history.html", history=history, months=[m["month_year"] for m in months],
                               is_admin=bool(session.get("admin_id")), import_time=int(time.time()), form=form)
    except Exception as e:
        logging.error(f"Error in history: {str(e)}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6800, debug=True)