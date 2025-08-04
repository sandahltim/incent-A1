# config.py
# Version: 1.2.6
# Note: Changed SECRET_KEY to static value to fix CSRF session token missing error due to dynamic key generation. Maintained Config class and all attributes from version 1.2.5. Ensured compatibility with app.py (1.2.36), incentive_service.py (1.2.9), init_db.py (1.2.1), forms.py (1.2.2), incentive.html (1.2.17), admin_manage.html (1.2.17), quick_adjust.html (1.2.7), script.js (1.2.28), style.css (1.2.11). No changes to core configuration values.

import os

class Config:
    # Base directory for the project
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

    # Database file path
    INCENTIVE_DB_FILE = os.path.join(BASE_DIR, "incentive.db")

    # Flask session secret key (static for consistent session handling)
    SECRET_KEY = "A1RentIt2025StaticKeyForSessionsAndCSRFProtection"

    # Vote code for session validation
    VOTE_CODE = "A1RentIt2025"

    ADMIN_SECTIONS = ['rules', 'manage_roles']