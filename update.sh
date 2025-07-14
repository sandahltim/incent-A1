#!/bin/bash
cd /home/tim/_rfidpi
# Stash local config.py
cp config.py config.py.bak
git pull origin main
# Restore local config.py
mv config.py.bak config.py
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart rfid_dash
