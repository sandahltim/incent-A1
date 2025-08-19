#!/usr/bin/bash
echo "Setting up RFID Incentive Program..."

# Prompt for port
read -p "Enter port for server [8101]: " PORT
PORT=${PORT:-8101}

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask gunicorn werkzeug

# Initialize database and store chosen port
python init_db.py
python - <<EOF
from config import Config
import sqlite3
conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('port', '$PORT'))
conn.commit()
conn.close()
EOF

# Make start script executable
chmod +x start.sh

# Configure systemd service to run the app on boot
APP_DIR="$(pwd)"
SERVICE_NAME=$(python - <<'PY'
from config import Config
print(getattr(Config, 'SERVICE_NAME', 'incentive.service'))
PY
)
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
sudo tee "$SERVICE_PATH" >/dev/null <<SERVICE
[Unit]
Description=RFID Incentive Program
After=network.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/start.sh
Restart=always

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Setup complete! To run the server, use './start.sh'"
echo "To access, visit http://rfid:$PORT/"
echo "Master Admin: username 'master', password 'Master8101'"
