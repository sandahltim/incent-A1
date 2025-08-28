# services/analytics.py
# Analytics and reporting service

import logging
from datetime import datetime, timedelta
from incentive_service import DatabaseConnection


def get_payout_analytics(days=30):
    """Get comprehensive payout analytics."""
    try:
        with DatabaseConnection() as conn:
            # Get payout summary
            payout_summary = conn.execute("""
                SELECT 
                    COUNT(*) as total_payouts,
                    SUM(dollar_value) as total_payout_value,
                    AVG(dollar_value) as avg_payout_value,
                    game_type,
                    prize_type
                FROM mini_game_payouts 
                WHERE payout_date >= date('now', '-{} days')
                GROUP BY game_type, prize_type
                ORDER BY total_payout_value DESC
            """.format(days)).fetchall()
            
            # Get daily trends
            daily_trends = conn.execute("""
                SELECT 
                    DATE(payout_date) as payout_date,
                    COUNT(*) as daily_payouts,
                    SUM(dollar_value) as daily_value,
                    COUNT(DISTINCT employee_id) as unique_players
                FROM mini_game_payouts 
                WHERE payout_date >= date('now', '-{} days')
                GROUP BY DATE(payout_date)
                ORDER BY payout_date
            """.format(days)).fetchall()
            
            # Get win rates by game type
            win_rates = conn.execute("""
                SELECT 
                    mg.game_type,
                    COUNT(*) as total_games,
                    COUNT(mp.id) as winning_games,
                    ROUND(CAST(COUNT(mp.id) AS FLOAT) / COUNT(*) * 100, 2) as win_rate_percent
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                WHERE mg.played_date >= date('now', '-{} days')
                GROUP BY mg.game_type
                ORDER BY win_rate_percent DESC
            """.format(days)).fetchall()
            
            return {
                "success": True,
                "analytics": {
                    "payout_summary": [dict(row) for row in payout_summary],
                    "daily_trends": [dict(row) for row in daily_trends],
                    "win_rates": [dict(row) for row in win_rates],
                    "period_days": days
                }
            }
            
    except Exception as e:
        logging.error(f"Error getting payout analytics: {str(e)}")
        return {"success": False, "message": "Failed to get analytics"}


def get_payout_rate_analysis(days=30):
    """Get payout rate analysis for odds adjustment."""
    try:
        with DatabaseConnection() as conn:
            payout_analysis = conn.execute("""
                SELECT 
                    mg.game_type,
                    COUNT(*) as total_games,
                    COALESCE(SUM(mp.dollar_value), 0) as total_payout,
                    go.win_probability as current_win_prob,
                    go.jackpot_probability as current_jackpot_prob
                FROM mini_games mg
                LEFT JOIN mini_game_payouts mp ON mg.id = mp.game_id
                LEFT JOIN game_odds go ON mg.game_type = go.game_type
                WHERE mg.played_date >= date('now', '-{} days')
                GROUP BY mg.game_type, go.win_probability, go.jackpot_probability
            """.format(days)).fetchall()
            
            return [dict(row) for row in payout_analysis]
            
    except Exception as e:
        logging.error(f"Error getting payout rate analysis: {str(e)}")
        return []


def get_system_trends():
    """Get system-wide trends and statistics."""
    try:
        with DatabaseConnection() as conn:
            # Daily activity trends
            activity_trends = conn.execute("""
                SELECT 
                    DATE(created_at) as activity_date,
                    COUNT(*) as total_activities,
                    COUNT(DISTINCT employee_id) as unique_employees
                FROM history 
                WHERE created_at >= date('now', '-30 days')
                GROUP BY DATE(created_at)
                ORDER BY activity_date
            """).fetchall()
            
            # Points distribution
            points_distribution = conn.execute("""
                SELECT 
                    CASE 
                        WHEN score >= 100 THEN '100+'
                        WHEN score >= 50 THEN '50-99'
                        WHEN score >= 25 THEN '25-49'
                        WHEN score >= 10 THEN '10-24'
                        ELSE '0-9'
                    END as score_range,
                    COUNT(*) as employee_count
                FROM employees 
                WHERE active = 1
                GROUP BY 
                    CASE 
                        WHEN score >= 100 THEN '100+'
                        WHEN score >= 50 THEN '50-99'
                        WHEN score >= 25 THEN '25-49'
                        WHEN score >= 10 THEN '10-24'
                        ELSE '0-9'
                    END
                ORDER BY MIN(score) DESC
            """).fetchall()
            
            # Top performers
            top_performers = conn.execute("""
                SELECT employee_id, name, score, role
                FROM employees 
                WHERE active = 1
                ORDER BY score DESC
                LIMIT 10
            """).fetchall()
            
            return {
                "success": True,
                "trends": {
                    "activity_trends": [dict(row) for row in activity_trends],
                    "points_distribution": [dict(row) for row in points_distribution],
                    "top_performers": [dict(row) for row in top_performers]
                }
            }
            
    except Exception as e:
        logging.error(f"Error getting system trends: {str(e)}")
        return {"success": False, "message": "Failed to get system trends"}


def adjust_odds_by_payout_rate(target_rate=0.15, adjustment_factor=0.1, days=30):
    """Automatically adjust game odds based on payout analysis."""
    try:
        payout_analysis = get_payout_rate_analysis(days)
        adjustments_made = []
        
        with DatabaseConnection() as conn:
            for analysis in payout_analysis:
                game_type = analysis['game_type']
                total_games = analysis['total_games']
                total_payout = analysis['total_payout'] or 0
                current_win_prob = analysis['current_win_prob']
                current_jackpot_prob = analysis['current_jackpot_prob']
                
                if total_games == 0:
                    continue
                    
                # Calculate current payout rate
                # Assume average game cost (this should be configurable)
                assumed_game_cost = 1.0
                current_payout_rate = total_payout / (total_games * assumed_game_cost)
                
                # Determine if adjustment is needed
                if current_payout_rate > target_rate * 1.1:  # 10% tolerance
                    # Reduce win probability
                    new_win_prob = max(0.01, current_win_prob * (1 - adjustment_factor))
                    new_jackpot_prob = max(0.001, current_jackpot_prob * (1 - adjustment_factor))
                    action = "REDUCED"
                elif current_payout_rate < target_rate * 0.9:  # 10% tolerance
                    # Increase win probability
                    new_win_prob = min(0.99, current_win_prob * (1 + adjustment_factor))
                    new_jackpot_prob = min(0.1, current_jackpot_prob * (1 + adjustment_factor))
                    action = "INCREASED"
                else:
                    continue  # No adjustment needed
                
                # Update odds in database
                conn.execute("""
                    UPDATE game_odds 
                    SET win_probability = ?, 
                        jackpot_probability = ?,
                        last_adjusted = CURRENT_TIMESTAMP
                    WHERE game_type = ?
                """, (new_win_prob, new_jackpot_prob, game_type))
                
                adjustments_made.append({
                    "game_type": game_type,
                    "action": action,
                    "old_win_prob": current_win_prob,
                    "new_win_prob": new_win_prob,
                    "old_jackpot_prob": current_jackpot_prob,
                    "new_jackpot_prob": new_jackpot_prob,
                    "current_payout_rate": round(current_payout_rate, 4),
                    "target_rate": target_rate
                })
            
            conn.commit()
            
        return {
            "success": True,
            "adjustments": adjustments_made,
            "message": f"Made {len(adjustments_made)} automatic adjustments"
        }
        
    except Exception as e:
        logging.error(f"Error adjusting odds by payout: {str(e)}")
        return {"success": False, "message": f"Failed to adjust odds: {str(e)}"}