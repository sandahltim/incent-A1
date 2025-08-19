#!/usr/bin/env python3
import sqlite3
from config import Config
from incentive_service import get_settings

conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
settings = get_settings(conn)
print(settings.get('server_port', '6800'))
conn.close()

