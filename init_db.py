# init_db.py
# Version: 1.2.5
# Note: Included default vote limit settings. Compatible with app.py (1.2.111), incentive_service.py (1.2.29), forms.py (1.2.21), settings.html (1.2.8), incentive.html (1.2.48), script.js (1.2.89).

import sqlite3
from config import Config
from werkzeug.security import generate_password_hash
import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

def initialize_incentive_db():
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    cursor = conn.cursor()

    # Create employees table
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

    # Create votes table
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

    # Create voting_sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS voting_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            vote_code TEXT,
            admin_id TEXT,
            start_time TEXT,
            end_time TEXT
        )
    """)

    # Create admins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            admin_id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Add is_master column if it doesn't exist
    try:
        cursor.execute("SELECT is_master FROM admins LIMIT 1")
    except sqlite3.OperationalError as e:
        if "no such column: is_master" in str(e):
            logging.debug("Adding is_master column to admins table")
            cursor.execute("ALTER TABLE admins ADD COLUMN is_master INTEGER DEFAULT 0")
            # Set is_master=1 for the master admin
            cursor.execute("UPDATE admins SET is_master = 1 WHERE admin_id = 'master'")
        else:
            raise

    # Insert default admins
    admins = [
        ("admin1", "admin1", generate_password_hash("Broadway8101"), 0),
        ("admin2", "admin2", generate_password_hash("Broadway8101"), 0),
        ("admin3", "admin3", generate_password_hash("Broadway8101"), 0),
        ("master", "master", generate_password_hash("Master8101"), 1)
    ]
    cursor.executemany("INSERT OR IGNORE INTO admins (admin_id, username, password, is_master) VALUES (?, ?, ?, ?)", admins)

    # Create score_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS score_history (
            history_id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT,
            changed_by TEXT,
            points INTEGER,
            reason TEXT,
            notes TEXT DEFAULT '',
            date TEXT,
            month_year TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    # Create incentive_rules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_rules (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL UNIQUE,
            points INTEGER NOT NULL,
            details TEXT DEFAULT '',
            display_order INTEGER DEFAULT 0
        )
    """)

    # Create incentive_pot table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_pot (
            id INTEGER PRIMARY KEY,
            sales_dollars REAL DEFAULT 0.0,
            bonus_percent REAL DEFAULT 0.0,
            prior_year_sales REAL DEFAULT 0.0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO incentive_pot (id, sales_dollars, bonus_percent, prior_year_sales) VALUES (1, 0.0, 0.0, 0.0)")

    # Create roles table with default roles
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
        ("Master", 0.0)  # Master role with 0% pot allocation
    ]
    cursor.executemany("INSERT OR IGNORE INTO roles (role_name, percentage) VALUES (?, ?)", default_roles)

    # Create point_decay table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS point_decay (
            id INTEGER PRIMARY KEY,
            role_name TEXT NOT NULL,
            points INTEGER NOT NULL,
            days TEXT NOT NULL,
            UNIQUE(role_name)
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

    # Create voting_results table
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

    # Create feedback table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            comment TEXT,
            submitter TEXT,
            timestamp TEXT,
            read INTEGER DEFAULT 0
        )
    """)

    # Create settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    default_settings = [
        ('voting_thresholds', '{"positive":[{"threshold":90,"points":10},{"threshold":60,"points":5},{"threshold":25,"points":2}],"negative":[{"threshold":90,"points":-10},{"threshold":60,"points":-5},{"threshold":25,"points":-2}]}'),
        ('program_end_date', ''),
        ('last_decay_run', ''),
        ('max_total_votes', '3'),
        ('max_plus_votes', '2'),
        ('max_minus_votes', '3')
    ]
    cursor.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings)

    conn.commit()
    conn.close()
    logging.debug("Incentive database initialized at %s", Config.INCENTIVE_DB_FILE)
    print("Incentive database initialized at", Config.INCENTIVE_DB_FILE)

if __name__ == "__main__":
    initialize_incentive_db()