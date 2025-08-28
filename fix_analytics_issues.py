#!/usr/bin/env python3
"""
Fix Critical Issues Found in Analytics System Debug
"""

import sqlite3
import json
from datetime import datetime
from config import Config

def fix_foreign_key_violations():
    """Fix foreign key violations by removing orphaned records"""
    print("Fixing foreign key violations...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Remove orphaned vote records
        cursor.execute("""
            DELETE FROM votes 
            WHERE recipient_id NOT IN (SELECT employee_id FROM employees)
        """)
        deleted_votes = cursor.rowcount
        print(f"  Removed {deleted_votes} orphaned vote records")
        
        # Remove orphaned voting_results records
        cursor.execute("""
            DELETE FROM voting_results 
            WHERE employee_id NOT IN (SELECT employee_id FROM employees)
        """)
        deleted_results = cursor.rowcount
        print(f"  Removed {deleted_results} orphaned voting_results records")
        
        # Remove orphaned score_history records
        cursor.execute("""
            DELETE FROM score_history 
            WHERE employee_id NOT IN (SELECT employee_id FROM employees)
        """)
        deleted_history = cursor.rowcount
        print(f"  Removed {deleted_history} orphaned score_history records")
        
        # Remove orphaned vote_participants records
        cursor.execute("""
            DELETE FROM vote_participants 
            WHERE session_id NOT IN (SELECT session_id FROM voting_sessions)
        """)
        deleted_participants = cursor.rowcount
        print(f"  Removed {deleted_participants} orphaned vote_participants records")
        
        conn.commit()
        print("✅ Foreign key violations fixed")
        
    except Exception as e:
        print(f"❌ Error fixing foreign key violations: {e}")
        conn.rollback()
    finally:
        conn.close()

def fix_wheel_game_probabilities():
    """Fix the wheel game probability issue (total > 1.0)"""
    print("Fixing wheel game probabilities...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Get current wheel probabilities
        cursor.execute("SELECT id, probability, prize_description FROM game_prizes WHERE game_type='wheel'")
        prizes = cursor.fetchall()
        
        total_prob = sum(p[1] for p in prizes)
        print(f"  Current total probability: {total_prob}")
        
        # Normalize probabilities to sum to ~0.5 (reasonable for games)
        target_total = 0.5
        scale_factor = target_total / total_prob
        
        for prize_id, prob, desc in prizes:
            new_prob = prob * scale_factor
            cursor.execute(
                "UPDATE game_prizes SET probability = ? WHERE id = ?",
                (new_prob, prize_id)
            )
            print(f"  Updated {desc}: {prob:.3f} -> {new_prob:.3f}")
        
        conn.commit()
        print("✅ Wheel game probabilities normalized")
        
    except Exception as e:
        print(f"❌ Error fixing wheel probabilities: {e}")
        conn.rollback()
    finally:
        conn.close()

def fix_dollar_value_calculations():
    """Fix the dollar value calculation issue in payouts"""
    print("Fixing dollar value calculations...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Get payouts with zero dollar values
        cursor.execute("""
            SELECT mp.id, mp.game_type, mp.prize_type, mp.prize_amount, 
                   gp.dollar_value as correct_dollar_value
            FROM mini_game_payouts mp
            LEFT JOIN game_prizes gp ON mp.game_type = gp.game_type 
                                     AND mp.prize_type = gp.prize_type
                                     AND mp.prize_amount = gp.prize_amount
            WHERE mp.dollar_value = 0.0 OR mp.dollar_value IS NULL
        """)
        
        zero_value_payouts = cursor.fetchall()
        
        for payout in zero_value_payouts:
            correct_value = payout['correct_dollar_value'] or 0.0
            
            # Special handling for points prizes - use prize_values table
            if payout['prize_type'] == 'points':
                cursor.execute("""
                    SELECT base_dollar_value, point_to_dollar_rate 
                    FROM prize_values 
                    WHERE prize_type = 'points'
                """)
                points_config = cursor.fetchone()
                
                if points_config and points_config['point_to_dollar_rate']:
                    correct_value = payout['prize_amount'] * points_config['point_to_dollar_rate']
                
            # Special handling for mini_game prizes
            elif payout['prize_type'] == 'mini_game':
                cursor.execute("""
                    SELECT base_dollar_value 
                    FROM prize_values 
                    WHERE prize_type = 'mini_game'
                """)
                minigame_config = cursor.fetchone()
                
                if minigame_config:
                    correct_value = minigame_config['base_dollar_value']
            
            # Update the payout record
            cursor.execute("""
                UPDATE mini_game_payouts 
                SET dollar_value = ? 
                WHERE id = ?
            """, (correct_value, payout['id']))
            
            print(f"  Updated payout {payout['id']}: {payout['prize_type']} ${correct_value:.2f}")
        
        conn.commit()
        print(f"✅ Fixed {len(zero_value_payouts)} payout dollar values")
        
    except Exception as e:
        print(f"❌ Error fixing dollar values: {e}")
        conn.rollback()
    finally:
        conn.close()

def validate_analytics_system():
    """Run validation checks after fixes"""
    print("Validating analytics system...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Check foreign key violations
        cursor.execute("PRAGMA foreign_key_check")
        violations = cursor.fetchall()
        if violations:
            print(f"  ⚠️  Still {len(violations)} foreign key violations")
        else:
            print("  ✅ No foreign key violations")
        
        # Check probability totals
        cursor.execute("""
            SELECT game_type, SUM(probability) as total_prob 
            FROM game_prizes 
            GROUP BY game_type
        """)
        prob_totals = cursor.fetchall()
        
        for game in prob_totals:
            if game['total_prob'] > 1.1:
                print(f"  ⚠️  {game['game_type']} still has high probability: {game['total_prob']:.3f}")
            else:
                print(f"  ✅ {game['game_type']} probability: {game['total_prob']:.3f}")
        
        # Check dollar values
        cursor.execute("""
            SELECT COUNT(*) as zero_count 
            FROM mini_game_payouts 
            WHERE dollar_value = 0.0 AND prize_type != 'bonus'
        """)
        zero_count = cursor.fetchone()['zero_count']
        
        if zero_count > 0:
            print(f"  ⚠️  Still {zero_count} payouts with zero dollar value")
        else:
            print("  ✅ All payouts have proper dollar values")
        
        # Test analytics query
        cursor.execute("""
            SELECT 
                COUNT(*) as total_payouts,
                SUM(dollar_value) as total_value,
                AVG(dollar_value) as avg_value
            FROM mini_game_payouts
        """)
        analytics = cursor.fetchone()
        
        print(f"  📊 Analytics: {analytics['total_payouts']} payouts, ${analytics['total_value']:.2f} total, ${analytics['avg_value']:.2f} average")
        
    except Exception as e:
        print(f"❌ Error validating system: {e}")
    finally:
        conn.close()

def create_system_analytics_entry():
    """Create a sample system analytics entry for testing"""
    print("Creating system analytics entry...")
    
    conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Calculate current metrics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_games,
                COUNT(mp.id) as winning_games,
                SUM(COALESCE(mp.dollar_value, 0)) as total_payout,
                AVG(COALESCE(mp.dollar_value, 0)) as avg_payout,
                COUNT(DISTINCT mg.employee_id) as active_players
            FROM mini_games mg
            LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
            WHERE mg.played_date >= date('now', '-30 days')
        """)
        
        metrics = cursor.fetchone()
        
        win_rate = (metrics['winning_games'] / metrics['total_games'] * 100) if metrics['total_games'] > 0 else 0
        
        # Get voting metrics
        cursor.execute("""
            SELECT COUNT(*) as total_votes 
            FROM votes 
            WHERE vote_date >= date('now', '-30 days')
        """)
        vote_metrics = cursor.fetchone()
        
        # Create analytics entry
        trend_data = {
            "period": "30_days",
            "games_breakdown": {
                "total": metrics['total_games'],
                "winning": metrics['winning_games'],
                "win_rate": round(win_rate, 2)
            },
            "payout_breakdown": {
                "total_value": float(metrics['total_payout']),
                "average": float(metrics['avg_payout'])
            },
            "engagement": {
                "active_players": metrics['active_players'],
                "votes_cast": vote_metrics['total_votes']
            }
        }
        
        cursor.execute("""
            INSERT OR REPLACE INTO system_analytics 
            (period_start, period_end, total_points_awarded, total_games_played, 
             total_payout_value, total_votes_cast, active_employees, win_rate, 
             average_payout, trend_analysis)
            VALUES (date('now', '-30 days'), date('now'), ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            0,  # points (calculated separately)
            metrics['total_games'],
            metrics['total_payout'],
            vote_metrics['total_votes'],
            metrics['active_players'],
            win_rate,
            metrics['avg_payout'],
            json.dumps(trend_data)
        ))
        
        conn.commit()
        print("✅ System analytics entry created")
        
    except Exception as e:
        print(f"❌ Error creating analytics entry: {e}")
        conn.rollback()
    finally:
        conn.close()

def main():
    """Run all fixes"""
    print("🔧 ANALYTICS SYSTEM REPAIR UTILITY")
    print("=" * 50)
    
    fix_foreign_key_violations()
    print()
    
    fix_wheel_game_probabilities()
    print()
    
    fix_dollar_value_calculations()
    print()
    
    create_system_analytics_entry()
    print()
    
    validate_analytics_system()
    print()
    
    print("🏁 Repair complete!")

if __name__ == "__main__":
    main()