#!/usr/bin/env python3
"""
Simple dual game system API routes
Integrated with existing Flask app structure
"""

from flask import Blueprint, request, jsonify, session
import sqlite3
import json
from datetime import datetime, date
import random
import logging

# Create blueprint
dual_game_bp = Blueprint('dual_game', __name__, url_prefix='/api/dual_game')

def get_db_connection():
    """Get database connection using existing pattern"""
    return sqlite3.connect('/home/tim/incentDev/incentive.db')

@dual_game_bp.route('/status')
def status():
    """Check dual game system status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('employee_tokens', 'dual_game_config')
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Get basic stats
        cursor.execute("SELECT COUNT(*) FROM employee_tokens")
        token_accounts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM dual_game_config")
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

@dual_game_bp.route('/tokens/<int:employee_id>')
def get_tokens(employee_id):
    """Get employee token balance"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT token_balance, total_earned, total_spent 
            FROM employee_tokens 
            WHERE employee_id = ?
        """, (employee_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'employee_id': employee_id,
                'token_balance': result[0],
                'total_earned': result[1],
                'total_spent': result[2]
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
        cursor.execute("SELECT role FROM employees WHERE employee_id = ?", (employee_id,))
        employee = cursor.fetchone()
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Simple exchange rates by role
        exchange_rates = {
            'Bronze': 10,  # 10 points = 1 token
            'Silver': 8,   # 8 points = 1 token
            'Gold': 6,     # 6 points = 1 token
            'Platinum': 5  # 5 points = 1 token
        }
        
        rate = exchange_rates.get(employee[0], 10)
        tokens_to_add = points // rate
        
        if tokens_to_add <= 0:
            return jsonify({'error': f'Not enough points for exchange (need at least {rate})'}), 400
        
        # Update token balance
        cursor.execute("""
            UPDATE employee_tokens 
            SET token_balance = token_balance + ?,
                total_earned = total_earned + ?,
                last_exchange_date = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE employee_id = ?
        """, (tokens_to_add, tokens_to_add, employee_id))
        
        # Record exchange
        cursor.execute("""
            INSERT INTO token_exchanges 
            (employee_id, exchange_type, points_amount, tokens_amount, exchange_rate)
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
        
        # Record game play
        cursor.execute("""
            INSERT INTO dual_game_history 
            (employee_id, game_type, category, bet_amount, win_amount, prize_type, prize_value, game_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (employee_id, game_type, category, bet_amount, 
              result.get('win_amount', 0), result.get('prize_type'),
              result.get('prize_value'), json.dumps(result.get('game_data', {}))))
        
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
    
    tier = employee[0] if employee else 'Bronze'
    
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
    tier = employee[0] if employee else 'Bronze'
    
    # Tier-based win odds
    win_odds = {
        'Bronze': 0.25,     # 25% win rate
        'Silver': 0.30,     # 30% win rate
        'Gold': 0.35,       # 35% win rate
        'Platinum': 0.40    # 40% win rate
    }
    
    base_odds = win_odds.get(tier, 0.25)
    
    # Determine win/loss
    won = random.random() < base_odds
    
    if won:
        # Calculate winnings (2x to 5x bet)
        multiplier = random.uniform(2.0, 5.0)
        win_amount = int(bet_amount * multiplier)
        
        # Update token balance (add winnings, subtract bet)
        net_change = win_amount - bet_amount
        cursor.execute("""
            UPDATE employee_tokens 
            SET token_balance = token_balance + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE employee_id = ?
        """, (net_change, employee_id))
        
        return {
            'success': True,
            'category': 'B',
            'won': True,
            'bet_amount': bet_amount,
            'win_amount': win_amount,
            'net_change': net_change,
            'multiplier': round(multiplier, 2),
            'tier': tier,
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
                total_spent = total_spent + ?,
                updated_at = CURRENT_TIMESTAMP
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
        
        cursor.execute("SELECT category, setting_key, setting_value FROM dual_game_config")
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