#!/bin/bash
source venv/bin/activate
PORT=$(python get_port.py)
gunicorn --workers 2 --timeout 180 --bind 0.0.0.0:$PORT app:app
