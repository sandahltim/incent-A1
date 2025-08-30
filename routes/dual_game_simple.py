#!/usr/bin/env python3
"""
Simple dual game system API routes
Integrated with existing Flask app structure
"""

from flask import Blueprint, request, jsonify, session, current_app
import sqlite3
import json
from datetime import datetime, date
import random
import logging
import calendar

# Create blueprint
dual_game_bp = Blueprint('dual_game', __name__, url_prefix='/api/dual_game')

def get_db_connection():
    """Get database connection using existing pattern"""
    return sqlite3.connect('/home/tim/incentDev/incentive.db')

def is_end_of_month():
    """Check if today is the last day of the month"""
    today = date.today()
    last_day = calendar.monthrange(today.year, today.month)[1]
    return today.day == last_day

def check_monthly_jackpot_eligibility(cursor, employee_id):
    """Check if employee is eligible for monthly jackpot"""
    # Check if employee played games this month
    cursor.execute("""
        SELECT COUNT(*) FROM token_transactions 
        WHERE employee_id = ? 
        AND strftime('%Y-%m', transaction_date) = strftime('%Y-%m', 'now')
        AND transaction_type IN ('win', 'spend')
    """, (employee_id,))
    
    monthly_activity = cursor.fetchone()[0]
    
    # Must have played at least 5 games this month to be eligible
    return monthly_activity >= 5

@dual_game_bp.route('/status')
def status():
    """Check dual game system status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('employee_tokens', 'admin_game_config')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get basic stats
        cursor.execute("SELECT COUNT(*) FROM employee_tokens")
        token_accounts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM admin_game_config")
        config_entries = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'status': 'active',
            'tables_found': tables,
            'token_accounts': token_accounts,
            'config_entries': config_entries,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dual_game_bp.route('/tokens/<employee_id>')
def get_tokens(employee_id):
    """Get employee token balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT token_balance, total_tokens_earned, total_tokens_spent 
            FROM employee_tokens 
            WHERE employee_id = ?
        """, (employee_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'employee_id': employee_id,
                'token_balance': result[0],
                'total_tokens_earned': result[1],
                'total_tokens_spent': result[2]
            })
        else:
            return jsonify({'error': 'Employee not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dual_game_bp.route('/exchange', methods=['POST'])
def exchange_tokens():
    """Exchange points for tokens"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        points = int(data.get('points', 0))
        
        if points <= 0:
            return jsonify({'error': 'Invalid points amount'}), 400
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get employee tier for exchange rate
        cursor.execute("SELECT role, score FROM employees WHERE employee_id = ?", (employee_id,))
        employee = cursor.fetchone()
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Check if employee has enough points
        points_required = points
        if employee[1] < points_required:
            return jsonify({'error': f'Insufficient points (have {employee[1]}, need {points_required})'}), 400
        
        # Map actual roles to tier levels and exchange rates
        role_to_tier = {
            'laborer': 'Bronze',
            'driver': 'Silver', 
            'supervisor': 'Gold',
            'master': 'Platinum'
        }
        
        # Simple exchange rates by tier
        exchange_rates = {
            'Bronze': 10,  # 10 points = 1 token
            'Silver': 8,   # 8 points = 1 token
            'Gold': 6,     # 6 points = 1 token
            'Platinum': 5  # 5 points = 1 token
        }
        
        tier = role_to_tier.get(employee[0], 'Bronze')
        rate = exchange_rates.get(tier, 10)
        tokens_to_add = points // rate
        
        if tokens_to_add <= 0:
            return jsonify({'error': f'Not enough points for exchange (need at least {rate})'}), 400
        
        # Update token balance
        cursor.execute("""
            UPDATE employee_tokens 
            SET token_balance = token_balance + ?,
                total_tokens_earned = total_tokens_earned + ?,
                last_exchange_date = CURRENT_TIMESTAMP
            WHERE employee_id = ?
        """, (tokens_to_add, tokens_to_add, employee_id))
        
        # Record exchange
        cursor.execute("""
            INSERT INTO token_transactions 
            (employee_id, transaction_type, points_amount, token_amount, exchange_rate)
            VALUES (?, 'points_to_tokens', ?, ?, ?)
        """, (employee_id, points, tokens_to_add, rate))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'points_used': points,
            'tokens_received': tokens_to_add,
            'exchange_rate': rate
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dual_game_bp.route('/play/<game_type>', methods=['POST'])
def play_game(game_type):
    """Play a dual game"""
    try:
        data = request.get_json()
        employee_id = data.get('employee_id')
        category = data.get('category', 'A')  # A or B
        bet_amount = int(data.get('bet_amount', 0))
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if category == 'A':
            # Category A - Guaranteed win
            result = play_category_a_game(cursor, employee_id, game_type)
        else:
            # Category B - Token gambling
            if bet_amount <= 0:
                return jsonify({'error': 'Bet amount required for Category B'}), 400
            result = play_category_b_game(cursor, employee_id, game_type, bet_amount)
        
        # TODO: Record game play in appropriate history table
        # For now, skip history logging until proper table structure is confirmed
        
        conn.commit()
        conn.close()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def play_category_a_game(cursor, employee_id, game_type):
    """Play Category A game (guaranteed win)"""
    
    # Get employee tier
    cursor.execute("SELECT role FROM employees WHERE employee_id = ?", (employee_id,))
    employee = cursor.fetchone()
    
    # Map actual roles to tier levels
    role_to_tier = {
        'laborer': 'Bronze',
        'driver': 'Silver',
        'supervisor': 'Gold', 
        'master': 'Platinum'
    }
    
    role = employee[0] if employee else 'laborer'
    tier = role_to_tier.get(role, 'Bronze')
    
    # Tier-based prizes
    tier_prizes = {
        'Bronze': {'points': 10, 'pto_hours': 1, 'swag': 'Basic Item'},
        'Silver': {'points': 20, 'pto_hours': 2, 'swag': 'Standard Item'},
        'Gold': {'points': 30, 'pto_hours': 4, 'swag': 'Premium Item'},
        'Platinum': {'points': 50, 'pto_hours': 6, 'swag': 'Exclusive Item'}
    }
    
    prize_options = tier_prizes.get(tier, tier_prizes['Bronze'])
    
    # Random prize selection (weighted toward points)
    prize_type = random.choices(
        ['points', 'pto_hours', 'swag'], 
        weights=[70, 20, 10]
    )[0]
    
    prize_value = prize_options[prize_type]
    
    return {
        'success': True,
        'category': 'A',
        'guaranteed_win': True,
        'prize_type': prize_type,
        'prize_value': prize_value,
        'tier': tier,
        'game_data': {
            'game_type': game_type,
            'outcome': 'win',
            'tier_bonus': tier != 'Bronze'
        }
    }

def play_category_b_game(cursor, employee_id, game_type, bet_amount):
    """Play Category B game (token gambling)"""
    
    # Check token balance
    cursor.execute("SELECT token_balance FROM employee_tokens WHERE employee_id = ?", (employee_id,))
    result = cursor.fetchone()
    
    if not result or result[0] < bet_amount:
        return {'error': 'Insufficient tokens'}
    
    # Get employee tier for win odds
    cursor.execute("SELECT role FROM employees WHERE employee_id = ?", (employee_id,))
    employee = cursor.fetchone()
    # Map actual roles to tier levels
    role_to_tier = {
        'laborer': 'Bronze',
        'driver': 'Silver',
        'supervisor': 'Gold',
        'master': 'Platinum'
    }
    
    role = employee[0] if employee else 'laborer'
    tier = role_to_tier.get(role, 'Bronze')
    
    # Tier-based win odds
    win_odds = {
        'Bronze': 0.25,     # 25% win rate
        'Silver': 0.30,     # 30% win rate
        'Gold': 0.35,       # 35% win rate
        'Platinum': 0.40    # 40% win rate
    }
    
    base_odds = win_odds.get(tier, 0.25)
    
    # Debug logging to check odds
    import logging
    logging.info(f"Category B game - Employee: {employee_id}, Role: {role}, Tier: {tier}, Odds: {base_odds}")
    
    # Determine win/loss
    won = random.random() < base_odds
    
    if won:
        # Determine prize type - enhanced with PTO and swag options
        prize_roll = random.random()
        
        # Enhanced prize probabilities with end-of-month jackpot
        jackpot_multiplier = 1.0
        if is_end_of_month() and check_monthly_jackpot_eligibility(cursor, employee_id):
            jackpot_multiplier = 3.0  # 3x chance for special prizes on last day
        
        special_chance = 0.05 * jackpot_multiplier
        if prize_roll < special_chance:  # Enhanced chance for special prizes
            # Check if special prizes are available this month
            cursor.execute("""
                SELECT prize_type, monthly_limit, monthly_used 
                FROM global_prize_pools 
                WHERE prize_type IN ('pto_4_hours', 'vacation_day') 
                AND monthly_used < monthly_limit
                ORDER BY RANDOM() LIMIT 1
            """)
            special_prize = cursor.fetchone()
            
            if special_prize:
                prize_type, monthly_limit, monthly_used = special_prize
                # Award special prize
                cursor.execute("""
                    UPDATE global_prize_pools 
                    SET monthly_used = monthly_used + 1 
                    WHERE prize_type = ?
                """, (prize_type,))
                
                # Still deduct the bet
                cursor.execute("""
                    UPDATE employee_tokens 
                    SET token_balance = token_balance - ?,
                        total_tokens_spent = total_tokens_spent + ?
                    WHERE employee_id = ?
                """, (bet_amount, bet_amount, employee_id))
                
                prize_descriptions = {
                    'pto_4_hours': '4 Hours PTO',
                    'vacation_day': '1 Vacation Day'
                }
                
                return {
                    'success': True,
                    'category': 'B',
                    'won': True,
                    'prize_type': 'special',
                    'prize_description': prize_descriptions.get(prize_type, prize_type),
                    'bet_amount': bet_amount,
                    'net_change': -bet_amount,
                    'tier': tier,
                    'game_data': {
                        'game_type': game_type,
                        'outcome': 'special_win',
                        'special_prize': prize_type,
                        'odds': base_odds
                    }
                }
        
        # Regular token multiplier win
        multiplier = random.uniform(2.0, 5.0)
        win_amount = int(bet_amount * multiplier)
        
        # Update token balance (add winnings, subtract bet)
        net_change = win_amount - bet_amount
        cursor.execute("""
            UPDATE employee_tokens 
            SET token_balance = token_balance + ?
            WHERE employee_id = ?
        """, (net_change, employee_id))
        
        return {
            'success': True,
            'category': 'B',
            'won': True,
            'prize_type': 'tokens',
            'bet_amount': bet_amount,
            'win_amount': win_amount,
            'net_change': net_change,
            'multiplier': round(multiplier, 2),
            'tier': tier,
            'role': role,
            'game_data': {
                'game_type': game_type,
                'outcome': 'win',
                'odds': base_odds
            }
        }
    else:
        # Loss - deduct bet amount
        cursor.execute("""
            UPDATE employee_tokens 
            SET token_balance = token_balance - ?,
                total_tokens_spent = total_tokens_spent + ?
            WHERE employee_id = ?
        """, (bet_amount, bet_amount, employee_id))
        
        return {
            'success': True,
            'category': 'B',
            'won': False,
            'bet_amount': bet_amount,
            'win_amount': 0,
            'net_change': -bet_amount,
            'tier': tier,
            'role': role,
            'game_data': {
                'game_type': game_type,
                'outcome': 'loss',
                'odds': base_odds
            }
        }

@dual_game_bp.route('/config')
def get_config():
    """Get dual game configuration"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT config_category, config_key, config_value FROM admin_game_config")
        configs = cursor.fetchall()
        conn.close()
        
        config_dict = {}
        for category, key, value in configs:
            if category not in config_dict:
                config_dict[category] = {}
            try:
                config_dict[category][key] = json.loads(value)
            except:
                config_dict[category][key] = value
        
        return jsonify(config_dict)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dual_game_bp.route('/jackpot/status')
def jackpot_status():
    """Get monthly jackpot status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if it's end of month
        end_of_month = is_end_of_month()
        
        # Get available jackpot prizes
        cursor.execute("""
            SELECT prize_type, monthly_limit, monthly_used, 
                   (monthly_limit - monthly_used) as remaining
            FROM global_prize_pools 
            WHERE prize_type LIKE '%jackpot%' OR prize_type IN ('vacation_day', 'pto_4_hours')
        """)
        
        prizes = []
        for row in cursor.fetchall():
            prizes.append({
                'prize_type': row[0],
                'monthly_limit': row[1],
                'monthly_used': row[2],
                'remaining': row[3]
            })
        
        conn.close()
        
        return jsonify({
            'end_of_month': end_of_month,
            'jackpot_multiplier': 3.0 if end_of_month else 1.0,
            'available_prizes': prizes,
            'eligibility_requirement': '5 games played this month',
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@dual_game_bp.route('/jackpot/eligible/<employee_id>')
def check_jackpot_eligibility(employee_id):
    """Check if employee is eligible for monthly jackpot"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        eligible = check_monthly_jackpot_eligibility(cursor, employee_id)
        
        # Get monthly activity count
        cursor.execute("""
            SELECT COUNT(*) FROM token_transactions 
            WHERE employee_id = ? 
            AND strftime('%Y-%m', transaction_date) = strftime('%Y-%m', 'now')
            AND transaction_type IN ('win', 'spend')
        """, (employee_id,))
        
        monthly_games = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'employee_id': employee_id,
            'eligible': eligible,
            'monthly_games_played': monthly_games,
            'required_games': 5,
            'end_of_month_bonus': is_end_of_month()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500