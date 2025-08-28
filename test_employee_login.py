#!/usr/bin/env python3
"""
Test Employee Portal Login
Tests the employee portal login functionality directly
"""

import sys
import sqlite3
from werkzeug.security import check_password_hash
from config import Config

def test_employee_login():
    """Test employee login functionality"""
    
    print("Testing Employee Portal Login")
    print("=" * 40)
    
    # Test credentials
    employee_id = "E001"
    test_pin = "8101"
    
    try:
        # Connect to database
        conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get employee
        employee = cursor.execute(
            "SELECT employee_id, name, pin_hash FROM employees WHERE employee_id = ?",
            (employee_id,)
        ).fetchone()
        
        if not employee:
            print(f"ERROR: Employee {employee_id} not found!")
            return False
        
        print(f"Found employee: {employee['name']} ({employee['employee_id']})")
        
        # Check if PIN hash exists
        if not employee['pin_hash']:
            print("ERROR: Employee has no PIN set!")
            return False
        
        print("PIN hash exists in database")
        
        # Verify PIN
        pin_valid = check_password_hash(employee['pin_hash'], test_pin)
        
        if pin_valid:
            print(f"SUCCESS: PIN {test_pin} is valid for {employee_id}")
            print("Login would succeed!")
            return True
        else:
            print(f"ERROR: PIN {test_pin} is NOT valid for {employee_id}")
            return False
            
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    success = test_employee_login()
    sys.exit(0 if success else 1)