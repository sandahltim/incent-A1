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
    SERVICE_NAME = "incent-dev.service"

    # Database connection pool settings
    DB_POOL_SIZE = 10  # Maximum number of connections in pool
    DB_POOL_TIMEOUT = 30  # Connection timeout in seconds
    DB_POOL_MAX_RETRIES = 3  # Max retries for failed connections
    DB_POOL_HEALTH_CHECK_INTERVAL = 300  # Health check every 5 minutes
    DB_POOL_MAX_OVERFLOW = 5  # Additional connections beyond pool size
    DB_POOL_RECYCLE_TIME = 3600  # Recycle connections every hour

    # Caching system settings
    CACHE_MAX_SIZE = 2000  # Maximum number of cache entries
    CACHE_DEFAULT_TTL = 300  # Default cache TTL in seconds (5 minutes)
    CACHE_CLEANUP_INTERVAL = 60  # Cache cleanup interval in seconds
    CACHE_ENABLED = True  # Enable/disable caching globally
    
    # Specific cache TTL settings (in seconds)
    CACHE_TTL_SCOREBOARD = 30  # Scoreboard data - 30 seconds
    CACHE_TTL_RULES = 300  # Rules data - 5 minutes
    CACHE_TTL_ROLES = 300  # Roles data - 5 minutes
    CACHE_TTL_SETTINGS = 120  # Settings data - 2 minutes
    CACHE_TTL_POT_INFO = 120  # Pot info - 2 minutes
    CACHE_TTL_VOTING_RESULTS = 300  # Voting results - 5 minutes
    CACHE_TTL_ANALYTICS = 600  # Analytics/charts - 10 minutes
    CACHE_TTL_EMPLOYEE_GAMES = 60  # Mini-games - 1 minute
    CACHE_TTL_ADMIN_DATA = 600  # Admin configurations - 10 minutes
    CACHE_TTL_HISTORY = 300  # History data - 5 minutes
