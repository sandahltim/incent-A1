import os
from datetime import datetime, timedelta

# Base directory for the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database file path
INCENTIVE_DB_FILE = os.path.join(BASE_DIR, "incentive.db")

# Flask session secret key
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "your-secret-key-here")

# Vote code for session validation
VOTE_CODE = "A1RentIt2025"

# Generate all Wednesdays in 2025 for voting days
def generate_voting_days(year=2025):
    start_date = datetime(year, 1, 1)
    end_date = datetime(year, 12, 31)
    delta = timedelta(days=1)
    voting_days = []
    current_date = start_date
    while current_date <= end_date:
        if current_date.weekday() == 2:  # Wednesday
            voting_days.append(current_date.strftime("%Y-%m-%d"))
        current_date += delta
    return voting_days

VOTING_DAYS_2025 = generate_voting_days(2025)