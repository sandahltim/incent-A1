# Dual Game System Technical Architecture Documentation

**Version**: 1.0.0  
**Date**: August 29, 2025  
**Target Audience**: Developers, System Administrators, Technical Staff  

## Table of Contents

1. [System Overview](#system-overview)
2. [Architecture Components](#architecture-components)
3. [Category A: Guaranteed Reward System](#category-a-guaranteed-reward-system)
4. [Category B: Token-Based Gambling System](#category-b-token-based-gambling-system)
5. [Token Economy Implementation](#token-economy-implementation)
6. [Prize Management System](#prize-management-system)
7. [Database Architecture](#database-architecture)
8. [Business Logic Implementation](#business-logic-implementation)
9. [Security Considerations](#security-considerations)
10. [Performance Optimization](#performance-optimization)
11. [Monitoring and Analytics](#monitoring-and-analytics)

## System Overview

The Dual Game System is a revolutionary implementation that provides two distinct gaming experiences within a single platform:

- **Category A**: Guaranteed win reward games with individual prize limits
- **Category B**: Token-based gambling games with global prize pools and real odds

### Core Principles

1. **Dual Experience**: Satisfy both risk-averse and risk-seeking employee preferences
2. **Budget Protection**: Individual and global limits prevent excessive payouts
3. **Tier-Based Benefits**: Higher-tier employees get better rates and limits
4. **Comprehensive Tracking**: Full audit trail and analytics
5. **Addiction Prevention**: Built-in monitoring and behavioral flags

### Technical Stack

```
Frontend: JavaScript (ES6+), HTML5, CSS3
Backend: Python 3.11, Flask 2.x
Database: SQLite 3 with connection pooling
Security: Flask-WTF CSRF protection
Caching: Custom in-memory cache with TTL
```

## Architecture Components

### Service Layer Architecture

```
┌─────────────────────────────────────────┐
│                Frontend                 │
│  JavaScript Game Controllers           │
└─────────────────────────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│              Flask App                  │
│  CSRF Protected API Endpoints          │
└─────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────┬──────────────────────┐
│  DualGameManager │  TokenEconomyService │
│  Category A & B  │  Exchange & Limits   │
└──────────────────┴──────────────────────┘
                    │
                    ▼
┌─────────────────────────────────────────┐
│           Database Layer                │
│  Connection Pool + Transaction Mgmt     │
└─────────────────────────────────────────┘
```

### Key Service Components

#### 1. DualGameManager (`services/dual_game_manager.py`)

```python
class DualGameManager:
    """Manages both Category A and Category B game systems."""
    
    def __init__(self):
        # Individual prize limits by tier
        self.individual_prize_limits = {
            'bronze': {'jackpot_cash': 1, 'pto_hours': 2, 'major_points': 5},
            'silver': {'jackpot_cash': 2, 'pto_hours': 4, 'major_points': 8},
            'gold': {'jackpot_cash': 3, 'pto_hours': 6, 'major_points': 12},
            'platinum': {'jackpot_cash': 5, 'pto_hours': 8, 'major_points': 20}
        }
```

#### 2. TokenEconomyService (`services/token_economy.py`)

```python
class TokenEconomyService:
    """Manages the token economy for Category B games."""
    
    def __init__(self):
        self.tier_exchange_rates = {
            'bronze': 10,    # 10 points per token
            'silver': 8,     # 8 points per token  
            'gold': 6,       # 6 points per token
            'platinum': 5    # 5 points per token
        }
```

## Category A: Guaranteed Reward System

### Design Philosophy

Category A games provide guaranteed wins with individual monthly limits to control costs while ensuring employee satisfaction.

### Implementation Details

#### Prize Tier System

```python
# Individual prize limits by employee tier (monthly)
INDIVIDUAL_PRIZE_LIMITS = {
    'bronze': {
        'jackpot_cash': 1,      # 1 cash jackpot per month
        'pto_hours': 2,         # 2 PTO hour rewards per month
        'major_points': 5       # 5 major point prizes per month
    },
    'silver': {
        'jackpot_cash': 2,      # 2 cash jackpots per month
        'pto_hours': 4,         # 4 PTO hour rewards per month
        'major_points': 8       # 8 major point prizes per month
    },
    # ... gold, platinum tiers
}
```

#### Game Flow

```python
def play_category_a_game(self, employee_id, game_id):
    """Play a Category A guaranteed win game."""
    with DatabaseConnection() as conn:
        # 1. Verify game belongs to employee and is Category A
        game = self._validate_category_a_game(game_id, employee_id)
        
        # 2. Check individual prize limits
        available_prizes = self._get_available_prizes(employee_id, game['tier_level'])
        
        # 3. Select prize based on tier and availability
        selected_prize = self._select_category_a_prize(game['tier_level'], available_prizes)
        
        # 4. Award prize and update limits
        prize_details = self._award_category_a_prize(conn, employee_id, selected_prize)
        
        # 5. Update game record and create history
        self._update_game_records(conn, game_id, prize_details)
        
        return True, f"Won: {prize_details['description']}", prize_details
```

#### Prize Selection Algorithm

```python
def _select_category_a_prize(self, tier, available_prizes):
    """Weighted prize selection based on tier."""
    weights = {
        'bronze': {'jackpot_cash': 10, 'pto_hours': 15, 'major_points': 25, 'basic_points': 50},
        'silver': {'jackpot_cash': 15, 'pto_hours': 20, 'major_points': 30, 'basic_points': 35},
        'gold': {'jackpot_cash': 20, 'pto_hours': 25, 'major_points': 35, 'basic_points': 20},
        'platinum': {'jackpot_cash': 30, 'pto_hours': 30, 'major_points': 25, 'basic_points': 15}
    }
    
    # Create weighted choices based on availability
    weighted_choices = []
    for prize in available_prizes:
        weight = weights[tier].get(prize['type'], 1)
        weighted_choices.extend([prize] * weight)
    
    return random.choice(weighted_choices)
```

## Category B: Token-Based Gambling System

### Design Philosophy

Category B games use a token-based economy with real gambling mechanics, global prize pools, and tier-based exchange rates.

### Token Exchange System

#### Tier-Based Exchange Rates

```python
TIER_EXCHANGE_RATES = {
    'bronze': 10,    # 10 points = 1 token (worst rate)
    'silver': 8,     # 8 points = 1 token
    'gold': 6,       # 6 points = 1 token  
    'platinum': 5    # 5 points = 1 token (best rate)
}
```

#### Daily Exchange Limits

```python
TIER_DAILY_LIMITS = {
    'bronze': 50,    # 50 tokens per day
    'silver': 100,   # 100 tokens per day
    'gold': 200,     # 200 tokens per day
    'platinum': 500  # 500 tokens per day
}
```

#### Exchange Implementation

```python
def exchange_points_for_tokens(self, employee_id, token_amount, admin_override=False):
    """Exchange employee points for tokens."""
    with DatabaseConnection() as conn:
        # 1. Check eligibility (cooldown, daily limits)
        can_exchange, reason = self.can_exchange_tokens(employee_id)
        if not can_exchange and not admin_override:
            return False, reason
        
        # 2. Calculate cost based on tier
        cost_info, error = self.calculate_exchange_cost(employee_id, token_amount)
        if error:
            return False, error
        
        # 3. Verify sufficient points
        if not cost_info['can_afford'] and not admin_override:
            return False, f"Insufficient points"
        
        # 4. Perform transaction
        self._execute_token_exchange(conn, employee_id, token_amount, cost_info)
        
        return True, f"Exchanged {cost_info['points_cost']} points for {token_amount} tokens"
```

### Gambling Game Mechanics

#### Win Rate Calculation

```python
def _determine_category_b_outcome(self, conn, game_type, tier):
    """Determine outcome using tier-based win rates."""
    base_win_rates = {
        'slots': {'bronze': 0.35, 'silver': 0.38, 'gold': 0.42, 'platinum': 0.45},
        'roulette': {'bronze': 0.28, 'silver': 0.31, 'gold': 0.35, 'platinum': 0.38},
        'dice': {'bronze': 0.32, 'silver': 0.35, 'gold': 0.39, 'platinum': 0.42},
        'wheel': {'bronze': 0.25, 'silver': 0.28, 'gold': 0.32, 'platinum': 0.35}
    }
    
    win_rate = base_win_rates[game_type][tier]
    
    if random.random() > win_rate:
        return {'outcome': 'loss', 'description': 'Better luck next time!'}
    
    # If win, determine prize from global pools
    return self._select_global_prize(conn)
```

#### Global Prize Pool System

```python
def _select_global_prize(self, conn):
    """Select prize from global pools with availability checking."""
    available_prizes = [
        ('major_points_500', 0.4),     # 40% chance
        ('cash_prize_50', 0.25),       # 25% chance
        ('pto_4_hours', 0.15),         # 15% chance
        ('cash_prize_100', 0.1),       # 10% chance
        ('jackpot_1000_pts', 0.05),    # 5% chance
        ('vacation_day', 0.05)         # 5% chance
    ]
    
    # Select based on probability
    selected_prize = self._weighted_random_selection(available_prizes)
    
    # Check global availability
    available, used, limit = self.check_global_prize_availability(selected_prize)
    
    if not available:
        # Fallback to basic points if pool exhausted
        return self._fallback_prize()
    
    # Update global pool usage
    self._update_global_pool_usage(conn, selected_prize)
    
    return self._get_category_b_prize_details(selected_prize)
```

## Token Economy Implementation

### Account Management

```python
def get_employee_token_account(self, employee_id):
    """Get comprehensive token account information."""
    with DatabaseConnection() as conn:
        account = conn.execute("""
            SELECT et.*, e.tier_level, e.score as current_points
            FROM employee_tokens et
            JOIN employees e ON et.employee_id = e.employee_id
            WHERE et.employee_id = ?
        """, (employee_id,)).fetchone()
        
        if not account:
            # Auto-create account for new users
            self._create_token_account(conn, employee_id)
            return self.get_employee_token_account(employee_id)
        
        return dict(account)
```

### Transaction Logging

```python
def _log_token_transaction(self, conn, employee_id, transaction_type, 
                          points_amount=None, token_amount=None, 
                          exchange_rate=None, game_id=None, notes=""):
    """Log all token transactions for audit trail."""
    conn.execute("""
        INSERT INTO token_transactions 
        (employee_id, transaction_type, points_amount, token_amount, 
         exchange_rate, game_id, admin_notes)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (employee_id, transaction_type, points_amount, token_amount,
          exchange_rate, game_id, notes))
```

### Cooldown Management

```python
def can_exchange_tokens(self, employee_id):
    """Check exchange eligibility including cooldowns."""
    account = self.get_employee_token_account(employee_id)
    tier = account.get('tier_level', 'bronze')
    
    # Check daily limit
    daily_limit = self.tier_daily_limits.get(tier, 50)
    if account['daily_exchange_count'] >= daily_limit:
        return False, f"Daily token limit reached ({daily_limit})"
    
    # Check cooldown
    if account['last_exchange_date']:
        last_exchange = datetime.fromisoformat(account['last_exchange_date'])
        cooldown_hours = self.tier_cooldowns.get(tier, 24)
        
        if datetime.now() - last_exchange < timedelta(hours=cooldown_hours):
            remaining = timedelta(hours=cooldown_hours) - (datetime.now() - last_exchange)
            hours_left = int(remaining.total_seconds() // 3600)
            return False, f"Cooldown active: {hours_left} hours remaining"
    
    return True, "Exchange available"
```

## Prize Management System

### Individual Prize Limits

Individual limits prevent employees from winning too many high-value prizes:

```python
def check_individual_prize_limit(self, employee_id, prize_type):
    """Check monthly prize limits for individual employees."""
    with DatabaseConnection() as conn:
        # Get employee tier
        tier = self._get_employee_tier(conn, employee_id)
        
        # Get current month usage
        monthly_used = conn.execute("""
            SELECT COALESCE(monthly_used, 0) 
            FROM employee_prize_limits
            WHERE employee_id = ? AND prize_type = ? AND tier_level = ?
        """, (employee_id, prize_type, tier)).fetchone()
        
        monthly_limit = self.individual_prize_limits[tier].get(prize_type, 0)
        used = monthly_used[0] if monthly_used else 0
        
        return used < monthly_limit, used, monthly_limit
```

### Global Prize Pools

Global pools limit total daily/weekly/monthly payouts across all employees:

```python
def check_global_prize_availability(self, prize_type):
    """Check if global prize is still available today."""
    with DatabaseConnection() as conn:
        pool = conn.execute("""
            SELECT * FROM global_prize_pools WHERE prize_type = ?
        """, (prize_type,)).fetchone()
        
        if not pool:
            return False, 0, 0
        
        # Check if daily reset is needed
        if pool['last_daily_reset'] != datetime.now().date().isoformat():
            self._reset_daily_pool(conn, prize_type)
            daily_used = 0
        else:
            daily_used = pool['daily_used']
        
        available = daily_used < pool['daily_limit']
        return available, daily_used, pool['daily_limit']
```

## Database Architecture

### Core Tables

#### Employee Tokens Table
```sql
CREATE TABLE employee_tokens (
    employee_id TEXT PRIMARY KEY,
    token_balance INTEGER DEFAULT 0,
    total_tokens_earned INTEGER DEFAULT 0,
    total_tokens_spent INTEGER DEFAULT 0,
    last_exchange_date TIMESTAMP,
    daily_exchange_count INTEGER DEFAULT 0,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
```

#### Token Transactions Table
```sql
CREATE TABLE token_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id TEXT,
    transaction_type TEXT, -- 'purchase', 'win', 'spend', 'admin_award'
    points_amount INTEGER,
    token_amount INTEGER,
    exchange_rate REAL,
    transaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    game_id INTEGER,
    admin_notes TEXT,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);
```

#### Global Prize Pools Table
```sql
CREATE TABLE global_prize_pools (
    prize_type TEXT PRIMARY KEY,
    daily_limit INTEGER,
    daily_used INTEGER DEFAULT 0,
    weekly_limit INTEGER,
    weekly_used INTEGER DEFAULT 0,
    monthly_limit INTEGER,
    monthly_used INTEGER DEFAULT 0,
    last_daily_reset DATE,
    last_weekly_reset DATE,
    last_monthly_reset DATE
);
```

#### Enhanced Mini Games Table
```sql
ALTER TABLE mini_games ADD COLUMN game_category TEXT DEFAULT 'reward';
ALTER TABLE mini_games ADD COLUMN guaranteed_win BOOLEAN DEFAULT 0;
ALTER TABLE mini_games ADD COLUMN token_cost INTEGER;
ALTER TABLE mini_games ADD COLUMN individual_odds_used TEXT;
ALTER TABLE mini_games ADD COLUMN global_pool_source TEXT;
ALTER TABLE mini_games ADD COLUMN tier_level TEXT;
```

### Performance Indexes

```sql
-- Token system indexes
CREATE INDEX idx_token_transactions_employee ON token_transactions(employee_id);
CREATE INDEX idx_token_transactions_date ON token_transactions(transaction_date);
CREATE INDEX idx_employee_prize_limits_employee ON employee_prize_limits(employee_id);

-- Game system indexes  
CREATE INDEX idx_mini_games_category ON mini_games(game_category);
CREATE INDEX idx_mini_games_status ON mini_games(status);
CREATE INDEX idx_game_history_date ON game_history(play_date);
```

## Business Logic Implementation

### Tier Advancement System

```python
def calculate_employee_tier(self, employee_id):
    """Calculate employee tier based on performance metrics."""
    with DatabaseConnection() as conn:
        metrics = conn.execute("""
            SELECT 
                COUNT(*) as games_played,
                AVG(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as win_rate,
                SUM(CASE WHEN prize_amount > 100 THEN 1 ELSE 0 END) as big_wins,
                e.score as current_score
            FROM game_history gh
            JOIN mini_games mg ON gh.mini_game_id = mg.id
            JOIN employees e ON mg.employee_id = e.employee_id
            WHERE mg.employee_id = ?
            AND gh.play_date > date('now', '-30 days')
        """, (employee_id,)).fetchone()
        
        # Tier calculation logic
        if metrics['current_score'] >= 500 and metrics['games_played'] >= 20:
            return 'platinum'
        elif metrics['current_score'] >= 300 and metrics['games_played'] >= 15:
            return 'gold'
        elif metrics['current_score'] >= 150 and metrics['games_played'] >= 10:
            return 'silver'
        else:
            return 'bronze'
```

### Behavioral Monitoring

```python
def monitor_gambling_behavior(self, employee_id):
    """Monitor for potential gambling addiction signs."""
    with DatabaseConnection() as conn:
        # Check recent gambling frequency
        recent_games = conn.execute("""
            SELECT COUNT(*) FROM mini_games
            WHERE employee_id = ? 
            AND game_category = 'gambling'
            AND played_date > datetime('now', '-24 hours')
        """, (employee_id,)).fetchone()[0]
        
        # Check token spending patterns
        recent_spending = conn.execute("""
            SELECT SUM(token_amount) FROM token_transactions
            WHERE employee_id = ?
            AND transaction_type = 'spend'
            AND transaction_date > datetime('now', '-24 hours')
        """, (employee_id,)).fetchone()[0] or 0
        
        # Flag concerning behavior
        flags = []
        if recent_games > 10:
            flags.append(('excessive_gambling', 'warning', 
                         f'{recent_games} games in 24h'))
        
        if recent_spending > 100:
            flags.append(('excessive_spending', 'alert',
                         f'{recent_spending} tokens spent in 24h'))
        
        # Log flags
        for flag_type, severity, details in flags:
            self._create_behavior_flag(conn, employee_id, flag_type, severity, details)
```

## Security Considerations

### CSRF Protection Integration

All dual game endpoints require CSRF validation:

```python
@app.route('/api/games/category-a/play/<game_id>', methods=['POST'])
def play_category_a_game(game_id):
    try:
        csrf.protect()
    except CSRFError:
        return jsonify({'success': False, 'message': 'CSRF validation failed'}), 400
    
    # Game logic continues...
```

### Input Validation

```python
def validate_game_request(self, employee_id, game_data):
    """Comprehensive input validation."""
    errors = []
    
    # Validate employee exists and is active
    if not self._validate_employee(employee_id):
        errors.append("Invalid employee")
    
    # Validate game parameters
    if 'game_type' in game_data:
        if game_data['game_type'] not in ['slots', 'roulette', 'dice', 'wheel']:
            errors.append("Invalid game type")
    
    # Validate token amounts
    if 'token_cost' in game_data:
        if not isinstance(game_data['token_cost'], int) or game_data['token_cost'] < 1:
            errors.append("Invalid token cost")
    
    return len(errors) == 0, errors
```

### Transaction Integrity

```python
def execute_game_with_transaction(self, employee_id, game_function, *args):
    """Execute game logic within database transaction."""
    with DatabaseConnection() as conn:
        try:
            conn.execute('BEGIN TRANSACTION')
            
            # Execute game logic
            result = game_function(conn, employee_id, *args)
            
            # Verify transaction integrity
            if not self._verify_transaction_integrity(conn, result):
                conn.rollback()
                return False, "Transaction integrity check failed"
            
            conn.commit()
            return True, result
            
        except Exception as e:
            conn.rollback()
            logging.error(f"Game transaction failed: {e}")
            return False, "Game execution failed"
```

## Performance Optimization

### Connection Pooling

```python
# Database connection pool configuration
DB_POOL_SIZE = 10
DB_POOL_TIMEOUT = 30
DB_POOL_MAX_RETRIES = 3

class DatabaseConnection:
    """Connection pool manager for high-performance database access."""
    
    def __init__(self):
        self.pool = ConnectionPool(
            database_path=Config.INCENTIVE_DB_FILE,
            pool_size=Config.DB_POOL_SIZE,
            timeout=Config.DB_POOL_TIMEOUT,
            max_retries=Config.DB_POOL_MAX_RETRIES
        )
```

### Caching Strategy

```python
# Cache configuration for dual game system
CACHE_TTL_EMPLOYEE_GAMES = 60      # 1 minute for active game data
CACHE_TTL_PRIZE_LIMITS = 300       # 5 minutes for prize limits
CACHE_TTL_TOKEN_ACCOUNTS = 60      # 1 minute for token balances
CACHE_TTL_GLOBAL_POOLS = 120       # 2 minutes for global pools

def get_cached_employee_limits(self, employee_id):
    """Get prize limits with caching."""
    cache_key = f"employee_limits:{employee_id}"
    cached = self.cache.get(cache_key)
    
    if cached is None:
        limits = self._fetch_employee_limits(employee_id)
        self.cache.set(cache_key, limits, ttl=300)
        return limits
    
    return cached
```

### Query Optimization

```python
def get_employee_game_summary_optimized(self, employee_id):
    """Optimized single-query game summary."""
    with DatabaseConnection() as conn:
        summary = conn.execute("""
            SELECT 
                -- Category A stats
                COUNT(CASE WHEN game_category = 'reward' THEN 1 END) as category_a_total,
                COUNT(CASE WHEN game_category = 'reward' AND status = 'unused' THEN 1 END) as category_a_unused,
                COUNT(CASE WHEN game_category = 'reward' AND outcome = 'win' THEN 1 END) as category_a_wins,
                
                -- Category B stats  
                COUNT(CASE WHEN game_category = 'gambling' THEN 1 END) as category_b_total,
                COUNT(CASE WHEN game_category = 'gambling' AND outcome = 'win' THEN 1 END) as category_b_wins,
                COALESCE(SUM(CASE WHEN game_category = 'gambling' THEN token_cost END), 0) as tokens_spent,
                
                -- Token account (from join)
                et.token_balance,
                et.total_tokens_earned,
                et.total_tokens_spent,
                e.tier_level
                
            FROM mini_games mg
            JOIN employees e ON mg.employee_id = e.employee_id
            LEFT JOIN employee_tokens et ON e.employee_id = et.employee_id
            WHERE mg.employee_id = ?
        """, (employee_id,)).fetchone()
        
        return dict(summary) if summary else {}
```

## Monitoring and Analytics

### Game Analytics

```python
def generate_dual_system_analytics(self):
    """Comprehensive analytics for both game categories."""
    with DatabaseConnection() as conn:
        analytics = {
            'category_a': self._analyze_category_a(conn),
            'category_b': self._analyze_category_b(conn),
            'token_economy': self._analyze_token_economy(conn),
            'behavioral_insights': self._analyze_behavior(conn)
        }
        
        return analytics

def _analyze_category_a(self, conn):
    """Category A specific analytics."""
    return conn.execute("""
        SELECT 
            COUNT(*) as total_games,
            COUNT(CASE WHEN outcome = 'win' THEN 1 END) as total_wins,
            AVG(CASE WHEN gh.prize_amount IS NOT NULL THEN gh.prize_amount END) as avg_prize,
            SUM(CASE WHEN gh.prize_amount IS NOT NULL THEN gh.prize_amount END) as total_payout,
            
            -- By tier breakdown
            COUNT(CASE WHEN mg.tier_level = 'bronze' THEN 1 END) as bronze_games,
            COUNT(CASE WHEN mg.tier_level = 'silver' THEN 1 END) as silver_games,
            COUNT(CASE WHEN mg.tier_level = 'gold' THEN 1 END) as gold_games,
            COUNT(CASE WHEN mg.tier_level = 'platinum' THEN 1 END) as platinum_games
            
        FROM mini_games mg
        LEFT JOIN game_history gh ON mg.id = gh.mini_game_id
        WHERE mg.game_category = 'reward'
        AND mg.played_date > date('now', '-30 days')
    """).fetchone()
```

### Performance Monitoring

```python
def monitor_system_performance(self):
    """Monitor key performance metrics."""
    metrics = {
        'database': self._monitor_database_performance(),
        'cache': self._monitor_cache_performance(), 
        'games': self._monitor_game_performance(),
        'tokens': self._monitor_token_performance()
    }
    
    # Alert on performance issues
    self._check_performance_alerts(metrics)
    
    return metrics

def _monitor_database_performance(self):
    """Database performance metrics."""
    with DatabaseConnection() as conn:
        return {
            'active_connections': self.pool.active_connections,
            'query_response_time': self._measure_query_time(conn),
            'transaction_success_rate': self._calculate_success_rate(),
            'deadlock_count': self._count_recent_deadlocks()
        }
```

### Behavioral Analytics

```python
def analyze_gambling_patterns(self):
    """Analyze gambling behavior patterns across all users."""
    with DatabaseConnection() as conn:
        patterns = conn.execute("""
            SELECT 
                e.tier_level,
                COUNT(*) as total_gambling_games,
                AVG(mg.token_cost) as avg_tokens_per_game,
                COUNT(DISTINCT mg.employee_id) as unique_gamblers,
                
                -- Win rates by tier
                AVG(CASE WHEN gh.outcome = 'win' THEN 1.0 ELSE 0.0 END) as win_rate,
                
                -- Spending patterns
                SUM(mg.token_cost) as total_tokens_spent,
                MAX(mg.token_cost) as max_single_bet,
                
                -- Time patterns
                COUNT(CASE WHEN time(mg.played_date) BETWEEN '09:00' AND '17:00' 
                      THEN 1 END) as business_hours_games,
                COUNT(CASE WHEN time(mg.played_date) NOT BETWEEN '09:00' AND '17:00' 
                      THEN 1 END) as after_hours_games
                      
            FROM mini_games mg
            JOIN employees e ON mg.employee_id = e.employee_id
            LEFT JOIN game_history gh ON mg.id = gh.mini_game_id
            WHERE mg.game_category = 'gambling'
            AND mg.played_date > date('now', '-30 days')
            GROUP BY e.tier_level
        """).fetchall()
        
        return [dict(pattern) for pattern in patterns]
```

---

## Integration Points

### API Integration

```python
# Example API endpoint implementation
@app.route('/api/dual-system/status', methods=['GET'])
def dual_system_status():
    """Get comprehensive dual system status."""
    try:
        status = {
            'system_health': dual_game_manager.check_system_health(),
            'global_pools': dual_game_manager.get_global_pool_status(),
            'token_economy': token_economy.get_token_economy_stats(),
            'active_users': dual_game_manager.get_active_user_count()
        }
        return jsonify(status)
    except Exception as e:
        logging.error(f"Error getting dual system status: {e}")
        return jsonify({'error': 'System status unavailable'}), 500
```

### Frontend Integration

```javascript
// Dual system JavaScript controller
class DualGameController {
    constructor() {
        this.csrfToken = this.getCSRFToken();
        this.categoryA = new CategoryAController();
        this.categoryB = new CategoryBController();
        this.tokenSystem = new TokenSystemController();
    }
    
    async playDualGameCategoryA(gameId) {
        const formData = new FormData();
        formData.append('csrf_token', this.csrfToken);
        formData.append('game_id', gameId);
        
        const response = await fetch(`/api/games/category-a/play/${gameId}`, {
            method: 'POST',
            body: formData
        });
        
        return await response.json();
    }
}
```

---

## Related Documentation

- [CSRF Security Implementation](CSRF_SECURITY_TECHNICAL_DOCS.md)
- [API Endpoint Documentation](API_ENDPOINTS_TECHNICAL_DOCS.md)  
- [Database Schema Documentation](DATABASE_SCHEMA_TECHNICAL_DOCS.md)
- [Testing and Validation Procedures](TESTING_VALIDATION_TECHNICAL_DOCS.md)

---

**Last Updated**: August 29, 2025  
**Next Review**: September 29, 2025  
**Maintained By**: Development Team