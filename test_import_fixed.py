#!/usr/bin/env python3
"""Test the fixed JSON import functionality"""

import json
import requests
import sys
from pathlib import Path

# Configuration
BASE_URL = "http://localhost:5000"
JSON_FILE = "/home/tim/RFID3/shared/incent/incentive_complete_export_20250828_091756.json"

def test_json_import():
    """Test importing the JSON file via the API"""
    print("=" * 60)
    print("Testing JSON Import Functionality")
    print("=" * 60)
    
    # First, we need to login as admin
    print("\n1. Logging in as admin...")
    session = requests.Session()
    
    # Try to login (you may need to adjust credentials)
    login_data = {
        'username': 'master',
        'password': 'master'  # You'll need the actual password
    }
    
    login_response = session.post(f"{BASE_URL}/admin/login", data=login_data)
    if login_response.status_code != 200:
        print("Failed to login. Please ensure the app is running and credentials are correct.")
        print(f"Response: {login_response.text}")
        return False
    
    print("Login successful!")
    
    # Load the JSON file
    print(f"\n2. Loading JSON file: {JSON_FILE}")
    with open(JSON_FILE, 'rb') as f:
        files = {'json_file': ('export.json', f, 'application/json')}
        data = {
            'table_name': 'all',  # Import all tables
            'import_mode': 'append'  # Append mode to avoid data loss
        }
        
        print("\n3. Sending import request...")
        response = session.post(f"{BASE_URL}/admin/import_json", files=files, data=data)
    
    print(f"\n4. Response Status: {response.status_code}")
    
    try:
        result = response.json()
        print(f"\n5. Import Result:")
        print(json.dumps(result, indent=2))
        
        if result.get('success'):
            print("\n✓ Import successful!")
            if 'details' in result:
                details = result['details']
                print(f"\n  Total records imported: {details.get('total_success', 0)}")
                print(f"  Total errors: {details.get('total_errors', 0)}")
                
                if 'table_results' in details:
                    print("\n  Table-by-table results:")
                    for table, table_result in details['table_results'].items():
                        success = table_result.get('success_count', 0)
                        errors = table_result.get('error_count', 0)
                        status = "✓" if errors == 0 else "⚠"
                        print(f"    {status} {table}: {success} imported, {errors} errors")
                        if errors > 0 and 'errors' in table_result:
                            for err in table_result['errors'][:3]:  # Show first 3 errors
                                print(f"      - {err}")
        else:
            print("\n✗ Import failed!")
            print(f"  Message: {result.get('message')}")
            
        return result.get('success', False)
        
    except json.JSONDecodeError:
        print("\n✗ Failed to parse response as JSON")
        print(f"Response text: {response.text}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        return False

def verify_imported_data():
    """Verify that data was imported correctly"""
    print("\n" + "=" * 60)
    print("Verifying Imported Data")
    print("=" * 60)
    
    import sqlite3
    
    db_path = "/home/tim/incentDev/incentive.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables_to_check = [
        'employees', 'votes', 'voting_sessions', 'vote_participants',
        'admins', 'score_history', 'incentive_rules', 'incentive_pot',
        'roles', 'point_decay', 'voting_results', 'settings'
    ]
    
    print(f"\nChecking record counts in database:")
    for table in tables_to_check:
        try:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"  {table}: {count} records")
        except sqlite3.OperationalError as e:
            print(f"  {table}: Table not found or error ({str(e)})")
    
    # Check specific problematic records
    print("\n\nChecking specific data integrity:")
    
    # Check score_history for proper field mapping
    cursor.execute("""
        SELECT COUNT(*) FROM score_history 
        WHERE date IS NOT NULL AND month_year IS NOT NULL
    """)
    score_history_complete = cursor.fetchone()[0]
    print(f"  score_history with date and month_year: {score_history_complete}")
    
    # Check voting_results for proper field mapping  
    cursor.execute("""
        SELECT COUNT(*) FROM voting_results 
        WHERE plus_percent IS NOT NULL AND minus_percent IS NOT NULL AND points IS NOT NULL
    """)
    voting_results_complete = cursor.fetchone()[0]
    print(f"  voting_results with percentages and points: {voting_results_complete}")
    
    # Check incentive_rules
    cursor.execute("SELECT COUNT(*) FROM incentive_rules WHERE display_order IS NOT NULL")
    rules_with_order = cursor.fetchone()[0]
    print(f"  incentive_rules with display_order: {rules_with_order}")
    
    conn.close()
    print("\n✓ Data verification complete")

if __name__ == "__main__":
    print("Starting JSON Import Test\n")
    
    # Check if Flask app is running
    try:
        response = requests.get(BASE_URL, timeout=2)
        print(f"✓ Flask app is running at {BASE_URL}")
    except requests.exceptions.RequestException:
        print(f"✗ Flask app is not running at {BASE_URL}")
        print("  Please start the app with: python3 app.py")
        sys.exit(1)
    
    # Run the import test
    success = test_json_import()
    
    if success:
        # Verify the imported data
        verify_imported_data()
        print("\n" + "=" * 60)
        print("✓ JSON IMPORT TEST COMPLETED SUCCESSFULLY")
        print("=" * 60)
    else:
        print("\n" + "=" * 60)
        print("✗ JSON IMPORT TEST FAILED")
        print("=" * 60)
        print("\nTroubleshooting tips:")
        print("1. Check that the Flask app is running")
        print("2. Verify admin credentials are correct")
        print("3. Check the app logs for detailed error messages")
        print("4. Ensure the JSON file exists and is readable")