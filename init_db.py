# init_db.py
# Version: 1.2.3
# Note: Restored voting_sessions, voting_results, and last_decay_date from 1.2.2 to maintain voting and point decay functionality. Added Master role with 0% pot allocation and enforced 6-role limit (including Supervisor and Master). Removed Mechanic and Warehouse roles, keeping Driver, Laborer, Supervisor, Warehouse Labor, and Master. Ensured compatibility with app.py (1.2.78), incentive_service.py (1.2.22), forms.py (1.2.7), config.py (1.2.6), admin_manage.html (1.2.32), incentive.html (1.2.27), quick_adjust.html (1.2.11), script.js (1.2.58), style.css (1.2.17), base.html (1.2.21), macros.html (1.2.10), start_voting.html (1.2.7), settings.html (1.2.6), admin_login.html (1.2.5), history.html (1.2.6), error.html. No removal of core functionality.

import sqlite3
from config import Config
from werkzeug.security import generate_password_hash

def initialize_incentive_db():
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS employees (
            employee_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            initials TEXT UNIQUE NOT NULL,
            score INTEGER DEFAULT 50,
            role TEXT,
            active INTEGER DEFAULT 1,
            last_decay_date TEXT DEFAULT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS votes (
            vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_initials TEXT,
            recipient_id TEXT,
            vote_value INTEGER CHECK(vote_value IN (-1, 0, 1)),
            vote_date TEXT,
            UNIQUE(voter_initials, recipient_id, vote_date),
            FOREIGN KEY(recipient_id) REFERENCES employees(employee_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voting_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_code TEXT,
            admin_id TEXT,
            start_time TEXT,
            end_time TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    admins = [
        ("admin1", "admin1", generate_password_hash("Broadway8101")),
        ("admin2", "admin2", generate_password_hash("Broadway8101")),
        ("admin3", "admin3", generate_password_hash("Broadway8101")),
        ("master", "master", generate_password_hash("Master8101"))
    ]
    cursor.executemany("INSERT OR IGNORE INTO admins (admin_id, username, password) VALUES (?, ?, ?)", admins)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS score_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            changed_by TEXT,
            points INTEGER,
            reason TEXT,
            notes TEXT,
            date TEXT,
            month_year TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_rules (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL UNIQUE,
            points INTEGER NOT NULL,
            details TEXT,
            display_order INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_pot (
            id INTEGER PRIMARY KEY,
            sales_dollars REAL DEFAULT 0.0,
            bonus_percent REAL DEFAULT 0.0,
            prior_year_sales REAL DEFAULT 0.0,
            driver_percent REAL DEFAULT 50.0,
            laborer_percent REAL DEFAULT 40.0,
            supervisor_percent REAL DEFAULT 9.0,
            warehouse_labor_percent REAL DEFAULT 1.0,
            master_percent REAL DEFAULT 0.0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO incentive_pot (id, sales_dollars, bonus_percent, prior_year_sales, driver_percent, laborer_percent, supervisor_percent, warehouse_labor_percent, master_percent) VALUES (1, 10000.0, 10.0, 50000.0, 50.0, 40.0, 9.0, 1.0, 0.0)")

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS roles (
            role_name TEXT PRIMARY KEY,
            percentage REAL
        )
    """)
    default_roles = [
        ("Driver", 50.0),
        ("Laborer", 40.0),
        ("Supervisor", 9.0),
        ("Warehouse Labor", 1.0),
        ("Master", 0.0)
    ]
    existing_roles = cursor.execute("SELECT role_name FROM roles").fetchall()
    existing_role_names = [row['role_name'] for row in existing_roles]
    for role_name, percentage in default_roles:
        if role_name not in existing_role_names and len(existing_role_names) < 6:
            cursor.execute('INSERT INTO roles (role_name, percentage) VALUES (?, ?)', (role_name, percentage))

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS point_decay (
            id INTEGER PRIMARY KEY,
            role_name TEXT NOT NULL,
            points INTEGER NOT NULL,
            days TEXT NOT NULL,
            UNIQUE(role_name),
            FOREIGN KEY (role_name) REFERENCES roles(role_name)
        )
    """)
    default_decay = [
        ("Driver", 1, '[]'),
        ("Laborer", 1, '[]'),
        ("Supervisor", 1, '[]'),
        ("Warehouse Labor", 1, '[]'),
        ("Master", 1, '[]')
    ]
    cursor.executemany("INSERT OR IGNORE INTO point_decay (id, role_name, points, days) VALUES (?, ?, ?, ?)", 
                      [(i+1, role, points, days) for i, (role, points, days) in enumerate(default_decay)])

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voting_results (
            session_id INTEGER,
            employee_id TEXT,
            plus_votes INTEGER,
            minus_votes INTEGER,
            plus_percent REAL,
            minus_percent REAL,
            points INTEGER,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment TEXT,
            submitter TEXT,
            timestamp TEXT,
            read INTEGER DEFAULT 0
        )
    """)

    conn.commit()
    conn.close()
    print("Incentive database initialized at", Config.INCENTIVE_DB_FILE)

if __name__ == "__main__":
    initialize_incentive_db()