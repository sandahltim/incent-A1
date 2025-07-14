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
