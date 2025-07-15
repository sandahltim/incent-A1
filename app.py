# app.py
# Version: 1.2.3
# Note: Fixed history_chart to return placeholder image if no data. Fixed export_payout to handle if 'notes' not in df, use group[['changed_by', 'points', 'reason', 'date']].to_csv() if no notes. Added program_end_date to settings, but no logic yet. Passed form to start_voting GET. No removals.

from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
from werkzeug.security import check_password_hash, generate_password_hash
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, edit_rule, remove_rule, get_pot_info, update_pot_info, close_voting_session, pause_voting_session, get_voting_results, master_reset_all, get_roles, add_role, edit_role, remove_role, edit_employee, reorder_rules, retire_employee, reactivate_employee, delete_employee, set_point_decay, get_point_decay, deduct_points_daily, get_latest_voting_results, add_feedback, get_unread_feedback_count, get_feedback, mark_feedback_read, get_settings, set_settings
import logging
import time
import traceback
from datetime import datetime
import sqlite3
import threading
from flask_wtf.csrf import CSRFProtect
from forms import VoteForm, FeedbackForm, AdminLoginForm, AdjustPointsForm
import io
import pandas as pd
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
import base64

app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = "your-secret-key-here"
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

# Start the thread when the app starts
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
        current_month = datetime.now().strftime("%B %Y")
        vote_form = VoteForm()
        feedback_form = FeedbackForm()
        logging.debug(f"Loaded incentive page: voting_active={voting_active}, results_count={len(voting_results)}")
        return render_template("incentive.html", scoreboard=scoreboard, voting_active=voting_active, rules=rules, pot_info=pot_info, roles=roles, is_admin=bool(session.get("admin_id")), import_time=int(time.time()), voting_results=voting_results, current_month=current_month, selected_week=week_number, get_score_class=get_score_class, vote_form=vote_form, feedback_form=feedback_form, unread_feedback=unread_feedback)
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
    form = AdminLoginForm()
    if request.method == "GET":
        return render_template("start_voting.html", form=form, is_master=session.get("admin_id") == "master", import_time=int(time.time()))
    username = request.form.get("username")
    password = request.form.get("password")
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

@app.route("/close_voting", methods=["POST"])
def close_voting():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    password = request.form.get("password")
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
    try:
        voter_initials = request.form.get("initials")
        if voter_initials is None or voter_initials.strip() == '':
            return jsonify({"success": False, "message": "Voter initials required and cannot be empty"}), 400
        votes = {key.split("_")[1]: int(value) for key, value in request.form.items() if key.startswith("vote_")}
        with DatabaseConnection() as conn:
            success, message = cast_votes(conn, voter_initials, votes)
        logging.debug(f"Vote cast: initials={voter_initials}, votes={votes}, success={success}, message={message}")
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in vote: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

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
        username = request.form["username"]
        password = request.form["password"]
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    session["admin_id"] = admin["admin_id"]
                    return redirect(url_for("admin"))
            return render_template("admin_login.html", error="Invalid credentials", import_time=int(time.time()), form=form)
        except Exception as e:
            logging.error(f"Error in admin login: {str(e)}\n{traceback.format_exc()}")
            return "Internal Server Error", 500
    if "admin_id" not in session:
        return render_template("admin_login.html", import_time=int(time.time()), form=form)
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
                    SELECT vs.session_id, v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, vr.points
                    FROM votes v
                    JOIN employees e ON v.recipient_id = e.employee_id
                    JOIN voting_sessions vs ON v.vote_date >= vs.start_time AND (v.vote_date <= vs.end_time OR vs.end_time IS NULL)
                    LEFT JOIN voting_results vr ON v.recipient_id = vr.employee_id AND vr.session_id = vs.session_id
                    ORDER BY vs.session_id DESC, v.vote_date DESC
                """).fetchall()
                voting_results = [dict(row) for row in results]
        logging.debug(f"Loaded admin page: employees_count={len(employees)}, roles_count={len(roles)}, voting_results_count={len(voting_results)}")
        return render_template("admin_manage.html", employees=employees, rules=rules, pot_info=pot_info, roles=roles, decay=decay, admins=admins, voting_results=voting_results, is_admin=True, is_master=session.get("admin_id") == "master", import_time=int(time.time()), unread_feedback=unread_feedback, feedback=feedback)
    except Exception as e:
        logging.error(f"Error in admin: {str(e)}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    session.pop("admin_id", None)
    return redirect(url_for("show_incentive"))

@app.route("/admin/add", methods=["POST"])
def admin_add():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    name = request.form["name"]
    initials = request.form["initials"]
    role = request.form["role"]
    try:
        with DatabaseConnection() as conn:
            success, message = add_employee(conn, name, initials, role)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_add: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/adjust_points", methods=["POST"])
def admin_adjust_points():
    logging.debug(f"Adjust points attempt: session={session.get('admin_id')}, form={request.form}")
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    employee_id = request.form["employee_id"]
    points = int(request.form["points"])
    reason = request.form["reason"]
    notes = request.form.get("notes", "")
    try:
        with DatabaseConnection() as conn:
            success, message = adjust_points(conn, employee_id, points, session["admin_id"], reason, notes)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_adjust_points: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/quick_adjust_points", methods=["POST"])
def admin_quick_adjust_points():
    logging.debug(f"Quick adjust points attempt: form={request.form}")
    username = request.form.get("username")
    password = request.form.get("password")
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
        logging.error(f"Error in quick_adjust_points: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/retire_employee", methods=["POST"])
def admin_retire_employee():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    employee_id = request.form["employee_id"]
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
    employee_id = request.form["employee_id"]
    try:
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
    employee_id = request.form["employee_id"]
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
    employee_id = request.form["employee_id"]
    name = request.form["name"]
    role = request.form["role"]
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
    password = request.form.get("password")
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
    old_username = request.form["old_username"]
    new_username = request.form["new_username"]
    new_password = request.form["new_password"]
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
    description = request.form["description"]
    points = int(request.form["points"])
    details = request.form.get("details", "")
    try:
        with DatabaseConnection() as conn:
            success, message = add_rule(conn, description, points, details)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_add_rule: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/admin/edit_rule", methods=["POST"])
def admin_edit_rule():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    old_description = request.form["old_description"]
    new_description = request.form["new_description"]
    points = int(request.form["points"])
    details = request.form.get("details", "")
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
    description = request.form["description"]
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
    role_name = request.form["role_name"]
    percentage = float(request.form["percentage"])
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
    old_role_name = request.form["old_role_name"]
    new_role_name = request.form["new_role_name"]
    percentage = float(request.form["percentage"])
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
    role_name = request.form["role_name"]
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
    try:
        sales_dollars = float(request.form["sales_dollars"])
        bonus_percent = float(request.form["bonus_percent"])
        logging.debug(f"Received pot update: sales_dollars={sales_dollars}, bonus_percent={bonus_percent}")
        with DatabaseConnection() as conn:
            conn.execute(
                "UPDATE incentive_pot SET sales_dollars = ?, bonus_percent = ? WHERE id = 1",
                (sales_dollars, bonus_percent)
            )
            success = True
            message = "Pot sales and bonus updated (role percentages managed via Edit Roles)"
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in admin_update_pot: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500
    
@app.route("/admin/update_prior_year_sales", methods=["POST"])
def admin_update_prior_year_sales():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    try:
        prior_year_sales = float(request.form["prior_year_sales"])
        logging.debug(f"Received prior year sales update: prior_year_sales={prior_year_sales}")
        with DatabaseConnection() as conn:
            conn.execute(
                "UPDATE incentive_pot SET prior_year_sales = ? WHERE id = 1",
                (prior_year_sales,)
            )
        return jsonify({"success": True, "message": "Prior year sales updated"})
    except Exception as e:
        logging.error(f"Error in update_prior_year_sales: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": f"Server error: {str(e)}"}), 500

@app.route("/admin/set_point_decay", methods=["POST"])
def admin_set_point_decay():
    if session.get("admin_id") != "master":
        return jsonify({"success": False, "message": "Master account required"}), 403
    role_name = request.form["role_name"]
    points = int(request.form["points"])
    days = request.form.getlist("days[]")
    try:
        with DatabaseConnection() as conn:
            success, message = set_point_decay(conn, role_name, points, days)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in set_point_decay: {str(e)}\n{traceback.format_exc()}")
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
    day = request.args.get("day")  # New for daily filter
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
        return "Internal Server Error", 500

@app.route("/admin/export_payout", methods=["GET"])
def export_payout():
    if "admin_id" not in session:
        return "Admin login required", 403
    month = request.args.get("month")
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, month)]
            if not history:
                return "No data for selected month", 404
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
                output_lines.append("")  # Blank line separator
            output = io.BytesIO()
            output.write("\n".join(output_lines).encode())
            output.seek(0)
        return send_file(output, mimetype='text/csv', as_attachment=True, download_name=f"payout_{month}.csv")
    except Exception as e:
        logging.error(f"Error in export_payout: {str(e)}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

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
        ax.plot(df['date'], df['score'].cumsum(), marker='o')  # Cumulative for trends
        ax.set_title(f"Score Trend for {history[0]['name']} in {month}")
        ax.set_xlabel("Date")
        ax.set_ylabel("Score")
        output = io.BytesIO()
        canvas = FigureCanvas(fig)
        canvas.print_png(output)
        output.seek(0)
        encoded = base64.b64encode(output.read()).decode('utf-8')
        return f"data:image/png;base64,{encoded}"
    except Exception as e:
        logging.error(f"Error in history_chart: {str(e)}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

@app.route("/admin/mark_feedback_read", methods=["POST"])
def mark_feedback_read():
    if "admin_id" not in session:
        return jsonify({"success": False, "message": "Admin login required"}), 403
    feedback_id = request.form["feedback_id"]
    try:
        with DatabaseConnection() as conn:
            success, message = mark_feedback_read(conn, feedback_id)
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logging.error(f"Error in mark_feedback_read: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"success": False, "message": "Server error"}), 500

@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    form = FeedbackForm()
    if form.validate_on_submit():
        try:
            with DatabaseConnection() as conn:
                success, message = add_feedback(conn, form.comment.data, form.initials.data if "admin_id" not in session else session["admin_id"])
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in submit_feedback: {str(e)}\n{traceback.format_exc()}")
            return jsonify({"success": False, "message": "Server error"}), 500
    return jsonify({"success": False, "message": "Invalid form"}), 400

@app.route("/admin/settings", methods=["GET", "POST"])
def admin_settings():
    if "admin_id" not in session or session.get("admin_id") != "master":
        return "Master admin required", 403
    if request.method == "POST":
        key = request.form["key"]
        value = request.form["value"]
        try:
            with DatabaseConnection() as conn:
                success, message = set_settings(conn, key, value)
            return jsonify({"success": success, "message": message})
        except Exception as e:
            logging.error(f"Error in admin_settings POST: {str(e)}\n{traceback.format_exc()}")
            return "Internal Server Error", 500
    try:
        with DatabaseConnection() as conn:
            settings = get_settings(conn)
        return render_template("settings.html", settings=settings)
    except Exception as e:
        logging.error(f"Error in admin_settings GET: {str(e)}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6800, debug=True)