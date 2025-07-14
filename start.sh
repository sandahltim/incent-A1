#!/bin/bash
source venv/bin/activate
gunicorn --workers 4 --timeout 180 --bind 0.0.0.0:6800 app:app