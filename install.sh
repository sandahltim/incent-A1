#!/bin/bash
echo "Setting up RFID Incentive Program..."

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install flask gunicorn werkzeug

# Initialize database
python init_db.py

# Make start script executable
chmod +x start.sh

echo "Setup complete! To run the server, use './start.sh'"
echo "To access, visit http://rfid:6800/"
echo "Master Admin: username 'master', password 'Master8101'"
