from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from incentive_service import DatabaseConnection, get_scoreboard, start_voting_session, is_voting_active, cast_votes, add_employee, reset_scores, get_history, adjust_points, get_rules, add_rule, edit_rule, remove_rule, get_pot_info, update_pot_info, close_voting_session, pause_voting_session, get_voting_results, master_reset_all, get_roles, add_role, edit_role, remove_role, edit_employee, reorder_rules, retire_employee, reactivate_employee, delete_employee, set_point_decay, get_point_decay, deduct_points_daily, get_latest_voting_results
import logging
import time
import traceback
from datetime import datetime
import sqlite3
import threading
from flask_wtf.csrf import CSRFProtect

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
        logging.debug(f"Loaded incentive page: voting_active={voting_active}, results_count={len(voting_results)}")
        return render_template("incentive.html", scoreboard=scoreboard, voting_active=voting_active, rules=rules, pot_info=pot_info, roles=roles, is_admin=bool(session.get("admin_id")), import_time=int(time.time()), voting_results=voting_results, current_month=current_month, selected_week=week_number)
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
    if request.method == "GET":
        if "admin_id" not in session:
            return render_template("start_voting.html", is_master=session.get("admin_id") == "master", import_time=int(time.time()))
        return render_template("start_voting.html", is_master=session.get("admin_id") == "master", import_time=int(time.time()))
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
        username = request.form["username"]
        password = request.form["password"]
        try:
            with DatabaseConnection() as conn:
                admin = conn.execute("SELECT * FROM admins WHERE username = ?", (username,)).fetchone()
                if admin and check_password_hash(admin["password"], password):
                    session["admin_id"] = admin["admin_id"]
                    return redirect(url_for("admin"))
            return render_template("admin_login.html", error="Invalid credentials", import_time=int(time.time()))
        except Exception as e:
            logging.error(f"Error in admin login: {str(e)}\n{traceback.format_exc()}")
            return "Internal Server Error", 500
    if "admin_id" not in session:
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
        return render_template("admin_manage.html", employees=employees, rules=rules, pot_info=pot_info, roles=roles, decay=decay, admins=admins, voting_results=voting_results, is_admin=True, is_master=session.get("admin_id") == "master", import_time=int(time.time()))
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
    try:
        with DatabaseConnection() as conn:
            success, message = adjust_points(conn, employee_id, points, session["admin_id"], reason)
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
            success, message = adjust_points(conn, employee_id, points, admin["admin_id"], reason)
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
    try:
        with DatabaseConnection() as conn:
            success, message = add_rule(conn, description, points)
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
    try:
        with DatabaseConnection() as conn:
            success, message = edit_rule(conn, old_description, new_description, points)
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
    try:
        with DatabaseConnection() as conn:
            history = [dict(row) for row in get_history(conn, month_year)]
            months = conn.execute("SELECT DISTINCT month_year FROM score_history ORDER BY month_year DESC").fetchall()
        return render_template("history.html", history=history, months=[m["month_year"] for m in months], is_admin=bool(session.get("admin_id")), import_time=int(time.time()))
    except Exception as e:
        logging.error(f"Error in history: {str(e)}\n{traceback.format_exc()}")
        return "Internal Server Error", 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=6800, debug=True)