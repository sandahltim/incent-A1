#!/usr/bin/env python3
"""Test script to identify JSON import issues"""

import json
import sqlite3
from pathlib import Path

# Load the JSON file
json_path = "/home/tim/RFID3/shared/incent/incentive_complete_export_20250828_091756.json"
print(f"Loading JSON from: {json_path}")

with open(json_path, 'r') as f:
    data = json.load(f)

print(f"\nMetadata:")
metadata = data.get('metadata', {})
print(f"  Export timestamp: {metadata.get('export_timestamp')}")
print(f"  Total tables: {metadata.get('total_tables')}")
print(f"  Total records: {metadata.get('total_records')}")

print(f"\nData tables found:")
data_section = data.get('data', {})
for table_name, records in data_section.items():
    print(f"  {table_name}: {len(records)} records")
    if records and len(records) > 0:
        # Show first record's keys
        print(f"    Keys: {list(records[0].keys())}")

# Check for field mismatches
print("\n=== FIELD ANALYSIS ===")

# Check score_history
if 'score_history' in data_section and data_section['score_history']:
    print("\nScore History fields in JSON:")
    first_record = data_section['score_history'][0]
    for key in first_record.keys():
        print(f"  - {key}: {type(first_record[key]).__name__}")
    
# Check voting_results  
if 'voting_results' in data_section and data_section['voting_results']:
    print("\nVoting Results fields in JSON:")
    first_record = data_section['voting_results'][0]
    for key in first_record.keys():
        print(f"  - {key}: {type(first_record[key]).__name__}")

# Check incentive_rules
if 'incentive_rules' in data_section and data_section['incentive_rules']:
    print("\nIncentive Rules fields in JSON:")
    first_record = data_section['incentive_rules'][0]
    for key in first_record.keys():
        print(f"  - {key}: {type(first_record[key]).__name__}")

print("\n=== DATABASE SCHEMA CHECK ===")

# Connect to database and check actual schema
db_path = "/home/tim/incentDev/incentive.db"
print(f"Checking database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Get table info
tables_to_check = ['score_history', 'voting_results', 'incentive_rules']
for table in tables_to_check:
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    print(f"\n{table} columns in database:")
    for col in columns:
        print(f"  - {col[1]}: {col[2]}")

conn.close()

print("\n=== MISMATCHES FOUND ===")
print("\n1. score_history:")
print("   - JSON has 'date' but import function expects 'change_date'")
print("   - JSON has 'notes' and 'month_year' fields not handled in import")

print("\n2. voting_results:")
print("   - JSON has 'points' field but import function expects 'net_score'")
print("   - JSON has 'plus_percent' and 'minus_percent' fields not handled")

print("\n3. incentive_rules:")
print("   - JSON has 'display_order' but import function expects 'order_index'")
print("   - Database table is called 'rules' not 'incentive_rules'")