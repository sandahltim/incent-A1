# -rfidpiA1 Rent-It Incentive Program
Overview
The A1 Rent-It Incentive Program is a web-based application designed to manage an employee incentive system for A1 Rent-It. Employees earn points based on performance, voting, and predefined rules, contributing to a share of an incentive pot derived from company sales. The application supports role-based point allocation, weekly voting, point decay, and administrative management. It is optimized for deployment on a Raspberry Pi, ensuring plug-and-play integration into A1 Rent-It's network with easy updates via Git. The interface uses a Golden Yellow (#FFC107) and Black (#000000) color scheme to align with A1 Rent-It's branding.
Repository

GitHub Repository: https://github.com/sandahltim/incent-A1.git
Primary Maintainer: Tim Sandahl

Features

Employee Management: Add, edit, retire, reactivate, or delete employees with unique IDs, names, initials, roles, and scores.
Incentive Pot: Allocate bonuses based on sales dollars, bonus percentage, and role-specific percentages (e.g., Driver, Laborer, Supervisor, Warehouse Labor).
Point System: Employees start with 50 points, adjustable via admin actions, voting, or daily decay. Scores are capped between 0 and 100.
Weekly Voting: Employees cast up to 2 positive (+1) and 3 negative (-1) votes weekly, with points awarded based on vote percentages (e.g., +10 for >90% positive votes).
Point Decay: Configurable daily point deductions per role, triggered on specific days.
Rules Management: Define positive or negative point rules for manual adjustments.
Role Management: Manage roles with percentage allocations for the incentive pot, ensuring the total does not exceed 100%.
Admin Interface: Secure admin access for managing employees, rules, roles, pot, decay, and admins (master only).
Voting Results: Display results for admins (detailed) and employees (weekly summary).
History Tracking: Log all point changes with reasons and timestamps.
Raspberry Pi Deployment: Plug-and-play setup with automatic network configuration and easy updates via Git.

Technology Stack

Backend: Python 3, Flask 2.2.5, SQLite3
Frontend: HTML, Jinja2 templates, CSS (Golden Yellow and Black theme)
Server: Gunicorn 23.0.0 with 4 workers
Dependencies: See requirements.txt for full list
Database: SQLite (incentive.db)
Deployment Platform: Raspberry Pi (Raspberry Pi OS)
Version Control: Git, hosted on GitHub

Installation and Setup
Prerequisites

Raspberry Pi (Model 3 or later recommended) with Raspberry Pi OS (latest version)
Internet connection for initial setup
Git installed (sudo apt install git)
Python 3.8+ (sudo apt install python3 python3-pip python3-venv)
SQLite3 (sudo apt install sqlite3)
Access to A1 Rent-It's network

Setup Instructions

Clone the Repository
git clone https://github.com/sandahltim/incent-A1.git
cd incent-A1


Run the Installation Script

The install.sh script sets up the virtual environment, installs dependencies, initializes the database, and configures the start script.

chmod +x install.sh
./install.sh


Output includes the URL (http://<pi-ip>:6800/) and default master admin credentials (username: master, password: Master8101).


Verify Database Creation

Ensure incentive.db is created in the project directory:ls -l /home/tim/incent-A1/incentive.db


If missing, check permissions and run:chmod -R u+rw /home/tim/incent-A1
source venv/bin/activate
python init_db.py




Network Configuration

Connect the Raspberry Pi to A1 Rent-It's network (Ethernet or Wi-Fi).
The application binds to 0.0.0.0:6800. Retrieve the Pi's IP address:hostname -I


For a static IP, edit /etc/dhcpcd.conf:sudo nano /etc/dhcpcd.conf

Add:interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8

Adjust IP addresses to match the network. Restart networking:sudo systemctl restart dhcpcd




Start the Application

Run the start script:chmod +x start.sh
./start.sh


Access at http://<pi-ip>:6800/.


Automatic Startup (Optional)

Add to crontab for boot startup:crontab -e

Add:@reboot /home/tim/incent-A1/start.sh





Updating the Application

Pull Updates:cd /home/tim/incent-A1
git pull origin main


Update Dependencies:source venv/bin/activate
pip install -r requirements.txt


Restart the Server:pkill gunicorn
./start.sh


Database Migrations:
init_db.py uses IF NOT EXISTS to preserve data. Run manually for schema changes:python init_db.py





File Structure

app.py: Flask application with routes for incentive, admin, voting, and data endpoints.
incentive_service.py: Backend logic for database operations, voting, and point calculations.
init_db.py: Initializes incentive.db with tables for employees, votes, sessions, admins, rules, roles, pot, decay, and history.
config.py: Configuration with dynamic database path and voting settings.
install.sh: Sets up virtual environment, dependencies, and database.
start.sh: Starts the Gunicorn server.
requirements.txt: Python dependencies.
templates/:
base.html: Base template with navigation (Golden Yellow and Black).
incentive.html: Public page with scoreboard, rules, pot, and voting.
admin_manage.html: Admin interface for management tasks.
admin_login.html: Admin login page.
start_voting.html: Voting session start page.
history.html: Point change history page.


static/style.css: CSS with A1 Rent-It branding (Golden Yellow and Black).

Database Schema

employees: (employee_id, name, initials, score, role, active, last_decay_date)
votes: (vote_id, voter_initials, recipient_id, vote_value, vote_date)
voting_sessions: (session_id, vote_code, admin_id, start_time, end_time)
admins: (admin_id, username, password)
score_history: (history_id, employee_id, changed_by, points, reason, date, month_year)
incentive_rules: (rule_id, description, points, display_order)
incentive_pot: (id, sales_dollars, bonus_percent, prior_year_sales, role percentages)
roles: (role_name, percentage)
point_decay: (id, role_name, points, days)
voting_results: (session_id, employee_id, plus_votes, minus_votes, plus_percent, minus_percent, points)

Usage

Access: http://<pi-ip>:6800/
Public Interface (incentive.html):
View scoreboard, rules, pot details.
Cast votes (requires initials).
View weekly voting results (+1/-1 counts).


Admin Interface (admin_manage.html):
Login with credentials (e.g., master/Master8101).
Manage employees, rules, roles, pot, decay, admins (master only).
Control voting sessions.
Reset scores or master reset (master only).


Voting: Weekly, with 2 positive and 3 negative vote limits.
Point Decay: Role-based, applied daily on specified days.

Styling

Colors:
Golden Yellow (#FFC107): Headers, buttons, highlights.
Black (#000000, #333333): Backgrounds, text, borders.


CSS: static/style.css implements the color scheme with responsive design.
Responsive Design: Mobile-friendly for tablets/phones.

Security

Admin Access: Hashed passwords (werkzeug.security).
Session Management: Flask sessions with secret key.
Vote Validation: Ensures active sessions and vote limits.
Master Account: Required for critical actions.

Maintenance

Backups:cp incentive.db incentive_backup_$(date +%F).db


Logs:journalctl -u gunicorn


Dependency Updates:pip install -r requirements.txt



Troubleshooting

Database Error (unable to open database file):
Verify incentive.db path in config.py.
Ensure directory permissions: chmod -R u+rw /home/tim/incent-A1.
Reinitialize: python init_db.py.


Server Not Starting:
Check start.sh permissions: chmod +x start.sh.
View logs: journalctl -u gunicorn.


Network Issues:
Confirm IP: hostname -I.
Check firewall: sudo ufw status.


Voting Not Active:
Start session via admin interface.
Verify VOTING_DAYS_2025 in config.py.



Future Improvements

Add client-side JavaScript for real-time scoreboard updates.
Implement CSRF protection for forms.
Enhance mobile responsiveness in CSS.
Add database backup/restore functionality.
Support multiple voting sessions per week if needed.

Contact
For issues or contributions, use GitHub.



## start.sh
#!/bin/bash
source venv/bin/activate
gunicorn --workers 4 --timeout 180 --bind 0.0.0.0:6800 app:app


## init_db.py
import sqlite3
from config import INCENTIVE_DB_FILE
from werkzeug.security import generate_password_hash

def initialize_incentive_db():
    conn = sqlite3.connect(INCENTIVE_DB_FILE)
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
            date TEXT,
            month_year TEXT,
            FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS incentive_rules (
            rule_id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            points INTEGER NOT NULL,
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
            laborer_percent REAL DEFAULT 50.0,
            supervisor_percent REAL DEFAULT 0.0
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO incentive_pot (id, sales_dollars, bonus_percent, prior_year_sales, driver_percent, laborer_percent, supervisor_percent) VALUES (1, 0.0, 0.0, 0.0, 50.0, 50.0, 0.0)")

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
        ("Warehouse Labor", 1.0)
    ]
    cursor.executemany("INSERT OR IGNORE INTO roles (role_name, percentage) VALUES (?, ?)", default_roles)

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
        ("Warehouse Labor", 1, '[]')
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

    conn.commit()
    conn.close()
    print("Incentive database initialized at", INCENTIVE_DB_FILE)

if __name__ == "__main__":
    initialize_incentive_db()


## config.py ?needs work?
import os

# Use the project directory for the database file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INCENTIVE_DB_FILE = os.path.join(BASE_DIR, "incentive.db")
VOTE_CODE = "A1RentIt2025"  # Updated for A1 Rent-It
VOTING_DAYS_2025 = [
    "2025-01-01", "2025-01-08", "2025-01-15", "2025-01-22", "2025-01-29",
    "2025-02-05", "2025-02-12", "2025-02-19", "2025-02-26",
    "2025-03-05", "2025-03-12", "2025-03-19", "2025-03-26",
    "2025-04-02", "2025-04-09", "2025-04-16", "2025-04-23", "2025-04-30",
    # Add more Wednesdays as needed
]


# requirements.txt
# Version: 1.1.0
# Note: Added pandas and matplotlib for data export and charts in improvements 5/6.

certifi==2025.1.31
charset-normalizer==3.4.1
click==8.1.8
colorama==0.4.6
Flask==2.2.5
Flask-WTF==1.2.1  # Added for CSRF protection
gunicorn==23.0.0
idna==3.10
importlib-metadata==6.7.0
itsdangerous==2.1.2
Jinja2==3.1.4
MarkupSafe==2.1.5
requests==2.31.0
typing_extensions==4.7.1
urllib3==2.0.7
Werkzeug==2.2.3
WTForms==3.1.2  # Added as dependency for Flask-WTF
zipp==3.15.0
pandas==2.2.2
matplotlib==3.9.1