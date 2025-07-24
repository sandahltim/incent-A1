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