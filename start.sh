#!/bin/bash
source venv/bin/activate
gunicorn --workers 2 --timeout 180 --bind 0.0.0.0:8101 app:app