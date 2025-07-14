import os

# Base directory for the project
BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Database file path
DB_FILE = os.path.join(BASE_DIR, "inventory.db")

# API configuration (as noted in the project overview)
API_USERNAME = os.environ.get("API_USERNAME", "api")
API_PASSWORD = os.environ.get("API_PASSWORD", "Broadway8101")
LOGIN_URL = "https://login.cloud.ptshome.com/api/v1/login"
ITEM_MASTER_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169344381"
TRANSACTION_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169346196"
SEED_URL = "https://cs.iot.ptshome.com/api/v1/data/14223767938169215907"

# Refresh configuration: data is refreshed every 10 minutes (600 seconds)
REFRESH_INTERVAL = 600

