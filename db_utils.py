import sqlite3
from config import DB_FILE
from db_connection import DatabaseConnection

def initialize_db():
    """
    Creates or updates the database and tables to store all fields from the API.
    If inventory.db already exists with an old schema, rename or remove it before running
    this if you want a clean start.
    """
    with DatabaseConnection() as conn:
        cursor = conn.cursor()

        # Expanded id_item_master table with all columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS id_item_master (
                tag_id TEXT PRIMARY KEY,
                uuid_accounts_fk TEXT,
                serial_number TEXT,
                client_name TEXT,
                rental_class_num TEXT,
                common_name TEXT,
                quality TEXT,
                bin_location TEXT,
                status TEXT,
                last_contract_num TEXT,
                last_scanned_by TEXT,
                notes TEXT,
                status_notes TEXT,
                long TEXT,
                lat TEXT,
                date_last_scanned TEXT,
                date_created TEXT,
                date_updated TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_contract ON id_item_master (last_contract_num)")

        # Expanded id_transactions table with all columns
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS id_transactions (
                contract_number TEXT,
                client_name TEXT,
                tag_id TEXT,
                common_name TEXT,
                bin_location TEXT,
                scan_type TEXT,
                status TEXT,
                scan_date TEXT,
                scan_by TEXT,
                location_of_repair TEXT,
                quality TEXT,
                dirty_or_mud TEXT,
                leaves TEXT,
                oil TEXT,
                mold TEXT,
                stain TEXT,
                oxidation TEXT,
                other TEXT,
                rip_or_tear TEXT,
                sewing_repair_needed TEXT,
                grommet TEXT,
                rope TEXT,
                buckle TEXT,
                date_created TEXT,
                date_updated TEXT,
                uuid_accounts_fk TEXT,
                serial_number TEXT,
                rental_class_num TEXT,
                long TEXT,
                lat TEXT,
                wet TEXT,
                service_required TEXT,
                notes TEXT,
                PRIMARY KEY (contract_number, tag_id, scan_type, scan_date)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_client_date ON id_transactions (client_name, scan_date)")

        # seed_rental_classes (present in main branch)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS seed_rental_classes (
                rental_class_id TEXT PRIMARY KEY,
                common_name TEXT,
                bin_location TEXT
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_common_name ON seed_rental_classes (common_name)")

        print("Database initialized at", DB_FILE)
        