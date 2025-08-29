#!/usr/bin/env python3
"""
Database Migration: Add Refined Dual Game System Tables
Adds necessary tables and columns for the enhanced dual game system.
"""

import sqlite3
import logging
from datetime import datetime
from incentive_service import DatabaseConnection

def migrate_database():
    """Run database migrations for refined dual game system"""
    
    migrations_run = []
    
    try:
        with DatabaseConnection() as conn:
            
            # 1. Add difficulty_level to mini_games table
            try:
                conn.execute("""
                    ALTER TABLE mini_games 
                    ADD COLUMN difficulty_level INTEGER DEFAULT 2
                """)
                migrations_run.append("Added difficulty_level to mini_games")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            # 2. Add achievement_source to mini_games table  
            try:
                conn.execute("""
                    ALTER TABLE mini_games
                    ADD COLUMN achievement_source TEXT
                """)
                migrations_run.append("Added achievement_source to mini_games")
            except sqlite3.OperationalError:
                pass
            
            # 3. Create employee_performance table for tracking metrics
            conn.execute("""
                CREATE TABLE IF NOT EXISTS employee_performance (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT NOT NULL,
                    date DATE NOT NULL,
                    completion_rate REAL DEFAULT 0.0,
                    quality_score REAL DEFAULT 0.0,
                    consistency REAL DEFAULT 0.0,
                    tasks_completed INTEGER DEFAULT 0,
                    tasks_assigned INTEGER DEFAULT 0,
                    bonus_earned INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
                    UNIQUE(employee_id, date)
                )
            """)
            migrations_run.append("Created employee_performance table")
            
            # 4. Create employee_stats table for boost tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS employee_stats (
                    employee_id TEXT PRIMARY KEY,
                    last_boost_time TIMESTAMP,
                    boost_count INTEGER DEFAULT 0,
                    consecutive_losses INTEGER DEFAULT 0,
                    score_percentile REAL,
                    last_percentile_calc TIMESTAMP,
                    total_gambling_wins INTEGER DEFAULT 0,
                    total_gambling_losses INTEGER DEFAULT 0,
                    highest_win_streak INTEGER DEFAULT 0,
                    current_win_streak INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
                )
            """)
            migrations_run.append("Created employee_stats table")
            
            # 5. Enhanced employee_tokens table
            try:
                conn.execute("""
                    ALTER TABLE employee_tokens
                    ADD COLUMN last_activity_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                """)
                migrations_run.append("Added last_activity_date to employee_tokens")
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute("""
                    ALTER TABLE employee_tokens
                    ADD COLUMN last_reversal_date TIMESTAMP
                """)
                migrations_run.append("Added last_reversal_date to employee_tokens")
            except sqlite3.OperationalError:
                pass
            
            # 6. Create prize_awards table for tracking all prizes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prize_awards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    prize_type TEXT NOT NULL,
                    prize_value TEXT,
                    awarded_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed BOOLEAN DEFAULT 0,
                    processed_date TIMESTAMP,
                    admin_notes TEXT,
                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
                )
            """)
            migrations_run.append("Created prize_awards table")
            
            # 7. Create game_sessions table for performance tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS game_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id TEXT NOT NULL,
                    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_end TIMESTAMP,
                    games_played INTEGER DEFAULT 0,
                    tokens_spent INTEGER DEFAULT 0,
                    points_won INTEGER DEFAULT 0,
                    category_a_played INTEGER DEFAULT 0,
                    category_b_played INTEGER DEFAULT 0,
                    peak_balance INTEGER DEFAULT 0,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
                )
            """)
            migrations_run.append("Created game_sessions table")
            
            # 8. Create difficulty_mappings table for rule-to-difficulty mapping
            conn.execute("""
                CREATE TABLE IF NOT EXISTS difficulty_mappings (
                    rule_id INTEGER PRIMARY KEY,
                    difficulty_level INTEGER NOT NULL,
                    custom_multiplier REAL,
                    notes TEXT,
                    updated_by TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (rule_id) REFERENCES rules(rule_id)
                )
            """)
            migrations_run.append("Created difficulty_mappings table")
            
            # 9. Add tier_level to employees if not exists
            try:
                conn.execute("""
                    ALTER TABLE employees
                    ADD COLUMN tier_level TEXT DEFAULT 'bronze'
                """)
                migrations_run.append("Added tier_level to employees")
            except sqlite3.OperationalError:
                pass
            
            # 10. Create scheduled_tasks table for automation
            conn.execute("""
                CREATE TABLE IF NOT EXISTS scheduled_tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT UNIQUE NOT NULL,
                    last_run TIMESTAMP,
                    next_run TIMESTAMP,
                    frequency TEXT,
                    enabled BOOLEAN DEFAULT 1,
                    last_result TEXT,
                    error_count INTEGER DEFAULT 0
                )
            """)
            migrations_run.append("Created scheduled_tasks table")
            
            # 11. Insert default scheduled tasks
            default_tasks = [
                ('monthly_reset', None, datetime.now().replace(day=1, hour=0, minute=0, second=0).isoformat(), 'monthly', 1),
                ('daily_token_reset', None, datetime.now().replace(hour=0, minute=0, second=0).isoformat(), 'daily', 1),
                ('auto_token_reversal', None, datetime.now().replace(hour=2, minute=0, second=0).isoformat(), 'daily', 1),
                ('calculate_percentiles', None, datetime.now().isoformat(), 'hourly', 1),
                ('expire_games', None, datetime.now().replace(hour=23, minute=59, second=0).isoformat(), 'daily', 1)
            ]
            
            for task in default_tasks:
                conn.execute("""
                    INSERT OR IGNORE INTO scheduled_tasks (task_name, last_run, next_run, frequency, enabled)
                    VALUES (?, ?, ?, ?, ?)
                """, task)
            
            migrations_run.append("Inserted default scheduled tasks")
            
            # 12. Create indexes for performance
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_mini_games_employee ON mini_games(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_mini_games_status ON mini_games(status)",
                "CREATE INDEX IF NOT EXISTS idx_mini_games_category ON mini_games(game_category)",
                "CREATE INDEX IF NOT EXISTS idx_token_transactions_employee ON token_transactions(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_token_transactions_date ON token_transactions(transaction_date)",
                "CREATE INDEX IF NOT EXISTS idx_employee_performance_date ON employee_performance(date)",
                "CREATE INDEX IF NOT EXISTS idx_prize_awards_employee ON prize_awards(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_prize_awards_processed ON prize_awards(processed)",
                "CREATE INDEX IF NOT EXISTS idx_game_sessions_employee ON game_sessions(employee_id)",
                "CREATE INDEX IF NOT EXISTS idx_game_sessions_start ON game_sessions(session_start)"
            ]
            
            for index_sql in indexes:
                conn.execute(index_sql)
            
            migrations_run.append("Created performance indexes")
            
            # 13. Update global_prize_pools with required columns
            try:
                conn.execute("""
                    ALTER TABLE global_prize_pools
                    ADD COLUMN prize_description TEXT
                """)
                migrations_run.append("Added prize_description to global_prize_pools")
            except sqlite3.OperationalError:
                pass
            
            try:
                conn.execute("""
                    ALTER TABLE global_prize_pools
                    ADD COLUMN category TEXT DEFAULT 'category_b'
                """)
                migrations_run.append("Added category to global_prize_pools")
            except sqlite3.OperationalError:
                pass
            
            # 14. Insert default global prize pools if not exist
            default_pools = [
                ('jackpot', 1, 5, 20, 'Jackpot Prize', 'category_b'),
                ('major', 5, 25, 100, 'Major Prize', 'category_b'),
                ('minor', 20, 100, 400, 'Minor Prize', 'category_b'),
                ('basic', 100, 500, 2000, 'Basic Prize', 'category_b')
            ]
            
            for pool in default_pools:
                conn.execute("""
                    INSERT OR IGNORE INTO global_prize_pools 
                    (prize_type, daily_limit, weekly_limit, monthly_limit, prize_description, category)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, pool)
            
            migrations_run.append("Inserted default prize pools")
            
            # 15. Add configuration to settings
            conn.execute("""
                INSERT OR IGNORE INTO settings (key, value)
                VALUES ('dual_game_config', '{}')
            """)
            migrations_run.append("Added dual_game_config to settings")
            
            # 16. Create employee tiers mapping
            conn.execute("""
                UPDATE employees 
                SET tier_level = CASE 
                    WHEN score >= 1000 THEN 'platinum'
                    WHEN score >= 500 THEN 'gold'
                    WHEN score >= 200 THEN 'silver'
                    ELSE 'bronze'
                END
                WHERE tier_level IS NULL
            """)
            migrations_run.append("Set initial employee tiers")
            
            conn.commit()
            
            # Log migration completion
            logging.info(f"Database migration completed. Changes: {', '.join(migrations_run)}")
            
            return True, migrations_run
            
    except Exception as e:
        logging.error(f"Migration failed: {e}")
        return False, [str(e)]

def rollback_migration():
    """Rollback migration changes (use with caution)"""
    
    try:
        with DatabaseConnection() as conn:
            # This would remove the new tables - use carefully!
            tables_to_drop = [
                'employee_performance',
                'employee_stats', 
                'prize_awards',
                'game_sessions',
                'difficulty_mappings',
                'scheduled_tasks'
            ]
            
            for table in tables_to_drop:
                conn.execute(f"DROP TABLE IF EXISTS {table}")
            
            conn.commit()
            logging.info("Migration rolled back")
            return True
            
    except Exception as e:
        logging.error(f"Rollback failed: {e}")
        return False

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        print("Rolling back migration...")
        if rollback_migration():
            print("Rollback successful")
        else:
            print("Rollback failed")
    else:
        print("Running database migration...")
        success, changes = migrate_database()
        
        if success:
            print("Migration successful!")
            print("Changes made:")
            for change in changes:
                print(f"  - {change}")
        else:
            print("Migration failed!")
            print("Errors:")
            for error in changes:
                print(f"  - {error}")