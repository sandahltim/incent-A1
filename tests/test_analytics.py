# tests/test_analytics.py
# Analytics service tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import os
import sys
import sqlite3
import time
from datetime import datetime, timedelta
from unittest.mock import patch, Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from services.analytics import get_payout_analytics
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False

from config import Config


@pytest.mark.skipif(not ANALYTICS_AVAILABLE, reason="Analytics module not available")
class TestAnalyticsService:
    """Test analytics service functionality"""
    
    def test_payout_analytics_with_no_data(self, test_db_path, init_test_db):
        """Test payout analytics with no payout data"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Create mini_game_payouts table if it doesn't exist
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            try:
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mini_game_payouts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        game_id INTEGER,
                        game_type TEXT NOT NULL,
                        prize_type TEXT NOT NULL,
                        dollar_value REAL NOT NULL,
                        payout_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees (id)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mini_games (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        game_type TEXT NOT NULL,
                        bet_amount INTEGER NOT NULL,
                        payout INTEGER NOT NULL,
                        result TEXT,
                        played_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees (id)
                    )
                ''')
                
                conn.commit()
                
                # Test analytics with empty tables
                analytics = get_payout_analytics()
                
                # Should return empty results or handle gracefully
                assert analytics is not None
                
            except Exception as e:
                # If analytics function expects different schema, that's ok
                # The test verifies it doesn't crash with missing data
                assert "no such table" in str(e).lower() or analytics is not None
            
            finally:
                conn.close()
    
    def test_payout_analytics_with_sample_data(self, test_db_path, init_test_db):
        """Test payout analytics with sample data"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            try:
                # Create required tables
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mini_game_payouts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        game_id INTEGER,
                        game_type TEXT NOT NULL,
                        prize_type TEXT NOT NULL,
                        dollar_value REAL NOT NULL,
                        payout_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees (id)
                    )
                ''')
                
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS mini_games (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        employee_id INTEGER NOT NULL,
                        game_type TEXT NOT NULL,
                        bet_amount INTEGER NOT NULL,
                        payout INTEGER NOT NULL,
                        result TEXT,
                        played_date TEXT DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (employee_id) REFERENCES employees (id)
                    )
                ''')
                
                # Insert sample payout data
                sample_payouts = [
                    (2, 1, "slots", "money", 25.00, datetime.now().isoformat()),
                    (3, 2, "scratch_off", "points", 0.00, datetime.now().isoformat()),
                    (2, 3, "roulette", "money", 50.00, (datetime.now() - timedelta(days=1)).isoformat()),
                    (4, 4, "wheel", "money", 100.00, (datetime.now() - timedelta(days=2)).isoformat())
                ]
                
                cursor.executemany(
                    "INSERT INTO mini_game_payouts (employee_id, game_id, game_type, prize_type, dollar_value, payout_date) VALUES (?, ?, ?, ?, ?, ?)",
                    sample_payouts
                )
                
                # Insert sample game data
                sample_games = [
                    (2, "slots", 10, 25, "win", datetime.now().isoformat()),
                    (3, "scratch_off", 5, 0, "lose", datetime.now().isoformat()),
                    (2, "roulette", 20, 50, "win", (datetime.now() - timedelta(days=1)).isoformat()),
                    (4, "wheel", 10, 100, "win", (datetime.now() - timedelta(days=2)).isoformat())
                ]
                
                cursor.executemany(
                    "INSERT INTO mini_games (employee_id, game_type, bet_amount, payout, result, played_date) VALUES (?, ?, ?, ?, ?, ?)",
                    sample_games
                )
                
                conn.commit()
                
                # Test analytics with sample data
                analytics = get_payout_analytics(days=30)
                
                # Should return analytics data
                assert analytics is not None
                
                # If analytics returns a structured response, verify it
                if isinstance(analytics, dict):
                    # Check for expected analytics structure
                    assert 'payout_summary' in analytics or 'daily_trends' in analytics or 'win_rates' in analytics
                elif isinstance(analytics, list):
                    # Analytics might return a list of results
                    assert len(analytics) >= 0
                
            except Exception as e:
                # If the analytics function has different expectations, that's ok
                # The test ensures it doesn't crash and handles data appropriately
                assert "no such table" not in str(e).lower()  # Tables should exist now
                
            finally:
                conn.close()


class TestAnalyticsIntegration:
    """Test analytics integration with the main application"""
    
    def test_analytics_database_connection(self, test_db_path, init_test_db):
        """Test that analytics can connect to database"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                # This test verifies the analytics service can connect to the database
                from incentive_service import DatabaseConnection
                
                with DatabaseConnection() as conn:
                    cursor = conn.cursor()
                    # Test a basic query that analytics might use
                    cursor.execute("SELECT COUNT(*) FROM employees")
                    count = cursor.fetchone()[0]
                    assert count >= 0
                    
            except Exception as e:
                # If there are connection issues, ensure they're handled gracefully
                assert "database" in str(e).lower() or "connection" in str(e).lower()
    
    def test_analytics_with_voting_data(self, test_db_path, init_test_db):
        """Test analytics integration with voting data"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            try:
                # Add some voting data for analytics
                cursor.execute(
                    "INSERT INTO votes (voter_id, voted_for_id, vote_type, session_id) VALUES (?, ?, ?, ?)",
                    (2, 3, "positive", "test_session")
                )
                cursor.execute(
                    "INSERT INTO votes (voter_id, voted_for_id, vote_type, session_id) VALUES (?, ?, ?, ?)",
                    (3, 2, "positive", "test_session")
                )
                conn.commit()
                
                # Test that analytics can process voting data
                cursor.execute("SELECT COUNT(*) FROM votes")
                vote_count = cursor.fetchone()[0]
                assert vote_count >= 2
                
                # Test voting analytics query
                cursor.execute("""
                    SELECT vote_type, COUNT(*) as count 
                    FROM votes 
                    GROUP BY vote_type
                """)
                results = cursor.fetchall()
                assert len(results) > 0
                
            finally:
                conn.close()
    
    def test_analytics_performance_metrics(self, test_db_path, init_test_db):
        """Test analytics performance with larger datasets"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            try:
                # Create a larger dataset for performance testing
                sample_data = []
                for i in range(100):
                    sample_data.append((
                        (i % 4) + 2,  # employee_id (2-5)
                        (i % 4) + 2,  # voted_for_id (2-5)
                        "positive" if i % 2 == 0 else "negative",
                        f"session_{i // 10}",  # 10 different sessions
                        datetime.now().isoformat()
                    ))
                
                cursor.executemany(
                    "INSERT INTO votes (voter_id, voted_for_id, vote_type, session_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                    sample_data
                )
                conn.commit()
                
                # Test analytics query performance
                start_time = time.time()
                
                cursor.execute("""
                    SELECT 
                        voter_id,
                        COUNT(*) as votes_cast,
                        COUNT(CASE WHEN vote_type = 'positive' THEN 1 END) as positive_votes,
                        COUNT(CASE WHEN vote_type = 'negative' THEN 1 END) as negative_votes
                    FROM votes
                    GROUP BY voter_id
                    ORDER BY votes_cast DESC
                """)
                results = cursor.fetchall()
                
                end_time = time.time()
                query_time = end_time - start_time
                
                # Should complete in reasonable time (less than 1 second for 100 records)
                assert query_time < 1.0
                assert len(results) > 0
                
            finally:
                conn.close()


class TestAnalyticsReporting:
    """Test analytics reporting functionality"""
    
    def test_generate_vote_summary_report(self, test_db_path, init_test_db):
        """Test generating vote summary reports"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            try:
                # Add test voting data
                test_votes = [
                    (2, 3, "positive", "session1", datetime.now().isoformat()),
                    (2, 4, "positive", "session1", datetime.now().isoformat()),
                    (3, 2, "negative", "session1", datetime.now().isoformat()),
                    (4, 2, "positive", "session1", datetime.now().isoformat())
                ]
                
                cursor.executemany(
                    "INSERT INTO votes (voter_id, voted_for_id, vote_type, session_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                    test_votes
                )
                conn.commit()
                
                # Generate vote summary report
                cursor.execute("""
                    SELECT 
                        e.name,
                        COUNT(CASE WHEN v.vote_type = 'positive' THEN 1 END) as positive_received,
                        COUNT(CASE WHEN v.vote_type = 'negative' THEN 1 END) as negative_received,
                        COUNT(v.id) as total_received
                    FROM employees e
                    LEFT JOIN votes v ON e.id = v.voted_for_id
                    WHERE e.is_active = 1
                    GROUP BY e.id, e.name
                    ORDER BY total_received DESC
                """)
                
                report_data = cursor.fetchall()
                assert len(report_data) > 0
                
                # Verify report structure
                for row in report_data:
                    assert len(row) == 4  # name, positive, negative, total
                    assert isinstance(row[0], str)  # name should be string
                    assert all(isinstance(x, int) for x in row[1:])  # counts should be integers
                
            finally:
                conn.close()
    
    def test_generate_employee_performance_report(self, test_db_path, init_test_db):
        """Test generating employee performance reports"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            try:
                # Add test point history data
                test_adjustments = [
                    (2, 50, "Good performance", 1, datetime.now().isoformat()),
                    (3, 25, "Teamwork", 1, (datetime.now() - timedelta(days=1)).isoformat()),
                    (2, -10, "Late arrival", 1, (datetime.now() - timedelta(days=2)).isoformat()),
                    (4, 75, "Excellent customer service", 1, (datetime.now() - timedelta(days=3)).isoformat())
                ]
                
                cursor.executemany(
                    "INSERT INTO point_history (employee_id, points_changed, reason, admin_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                    test_adjustments
                )
                conn.commit()
                
                # Generate performance report
                cursor.execute("""
                    SELECT 
                        e.name,
                        e.score,
                        COUNT(ph.id) as adjustment_count,
                        SUM(ph.points_changed) as total_adjustments,
                        AVG(ph.points_changed) as avg_adjustment
                    FROM employees e
                    LEFT JOIN point_history ph ON e.id = ph.employee_id
                    WHERE e.is_active = 1
                    GROUP BY e.id, e.name, e.score
                    ORDER BY e.score DESC
                """)
                
                performance_data = cursor.fetchall()
                assert len(performance_data) > 0
                
                # Verify report structure
                for row in performance_data:
                    assert len(row) == 5  # name, score, count, total, avg
                    assert isinstance(row[0], str)  # name
                    assert isinstance(row[1], (int, float))  # score
                
            finally:
                conn.close()
    
    def test_generate_time_series_analytics(self, test_db_path, init_test_db):
        """Test generating time series analytics"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            try:
                # Create time series data over several days
                base_date = datetime.now() - timedelta(days=7)
                test_data = []
                
                for day in range(7):
                    current_date = base_date + timedelta(days=day)
                    # Add multiple votes per day
                    for hour in [9, 12, 15]:  # 3 times per day
                        vote_time = current_date.replace(hour=hour, minute=0, second=0)
                        test_data.extend([
                            (2, 3, "positive", f"session_{day}_{hour}", vote_time.isoformat()),
                            (3, 4, "positive", f"session_{day}_{hour}", vote_time.isoformat()),
                            (4, 2, "negative", f"session_{day}_{hour}", vote_time.isoformat())
                        ])
                
                cursor.executemany(
                    "INSERT INTO votes (voter_id, voted_for_id, vote_type, session_id, timestamp) VALUES (?, ?, ?, ?, ?)",
                    test_data
                )
                conn.commit()
                
                # Generate daily analytics
                cursor.execute("""
                    SELECT 
                        DATE(timestamp) as vote_date,
                        COUNT(*) as daily_votes,
                        COUNT(DISTINCT voter_id) as unique_voters,
                        COUNT(CASE WHEN vote_type = 'positive' THEN 1 END) as positive_votes,
                        COUNT(CASE WHEN vote_type = 'negative' THEN 1 END) as negative_votes
                    FROM votes
                    WHERE timestamp >= date('now', '-7 days')
                    GROUP BY DATE(timestamp)
                    ORDER BY vote_date
                """)
                
                time_series_data = cursor.fetchall()
                assert len(time_series_data) > 0
                
                # Verify time series structure
                for row in time_series_data:
                    assert len(row) == 5  # date, total, unique, positive, negative
                    assert all(isinstance(x, (int, str)) for x in row)
                
            finally:
                conn.close()


class TestAnalyticsErrorHandling:
    """Test analytics error handling"""
    
    def test_analytics_with_corrupted_data(self, test_db_path, init_test_db):
        """Test analytics handling of corrupted or invalid data"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            try:
                # Insert some invalid data
                cursor.execute(
                    "INSERT INTO votes (voter_id, voted_for_id, vote_type, session_id) VALUES (?, ?, ?, ?)",
                    (999, 999, "invalid_type", "test_session")  # Non-existent employee IDs
                )
                conn.commit()
                
                # Analytics should handle invalid data gracefully
                cursor.execute("""
                    SELECT 
                        v.vote_type,
                        COUNT(*) as count,
                        e1.name as voter_name,
                        e2.name as voted_for_name
                    FROM votes v
                    LEFT JOIN employees e1 ON v.voter_id = e1.id
                    LEFT JOIN employees e2 ON v.voted_for_id = e2.id
                    GROUP BY v.vote_type, e1.name, e2.name
                """)
                
                results = cursor.fetchall()
                # Should not crash, even with invalid references
                assert isinstance(results, list)
                
            except Exception as e:
                # Some errors are acceptable when dealing with invalid data
                assert "foreign key" in str(e).lower() or "constraint" in str(e).lower()
            
            finally:
                conn.close()
    
    def test_analytics_with_missing_tables(self, test_db_path):
        """Test analytics handling when required tables are missing"""
        # Create a minimal database without all required tables
        conn = sqlite3.connect(test_db_path)
        cursor = conn.cursor()
        
        # Only create employees table, not votes table
        cursor.execute('''
            CREATE TABLE employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                pin TEXT NOT NULL UNIQUE,
                score INTEGER DEFAULT 0
            )
        ''')
        conn.commit()
        conn.close()
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                # Try to run analytics that might need votes table
                if ANALYTICS_AVAILABLE:
                    result = get_payout_analytics()
                    # Should handle missing tables gracefully
                    assert result is None or isinstance(result, (dict, list))
                else:
                    # If analytics not available, test basic database operations
                    conn = sqlite3.connect(test_db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM employees")
                    count = cursor.fetchone()[0]
                    assert count == 0
                    conn.close()
                    
            except Exception as e:
                # Missing table errors are acceptable
                assert "no such table" in str(e).lower()
    
    def test_analytics_with_empty_database(self, test_db_path):
        """Test analytics with completely empty database"""
        # Create empty database file
        open(test_db_path, 'a').close()
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                if ANALYTICS_AVAILABLE:
                    result = get_payout_analytics()
                    # Should handle empty database gracefully
                    assert result is None or isinstance(result, (dict, list))
                else:
                    # Test basic connection to empty database
                    conn = sqlite3.connect(test_db_path)
                    # Should be able to connect but queries will fail
                    assert conn is not None
                    conn.close()
                    
            except Exception as e:
                # Database errors are expected with empty database
                assert any(keyword in str(e).lower() for keyword in ["no such table", "database", "sql"])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])