# incentive_service.py
# Version: 1.2.9
# Note: Fixed ImportError by updating import to 'from config import Config' and using Config.INCENTIVE_DB_FILE. Maintained fixes from version 1.2.8 (SyntaxError in get_settings, delete_feedback function, unique employee_id generation). Ensured compatibility with app.py (1.2.34), forms.py (1.2.2), config.py (1.2.5), admin_manage.html (1.2.16), incentive.html (1.2.17), quick_adjust.html (1.2.7), script.js (1.2.28), style.css (1.2.11). No changes to core functionality (database operations, voting, point calculations).

import sqlite3
from datetime import datetime, timedelta
from config import Config
import logging
import json
import time

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

class DatabaseConnection:
    def __enter__(self):
        self.conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
            logging.error(f"DB rollback due to {exc_type}: {exc_val}")
        else:
            self.conn.commit()
        self.conn.close()

def get_scoreboard(conn):
    return conn.execute("""
        SELECT e.employee_id, e.name, e.initials, e.score, LOWER(r.role_name) AS role
        FROM employees e
        JOIN roles r ON e.role = LOWER(r.role_name)
        WHERE e.active = 1
        ORDER BY e.score DESC
    """).fetchall()

def start_voting_session(conn, admin_id):
    now = datetime.now()
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time > ? OR end_time IS NULL",
        (now.strftime("%Y-%m-%d %H:%M:%S"),)
    ).fetchone()
    if active_session:
        return False, "Voting session already active or paused"
    start_time = now.strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "INSERT INTO voting_sessions (vote_code, admin_id, start_time, end_time) VALUES (?, ?, ?, NULL)",
        ("active", admin_id, start_time)
    )
    logging.debug(f"Voting session started: admin_id={admin_id}, start={start_time}")
    return True, "Voting session started"

def close_voting_session(conn, admin_id):
    now = datetime.now()
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time IS NULL"
    ).fetchone()
    if not active_session:
        return False, "No active voting session to close"
    session_id = active_session["session_id"]
    start_time = active_session["start_time"]
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    votes = conn.execute(
        "SELECT voter_initials, recipient_id, vote_value FROM votes WHERE vote_date >= ? AND vote_date <= ?",
        (start_time, now.strftime("%Y-%m-%d %H:%M:%S"))
    ).fetchall()
    logging.debug(f"Closing session: {len(votes)} votes found between {start_time} and {end_time}")
    employees = {e["employee_id"]: dict(e) for e in conn.execute("SELECT employee_id, name, role, score FROM employees").fetchall()}
    vote_counts = {}
    total_voters = conn.execute("SELECT COUNT(*) as count FROM employees WHERE active = 1").fetchone()["count"]
    
    for vote in votes:
        recipient_id = vote["recipient_id"]
        if recipient_id not in vote_counts:
            vote_counts[recipient_id] = {"plus": 0, "minus": 0}
        if vote["vote_value"] > 0:
            vote_counts[recipient_id]["plus"] += 1
        elif vote["vote_value"] < 0:
            vote_counts[recipient_id]["minus"] += 1

    logging.debug(f"Total eligible voters: {total_voters}")
    settings = get_settings(conn)
    thresholds_json = settings.get('voting_thresholds', '{"positive":[{"threshold":90,"points":10},{"threshold":60,"points":5},{"threshold":25,"points":2}],"negative":[{"threshold":90,"points":-10},{"threshold":60,"points":-5},{"threshold":25,"points":-2}]}')
    thresholds = json.loads(thresholds_json)
    positive_thresholds = sorted(thresholds['positive'], key=lambda x: x['threshold'], reverse=True)
    negative_thresholds = sorted(thresholds['negative'], key=lambda x: x['threshold'], reverse=True)
    
    for emp_id, counts in vote_counts.items():
        if emp_id not in employees:
            logging.warning(f"Employee ID {emp_id} not found in employees table")
            continue
        plus_percent = (counts["plus"] / total_voters) * 100 if total_voters > 0 else 0
        minus_percent = (counts["minus"] / total_voters) * 100 if total_voters > 0 else 0
        points = 0
        for thresh in positive_thresholds:
            if plus_percent >= thresh['threshold']:
                points += thresh['points']
                break
        for thresh in negative_thresholds:
            if minus_percent >= thresh['threshold']:
                points += thresh['points']
                break
        logging.debug(f"Employee {emp_id} ({employees[emp_id]['name']}): plus={counts['plus']} ({plus_percent}%), minus={counts['minus']} ({minus_percent}%), points={points}")
        if points != 0:
            old_score = employees[emp_id]["score"]
            new_score = min(100, max(0, old_score + points))
            conn.execute(
                "UPDATE employees SET score = ? WHERE employee_id = ?",
                (new_score, emp_id)
            )
            conn.execute(
                "INSERT INTO score_history (employee_id, changed_by, points, reason, date, month_year) VALUES (?, ?, ?, ?, ?, ?)",
                (emp_id, admin_id, points, f"Weekly vote result: {counts['plus']} +1, {counts['minus']} -1", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
            )
        conn.execute(
            "INSERT INTO voting_results (session_id, employee_id, plus_votes, minus_votes, plus_percent, minus_percent, points) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, emp_id, counts["plus"], counts["minus"], plus_percent, minus_percent, points)
        )

    conn.execute("UPDATE voting_sessions SET end_time = ? WHERE session_id = ?", (end_time, session_id))
    logging.debug(f"Voting session closed: total_voters={total_voters}")
    return True, f"Voting session closed, scores updated based on {total_voters} voters"

def pause_voting_session(conn, admin_id):
    now = datetime.now()
    active_session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time IS NULL"
    ).fetchone()
    if not active_session:
        return False, "No active voting session to pause"
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    conn.execute("UPDATE voting_sessions SET end_time = ? WHERE session_id = ?", (end_time, active_session["session_id"]))
    logging.debug(f"Voting session paused: admin_id={admin_id}, end_time={end_time}")
    return True, "Voting session paused"

def is_voting_active(conn):
    now = datetime.now()
    session = conn.execute(
        "SELECT * FROM voting_sessions WHERE end_time IS NULL"
    ).fetchone()
    if not session:
        return False
    eligible_voters = conn.execute("SELECT COUNT(*) as count FROM employees").fetchone()["count"]
    votes_cast = conn.execute(
        "SELECT COUNT(DISTINCT voter_initials) as count FROM votes WHERE vote_date >= ?",
        (session["start_time"],)
    ).fetchone()["count"]
    return votes_cast < eligible_voters

def cast_votes(conn, voter_initials, votes):
    now = datetime.now()
    start_time = time.time()
    try:
        with conn:
            if not voter_initials or not voter_initials.strip():
                logging.error("cast_votes: Empty or None voter_initials received")
                return False, "Voter initials cannot be empty"
            voter = conn.execute("SELECT employee_id, role FROM employees WHERE LOWER(initials) = ?", (voter_initials.lower(),)).fetchone()
            if not voter:
                logging.error(f"cast_votes: No employee found for initials {voter_initials}")
                return False, "Invalid voter initials"
            if not is_voting_active(conn):
                logging.error("cast_votes: Voting is not active")
                return False, "Voting is not active"
            week_number = now.isocalendar()[1]
            existing_vote = conn.execute(
                "SELECT COUNT(*) as count FROM votes WHERE LOWER(voter_initials) = ? AND strftime('%W', vote_date) = ?",
                (voter_initials.lower(), str(week_number))
            ).fetchone()["count"]
            if existing_vote > 0:
                logging.error(f"cast_votes: {voter_initials} has already voted this week")
                return False, "You have already voted this week"

            plus_votes = sum(1 for value in votes.values() if value > 0)
            minus_votes = sum(1 for value in votes.values() if value < 0)
            total_votes = plus_votes + minus_votes
            
            if plus_votes > 2:
                logging.error(f"cast_votes: Too many positive votes ({plus_votes}) from {voter_initials}")
                return False, "You can only cast up to 2 positive (+1) votes per session"
            if minus_votes > 3:
                logging.error(f"cast_votes: Too many negative votes ({minus_votes}) from {voter_initials}")
                return False, "You can only cast up to 3 negative (-1) votes per session"
            if total_votes > 3:
                logging.error(f"cast_votes: Total votes ({total_votes}) exceeds limit from {voter_initials}")
                return False, "You can only cast a maximum of 3 votes total per session"

            for recipient_id, vote_value in votes.items():
                if not conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (recipient_id,)).fetchone():
                    logging.warning(f"Invalid recipient_id: {recipient_id}")
                    continue
                conn.execute(
                    "INSERT INTO votes (voter_initials, recipient_id, vote_value, vote_date) VALUES (?, ?, ?, ?)",
                    (voter_initials, recipient_id, vote_value, now.strftime("%Y-%m-%d %H:%M:%S"))
                )
                logging.debug(f"Vote recorded: voter={voter_initials}, recipient={recipient_id}, value={vote_value}")
        duration = time.time() - start_time
        logging.debug(f"Vote processing completed in {duration:.2f} seconds for {voter_initials}")
        return True, "Votes cast successfully"
    except sqlite3.OperationalError as e:
        duration = time.time() - start_time
        logging.error(f"Database error during voting for {voter_initials}: {str(e)}, duration={duration:.2f} seconds")
        return False, "Failed to record votes due to database error"

def add_employee(conn, name, initials, role):
    role_lower = role.lower()
    valid_role = conn.execute("SELECT 1 FROM roles WHERE LOWER(role_name) = ?", (role_lower,)).fetchone()
    if not valid_role:
        return False, f"Role '{role}' does not exist"
    
    try:
        # Get the highest existing employee_id and increment it
        max_id_row = conn.execute("SELECT MAX(CAST(SUBSTR(employee_id, 2) AS INTEGER)) as max_id FROM employees").fetchone()
        max_id = max_id_row["max_id"] if max_id_row["max_id"] is not None else 0
        employee_id = f"E{str(max_id + 1).zfill(3)}"
        
        conn.execute(
            "INSERT INTO employees (employee_id, name, initials, score, role, active) VALUES (?, ?, ?, 50, ?, 1)",
            (employee_id, name, initials, role_lower)
        )
        return True, f"Employee {name} added with ID {employee_id}"
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: employees.initials" in str(e):
            return False, f"Initials '{initials}' are already in use"
        logging.error(f"Error in add_employee: {str(e)}")
        return False, f"Failed to add employee due to database error: {str(e)}"

def retire_employee(conn, employee_id):
    conn.execute(
        "UPDATE employees SET active = 0 WHERE employee_id = ?",
        (employee_id,)
    )
    affected = conn.total_changes
    return affected > 0, f"Employee {employee_id} retired" if affected > 0 else "Employee not found"

def reactivate_employee(conn, employee_id):
    conn.execute(
        "UPDATE employees SET active = 1 WHERE employee_id = ?",
        (employee_id,)
    )
    affected = conn.total_changes
    return affected > 0, f"Employee {employee_id} reactivated" if affected > 0 else "Employee not found"

def delete_employee(conn, employee_id):
    conn.execute("DELETE FROM employees WHERE employee_id = ?", (employee_id,))
    affected = conn.total_changes
    return affected > 0, f"Employee {employee_id} permanently deleted" if affected > 0 else "Employee not found"

def edit_employee(conn, employee_id, name, role):
    role_lower = role.lower()
    valid_role = conn.execute("SELECT 1 FROM roles WHERE LOWER(role_name) = ?", (role_lower,)).fetchone()
    if not valid_role:
        return False, f"Role '{role}' does not exist"
    
    conn.execute(
        "UPDATE employees SET name = ?, role = ? WHERE employee_id = ?",
        (name, role_lower, employee_id)
    )
    affected = conn.total_changes
    return affected > 0, f"Employee {employee_id} updated" if affected > 0 else "Employee not found"

def adjust_points(conn, employee_id, points, admin_id, reason, notes=""):
    now = datetime.now()
    employee = conn.execute("SELECT score FROM employees WHERE employee_id = ?", (employee_id,)).fetchone()
    if not employee:
        return False, "Employee not found"
    new_score = min(100, max(0, employee["score"] + points))
    conn.execute(
        "UPDATE employees SET score = ? WHERE employee_id = ?",
        (new_score, employee_id)
    )
    try:
        conn.execute(
            "INSERT INTO score_history (employee_id, changed_by, points, reason, notes, date, month_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (employee_id, admin_id, points, reason, notes, now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
        )
    except sqlite3.OperationalError as e:
        if "no column named notes" in str(e):
            conn.execute("ALTER TABLE score_history ADD COLUMN notes TEXT DEFAULT ''")
            conn.execute(
                "INSERT INTO score_history (employee_id, changed_by, points, reason, notes, date, month_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (employee_id, admin_id, points, reason, notes, now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
            )
        else:
            raise
    return True, f"Adjusted {points} points for employee {employee_id}"

def reset_scores(conn, admin_id, reason=None):
    now = datetime.now()
    employees = conn.execute("SELECT employee_id, score FROM employees").fetchall()
    for emp in employees:
        if emp["score"] != 50:
            conn.execute(
                "INSERT INTO score_history (employee_id, changed_by, points, reason, date, month_year) VALUES (?, ?, ?, ?, ?, ?)",
                (emp["employee_id"], admin_id, 50 - emp["score"], reason or "Manual reset", now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
            )
    conn.execute("UPDATE employees SET score = 50")
    return True, "Scores reset to 50"

def master_reset_all(conn):
    conn.execute("DELETE FROM votes")
    conn.execute("DELETE FROM score_history")
    conn.execute("DELETE FROM voting_sessions")
    conn.execute("UPDATE employees SET score = 50")
    logging.debug("Master reset: cleared votes, history, sessions, reset scores to 50")
    return True, "All voting data and history reset"

def get_history(conn, month_year=None, day=None, employee_id=None):
    try:
        conn.execute("SELECT notes FROM score_history LIMIT 1")
    except sqlite3.OperationalError as e:
        if "no column named notes" in str(e):
            conn.execute("ALTER TABLE score_history ADD COLUMN notes TEXT DEFAULT ''")
    query = "SELECT sh.*, e.name FROM score_history sh JOIN employees e ON sh.employee_id = e.employee_id"
    params = []
    where = []
    if month_year:
        where.append("month_year = ?")
        params.append(month_year)
    if day:
        where.append("substr(date, 1, 10) = ?")
        params.append(day)
    if employee_id:
        where.append("sh.employee_id = ?")
        params.append(employee_id)
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY date DESC"
    return conn.execute(query, params).fetchall()

def get_rules(conn):
    try:
        return conn.execute("SELECT description, points, details FROM incentive_rules ORDER BY display_order ASC").fetchall()
    except sqlite3.OperationalError as e:
        if "no such column: details" in str(e):
            logging.warning("details column missing, adding now")
            conn.execute("ALTER TABLE incentive_rules ADD COLUMN details TEXT DEFAULT ''")
            return conn.execute("SELECT description, points, details FROM incentive_rules ORDER BY display_order ASC").fetchall()
        if "no such column: display_order" in str(e):
            logging.warning("display_order column missing, falling back to unordered fetch")
            return conn.execute("SELECT description, points, details FROM incentive_rules").fetchall()
        raise

def add_rule(conn, description, points, details=""):
    try:
        max_order = conn.execute("SELECT MAX(display_order) as max_order FROM incentive_rules").fetchone()["max_order"] or 0
        conn.execute(
            "INSERT INTO incentive_rules (description, points, details, display_order) VALUES (?, ?, ?, ?)",
            (description, points, details, max_order + 1)
        )
    except sqlite3.OperationalError as e:
        if "no such column: details" in str(e):
            conn.execute("ALTER TABLE incentive_rules ADD COLUMN details TEXT DEFAULT ''")
            conn.execute(
                "INSERT INTO incentive_rules (description, points, details, display_order) VALUES (?, ?, ?, ?)",
                (description, points, details, max_order + 1)
            )
        elif "no such column: display_order" in str(e):
            conn.execute(
                "INSERT INTO incentive_rules (description, points, details) VALUES (?, ?, ?)",
                (description, points, details)
            )
        else:
            raise
    return True, f"Rule '{description}' added with {points} points"

def edit_rule(conn, old_description, new_description, points, details):
    conn.execute(
        "UPDATE incentive_rules SET description = ?, points = ?, details = ? WHERE description = ?",
        (new_description, points, details, old_description)
    )
    affected = conn.total_changes
    return affected > 0, f"Rule '{old_description}' updated to '{new_description}' with {points} points" if affected > 0 else "Rule not found"

def remove_rule(conn, description):
    conn.execute(
        "DELETE FROM incentive_rules WHERE description = ?",
        (description,)
    )
    affected = conn.total_changes
    return affected > 0, f"Rule '{description}' removed" if affected > 0 else "Rule not found"

def reorder_rules(conn, order):
    try:
        for index, description in enumerate(order):
            conn.execute(
                "UPDATE incentive_rules SET display_order = ? WHERE description = ?",
                (index + 1, description)
            )
        return True, "Rules reordered successfully"
    except sqlite3.OperationalError as e:
        if "no such column: display_order" in str(e):
            logging.warning("display_order column missing, reordering not supported")
            return False, "Rule reordering not available due to missing display_order column"
        raise

def get_roles(conn):
    try:
        return conn.execute("SELECT role_name, percentage FROM roles").fetchall()
    except sqlite3.OperationalError:
        logging.warning("roles table missing, returning default roles with supervisor")
        conn.execute("CREATE TABLE roles (role_name TEXT PRIMARY KEY, percentage REAL)")
        conn.execute("INSERT INTO roles (role_name, percentage) VALUES ('driver', 50)")
        conn.execute("INSERT INTO roles (role_name, percentage) VALUES ('laborer', 45)")
        conn.execute("INSERT INTO roles (role_name, percentage) VALUES ('supervisor', 5)")
        return conn.execute("SELECT role_name, percentage FROM roles").fetchall()

def add_role(conn, role_name, percentage):
    roles = get_roles(conn)
    if len(roles) >= 10:
        return False, "Maximum number of roles reached"
    total_percentage = sum(role["percentage"] for role in roles) + percentage
    if total_percentage > 100:
        current_roles_str = ", ".join([str(role["role_name"]) + ": " + str(role["percentage"]) + "%" for role in roles])
        return False, f"Total percentage exceeds 100%, got {total_percentage}% (Current roles: {current_roles_str}), New role: {role_name} with {percentage}%"
    role_name_lower = role_name.lower()
    conn.execute(
        "INSERT INTO roles (role_name, percentage) VALUES (?, ?)",
        (role_name, percentage)
    )
    conn.execute(
        "UPDATE employees SET role = ? WHERE role = ?",
        (role_name_lower, role_name)
    )
    conn.execute(
        "INSERT OR IGNORE INTO point_decay (role_name, points, days) VALUES (?, ?, ?)",
        (role_name, 1, json.dumps([]))
    )
    return True, f"Role '{role_name}' added with {percentage}%"

def edit_role(conn, old_role_name, new_role_name, percentage):
    roles = get_roles(conn)
    total_percentage = sum(role["percentage"] for role in roles if role["role_name"] != old_role_name) + percentage
    if total_percentage > 100:
        return False, f"Total percentage cannot exceed 100%, got {total_percentage}% after edit"
    new_role_name_lower = new_role_name.lower()
    conn.execute(
        "UPDATE roles SET role_name = ?, percentage = ? WHERE role_name = ?",
        (new_role_name, percentage, old_role_name)
    )
    conn.execute(
        "UPDATE employees SET role = ? WHERE role = ?",
        (new_role_name_lower, old_role_name)
    )
    conn.execute(
        "UPDATE point_decay SET role_name = ? WHERE role_name = ?",
        (new_role_name, old_role_name)
    )
    affected = conn.total_changes
    return affected > 0, f"Role '{old_role_name}' updated to '{new_role_name}' with {percentage}% (Total: {total_percentage}%)" if affected > 0 else "Role not found"

def remove_role(conn, role_name):
    if role_name == "supervisor":
        return False, "Cannot remove the 'supervisor' role as it is required for voting weight and admin functionality"
    roles = get_roles(conn)
    if len(roles) <= 2:
        return False, "Cannot remove role; minimum of 2 roles (excluding supervisor) required"
    conn.execute("DELETE FROM roles WHERE role_name = ?", (role_name,))
    affected = conn.total_changes
    if affected > 0:
        conn.execute("UPDATE employees SET role = 'driver' WHERE role = ?", (role_name,))
        conn.execute("DELETE FROM point_decay WHERE role_name = ?", (role_name,))
        return True, f"Role '{role_name}' removed, affected employees reassigned to 'driver'"
    return False, "Role not found"

def get_pot_info(conn):
    pot_row = conn.execute("SELECT sales_dollars, bonus_percent, prior_year_sales FROM incentive_pot WHERE id = 1").fetchone()
    pot = dict(pot_row) if pot_row else {"sales_dollars": 0.0, "bonus_percent": 0.0, "prior_year_sales": 0.0}
    roles = get_roles(conn)
    for role in roles:
        role_name = role["role_name"].lower()
        pot[f"{role_name}_percent"] = role["percentage"]
        pot[f"{role_name}_pot"] = 0.0
        pot[f"{role_name}_point_value"] = 0.0
        pot[f"{role_name}_prior_year_pot"] = 0.0
        pot[f"{role_name}_prior_year_point_value"] = 0.0

    total_pot = pot["sales_dollars"] * pot["bonus_percent"] / 100
    for role in roles:
        role_name = role["role_name"].lower()
        role_percent = pot[f"{role_name}_percent"]
        role_pot = total_pot * role_percent / 100
        role_count = conn.execute("SELECT COUNT(*) as count FROM employees WHERE role = ? AND active = 1", (role_name,)).fetchone()["count"] or 1
        max_points_per_employee = 100
        role_max_points = role_count * max_points_per_employee
        role_point_value = role_pot / role_max_points if role_max_points > 0 else 0
        pot[f"{role_name}_pot"] = role_pot
        pot[f"{role_name}_point_value"] = role_point_value

    prior_year_total_pot = pot["prior_year_sales"] * pot["bonus_percent"] / 100
    for role in roles:
        role_name = role["role_name"].lower()
        role_percent = pot[f"{role_name}_percent"]
        role_prior_year_pot = prior_year_total_pot * role_percent / 100
        role_count = conn.execute("SELECT COUNT(*) as count FROM employees WHERE role = ? AND active = 1", (role_name,)).fetchone()["count"] or 1
        max_points_per_employee = 100
        role_max_points = role_count * max_points_per_employee
        role_prior_year_point_value = role_prior_year_pot / role_max_points if role_max_points > 0 else 0
        pot[f"{role_name}_prior_year_pot"] = role_prior_year_pot
        pot[f"{role_name}_prior_year_point_value"] = role_prior_year_point_value

    logging.debug(f"Pot info retrieved: {pot}")
    return pot

def update_pot_info(conn, sales_dollars, bonus_percent, percentages):
    roles = get_roles(conn)
    total_role_percentage = sum(percentages.values())
    if total_role_percentage != 100:
        return False, f"Total role percentages must equal 100%, got {total_role_percentage}%"
    if len(roles) != len(percentages):
        return False, "Percentage must be provided for each role"
    for role in roles:
        role_name = role["role_name"]
        if role_name not in percentages:
            return False, f"Percentage for role '{role_name}' missing"
        conn.execute(
            "UPDATE roles SET percentage = ? WHERE role_name = ?",
            (percentages[role_name], role_name)
        )
    conn.execute(
        "INSERT OR REPLACE INTO incentive_pot (id, sales_dollars, bonus_percent) VALUES (1, ?, ?)",
        (sales_dollars, bonus_percent)
    )
    return True, "Pot info updated"

def get_voting_results(conn, is_admin=False, week_number=None):
    now = datetime.now()
    current_month = now.strftime("%Y-%m")
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
    end_of_month = (now.replace(day=1, month=now.month+1) - timedelta(days=1)).replace(hour=23, minute=59, second=59).strftime("%Y-%m-%d %H:%M:%S")

    if is_admin and week_number:
        week_start = (now.replace(day=1) + timedelta(weeks=week_number-1)).strftime("%Y-%m-%d 00:00:00")
        week_end = (datetime.strptime(week_start, "%Y-%m-%d %H:%M:%S") + timedelta(days=6)).strftime("%Y-%m-%d 23:59:59")
        query = """
            SELECT v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, COALESCE(sh.points, 0) AS points
            FROM votes v
            JOIN employees e ON v.recipient_id = e.employee_id
            LEFT JOIN score_history sh ON v.recipient_id = sh.employee_id AND sh.reason LIKE 'Weekly vote result%' AND sh.date >= ? AND sh.date <= ?
            WHERE v.vote_date >= ? AND v.vote_date <= ?
            ORDER BY v.vote_date DESC
        """
        params = [week_start, week_end, week_start, week_end]
    elif is_admin:
        last_session = conn.execute(
            "SELECT start_time, end_time FROM voting_sessions ORDER BY end_time DESC LIMIT 1"
        ).fetchone()
        if not last_session:
            logging.debug("No voting sessions found")
            return []
        start_date = last_session["start_time"]
        end_date = last_session["end_time"] or now.strftime("%Y-%m-%d %H:%M:%S")
        query = """
            SELECT v.voter_initials, e.name AS recipient_name, v.vote_value, v.vote_date, COALESCE(sh.points, 0) AS points
            FROM votes v
            JOIN employees e ON v.recipient_id = e.employee_id
            LEFT JOIN score_history sh ON v.recipient_id = sh.employee_id AND sh.reason LIKE 'Weekly vote result%' AND sh.date >= ? AND sh.date <= ?
            WHERE v.vote_date >= ? AND v.vote_date <= ?
            ORDER BY v.vote_date DESC
        """
        params = [start_date, end_date, start_date, end_date]
    else:
        query = """
            SELECT strftime('%W', v.vote_date) AS week_number, e.name AS recipient_name,
                   SUM(CASE WHEN v.vote_value > 0 THEN v.vote_value ELSE 0 END) AS plus_votes,
                   SUM(CASE WHEN v.vote_value < 0 THEN -v.vote_value ELSE 0 END) AS minus_votes, COALESCE(sh.points, 0) AS points
            FROM votes v
            JOIN employees e ON v.recipient_id = e.employee_id
            LEFT JOIN score_history sh ON v.recipient_id = sh.employee_id AND sh.reason LIKE 'Weekly vote result%' AND sh.date >= ? AND sh.date <= ?
            WHERE v.vote_date >= ? AND v.vote_date <= ?
            GROUP BY strftime('%W', v.vote_date), e.name, sh.points
            ORDER BY week_number DESC
        """
        params = [start_of_month, end_of_month, start_of_month, end_of_month]

    results = conn.execute(query, params).fetchall()
    logging.debug(f"Voting results fetched: {len(results)} entries for {'admin' if is_admin else 'non-admin'} view")
    return [dict(row) for row in results]

def get_latest_voting_results(conn):
    latest_session = conn.execute("SELECT session_id FROM voting_sessions ORDER BY end_time DESC LIMIT 1").fetchone()
    if not latest_session:
        return []
    results = conn.execute("""
        SELECT vr.employee_id, e.name, vr.plus_votes, vr.minus_votes, vr.plus_percent, vr.minus_percent, vr.points
        FROM voting_results vr
        JOIN employees e ON vr.employee_id = e.employee_id
        WHERE vr.session_id = ?
    """, (latest_session["session_id"],)).fetchall()
    return [dict(row) for row in results]

def set_point_decay(conn, role_name, points, days):
    days_json = json.dumps(days)
    conn.execute(
        "INSERT OR REPLACE INTO point_decay (id, role_name, points, days) VALUES ((SELECT id FROM point_decay WHERE role_name = ?), ?, ?, ?)",
        (role_name, role_name, points, days_json)
    )
    return True, f"Point decay for {role_name} set to {points} points on {days}"

def get_point_decay(conn):
    roles = get_roles(conn)
    role_names = [role["role_name"] for role in roles]
    
    for role_name in role_names:
        existing = conn.execute("SELECT 1 FROM point_decay WHERE role_name = ?", (role_name,)).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO point_decay (role_name, points, days) VALUES (?, ?, ?)",
                (role_name, 1, json.dumps([]))
            )
            logging.debug(f"Added default point_decay entry for role: {role_name}")

    rows = conn.execute("SELECT role_name, points, days FROM point_decay").fetchall()
    return {row["role_name"]: {"points": row["points"], "days": json.loads(row["days"])} for row in rows}

def deduct_points_daily(conn):
    today = datetime.now().strftime("%A")
    decay_settings = get_point_decay(conn)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    messages = []
    
    for role_name, decay in decay_settings.items():
        if today not in decay["days"]:
            logging.debug(f"Skipping decay for {role_name} - {today} not in {decay['days']}")
            continue
        points_to_deduct = decay["points"]
        employees = conn.execute(
            "SELECT employee_id, score, last_decay_date FROM employees WHERE active = 1 AND role = ?",
            (role_name.lower(),)
        ).fetchall()
        
        for emp in employees:
            employee_id = emp["employee_id"]
            last_decay = emp["last_decay_date"]
            logging.debug(f"Processing employee {employee_id} in role {role_name}, last_decay={last_decay}")
            if not last_decay or (datetime.strptime(now, "%Y-%m-%d %H:%M:%S") - datetime.strptime(last_decay, "%Y-%m-%d %H:%M:%S")).days >= 1:
                new_score = max(0, emp["score"] - points_to_deduct)
                logging.debug(f"Applying decay for {employee_id}: {emp['score']} -> {new_score}")
                conn.execute(
                    "UPDATE employees SET score = ?, last_decay_date = ? WHERE employee_id = ?",
                    (new_score, now, employee_id)
                )
                conn.execute(
                    "INSERT INTO score_history (employee_id, changed_by, points, reason, date, month_year) VALUES (?, ?, ?, ?, ?, ?)",
                    (employee_id, "system", -points_to_deduct, f"Daily point decay for {role_name}", now, now[:7])
                )
                conn.commit()
                messages.append(f"Deducted {points_to_deduct} points from {employee_id} ({role_name}) on {today}")
            else:
                logging.debug(f"Skipping decay for {employee_id} - last decay too recent")
    
    return bool(messages), "; ".join(messages) or f"No decay scheduled for {today}"

def add_feedback(conn, comment, submitter):
    now = datetime.now()
    if not comment or not comment.strip():
        return False, "Feedback comment cannot be empty"
    try:
        conn.execute(
            "INSERT INTO feedback (comment, submitter, timestamp, read) VALUES (?, ?, ?, 0)",
            (comment, submitter, now.strftime("%Y-%m-%d %H:%M:%S"))
        )
    except sqlite3.OperationalError as e:
        if "no such table: feedback" in str(e):
            logging.warning("feedback table missing, creating now")
            conn.execute("CREATE TABLE feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, comment TEXT, submitter TEXT, timestamp TEXT, read INTEGER DEFAULT 0)")
            conn.execute(
                "INSERT INTO feedback (comment, submitter, timestamp, read) VALUES (?, ?, ?, 0)",
                (comment, submitter, now.strftime("%Y-%m-%d %H:%M:%S"))
            )
        else:
            raise
    return True, "Feedback submitted"

def get_unread_feedback_count(conn):
    try:
        return conn.execute("SELECT COUNT(*) as count FROM feedback WHERE read = 0").fetchone()["count"]
    except sqlite3.OperationalError as e:
        if "no such table: feedback" in str(e):
            logging.warning("feedback table missing, creating now")
            conn.execute("CREATE TABLE feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, comment TEXT, submitter TEXT, timestamp TEXT, read INTEGER DEFAULT 0)")
            return 0
        raise

def get_feedback(conn):
    try:
        return conn.execute("SELECT * FROM feedback ORDER BY timestamp DESC").fetchall()
    except sqlite3.OperationalError as e:
        if "no such table: feedback" in str(e):
            logging.warning("feedback table missing, creating now")
            conn.execute("CREATE TABLE feedback (id INTEGER PRIMARY KEY AUTOINCREMENT, comment TEXT, submitter TEXT, timestamp TEXT, read INTEGER DEFAULT 0)")
            return []
        raise

def mark_feedback_read(conn, feedback_id):
    if not feedback_id:
        logging.error("mark_feedback_read: Missing feedback_id")
        return False, "Feedback ID required"
    try:
        feedback_id = int(feedback_id)
        conn.execute("UPDATE feedback SET read = 1 WHERE id = ?", (feedback_id,))
        affected = conn.total_changes
        return affected > 0, "Feedback marked read" if affected > 0 else "Feedback not found"
    except ValueError:
        logging.error(f"mark_feedback_read: Invalid feedback_id {feedback_id}")
        return False, "Invalid feedback ID"

def delete_feedback(conn, feedback_id):
    if not feedback_id:
        logging.error("delete_feedback: Missing feedback_id")
        return False, "Feedback ID required"
    try:
        feedback_id = int(feedback_id)
        conn.execute("DELETE FROM feedback WHERE id = ?", (feedback_id,))
        affected = conn.total_changes
        return affected > 0, "Feedback deleted" if affected > 0 else "Feedback not found"
    except ValueError:
        logging.error(f"delete_feedback: Invalid feedback_id {feedback_id}")
        return False, "Invalid feedback ID"

def get_settings(conn):
    try:
        settings = dict(conn.execute("SELECT key, value FROM settings").fetchall())
        if 'voting_thresholds' not in settings:
            default_thresholds = '{"positive":[{"threshold":90,"points":10},{"threshold":60,"points":5},{"threshold":25,"points":2}],"negative":[{"threshold":90,"points":-10},{"threshold":60,"points":-5},{"threshold":25,"points":-2}]}'
            set_settings(conn, 'voting_thresholds', default_thresholds)
            settings['voting_thresholds'] = default_thresholds
        if 'program_end_date' not in settings:
            set_settings(conn, 'program_end_date', '')
            settings['program_end_date'] = ''
        return settings
    except sqlite3.OperationalError as e:
        if "no such table: settings" in str(e):
            logging.warning("settings table missing, creating now")
            conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
            return get_settings(conn)
        raise

def set_settings(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    return True, f"Setting '{key}' updated"