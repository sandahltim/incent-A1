# config.py
# Version: 1.2.4
# Note: Strengthened SECRET_KEY with secrets module for improved security. Maintained INCENTIVE_DB_FILE and VOTE_CODE. Ensured compatibility with app.py (version 1.2.27).

import os
import secrets

# Base directory for the project
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Database file path
INCENTIVE_DB_FILE = os.path.join(BASE_DIR, "incentive.db")

# Flask session secret key
SECRET_KEY = secrets.token_urlsafe(32)

# Vote code for session validation
VOTE_CODE = "A1RentIt2025"