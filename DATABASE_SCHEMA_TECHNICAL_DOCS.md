# Database Schema Technical Documentation

**Version**: 1.0.0  
**Date**: August 29, 2025  
**Target Audience**: Developers, System Administrators, Database Administrators  

## Table of Contents

1. [Database Overview](#database-overview)
2. [Core Tables](#core-tables)
3. [Dual Game System Tables](#dual-game-system-tables)
4. [Legacy Game Tables](#legacy-game-tables)
5. [Administrative Tables](#administrative-tables)
6. [Analytics and Monitoring Tables](#analytics-and-monitoring-tables)
7. [Indexes and Performance](#indexes-and-performance)
8. [Database Migrations](#database-migrations)
9. [Backup and Recovery](#backup-and-recovery)
10. [Data Integrity Constraints](#data-integrity-constraints)

## Database Overview

The system uses SQLite 3 with connection pooling for high-performance concurrent access. The schema supports both legacy functionality and the new dual game system.

### Database Configuration

```python
# config.py
INCENTIVE_DB_FILE = "/home/tim/incentDev/incentive.db"
DB_POOL_SIZE = 10
DB_POOL_TIMEOUT = 30
DB_POOL_MAX_RETRIES = 3
DB_POOL_HEALTH_CHECK_INTERVAL = 300
```

### Connection Management

```python
# Connection pool with transaction management
class DatabaseConnection:
    def __init__(self):
        self.pool = ConnectionPool(
            database_path=Config.INCENTIVE_DB_FILE,
            pool_size=Config.DB_POOL_SIZE,
            timeout=Config.DB_POOL_TIMEOUT
        )
    
    def __enter__(self):
        return self.pool.get_connection()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.connection.rollback()
        self.pool.return_connection(self.connection)
```

## Core Tables

### employees

**Purpose**: Central employee registry with authentication and tier information

```sql
CREATE TABLE employees (
    employee_id TEXT PRIMARY KEY,              -- Format: E001, E002, etc.
    name TEXT NOT NULL,                        -- Full employee name
    initials TEXT UNIQUE NOT NULL,             -- Unique initials for voting
    score INTEGER DEFAULT 50,                  -- Current point balance
    role TEXT,                                 -- Employee role (Driver, Laborer, etc.)
    active INTEGER DEFAULT 1,                 -- 1=active, 0=retired
    last_decay_date TEXT DEFAULT NULL,         -- Last point decay date
    pin_hash TEXT,                            -- Hashed PIN for authentication
    -- Dual system columns
    token_balance INTEGER DEFAULT 0,           -- Current token balance
    preferred_game_category TEXT DEFAULT 'reward',  -- 'reward' or 'gambling'
    gambling_risk_profile TEXT DEFAULT 'conservative', -- Risk assessment
    last_token_exchange TIMESTAMP,            -- Last token exchange time
    tier_level TEXT DEFAULT 'bronze'          -- bronze, silver, gold, platinum
);
```

**Key Relationships**:
- Parent to `mini_games`, `votes`, `employee_tokens`
- Referenced by `score_history`, `voting_results`

**Indexes**:
```sql
CREATE INDEX idx_employees_active ON employees(active);
CREATE INDEX idx_employees_tier ON employees(tier_level);
CREATE INDEX idx_employees_role ON employees(role);
```

### admins

**Purpose**: Administrative user accounts with role-based access

```sql
CREATE TABLE admins (
    admin_id TEXT PRIMARY KEY,                 -- Unique admin identifier
    username TEXT UNIQUE NOT NULL,            -- Login username
    password TEXT NOT NULL,                   -- Hashed password
    is_master INTEGER DEFAULT 0              -- 1=master admin, 0=regular admin
);
```

**Default Accounts**:
```sql
INSERT INTO admins VALUES 
    ('admin1', 'admin1', '$hashed_password', 0),
    ('admin2', 'admin2', '$hashed_password', 0),
    ('admin3', 'admin3', '$hashed_password', 0),
    ('master', 'master', '$hashed_password', 1);
```

## Dual Game System Tables

### employee_tokens

**Purpose**: Token economy management for Category B gambling games

```sql
CREATE TABLE employee_tokens (
    employee_id TEXT PRIMARY KEY,             -- Links to employees table
    token_balance INTEGER DEFAULT 0,          -- Current token balance
    total_tokens_earned INTEGER DEFAULT 0,    -- Lifetime tokens earned
    total_tokens_spent INTEGER DEFAULT 0,     -- Lifetime tokens spent
    last_exchange_date TIMESTAMP,            -- Last points-to-tokens exchange
    daily_exchange_count INTEGER DEFAULT 0,   -- Exchanges today (resets daily)
    daily_exchange_limit INTEGER DEFAULT 50,  -- Max exchanges per day
    exchange_cooldown_hours INTEGER DEFAULT 24, -- Hours between exchanges
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
```

**Business Rules**:
- Exchange rates vary by employee tier (bronze: 10:1, platinum: 5:1)
- Daily limits prevent excessive token generation
- Cooldown periods control exchange frequency

### token_transactions

**Purpose**: Complete audit trail of all token-related transactions

```sql
CREATE TABLE token_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,                         -- Employee involved
    transaction_type TEXT,                    -- 'purchase', 'win', 'spend', 'admin_award'
    points_amount INTEGER,                    -- Points involved (null for non-point transactions)
    token_amount INTEGER,                     -- Tokens gained/lost
    exchange_rate REAL,                       -- Points per token at transaction time
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    game_id INTEGER,                          -- Associated game (if applicable)
    admin_notes TEXT,                         -- Additional context
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
```

**Transaction Types**:
- `purchase`: Employee exchanges points for tokens
- `spend`: Employee spends tokens on games
- `win`: Employee wins tokens from games
- `admin_award`: Administrator awards tokens

### employee_prize_limits

**Purpose**: Individual monthly prize limits for Category A games

```sql
CREATE TABLE employee_prize_limits (
    employee_id TEXT,                         -- Employee identifier
    prize_type TEXT,                          -- 'jackpot_cash', 'pto_hours', 'major_points'
    tier_level TEXT,                          -- Tier when limit was set
    monthly_limit INTEGER,                   -- Max prizes this month
    monthly_used INTEGER DEFAULT 0,          -- Prizes used this month
    last_reset_date DATE DEFAULT (date('now', 'start of month')),
    PRIMARY KEY (employee_id, prize_type, tier_level),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
```

**Tier-Based Limits** (per month):
- Bronze: 1 jackpot, 2 PTO hours, 5 major points
- Silver: 2 jackpots, 4 PTO hours, 8 major points  
- Gold: 3 jackpots, 6 PTO hours, 12 major points
- Platinum: 5 jackpots, 8 PTO hours, 20 major points

### global_prize_pools

**Purpose**: Global limits on high-value prizes for Category B games

```sql
CREATE TABLE global_prize_pools (
    prize_type TEXT PRIMARY KEY,             -- Unique prize identifier
    daily_limit INTEGER,                     -- Max awards per day
    daily_used INTEGER DEFAULT 0,           -- Used today
    weekly_limit INTEGER,                   -- Max awards per week
    weekly_used INTEGER DEFAULT 0,          -- Used this week
    monthly_limit INTEGER,                  -- Max awards per month
    monthly_used INTEGER DEFAULT 0,         -- Used this month
    last_daily_reset DATE DEFAULT (date('now')),
    last_weekly_reset DATE DEFAULT (date('now', 'weekday 0', '-7 days')),
    last_monthly_reset DATE DEFAULT (date('now', 'start of month'))
);
```

**Default Prize Pools**:
```sql
INSERT INTO global_prize_pools VALUES
    ('jackpot_1000_pts', 1, 0, 5, 0, 15, 0, date('now'), date('now', 'weekday 0', '-7 days'), date('now', 'start of month')),
    ('cash_prize_100', 2, 0, 8, 0, 25, 0, date('now'), date('now', 'weekday 0', '-7 days'), date('now', 'start of month')),
    ('vacation_day', 1, 0, 2, 0, 5, 0, date('now'), date('now', 'weekday 0', '-7 days'), date('now', 'start of month'));
```

### employee_behavior_flags

**Purpose**: Addiction prevention and behavioral monitoring

```sql
CREATE TABLE employee_behavior_flags (
    employee_id TEXT,                         -- Flagged employee
    flag_type TEXT,                           -- 'excessive_gambling', 'token_hoarding', etc.
    flag_severity TEXT,                       -- 'info', 'warning', 'alert'
    flag_data TEXT,                           -- JSON with flag details
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_date TIMESTAMP,                 -- When flag was cleared
    resolved_by TEXT,                        -- Who resolved the flag
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
```

**Flag Types**:
- `excessive_gambling`: Too many games in short period
- `token_hoarding`: Accumulating tokens without spending
- `prize_limit_reached`: Hit monthly prize limits
- `unusual_patterns`: Abnormal gaming behavior

## Legacy Game Tables

### mini_games

**Purpose**: Enhanced game tracking for both legacy and dual systems

```sql
CREATE TABLE mini_games (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,            -- Employee who owns the game
    game_type TEXT NOT NULL,                 -- 'slot', 'scratch', 'roulette', etc.
    awarded_date DATETIME NOT NULL,          -- When game was awarded
    played_date DATETIME,                    -- When game was played (null if unplayed)
    status TEXT NOT NULL DEFAULT 'unused',   -- 'unused', 'played'
    outcome TEXT,                            -- 'win', 'loss' (null if unplayed)
    -- Dual system enhancements
    game_category TEXT DEFAULT 'reward',     -- 'reward' (Category A) or 'gambling' (Category B)
    guaranteed_win BOOLEAN DEFAULT 0,        -- 1 for Category A games
    token_cost INTEGER,                      -- Cost in tokens for Category B
    individual_odds_used TEXT,               -- JSON: individual limits applied
    global_pool_source TEXT,                -- Global pool used for prize
    tier_level TEXT,                         -- Employee tier at play time
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
```

**Enhanced Columns**:
- `game_category`: Distinguishes Category A (reward) from Category B (gambling)
- `guaranteed_win`: Boolean flag for guaranteed win games
- `token_cost`: Tokens spent for gambling games
- `individual_odds_used`: JSON data about individual limits
- `global_pool_source`: Which global pool provided the prize

### game_history

**Purpose**: Detailed history of all game plays and outcomes

```sql
CREATE TABLE game_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mini_game_id INTEGER NOT NULL,           -- Links to mini_games
    game_type TEXT,                          -- Type of game played
    play_date DATETIME NOT NULL,             -- When played
    outcome TEXT,                            -- 'win', 'loss'
    prize_type TEXT,                         -- Type of prize won
    prize_amount REAL,                       -- Numeric prize value
    prize_description TEXT,                  -- Human-readable prize description
    -- Dual system enhancements
    token_cost INTEGER,                      -- Tokens spent (Category B only)
    game_category TEXT,                      -- 'reward' or 'gambling'
    guaranteed_win BOOLEAN,                  -- Was this a guaranteed win?
    global_pool_exhausted BOOLEAN DEFAULT 0, -- Was global pool exhausted?
    FOREIGN KEY (mini_game_id) REFERENCES mini_games(id)
);
```

## Administrative Tables

### admin_game_config

**Purpose**: Dynamic configuration for dual game system

```sql
CREATE TABLE admin_game_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_category TEXT,                    -- 'reward_system', 'gambling_system', 'token_economy'
    config_key TEXT,                         -- Specific setting key
    config_value TEXT,                       -- Value (JSON for complex data)
    tier_specific TEXT,                      -- NULL for global, or specific tier
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by TEXT                          -- Admin who made change
);
```

**Configuration Categories**:
```sql
-- Token economy settings
INSERT INTO admin_game_config VALUES
    (NULL, 'token_economy', 'bronze_exchange_rate', '10', 'bronze', CURRENT_TIMESTAMP, 'SYSTEM_INIT'),
    (NULL, 'token_economy', 'silver_exchange_rate', '8', 'silver', CURRENT_TIMESTAMP, 'SYSTEM_INIT'),
    (NULL, 'token_economy', 'gold_exchange_rate', '6', 'gold', CURRENT_TIMESTAMP, 'SYSTEM_INIT'),
    (NULL, 'token_economy', 'platinum_exchange_rate', '5', 'platinum', CURRENT_TIMESTAMP, 'SYSTEM_INIT');

-- System budgets
INSERT INTO admin_game_config VALUES
    (NULL, 'reward_system', 'budget_allocation', '60', NULL, CURRENT_TIMESTAMP, 'SYSTEM_INIT'),
    (NULL, 'gambling_system', 'budget_allocation', '40', NULL, CURRENT_TIMESTAMP, 'SYSTEM_INIT');
```

### settings

**Purpose**: System-wide configuration and settings

```sql
CREATE TABLE settings (
    key TEXT PRIMARY KEY,                    -- Setting name
    value TEXT                               -- Setting value (JSON for complex data)
);
```

**Key Settings**:
```sql
INSERT INTO settings VALUES
    ('voting_thresholds', '{"positive":[{"threshold":90,"points":10}],"negative":[{"threshold":90,"points":-10}]}'),
    ('max_total_votes', '3'),
    ('port', '7410'),  -- Updated from 7409
    ('mini_game_settings', '{"award_chance_points":10,"award_chance_vote":15}'),
    ('site_name', 'A1 Rent-It'),
    ('primary_color', '#D4AF37');
```

### roles

**Purpose**: Employee role definitions and pot percentages

```sql
CREATE TABLE roles (
    role_name TEXT PRIMARY KEY,              -- Role name
    percentage REAL                          -- Percentage of incentive pot
);
```

**Default Roles**:
```sql
INSERT INTO roles VALUES
    ('Driver', 50.0),
    ('Laborer', 40.0),
    ('Supervisor', 9.0),
    ('Warehouse Labor', 1.0),
    ('Master', 0.0);
```

## Analytics and Monitoring Tables

### employee_tiers

**Purpose**: Enhanced tier tracking with performance metrics

```sql
CREATE TABLE employee_tiers (
    employee_id TEXT PRIMARY KEY,            -- Employee identifier
    tier_level TEXT DEFAULT 'bronze',        -- Current tier
    tier_start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    games_played INTEGER DEFAULT 0,          -- Total games played
    total_wins INTEGER DEFAULT 0,            -- Total wins
    total_prizes_won INTEGER DEFAULT 0,      -- Total prizes won
    performance_average REAL DEFAULT 0.0,    -- Performance score
    streak_count INTEGER DEFAULT 0,          -- Current winning streak
    last_tier_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
```

**Tier Calculation Logic**:
```sql
-- Tier advancement based on performance
UPDATE employee_tiers 
SET tier_level = CASE
    WHEN games_played >= 20 AND performance_average >= 0.8 THEN 'platinum'
    WHEN games_played >= 15 AND performance_average >= 0.6 THEN 'gold' 
    WHEN games_played >= 10 AND performance_average >= 0.4 THEN 'silver'
    ELSE 'bronze'
END;
```

### Voting and History Tables

#### votes

```sql
CREATE TABLE votes (
    vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
    voter_initials TEXT,                     -- Who voted
    recipient_id TEXT,                       -- Who received the vote
    vote_value INTEGER CHECK(vote_value IN (-1, 0, 1)), -- -1, 0, or 1
    vote_date TEXT,                          -- When vote was cast
    UNIQUE(voter_initials, recipient_id, vote_date),
    FOREIGN KEY(recipient_id) REFERENCES employees(employee_id)
);
```

#### score_history

```sql
CREATE TABLE score_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,                        -- Employee affected
    changed_by TEXT,                         -- Who made the change
    points INTEGER,                          -- Points added/removed
    reason TEXT,                             -- Reason for change
    notes TEXT DEFAULT '',                   -- Additional notes
    date TEXT,                               -- When change occurred
    month_year TEXT,                         -- Month/year for reporting
    FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
);
```

#### voting_results

```sql
CREATE TABLE voting_results (
    session_id INTEGER,                      -- Voting session
    employee_id TEXT,                        -- Employee results
    plus_votes INTEGER,                      -- Positive votes received
    minus_votes INTEGER,                     -- Negative votes received
    plus_percent REAL,                       -- Percentage positive
    minus_percent REAL,                      -- Percentage negative
    points INTEGER,                          -- Points awarded
    FOREIGN KEY(employee_id) REFERENCES employees(employee_id)
);
```

## Indexes and Performance

### Primary Indexes

```sql
-- Core performance indexes
CREATE INDEX idx_employees_active ON employees(active);
CREATE INDEX idx_employees_tier ON employees(tier_level);
CREATE INDEX idx_votes_vote_date ON votes(vote_date);

-- Dual game system indexes
CREATE INDEX idx_token_transactions_employee ON token_transactions(employee_id);
CREATE INDEX idx_token_transactions_date ON token_transactions(transaction_date);
CREATE INDEX idx_token_transactions_type ON token_transactions(transaction_type);
CREATE INDEX idx_employee_prize_limits_employee ON employee_prize_limits(employee_id);
CREATE INDEX idx_behavior_flags_employee ON employee_behavior_flags(employee_id);
CREATE INDEX idx_behavior_flags_type ON employee_behavior_flags(flag_type);

-- Game system indexes
CREATE INDEX idx_mini_games_category ON mini_games(game_category);
CREATE INDEX idx_mini_games_status ON mini_games(status);
CREATE INDEX idx_mini_games_employee ON mini_games(employee_id);
CREATE INDEX idx_game_history_date ON game_history(play_date);
CREATE INDEX idx_game_history_mini_game ON game_history(mini_game_id);

-- Administrative indexes
CREATE INDEX idx_admin_game_config_category ON admin_game_config(config_category);
CREATE INDEX idx_admin_game_config_key ON admin_game_config(config_key);
```

### Composite Indexes

```sql
-- Multi-column indexes for complex queries
CREATE INDEX idx_mini_games_employee_category_status ON mini_games(employee_id, game_category, status);
CREATE INDEX idx_token_transactions_employee_type_date ON token_transactions(employee_id, transaction_type, transaction_date);
CREATE INDEX idx_game_history_category_date ON game_history(game_category, play_date);
CREATE INDEX idx_behavior_flags_employee_severity ON employee_behavior_flags(employee_id, flag_severity);
```

### Query Optimization Examples

```sql
-- Optimized query for employee game summary
EXPLAIN QUERY PLAN
SELECT 
    COUNT(CASE WHEN game_category = 'reward' THEN 1 END) as category_a_total,
    COUNT(CASE WHEN game_category = 'gambling' THEN 1 END) as category_b_total,
    et.token_balance
FROM mini_games mg
JOIN employee_tokens et ON mg.employee_id = et.employee_id  
WHERE mg.employee_id = 'E001';

-- Uses: idx_mini_games_employee, primary key on employee_tokens
```

## Database Migrations

### Migration Script Template

```python
def migrate_to_dual_system():
    """Migration script for dual game system setup."""
    conn = sqlite3.connect('incentive.db')
    conn.execute('PRAGMA foreign_keys = ON')
    
    try:
        conn.execute('BEGIN TRANSACTION')
        
        # 1. Create new tables
        create_dual_system_tables(conn)
        
        # 2. Add columns to existing tables  
        add_dual_system_columns(conn)
        
        # 3. Migrate existing data
        migrate_existing_data(conn)
        
        # 4. Create indexes
        create_performance_indexes(conn)
        
        # 5. Verify integrity
        verify_migration_integrity(conn)
        
        conn.commit()
        print("✅ Migration completed successfully")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        conn.close()
```

### Schema Version Tracking

```sql
-- Track schema versions
CREATE TABLE IF NOT EXISTS schema_versions (
    version TEXT PRIMARY KEY,
    applied_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description TEXT
);

INSERT INTO schema_versions VALUES
    ('1.0.0', '2025-08-29T00:00:00Z', 'Initial dual game system'),
    ('1.0.1', '2025-08-29T12:00:00Z', 'Added behavior monitoring');
```

## Backup and Recovery

### Automated Backup Strategy

```bash
#!/bin/bash
# Backup script (runs nightly)

DB_FILE="/home/tim/incentDev/incentive.db"
BACKUP_DIR="/home/tim/incentDev/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Create consistent backup
sqlite3 "$DB_FILE" ".backup '$BACKUP_DIR/incentive.db.bak-$DATE'"

# Verify backup integrity
sqlite3 "$BACKUP_DIR/incentive.db.bak-$DATE" "PRAGMA integrity_check;"

# Keep last 30 backups
find "$BACKUP_DIR" -name "incentive.db.bak-*" -mtime +30 -delete
```

### Recovery Procedures

```bash
# Restore from backup
cp "/home/tim/incentDev/backups/incentive.db.bak-20250829_120000" "/home/tim/incentDev/incentive.db"

# Verify restored database
sqlite3 "/home/tim/incentDev/incentive.db" "PRAGMA integrity_check;"
```

### Point-in-Time Recovery

```sql
-- Using WAL mode for point-in-time recovery
PRAGMA journal_mode = WAL;
PRAGMA wal_checkpoint(FULL);

-- Create checkpoint backup
.backup /path/to/checkpoint/incentive.db
```

## Data Integrity Constraints

### Foreign Key Constraints

```sql
-- Enable foreign key enforcement
PRAGMA foreign_keys = ON;

-- Key relationships
FOREIGN KEY (employee_id) REFERENCES employees(employee_id) ON DELETE CASCADE
FOREIGN KEY (mini_game_id) REFERENCES mini_games(id) ON DELETE CASCADE
FOREIGN KEY (session_id) REFERENCES voting_sessions(session_id) ON DELETE CASCADE
```

### Check Constraints

```sql
-- Vote values must be -1, 0, or 1
vote_value INTEGER CHECK(vote_value IN (-1, 0, 1))

-- Token balances cannot be negative
token_balance INTEGER CHECK(token_balance >= 0)

-- Prize limits must be positive
monthly_limit INTEGER CHECK(monthly_limit > 0)
daily_limit INTEGER CHECK(daily_limit > 0)

-- Tier levels must be valid
tier_level TEXT CHECK(tier_level IN ('bronze', 'silver', 'gold', 'platinum'))
```

### Unique Constraints

```sql
-- Prevent duplicate votes
UNIQUE(voter_initials, recipient_id, vote_date)

-- Unique employee initials
initials TEXT UNIQUE NOT NULL

-- Unique admin usernames  
username TEXT UNIQUE NOT NULL

-- Unique prize limit per employee/type/tier
PRIMARY KEY (employee_id, prize_type, tier_level)
```

### Triggers for Data Consistency

```sql
-- Update token balance when transactions occur
CREATE TRIGGER update_token_balance_insert
AFTER INSERT ON token_transactions
FOR EACH ROW
BEGIN
    UPDATE employee_tokens 
    SET token_balance = token_balance + NEW.token_amount
    WHERE employee_id = NEW.employee_id;
END;

-- Prevent negative token balances
CREATE TRIGGER prevent_negative_tokens
BEFORE UPDATE ON employee_tokens
FOR EACH ROW
WHEN NEW.token_balance < 0
BEGIN
    SELECT RAISE(ABORT, 'Token balance cannot be negative');
END;

-- Auto-reset daily limits
CREATE TRIGGER reset_daily_exchange_limits
AFTER UPDATE ON employee_tokens
FOR EACH ROW
WHEN date(NEW.last_exchange_date) != date('now')
BEGIN
    UPDATE employee_tokens 
    SET daily_exchange_count = 0
    WHERE employee_id = NEW.employee_id;
END;
```

## Data Validation Queries

### Integrity Checks

```sql
-- Check for orphaned records
SELECT COUNT(*) FROM mini_games mg 
WHERE NOT EXISTS (SELECT 1 FROM employees e WHERE e.employee_id = mg.employee_id);

-- Verify token balance consistency
SELECT et.employee_id, 
       et.token_balance,
       COALESCE(SUM(CASE WHEN tt.token_amount > 0 THEN tt.token_amount ELSE 0 END), 0) as earned,
       COALESCE(SUM(CASE WHEN tt.token_amount < 0 THEN ABS(tt.token_amount) ELSE 0 END), 0) as spent
FROM employee_tokens et
LEFT JOIN token_transactions tt ON et.employee_id = tt.employee_id
GROUP BY et.employee_id
HAVING et.token_balance != (earned - spent);

-- Check global pool limits
SELECT prize_type, daily_used, daily_limit,
       CASE WHEN daily_used > daily_limit THEN 'VIOLATION' ELSE 'OK' END as status
FROM global_prize_pools;
```

### Performance Analysis

```sql
-- Query performance analysis
EXPLAIN QUERY PLAN 
SELECT mg.*, gh.prize_description
FROM mini_games mg
JOIN game_history gh ON mg.id = gh.mini_game_id
WHERE mg.employee_id = 'E001' 
AND mg.game_category = 'gambling'
ORDER BY mg.played_date DESC;

-- Table size analysis
SELECT 
    name,
    COUNT(*) as row_count,
    AVG(LENGTH(sql)) as avg_row_size
FROM sqlite_master m
JOIN pragma_table_info(m.name) p
WHERE m.type = 'table'
GROUP BY name;
```

---

## Database Maintenance

### Regular Maintenance Tasks

```sql
-- Vacuum database (reclaim space)
VACUUM;

-- Analyze query patterns
ANALYZE;

-- Check integrity
PRAGMA integrity_check;

-- Optimize indexes
REINDEX;
```

### Monitoring Queries

```sql
-- Database size
SELECT page_count * page_size as size_bytes FROM pragma_page_count(), pragma_page_size();

-- WAL file size
SELECT * FROM pragma_wal_checkpoint(PASSIVE);

-- Lock status
SELECT * FROM pragma_lock_status();
```

## Related Documentation

- [Dual Game System Technical Architecture](DUAL_GAME_SYSTEM_TECHNICAL_DOCS.md)
- [API Endpoint Documentation](API_ENDPOINTS_TECHNICAL_DOCS.md)
- [CSRF Security Implementation](CSRF_SECURITY_TECHNICAL_DOCS.md)
- [Testing and Validation Procedures](TESTING_VALIDATION_TECHNICAL_DOCS.md)

---

**Last Updated**: August 29, 2025  
**Next Review**: September 29, 2025  
**Maintained By**: Development Team