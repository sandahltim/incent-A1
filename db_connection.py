import sqlite3
from config import DB_FILE

class DatabaseConnection:
    """
    Context manager for SQLite connections.
    Ensures a consistent method to open and close the database.
    """
    def __enter__(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.conn.row_factory = sqlite3.Row
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

