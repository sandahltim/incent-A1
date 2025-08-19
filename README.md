# Broadway Tent & Event Incentive Program (Internal Documentation)
Keep this fucking simple as it is for internal company use and security or hacking is hte least of my concerns. 
**Repository:** [github.com/sandahltim/incentive](https://github.com/sandahltim/incentive)  
**Maintainer:** Tim Sandahl  
**For Internal Use Only**  
_Last updated: 2025-07-21_
**auto push to pi for main branch from github-updated 8-4 working now


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

Run the provided installation script to set up the application, choose a port, and install a systemd service that launches the app on boot:
Ports below 1024 require root privileges; choose a port between 1024 and 65535.

```bash
./install.sh
```

The script creates a virtual environment, installs dependencies, initializes the database, and configures `/etc/systemd/system/incentive.service` (configurable via `Config.SERVICE_NAME`) to execute `start.sh`, which reads the port from the database. After installation the app will start automatically on reboot and can be managed from the master admin settings page.

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

Voting Controls: Open, pause, resume, finalize, or end voting sessions for a week.

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

Votes are submitted as positive (+1) or negative (-1) and are weighted
based on the voter's role. Votes do not immediately change employee
scores.

Voting thresholds:

Points awarded/deducted based on thresholds in settings (see above).

Points are applied after a session closes when an employee receives a
percentage of the total available weighted vote points that meets a
configured threshold. Role vote weights can be adjusted via the
`role_vote_weights` setting. The setting stores a JSON object mapping
role names to numeric weights, for example:

```
{"Driver": 1, "Laborer": 1, "Supervisor": 2, "Master": 3}
```

By default, regular employees carry a weight of 1, supervisors 2, and the
master role 3. Any role not listed defaults to 1. During session close,
each vote's weight is divided by the number of employees who participated
in the session, so weighted votes from supervisors or the master can push
an individual's percentage above 100%.

Voting session management:

Open new session (start_voting.html)

Pause, resume, finalize or end session from admin panel.

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
gunicorn --workers 4 --timeout 180 --bind 0.0.0.0:$PORT app:app


# init_db.py
# Version: 1.2.4
# Note: Added migration to include is_master column in admins table to fix sqlite3.OperationalError. Updated master admin to set is_master=1. Ensured idempotent initialization to preserve existing data. Retained dynamic role handling (Master at 0% pot, Supervisor adjustable, max 6 roles). Compatible with app.py (1.2.79), incentive_service.py (1.2.22), forms.py (1.2.7), config.py (1.2.6), admin_manage.html (1.2.32), incentive.html (1.2.28), quick_adjust.html (1.2.11), script.js (1.2.58), style.css (1.2.17), base.html (1.2.21), macros.html (1.2.10), start_voting.html (1.2.7), settings.html (1.2.6), admin_login.html (1.2.5), history.html (1.2.6), error.html. No changes to core database initialization functionality.

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
        ('last_decay_run', '')
    ]
    cursor.executemany("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", default_settings)

    conn.commit()
    conn.close()
    logging.debug("Incentive database initialized at %s", Config.INCENTIVE_DB_FILE)
    print("Incentive database initialized at", Config.INCENTIVE_DB_FILE)

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

#start.sh

#!/bin/bash
source venv/bin/activate
gunicorn --workers 2 --timeout 180 --bind 0.0.0.0:$PORT app:app

## 🚀 Automatic Deployment from GitHub to Raspberry Pi (Self-Hosted Runner)

This repo uses a **self-hosted GitHub Actions runner** on your Raspberry Pi. Any push to the `main` branch pulls new code and restarts the service automatically.

### 1. Clone the Repo

git clone https://github.com/sandahltim/incent-A1.git
cd incent-A1

### 2. Install Dependencies

sudo apt update
sudo apt install curl git

# Your app dependencies (example for Python):
# pip install -r requirements.txt

### 3. Create or Edit Your Systemd Service

# Example: incent-a1.service. Copy to /etc/systemd/system/ and enable it:
sudo systemctl daemon-reload
sudo systemctl enable incent-a1.service
sudo systemctl start incent-a1.service

### 4. Set Up SSH Key for Deploy

# On the Pi, as user 'tim':
ssh-keygen -t ed25519 -C "github-deploy-pi"
# Save as: /home/tim/.ssh/github_deploy_key   (no passphrase)

cat /home/tim/.ssh/github_deploy_key.pub >> /home/tim/.ssh/authorized_keys
chmod 600 /home/tim/.ssh/authorized_keys

# In your GitHub repo: Settings > Secrets and variables > Actions > New repository secret
# Name: PI_DEPLOY_KEY     Value: (paste contents of /home/tim/.ssh/github_deploy_key)
# Name: PI_HOST           Value: (your Pi's Tailscale or LAN IP, e.g. 100.104.xxx.xxx)
# Name: PI_USER           Value: tim

### 5. Enable Passwordless Service Restart

sudo visudo

# Add this line:
tim ALL=NOPASSWD: /bin/systemctl restart incent-a1.service

### 6. Register the Self-Hosted Runner

cd ~/incent-A1
mkdir actions-runner && cd actions-runner

# Download latest ARM64 runner:
curl -o actions-runner-linux-arm64-2.327.1.tar.gz -L https://github.com/actions/runner/releases/download/v2.327.1/actions-runner-linux-arm64-2.327.1.tar.gz

tar xzf ./actions-runner-linux-arm64-2.327.1.tar.gz

# Register (get token from GitHub: Settings > Actions > Runners > New self-hosted runner):
./config.sh --url https://github.com/sandahltim/incent-A1 --token <REGISTRATION_TOKEN>

sudo ./svc.sh install
sudo ./svc.sh start

### 7. Test the Setup

# Push any commit to main branch on GitHub.
# Check your Pi—latest code should pull and service should restart automatically.

-------------------------

## Troubleshooting

- SSH must be accessible from GitHub Actions runner (Tailscale recommended for private networks).
- Systemd service name must match what’s in the workflow (`incent-a1.service`).
- Check logs in Actions tab on GitHub for details.

-------------------------

Q1: How do I deploy from a branch other than main?

Q2: How do I add post-deploy steps (migrate DB, install requirements, etc)?

Q3: How do I rotate the SSH deploy key if compromised?

