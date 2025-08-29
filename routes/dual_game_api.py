# routes/dual_game_api.py
"""
API Routes for Refined Dual Game System
Provides endpoints for game operations, configuration, and monitoring.
"""

from flask import Blueprint, request, jsonify, session
from functools import wraps
import logging
import json
from datetime import datetime
from incentive_service import DatabaseConnection
from services.refined_dual_game_system import (
    refined_game_manager, 
    GameCategory, 
    DifficultyLevel
)
from services.game_configuration import game_config_manager
from services.token_economy import token_economy

# Create blueprint
dual_game_api = Blueprint('dual_game_api', __name__, url_prefix='/api/dual_game')

def require_auth(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'employee_id' not in session and 'admin_id' not in session:
            return jsonify({'success': False, 'message': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def require_admin(f):
    """Decorator to require admin authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session:
            return jsonify({'success': False, 'message': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

# Game Playing Endpoints
@dual_game_api.route('/play/<int:game_id>', methods=['POST'])
@require_auth
def play_game(game_id):
    """Play a game (Category A or B)"""
    try:
        employee_id = session.get('employee_id') or session.get('admin_id')
        
        with DatabaseConnection() as conn:
            result = refined_game_manager.play_game(conn, employee_id, game_id)
            
            if result.get('success'):
                # Track analytics
                conn.execute("""
                    INSERT INTO game_history 
                    (mini_game_id, game_type, play_date, outcome, prize_type, 
                     prize_description, prize_amount)
                    VALUES (?, ?, CURRENT_TIMESTAMP, ?, ?, ?, ?)
                """, (game_id, 'dual_game', result.get('outcome'), 
                      result.get('prize', {}).get('type'),
                      result.get('message'), 
                      result.get('prize', {}).get('value', 0)))
                conn.commit()
            
            return jsonify(result)
            
    except Exception as e:
        logging.error(f"Error playing game {game_id}: {e}")
        return jsonify({'success': False, 'message': 'Game play failed'}), 500

@dual_game_api.route('/available', methods=['GET'])
@require_auth
def get_available_games():
    """Get available games for employee"""
    try:
        employee_id = session.get('employee_id') or session.get('admin_id')
        
        with DatabaseConnection() as conn:
            # Get unused games
            games = conn.execute("""
                SELECT mg.*, 
                       CASE 
                           WHEN mg.game_category = 'guaranteed' THEN 'Category A'
                           ELSE 'Category B'
                       END as category_display,
                       CASE mg.difficulty_level
                           WHEN 1 THEN 'Trivial'
                           WHEN 2 THEN 'Easy'
                           WHEN 3 THEN 'Moderate'
                           WHEN 4 THEN 'Hard'
                           WHEN 5 THEN 'Extreme'
                           ELSE 'Unknown'
                       END as difficulty_display
                FROM mini_games mg
                WHERE mg.employee_id = ? AND mg.status = 'unused'
                ORDER BY mg.awarded_date DESC
            """, (employee_id,)).fetchall()
            
            # Get token balance for Category B games
            token_account = token_economy.get_employee_token_account(employee_id)
            
            return jsonify({
                'success': True,
                'games': [dict(game) for game in games],
                'token_balance': token_account.get('token_balance', 0) if token_account else 0,
                'tier': token_account.get('tier_level', 'bronze') if token_account else 'bronze'
            })
            
    except Exception as e:
        logging.error(f"Error getting available games: {e}")
        return jsonify({'success': False, 'message': 'Failed to get games'}), 500

# Token Exchange Endpoints
@dual_game_api.route('/tokens/exchange', methods=['POST'])
@require_auth
def exchange_tokens():
    """Exchange points for tokens or vice versa"""
    try:
        employee_id = session.get('employee_id') or session.get('admin_id')
        data = request.json
        
        direction = data.get('direction', 'points_to_tokens')
        amount = int(data.get('amount', 0))
        
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Invalid amount'}), 400
        
        with DatabaseConnection() as conn:
            # Get employee data
            employee = conn.execute("""
                SELECT e.*, et.token_balance, et.daily_exchange_count, 
                       et.last_exchange_date
                FROM employees e
                LEFT JOIN employee_tokens et ON e.employee_id = et.employee_id
                WHERE e.employee_id = ?
            """, (employee_id,)).fetchone()
            
            if not employee:
                return jsonify({'success': False, 'message': 'Employee not found'}), 404
            
            employee_data = dict(employee)
            
            # Check if exchange is allowed
            exchange_manager = refined_game_manager.exchange_manager
            can_exchange, message = exchange_manager.can_exchange(employee_data, amount, direction)
            
            if not can_exchange:
                return jsonify({'success': False, 'message': message}), 400
            
            # Calculate exchange
            rate = exchange_manager.calculate_exchange_rate(
                employee_data.get('tier_level', 'bronze'), 
                direction
            )
            
            if direction == 'points_to_tokens':
                points_cost = int(amount * rate)
                
                # Deduct points and add tokens
                conn.execute("""
                    UPDATE employees SET score = score - ? WHERE employee_id = ?
                """, (points_cost, employee_id))
                
                conn.execute("""
                    UPDATE employee_tokens 
                    SET token_balance = token_balance + ?,
                        daily_exchange_count = daily_exchange_count + ?,
                        last_exchange_date = CURRENT_TIMESTAMP,
                        last_activity_date = CURRENT_TIMESTAMP
                    WHERE employee_id = ?
                """, (amount, amount, employee_id))
                
                # Log transaction
                conn.execute("""
                    INSERT INTO token_transactions 
                    (employee_id, transaction_type, points_amount, token_amount, exchange_rate)
                    VALUES (?, 'purchase', ?, ?, ?)
                """, (employee_id, points_cost, amount, rate))
                
                message = f"Exchanged {points_cost} points for {amount} tokens"
                
            else:  # tokens_to_points
                points_returned = int(amount / rate)
                
                # Deduct tokens and add points
                conn.execute("""
                    UPDATE employee_tokens 
                    SET token_balance = token_balance - ?,
                        last_activity_date = CURRENT_TIMESTAMP
                    WHERE employee_id = ?
                """, (amount, employee_id))
                
                conn.execute("""
                    UPDATE employees SET score = score + ? WHERE employee_id = ?
                """, (points_returned, employee_id))
                
                # Log transaction
                conn.execute("""
                    INSERT INTO token_transactions 
                    (employee_id, transaction_type, points_amount, token_amount, exchange_rate)
                    VALUES (?, 'reverse', ?, ?, ?)
                """, (employee_id, points_returned, -amount, rate))
                
                message = f"Exchanged {amount} tokens for {points_returned} points"
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': message,
                'new_balance': {
                    'points': conn.execute("SELECT score FROM employees WHERE employee_id = ?", 
                                          (employee_id,)).fetchone()['score'],
                    'tokens': conn.execute("SELECT token_balance FROM employee_tokens WHERE employee_id = ?", 
                                          (employee_id,)).fetchone()['token_balance']
                }
            })
            
    except Exception as e:
        logging.error(f"Error exchanging tokens: {e}")
        return jsonify({'success': False, 'message': 'Exchange failed'}), 500

@dual_game_api.route('/tokens/balance', methods=['GET'])
@require_auth
def get_token_balance():
    """Get current token balance and exchange rates"""
    try:
        employee_id = session.get('employee_id') or session.get('admin_id')
        
        account = token_economy.get_employee_token_account(employee_id)
        
        if not account:
            return jsonify({'success': False, 'message': 'Account not found'}), 404
        
        # Get exchange rates
        exchange_manager = refined_game_manager.exchange_manager
        tier = account.get('tier_level', 'bronze')
        
        return jsonify({
            'success': True,
            'balance': account.get('token_balance', 0),
            'tier': tier,
            'exchange_rates': {
                'points_to_tokens': exchange_manager.calculate_exchange_rate(tier, 'points_to_tokens'),
                'tokens_to_points': exchange_manager.calculate_exchange_rate(tier, 'tokens_to_points')
            },
            'daily_limit': account.get('daily_exchange_limit', 50),
            'daily_used': account.get('daily_exchange_count', 0)
        })
        
    except Exception as e:
        logging.error(f"Error getting token balance: {e}")
        return jsonify({'success': False, 'message': 'Failed to get balance'}), 500

# Admin Configuration Endpoints
@dual_game_api.route('/config/current', methods=['GET'])
@require_admin
def get_current_config():
    """Get current game configuration"""
    try:
        config = game_config_manager.get_admin_display_config()
        return jsonify({'success': True, 'config': config})
        
    except Exception as e:
        logging.error(f"Error getting config: {e}")
        return jsonify({'success': False, 'message': 'Failed to get configuration'}), 500

@dual_game_api.route('/config/update', methods=['POST'])
@require_admin
def update_config():
    """Update game configuration"""
    try:
        data = request.json
        section = data.get('section')
        settings = data.get('data')
        
        if not section or not settings:
            return jsonify({'success': False, 'message': 'Invalid request'}), 400
        
        with DatabaseConnection() as conn:
            success = game_config_manager.update_setting(conn, section, section, settings)
            
            if success:
                # Log configuration change
                conn.execute("""
                    INSERT INTO history 
                    (employee_id, action, points_change, admin_id, created_at)
                    VALUES ('SYSTEM', ?, 0, ?, CURRENT_TIMESTAMP)
                """, (f"Updated {section} configuration", session.get('admin_id')))
                conn.commit()
                
                return jsonify({'success': True, 'message': 'Configuration updated'})
            else:
                return jsonify({'success': False, 'message': 'Failed to update configuration'}), 500
                
    except Exception as e:
        logging.error(f"Error updating config: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@dual_game_api.route('/config/export', methods=['GET'])
@require_admin
def export_config():
    """Export current configuration"""
    try:
        with DatabaseConnection() as conn:
            config_json = game_config_manager.export_config(conn)
            config = json.loads(config_json)
            
            return jsonify({
                'success': True,
                'config': config,
                'exported_at': datetime.now().isoformat()
            })
            
    except Exception as e:
        logging.error(f"Error exporting config: {e}")
        return jsonify({'success': False, 'message': 'Export failed'}), 500

@dual_game_api.route('/config/import', methods=['POST'])
@require_admin
def import_config():
    """Import configuration"""
    try:
        config_data = request.get_json()
        
        with DatabaseConnection() as conn:
            success, errors = game_config_manager.import_config(conn, json.dumps(config_data))
            
            if success:
                return jsonify({'success': True, 'message': 'Configuration imported'})
            else:
                return jsonify({'success': False, 'errors': errors}), 400
                
    except Exception as e:
        logging.error(f"Error importing config: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@dual_game_api.route('/config/validate', methods=['GET'])
@require_admin
def validate_config():
    """Validate current configuration"""
    try:
        config = game_config_manager.load_config()
        errors = game_config_manager.validate_config(config)
        
        return jsonify({
            'success': True,
            'valid': len(errors) == 0,
            'errors': errors
        })
        
    except Exception as e:
        logging.error(f"Error validating config: {e}")
        return jsonify({'success': False, 'message': 'Validation failed'}), 500

@dual_game_api.route('/config/reset', methods=['POST'])
@require_admin
def reset_config():
    """Reset configuration to defaults"""
    try:
        with DatabaseConnection() as conn:
            from services.game_configuration import DualGameConfig
            
            default_config = DualGameConfig()
            success = game_config_manager.save_config(conn, default_config)
            
            if success:
                return jsonify({'success': True, 'message': 'Configuration reset to defaults'})
            else:
                return jsonify({'success': False, 'message': 'Reset failed'}), 500
                
    except Exception as e:
        logging.error(f"Error resetting config: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

# Monitoring and Analytics Endpoints
@dual_game_api.route('/metrics', methods=['GET'])
@require_admin
def get_system_metrics():
    """Get system metrics and analytics"""
    try:
        with DatabaseConnection() as conn:
            metrics = refined_game_manager.get_system_metrics(conn)
            
            return jsonify({
                'success': True,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            })
            
    except Exception as e:
        logging.error(f"Error getting metrics: {e}")
        return jsonify({'success': False, 'message': 'Failed to get metrics'}), 500

@dual_game_api.route('/employee/<employee_id>/summary', methods=['GET'])
@require_admin
def get_employee_summary(employee_id):
    """Get employee game summary"""
    try:
        with DatabaseConnection() as conn:
            # Get employee game stats
            stats = conn.execute("""
                SELECT 
                    COUNT(*) as total_games,
                    SUM(CASE WHEN status = 'unused' THEN 1 ELSE 0 END) as unused_games,
                    SUM(CASE WHEN game_category = 'guaranteed' THEN 1 ELSE 0 END) as category_a_games,
                    SUM(CASE WHEN game_category = 'gambling' THEN 1 ELSE 0 END) as category_b_games,
                    SUM(CASE WHEN outcome LIKE '%win%' THEN 1 ELSE 0 END) as total_wins
                FROM mini_games
                WHERE employee_id = ?
            """, (employee_id,)).fetchone()
            
            # Get token info
            token_account = token_economy.get_employee_token_account(employee_id)
            
            # Get recent prizes
            recent_prizes = conn.execute("""
                SELECT prize_type, prize_value, awarded_date
                FROM prize_awards
                WHERE employee_id = ?
                ORDER BY awarded_date DESC
                LIMIT 10
            """, (employee_id,)).fetchall()
            
            return jsonify({
                'success': True,
                'summary': {
                    'game_stats': dict(stats) if stats else {},
                    'token_account': token_account,
                    'recent_prizes': [dict(prize) for prize in recent_prizes]
                }
            })
            
    except Exception as e:
        logging.error(f"Error getting employee summary: {e}")
        return jsonify({'success': False, 'message': 'Failed to get summary'}), 500

# Manual Award Endpoint
@dual_game_api.route('/award', methods=['POST'])
@require_admin
def award_game_manual():
    """Manually award a game to an employee"""
    try:
        data = request.json
        employee_id = data.get('employee_id')
        category = data.get('category', 'guaranteed')
        difficulty = data.get('difficulty', 2)
        reason = data.get('reason', 'Manual admin award')
        
        if not employee_id:
            return jsonify({'success': False, 'message': 'Employee ID required'}), 400
        
        with DatabaseConnection() as conn:
            result = refined_game_manager.award_game_for_achievement(
                conn, 
                employee_id,
                'admin_manual',
                DifficultyLevel(difficulty)
            )
            
            # Log the award
            conn.execute("""
                INSERT INTO history 
                (employee_id, action, points_change, admin_id, created_at)
                VALUES (?, ?, 0, ?, CURRENT_TIMESTAMP)
            """, (employee_id, f"Awarded {category} game: {reason}", session.get('admin_id')))
            
            conn.commit()
            
            return jsonify({
                'success': True,
                'message': f"Game awarded successfully",
                'game_id': result.get('game_id')
            })
            
    except Exception as e:
        logging.error(f"Error awarding game: {e}")
        return jsonify({'success': False, 'message': 'Failed to award game'}), 500

# Scheduled Task Endpoints
@dual_game_api.route('/tasks/monthly_reset', methods=['POST'])
@require_admin
def run_monthly_reset():
    """Manually trigger monthly reset"""
    try:
        with DatabaseConnection() as conn:
            results = refined_game_manager.process_monthly_reset(conn)
            
            return jsonify({
                'success': True,
                'message': 'Monthly reset completed',
                'results': results
            })
            
    except Exception as e:
        logging.error(f"Error running monthly reset: {e}")
        return jsonify({'success': False, 'message': 'Reset failed'}), 500

@dual_game_api.route('/tasks/auto_reverse', methods=['POST'])
@require_admin
def run_auto_reverse():
    """Manually trigger auto token reversal"""
    try:
        with DatabaseConnection() as conn:
            results = refined_game_manager.exchange_manager.process_auto_reverse(conn)
            
            return jsonify({
                'success': True,
                'message': f"Processed {len(results)} reversals",
                'results': results
            })
            
    except Exception as e:
        logging.error(f"Error running auto reverse: {e}")
        return jsonify({'success': False, 'message': 'Auto reverse failed'}), 500