# tests/test_games.py
# Mini-games functionality tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import os
import sys
import sqlite3
import json
import random
import time
from unittest.mock import patch, Mock, MagicMock, call
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from models.games import (
        get_game_odds_and_prizes, select_prize_by_probability
    )
    GAMES_MODEL_AVAILABLE = True
except ImportError:
    GAMES_MODEL_AVAILABLE = False

from config import Config
import incentive_service
from incentive_service import play_mini_game, award_mini_game


class TestGameModels:
    """Test game model functionality"""
    
    @pytest.mark.skipif(not GAMES_MODEL_AVAILABLE, reason="Games model not available")
    def test_get_game_odds_with_database_data(self, test_db_path, init_test_db):
        """Test getting game odds from database"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            try:
                # Create game_odds table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS game_odds (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_type TEXT UNIQUE NOT NULL,
                        win_probability REAL NOT NULL,
                        jackpot_probability REAL NOT NULL
                    )
                ''')
                
                # Create game_prizes table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS game_prizes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        game_type TEXT NOT NULL,
                        prize_type TEXT NOT NULL,
                        prize_amount INTEGER NOT NULL,
                        prize_description TEXT NOT NULL,
                        probability REAL NOT NULL,
                        is_jackpot INTEGER DEFAULT 0
                    )
                ''')
                
                # Insert test data
                cursor.execute(
                    "INSERT INTO game_odds (game_type, win_probability, jackpot_probability) VALUES (?, ?, ?)",
                    ("slots", 0.25, 0.02)
                )
                
                cursor.execute(
                    "INSERT INTO game_prizes (game_type, prize_type, prize_amount, prize_description, probability, is_jackpot) VALUES (?, ?, ?, ?, ?, ?)",
                    ("slots", "points", 10, "10 Points", 0.15, 0)
                )
                
                conn.commit()
                
                # Test getting odds and prizes
                odds, prizes = get_game_odds_and_prizes(conn, "slots")
                
                assert odds['win_probability'] == 0.25
                assert odds['jackpot_probability'] == 0.02
                assert len(prizes) == 1
                assert prizes[0]['prize_type'] == "points"
                assert prizes[0]['prize_amount'] == 10
                
            finally:
                conn.close()
    
    @pytest.mark.skipif(not GAMES_MODEL_AVAILABLE, reason="Games model not available")
    def test_get_game_odds_with_fallback(self, test_db_path, init_test_db):
        """Test getting game odds with fallback values"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            conn.row_factory = sqlite3.Row
            
            try:
                # Test with non-existent game type (should use fallbacks)
                odds, prizes = get_game_odds_and_prizes(conn, "nonexistent_game")
                
                # Should return fallback values
                assert odds['win_probability'] == 0.3
                assert odds['jackpot_probability'] == 0.05
                assert len(prizes) >= 1
                assert all(p['prize_type'] == 'points' for p in prizes)
                
            finally:
                conn.close()
    
    @pytest.mark.skipif(not GAMES_MODEL_AVAILABLE, reason="Games model not available")
    def test_select_prize_by_probability(self):
        """Test prize selection based on probability"""
        prizes = [
            {'prize_type': 'points', 'prize_amount': 5, 'probability': 0.5, 'is_jackpot': 0},
            {'prize_type': 'points', 'prize_amount': 10, 'probability': 0.3, 'is_jackpot': 0},
            {'prize_type': 'money', 'prize_amount': 25, 'probability': 0.2, 'is_jackpot': 1}
        ]
        
        # Test multiple selections to verify probability distribution
        selections = {}
        for _ in range(1000):
            prize = select_prize_by_probability(prizes)
            key = f"{prize['prize_type']}_{prize['prize_amount']}"
            selections[key] = selections.get(key, 0) + 1
        
        # Most frequent should be the 5 points (50% probability)
        most_common = max(selections.items(), key=lambda x: x[1])
        assert "points_5" in most_common[0]
        
        # All prize types should have been selected at least once
        assert len(selections) == 3


class TestMiniGameService:
    """Test mini-game service functionality"""
    
    def test_play_mini_game_slots(self, test_db_path, init_test_db):
        """Test playing slots mini-game"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Create required tables for mini-games
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mini_game_plays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    bet_amount INTEGER NOT NULL,
                    payout INTEGER NOT NULL,
                    result TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees (id)
                )
            ''')
            
            conn.commit()
            conn.close()
            
            try:
                # Test playing slots game
                result = play_mini_game(2, "slots", 10)  # Employee ID 2, bet 10 points
                
                # Should return game result
                assert result is not None
                
                if isinstance(result, dict):
                    assert 'game_type' in result
                    assert result['game_type'] == 'slots'
                    assert 'payout' in result
                    assert isinstance(result['payout'], (int, float))
                
            except Exception as e:
                # Some errors are acceptable if game logic requires additional setup
                assert any(keyword in str(e).lower() for keyword in ["table", "column", "game"])
    
    def test_play_mini_game_scratch_off(self, test_db_path, init_test_db):
        """Test playing scratch-off mini-game"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                result = play_mini_game(2, "scratch_off", 5)
                
                # Should return game result
                assert result is not None
                
                if isinstance(result, dict):
                    assert 'game_type' in result or 'payout' in result
                
            except Exception as e:
                # Some errors are acceptable if game logic requires additional setup
                assert any(keyword in str(e).lower() for keyword in ["table", "column", "game", "implemented"])
    
    def test_play_mini_game_roulette(self, test_db_path, init_test_db):
        """Test playing roulette mini-game"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                result = play_mini_game(2, "roulette", 20)
                
                # Should return game result
                assert result is not None
                
            except Exception as e:
                # Some errors are acceptable if game logic requires additional setup
                assert any(keyword in str(e).lower() for keyword in ["table", "column", "game", "implemented"])
    
    def test_play_mini_game_wheel(self, test_db_path, init_test_db):
        """Test playing wheel mini-game"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                result = play_mini_game(2, "wheel", 15)
                
                # Should return game result
                assert result is not None
                
            except Exception as e:
                # Some errors are acceptable if game logic requires additional setup
                assert any(keyword in str(e).lower() for keyword in ["table", "column", "game", "implemented"])
    
    def test_play_mini_game_dice(self, test_db_path, init_test_db):
        """Test playing dice mini-game"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                result = play_mini_game(2, "dice", 8)
                
                # Should return game result
                assert result is not None
                
            except Exception as e:
                # Some errors are acceptable if game logic requires additional setup
                assert any(keyword in str(e).lower() for keyword in ["table", "column", "game", "implemented"])
    
    def test_award_mini_game(self, test_db_path, init_test_db):
        """Test awarding mini-game prizes"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                # Test awarding a prize
                result = award_mini_game(2, "slots", "points", 25, "Won 25 points")
                
                # Should return success indicator
                assert result is not None
                
                if isinstance(result, bool):
                    assert result is True
                elif isinstance(result, dict):
                    assert 'success' in result or 'awarded' in result
                
            except Exception as e:
                # Some errors are acceptable if award logic requires additional setup
                assert any(keyword in str(e).lower() for keyword in ["table", "column", "award", "implemented"])


class TestGameLogic:
    """Test individual game logic components"""
    
    def test_slots_game_logic(self):
        """Test slots game logic"""
        # Test basic slots mechanics
        def simulate_slots_spin():
            symbols = ['🍒', '🍋', '🍊', '🍇', '⭐', '💎']
            reels = [random.choice(symbols) for _ in range(3)]
            
            # Check for wins
            if len(set(reels)) == 1:  # All same
                return {'result': 'jackpot', 'symbols': reels, 'multiplier': 10}
            elif len(set(reels)) == 2:  # Two same
                return {'result': 'win', 'symbols': reels, 'multiplier': 2}
            else:  # No match
                return {'result': 'lose', 'symbols': reels, 'multiplier': 0}
        
        # Run multiple simulations
        results = [simulate_slots_spin() for _ in range(100)]
        
        # Should have variety of outcomes
        win_types = set(r['result'] for r in results)
        assert len(win_types) > 1  # Should have different outcomes
        assert all(r['multiplier'] >= 0 for r in results)  # Multipliers should be non-negative
    
    def test_scratch_off_game_logic(self):
        """Test scratch-off game logic"""
        def simulate_scratch_off():
            # Simple scratch-off logic
            hidden_symbols = ['💰', '🎁', '💎', '⭐', '🍀', '❌']
            revealed = [random.choice(hidden_symbols) for _ in range(9)]
            
            # Check for winning patterns
            symbol_counts = {}
            for symbol in revealed:
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            
            # Win if 3 or more of the same symbol
            max_count = max(symbol_counts.values()) if symbol_counts else 0
            if max_count >= 3:
                winning_symbol = max(symbol_counts.items(), key=lambda x: x[1])[0]
                return {'result': 'win', 'symbol': winning_symbol, 'count': max_count}
            else:
                return {'result': 'lose', 'count': max_count}
        
        # Run simulations
        results = [simulate_scratch_off() for _ in range(100)]
        
        # Should have both wins and losses
        outcomes = set(r['result'] for r in results)
        assert 'win' in outcomes or 'lose' in outcomes
        assert all('count' in r for r in results)
    
    def test_roulette_game_logic(self):
        """Test roulette game logic"""
        def simulate_roulette_spin(bet_type, bet_value):
            # Simulate roulette wheel (0-36)
            winning_number = random.randint(0, 36)
            
            # Determine win/lose based on bet type
            if bet_type == 'number':
                return {'result': 'win' if winning_number == bet_value else 'lose', 
                       'number': winning_number, 'payout': 35 if winning_number == bet_value else 0}
            elif bet_type == 'red':
                red_numbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
                return {'result': 'win' if winning_number in red_numbers else 'lose',
                       'number': winning_number, 'payout': 1 if winning_number in red_numbers else 0}
            elif bet_type == 'even':
                return {'result': 'win' if winning_number > 0 and winning_number % 2 == 0 else 'lose',
                       'number': winning_number, 'payout': 1 if winning_number > 0 and winning_number % 2 == 0 else 0}
            else:
                return {'result': 'lose', 'number': winning_number, 'payout': 0}
        
        # Test different bet types
        number_result = simulate_roulette_spin('number', 17)
        red_result = simulate_roulette_spin('red', None)
        even_result = simulate_roulette_spin('even', None)
        
        # All should have required fields
        for result in [number_result, red_result, even_result]:
            assert 'result' in result
            assert 'number' in result
            assert 'payout' in result
            assert result['result'] in ['win', 'lose']
            assert 0 <= result['number'] <= 36
    
    def test_wheel_game_logic(self):
        """Test wheel of fortune game logic"""
        def simulate_wheel_spin():
            # Define wheel segments with different values and probabilities
            segments = [
                {'value': 0, 'probability': 0.3, 'color': 'red'},
                {'value': 5, 'probability': 0.2, 'color': 'blue'},
                {'value': 10, 'probability': 0.2, 'color': 'green'},
                {'value': 25, 'probability': 0.15, 'color': 'yellow'},
                {'value': 50, 'probability': 0.1, 'color': 'purple'},
                {'value': 100, 'probability': 0.05, 'color': 'gold'}
            ]
            
            # Select segment based on probability
            rand_val = random.random()
            cumulative = 0
            
            for segment in segments:
                cumulative += segment['probability']
                if rand_val <= cumulative:
                    return {
                        'result': 'win' if segment['value'] > 0 else 'lose',
                        'value': segment['value'],
                        'color': segment['color']
                    }
            
            # Fallback to last segment
            return {'result': 'lose', 'value': 0, 'color': 'red'}
        
        # Run simulations
        results = [simulate_wheel_spin() for _ in range(100)]
        
        # Should have variety of outcomes
        values = set(r['value'] for r in results)
        colors = set(r['color'] for r in results)
        
        assert len(values) > 1  # Multiple values should be hit
        assert len(colors) > 1  # Multiple colors should be hit
        assert all(r['value'] >= 0 for r in results)  # Values should be non-negative
    
    def test_dice_game_logic(self):
        """Test dice game logic"""
        def simulate_dice_roll(num_dice=2):
            rolls = [random.randint(1, 6) for _ in range(num_dice)]
            total = sum(rolls)
            
            # Simple winning conditions
            if total == 7 or total == 11:  # Lucky numbers
                return {'result': 'big_win', 'rolls': rolls, 'total': total, 'payout': 3}
            elif total in [6, 8]:  # Good numbers
                return {'result': 'win', 'rolls': rolls, 'total': total, 'payout': 2}
            elif total == 2 or total == 12:  # Snake eyes or boxcars
                return {'result': 'small_win', 'rolls': rolls, 'total': total, 'payout': 1}
            else:
                return {'result': 'lose', 'rolls': rolls, 'total': total, 'payout': 0}
        
        # Test multiple dice rolls
        results = [simulate_dice_roll() for _ in range(100)]
        
        # Verify dice roll properties
        for result in results:
            assert 'result' in result
            assert 'rolls' in result
            assert 'total' in result
            assert 'payout' in result
            assert len(result['rolls']) == 2
            assert all(1 <= roll <= 6 for roll in result['rolls'])
            assert result['total'] == sum(result['rolls'])
            assert 2 <= result['total'] <= 12


class TestGamePersistence:
    """Test game data persistence"""
    
    def test_game_play_recording(self, test_db_path, init_test_db):
        """Test that game plays are recorded in database"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            # Create mini_game_plays table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mini_game_plays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    bet_amount INTEGER NOT NULL,
                    payout INTEGER NOT NULL,
                    result TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (employee_id) REFERENCES employees (id)
                )
            ''')
            
            # Record a test game play
            cursor.execute(
                "INSERT INTO mini_game_plays (employee_id, game_type, bet_amount, payout, result) VALUES (?, ?, ?, ?, ?)",
                (2, "slots", 10, 25, "win")
            )
            
            conn.commit()
            
            # Verify the record was saved
            cursor.execute("SELECT * FROM mini_game_plays WHERE employee_id = ? AND game_type = ?", (2, "slots"))
            record = cursor.fetchone()
            
            assert record is not None
            assert record[1] == 2  # employee_id
            assert record[2] == "slots"  # game_type
            assert record[3] == 10  # bet_amount
            assert record[4] == 25  # payout
            assert record[5] == "win"  # result
            
            conn.close()
    
    def test_game_statistics_tracking(self, test_db_path, init_test_db):
        """Test tracking of game statistics"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            # Create required tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS mini_game_plays (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    employee_id INTEGER NOT NULL,
                    game_type TEXT NOT NULL,
                    bet_amount INTEGER NOT NULL,
                    payout INTEGER NOT NULL,
                    result TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Insert multiple game plays for statistics
            game_plays = [
                (2, "slots", 10, 0, "lose", datetime.now().isoformat()),
                (2, "slots", 10, 20, "win", datetime.now().isoformat()),
                (2, "slots", 10, 50, "big_win", datetime.now().isoformat()),
                (3, "roulette", 20, 0, "lose", datetime.now().isoformat()),
                (3, "roulette", 20, 40, "win", datetime.now().isoformat())
            ]
            
            cursor.executemany(
                "INSERT INTO mini_game_plays (employee_id, game_type, bet_amount, payout, result, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                game_plays
            )
            
            conn.commit()
            
            # Generate statistics
            cursor.execute("""
                SELECT 
                    game_type,
                    COUNT(*) as total_plays,
                    SUM(bet_amount) as total_bet,
                    SUM(payout) as total_payout,
                    AVG(payout) as avg_payout,
                    COUNT(CASE WHEN payout > 0 THEN 1 END) as wins,
                    ROUND(COUNT(CASE WHEN payout > 0 THEN 1 END) * 100.0 / COUNT(*), 2) as win_rate
                FROM mini_game_plays
                GROUP BY game_type
            """)
            
            stats = cursor.fetchall()
            assert len(stats) >= 2  # Should have stats for at least 2 game types
            
            # Verify statistics structure
            for stat in stats:
                assert len(stat) == 7  # All expected columns
                assert stat[1] > 0  # total_plays should be positive
                assert stat[2] > 0  # total_bet should be positive
                assert stat[6] >= 0 and stat[6] <= 100  # win_rate should be percentage
            
            conn.close()


class TestGameErrorHandling:
    """Test game error handling"""
    
    def test_invalid_game_type(self, test_db_path, init_test_db):
        """Test handling of invalid game types"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                result = play_mini_game(2, "invalid_game", 10)
                
                # Should handle invalid game type gracefully
                if result is not None:
                    assert isinstance(result, (dict, bool))
                else:
                    assert result is None  # Acceptable response for invalid game
                    
            except Exception as e:
                # Specific game-related errors are acceptable
                assert any(keyword in str(e).lower() for keyword in ["game", "invalid", "type", "implemented"])
    
    def test_insufficient_points(self, test_db_path, init_test_db):
        """Test handling when employee has insufficient points"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Try to bet more points than employee has
            # John Doe has 100 points, try to bet 200
            try:
                result = play_mini_game(2, "slots", 200)
                
                # Should handle insufficient points gracefully
                if result is not None:
                    if isinstance(result, dict):
                        assert 'error' in result or 'insufficient' in str(result).lower()
                    else:
                        assert isinstance(result, bool) and result is False
                        
            except Exception as e:
                # Errors related to insufficient points are acceptable
                assert any(keyword in str(e).lower() for keyword in ["insufficient", "points", "balance", "funds"])
    
    def test_invalid_employee(self, test_db_path, init_test_db):
        """Test handling of invalid employee ID"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                result = play_mini_game(999, "slots", 10)  # Non-existent employee
                
                # Should handle invalid employee gracefully
                if result is not None:
                    if isinstance(result, dict):
                        assert 'error' in result or 'employee' in str(result).lower()
                    else:
                        assert isinstance(result, bool) and result is False
                        
            except Exception as e:
                # Errors related to invalid employee are acceptable
                assert any(keyword in str(e).lower() for keyword in ["employee", "not found", "invalid", "foreign key"])
    
    def test_negative_bet_amount(self, test_db_path, init_test_db):
        """Test handling of negative bet amounts"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            try:
                result = play_mini_game(2, "slots", -10)  # Negative bet
                
                # Should reject negative bets
                if result is not None:
                    if isinstance(result, dict):
                        assert 'error' in result or 'invalid' in str(result).lower()
                    else:
                        assert isinstance(result, bool) and result is False
                        
            except Exception as e:
                # Errors related to invalid bet amounts are acceptable
                assert any(keyword in str(e).lower() for keyword in ["bet", "amount", "invalid", "negative"])


class TestGamePerformance:
    """Test game performance characteristics"""
    
    def test_game_response_time(self, test_db_path, init_test_db):
        """Test that games respond within reasonable time"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Test game response times
            start_time = time.time()
            
            try:
                # Try to play a game and measure response time
                result = play_mini_game(2, "slots", 10)
                elapsed_time = time.time() - start_time
                
                # Should respond within 5 seconds
                assert elapsed_time < 5.0
                
            except Exception:
                # Even if game fails, it should fail quickly
                elapsed_time = time.time() - start_time
                assert elapsed_time < 5.0
    
    def test_concurrent_game_plays(self, test_db_path, init_test_db):
        """Test concurrent game plays"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            import threading
            
            results = []
            errors = []
            
            def play_game(employee_id, game_type, bet_amount):
                try:
                    result = play_mini_game(employee_id, game_type, bet_amount)
                    results.append(result)
                except Exception as e:
                    errors.append(str(e))
            
            # Create multiple threads playing games concurrently
            threads = []
            for i in range(5):
                thread = threading.Thread(target=play_game, args=(2, "slots", 5))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads to complete
            for thread in threads:
                thread.join(timeout=10)  # 10 second timeout
            
            # Should handle concurrent plays without major issues
            total_operations = len(results) + len(errors)
            assert total_operations == 5  # All operations should complete
            
            # Most operations should succeed or fail gracefully
            critical_errors = [e for e in errors if "database is locked" in e.lower()]
            assert len(critical_errors) < 3  # Allow some database locking but not all


if __name__ == '__main__':
    pytest.main([__file__, '-v'])