# services/token_economy.py
# Token Economy Service for Dual Game System

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from incentive_service import DatabaseConnection

class TokenEconomyService:
    """Manages the token economy system for Category B gambling games."""
    
    def __init__(self):
        self.tier_exchange_rates = {
            'bronze': 10,    # 10 points per token
            'silver': 8,     # 8 points per token  
            'gold': 6,       # 6 points per token
            'platinum': 5    # 5 points per token
        }
        
        self.tier_daily_limits = {
            'bronze': 50,    # 50 tokens per day
            'silver': 100,   # 100 tokens per day
            'gold': 200,     # 200 tokens per day
            'platinum': 500  # 500 tokens per day
        }
        
        self.tier_cooldowns = {
            'bronze': 24,    # 24 hours
            'silver': 18,    # 18 hours
            'gold': 12,      # 12 hours
            'platinum': 6    # 6 hours
        }

    def get_employee_token_account(self, employee_id):
        """Get employee's token account information."""
        try:
            with DatabaseConnection() as conn:
                account = conn.execute("""
                    SELECT et.*, e.tier_level, e.score as current_points
                    FROM employee_tokens et
                    JOIN employees e ON et.employee_id = e.employee_id
                    WHERE et.employee_id = ?
                """, (employee_id,)).fetchone()
                
                if not account:
                    # Create account if doesn't exist
                    conn.execute("""
                        INSERT INTO employee_tokens (employee_id)
                        VALUES (?)
                    """, (employee_id,))
                    conn.commit()
                    return self.get_employee_token_account(employee_id)
                
                return dict(account)
        except Exception as e:
            logging.error(f"Error getting token account for {employee_id}: {e}")
            return None

    def can_exchange_tokens(self, employee_id):
        """Check if employee can exchange points for tokens."""
        try:
            account = self.get_employee_token_account(employee_id)
            if not account:
                return False, "Account not found"
            
            tier = account.get('tier_level', 'bronze')
            
            # Check daily limit
            daily_limit = self.tier_daily_limits.get(tier, 50)
            if account['daily_exchange_count'] >= daily_limit:
                return False, f"Daily token limit reached ({daily_limit} tokens)"
            
            # Check cooldown
            if account['last_exchange_date']:
                last_exchange = datetime.fromisoformat(account['last_exchange_date'])
                cooldown_hours = self.tier_cooldowns.get(tier, 24)
                if datetime.now() - last_exchange < timedelta(hours=cooldown_hours):
                    remaining = timedelta(hours=cooldown_hours) - (datetime.now() - last_exchange)
                    hours_left = int(remaining.total_seconds() // 3600)
                    return False, f"Cooldown active: {hours_left} hours remaining"
            
            return True, "Exchange available"
            
        except Exception as e:
            logging.error(f"Error checking exchange eligibility for {employee_id}: {e}")
            return False, "System error"

    def calculate_exchange_cost(self, employee_id, token_amount):
        """Calculate points cost for token exchange."""
        try:
            account = self.get_employee_token_account(employee_id)
            if not account:
                return None, "Account not found"
            
            tier = account.get('tier_level', 'bronze')
            exchange_rate = self.tier_exchange_rates.get(tier, 10)
            
            total_cost = token_amount * exchange_rate
            
            return {
                'token_amount': token_amount,
                'points_cost': total_cost,
                'exchange_rate': exchange_rate,
                'tier': tier,
                'current_points': account['current_points'],
                'can_afford': account['current_points'] >= total_cost
            }, None
            
        except Exception as e:
            logging.error(f"Error calculating exchange cost: {e}")
            return None, "Calculation error"

    def exchange_points_for_tokens(self, employee_id, token_amount, admin_override=False):
        """Exchange employee points for tokens."""
        try:
            with DatabaseConnection() as conn:
                # Check eligibility
                if not admin_override:
                    can_exchange, reason = self.can_exchange_tokens(employee_id)
                    if not can_exchange:
                        return False, reason
                
                # Calculate cost
                cost_info, error = self.calculate_exchange_cost(employee_id, token_amount)
                if error:
                    return False, error
                
                if not cost_info['can_afford'] and not admin_override:
                    return False, f"Insufficient points (need {cost_info['points_cost']}, have {cost_info['current_points']})"
                
                # Perform exchange
                points_cost = cost_info['points_cost']
                exchange_rate = cost_info['exchange_rate']
                
                # Deduct points
                conn.execute("""
                    UPDATE employees 
                    SET score = score - ?
                    WHERE employee_id = ?
                """, (points_cost, employee_id))
                
                # Add tokens
                conn.execute("""
                    UPDATE employee_tokens 
                    SET token_balance = token_balance + ?,
                        total_tokens_earned = total_tokens_earned + ?,
                        last_exchange_date = CURRENT_TIMESTAMP,
                        daily_exchange_count = daily_exchange_count + ?
                    WHERE employee_id = ?
                """, (token_amount, token_amount, token_amount, employee_id))
                
                # Log transaction
                conn.execute("""
                    INSERT INTO token_transactions 
                    (employee_id, transaction_type, points_amount, token_amount, exchange_rate, admin_notes)
                    VALUES (?, 'purchase', ?, ?, ?, ?)
                """, (employee_id, points_cost, token_amount, exchange_rate, 
                      'Admin override' if admin_override else 'Normal exchange'))
                
                conn.commit()
                
                return True, f"Exchanged {points_cost} points for {token_amount} tokens"
                
        except Exception as e:
            logging.error(f"Error exchanging tokens for {employee_id}: {e}")
            return False, "Exchange failed"

    def spend_tokens(self, employee_id, token_amount, game_id=None, description="Game play"):
        """Spend tokens for games or other activities."""
        try:
            with DatabaseConnection() as conn:
                account = self.get_employee_token_account(employee_id)
                if not account:
                    return False, "Account not found"
                
                if account['token_balance'] < token_amount:
                    return False, f"Insufficient tokens (need {token_amount}, have {account['token_balance']})"
                
                # Deduct tokens
                conn.execute("""
                    UPDATE employee_tokens 
                    SET token_balance = token_balance - ?,
                        total_tokens_spent = total_tokens_spent + ?
                    WHERE employee_id = ?
                """, (token_amount, token_amount, employee_id))
                
                # Log transaction
                conn.execute("""
                    INSERT INTO token_transactions 
                    (employee_id, transaction_type, token_amount, game_id, admin_notes)
                    VALUES (?, 'spend', ?, ?, ?)
                """, (employee_id, -token_amount, game_id, description))
                
                conn.commit()
                return True, f"Spent {token_amount} tokens"
                
        except Exception as e:
            logging.error(f"Error spending tokens for {employee_id}: {e}")
            return False, "Spending failed"

    def award_tokens(self, employee_id, token_amount, source="Game win", admin_notes=""):
        """Award tokens to employee (from game wins, admin awards, etc)."""
        try:
            with DatabaseConnection() as conn:
                # Add tokens
                conn.execute("""
                    UPDATE employee_tokens 
                    SET token_balance = token_balance + ?,
                        total_tokens_earned = total_tokens_earned + ?
                    WHERE employee_id = ?
                """, (token_amount, token_amount, employee_id))
                
                # Log transaction
                conn.execute("""
                    INSERT INTO token_transactions 
                    (employee_id, transaction_type, token_amount, admin_notes)
                    VALUES (?, 'win', ?, ?)
                """, (employee_id, token_amount, f"{source} - {admin_notes}"))
                
                conn.commit()
                return True, f"Awarded {token_amount} tokens"
                
        except Exception as e:
            logging.error(f"Error awarding tokens to {employee_id}: {e}")
            return False, "Award failed"

    def get_token_transaction_history(self, employee_id, limit=50):
        """Get token transaction history for employee."""
        try:
            with DatabaseConnection() as conn:
                transactions = conn.execute("""
                    SELECT * FROM token_transactions
                    WHERE employee_id = ?
                    ORDER BY transaction_date DESC
                    LIMIT ?
                """, (employee_id, limit)).fetchall()
                
                return [dict(tx) for tx in transactions]
                
        except Exception as e:
            logging.error(f"Error getting token history for {employee_id}: {e}")
            return []

    def reset_daily_exchange_limits(self):
        """Reset daily exchange limits (run as scheduled task)."""
        try:
            with DatabaseConnection() as conn:
                conn.execute("""
                    UPDATE employee_tokens 
                    SET daily_exchange_count = 0
                    WHERE DATE(last_exchange_date) < DATE('now')
                """)
                conn.commit()
                
                rows_affected = conn.total_changes
                logging.info(f"Reset daily exchange limits for {rows_affected} accounts")
                return True
                
        except Exception as e:
            logging.error(f"Error resetting daily limits: {e}")
            return False

    def get_token_economy_stats(self):
        """Get system-wide token economy statistics."""
        try:
            with DatabaseConnection() as conn:
                stats = {}
                
                # Total tokens in circulation
                result = conn.execute("SELECT SUM(token_balance) FROM employee_tokens").fetchone()
                stats['total_tokens_in_circulation'] = result[0] or 0
                
                # Total tokens ever earned/spent
                result = conn.execute("SELECT SUM(total_tokens_earned), SUM(total_tokens_spent) FROM employee_tokens").fetchone()
                stats['total_tokens_earned'] = result[0] or 0
                stats['total_tokens_spent'] = result[1] or 0
                
                # Active token users (have tokens or recent activity)
                result = conn.execute("""
                    SELECT COUNT(DISTINCT employee_id) FROM employee_tokens 
                    WHERE token_balance > 0 OR last_exchange_date > date('now', '-7 days')
                """).fetchone()
                stats['active_token_users'] = result[0] or 0
                
                # Recent exchange activity
                result = conn.execute("""
                    SELECT COUNT(*), SUM(token_amount) FROM token_transactions
                    WHERE transaction_type = 'purchase' AND transaction_date > date('now', '-7 days')
                """).fetchone()
                stats['weekly_exchanges'] = result[0] or 0
                stats['weekly_tokens_purchased'] = result[1] or 0
                
                return stats
                
        except Exception as e:
            logging.error(f"Error getting token economy stats: {e}")
            return {}

# Global instance
token_economy = TokenEconomyService()