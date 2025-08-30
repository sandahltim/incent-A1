#!/usr/bin/env python3
"""
Dual Game System Frontend Routes
Flask routes for serving the dual game UI templates
Integrates with existing dual_game_simple.py API
"""

from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from flask_wtf.csrf import validate_csrf
import sqlite3
import json
from datetime import datetime
import logging

# Create blueprint for frontend routes
dual_game_frontend = Blueprint('dual_game_frontend', __name__, url_prefix='/dual-games')

def get_db_connection():
    """Get database connection using existing pattern"""
    return sqlite3.connect('/home/tim/incentDev/incentive.db')

def get_employee_data(employee_id):
    """Get employee data for dual game system"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get basic employee info
        cursor.execute("""
            SELECT employee_id, name, role, tier, points_balance
            FROM employees 
            WHERE employee_id = ?
        """, (employee_id,))
        
        employee = cursor.fetchone()
        if not employee:
            return None
            
        # Get token balance
        cursor.execute("""
            SELECT token_balance FROM employee_tokens 
            WHERE employee_id = ?
        """, (employee_id,))
        
        token_row = cursor.fetchone()
        token_balance = token_row[0] if token_row else 0
        
        # Get exchange rate based on tier
        exchange_rates = {
            'bronze': 10,
            'silver': 8, 
            'gold': 6,
            'platinum': 5
        }
        
        # Get win odds based on tier
        win_odds = {
            'bronze': 25,
            'silver': 30,
            'gold': 35,
            'platinum': 40
        }
        
        tier = employee[3].lower() if employee[3] else 'bronze'
        
        conn.close()
        
        return {
            'employee_id': employee[0],
            'name': employee[1],
            'role': employee[2],
            'tier': tier,
            'points_balance': employee[4],
            'token_balance': token_balance,
            'exchange_rate': exchange_rates.get(tier, 10),
            'win_odds': win_odds.get(tier, 25)
        }
        
    except Exception as e:
        logging.error(f"Error getting employee data: {e}")
        return None

@dual_game_frontend.route('/')
def dashboard():
    """Main dual game dashboard"""
    employee_id = session.get('employee_id')
    if not employee_id:
        flash('Please select an employee first', 'warning')
        return redirect(url_for('employee_portal'))
    
    employee_data = get_employee_data(employee_id)
    if not employee_data:
        flash('Employee not found', 'error')
        return redirect(url_for('employee_portal'))
    
    try:
        # Get system status
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if dual game system is active
        cursor.execute("""
            SELECT value FROM settings 
            WHERE key = 'dual_game_status'
        """)
        status_row = cursor.fetchone()
        system_status = status_row[0] if status_row else 'active'
        
        conn.close()
        
        if system_status != 'active':
            flash('Dual game system is currently under maintenance', 'warning')
            return redirect(url_for('show_incentive'))
        
        return render_template('dual_game_dashboard.html',
                             employee_id=employee_id,
                             employee_data=employee_data,
                             page_title='Dual Casino Games')
                             
    except Exception as e:
        logging.error(f"Error loading dual game dashboard: {e}")
        flash('Error loading game dashboard', 'error')
        return redirect(url_for('show_incentive'))

@dual_game_frontend.route('/category-a')
def category_a_games():
    """Category A (guaranteed win) games interface"""
    employee_id = session.get('employee_id')
    if not employee_id:
        flash('Please select an employee first', 'warning')
        return redirect(url_for('employee_portal'))
    
    employee_data = get_employee_data(employee_id)
    if not employee_data:
        flash('Employee not found', 'error')
        return redirect(url_for('employee_portal'))
    
    try:
        # Get available Category A games for this employee
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ag.game_id, ag.employee_id, ag.awarded_date, ag.expires_date,
                   mg.name, mg.description, ag.prize_type, ag.prize_value, ag.prize_details
            FROM awarded_games ag
            JOIN mini_games mg ON ag.game_id = mg.id
            WHERE ag.employee_id = ? 
            AND ag.claimed = 0 
            AND ag.expires_date > datetime('now')
            AND mg.game_category = 'guaranteed'
            ORDER BY ag.awarded_date DESC
        """, (employee_id,))
        
        available_games = []
        for row in cursor.fetchall():
            available_games.append({
                'id': row[0],
                'employee_id': row[1],
                'awarded_date': row[2],
                'expires_date': row[3],
                'name': row[4],
                'description': row[5],
                'prize_type': row[6],
                'prize_value': row[7],
                'prize_details': row[8]
            })
        
        conn.close()
        
        return render_template('category_a_games.html',
                             employee_id=employee_id,
                             employee_data=employee_data,
                             available_games=available_games,
                             page_title='Category A - Guaranteed Wins')
                             
    except Exception as e:
        logging.error(f"Error loading Category A games: {e}")
        flash('Error loading Category A games', 'error')
        return redirect(url_for('dual_game_frontend.dashboard'))

@dual_game_frontend.route('/category-b')
def category_b_games():
    """Category B (token gambling) games interface"""
    employee_id = session.get('employee_id')
    if not employee_id:
        flash('Please select an employee first', 'warning')
        return redirect(url_for('employee_portal'))
    
    employee_data = get_employee_data(employee_id)
    if not employee_data:
        flash('Employee not found', 'error')
        return redirect(url_for('employee_portal'))
    
    try:
        # Get Category B game configuration
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name, description, game_category, guaranteed_win, token_cost
            FROM mini_games 
            WHERE game_category = 'gambling'
            AND active = 1
            ORDER BY name
        """)
        
        available_games = []
        for row in cursor.fetchall():
            available_games.append({
                'name': row[0],
                'description': row[1],
                'category': row[2],
                'guaranteed_win': row[3],
                'min_token_cost': row[4] or 5
            })
        
        conn.close()
        
        return render_template('category_b_games.html',
                             employee_id=employee_id,
                             employee_data=employee_data,
                             available_games=available_games,
                             page_title='Category B - Token Casino')
                             
    except Exception as e:
        logging.error(f"Error loading Category B games: {e}")
        flash('Error loading Category B games', 'error')
        return redirect(url_for('dual_game_frontend.dashboard'))

@dual_game_frontend.route('/admin')
def admin_dashboard():
    """Admin dashboard for dual game management"""
    if not session.get('admin_id'):
        flash('Admin access required', 'error')
        return redirect(url_for('admin'))
    
    try:
        # Get system metrics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get basic stats
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT et.employee_id) as active_players,
                COALESCE(SUM(et.token_balance), 0) as total_tokens,
                COUNT(CASE WHEN gp.play_date > date('now', '-1 day') THEN 1 END) as games_today
            FROM employee_tokens et
            LEFT JOIN game_plays gp ON et.employee_id = gp.employee_id
        """)
        
        stats_row = cursor.fetchone()
        system_stats = {
            'active_players': stats_row[0] if stats_row else 0,
            'total_tokens': stats_row[1] if stats_row else 0,
            'games_today': stats_row[2] if stats_row else 0
        }
        
        # Get Category A wins today
        cursor.execute("""
            SELECT COUNT(*) FROM game_plays 
            WHERE game_type = 'category_a' 
            AND play_date > date('now', '-1 day')
            AND outcome = 'win'
        """)
        category_a_wins = cursor.fetchone()[0]
        
        # Get Category B wins today  
        cursor.execute("""
            SELECT COUNT(*) FROM game_plays 
            WHERE game_type = 'category_b' 
            AND play_date > date('now', '-1 day')
            AND outcome = 'win'
        """)
        category_b_wins = cursor.fetchone()[0]
        
        system_stats['category_a_wins'] = category_a_wins
        system_stats['category_b_wins'] = category_b_wins
        
        # Get recent activity
        cursor.execute("""
            SELECT gp.employee_id, gp.game_type, gp.outcome, gp.points_change, 
                   gp.play_date, e.name
            FROM game_plays gp
            LEFT JOIN employees e ON gp.employee_id = e.employee_id
            WHERE gp.play_date > datetime('now', '-1 day')
            ORDER BY gp.play_date DESC
            LIMIT 20
        """)
        
        recent_activity = []
        for row in cursor.fetchall():
            recent_activity.append({
                'employee_id': row[0],
                'employee_name': row[5] or 'Unknown',
                'game_type': row[1],
                'outcome': row[2],
                'points_change': row[3],
                'play_date': row[4]
            })
        
        conn.close()
        
        return render_template('admin_dual_game_dashboard.html',
                             system_stats=system_stats,
                             recent_activity=recent_activity,
                             page_title='Dual Game Administration')
                             
    except Exception as e:
        logging.error(f"Error loading admin dashboard: {e}")
        flash('Error loading admin dashboard', 'error')
        return redirect(url_for('admin'))

@dual_game_frontend.route('/api/employee-stats/<employee_id>')
def get_employee_stats(employee_id):
    """API endpoint to get employee statistics for dashboard"""
    try:
        employee_data = get_employee_data(employee_id)
        if not employee_data:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Get game statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as games_played,
                COUNT(CASE WHEN outcome = 'win' THEN 1 END) as games_won,
                COALESCE(SUM(CASE WHEN points_change > 0 THEN points_change ELSE 0 END), 0) as total_won,
                COALESCE(SUM(CASE WHEN token_cost > 0 THEN token_cost ELSE 0 END), 0) as tokens_spent
            FROM game_plays 
            WHERE employee_id = ?
        """, (employee_id,))
        
        stats_row = cursor.fetchone()
        games_played = stats_row[0] if stats_row else 0
        games_won = stats_row[1] if stats_row else 0
        total_won = stats_row[2] if stats_row else 0
        tokens_spent = stats_row[3] if stats_row else 0
        
        win_rate = round((games_won / games_played * 100), 1) if games_played > 0 else 0
        
        conn.close()
        
        employee_data.update({
            'games_played': games_played,
            'games_won': games_won,
            'win_rate': f"{win_rate}%",
            'total_won': total_won,
            'tokens_spent': tokens_spent
        })
        
        return jsonify(employee_data)
        
    except Exception as e:
        logging.error(f"Error getting employee stats: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dual_game_frontend.route('/api/game-history/<employee_id>')
def get_game_history(employee_id):
    """API endpoint to get game history for employee"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT game_type, outcome, points_change, token_cost, play_date
            FROM game_plays 
            WHERE employee_id = ?
            ORDER BY play_date DESC
            LIMIT 10
        """, (employee_id,))
        
        history = []
        for row in cursor.fetchall():
            history.append({
                'game_type': row[0],
                'outcome': row[1], 
                'points_change': row[2],
                'token_cost': row[3],
                'play_date': row[4],
                'display_name': row[0].replace('_', ' ').title()
            })
        
        conn.close()
        return jsonify({'history': history})
        
    except Exception as e:
        logging.error(f"Error getting game history: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@dual_game_frontend.route('/api/available-games/<employee_id>')
def get_available_games(employee_id):
    """API endpoint to get available games for employee"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get Category A games
        cursor.execute("""
            SELECT ag.game_id, mg.name, mg.description, ag.prize_type, 
                   ag.prize_value, ag.awarded_date
            FROM awarded_games ag
            JOIN mini_games mg ON ag.game_id = mg.id
            WHERE ag.employee_id = ? 
            AND ag.claimed = 0 
            AND ag.expires_date > datetime('now')
            AND mg.game_category = 'guaranteed'
        """, (employee_id,))
        
        category_a = []
        for row in cursor.fetchall():
            category_a.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'prize_type': row[3],
                'prize_value': row[4],
                'awarded_date': row[5],
                'category': 'Category A'
            })
        
        # Get Category B games (always available)
        cursor.execute("""
            SELECT id, name, description, token_cost
            FROM mini_games 
            WHERE game_category = 'gambling'
            AND active = 1
        """)
        
        category_b = []
        for row in cursor.fetchall():
            category_b.append({
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'min_cost': row[3] or 5,
                'category': 'Category B'
            })
        
        conn.close()
        
        return jsonify({
            'category_a': category_a,
            'category_b': category_b,
            'games': category_a + category_b
        })
        
    except Exception as e:
        logging.error(f"Error getting available games: {e}")
        return jsonify({'error': 'Internal server error'}), 500

# Error handlers for dual game frontend
@dual_game_frontend.errorhandler(404)
def not_found(error):
    """Handle 404 errors in dual game routes"""
    return render_template('error.html', 
                         error_title='Game Not Found',
                         error_message='The requested game or page could not be found.',
                         page_title='Not Found'), 404

@dual_game_frontend.errorhandler(500) 
def internal_error(error):
    """Handle 500 errors in dual game routes"""
    return render_template('error.html',
                         error_title='Game System Error', 
                         error_message='An internal error occurred in the game system.',
                         page_title='System Error'), 500

# Template context processors
@dual_game_frontend.context_processor
def inject_dual_game_context():
    """Inject dual game specific context into templates"""
    return {
        'dual_game_active': True,
        'casino_theme': True
    }

# Before request handler
@dual_game_frontend.before_request
def before_dual_game_request():
    """Check system status before processing dual game requests"""
    # Skip checks for API endpoints
    if request.endpoint and 'api' in request.endpoint:
        return
        
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT value FROM settings 
            WHERE key = 'dual_game_status'
        """)
        
        status_row = cursor.fetchone()
        system_status = status_row[0] if status_row else 'active'
        conn.close()
        
        if system_status == 'maintenance':
            if not session.get('admin_id'):
                flash('Dual game system is under maintenance', 'warning')
                return redirect(url_for('show_incentive'))
        elif system_status == 'disabled':
            flash('Dual game system is currently disabled', 'error')
            return redirect(url_for('show_incentive'))
            
    except Exception as e:
        logging.error(f"Error checking dual game system status: {e}")
        # Don't block access on database errors
        pass