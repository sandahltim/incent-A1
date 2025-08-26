#!/usr/bin/env python3
"""
Fix Employee PINs Script
Adds default PIN 8101 to all employees who don't have one.
This fixes the PIN addition error for existing employees.
"""

import sqlite3
import sys
from config import Config
from werkzeug.security import generate_password_hash

DEFAULT_PIN = "8101"

def main():
    # Check for --auto flag
    auto_mode = '--auto' in sys.argv or len(sys.argv) == 1  # Default to auto if no args
    print("🔧 Employee PIN Fix Script")
    print("=" * 40)
    
    try:
        # Connect to database
        conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Check current PIN status
        print("📊 Checking current employee PIN status...")
        employees = cursor.execute("""
            SELECT employee_id, name, initials, pin_hash
            FROM employees 
            WHERE active = 1
            ORDER BY name
        """).fetchall()
        
        employees_without_pin = []
        employees_with_pin = []
        
        for emp in employees:
            if emp['pin_hash'] is None or emp['pin_hash'] == '':
                employees_without_pin.append(emp)
            else:
                employees_with_pin.append(emp)
        
        print(f"✅ Employees with PINs: {len(employees_with_pin)}")
        print(f"⚠️  Employees without PINs: {len(employees_without_pin)}")
        print()
        
        if not employees_without_pin:
            print("🎉 All employees already have PINs! No changes needed.")
            return
        
        print("Employees needing PINs:")
        for emp in employees_without_pin:
            print(f"  - {emp['employee_id']}: {emp['name']} ({emp['initials']})")
        print()
        
        # Auto-confirm for script execution
        print(f"🔄 Adding default PIN '{DEFAULT_PIN}' to {len(employees_without_pin)} employees...")
        
        # Generate hashed PIN
        pin_hash = generate_password_hash(DEFAULT_PIN)
        print(f"🔐 Generated PIN hash for '{DEFAULT_PIN}'")
        
        # Update employees
        updated_count = 0
        for emp in employees_without_pin:
            try:
                cursor.execute("""
                    UPDATE employees 
                    SET pin_hash = ? 
                    WHERE employee_id = ?
                """, (pin_hash, emp['employee_id']))
                
                print(f"✅ Updated {emp['employee_id']}: {emp['name']}")
                updated_count += 1
                
            except Exception as e:
                print(f"❌ Failed to update {emp['employee_id']}: {e}")
        
        # Commit changes
        conn.commit()
        print()
        print(f"🎉 Successfully updated {updated_count} employees!")
        print(f"📝 Default PIN for all employees is now: {DEFAULT_PIN}")
        print()
        print("⚠️  SECURITY NOTE: Employees should change their PINs after first login.")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()