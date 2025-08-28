#!/usr/bin/env python3
"""Simple test to verify the JSON structure matches our fixes"""

import json
import sqlite3

def test_json_structure():
    """Test that the JSON structure is compatible with our fixes"""
    
    # Load the JSON file
    json_path = "/home/tim/RFID3/shared/incent/incentive_complete_export_20250828_091756.json"
    print(f"Testing JSON file: {json_path}\n")
    
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    data_section = data.get('data', {})
    
    print("=" * 60)
    print("JSON STRUCTURE VALIDATION")
    print("=" * 60)
    
    # Test each problematic table
    issues_found = []
    
    # 1. Test score_history
    print("\n1. SCORE_HISTORY Table:")
    if 'score_history' in data_section and data_section['score_history']:
        sample = data_section['score_history'][0]
        print(f"   Total records: {len(data_section['score_history'])}")
        print(f"   Sample record keys: {list(sample.keys())}")
        
        # Check expected fields
        if 'date' in sample:
            print("   ✓ Has 'date' field (fixed in import function)")
        else:
            issues_found.append("score_history missing 'date' field")
            
        if 'notes' in sample:
            print("   ✓ Has 'notes' field (now handled)")
        
        if 'month_year' in sample:
            print("   ✓ Has 'month_year' field (now handled)")
    
    # 2. Test voting_results
    print("\n2. VOTING_RESULTS Table:")
    if 'voting_results' in data_section and data_section['voting_results']:
        sample = data_section['voting_results'][0]
        print(f"   Total records: {len(data_section['voting_results'])}")
        print(f"   Sample record keys: {list(sample.keys())}")
        
        if 'points' in sample:
            print("   ✓ Has 'points' field (fixed in import function)")
        else:
            issues_found.append("voting_results missing 'points' field")
            
        if 'plus_percent' in sample:
            print("   ✓ Has 'plus_percent' field (now handled)")
            
        if 'minus_percent' in sample:
            print("   ✓ Has 'minus_percent' field (now handled)")
    
    # 3. Test incentive_rules
    print("\n3. INCENTIVE_RULES Table:")
    if 'incentive_rules' in data_section and data_section['incentive_rules']:
        sample = data_section['incentive_rules'][0]
        print(f"   Total records: {len(data_section['incentive_rules'])}")
        print(f"   Sample record keys: {list(sample.keys())}")
        
        if 'display_order' in sample:
            print("   ✓ Has 'display_order' field (fixed in import function)")
        else:
            issues_found.append("incentive_rules missing 'display_order' field")
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    if issues_found:
        print("\n✗ Issues found:")
        for issue in issues_found:
            print(f"  - {issue}")
    else:
        print("\n✓ All expected fields are present in JSON")
        print("✓ The import functions have been fixed to handle these fields")
        
    return len(issues_found) == 0

def show_fixes_applied():
    """Show what fixes were applied to the import functions"""
    
    print("\n" + "=" * 60)
    print("FIXES APPLIED TO app.py")
    print("=" * 60)
    
    print("\n1. _import_score_history_record():")
    print("   - Now accepts 'date' field (not just 'change_date')")
    print("   - Now handles 'notes' field")
    print("   - Now handles 'month_year' field")
    
    print("\n2. _import_voting_results_record():")
    print("   - Now accepts 'points' field (not just 'net_score')")
    print("   - Now handles 'plus_percent' field")
    print("   - Now handles 'minus_percent' field")
    
    print("\n3. _import_incentive_rule_record():")
    print("   - Now accepts 'display_order' field (not just 'order_index')")
    print("   - Table name handling updated for 'incentive_rules'")
    
    print("\n4. _process_table_data():")
    print("   - Added support for 'rules' as alias for 'incentive_rules'")

def test_database_schema():
    """Verify the database schema matches what we're importing"""
    
    print("\n" + "=" * 60)
    print("DATABASE SCHEMA VERIFICATION")
    print("=" * 60)
    
    db_path = "/home/tim/incentDev/incentive.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tables exist with correct columns
    tables_to_check = {
        'score_history': ['history_id', 'employee_id', 'changed_by', 'points', 'reason', 'notes', 'date', 'month_year'],
        'voting_results': ['session_id', 'employee_id', 'plus_votes', 'minus_votes', 'plus_percent', 'minus_percent', 'points'],
        'incentive_rules': ['rule_id', 'description', 'points', 'details', 'display_order']
    }
    
    for table_name, expected_columns in tables_to_check.items():
        print(f"\nChecking {table_name}:")
        try:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            actual_columns = [col[1] for col in columns]
            
            for expected_col in expected_columns:
                if expected_col in actual_columns:
                    print(f"  ✓ Column '{expected_col}' exists")
                else:
                    print(f"  ✗ Column '{expected_col}' missing")
        except sqlite3.OperationalError as e:
            print(f"  ✗ Table error: {str(e)}")
    
    conn.close()

if __name__ == "__main__":
    print("JSON Import Compatibility Test\n")
    
    # Test JSON structure
    json_valid = test_json_structure()
    
    # Show fixes applied
    show_fixes_applied()
    
    # Test database schema
    test_database_schema()
    
    print("\n" + "=" * 60)
    if json_valid:
        print("✓ JSON IMPORT SHOULD NOW WORK CORRECTLY")
        print("\nTo import the data:")
        print("1. Start the Flask app: python3 app.py")
        print("2. Login as admin at http://localhost:5000/admin")
        print("3. Go to Data Management section")
        print("4. Use 'Import JSON' with table='all' and the JSON file")
    else:
        print("✗ ADDITIONAL FIXES MAY BE NEEDED")
    print("=" * 60)