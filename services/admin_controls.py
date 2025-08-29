# services/admin_controls.py
# Comprehensive Admin Controls for Dual Game System

import sqlite3
import logging
import json
from datetime import datetime, timedelta
from incentive_service import DatabaseConnection
from services.token_economy import token_economy
from services.dual_game_manager import dual_game_manager

class AdminControlsService:
    """Comprehensive administrative controls for the dual game system."""
    
    def __init__(self):
        self.config_categories = ['reward_system', 'gambling_system', 'token_economy', 'security']

    def get_system_overview(self):
        """Get comprehensive system overview for admin dashboard."""
        try:
            with DatabaseConnection() as conn:
                overview = {}
                
                # Token economy stats
                overview['token_economy'] = token_economy.get_token_economy_stats()
                
                # Category A stats
                category_a_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_reward_games,
                        COUNT(CASE WHEN status = 'unused' THEN 1 END) as unused_reward_games,
                        COUNT(CASE WHEN outcome = 'win' THEN 1 END) as reward_wins,
                        COUNT(DISTINCT employee_id) as active_reward_players
                    FROM mini_games 
                    WHERE game_category = 'reward' AND awarded_date > date('now', '-30 days')
                """).fetchone()
                overview['category_a'] = dict(category_a_stats) if category_a_stats else {}
                
                # Category B stats
                category_b_stats = conn.execute("""
                    SELECT 
                        COUNT(*) as total_gambling_games,
                        COUNT(CASE WHEN outcome = 'win' THEN 1 END) as gambling_wins,
                        COALESCE(SUM(token_cost), 0) as total_tokens_spent,
                        COUNT(DISTINCT employee_id) as active_gambling_players,
                        ROUND(AVG(CASE WHEN outcome = 'win' THEN 1.0 ELSE 0.0 END) * 100, 2) as win_rate
                    FROM mini_games 
                    WHERE game_category = 'gambling' AND played_date > date('now', '-30 days')
                """).fetchone()
                overview['category_b'] = dict(category_b_stats) if category_b_stats else {}
                
                # Global prize pool status
                global_pools = conn.execute("""
                    SELECT prize_type, daily_limit, daily_used, 
                           weekly_limit, weekly_used, monthly_limit, monthly_used
                    FROM global_prize_pools
                """).fetchall()
                overview['global_pools'] = [dict(pool) for pool in global_pools]
                
                # Recent behavior flags
                recent_flags = conn.execute("""
                    SELECT flag_type, flag_severity, COUNT(*) as count
                    FROM employee_behavior_flags
                    WHERE created_date > date('now', '-7 days') AND resolved_date IS NULL
                    GROUP BY flag_type, flag_severity
                """).fetchall()
                overview['behavior_flags'] = [dict(flag) for flag in recent_flags]
                
                # Budget tracking
                overview['budget_status'] = self._calculate_budget_status(conn)
                
                return overview
                
        except Exception as e:
            logging.error(f"Error getting system overview: {e}")
            return {}

    def _calculate_budget_status(self, conn):
        """Calculate current budget utilization."""
        try:
            # Calculate Category A costs (guaranteed rewards)
            category_a_cost = conn.execute("""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN prize_type LIKE '%cash%' THEN prize_amount
                        WHEN prize_type LIKE '%points%' THEN prize_amount * 0.01  -- $0.01 per point
                        WHEN prize_type LIKE '%pto%' OR prize_type LIKE '%vacation%' THEN prize_amount * 25  -- $25/hour
                        ELSE 10  -- default cost
                    END
                ), 0) FROM game_history
                WHERE game_category = 'reward' AND play_date > date('now', 'start of month')
            """).fetchone()[0]
            
            # Calculate Category B costs (token subsidies + prizes)
            category_b_cost = conn.execute("""
                SELECT COALESCE(SUM(
                    CASE 
                        WHEN prize_type LIKE '%cash%' THEN prize_amount
                        WHEN prize_type LIKE '%points%' THEN prize_amount * 0.01
                        WHEN prize_type LIKE '%pto%' OR prize_type LIKE '%vacation%' THEN prize_amount * 25
                        ELSE 5
                    END
                ), 0) FROM game_history
                WHERE game_category = 'gambling' AND play_date > date('now', 'start of month')
            """).fetchone()[0]
            
            # Token exchange subsidy (difference between point value and token value)
            token_subsidy = conn.execute("""
                SELECT COALESCE(SUM(points_amount * 0.01), 0) FROM token_transactions
                WHERE transaction_type = 'purchase' AND transaction_date > date('now', 'start of month')
            """).fetchone()[0]
            
            total_cost = category_a_cost + category_b_cost + token_subsidy
            
            return {
                'category_a_cost': round(category_a_cost, 2),
                'category_b_cost': round(category_b_cost, 2),
                'token_subsidy': round(token_subsidy, 2),
                'total_monthly_cost': round(total_cost, 2),
                'budget_utilization': round(total_cost / 5000 * 100, 2)  # Assuming $5000 monthly budget
            }
            
        except Exception as e:
            logging.error(f"Error calculating budget status: {e}")
            return {}

    def update_global_prize_pool(self, prize_type, daily_limit=None, weekly_limit=None, monthly_limit=None, admin_id="ADMIN"):
        """Update global prize pool limits."""
        try:
            with DatabaseConnection() as conn:
                updates = []
                params = []
                
                if daily_limit is not None:
                    updates.append("daily_limit = ?")
                    params.append(daily_limit)
                
                if weekly_limit is not None:
                    updates.append("weekly_limit = ?")
                    params.append(weekly_limit)
                
                if monthly_limit is not None:
                    updates.append("monthly_limit = ?")
                    params.append(monthly_limit)
                
                if not updates:
                    return False, "No updates specified"
                
                query = f"UPDATE global_prize_pools SET {', '.join(updates)} WHERE prize_type = ?"
                params.append(prize_type)
                
                conn.execute(query, params)
                
                # Log the change
                conn.execute("""
                    INSERT INTO admin_game_config 
                    (config_category, config_key, config_value, updated_by)
                    VALUES ('gambling_system', ?, ?, ?)
                """, (f"global_pool_{prize_type}", json.dumps({
                    'daily_limit': daily_limit,
                    'weekly_limit': weekly_limit,
                    'monthly_limit': monthly_limit
                }), admin_id))
                
                conn.commit()
                
                logging.info(f"Updated global prize pool {prize_type} by {admin_id}")
                return True, f"Updated {prize_type} limits"
                
        except Exception as e:
            logging.error(f"Error updating global prize pool: {e}")
            return False, "Update failed"

    def update_token_economy_config(self, tier=None, exchange_rate=None, daily_limit=None, cooldown_hours=None, admin_id="ADMIN"):
        """Update token economy configuration."""
        try:
            if not tier:
                return False, "Tier must be specified"
            
            updates = {}
            if exchange_rate is not None:
                token_economy.tier_exchange_rates[tier] = exchange_rate
                updates['exchange_rate'] = exchange_rate
            
            if daily_limit is not None:
                token_economy.tier_daily_limits[tier] = daily_limit
                updates['daily_limit'] = daily_limit
            
            if cooldown_hours is not None:
                token_economy.tier_cooldowns[tier] = cooldown_hours
                updates['cooldown_hours'] = cooldown_hours
            
            if not updates:
                return False, "No updates specified"
            
            with DatabaseConnection() as conn:
                # Log the configuration change
                conn.execute("""
                    INSERT INTO admin_game_config 
                    (config_category, config_key, config_value, tier_specific, updated_by)
                    VALUES ('token_economy', ?, ?, ?, ?)
                """, (f"{tier}_config", json.dumps(updates), tier, admin_id))
                
                conn.commit()
            
            logging.info(f"Updated token economy config for {tier} by {admin_id}")
            return True, f"Updated {tier} tier token settings"
            
        except Exception as e:
            logging.error(f"Error updating token economy config: {e}")
            return False, "Update failed"

    def award_category_a_games_bulk(self, employee_ids, source="admin_bulk", description="", admin_id="ADMIN"):
        """Award Category A games to multiple employees."""
        try:
            results = {'success': [], 'failed': []}
            
            for employee_id in employee_ids:
                success, message = dual_game_manager.award_category_a_game(
                    employee_id, source, description, admin_id
                )
                
                if success:
                    results['success'].append({'employee_id': employee_id, 'message': message})
                else:
                    results['failed'].append({'employee_id': employee_id, 'error': message})
            
            logging.info(f"Bulk award by {admin_id}: {len(results['success'])} success, {len(results['failed'])} failed")
            return True, f"Awarded games to {len(results['success'])} employees", results
            
        except Exception as e:
            logging.error(f"Error in bulk award: {e}")
            return False, "Bulk award failed", {}

    def award_tokens_bulk(self, employee_ids, token_amount, description="Admin award", admin_id="ADMIN"):
        """Award tokens to multiple employees."""
        try:
            results = {'success': [], 'failed': []}
            
            for employee_id in employee_ids:
                success, message = token_economy.award_tokens(
                    employee_id, token_amount, f"Admin award: {description}", f"Bulk award by {admin_id}"
                )
                
                if success:
                    results['success'].append({'employee_id': employee_id, 'message': message})
                else:
                    results['failed'].append({'employee_id': employee_id, 'error': message})
            
            logging.info(f"Bulk token award by {admin_id}: {len(results['success'])} success, {len(results['failed'])} failed")
            return True, f"Awarded {token_amount} tokens to {len(results['success'])} employees", results
            
        except Exception as e:
            logging.error(f"Error in bulk token award: {e}")
            return False, "Bulk token award failed", {}

    def get_behavioral_alerts(self):
        """Get current behavioral monitoring alerts."""
        try:
            with DatabaseConnection() as conn:
                alerts = conn.execute("""
                    SELECT ebf.*, e.name as employee_name
                    FROM employee_behavior_flags ebf
                    JOIN employees e ON ebf.employee_id = e.employee_id
                    WHERE ebf.resolved_date IS NULL
                    ORDER BY ebf.flag_severity DESC, ebf.created_date DESC
                """).fetchall()
                
                return [dict(alert) for alert in alerts]
                
        except Exception as e:
            logging.error(f"Error getting behavioral alerts: {e}")
            return []

    def create_behavioral_alert(self, employee_id, flag_type, severity, details, admin_id="SYSTEM"):
        """Create a behavioral monitoring alert."""
        try:
            with DatabaseConnection() as conn:
                conn.execute("""
                    INSERT INTO employee_behavior_flags
                    (employee_id, flag_type, flag_severity, flag_data, created_date)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (employee_id, flag_type, severity, json.dumps(details)))
                
                conn.commit()
                
                logging.warning(f"Behavioral alert created for {employee_id}: {flag_type} ({severity})")
                return True, "Alert created"
                
        except Exception as e:
            logging.error(f"Error creating behavioral alert: {e}")
            return False, "Failed to create alert"

    def resolve_behavioral_alert(self, alert_id, resolution_notes, admin_id):
        """Resolve a behavioral monitoring alert."""
        try:
            with DatabaseConnection() as conn:
                conn.execute("""
                    UPDATE employee_behavior_flags 
                    SET resolved_date = CURRENT_TIMESTAMP,
                        resolved_by = ?
                    WHERE id = ?
                """, (f"{admin_id}: {resolution_notes}", alert_id))
                
                conn.commit()
                
                logging.info(f"Behavioral alert {alert_id} resolved by {admin_id}")
                return True, "Alert resolved"
                
        except Exception as e:
            logging.error(f"Error resolving behavioral alert: {e}")
            return False, "Failed to resolve alert"

    def get_employee_detailed_report(self, employee_id):
        """Get comprehensive employee report for admin review."""
        try:
            with DatabaseConnection() as conn:
                # Basic employee info
                employee = conn.execute("""
                    SELECT e.*, et.token_balance, et.total_tokens_earned, et.total_tokens_spent
                    FROM employees e
                    LEFT JOIN employee_tokens et ON e.employee_id = et.employee_id
                    WHERE e.employee_id = ?
                """, (employee_id,)).fetchone()
                
                if not employee:
                    return None
                
                # Game summary
                game_summary = dual_game_manager.get_employee_game_summary(employee_id)
                
                # Recent transactions
                token_history = token_economy.get_token_transaction_history(employee_id, 20)
                
                # Prize limit status
                prize_limits = conn.execute("""
                    SELECT * FROM employee_prize_limits WHERE employee_id = ?
                """, (employee_id,)).fetchall()
                
                # Behavioral flags
                behavior_flags = conn.execute("""
                    SELECT * FROM employee_behavior_flags 
                    WHERE employee_id = ? 
                    ORDER BY created_date DESC LIMIT 10
                """, (employee_id,)).fetchall()
                
                # Recent game history
                recent_games = conn.execute("""
                    SELECT gh.*, mg.game_category, mg.guaranteed_win
                    FROM game_history gh
                    JOIN mini_games mg ON gh.mini_game_id = mg.id
                    WHERE mg.employee_id = ?
                    ORDER BY gh.play_date DESC LIMIT 20
                """, (employee_id,)).fetchall()
                
                return {
                    'employee': dict(employee),
                    'game_summary': game_summary,
                    'token_history': token_history,
                    'prize_limits': [dict(limit) for limit in prize_limits],
                    'behavior_flags': [dict(flag) for flag in behavior_flags],
                    'recent_games': [dict(game) for game in recent_games]
                }
                
        except Exception as e:
            logging.error(f"Error getting employee report for {employee_id}: {e}")
            return None

    def emergency_system_shutdown(self, reason, admin_id):
        """Emergency shutdown of dual game system."""
        try:
            with DatabaseConnection() as conn:
                # Disable all game categories
                conn.execute("""
                    INSERT INTO admin_game_config 
                    (config_category, config_key, config_value, updated_by)
                    VALUES ('security', 'system_shutdown', ?, ?)
                """, (json.dumps({'active': True, 'reason': reason, 'timestamp': datetime.now().isoformat()}), admin_id))
                
                conn.commit()
                
                logging.critical(f"EMERGENCY SHUTDOWN initiated by {admin_id}: {reason}")
                return True, "Emergency shutdown activated"
                
        except Exception as e:
            logging.error(f"Error in emergency shutdown: {e}")
            return False, "Shutdown failed"

    def get_system_audit_log(self, limit=100):
        """Get system audit log for admin review."""
        try:
            with DatabaseConnection() as conn:
                audit_entries = conn.execute("""
                    SELECT * FROM admin_game_config
                    ORDER BY last_updated DESC
                    LIMIT ?
                """, (limit,)).fetchall()
                
                return [dict(entry) for entry in audit_entries]
                
        except Exception as e:
            logging.error(f"Error getting audit log: {e}")
            return []

# Global instance
admin_controls = AdminControlsService()