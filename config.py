# config.py
# Version: 1.2.7
# Note: Added SERVICE_NAME for systemd integration while maintaining previous configuration values. Ensured compatibility with app.py (1.2.79+), incentive_service.py (1.2.22+), forms.py (1.2.7+), and related templates.

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

    # Systemd service unit controlling the app
    SERVICE_NAME = "incentive.service"
