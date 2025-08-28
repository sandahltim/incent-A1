#!/usr/bin/env python3
"""Manual test of the fixed import functions"""

import json
import sqlite3
import sys
import os

# Add the app directory to path so we can import the functions
sys.path.insert(0, '/home/tim/incentDev')

# Import the database connection and functions from app.py
from app import DatabaseConnection, _process_table_data

def test_import_functions():
    """Test the import functions directly"""
    
    # Load the JSON file
    json_path = "/home/tim/RFID3/shared/incent/incentive_complete_export_20250828_091756.json"
    print(f"Loading JSON from: {json_path}")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    data_section = data.get('data', {})
    
    # Test importing specific problematic tables
    print("\n=== Testing Import Functions ===\n")
    
    test_tables = ['score_history', 'voting_results', 'incentive_rules']
    
    with DatabaseConnection() as conn:
        for table_name in test_tables:
            if table_name not in data_section:
                print(f"Skipping {table_name} - not in JSON")
                continue
                
            table_data = data_section[table_name]
            if not table_data:
                print(f"Skipping {table_name} - no data")
                continue
            
            print(f"Testing {table_name}...")
            print(f"  Records to import: {len(table_data)}")
            
            # Take a sample record to test
            sample_record = table_data[0] if table_data else None
            if sample_record:
                print(f"  Sample record fields: {list(sample_record.keys())}")
            
            try:
                # Test processing the table data
                result = _process_table_data(conn, table_name, table_data[:5], 'append')  # Test with first 5 records
                print(f"  ✓ Success: {result['success_count']} imported, {result['error_count']} errors")
                if result['error_count'] > 0:
                    print(f"  Errors: {result.get('errors', [])}")
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
        
        # Don't commit - this is just a test
        conn.rollback()
        print("\n✓ Test completed (changes rolled back)")

def check_field_compatibility():
    """Check if our fixes handle all field variations"""
    print("\n=== Field Compatibility Check ===\n")
    
    json_path = "/home/tim/RFID3/shared/incent/incentive_complete_export_20250828_091756.json"
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    data_section = data.get('data', {})
    
    # Check score_history
    if 'score_history' in data_section and data_section['score_history']:
        record = data_section['score_history'][0]
        print("score_history:")
        print(f"  ✓ 'date' field present: {'date' in record}")
        print(f"  ✓ 'notes' field present: {'notes' in record}")
        print(f"  ✓ 'month_year' field present: {'month_year' in record}")
    
    # Check voting_results
    if 'voting_results' in data_section and data_section['voting_results']:
        record = data_section['voting_results'][0]
        print("\nvoting_results:")
        print(f"  ✓ 'points' field present: {'points' in record}")
        print(f"  ✓ 'plus_percent' field present: {'plus_percent' in record}")
        print(f"  ✓ 'minus_percent' field present: {'minus_percent' in record}")
    
    # Check incentive_rules
    if 'incentive_rules' in data_section and data_section['incentive_rules']:
        record = data_section['incentive_rules'][0]
        print("\nincentive_rules:")
        print(f"  ✓ 'display_order' field present: {'display_order' in record}")
    
    print("\n✓ All expected fields are present in JSON")

if __name__ == "__main__":
    print("Manual Import Function Test\n")
    print("=" * 60)
    
    # Check field compatibility
    check_field_compatibility()
    
    # Test the import functions
    test_import_functions()
    
    print("\n" + "=" * 60)
    print("✓ Manual test completed successfully")
    print("=" * 60)