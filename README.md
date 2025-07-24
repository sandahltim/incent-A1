# Broadway Tent & Event Incentive Program (Internal Documentation)

**Repository:** [github.com/sandahltim/incentive](https://github.com/sandahltim/incentive)  
**Maintainer:** Tim Sandahl  
**For Internal Use Only**  
_Last updated: 2025-07-21_

---

## Table of Contents
- [Project Overview](#project-overview)
- [Features](#features)
- [Security & Roles](#security--roles)
- [Database Structure](#database-structure)
- [File/Folder Structure](#filefolder-structure)
- [Setup & Installation](#setup--installation)
- [Configuration & Environment](#configuration--environment)
- [Process Flows & Usage](#process-flows--usage)
- [Admin Operations](#admin-operations)
- [Settings Management](#settings-management)
- [Voting & Points System](#voting--points-system)
- [Manual Adjustments](#manual-adjustments)
- [Automation: Point Decay & Program End](#automation-point-decay--program-end)
- [Export, Import, and Backup](#export-import-and-backup)
- [Versioning & Upgrade Notes](#versioning--upgrade-notes)
- [Known Users/Admins](#known-usersadmins)
- [Support](#support)
- [FAQ / Key Internal Questions](#faq--key-internal-questions)

---

## Project Overview

A Flask-based, point-driven employee incentive and peer-voting system for Broadway Tent & Event.  
Tracks employee performance, enables weekly peer voting, allows admin point adjustments, and computes payouts based on role and performance.  
Designed for secure internal deployment with admin and master-admin roles.

---

## Features

- **Weekly Voting Sessions** (peer recognition, positive or negative)
- **Admin Panel**:  
    - Adjust employee points (add/remove)
    - Add/edit/remove point rules
    - Add/retire/reactivate/delete employees
    - Edit job roles and their payout shares
    - Configure incentive pot (sales, bonus %)
    - Set daily point decay per role and day
    - View/mark feedback submissions
    - Export all or monthly payout data
    - Start, pause, and end voting sessions
    - Master admin: Add/remove admins, reset program, manage app settings
- **Point Rules Engine** (standardized or custom reasons for point changes)
- **Daily Point Decay** (scheduled automatic deductions by role and weekday)
- **Responsive Bootstrap UI**
- **Feedback System** (user comments, admin review)
- **Settings Management** (JSON, paths, dates via web UI)
- **CSV Data Export**
- **Backup/Restore with custom path**
- **User authentication & access control**
- **Audit logging for all adjustments and voting actions**

---

## Security & Roles

- **Master Admin:**  
  - Can do everything (users, settings, program resets, backups, add/remove admins, set end dates).
- **Admin:**  
  - Can manage employees, voting, points, rules, feedback, export data.
  - Cannot manage other admins or change global settings.
- **Employee:**  
  - Can vote, view scores/history, submit feedback.

- **Logins:**  
  - Admin login at `/admin_login` (passwords hashed in DB)
  - Voting is authenticated by initials

---

## Database Structure

| Table            | Key Columns / Description                                                                    |
|------------------|---------------------------------------------------------------------------------------------|
| `employees`      | `employee_id (PK)`, `name`, `initials (unique)`, `role`, `score`, `active`                  |
| `admins`         | `admin_id (PK)`, `username (unique)`, `password_hash`, `is_master`                          |
| `rules`          | `id (PK)`, `description (unique)`, `points`                                                 |
| `roles`          | `role_name (PK)`, `percentage`                                                              |
| `pot_info`       | `key (PK)`, `value` (JSON/text: e.g. sales, bonus %, etc.)                                  |
| `voting_results` | `id (PK)`, `session_id`, `voter_initials`, `recipient_name`, `vote_value`, `vote_date`, `points`, `week_number` |
| `feedback`       | `id (PK)`, `submitter`, `comment`, `timestamp`, `read`                                      |
| `settings`       | `key (PK)`, `value` (text/JSON, e.g. thresholds, backup path, program end date)             |

**Key Notes:**
- All critical settings (thresholds, backup path, end date) are stored in `settings`.
- All voting/adjustments logged with timestamps.
- Payout calculations use employee `score`, role `percentage`, and `pot_info` metrics.

---

## File/Folder Structure

project-root/
├── app.py # Main Flask application logic/routing
├── config.py # Global configuration (DB path, etc.)
├── forms.py # WTForms (field/validation definitions)
├── incentive_service.py # Core business logic
├── requirements.txt # (optional) Python dependencies
├── README.md # This file (internal documentation)
├── templates/ # Jinja2 HTML templates
│ ├── base.html
│ ├── admin_login.html
│ ├── admin_manage.html
│ ├── macros.html
│ ├── incentive.html
│ ├── quick_adjust.html
│ ├── history.html
│ ├── start_voting.html
│ └── settings.html
├── static/
│ ├── style.css
│ └── script.js
└── <db-file>.db # SQLite3 database (default: incentive.db)



---

## Setup & Installation

```bash
# 1. Clone repo and enter directory
git clone https://github.com/sandahltim/incentive.git
cd incentive

# 2. Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set config as needed in config.py (default DB: incentive.db)

# 5. Start the application (dev mode)
flask run

# OR for production
gunicorn -w 4 -b 0.0.0.0:8000 app:app
Database tables will be auto-created on first run if not found.

Configuration & Environment
All runtime settings live in the settings table and are modifiable from the admin settings UI.

backup_path — File system location for DB/file backups

voting_thresholds — JSON string (see below for format)

program_end_date — YYYY-MM-DD string

config.py for DB paths, environment-specific overrides.

Process Flows & Usage
Employee Usage
Vote for peers (once per session, +1 or -1), tracked by initials

Check own score, role, and standing on main interface

Submit feedback

Admin Usage
Login at /admin_login

Adjust points, add/remove rules, reset scores, manage voting sessions

Add/edit/retire/reactivate/delete employees

Edit payout metrics (sales, bonus %, prior year sales, roles)

Export payout and voting data

Manage feedback and read status

Master Admin Usage
All admin features, plus:

Add/remove other admins, change usernames/passwords

Edit voting thresholds, backup path, and end date

Run a master reset (erases history, resets scores/settings)

Admin Operations
Key Panels/Functions:

Adjust Points: Manual change to employee score (positive or negative), logged with reason.

Points Rules: Admins can define rules for common adjustments. Used in both voting and admin forms.

Manage Employees: Add, update, retire, reactivate, or fully delete employee records.

Voting Controls: Open, pause, close, or end voting sessions for a week.

Payout Settings: Edit pot sales, bonus percent, role shares.

Daily Point Decay: Automatic deduction by role and day.

Feedback Panel: Mark feedback as read; audit all comments.

Data Export: Download all or filtered (monthly) CSV data.

Settings Panel: (master only) Edit backup, thresholds, end date.

Settings Management
Backup Path: Set location for DB or data backups.

Voting Thresholds:
Example JSON (set in settings table):

json
Copy
Edit
{
  "positive": [
    {"threshold": 90, "points": 10},
    {"threshold": 60, "points": 5},
    {"threshold": 25, "points": 2}
  ],
  "negative": [
    {"threshold": 90, "points": -10},
    {"threshold": 60, "points": -5},
    {"threshold": 25, "points": -2}
  ]
}
Program End Date:
String: "YYYY-MM-DD" — after this, voting/payouts are locked.

Settings can be changed ONLY by master admin via /settings.

Voting & Points System
Weekly voting sessions:

Opened/closed by admin.

Each user votes for others by initials.

Each vote is +1 (positive) or -1 (negative).

Voting thresholds:

Points awarded/deducted based on thresholds in settings (see above).

Voting session management:

Open new session (start_voting.html)

Pause or end session from admin panel.

Audit logging:

All voting stored in voting_results, with session ID, date, and points.

Manual adjustments:

Immediate, can be positive or negative, and must include a reason.

Manual Adjustments
Quick Adjust panel (password required) for rapid, secure changes.

Each adjustment is:

Logged with admin username, employee, amount, and reason.

Can be tied to a rule or entered as custom text.

Automation: Point Decay & Program End
Daily Point Decay:

Configured by role and day via admin panel.

Deducts N points per day/role, e.g., drivers lose 1 point per Monday.

End of Program:

System can lock voting and payout after set date.

Export, Import, and Backup
CSV Export:

Export all data or current month from admin panel.

Includes payout data and voting history.

Full Backup:

Use backup path setting (default or custom).

Copy SQLite DB file for full system backup.

Restore:

Replace database file, restart Flask/Gunicorn.

Versioning & Upgrade Notes
All major code files/templates have version comments at the top (e.g., # Version: 1.2.2).

On structural updates, update README, version in code headers, and note in GitHub if possible.

No auto-upgrade scripts; upgrades should be planned and manual.

Known Users/Admins
Master Admin Username: master

Password: (set at setup, or see admins table in DB)Master8101

Other Admins: Add/remove/edit from admin panel (master only).

Support
Internal project — Contact Tim Sandahl for codebase, DB issues, or feature requests.

All user and admin feedback is logged via UI.

FAQ / Key Internal Questions
Q1:
How can new roles, rules, or voting thresholds be safely added or changed, and what areas of the application do they affect?

A:
Use the admin UI to add roles/rules; changes are instant and affect all related payout calculations and voting/adjustment forms. Voting thresholds are JSON in settings and affect points awarded for voting.

Q2:
What’s the process and impact of performing a master reset, and which data or settings are preserved or erased?

A:
Master reset (admin panel): erases all voting history, resets all employee scores to baseline, wipes payout history, and resets settings to defaults. User/admin accounts are preserved but all operational data is wiped.

Q3:
How does the daily point decay feature interact with employee roles and voting, and how is it configured or overridden?

A:
Decay is set by role and day; deducted points apply daily on specified days for each role (e.g., "Laborer" -1 on Friday). Configurable via admin panel; changes take effect immediately.


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


## config.py 
# config.py
# Version: 1.2.5
# Note: Added Config class to fix ImportStringError in app.py (version 1.2.34) due to missing 'config.Config'. Moved existing variables (BASE_DIR, INCENTIVE_DB_FILE, SECRET_KEY, VOTE_CODE) into Config class as attributes. Ensured compatibility with app.py (version 1.2.34), incentive_service.py (1.2.8), forms.py (1.2.2), incentive.html (1.2.17), admin_manage.html (1.2.16), quick_adjust.html (1.2.7), script.js (1.2.28), style.css (1.2.11). No changes to core configuration values.

import os
import secrets

class Config:
    # Base directory for the project
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Database file path
    INCENTIVE_DB_FILE = os.path.join(BASE_DIR, "incentive.db")

    # Flask session secret key
    SECRET_KEY = secrets.token_urlsafe(32)

    # Vote code for session validation
    VOTE_CODE = "A1RentIt2025"


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