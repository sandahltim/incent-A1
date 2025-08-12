# incentive_service.py
# Version: 1.2.31
# Note: Added default scoreboard timing settings. Compatible with app.py (1.2.114), forms.py (1.2.22), settings.html (1.3.1), incentive.html (1.3.2), script.js (1.2.97), init_db.py (1.2.5).

import sqlite3
from datetime import datetime, timedelta
from config import Config
import logging
from logging_config import setup_logging
import json
import time
import traceback

_pot_cache = None
_pot_cache_timestamp = None
_POT_CACHE_DURATION = 60  # Cache for 60 seconds
setup_logging()

class DatabaseConnection:
    def __enter__(self):
        self.conn = sqlite3.connect(Config.INCENTIVE_DB_FILE, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        logging.debug(f"Database connection opened: {Config.INCENTIVE_DB_FILE} with WAL mode")
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
            logging.error(f"DB rollback due to {exc_type}: {exc_val}")
        else:
            self.conn.commit()
            logging.debug("Database changes committed")
        self.conn.close()
        logging.debug("Database connection closed")

def get_scoreboard(conn):
    return conn.execute(
        """
        SELECT e.employee_id, e.name, e.initials, e.score, LOWER(r.role_name) AS role
        FROM employees e
        JOIN roles r ON e.role = LOWER(r.role_name)
        WHERE e.active = 1 AND LOWER(r.role_name) != 'master'
        ORDER BY e.score DESC
        """
    ).fetchall()

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
        """
        SELECT v.voter_initials, v.recipient_id, v.vote_value, e.role
        FROM votes v
        JOIN employees e ON LOWER(v.voter_initials) = LOWER(e.initials)
        WHERE v.vote_date >= ? AND v.vote_date <= ?
        """,
        (start_time, end_time)
    ).fetchall()
    logging.debug(f"Closing session: {len(votes)} votes found between {start_time} and {end_time}")

    settings = get_settings(conn)
    try:
        raw_weights = json.loads(settings.get('role_vote_weights', '{}'))
        role_weights = {k.lower(): float(v) for k, v in raw_weights.items()}
    except json.JSONDecodeError:
        role_weights = {}

    if not role_weights:
        roles = conn.execute('SELECT role_name FROM roles').fetchall()
        for r in roles:
            role = r['role_name'].lower()
            if role == 'supervisor':
                role_weights[role] = 2.0
            elif role == 'master':
                role_weights[role] = 3.0
            else:
                role_weights[role] = 1.0

    def weight_for_role(role_name):
        if not role_name:
            return 1.0
        return float(role_weights.get(role_name.lower(), 1.0))
    vote_counts = {}
    voter_weights = {}
    for vote in votes:
        recipient_id = vote["recipient_id"]
        voter = vote["voter_initials"].lower()
        weight = weight_for_role(vote["role"])
        voter_weights.setdefault(voter, weight)
        if recipient_id not in vote_counts:
            vote_counts[recipient_id] = {"plus": 0, "minus": 0, "plus_weight": 0.0, "minus_weight": 0.0}
        if vote["vote_value"] > 0:
            vote_counts[recipient_id]["plus"] += 1
            vote_counts[recipient_id]["plus_weight"] += weight
        elif vote["vote_value"] < 0:
            vote_counts[recipient_id]["minus"] += 1
            vote_counts[recipient_id]["minus_weight"] += weight

    total_weight = sum(voter_weights.values())
    total_voters = len(voter_weights)
    logging.debug(f"Total voter weight in session: {total_weight}")

    thresholds = json.loads(settings.get('voting_thresholds'))
    pos_thresholds = sorted(thresholds.get('positive', []), key=lambda x: x['threshold'], reverse=True)
    neg_thresholds = sorted(thresholds.get('negative', []), key=lambda x: x['threshold'], reverse=True)

    for emp_id, counts in vote_counts.items():

        recipient_initials = conn.execute(
            "SELECT LOWER(initials) AS initials FROM employees WHERE employee_id = ?",
            (emp_id,),
        ).fetchone()["initials"]
        eligible_voters = total_voters - (1 if recipient_initials in voter_weights else 0)
        plus_percent = (counts["plus"] / eligible_voters) * 100 if eligible_voters > 0 else 0
        minus_percent = (counts["minus"] / eligible_voters) * 100 if eligible_voters > 0 else 0


        points_awarded = 0
        for t in pos_thresholds:
            if plus_percent >= t["threshold"]:
                points_awarded += t["points"]
                break
        for t in neg_thresholds:
            if minus_percent >= t["threshold"]:
                points_awarded += t["points"]
                break

        conn.execute(
            "INSERT INTO voting_results (session_id, employee_id, plus_votes, minus_votes, plus_percent, minus_percent, points) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (session_id, emp_id, counts["plus_weight"], counts["minus_weight"], plus_percent, minus_percent, points_awarded)
        )

        current_score_row = conn.execute("SELECT score FROM employees WHERE employee_id = ?", (emp_id,)).fetchone()
        if current_score_row:
            new_score = min(100, max(0, current_score_row["score"] + points_awarded))
            conn.execute("UPDATE employees SET score = ? WHERE employee_id = ?", (new_score, emp_id))
            conn.execute(
                "INSERT INTO score_history (employee_id, changed_by, points, reason, notes, date, month_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    emp_id,
                    admin_id,
                    points_awarded,
                    "Voting result",
                    "",
                    now.strftime("%Y-%m-%d %H:%M:%S"),
                    now.strftime("%Y-%m")
                )
            )

    conn.execute("UPDATE voting_sessions SET end_time = ? WHERE session_id = ?", (end_time, session_id))
    logging.debug(f"Voting session closed: total_weight={total_weight}")
    return True, f"Voting session closed, results recorded for {len(votes)} votes"

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
        logging.debug("No active voting session found")
        return False
    active_employees = conn.execute(
        "SELECT COUNT(*) as count FROM employees WHERE active = 1 AND LOWER(role) != 'master'"
    ).fetchone()["count"]
    votes_cast = conn.execute(
        "SELECT COUNT(DISTINCT voter_initials) as count FROM votes WHERE vote_date >= ?",
        (session["start_time"],)
    ).fetchone()["count"]
    is_active = votes_cast < active_employees
    logging.debug(
        f"Voting active check: votes_cast={votes_cast}, active_employees={active_employees}, is_active={is_active}"
    )
    return is_active

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
            session_row = conn.execute(
                "SELECT session_id, start_time FROM voting_sessions WHERE end_time IS NULL"
            ).fetchone()
            if not session_row:
                logging.error("cast_votes: No active voting session found")
                return False, "Voting is not active"
            session_id = session_row["session_id"]

            # Prevent self-voting before recording participation
            voter_id = voter["employee_id"]
            if any(recipient_id == voter_id and value != 0 for recipient_id, value in votes.items()):
                logging.error(f"cast_votes: {voter_initials} attempted to vote for themselves")
                return False, "You cannot vote for yourself"

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

            try:
                conn.execute(
                    "INSERT INTO vote_participants (session_id, voter_initials) VALUES (?, ?)",
                    (session_id, voter_initials.lower())
                )
            except sqlite3.IntegrityError:
                logging.error(f"cast_votes: {voter_initials} has already voted in this session")
                return False, "You have already voted in this session"

            plus_votes = sum(1 for value in votes.values() if value > 0)
            minus_votes = sum(1 for value in votes.values() if value < 0)
            total_votes = plus_votes + minus_votes

            settings = get_settings(conn)
            max_plus = int(settings.get('max_plus_votes', 2))
            max_minus = int(settings.get('max_minus_votes', 3))
            max_total = int(settings.get('max_total_votes', 3))

            if plus_votes > max_plus:
                logging.error(f"cast_votes: Too many positive votes ({plus_votes}) from {voter_initials}")
                conn.execute(
                    "DELETE FROM vote_participants WHERE session_id = ? AND voter_initials = ?",
                    (session_id, voter_initials.lower())
                )
                return False, f"You can only cast up to {max_plus} positive (+1) votes per session"
            if minus_votes > max_minus:
                logging.error(f"cast_votes: Too many negative votes ({minus_votes}) from {voter_initials}")
                conn.execute(
                    "DELETE FROM vote_participants WHERE session_id = ? AND voter_initials = ?",
                    (session_id, voter_initials.lower())
                )
                return False, f"You can only cast up to {max_minus} negative (-1) votes per session"
            if total_votes > max_total:
                logging.error(f"cast_votes: Total votes ({total_votes}) exceeds limit from {voter_initials}")
                conn.execute(
                    "DELETE FROM vote_participants WHERE session_id = ? AND voter_initials = ?",
                    (session_id, voter_initials.lower())
                )
                return False, f"You can only cast a maximum of {max_total} votes total per session"

            for recipient_id, vote_value in votes.items():
                if not conn.execute("SELECT 1 FROM employees WHERE employee_id = ?", (recipient_id,)).fetchone():
                    logging.warning(f"Invalid recipient_id: {recipient_id}")
                    continue
                conn.execute(
                    "INSERT INTO votes (voter_initials, recipient_id, vote_value, vote_date) VALUES (?, ?, ?, ?)",
                    (voter_initials, recipient_id, vote_value, now.strftime("%Y-%m-%d %H:%M:%S"))
                )
                logging.debug(
                    f"Vote recorded: voter={voter_initials}, recipient={recipient_id}, value={vote_value}"
                )
        duration = time.time() - start_time
        logging.debug(f"Vote processing completed in {duration:.2f} seconds for {voter_initials}")
        return True, "JACKPOT VOTE CAST! MONEY INCOMING!"
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
            logging.warning("notes column missing in score_history, adding now")
            conn.execute("ALTER TABLE score_history ADD COLUMN notes TEXT DEFAULT ''")
            conn.execute(
                "INSERT INTO score_history (employee_id, changed_by, points, reason, notes, date, month_year) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (employee_id, admin_id, points, reason, notes, now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m"))
            )
        else:
            logging.error(f"Database error in adjust_points: {str(e)}\n{traceback.format_exc()}")
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
    conn.execute("DELETE FROM employees")
    conn.execute("DELETE FROM incentive_rules")
    conn.execute("DELETE FROM feedback")
    conn.execute("DELETE FROM point_decay")
    conn.execute("DELETE FROM incentive_pot")
    conn.execute("DELETE FROM roles")
    conn.execute("DELETE FROM settings")
    # Reinsert default incentive pot, roles, and settings
    conn.execute(
        "INSERT INTO incentive_pot (id, sales_dollars, bonus_percent, prior_year_sales) VALUES (1, 0.0, 0.0, 0.0)"
    )
    default_roles = [
        ("Driver", 50.0),
        ("Laborer", 40.0),
        ("Supervisor", 9.0),
        ("Warehouse Labor", 1.0),
        ("Master", 0.0),
    ]
    conn.executemany("INSERT INTO roles (role_name, percentage) VALUES (?, ?)", default_roles)
    default_settings = [
        (
            "voting_thresholds",
            '{"positive":[{"threshold":90,"points":10},{"threshold":60,"points":5},{"threshold":25,"points":2}],"negative":[{"threshold":90,"points":-10},{"threshold":60,"points":-5},{"threshold":25,"points":-2}]}',
        ),
        ("program_end_date", ""),
        ("last_decay_run", ""),
        ("max_total_votes", "3"),
        ("max_plus_votes", "2"),
        ("max_minus_votes", "3"),
        ("site_name", "A1 Rent-It"),
        ("site_title", "A1 Rent-It"),
        ("primary_color", "#D4AF37"),
        ("secondary_color", "#000000"),
        ("background_color", "#3A3A3A"),
        ("surface_color", "#222222"),
        ("surface_alt_color", "#1A1A1A"),
    ]
    conn.executemany("INSERT INTO settings (key, value) VALUES (?, ?)", default_settings)
    logging.debug(
        "Master reset: cleared votes, history, sessions, employees, rules, feedback, settings, pot, and roles"
    )
    return True, "All data reset to defaults"

def get_history(conn, month_year=None, day=None, employee_id=None, start_date=None, end_date=None):
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
    if start_date and end_date:
        where.append("substr(date, 1, 10) BETWEEN ? AND ?")
        params.extend([start_date, end_date])
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY date DESC"
    return conn.execute(query, params).fetchall()

def get_recent_admin_adjustments(conn, limit=10):
    """Return the most recent point adjustments made by admins."""
    try:
        rows = conn.execute(
            """
            SELECT sh.date, sh.points, sh.reason, sh.notes, e.name
            FROM score_history sh
            JOIN employees e ON sh.employee_id = e.employee_id
            WHERE sh.changed_by != 'system' AND sh.reason != 'Voting result'
            ORDER BY sh.date DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return rows
    except Exception as e:
        logging.error(f"Error fetching recent adjustments: {str(e)}\n{traceback.format_exc()}")
        return []

def get_rules(conn):
    try:
        return conn.execute(
            "SELECT description, points, details FROM incentive_rules ORDER BY display_order ASC"
        ).fetchall()
    except sqlite3.OperationalError as e:
        if "no such column: details" in str(e):
            logging.warning("details column missing, adding now")
            conn.execute("ALTER TABLE incentive_rules ADD COLUMN details TEXT DEFAULT ''")
            try:
                return conn.execute(
                    "SELECT description, points, details FROM incentive_rules ORDER BY display_order ASC"
                ).fetchall()
            except sqlite3.OperationalError as e2:
                if "no such column: display_order" in str(e2):
                    logging.warning(
                        "display_order column missing after adding details, falling back to unordered fetch"
                    )
                    return conn.execute(
                        "SELECT description, points, details FROM incentive_rules"
                    ).fetchall()
                raise
        if "no such column: display_order" in str(e):
            logging.warning("display_order column missing, falling back to unordered fetch")
            return conn.execute(
                "SELECT description, points, details FROM incentive_rules"
            ).fetchall()
        raise

def add_rule(conn, description, points, details=""):
    try:
        max_order = conn.execute("SELECT MAX(display_order) as max_order FROM incentive_rules").fetchone()["max_order"] or 0
        conn.execute(
            "INSERT INTO incentive_rules (description, points, details, display_order) VALUES (?, ?, ?, ?)",
            (description, points, details, max_order + 1)
        )
        logging.debug(f"Rule added: description={description}, points={points}, details={details}, display_order={max_order + 1}")
        return True, f"Rule '{description}' added with {points} points"
    except sqlite3.IntegrityError as e:
        if "UNIQUE constraint failed: incentive_rules.description" in str(e):
            logging.error(f"Failed to add rule: description '{description}' already exists")
            return False, f"Rule '{description}' already exists"
        logging.error(f"Database error in add_rule: {str(e)}\n{traceback.format_exc()}")
        return False, f"Failed to add rule due to database error: {str(e)}"
    except sqlite3.OperationalError as e:
        if "no such column: details" in str(e):
            logging.warning("details column missing, adding now")
            conn.execute("ALTER TABLE incentive_rules ADD COLUMN details TEXT DEFAULT ''")
            conn.execute(
                "INSERT INTO incentive_rules (description, points, details, display_order) VALUES (?, ?, ?, ?)",
                (description, points, details, max_order + 1)
            )
            logging.debug(f"Rule added after adding details column: description={description}, points={points}, details={details}")
            return True, f"Rule '{description}' added with {points} points"
        elif "no such column: display_order" in str(e):
            logging.warning("display_order column missing, inserting without order")
            conn.execute(
                "INSERT INTO incentive_rules (description, points, details) VALUES (?, ?, ?)",
                (description, points, details)
            )
            logging.debug(f"Rule added without display_order: description={description}, points={points}, details={details}")
            return True, f"Rule '{description}' added with {points} points"
        logging.error(f"Database error in add_rule: {str(e)}\n{traceback.format_exc()}")
        return False, f"Failed to add rule due to database error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error in add_rule: {str(e)}\n{traceback.format_exc()}")
        return False, f"Failed to add rule due to unexpected error: {str(e)}"


def edit_rule(conn, old_description, new_description, points, details):
    conn.execute(
        "UPDATE incentive_rules SET description = ?, points = ?, details = ? WHERE description = ?",
        (new_description, points, details, old_description)
    )
    affected = conn.total_changes
    return affected > 0, f"Rule '{old_description}' updated to '{new_description}' with {points} points" if affected > 0 else "Rule not found"

def remove_rule(conn, description):
    try:
        rule = conn.execute("SELECT rule_id, display_order FROM incentive_rules WHERE description = ?", (description,)).fetchone()
        if not rule:
            logging.error(f"Rule not found: description={description}")
            return False, f"Rule '{description}' not found"
        conn.execute("DELETE FROM incentive_rules WHERE description = ?", (description,))
        conn.execute("UPDATE incentive_rules SET display_order = display_order - 1 WHERE display_order > ?", 
                    (rule["display_order"],))
        conn.commit()
        logging.debug(f"Rule removed: description={description}, rule_id={rule['rule_id']}")
        return True, f"Rule '{description}' removed"
    except sqlite3.IntegrityError as e:
        logging.error(f"Integrity error in remove_rule: {str(e)}\n{traceback.format_exc()}")
        return False, f"Failed to remove rule due to database integrity error: {str(e)}"
    except Exception as e:
        logging.error(f"Unexpected error in remove_rule: {str(e)}\n{traceback.format_exc()}")
        return False, f"Failed to remove rule due to error: {str(e)}"


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
    global _pot_cache, _pot_cache_timestamp
    start_time = time.time()
    try:
        if _pot_cache and _pot_cache_timestamp and (time.time() - _pot_cache_timestamp) < _POT_CACHE_DURATION:
            logging.debug(f"Returning cached pot info in {time.time() - start_time:.2f} seconds")
            return _pot_cache
        pot_row = conn.execute("SELECT sales_dollars, bonus_percent, prior_year_sales FROM incentive_pot WHERE id = 1").fetchone()
        pot = dict(pot_row) if pot_row else {"sales_dollars": 0.0, "bonus_percent": 0.0, "prior_year_sales": 0.0}
        roles = get_roles(conn)
        role_counts = {}
        for role in roles:
            role_name = role["role_name"]
            role_counts[role_name] = conn.execute(
                "SELECT COUNT(*) as count FROM employees WHERE role = ? AND active = 1",
                (role_name.lower(),)
            ).fetchone()["count"] or 1
        total_pot = pot["sales_dollars"] * pot["bonus_percent"] / 100
        prior_year_total_pot = pot["prior_year_sales"] * pot["bonus_percent"] / 100
        max_points_per_employee = 100
        for role in roles:
            role_name = role["role_name"]
            key = role_name.lower().replace(" ", "_")
            pot[f"{key}_percent"] = role["percentage"] if role_name.lower() != "master" else 0.0
            role_percent = pot[f"{key}_percent"]
            role_pot = total_pot * role_percent / 100
            role_max_points = role_counts[role_name] * max_points_per_employee
            role_point_value = role_pot / role_max_points if role_max_points > 0 else 0
            pot[f"{key}_pot"] = role_pot
            pot[f"{key}_point_value"] = role_point_value
            role_prior_year_pot = prior_year_total_pot * role_percent / 100
            role_prior_year_point_value = role_prior_year_pot / role_max_points if role_max_points > 0 else 0
            pot[f"{key}_prior_year_pot"] = role_prior_year_pot
            pot[f"{key}_prior_year_point_value"] = role_prior_year_point_value
        _pot_cache = pot
        _pot_cache_timestamp = time.time()
        logging.debug(f"Pot info retrieved in {time.time() - start_time:.2f} seconds: {pot}")
        return pot
    except Exception as e:
        logging.error(f"Error in get_pot_info: {str(e)}\n{traceback.format_exc()}")
        raise

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
    """Retrieve voting results with scoreboard points applied via thresholds."""
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0).strftime("%Y-%m-%d %H:%M:%S")
    end_of_month = (now.replace(day=1, month=now.month + 1) - timedelta(days=1)).replace(
        hour=23, minute=59, second=59
    ).strftime("%Y-%m-%d %H:%M:%S")

    base_query = (
        "SELECT strftime('%W', vs.start_time) AS week_number, "
        "e.name AS recipient_name, vr.plus_votes, vr.minus_votes, vr.points "
        "FROM voting_results vr "
        "JOIN voting_sessions vs ON vr.session_id = vs.session_id "
        "JOIN employees e ON vr.employee_id = e.employee_id "
        "WHERE vs.start_time >= ? AND vs.start_time <= ?"
    )
    params = [start_of_month, end_of_month]

    if week_number is not None:
        base_query += " AND strftime('%W', vs.start_time) = ?"
        params.append(f"{week_number:02d}")

    base_query += " ORDER BY week_number DESC, e.name"
    results = conn.execute(base_query, params).fetchall()
    logging.debug(
        f"Voting results fetched: {len(results)} entries for {'admin' if is_admin else 'non-admin'} view"
    )
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
    try:
        logging.debug(f"set_point_decay input: role_name={role_name}, points={points}, days={days}")
        valid_days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        days = [d for d in days if d in valid_days]
        days_json = json.dumps(days)
        conn.execute(
            "INSERT OR REPLACE INTO point_decay (id, role_name, points, days) VALUES ((SELECT id FROM point_decay WHERE role_name = ?), ?, ?, ?)",
            (role_name, role_name, points, days_json)
        )
        logging.debug(f"Point decay set: role_name={role_name}, points={points}, days={days_json}")
        return True, f"Point decay for {role_name} set to {points} points on {days if days else '[]'}"
    except Exception as e:
        logging.error(f"Error in set_point_decay: {str(e)}\n{traceback.format_exc()}")
        return False, f"Failed to set point decay due to error: {str(e)}"

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
        if 'max_total_votes' not in settings:
            set_settings(conn, 'max_total_votes', '3')
            settings['max_total_votes'] = '3'
        if 'max_plus_votes' not in settings:
            set_settings(conn, 'max_plus_votes', '2')
            settings['max_plus_votes'] = '2'
        if 'max_minus_votes' not in settings:
            set_settings(conn, 'max_minus_votes', '3')
            settings['max_minus_votes'] = '3'
        if 'role_vote_weights' not in settings:
            set_settings(conn, 'role_vote_weights', '{}')
            settings['role_vote_weights'] = '{}'
        if 'site_name' not in settings:
            set_settings(conn, 'site_name', 'A1 Rent-It')
            settings['site_name'] = 'A1 Rent-It'
        if 'site_title' not in settings:
            set_settings(conn, 'site_title', 'A1 Rent-It')
            settings['site_title'] = 'A1 Rent-It'
        if 'primary_color' not in settings:
            set_settings(conn, 'primary_color', '#D4AF37')
            settings['primary_color'] = '#D4AF37'
        if 'secondary_color' not in settings:
            set_settings(conn, 'secondary_color', '#000000')
            settings['secondary_color'] = '#000000'
        if 'background_color' not in settings:
            set_settings(conn, 'background_color', '#3A3A3A')
            settings['background_color'] = '#3A3A3A'
        if 'surface_color' not in settings:
            set_settings(conn, 'surface_color', '#222222')
            settings['surface_color'] = '#222222'
        if 'surface_alt_color' not in settings:
            set_settings(conn, 'surface_alt_color', '#1A1A1A')
            settings['surface_alt_color'] = '#1A1A1A'
        if 'money_threshold' not in settings:
            set_settings(conn, 'money_threshold', '50')
            settings['money_threshold'] = '50'
        if 'score_top_color' not in settings:
            set_settings(conn, 'score_top_color', '#D4AF37')
            settings['score_top_color'] = '#D4AF37'
        if 'score_mid_color' not in settings:
            set_settings(conn, 'score_mid_color', '#FFFFFF')
            settings['score_mid_color'] = '#FFFFFF'
        if 'score_bottom_color' not in settings:
            set_settings(conn, 'score_bottom_color', '#FF6347')
            settings['score_bottom_color'] = '#FF6347'
        if 'scoreboard_spin_duration' not in settings:
            set_settings(conn, 'scoreboard_spin_duration', '10')
            settings['scoreboard_spin_duration'] = '10'
        if 'scoreboard_spin_iterations' not in settings:
            set_settings(conn, 'scoreboard_spin_iterations', '0')
            settings['scoreboard_spin_iterations'] = '0'
        if 'scoreboard_spin_pause' not in settings:
            set_settings(conn, 'scoreboard_spin_pause', '0')
            settings['scoreboard_spin_pause'] = '0'
        if 'scoreboard_refresh_interval' not in settings:
            set_settings(conn, 'scoreboard_refresh_interval', '60')
            settings['scoreboard_refresh_interval'] = '60'
        for section in Config.ADMIN_SECTIONS:
            key = f'allow_section_{section}'
            if key not in settings:
                set_settings(conn, key, '0')
                settings[key] = '0'
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