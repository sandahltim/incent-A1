#!/usr/bin/env python3
"""
Setup script for the revolutionary dual game system.
Creates all necessary database tables and initial configuration.
"""

import sqlite3
import json
from datetime import datetime

def setup_dual_game_system():
    """Create all tables and setup for the dual game system."""
    
    conn = sqlite3.connect('incentive.db')
    conn.execute('PRAGMA foreign_keys = ON')
    
    try:
        # Employee token balances and history
        conn.execute('''
            CREATE TABLE IF NOT EXISTS employee_tokens (
                employee_id TEXT PRIMARY KEY,
                token_balance INTEGER DEFAULT 0,
                total_tokens_earned INTEGER DEFAULT 0,
                total_tokens_spent INTEGER DEFAULT 0,
                last_exchange_date TIMESTAMP,
                daily_exchange_count INTEGER DEFAULT 0,
                daily_exchange_limit INTEGER DEFAULT 50,
                exchange_cooldown_hours INTEGER DEFAULT 24,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        ''')
        
        # Token exchange transactions
        conn.execute('''
            CREATE TABLE IF NOT EXISTS token_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id TEXT,
                transaction_type TEXT, -- 'purchase', 'win', 'spend', 'admin_award'
                points_amount INTEGER, -- points spent/earned (null for non-point transactions)
                token_amount INTEGER, -- tokens gained/lost
                exchange_rate REAL, -- points per token at time of transaction
                transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                game_id INTEGER, -- associated game if applicable
                admin_notes TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        ''')
        
        # Individual prize limits and tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS employee_prize_limits (
                employee_id TEXT,
                prize_type TEXT, -- 'jackpot_cash', 'pto_hours', 'major_points'
                tier_level TEXT,
                monthly_limit INTEGER,
                monthly_used INTEGER DEFAULT 0,
                last_reset_date DATE DEFAULT (date('now', 'start of month')),
                PRIMARY KEY (employee_id, prize_type, tier_level),
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        ''')
        
        # Global prize pool tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS global_prize_pools (
                prize_type TEXT PRIMARY KEY,
                daily_limit INTEGER,
                daily_used INTEGER DEFAULT 0,
                weekly_limit INTEGER,
                weekly_used INTEGER DEFAULT 0,
                monthly_limit INTEGER,
                monthly_used INTEGER DEFAULT 0,
                last_daily_reset DATE DEFAULT (date('now')),
                last_weekly_reset DATE DEFAULT (date('now', 'weekday 0', '-7 days')),
                last_monthly_reset DATE DEFAULT (date('now', 'start of month'))
            )
        ''')
        
        # Dynamic admin settings for both systems
        conn.execute('''
            CREATE TABLE IF NOT EXISTS admin_game_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_category TEXT, -- 'reward_system', 'gambling_system', 'token_economy'
                config_key TEXT,
                config_value TEXT, -- JSON for complex values
                tier_specific TEXT, -- null for global, or specific tier
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by TEXT -- admin user who made change
            )
        ''')
        
        # Behavioral monitoring and alerts
        conn.execute('''
            CREATE TABLE IF NOT EXISTS employee_behavior_flags (
                employee_id TEXT,
                flag_type TEXT, -- 'excessive_gambling', 'token_hoarding', 'prize_limit_reached'
                flag_severity TEXT, -- 'info', 'warning', 'alert'
                flag_data TEXT, -- JSON with details
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_date TIMESTAMP,
                resolved_by TEXT,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        ''')
        
        # Enhanced employee tier tracking
        conn.execute('''
            CREATE TABLE IF NOT EXISTS employee_tiers (
                employee_id TEXT PRIMARY KEY,
                tier_level TEXT DEFAULT 'bronze', -- bronze, silver, gold, platinum
                tier_start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                games_played INTEGER DEFAULT 0,
                total_wins INTEGER DEFAULT 0,
                total_prizes_won INTEGER DEFAULT 0,
                performance_average REAL DEFAULT 0.0,
                streak_count INTEGER DEFAULT 0,
                last_tier_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
            )
        ''')
        
        print("✓ Created dual system base tables")
        
        # Add columns to existing tables
        try:
            # Add dual system columns to mini_games
            conn.execute('ALTER TABLE mini_games ADD COLUMN game_category TEXT DEFAULT "reward"') # 'reward' or 'gambling'
            conn.execute('ALTER TABLE mini_games ADD COLUMN guaranteed_win BOOLEAN DEFAULT 0')
            conn.execute('ALTER TABLE mini_games ADD COLUMN token_cost INTEGER') # for gambling games
            conn.execute('ALTER TABLE mini_games ADD COLUMN individual_odds_used TEXT') # JSON of individual limits applied
            conn.execute('ALTER TABLE mini_games ADD COLUMN global_pool_source TEXT') # which global pool was used
            print("✓ Enhanced mini_games table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Warning: mini_games enhancement - {e}")
        
        try:
            # Add token tracking to employees
            conn.execute('ALTER TABLE employees ADD COLUMN token_balance INTEGER DEFAULT 0')
            conn.execute('ALTER TABLE employees ADD COLUMN preferred_game_category TEXT DEFAULT "reward"')
            conn.execute('ALTER TABLE employees ADD COLUMN gambling_risk_profile TEXT DEFAULT "conservative"') # conservative, moderate, aggressive
            conn.execute('ALTER TABLE employees ADD COLUMN last_token_exchange TIMESTAMP')
            conn.execute('ALTER TABLE employees ADD COLUMN tier_level TEXT DEFAULT "bronze"')
            print("✓ Enhanced employees table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e):
                print(f"Warning: employees enhancement - {e}")
        
        # Setup default global prize pools
        default_pools = [
            ('jackpot_1000_pts', 1, 0, 5, 0, 15, 0),  # 1 per day, 5 per week, 15 per month
            ('cash_prize_100', 2, 0, 8, 0, 25, 0),    # 2 per day, 8 per week, 25 per month
            ('cash_prize_50', 3, 0, 12, 0, 40, 0),    # 3 per day, 12 per week, 40 per month
            ('vacation_day', 1, 0, 2, 0, 5, 0),       # 1 per day, 2 per week, 5 per month
            ('pto_4_hours', 2, 0, 6, 0, 20, 0),       # 2 per day, 6 per week, 20 per month
            ('major_points_500', 3, 0, 15, 0, 50, 0), # 3 per day, 15 per week, 50 per month
        ]
        
        for pool in default_pools:
            conn.execute('''
                INSERT OR IGNORE INTO global_prize_pools 
                (prize_type, daily_limit, daily_used, weekly_limit, weekly_used, monthly_limit, monthly_used)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', pool)
        
        print("✓ Setup default global prize pools")
        
        # Setup default admin configuration
        default_configs = [
            ('token_economy', 'bronze_exchange_rate', '10', 'bronze'),
            ('token_economy', 'silver_exchange_rate', '8', 'silver'),
            ('token_economy', 'gold_exchange_rate', '6', 'gold'),
            ('token_economy', 'platinum_exchange_rate', '5', 'platinum'),
            ('token_economy', 'bronze_daily_limit', '50', 'bronze'),
            ('token_economy', 'silver_daily_limit', '100', 'silver'),
            ('token_economy', 'gold_daily_limit', '200', 'gold'),
            ('token_economy', 'platinum_daily_limit', '500', 'platinum'),
            ('reward_system', 'budget_allocation', '60', None),  # 60% for guaranteed rewards
            ('gambling_system', 'budget_allocation', '40', None), # 40% for gambling pool
            ('reward_system', 'bronze_jackpot_limit', '1', 'bronze'),  # 1 jackpot per month
            ('reward_system', 'silver_jackpot_limit', '2', 'silver'),
            ('reward_system', 'gold_jackpot_limit', '3', 'gold'),
            ('reward_system', 'platinum_jackpot_limit', '5', 'platinum'),
            ('gambling_system', 'addiction_prevention', '1', None), # enabled
        ]
        
        for config in default_configs:
            conn.execute('''
                INSERT OR IGNORE INTO admin_game_config 
                (config_category, config_key, config_value, tier_specific, updated_by)
                VALUES (?, ?, ?, ?, 'SYSTEM_INIT')
            ''', config)
        
        print("✓ Setup default admin configuration")
        
        # Initialize employee token accounts for existing employees
        conn.execute('''
            INSERT OR IGNORE INTO employee_tokens (employee_id)
            SELECT employee_id FROM employees
        ''')
        
        # Initialize employee tier records for existing employees
        conn.execute('''
            INSERT OR IGNORE INTO employee_tiers (employee_id)
            SELECT employee_id FROM employees
        ''')
        
        print("✓ Initialized existing employee accounts")
        
        # Create indexes for performance
        indexes = [
            'CREATE INDEX IF NOT EXISTS idx_token_transactions_employee ON token_transactions(employee_id)',
            'CREATE INDEX IF NOT EXISTS idx_token_transactions_date ON token_transactions(transaction_date)',
            'CREATE INDEX IF NOT EXISTS idx_employee_prize_limits_employee ON employee_prize_limits(employee_id)',
            'CREATE INDEX IF NOT EXISTS idx_behavior_flags_employee ON employee_behavior_flags(employee_id)',
            'CREATE INDEX IF NOT EXISTS idx_behavior_flags_type ON employee_behavior_flags(flag_type)',
            'CREATE INDEX IF NOT EXISTS idx_mini_games_category ON mini_games(game_category)',
        ]
        
        for index in indexes:
            conn.execute(index)
        
        print("✓ Created performance indexes")
        
        conn.commit()
        print("\n🎉 DUAL GAME SYSTEM SETUP COMPLETE!")
        print("\nNew features enabled:")
        print("- Token economy with tier-based exchange rates")
        print("- Category A: Guaranteed win reward games")  
        print("- Category B: Risk-based gambling games")
        print("- Individual and global prize limits")
        print("- Comprehensive admin controls")
        print("- Behavioral monitoring and addiction prevention")
        print("- Enhanced analytics and tracking")
        
        return True
        
    except Exception as e:
        print(f"❌ Error setting up dual game system: {e}")
        conn.rollback()
        return False
    
    finally:
        conn.close()

def verify_setup():
    """Verify that the dual game system was setup correctly."""
    conn = sqlite3.connect('incentive.db')
    
    try:
        # Check tables exist
        tables_to_check = [
            'employee_tokens',
            'token_transactions', 
            'employee_prize_limits',
            'global_prize_pools',
            'admin_game_config',
            'employee_behavior_flags',
            'employee_tiers'
        ]
        
        for table in tables_to_check:
            result = conn.execute(f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table}'").fetchone()
            if result[0] == 0:
                print(f"❌ Table {table} not found")
                return False
            else:
                print(f"✓ Table {table} exists")
        
        # Check global prize pools
        pools = conn.execute("SELECT COUNT(*) FROM global_prize_pools").fetchone()[0]
        print(f"✓ Global prize pools configured: {pools}")
        
        # Check admin config
        configs = conn.execute("SELECT COUNT(*) FROM admin_game_config").fetchone()[0] 
        print(f"✓ Admin configurations: {configs}")
        
        # Check employee accounts
        token_accounts = conn.execute("SELECT COUNT(*) FROM employee_tokens").fetchone()[0]
        tier_accounts = conn.execute("SELECT COUNT(*) FROM employee_tiers").fetchone()[0]
        print(f"✓ Employee token accounts: {token_accounts}")
        print(f"✓ Employee tier accounts: {tier_accounts}")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False
    
    finally:
        conn.close()

if __name__ == "__main__":
    print("Setting up Revolutionary Dual Game System...")
    print("=" * 50)
    
    if setup_dual_game_system():
        print("\n" + "=" * 50)
        print("Verifying setup...")
        if verify_setup():
            print("\n🎯 DUAL GAME SYSTEM READY!")
            print("\nNext steps:")
            print("1. Restart the Flask application")
            print("2. Access admin panel to configure prize pools") 
            print("3. Test token exchange functionality")
            print("4. Begin Category A reward game testing")
        else:
            print("\n❌ Setup verification failed")
    else:
        print("\n❌ Setup failed")