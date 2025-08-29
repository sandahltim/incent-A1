# services/dual_game_manager.py
# Dual Game Manager for Category A (Guaranteed Wins) and Category B (Gambling) Systems

import sqlite3
import logging
import json
import random
from datetime import datetime, timedelta
from incentive_service import DatabaseConnection
from services.token_economy import token_economy

class DualGameManager:
    """Manages both Category A (guaranteed win) and Category B (gambling) game systems."""
    
    def __init__(self):
        # Category A: Individual prize limits by tier
        self.individual_prize_limits = {
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
            'gold': {
                'jackpot_cash': 3,      # 3 cash jackpots per month
                'pto_hours': 6,         # 6 PTO hour rewards per month
                'major_points': 12      # 12 major point prizes per month
            },
            'platinum': {
                'jackpot_cash': 5,      # 5 cash jackpots per month
                'pto_hours': 8,         # 8 PTO hour rewards per month
                'major_points': 20      # 20 major point prizes per month
            }
        }

    def award_category_a_game(self, employee_id, source="admin_award", source_description="", admin_id="SYSTEM"):
        """Award a Category A guaranteed win game to employee."""
        try:
            with DatabaseConnection() as conn:
                # Get employee tier
                employee = conn.execute("""
                    SELECT tier_level, name FROM employees WHERE employee_id = ?
                """, (employee_id,)).fetchone()
                
                if not employee:
                    return False, "Employee not found"
                
                tier = employee['tier_level'] or 'bronze'
                
                # Create guaranteed win game
                conn.execute("""
                    INSERT INTO mini_games 
                    (employee_id, game_type, awarded_date, status, game_category, guaranteed_win, tier_level)
                    VALUES (?, 'reward_selection', CURRENT_TIMESTAMP, 'unused', 'reward', 1, ?)
                """, (employee_id, tier))
                
                game_id = conn.lastrowid
                
                # Log the award
                conn.execute("""
                    INSERT INTO history 
                    (employee_id, action, points_change, admin_id, created_at)
                    VALUES (?, ?, 0, ?, CURRENT_TIMESTAMP)
                """, (employee_id, f"Awarded guaranteed reward game - {source}: {source_description}", admin_id))
                
                conn.commit()
                
                logging.info(f"Awarded Category A game {game_id} to {employee_id} from {source}")
                return True, f"Guaranteed reward game awarded to {employee['name']}"
                
        except Exception as e:
            logging.error(f"Error awarding Category A game to {employee_id}: {e}")
            return False, "Failed to award guaranteed reward game"

    def check_individual_prize_limit(self, employee_id, prize_type):
        """Check if employee has reached their individual monthly limit for a prize type."""
        try:
            with DatabaseConnection() as conn:
                # Get employee tier
                tier = conn.execute("""
                    SELECT tier_level FROM employees WHERE employee_id = ?
                """, (employee_id,)).fetchone()
                
                if not tier:
                    return False, 0, 0
                
                tier_level = tier['tier_level'] or 'bronze'
                
                # Get current month usage
                current_usage = conn.execute("""
                    SELECT COALESCE(monthly_used, 0) FROM employee_prize_limits
                    WHERE employee_id = ? AND prize_type = ? AND tier_level = ?
                """, (employee_id, prize_type, tier_level)).fetchone()
                
                monthly_used = current_usage[0] if current_usage else 0
                monthly_limit = self.individual_prize_limits.get(tier_level, {}).get(prize_type, 0)
                
                can_win = monthly_used < monthly_limit
                return can_win, monthly_used, monthly_limit
                
        except Exception as e:
            logging.error(f"Error checking individual prize limit: {e}")
            return False, 0, 0

    def play_category_a_game(self, employee_id, game_id):
        """Play a Category A guaranteed win game with individual prize limits."""
        try:
            with DatabaseConnection() as conn:
                # Verify game belongs to employee and is Category A
                game = conn.execute("""
                    SELECT * FROM mini_games 
                    WHERE id = ? AND employee_id = ? AND game_category = 'reward' AND status = 'unused'
                """, (game_id, employee_id)).fetchone()
                
                if not game:
                    return False, "Invalid or already played reward game", None
                
                # Get employee tier
                tier = game['tier_level'] or 'bronze'
                
                # Determine available prizes based on individual limits
                available_prizes = []
                
                # Check each prize type
                for prize_type in ['jackpot_cash', 'pto_hours', 'major_points']:
                    can_win, used, limit = self.check_individual_prize_limit(employee_id, prize_type)
                    if can_win:
                        available_prizes.append({
                            'type': prize_type,
                            'remaining': limit - used
                        })
                
                # Always include basic point prizes (no limits)
                available_prizes.append({'type': 'basic_points', 'remaining': 999})
                
                # Select prize (weighted towards better prizes for higher tiers)
                selected_prize = self._select_category_a_prize(tier, available_prizes)
                
                # Award the prize
                prize_details = self._award_category_a_prize(conn, employee_id, selected_prize, tier)
                
                # Update game record
                conn.execute("""
                    UPDATE mini_games 
                    SET played_date = CURRENT_TIMESTAMP, 
                        status = 'played',
                        outcome = 'win',
                        individual_odds_used = ?
                    WHERE id = ?
                """, (json.dumps({'selected_prize': selected_prize, 'available': len(available_prizes)}), game_id))
                
                # Create game history
                conn.execute("""
                    INSERT INTO game_history 
                    (mini_game_id, game_type, play_date, outcome, prize_type, prize_description, 
                     prize_amount, game_category, guaranteed_win)
                    VALUES (?, ?, CURRENT_TIMESTAMP, 'win', ?, ?, ?, 'reward', 1)
                """, (game_id, game['game_type'], prize_details['type'], 
                      prize_details['description'], prize_details['amount']))
                
                # Update individual prize usage
                if selected_prize['type'] != 'basic_points':
                    conn.execute("""
                        INSERT OR REPLACE INTO employee_prize_limits
                        (employee_id, prize_type, tier_level, monthly_limit, monthly_used, last_reset_date)
                        VALUES (?, ?, ?, ?, 
                                COALESCE((SELECT monthly_used FROM employee_prize_limits 
                                         WHERE employee_id = ? AND prize_type = ? AND tier_level = ?), 0) + 1,
                                date('now', 'start of month'))
                    """, (employee_id, selected_prize['type'], tier, 
                          self.individual_prize_limits[tier][selected_prize['type']],
                          employee_id, selected_prize['type'], tier))
                
                conn.commit()
                
                logging.info(f"Category A game {game_id} played by {employee_id}: {prize_details['description']}")
                return True, f"Congratulations! You won: {prize_details['description']}", prize_details
                
        except Exception as e:
            logging.error(f"Error playing Category A game {game_id}: {e}")
            return False, "Game play failed", None

    def _select_category_a_prize(self, tier, available_prizes):
        """Select prize for Category A based on tier and available prizes."""
        # Weight prizes based on tier (higher tiers get better prizes more often)
        weights = {
            'bronze': {'jackpot_cash': 10, 'pto_hours': 15, 'major_points': 25, 'basic_points': 50},
            'silver': {'jackpot_cash': 15, 'pto_hours': 20, 'major_points': 30, 'basic_points': 35},
            'gold': {'jackpot_cash': 20, 'pto_hours': 25, 'major_points': 35, 'basic_points': 20},
            'platinum': {'jackpot_cash': 30, 'pto_hours': 30, 'major_points': 25, 'basic_points': 15}
        }
        
        tier_weights = weights.get(tier, weights['bronze'])
        
        # Create weighted list based on available prizes
        weighted_choices = []
        for prize in available_prizes:
            prize_type = prize['type']
            if prize['remaining'] > 0:
                weight = tier_weights.get(prize_type, 1)
                weighted_choices.extend([prize] * weight)
        
        # Select random prize
        return random.choice(weighted_choices) if weighted_choices else available_prizes[0]

    def _award_category_a_prize(self, conn, employee_id, selected_prize, tier):
        """Award the selected prize to employee."""
        prize_type = selected_prize['type']
        
        if prize_type == 'jackpot_cash':
            # Cash prizes by tier
            amounts = {'bronze': 25, 'silver': 50, 'gold': 100, 'platinum': 200}
            amount = amounts.get(tier, 25)
            description = f"${amount} Cash Prize"
            
        elif prize_type == 'pto_hours':
            # PTO hours by tier
            amounts = {'bronze': 2, 'silver': 4, 'gold': 6, 'platinum': 8}
            amount = amounts.get(tier, 2)
            description = f"{amount} Hours PTO"
            
        elif prize_type == 'major_points':
            # Major point prizes by tier
            amounts = {'bronze': 100, 'silver': 200, 'gold': 300, 'platinum': 500}
            amount = amounts.get(tier, 100)
            description = f"{amount} Bonus Points"
            
            # Award points immediately
            conn.execute("""
                UPDATE employees SET score = score + ? WHERE employee_id = ?
            """, (amount, employee_id))
            
        else:  # basic_points
            # Basic point prizes
            amounts = {'bronze': 25, 'silver': 35, 'gold': 50, 'platinum': 75}
            amount = amounts.get(tier, 25)
            description = f"{amount} Points"
            
            # Award points immediately
            conn.execute("""
                UPDATE employees SET score = score + ? WHERE employee_id = ?
            """, (amount, employee_id))
        
        return {
            'type': prize_type,
            'amount': amount,
            'description': description
        }

    def check_global_prize_availability(self, prize_type):
        """Check if global prize is still available today."""
        try:
            with DatabaseConnection() as conn:
                # Check current usage
                pool = conn.execute("""
                    SELECT * FROM global_prize_pools WHERE prize_type = ?
                """, (prize_type,)).fetchone()
                
                if not pool:
                    return False, 0, 0
                
                # Check if daily reset is needed
                if pool['last_daily_reset'] != datetime.now().date().isoformat():
                    conn.execute("""
                        UPDATE global_prize_pools 
                        SET daily_used = 0, last_daily_reset = date('now')
                        WHERE prize_type = ?
                    """, (prize_type,))
                    conn.commit()
                    daily_used = 0
                else:
                    daily_used = pool['daily_used']
                
                available = daily_used < pool['daily_limit']
                return available, daily_used, pool['daily_limit']
                
        except Exception as e:
            logging.error(f"Error checking global prize availability: {e}")
            return False, 0, 0

    def play_category_b_game(self, employee_id, game_type, token_cost):
        """Play a Category B gambling game with global odds and token cost."""
        try:
            with DatabaseConnection() as conn:
                # Verify employee has enough tokens
                account = token_economy.get_employee_token_account(employee_id)
                if not account or account['token_balance'] < token_cost:
                    return False, "Insufficient tokens", None
                
                # Spend tokens
                success, message = token_economy.spend_tokens(employee_id, token_cost, description=f"Category B {game_type}")
                if not success:
                    return False, message, None
                
                # Create gambling game record
                conn.execute("""
                    INSERT INTO mini_games 
                    (employee_id, game_type, awarded_date, played_date, status, 
                     game_category, guaranteed_win, token_cost, tier_level)
                    VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'played', 
                            'gambling', 0, ?, ?)
                """, (employee_id, game_type, token_cost, account.get('tier_level', 'bronze')))
                
                game_id = conn.lastrowid
                
                # Determine win/loss and prize using global odds
                win_result = self._determine_category_b_outcome(conn, game_type, account.get('tier_level', 'bronze'))
                
                # Update game record with outcome
                conn.execute("""
                    UPDATE mini_games 
                    SET outcome = ?,
                        global_pool_source = ?
                    WHERE id = ?
                """, (win_result['outcome'], win_result.get('prize_type'), game_id))
                
                # Create game history
                conn.execute("""
                    INSERT INTO game_history 
                    (mini_game_id, game_type, play_date, outcome, prize_type, prize_description, 
                     prize_amount, token_cost, game_category, guaranteed_win, global_pool_exhausted)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?, ?, 'gambling', 0, ?)
                """, (game_id, game_type, win_result['outcome'], win_result.get('prize_type'),
                      win_result.get('description', 'No prize'), win_result.get('amount', 0),
                      token_cost, win_result.get('pool_exhausted', 0)))
                
                # Award prize if won
                if win_result['outcome'] == 'win':
                    self._award_category_b_prize(conn, employee_id, win_result)
                
                conn.commit()
                
                result_message = win_result.get('description', 'Better luck next time!')
                logging.info(f"Category B {game_type} played by {employee_id}: {result_message}")
                return True, result_message, win_result
                
        except Exception as e:
            logging.error(f"Error playing Category B game: {e}")
            return False, "Game play failed", None

    def _determine_category_b_outcome(self, conn, game_type, tier):
        """Determine outcome for Category B game using global odds."""
        # Base win rates by game type and tier
        base_win_rates = {
            'slots': {'bronze': 0.35, 'silver': 0.38, 'gold': 0.42, 'platinum': 0.45},
            'roulette': {'bronze': 0.28, 'silver': 0.31, 'gold': 0.35, 'platinum': 0.38},
            'dice': {'bronze': 0.32, 'silver': 0.35, 'gold': 0.39, 'platinum': 0.42},
            'wheel': {'bronze': 0.25, 'silver': 0.28, 'gold': 0.32, 'platinum': 0.35}
        }
        
        win_rate = base_win_rates.get(game_type, base_win_rates['slots']).get(tier, 0.35)
        
        if random.random() > win_rate:
            return {'outcome': 'loss', 'description': 'Better luck next time!'}
        
        # Won! Now determine prize based on global availability
        available_prizes = [
            ('major_points_500', 0.4),     # 40% chance
            ('cash_prize_50', 0.25),       # 25% chance
            ('pto_4_hours', 0.15),         # 15% chance
            ('cash_prize_100', 0.1),       # 10% chance
            ('jackpot_1000_pts', 0.05),    # 5% chance
            ('vacation_day', 0.05)         # 5% chance
        ]
        
        # Select prize type based on probability
        rand = random.random()
        cumulative = 0
        selected_prize_type = 'major_points_500'  # fallback
        
        for prize_type, probability in available_prizes:
            cumulative += probability
            if rand <= cumulative:
                selected_prize_type = prize_type
                break
        
        # Check global availability
        available, used, limit = self.check_global_prize_availability(selected_prize_type)
        
        if not available:
            # Fallback to basic points if global prize exhausted
            return {
                'outcome': 'win',
                'prize_type': 'basic_points',
                'amount': 50,
                'description': '50 Points (Global prize pool exhausted)',
                'pool_exhausted': 1
            }
        
        # Award global prize and update usage
        conn.execute("""
            UPDATE global_prize_pools 
            SET daily_used = daily_used + 1
            WHERE prize_type = ?
        """, (selected_prize_type,))
        
        # Return prize details
        return self._get_category_b_prize_details(selected_prize_type)

    def _get_category_b_prize_details(self, prize_type):
        """Get prize details for Category B prizes."""
        prizes = {
            'major_points_500': {'amount': 500, 'description': '500 Bonus Points'},
            'cash_prize_50': {'amount': 50, 'description': '$50 Cash Prize'},
            'pto_4_hours': {'amount': 4, 'description': '4 Hours PTO'},
            'cash_prize_100': {'amount': 100, 'description': '$100 Cash Prize'},
            'jackpot_1000_pts': {'amount': 1000, 'description': '1000 Point Jackpot!'},
            'vacation_day': {'amount': 8, 'description': 'Full Vacation Day'}
        }
        
        details = prizes.get(prize_type, {'amount': 50, 'description': '50 Points'})
        return {
            'outcome': 'win',
            'prize_type': prize_type,
            'amount': details['amount'],
            'description': details['description'],
            'pool_exhausted': 0
        }

    def _award_category_b_prize(self, conn, employee_id, win_result):
        """Award Category B prize to employee."""
        prize_type = win_result.get('prize_type')
        amount = win_result.get('amount', 0)
        
        if 'points' in prize_type.lower():
            # Award points
            conn.execute("""
                UPDATE employees SET score = score + ? WHERE employee_id = ?
            """, (amount, employee_id))
        
        # Note: Cash prizes and PTO would be handled by admin/HR systems
        # For now, we log them for admin processing

    def get_employee_game_summary(self, employee_id):
        """Get comprehensive game summary for employee."""
        try:
            with DatabaseConnection() as conn:
                # Category A stats
                category_a = conn.execute("""
                    SELECT 
                        COUNT(*) as total_games,
                        COUNT(CASE WHEN status = 'unused' THEN 1 END) as unused_games,
                        COUNT(CASE WHEN outcome = 'win' THEN 1 END) as wins
                    FROM mini_games 
                    WHERE employee_id = ? AND game_category = 'reward'
                """, (employee_id,)).fetchone()
                
                # Category B stats
                category_b = conn.execute("""
                    SELECT 
                        COUNT(*) as total_games,
                        COUNT(CASE WHEN outcome = 'win' THEN 1 END) as wins,
                        COALESCE(SUM(token_cost), 0) as total_tokens_spent
                    FROM mini_games 
                    WHERE employee_id = ? AND game_category = 'gambling'
                """, (employee_id,)).fetchone()
                
                # Token account
                token_account = token_economy.get_employee_token_account(employee_id)
                
                # Recent prize limits
                prize_limits = conn.execute("""
                    SELECT prize_type, monthly_used, monthly_limit
                    FROM employee_prize_limits
                    WHERE employee_id = ?
                """, (employee_id,)).fetchall()
                
                return {
                    'category_a': dict(category_a) if category_a else {},
                    'category_b': dict(category_b) if category_b else {},
                    'token_account': token_account,
                    'prize_limits': [dict(limit) for limit in prize_limits]
                }
                
        except Exception as e:
            logging.error(f"Error getting game summary for {employee_id}: {e}")
            return {}

# Global instance
dual_game_manager = DualGameManager()