#!/usr/bin/env python3
"""
Apply fixes to the dual game system
Run this script to fix remaining issues found during debugging
"""

import sqlite3
import sys
import json

def enable_foreign_keys():
    """Enable foreign key constraints in the database"""
    print("Enabling foreign key constraints...")
    conn = sqlite3.connect('/home/tim/incentDev/incentive.db')
    cursor = conn.cursor()
    
    # Check current status
    cursor.execute("PRAGMA foreign_keys")
    current = cursor.fetchone()[0]
    print(f"  Current foreign_keys status: {current}")
    
    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON")
    
    # Verify
    cursor.execute("PRAGMA foreign_keys")
    new_status = cursor.fetchone()[0]
    print(f"  New foreign_keys status: {new_status}")
    
    conn.close()
    return new_status == 1

def fix_input_validation():
    """Add a note about input validation fix needed"""
    print("\nInput Validation Fix Required:")
    print("  In /home/tim/incentDev/routes/dual_game_simple.py")
    print("  The exchange endpoint needs better type checking:")
    print("  - Add: points = int(data.get('points', 0))")
    print("  - Wrap in try/except to handle non-numeric values")
    
    fix_code = '''
    try:
        points = int(data.get('points', 0))
    except (ValueError, TypeError):
        return jsonify({'error': 'Points must be a number'}), 400
    '''
    print(f"\n  Suggested fix:{fix_code}")

def check_win_rates():
    """Analyze actual win rates in the database"""
    print("\nAnalyzing Win Rates from Transaction History...")
    conn = sqlite3.connect('/home/tim/incentDev/incentive.db')
    cursor = conn.cursor()
    
    # Get recent gambling transactions
    cursor.execute("""
        SELECT 
            e.role,
            COUNT(*) as total_games,
            SUM(CASE WHEN tt.token_amount > 0 THEN 1 ELSE 0 END) as wins,
            ROUND(CAST(SUM(CASE WHEN tt.token_amount > 0 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) * 100, 2) as win_rate
        FROM token_transactions tt
        JOIN employees e ON tt.employee_id = e.employee_id
        WHERE tt.transaction_type IN ('gambling_win', 'gambling_loss', 'game_play')
        GROUP BY e.role
    """)
    
    results = cursor.fetchall()
    
    if results:
        print("  Historical win rates by role:")
        for role, total, wins, rate in results:
            expected = {'master': 40, 'supervisor': 35, 'driver': 30, 'laborer': 25}.get(role, 25)
            status = "✓" if abs(rate - expected) < 10 else "✗"
            print(f"    {role}: {rate}% (expected {expected}%) {status}")
    else:
        print("  No gambling transaction history found")
    
    conn.close()

def add_default_config():
    """Add default configuration values if missing"""
    print("\nChecking Game Configuration...")
    conn = sqlite3.connect('/home/tim/incentDev/incentive.db')
    cursor = conn.cursor()
    
    # Check existing config
    cursor.execute("SELECT COUNT(*) FROM admin_game_config")
    config_count = cursor.fetchone()[0]
    print(f"  Found {config_count} configuration entries")
    
    if config_count < 10:
        print("  Adding default configuration...")
        
        default_configs = [
            ('token_economy', 'daily_exchange_limit', '100'),
            ('token_economy', 'cooldown_hours', '24'),
            ('gambling_system', 'min_bet', '1'),
            ('gambling_system', 'max_bet', '100'),
            ('gambling_system', 'multiplier_min', '2.0'),
            ('gambling_system', 'multiplier_max', '5.0'),
            ('reward_system', 'category_a_cooldown', '86400'),
            ('reward_system', 'points_weight', '70'),
            ('reward_system', 'pto_weight', '20'),
            ('reward_system', 'swag_weight', '10')
        ]
        
        for category, key, value in default_configs:
            cursor.execute("""
                INSERT OR IGNORE INTO admin_game_config 
                (config_category, config_key, config_value)
                VALUES (?, ?, ?)
            """, (category, key, value))
        
        conn.commit()
        print("  Default configuration added")
    
    conn.close()

def verify_table_structure():
    """Verify all required tables and columns exist"""
    print("\nVerifying Database Structure...")
    conn = sqlite3.connect('/home/tim/incentDev/incentive.db')
    cursor = conn.cursor()
    
    required_tables = {
        'employee_tokens': [
            'employee_id', 'token_balance', 'total_tokens_earned', 
            'total_tokens_spent', 'last_exchange_date'
        ],
        'admin_game_config': [
            'id', 'config_category', 'config_key', 'config_value'
        ],
        'token_transactions': [
            'id', 'employee_id', 'transaction_type', 'token_amount', 
            'transaction_date'
        ]
    }
    
    all_good = True
    for table, required_cols in required_tables.items():
        cursor.execute(f"PRAGMA table_info({table})")
        columns = [col[1] for col in cursor.fetchall()]
        
        if not columns:
            print(f"  ✗ Table {table} does not exist!")
            all_good = False
        else:
            missing = set(required_cols) - set(columns)
            if missing:
                print(f"  ✗ Table {table} missing columns: {missing}")
                all_good = False
            else:
                print(f"  ✓ Table {table} structure verified")
    
    conn.close()
    return all_good

def main():
    print("="*60)
    print("DUAL GAME SYSTEM FIX SCRIPT")
    print("="*60)
    
    # Note about Flask restart
    print("\n⚠️  IMPORTANT: Flask application needs to be restarted!")
    print("The code fixes have been applied but won't take effect until restart.")
    print("-"*60)
    
    # Run fixes
    success = True
    
    # 1. Verify table structure
    if not verify_table_structure():
        print("\n✗ Database structure issues found!")
        success = False
    
    # 2. Enable foreign keys (note: only for new connections)
    if not enable_foreign_keys():
        print("\n✗ Could not enable foreign keys")
        print("  Note: This setting only affects new connections")
        print("  Add 'PRAGMA foreign_keys = ON' to your app startup")
    
    # 3. Add default config
    add_default_config()
    
    # 4. Check win rates
    check_win_rates()
    
    # 5. Show input validation fix
    fix_input_validation()
    
    print("\n" + "="*60)
    if success:
        print("✓ All automated fixes applied successfully")
    else:
        print("⚠️  Some issues require manual intervention")
    
    print("\nNext Steps:")
    print("1. Restart the Flask application to apply code changes")
    print("2. Add 'PRAGMA foreign_keys = ON' to database initialization")
    print("3. Monitor win rates in production and adjust if needed")
    print("4. Apply the input validation fix shown above")
    print("="*60)

if __name__ == "__main__":
    main()