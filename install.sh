#!/bin/bash
echo "Setting up RFID Dashboard on Pi..."
sudo apt update && sudo apt install python3.11 -y || { echo "Python install failed"; exit 1; }
python3.11 -m venv venv || { echo "Venv creation failed"; exit 1; }
source venv/bin/activate
pip install -r requirements.txt
pip install flask==2.3.2 gunicorn==22.0.0 || { echo "Pip install failed"; exit 1; }
sudo cp rfid_dash.service /etc/systemd/system/ || { echo "Systemd copy failed"; exit 1; }
sudo systemctl daemon-reload
sudo systemctl enable rfid_dash || { echo "Systemd enable failed"; exit 1; }
python3 db_utils.py  # Initialize DB
echo "Install complete! Reboot to start or run ./start.sh."
