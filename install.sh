#!/bin/bash
echo "Setting up RFID Incentive Program..."

read -p "Enter server port [6800]: " PORT
PORT=${PORT:-6800}

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask gunicorn werkzeug

# Initialize database
python init_db.py

# Store selected port in settings
python - <<PY
import sqlite3
from config import Config
from incentive_service import set_settings
conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
set_settings(conn, 'server_port', '$PORT')
conn.commit()
conn.close()
PY

# Make start script executable
chmod +x start.sh

echo "Setup complete! To run the server, use './start.sh'"
echo "To access, visit http://rfid:$PORT/"
echo "Master Admin: username 'master', password 'Master8101'"

