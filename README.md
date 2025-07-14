# -rfidpiA1 Rent-It Incentive Program
Overview
The A1 Rent-It Incentive Program is a web-based application designed to manage an employee incentive system for A1 Rent-It. Employees earn points based on performance, voting, and predefined rules, which contribute to a share of an incentive pot derived from company sales. The application supports role-based point allocation, weekly voting, point decay, and administrative management. It is designed to run on a Raspberry Pi, ensuring easy deployment on A1 Rent-It's network with straightforward updates. The interface uses a Golden Yellow (#FFC107) and Black (#000000) color scheme to align with A1 Rent-It's branding.
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
Admin Interface: Secure admin access for managing employees, rules, roles, voting sessions, and the incentive pot.
Voting Results: Display results for admins (detailed) and employees (weekly summary).
History Tracking: Log all point changes with reasons and timestamps.
Raspberry Pi Deployment: Plug-and-play setup with automatic network configuration and easy updates via Git.

Technology Stack

Backend: Python 3, Flask 2.2.5, SQLite3
Frontend: HTML, Jinja2 templates, CSS (Golden Yellow and Black theme)
Server: Gunicorn 23.0.0 with 4 workers
Dependencies: See requirements.txt for full list
Database: SQLite (incentive.db)
Deployment Platform: Raspberry Pi (Raspbian/Raspberry Pi OS)
Version Control: Git, hosted on GitHub

Installation and Setup
Prerequisites

Raspberry Pi (Model 3 or later recommended) with Raspberry Pi OS (latest version)
Internet connection for initial setup
Git installed (sudo apt install git)
Python 3.8+ (sudo apt install python3 python3-pip python3-venv)
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


Network Configuration

Ensure the Raspberry Pi is connected to A1 Rent-It's network (Ethernet or Wi-Fi).
The application binds to 0.0.0.0:6800, making it accessible on the network. Retrieve the Pi's IP address:hostname -I


If static IP is required, configure /etc/dhcpcd.conf on the Pi:sudo nano /etc/dhcpcd.conf

Add:interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=8.8.8.8

Adjust IP addresses to match the network. Restart networking:sudo systemctl restart dhcpcd




Start the Application

Run the start script to launch the Gunicorn server:chmod +x start.sh
./start.sh


The application is now accessible at http://<pi-ip>:6800/.


Automatic Startup (Optional)

To run the application on boot, add to crontab:crontab -e

Add:@reboot /path/to/incent-A1/start.sh

Replace /path/to/incent-A1/ with the full path to the project directory.



Updating the Application

Pull Updates from GitHub:cd /path/to/incent-A1
git pull origin main


Update Dependencies (if requirements.txt changes):source venv/bin/activate
pip install -r requirements.txt


Restart the Server:pkill gunicorn
./start.sh


Database Migrations: The init_db.py script uses IF NOT EXISTS to avoid overwriting data. Run manually if schema changes are needed:source venv/bin/activate
python init_db.py



File Structure

app.py: Main Flask application with routes for incentive, admin, voting, and data endpoints.
incentive_service.py: Backend logic for database operations, voting, and point calculations.
init_db.py: Initializes the SQLite database (incentive.db) with tables for employees, votes, sessions, admins, rules, roles, pot, decay, and history.
config.py: Configuration file with database path and voting settings.
install.sh: Setup script for virtual environment, dependencies, and database initialization.
start.sh: Script to start the Gunicorn server.
requirements.txt: Python dependencies.
templates/:
base.html: Base template with navigation (Golden Yellow and Black styling).
incentive.html: Public-facing page with scoreboard, rules, pot info, and voting interface.
admin_manage.html: Admin interface for managing employees, rules, roles, pot, decay, and voting.
admin_login.html: Admin login page (not provided but referenced).
start_voting.html: Voting session start page (not provided but referenced).
history.html: Point change history page (not provided but referenced).


static/: Static files (CSS, JS) for styling and client-side functionality (not provided but assumed to exist).

Database Schema

employees: Stores employee data (employee_id, name, initials, score, role, active, last_decay_date).
votes: Records votes (vote_id, voter_initials, recipient_id, vote_value, vote_date).
voting_sessions: Tracks voting sessions (session_id, vote_code, admin_id, start_time, end_time).
admins: Admin credentials (admin_id, username, password).
score_history: Logs point changes (history_id, employee_id, changed_by, points, reason, date, month_year).
incentive_rules: Point rules (rule_id, description, points, display_order).
incentive_pot: Pot details (id, sales_dollars, bonus_percent, prior_year_sales, role percentages).
roles: Role definitions (role_name, percentage).
point_decay: Daily decay settings (id, role_name, points, days).
voting_results: Voting outcomes (session_id, employee_id, plus_votes, minus_votes, plus_percent, minus_percent, points).

Usage

Access: Visit http://<pi-ip>:6800/ on the network.
Public Interface (incentive.html):
View scoreboard, rules, and incentive pot details.
Cast votes when voting is active (requires initials).
View weekly voting results (non-admin view shows +1/-1 vote counts).


Admin Interface (admin_manage.html):
Login with admin credentials (e.g., master/Master8101).
Manage employees, rules, roles, pot, decay, and admins (master only).
Start/pause/end voting sessions.
Reset scores or perform a master reset (master only).


Voting:
Weekly sessions allow up to 2 positive and 3 negative votes per employee.
Points awarded based on vote percentages (e.g., +10 for >90% positive).


Point Decay: Configurable per role, applied daily on specified days.

Styling

Colors:
Golden Yellow (#FFC107): Primary color for headers, buttons, and highlights.
Black (#000000): Backgrounds, text, and borders.


CSS: Stored in static/ (not provided but should implement the color scheme).
Responsive Design: Ensure templates are mobile-friendly for use on tablets or phones.

Security

Admin Access: Passwords are hashed using werkzeug.security.generate_password_hash.
Session Management: Flask sessions with a secret key (app.secret_key).
Vote Validation: Checks for active sessions, unique votes per week, and vote limits.
Master Account: Required for critical actions (e.g., role management, master reset).

Maintenance

Backups: Regularly back up incentive.db:cp incentive.db incentive_backup_$(date +%F).db


Logs: Check Gunicorn logs for errors:journalctl -u gunicorn


Dependency Updates: Periodically update requirements.txt and run pip install -r requirements.txt.

Troubleshooting

Server Not Starting:
Verify start.sh is executable (chmod +x start.sh).
Check Gunicorn logs: journalctl -u gunicorn.


Database Errors:
Ensure incentive.db is writable: chmod 666 incentive.db.
Reinitialize database: python init_db.py.


Network Issues:
Confirm Pi’s IP address: hostname -I.
Check firewall settings: sudo ufw status.


Voting Not Active:
Ensure a voting session is started via the admin interface.
Verify VOTING_DAYS_2025 in config.py.



Future Improvements

Add client-side JavaScript for real-time updates (e.g., scoreboard refresh).
Implement CSRF protection for forms.
Enhance CSS for better mobile responsiveness.
Add backup and restore functionality for the database.
Support for multiple voting sessions per week if needed.

Contact
For issues or contributions, open a pull request or issue on GitHub.