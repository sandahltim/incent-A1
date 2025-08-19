#!/usr/bin/bash
# Ensure we run from the directory containing this script so relative paths work
cd "$(dirname "$0")"
source venv/bin/activate
PORT=$(python - <<'PY'
from config import Config
import sqlite3
port = '8101'
try:
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    cur = conn.execute("SELECT value FROM settings WHERE key='port'")
    row = cur.fetchone()
    if row and row[0]:
        port = row[0]
finally:
    conn.close()
print(port)
PY
)
exec gunicorn --workers 2 --timeout 180 --bind 0.0.0.0:$PORT app:app
