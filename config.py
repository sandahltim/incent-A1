import os

# Base directory for the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database file path
INCENTIVE_DB_FILE = os.path.join(BASE_DIR, "incentive.db")

# Flask session secret key
SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "your-secret-key-here")

# Vote code for session validation
VOTE_CODE = "A1RentIt2025"