# services/refined_dual_game_system.py
"""
Refined Dual Game System with Advanced Algorithms
Implements Category A (guaranteed wins) and Category B (token gambling)
with sophisticated odds scaling, boost algorithms, and win cap management.
"""

import sqlite3
import logging
import json
import random
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class GameCategory(Enum):
    """Game category types"""
    CATEGORY_A = "guaranteed"  # Guaranteed win games
    CATEGORY_B = "gambling"     # Token gambling games

class DifficultyLevel(Enum):
    """Task/rule difficulty levels for odds scaling"""
    TRIVIAL = 1      # Simple daily tasks
    EASY = 2         # Basic performance metrics
    MODERATE = 3     # Standard achievements
    HARD = 4         # Challenging goals
    EXTREME = 5      # Exceptional performance

@dataclass
class GameSettings:
    """Centralized game configuration"""
    # Odds scaling by difficulty
    difficulty_multipliers: Dict[int, float] = None
    
    # Random boost algorithm parameters
    boost_enabled: bool = True
    boost_threshold_percentile: float = 30.0  # Bottom 30% get boost
    boost_max_multiplier: float = 2.0
    boost_frequency_hours: int = 24
    
    # Win cap settings
    win_cap_enabled: bool = True
    win_cap_multiplier: float = 1.5  # Max 150% of non-gambling potential
    win_cap_period_days: int = 30
    
    # Exchange system settings
    exchange_enabled: bool = True
    exchange_rate_base: int = 10  # Base points per token
    exchange_daily_limit: int = 100
    exchange_cooldown_hours: int = 6
    exchange_reverse_fee: float = 0.2  # 20% fee for token->points
    
    # Expiration settings
    category_a_expire_end_month: bool = True
    category_b_token_hold_days: int = 60
    category_b_auto_reverse_threshold: int = 500
    
    # Performance optimization for Pi 5
    max_concurrent_users: int = 6
    cache_ttl_seconds: int = 30
    batch_process_size: int = 10
    
    def __post_init__(self):
        if self.difficulty_multipliers is None:
            self.difficulty_multipliers = {
                1: 0.5,   # Trivial: 50% odds
                2: 1.0,   # Easy: 100% (base)
                3: 1.5,   # Moderate: 150%
                4: 2.0,   # Hard: 200%
                5: 3.0    # Extreme: 300%
            }

class OddsCalculator:
    """Advanced odds calculation engine"""
    
    def __init__(self, settings: GameSettings):
        self.settings = settings
        
    def calculate_category_a_odds(self, difficulty: DifficultyLevel, 
                                  employee_performance: Dict) -> float:
        """
        Calculate odds for Category A games based on difficulty.
        These are guaranteed wins but prize value scales with difficulty.
        """
        base_multiplier = self.settings.difficulty_multipliers[difficulty.value]
        
        # Adjust for employee performance
        performance_modifier = self._calculate_performance_modifier(employee_performance)
        
        # Category A is guaranteed win, but affects prize tier
        prize_tier_probability = min(1.0, base_multiplier * performance_modifier)
        
        return prize_tier_probability
    
    def calculate_category_b_odds(self, game_type: str, difficulty: DifficultyLevel,
                                  employee_stats: Dict) -> Dict[str, float]:
        """
        Calculate odds for Category B gambling games.
        Returns win probabilities for different prize tiers.
        """
        base_odds = self._get_base_game_odds(game_type)
        difficulty_mult = self.settings.difficulty_multipliers[difficulty.value]
        
        # Apply boost if eligible
        boost_mult = self._calculate_boost_multiplier(employee_stats)
        
        # Calculate final odds for each prize tier
        odds = {}
        for prize_tier, base_prob in base_odds.items():
            # Scale by difficulty and boost
            adjusted_prob = base_prob * difficulty_mult * boost_mult
            
            # Apply win cap check
            if self.settings.win_cap_enabled:
                adjusted_prob = self._apply_win_cap(adjusted_prob, employee_stats)
            
            odds[prize_tier] = min(0.95, adjusted_prob)  # Cap at 95% max
        
        return odds
    
    def _get_base_game_odds(self, game_type: str) -> Dict[str, float]:
        """Get base odds for each game type"""
        game_odds = {
            'slots': {
                'jackpot': 0.01,
                'major': 0.05,
                'minor': 0.15,
                'basic': 0.30
            },
            'roulette': {
                'jackpot': 0.005,
                'major': 0.03,
                'minor': 0.12,
                'basic': 0.25
            },
            'dice': {
                'jackpot': 0.02,
                'major': 0.08,
                'minor': 0.20,
                'basic': 0.35
            },
            'wheel': {
                'jackpot': 0.008,
                'major': 0.04,
                'minor': 0.10,
                'basic': 0.28
            }
        }
        return game_odds.get(game_type, game_odds['slots'])
    
    def _calculate_performance_modifier(self, performance: Dict) -> float:
        """Calculate modifier based on employee performance"""
        # Factors: completion rate, quality score, consistency
        completion_rate = performance.get('completion_rate', 0.5)
        quality_score = performance.get('quality_score', 0.5)
        consistency = performance.get('consistency', 0.5)
        
        # Weighted average
        modifier = (completion_rate * 0.4 + quality_score * 0.4 + consistency * 0.2)
        return max(0.5, min(1.5, modifier))  # Clamp between 0.5 and 1.5
    
    def _calculate_boost_multiplier(self, employee_stats: Dict) -> float:
        """Calculate random boost for low-point holders"""
        if not self.settings.boost_enabled:
            return 1.0
        
        # Check if eligible for boost (bottom percentile)
        percentile = employee_stats.get('score_percentile', 50)
        if percentile > self.settings.boost_threshold_percentile:
            return 1.0
        
        # Check boost cooldown
        last_boost = employee_stats.get('last_boost_time')
        if last_boost:
            hours_since = (datetime.now() - datetime.fromisoformat(last_boost)).total_seconds() / 3600
            if hours_since < self.settings.boost_frequency_hours:
                return 1.0
        
        # Calculate boost based on how far below threshold
        deficit_ratio = (self.settings.boost_threshold_percentile - percentile) / self.settings.boost_threshold_percentile
        boost = 1.0 + (deficit_ratio * (self.settings.boost_max_multiplier - 1.0))
        
        # Add small random variation
        boost *= random.uniform(0.9, 1.1)
        
        return min(self.settings.boost_max_multiplier, boost)
    
    def _apply_win_cap(self, probability: float, employee_stats: Dict) -> float:
        """Apply win cap to prevent excessive gambling wins"""
        if not self.settings.win_cap_enabled:
            return probability
        
        # Calculate maximum allowed winnings
        period_start = datetime.now() - timedelta(days=self.settings.win_cap_period_days)
        gambling_wins = employee_stats.get('gambling_wins_period', 0)
        non_gambling_max = employee_stats.get('non_gambling_max_potential', 1000)
        
        max_allowed = non_gambling_max * self.settings.win_cap_multiplier
        
        if gambling_wins >= max_allowed:
            # Reached cap, drastically reduce odds
            return probability * 0.1
        elif gambling_wins >= max_allowed * 0.8:
            # Approaching cap, reduce odds
            reduction_factor = (max_allowed - gambling_wins) / (max_allowed * 0.2)
            return probability * reduction_factor
        
        return probability

class TokenExchangeManager:
    """Manages point-to-token and token-to-point exchanges"""
    
    def __init__(self, settings: GameSettings):
        self.settings = settings
    
    def calculate_exchange_rate(self, employee_tier: str, direction: str = 'points_to_tokens') -> float:
        """Calculate dynamic exchange rate based on tier and direction"""
        base_rate = self.settings.exchange_rate_base
        
        # Tier modifiers
        tier_modifiers = {
            'bronze': 1.2,
            'silver': 1.0,
            'gold': 0.8,
            'platinum': 0.6
        }
        
        rate = base_rate * tier_modifiers.get(employee_tier, 1.0)
        
        # Apply reverse exchange fee
        if direction == 'tokens_to_points':
            rate = rate * (1 + self.settings.exchange_reverse_fee)
        
        return rate
    
    def can_exchange(self, employee_data: Dict, amount: int, direction: str) -> Tuple[bool, str]:
        """Check if exchange is allowed"""
        if not self.settings.exchange_enabled:
            return False, "Exchange system is disabled"
        
        # Check daily limit
        daily_exchanged = employee_data.get('daily_exchange_count', 0)
        if daily_exchanged + amount > self.settings.exchange_daily_limit:
            remaining = self.settings.exchange_daily_limit - daily_exchanged
            return False, f"Daily limit exceeded. You can exchange {remaining} more tokens today"
        
        # Check cooldown
        last_exchange = employee_data.get('last_exchange_time')
        if last_exchange:
            hours_since = (datetime.now() - datetime.fromisoformat(last_exchange)).total_seconds() / 3600
            if hours_since < self.settings.exchange_cooldown_hours:
                hours_left = self.settings.exchange_cooldown_hours - hours_since
                return False, f"Cooldown active. Wait {hours_left:.1f} more hours"
        
        # Check balance
        if direction == 'points_to_tokens':
            rate = self.calculate_exchange_rate(employee_data.get('tier', 'bronze'), direction)
            points_needed = amount * rate
            if employee_data.get('points', 0) < points_needed:
                return False, f"Insufficient points. Need {points_needed:.0f} points"
        else:
            if employee_data.get('tokens', 0) < amount:
                return False, f"Insufficient tokens"
        
        return True, "Exchange allowed"
    
    def process_auto_reverse(self, conn: sqlite3.Connection) -> List[Dict]:
        """Process automatic token-to-points reversal for expired tokens"""
        results = []
        
        try:
            # Find tokens exceeding hold limit
            expiry_date = datetime.now() - timedelta(days=self.settings.category_b_token_hold_days)
            
            expired_tokens = conn.execute("""
                SELECT et.employee_id, et.token_balance, e.tier_level, e.name
                FROM employee_tokens et
                JOIN employees e ON et.employee_id = e.employee_id
                WHERE et.last_activity_date < ? AND et.token_balance > ?
            """, (expiry_date.isoformat(), self.settings.category_b_auto_reverse_threshold)).fetchall()
            
            for record in expired_tokens:
                employee_id = record['employee_id']
                tokens = record['token_balance']
                tier = record['tier_level']
                
                # Calculate reverse exchange
                rate = self.calculate_exchange_rate(tier, 'tokens_to_points')
                points_returned = int(tokens / rate)
                
                # Process reversal
                conn.execute("""
                    UPDATE employees SET score = score + ? WHERE employee_id = ?
                """, (points_returned, employee_id))
                
                conn.execute("""
                    UPDATE employee_tokens SET token_balance = 0, 
                    last_reversal_date = CURRENT_TIMESTAMP
                    WHERE employee_id = ?
                """, (employee_id,))
                
                # Log transaction
                conn.execute("""
                    INSERT INTO token_transactions 
                    (employee_id, transaction_type, token_amount, points_amount, admin_notes)
                    VALUES (?, 'auto_reverse', ?, ?, 'Automatic expiration reversal')
                """, (employee_id, -tokens, points_returned))
                
                results.append({
                    'employee_id': employee_id,
                    'name': record['name'],
                    'tokens_reversed': tokens,
                    'points_returned': points_returned
                })
            
            conn.commit()
            
        except Exception as e:
            logging.error(f"Error in auto-reverse process: {e}")
            conn.rollback()
        
        return results

class PrizePoolManager:
    """Manages global and individual prize pools"""
    
    def __init__(self):
        self.prize_tiers = {
            'category_a': {
                'bronze': {
                    'cash': {'limit': 1, 'value': 25},
                    'pto': {'limit': 2, 'value': 2},
                    'points': {'limit': 5, 'value': 100},
                    'swag': {'limit': 10, 'value': 'item'}
                },
                'silver': {
                    'cash': {'limit': 2, 'value': 50},
                    'pto': {'limit': 4, 'value': 4},
                    'points': {'limit': 8, 'value': 200},
                    'swag': {'limit': 15, 'value': 'item'}
                },
                'gold': {
                    'cash': {'limit': 3, 'value': 100},
                    'pto': {'limit': 6, 'value': 6},
                    'points': {'limit': 12, 'value': 300},
                    'swag': {'limit': 20, 'value': 'item'}
                },
                'platinum': {
                    'cash': {'limit': 5, 'value': 200},
                    'pto': {'limit': 8, 'value': 8},
                    'points': {'limit': 20, 'value': 500},
                    'swag': {'limit': 30, 'value': 'item'}
                }
            },
            'category_b': {
                # Category B prizes lean toward PTO/swag rather than money/points
                'jackpot': {'pto': 8, 'swag': 'premium', 'points': 100},
                'major': {'pto': 4, 'swag': 'standard', 'points': 50},
                'minor': {'pto': 2, 'swag': 'basic', 'points': 25},
                'basic': {'points': 10, 'tokens': 5}
            }
        }
    
    def check_availability(self, conn: sqlite3.Connection, employee_id: str, 
                          category: GameCategory, prize_type: str) -> Tuple[bool, str]:
        """Check if prize is available for employee"""
        
        if category == GameCategory.CATEGORY_A:
            # Check individual monthly limits
            result = conn.execute("""
                SELECT monthly_used, monthly_limit 
                FROM employee_prize_limits
                WHERE employee_id = ? AND prize_type = ?
                AND last_reset_date = date('now', 'start of month')
            """, (employee_id, prize_type)).fetchone()
            
            if result:
                if result['monthly_used'] >= result['monthly_limit']:
                    return False, f"Monthly limit reached for {prize_type}"
            
            return True, "Available"
        
        else:  # Category B
            # Check global daily pool
            result = conn.execute("""
                SELECT daily_used, daily_limit
                FROM global_prize_pools
                WHERE prize_type = ? AND last_daily_reset = date('now')
            """, (prize_type,)).fetchone()
            
            if result:
                if result['daily_used'] >= result['daily_limit']:
                    return False, f"Daily pool exhausted for {prize_type}"
            
            return True, "Available"
    
    def award_prize(self, conn: sqlite3.Connection, employee_id: str, 
                   category: GameCategory, prize_info: Dict) -> Dict:
        """Award prize and update pools"""
        
        try:
            if category == GameCategory.CATEGORY_A:
                # Update individual limit
                conn.execute("""
                    UPDATE employee_prize_limits 
                    SET monthly_used = monthly_used + 1
                    WHERE employee_id = ? AND prize_type = ?
                """, (employee_id, prize_info['type']))
            
            else:  # Category B
                # Update global pool
                conn.execute("""
                    UPDATE global_prize_pools 
                    SET daily_used = daily_used + 1
                    WHERE prize_type = ?
                """, (prize_info['type'],))
            
            # Award points if applicable
            if 'points' in prize_info:
                conn.execute("""
                    UPDATE employees SET score = score + ? WHERE employee_id = ?
                """, (prize_info['points'], employee_id))
            
            # Log prize
            conn.execute("""
                INSERT INTO prize_awards 
                (employee_id, category, prize_type, prize_value, awarded_date)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (employee_id, category.value, prize_info['type'], 
                  json.dumps(prize_info)))
            
            return prize_info
            
        except Exception as e:
            logging.error(f"Error awarding prize: {e}")
            raise

class RefinedDualGameManager:
    """Main manager for the refined dual game system"""
    
    def __init__(self, settings: Optional[GameSettings] = None):
        self.settings = settings or GameSettings()
        self.odds_calculator = OddsCalculator(self.settings)
        self.exchange_manager = TokenExchangeManager(self.settings)
        self.prize_manager = PrizePoolManager()
        
        # Performance optimization cache
        self._cache = {}
        self._cache_timestamps = {}
    
    def award_game_for_achievement(self, conn: sqlite3.Connection, employee_id: str,
                                   achievement_type: str, difficulty: DifficultyLevel) -> Dict:
        """Award game based on achievement with appropriate category"""
        
        # Determine category based on achievement and difficulty
        if difficulty.value >= 4:  # Hard or Extreme
            category = GameCategory.CATEGORY_A
            game_type = 'premium_reward'
        elif achievement_type == 'voting':
            # Voting always awards high-value games
            category = GameCategory.CATEGORY_A
            game_type = 'voting_reward'
        else:
            # Lower difficulty gets Category B opportunity
            category = GameCategory.CATEGORY_B
            game_type = 'standard_gamble'
        
        # Create game record
        cursor = conn.execute("""
            INSERT INTO mini_games 
            (employee_id, game_type, game_category, awarded_date, status, 
             difficulty_level, achievement_source)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, 'unused', ?, ?)
        """, (employee_id, game_type, category.value, difficulty.value, achievement_type))
        
        game_id = cursor.lastrowid
        
        # Log award
        conn.execute("""
            INSERT INTO history 
            (employee_id, action, points_change, admin_id, created_at)
            VALUES (?, ?, 0, 'SYSTEM', CURRENT_TIMESTAMP)
        """, (employee_id, f"Awarded {category.value} game for {achievement_type} (difficulty: {difficulty.name})"))
        
        conn.commit()
        
        return {
            'game_id': game_id,
            'category': category.value,
            'game_type': game_type,
            'difficulty': difficulty.name
        }
    
    def play_game(self, conn: sqlite3.Connection, employee_id: str, 
                  game_id: int) -> Dict:
        """Play a game with full algorithm application"""
        
        # Get game details
        game = conn.execute("""
            SELECT * FROM mini_games 
            WHERE id = ? AND employee_id = ? AND status = 'unused'
        """, (game_id, employee_id)).fetchone()
        
        if not game:
            return {'success': False, 'message': 'Invalid or already played game'}
        
        # Get employee stats for algorithms
        employee_stats = self._get_employee_stats(conn, employee_id)
        
        category = GameCategory(game['game_category'])
        difficulty = DifficultyLevel(game['difficulty_level'])
        
        if category == GameCategory.CATEGORY_A:
            result = self._play_category_a(conn, employee_id, game_id, difficulty, employee_stats)
        else:
            result = self._play_category_b(conn, employee_id, game_id, game['game_type'], 
                                          difficulty, employee_stats)
        
        # Update game status
        conn.execute("""
            UPDATE mini_games 
            SET status = 'played', played_date = CURRENT_TIMESTAMP, outcome = ?
            WHERE id = ?
        """, (json.dumps(result), game_id))
        
        conn.commit()
        
        return result
    
    def _play_category_a(self, conn: sqlite3.Connection, employee_id: str, 
                        game_id: int, difficulty: DifficultyLevel, 
                        employee_stats: Dict) -> Dict:
        """Play Category A guaranteed win game"""
        
        # Calculate performance-based prize tier
        performance = {
            'completion_rate': employee_stats.get('task_completion_rate', 0.5),
            'quality_score': employee_stats.get('quality_score', 0.5),
            'consistency': employee_stats.get('consistency_score', 0.5)
        }
        
        prize_tier_prob = self.odds_calculator.calculate_category_a_odds(difficulty, performance)
        
        # Select prize based on probability and availability
        tier = employee_stats.get('tier', 'bronze')
        available_prizes = self.prize_manager.prize_tiers['category_a'][tier]
        
        # Weight selection by probability
        if random.random() < prize_tier_prob * 0.3:
            prize_type = 'cash' if self._check_limit(conn, employee_id, 'cash') else 'points'
        elif random.random() < prize_tier_prob * 0.6:
            prize_type = 'pto' if self._check_limit(conn, employee_id, 'pto') else 'points'
        else:
            prize_type = 'swag' if random.random() < 0.5 else 'points'
        
        prize_info = {
            'type': prize_type,
            'value': available_prizes[prize_type]['value'],
            'category': 'guaranteed_win'
        }
        
        # Award prize
        self.prize_manager.award_prize(conn, employee_id, GameCategory.CATEGORY_A, prize_info)
        
        return {
            'success': True,
            'outcome': 'win',
            'prize': prize_info,
            'message': f"Congratulations! You won {prize_info['value']} {prize_type}!"
        }
    
    def _play_category_b(self, conn: sqlite3.Connection, employee_id: str,
                        game_id: int, game_type: str, difficulty: DifficultyLevel,
                        employee_stats: Dict) -> Dict:
        """Play Category B gambling game"""
        
        # Check token balance
        token_cost = self._calculate_token_cost(game_type, difficulty)
        if employee_stats.get('tokens', 0) < token_cost:
            return {'success': False, 'message': 'Insufficient tokens'}
        
        # Deduct tokens
        conn.execute("""
            UPDATE employee_tokens SET token_balance = token_balance - ?
            WHERE employee_id = ?
        """, (token_cost, employee_id))
        
        # Calculate odds with all modifiers
        odds = self.odds_calculator.calculate_category_b_odds(game_type, difficulty, employee_stats)
        
        # Determine outcome
        roll = random.random()
        cumulative = 0
        outcome = 'loss'
        prize_tier = None
        
        for tier in ['jackpot', 'major', 'minor', 'basic']:
            cumulative += odds[tier]
            if roll < cumulative:
                outcome = 'win'
                prize_tier = tier
                break
        
        if outcome == 'win':
            # Check global pool availability
            available, msg = self.prize_manager.check_availability(
                conn, employee_id, GameCategory.CATEGORY_B, prize_tier
            )
            
            if not available:
                # Downgrade to basic prize
                prize_tier = 'basic'
            
            prize_info = self.prize_manager.prize_tiers['category_b'][prize_tier]
            
            # Award prize
            self.prize_manager.award_prize(conn, employee_id, GameCategory.CATEGORY_B, 
                                         {'type': prize_tier, **prize_info})
            
            # Update boost timestamp if boost was applied
            if employee_stats.get('boost_applied'):
                conn.execute("""
                    UPDATE employee_stats SET last_boost_time = CURRENT_TIMESTAMP
                    WHERE employee_id = ?
                """, (employee_id,))
            
            return {
                'success': True,
                'outcome': 'win',
                'prize': prize_info,
                'message': f"Winner! You got {prize_tier} prize!"
            }
        else:
            return {
                'success': True,
                'outcome': 'loss',
                'message': 'Better luck next time!'
            }
    
    def _calculate_token_cost(self, game_type: str, difficulty: DifficultyLevel) -> int:
        """Calculate token cost for Category B games"""
        base_costs = {
            'slots': 5,
            'roulette': 10,
            'dice': 7,
            'wheel': 15
        }
        
        base = base_costs.get(game_type, 5)
        
        # Scale by difficulty (easier = cheaper)
        difficulty_scale = {
            1: 0.5,
            2: 0.75,
            3: 1.0,
            4: 1.5,
            5: 2.0
        }
        
        return int(base * difficulty_scale[difficulty.value])
    
    def _get_employee_stats(self, conn: sqlite3.Connection, employee_id: str) -> Dict:
        """Get comprehensive employee statistics with caching"""
        
        # Check cache
        cache_key = f"stats_{employee_id}"
        if cache_key in self._cache:
            timestamp = self._cache_timestamps.get(cache_key, 0)
            if time.time() - timestamp < self.settings.cache_ttl_seconds:
                return self._cache[cache_key]
        
        # Fetch fresh stats
        stats = {}
        
        # Basic info
        employee = conn.execute("""
            SELECT e.*, et.token_balance,
                   (SELECT COUNT(*) FROM employees WHERE score > e.score) as rank,
                   (SELECT COUNT(*) FROM employees) as total_employees
            FROM employees e
            LEFT JOIN employee_tokens et ON e.employee_id = et.employee_id
            WHERE e.employee_id = ?
        """, (employee_id,)).fetchone()
        
        if employee:
            stats.update(dict(employee))
            stats['score_percentile'] = (1 - (stats['rank'] / stats['total_employees'])) * 100
        
        # Performance metrics
        perf = conn.execute("""
            SELECT AVG(completion_rate) as task_completion_rate,
                   AVG(quality_score) as quality_score,
                   AVG(consistency) as consistency_score
            FROM employee_performance
            WHERE employee_id = ? AND date >= date('now', '-30 days')
        """, (employee_id,)).fetchone()
        
        if perf:
            stats.update(dict(perf))
        
        # Gambling history
        gambling = conn.execute("""
            SELECT COUNT(*) as total_gambles,
                   SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) as wins,
                   SUM(CASE WHEN outcome = 'win' THEN prize_value ELSE 0 END) as gambling_wins_period
            FROM mini_games
            WHERE employee_id = ? AND game_category = 'gambling' 
            AND played_date >= date('now', '-30 days')
        """, (employee_id,)).fetchone()
        
        if gambling:
            stats.update(dict(gambling))
        
        # Non-gambling potential
        potential = conn.execute("""
            SELECT MAX(score_change) as max_monthly_points
            FROM (
                SELECT SUM(points_change) as score_change
                FROM history
                WHERE employee_id = ? AND admin_id != 'GAMBLING'
                GROUP BY strftime('%Y-%m', created_at)
            )
        """, (employee_id,)).fetchone()
        
        if potential:
            stats['non_gambling_max_potential'] = potential['max_monthly_points'] or 1000
        
        # Check for boost eligibility
        last_boost = conn.execute("""
            SELECT last_boost_time FROM employee_stats WHERE employee_id = ?
        """, (employee_id,)).fetchone()
        
        if last_boost:
            stats['last_boost_time'] = last_boost['last_boost_time']
        
        # Cache stats
        self._cache[cache_key] = stats
        self._cache_timestamps[cache_key] = time.time()
        
        return stats
    
    def _check_limit(self, conn: sqlite3.Connection, employee_id: str, 
                    prize_type: str) -> bool:
        """Quick check if prize limit is reached"""
        result = conn.execute("""
            SELECT monthly_used < monthly_limit as available
            FROM employee_prize_limits
            WHERE employee_id = ? AND prize_type = ?
            AND last_reset_date = date('now', 'start of month')
        """, (employee_id, prize_type)).fetchone()
        
        return result['available'] if result else True
    
    def process_monthly_reset(self, conn: sqlite3.Connection) -> Dict:
        """Process monthly resets for Category A games and limits"""
        
        results = {'expired_games': 0, 'reset_limits': 0}
        
        try:
            # Expire unused Category A games from previous month
            if self.settings.category_a_expire_end_month:
                cursor = conn.execute("""
                    UPDATE mini_games 
                    SET status = 'expired'
                    WHERE game_category = 'guaranteed' 
                    AND status = 'unused'
                    AND awarded_date < date('now', 'start of month')
                """)
                results['expired_games'] = cursor.rowcount
            
            # Reset individual prize limits
            conn.execute("""
                UPDATE employee_prize_limits
                SET monthly_used = 0, last_reset_date = date('now', 'start of month')
                WHERE last_reset_date < date('now', 'start of month')
            """)
            
            # Reset global monthly pools
            conn.execute("""
                UPDATE global_prize_pools
                SET monthly_used = 0, last_monthly_reset = date('now', 'start of month')
                WHERE last_monthly_reset < date('now', 'start of month')
            """)
            
            conn.commit()
            
        except Exception as e:
            logging.error(f"Error in monthly reset: {e}")
            conn.rollback()
        
        return results
    
    def get_system_metrics(self, conn: sqlite3.Connection) -> Dict:
        """Get comprehensive system metrics for monitoring"""
        
        metrics = {}
        
        # Game distribution
        game_dist = conn.execute("""
            SELECT game_category, status, COUNT(*) as count
            FROM mini_games
            WHERE awarded_date >= date('now', '-30 days')
            GROUP BY game_category, status
        """).fetchall()
        
        metrics['game_distribution'] = [dict(row) for row in game_dist]
        
        # Token economy
        token_stats = conn.execute("""
            SELECT 
                SUM(token_balance) as total_circulation,
                AVG(token_balance) as avg_balance,
                COUNT(CASE WHEN token_balance > 0 THEN 1 END) as active_holders
            FROM employee_tokens
        """).fetchone()
        
        metrics['token_economy'] = dict(token_stats) if token_stats else {}
        
        # Prize pool status
        pool_status = conn.execute("""
            SELECT prize_type, 
                   daily_limit - daily_used as daily_remaining,
                   weekly_limit - weekly_used as weekly_remaining
            FROM global_prize_pools
            WHERE last_daily_reset = date('now')
        """).fetchall()
        
        metrics['prize_pools'] = [dict(row) for row in pool_status]
        
        # Win rates by difficulty
        win_rates = conn.execute("""
            SELECT difficulty_level, 
                   COUNT(*) as total_games,
                   SUM(CASE WHEN outcome LIKE '%win%' THEN 1 ELSE 0 END) as wins,
                   ROUND(AVG(CASE WHEN outcome LIKE '%win%' THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate
            FROM mini_games
            WHERE played_date >= date('now', '-7 days')
            GROUP BY difficulty_level
        """).fetchall()
        
        metrics['win_rates'] = [dict(row) for row in win_rates]
        
        # Boost effectiveness
        boost_stats = conn.execute("""
            SELECT COUNT(*) as boosts_applied,
                   AVG(CASE WHEN outcome LIKE '%win%' THEN 1.0 ELSE 0.0 END) as boost_win_rate
            FROM mini_games mg
            JOIN employee_stats es ON mg.employee_id = es.employee_id
            WHERE mg.played_date >= date('now', '-7 days')
            AND mg.played_date >= es.last_boost_time
            AND datetime(mg.played_date) <= datetime(es.last_boost_time, '+1 hour')
        """).fetchone()
        
        metrics['boost_effectiveness'] = dict(boost_stats) if boost_stats else {}
        
        return metrics

# Global instance with default settings
refined_game_manager = RefinedDualGameManager()

# Import statement
import time