#!/bin/bash
source /home/tim/_rfidpi/venv/bin/activate
gunicorn --workers 2 --bind 0.0.0.0:8101 --timeout 60 run:app 
