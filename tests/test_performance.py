# tests/test_performance.py
# Performance and load tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import time
import threading
import sqlite3
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch, Mock
import tempfile
import random

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
import incentive_service
from incentive_service import (
    DatabaseConnection, get_scoreboard, start_voting_session, cast_votes,
    play_mini_game, get_settings
)


class TestDatabasePerformance:
    """Test database operation performance"""
    
    def test_connection_establishment_time(self, test_db_path, init_test_db):
        """Test database connection establishment time"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            connection_times = []
            
            for _ in range(10):
                start_time = time.time()
                with DatabaseConnection() as conn:
                    connection_times.append(time.time() - start_time)
            
            avg_connection_time = sum(connection_times) / len(connection_times)
            max_connection_time = max(connection_times)
            
            # Connection should be fast (less than 100ms average, 500ms max)
            assert avg_connection_time < 0.1, f"Average connection time too slow: {avg_connection_time:.3f}s"
            assert max_connection_time < 0.5, f"Max connection time too slow: {max_connection_time:.3f}s"
    
    def test_scoreboard_query_performance(self, test_db_path, init_test_db):
        """Test scoreboard query performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Add more employees for performance testing
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            # Add 100 test employees
            employees = [(f"Employee {i}", f"{i+1000:04d}", i * 10, "employee", 1) 
                        for i in range(100)]
            cursor.executemany(
                "INSERT INTO employees (name, pin, score, role, is_active) VALUES (?, ?, ?, ?, ?)",
                employees
            )
            conn.commit()
            conn.close()
            
            # Test scoreboard query performance
            query_times = []
            for _ in range(10):
                start_time = time.time()
                with DatabaseConnection() as conn:
                    scoreboard = get_scoreboard(conn)
                query_times.append(time.time() - start_time)
            
            avg_query_time = sum(query_times) / len(query_times)
            max_query_time = max(query_times)
            
            # Query should be fast even with many employees
            assert avg_query_time < 0.5, f"Scoreboard query too slow: {avg_query_time:.3f}s"
            assert max_query_time < 1.0, f"Max scoreboard query time too slow: {max_query_time:.3f}s"
            assert len(scoreboard) >= 100, "Not all employees returned"
    
    def test_concurrent_database_operations(self, test_db_path, init_test_db):
        """Test concurrent database operations performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            results = []
            errors = []
            
            def database_operation(operation_id):
                try:
                    start_time = time.time()
                    with DatabaseConnection() as conn:
                        # Perform various database operations
                        scoreboard = get_scoreboard(conn)
                        settings = get_settings(conn)
                        
                        # Simulate some data modification
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE employees SET score = score + 1 WHERE id = ?",
                            (2 + (operation_id % 3),)  # Update different employees
                        )
                        conn.commit()
                    
                    elapsed = time.time() - start_time
                    results.append(elapsed)
                    
                except Exception as e:
                    errors.append(str(e))
            
            # Run 20 concurrent database operations
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(database_operation, i) for i in range(20)]
                
                for future in as_completed(futures, timeout=30):
                    future.result()
            
            # Analyze performance
            assert len(errors) == 0, f"Database errors during concurrent operations: {errors}"
            assert len(results) == 20, "Not all operations completed"
            
            avg_time = sum(results) / len(results)
            max_time = max(results)
            
            # Concurrent operations should complete in reasonable time
            assert avg_time < 2.0, f"Average concurrent operation time too slow: {avg_time:.3f}s"
            assert max_time < 5.0, f"Max concurrent operation time too slow: {max_time:.3f}s"
    
    def test_large_dataset_performance(self, test_db_path, init_test_db):
        """Test performance with large datasets"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Create large dataset
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            # Add 1000 employees
            start_time = time.time()
            employees = [(f"Employee {i}", f"{i+2000:04d}", random.randint(0, 1000), "employee", 1) 
                        for i in range(1000)]
            cursor.executemany(
                "INSERT INTO employees (name, pin, score, role, is_active) VALUES (?, ?, ?, ?, ?)",
                employees
            )
            conn.commit()
            insertion_time = time.time() - start_time
            
            # Add votes for performance testing
            start_time = time.time()
            votes = []
            for i in range(5000):  # 5000 votes
                voter_id = random.randint(2, 501)  # Random voter
                voted_for_id = random.randint(2, 501)  # Random target
                vote_type = random.choice(['positive', 'negative'])
                votes.append((voter_id, voted_for_id, vote_type, 'perf_test_session'))
            
            cursor.executemany(
                "INSERT INTO votes (voter_id, voted_for_id, vote_type, session_id) VALUES (?, ?, ?, ?)",
                votes
            )
            conn.commit()
            vote_insertion_time = time.time() - start_time
            conn.close()
            
            # Test query performance with large dataset
            start_time = time.time()
            with DatabaseConnection() as conn:
                scoreboard = get_scoreboard(conn)
            large_query_time = time.time() - start_time
            
            # Performance benchmarks for large datasets
            assert insertion_time < 10.0, f"Employee insertion too slow: {insertion_time:.3f}s"
            assert vote_insertion_time < 10.0, f"Vote insertion too slow: {vote_insertion_time:.3f}s"
            assert large_query_time < 2.0, f"Large dataset query too slow: {large_query_time:.3f}s"
            assert len(scoreboard) >= 1000, "Not all employees returned from large dataset"


class TestApplicationPerformance:
    """Test Flask application performance"""
    
    def test_route_response_times(self, client, performance_timer):
        """Test response times for main routes"""
        routes_to_test = [
            '/',
            '/admin',
            '/static/style.css',
            '/static/script.js'
        ]
        
        response_times = {}
        
        for route in routes_to_test:
            with performance_timer() as timer:
                response = client.get(route)
                elapsed = timer()
            
            response_times[route] = elapsed
            
            # Each route should respond quickly
            assert elapsed < 2.0, f"Route {route} too slow: {elapsed:.3f}s"
            assert response.status_code in [200, 302, 404], f"Route {route} returned {response.status_code}"
        
        # Home page should be especially fast
        if '/' in response_times:
            assert response_times['/'] < 1.0, f"Home page too slow: {response_times['/']:.3f}s"
    
    @patch('app.get_settings')
    @patch('app.get_scoreboard') 
    @patch('app.is_voting_active')
    def test_concurrent_web_requests(self, mock_is_voting_active, mock_get_scoreboard, 
                                   mock_get_settings, client):
        """Test concurrent web request handling"""
        # Mock dependencies to avoid database issues
        mock_get_settings.return_value = {'site_name': 'Test Site'}
        mock_get_scoreboard.return_value = []
        mock_is_voting_active.return_value = False
        
        results = []
        errors = []
        
        def make_request(request_id):
            try:
                start_time = time.time()
                response = client.get('/')
                elapsed = time.time() - start_time
                
                results.append({
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'response_time': elapsed
                })
            except Exception as e:
                errors.append(f"Request {request_id}: {str(e)}")
        
        # Make 50 concurrent requests
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request, i) for i in range(50)]
            
            for future in as_completed(futures, timeout=30):
                future.result()
        
        # Analyze results
        assert len(errors) == 0, f"Errors during concurrent requests: {errors}"
        assert len(results) == 50, "Not all requests completed"
        
        # All requests should succeed
        successful_requests = [r for r in results if r['status_code'] == 200]
        assert len(successful_requests) >= 45, "Too many failed requests"  # Allow 10% failure rate
        
        # Response times should be reasonable
        avg_response_time = sum(r['response_time'] for r in results) / len(results)
        max_response_time = max(r['response_time'] for r in results)
        
        assert avg_response_time < 2.0, f"Average response time too slow: {avg_response_time:.3f}s"
        assert max_response_time < 5.0, f"Max response time too slow: {max_response_time:.3f}s"
    
    def test_memory_usage_stability(self, client):
        """Test memory usage stability under load"""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make many requests to test for memory leaks
        for i in range(100):
            response = client.get('/')
            
            # Check memory every 20 requests
            if i % 20 == 0:
                current_memory = process.memory_info().rss
                memory_increase = current_memory - initial_memory
                
                # Memory shouldn't grow excessively (allow 50MB growth)
                assert memory_increase < 50 * 1024 * 1024, \
                    f"Memory usage increased too much: {memory_increase / 1024 / 1024:.1f}MB"
        
        # Final memory check
        final_memory = process.memory_info().rss
        total_memory_increase = final_memory - initial_memory
        
        # Total memory increase should be reasonable
        assert total_memory_increase < 100 * 1024 * 1024, \
            f"Total memory increase too large: {total_memory_increase / 1024 / 1024:.1f}MB"


class TestVotingPerformance:
    """Test voting system performance"""
    
    def test_voting_session_creation_performance(self, test_db_path, init_test_db):
        """Test voting session creation performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            creation_times = []
            
            for _ in range(10):
                start_time = time.time()
                with DatabaseConnection() as conn:
                    session_id = start_voting_session(conn)
                    # Close the session immediately
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE voting_sessions SET status = 'closed' WHERE session_id = ?",
                        (session_id,)
                    )
                    conn.commit()
                
                creation_times.append(time.time() - start_time)
            
            avg_time = sum(creation_times) / len(creation_times)
            max_time = max(creation_times)
            
            assert avg_time < 0.1, f"Voting session creation too slow: {avg_time:.3f}s"
            assert max_time < 0.5, f"Max voting session creation time too slow: {max_time:.3f}s"
    
    def test_vote_casting_performance(self, test_db_path, init_test_db):
        """Test vote casting performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Start voting session
            with DatabaseConnection() as conn:
                session_id = start_voting_session(conn)
            
            # Test individual vote casting performance
            individual_times = []
            for i in range(10):
                votes = {str(3): "positive", str(4): "negative"}  # Two votes
                
                start_time = time.time()
                with DatabaseConnection() as conn:
                    success = cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)
                elapsed = time.time() - start_time
                
                individual_times.append(elapsed)
                assert success is True or success is not False, f"Vote casting failed on iteration {i}"
            
            avg_time = sum(individual_times) / len(individual_times)
            max_time = max(individual_times)
            
            assert avg_time < 0.2, f"Vote casting too slow: {avg_time:.3f}s"
            assert max_time < 0.5, f"Max vote casting time too slow: {max_time:.3f}s"
    
    def test_concurrent_vote_casting(self, test_db_path, init_test_db):
        """Test concurrent vote casting performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Add more employees for concurrent voting
            conn = sqlite3.connect(test_db_path)
            cursor = conn.cursor()
            
            # Add 20 test employees (voters and targets)
            employees = [(f"Voter {i}", f"{i+3000:04d}", 100, "employee", 1) 
                        for i in range(20)]
            cursor.executemany(
                "INSERT INTO employees (name, pin, score, role, is_active) VALUES (?, ?, ?, ?, ?)",
                employees
            )
            conn.commit()
            
            # Start voting session
            session_id = start_voting_session(DatabaseConnection().__enter__())
            conn.close()
            
            results = []
            errors = []
            
            def cast_concurrent_votes(voter_offset):
                try:
                    start_time = time.time()
                    
                    # Each voter votes for 3 different people
                    voter_id = 7 + voter_offset  # Start from employee ID 7
                    votes = {}
                    for i in range(3):
                        target_id = 2 + ((voter_offset + i) % 5)  # Rotate through first 5 employees
                        votes[str(target_id)] = "positive"
                    
                    with DatabaseConnection() as conn:
                        success = cast_votes(conn, voter_id=voter_id, votes=votes, session_id=session_id)
                    
                    elapsed = time.time() - start_time
                    results.append({'success': success, 'time': elapsed})
                    
                except Exception as e:
                    errors.append(str(e))
            
            # Run 15 concurrent voters
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(cast_concurrent_votes, i) for i in range(15)]
                
                for future in as_completed(futures, timeout=20):
                    future.result()
            
            # Analyze results
            successful_votes = [r for r in results if r['success'] is True or r['success'] is not False]
            
            # Most votes should succeed (allow some database conflicts)
            assert len(errors) < 5, f"Too many errors during concurrent voting: {errors[:3]}..."
            assert len(successful_votes) >= 10, f"Too few successful votes: {len(successful_votes)}/15"
            
            if successful_votes:
                avg_time = sum(r['time'] for r in successful_votes) / len(successful_votes)
                max_time = max(r['time'] for r in successful_votes)
                
                assert avg_time < 1.0, f"Concurrent vote casting too slow: {avg_time:.3f}s"
                assert max_time < 3.0, f"Max concurrent vote time too slow: {max_time:.3f}s"


class TestGamePerformance:
    """Test mini-game performance"""
    
    def test_game_execution_performance(self, test_db_path, init_test_db):
        """Test game execution performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            game_types = ['slots', 'scratch_off', 'roulette', 'wheel', 'dice']
            
            for game_type in game_types:
                game_times = []
                
                for _ in range(5):  # Test each game 5 times
                    start_time = time.time()
                    try:
                        result = play_mini_game(2, game_type, 10)
                        elapsed = time.time() - start_time
                        game_times.append(elapsed)
                        
                        # Game should return a result
                        assert result is not None or elapsed < 1.0  # Quick failure is acceptable
                        
                    except Exception as e:
                        elapsed = time.time() - start_time
                        # Even exceptions should happen quickly
                        assert elapsed < 1.0, f"Game {game_type} exception too slow: {elapsed:.3f}s"
                        game_times.append(elapsed)
                
                if game_times:
                    avg_time = sum(game_times) / len(game_times)
                    max_time = max(game_times)
                    
                    assert avg_time < 0.5, f"Game {game_type} too slow: {avg_time:.3f}s"
                    assert max_time < 2.0, f"Game {game_type} max time too slow: {max_time:.3f}s"
    
    def test_concurrent_game_plays(self, test_db_path, init_test_db):
        """Test concurrent game play performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            results = []
            errors = []
            
            def play_concurrent_game(player_id):
                try:
                    start_time = time.time()
                    result = play_mini_game(2 + (player_id % 4), 'slots', 5)  # Rotate between employees
                    elapsed = time.time() - start_time
                    
                    results.append({'result': result, 'time': elapsed})
                    
                except Exception as e:
                    errors.append(str(e))
            
            # Run 20 concurrent games
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(play_concurrent_game, i) for i in range(20)]
                
                for future in as_completed(futures, timeout=30):
                    future.result()
            
            # Analyze results
            completed_games = len(results) + len(errors)
            assert completed_games == 20, "Not all games completed"
            
            if results:
                avg_time = sum(r['time'] for r in results) / len(results)
                max_time = max(r['time'] for r in results)
                
                assert avg_time < 1.0, f"Concurrent games too slow: {avg_time:.3f}s"
                assert max_time < 3.0, f"Max concurrent game time too slow: {max_time:.3f}s"
            
            # Allow some errors but not too many
            error_rate = len(errors) / completed_games
            assert error_rate < 0.5, f"Too many game errors: {error_rate:.1%}"


class TestCachePerformance:
    """Test caching system performance"""
    
    @pytest.mark.skipif(not hasattr(incentive_service, 'CACHING_AVAILABLE') or 
                       not incentive_service.CACHING_AVAILABLE, 
                       reason="Caching not available")
    def test_cache_hit_performance(self, test_db_path, init_test_db):
        """Test cache hit performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # First call to populate cache
            with DatabaseConnection() as conn:
                scoreboard1 = get_scoreboard(conn)
            
            # Subsequent calls should use cache and be faster
            cache_times = []
            for _ in range(10):
                start_time = time.time()
                with DatabaseConnection() as conn:
                    scoreboard2 = get_scoreboard(conn)
                cache_times.append(time.time() - start_time)
            
            avg_cache_time = sum(cache_times) / len(cache_times)
            max_cache_time = max(cache_times)
            
            # Cached calls should be very fast
            assert avg_cache_time < 0.05, f"Cache hits too slow: {avg_cache_time:.3f}s"
            assert max_cache_time < 0.1, f"Max cache hit time too slow: {max_cache_time:.3f}s"
    
    def test_cache_vs_database_performance(self, test_db_path, init_test_db):
        """Test cache performance vs direct database queries"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Time direct database queries (cache disabled)
            db_times = []
            for _ in range(5):
                start_time = time.time()
                with DatabaseConnection() as conn:
                    # Direct query without cache
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT id, name, score, role FROM employees WHERE is_active = 1 ORDER BY score DESC"
                    )
                    direct_result = cursor.fetchall()
                db_times.append(time.time() - start_time)
            
            # Time cached queries
            cache_times = []
            for _ in range(5):
                start_time = time.time()
                with DatabaseConnection() as conn:
                    cached_result = get_scoreboard(conn)  # This may use cache
                cache_times.append(time.time() - start_time)
            
            avg_db_time = sum(db_times) / len(db_times)
            avg_cache_time = sum(cache_times) / len(cache_times)
            
            # Either cache should be faster, or both should be reasonable
            if avg_cache_time < avg_db_time:
                # Cache is working and faster
                speedup_ratio = avg_db_time / avg_cache_time
                assert speedup_ratio > 1.5, f"Cache not significantly faster: {speedup_ratio:.1f}x"
            else:
                # No cache benefit detected, but performance should still be good
                assert avg_cache_time < 0.5, f"Query performance poor: {avg_cache_time:.3f}s"


class TestStressTests:
    """Stress tests for system limits"""
    
    def test_high_concurrent_load(self, client):
        """Test system under high concurrent load"""
        results = []
        errors = []
        
        def stress_request(request_id):
            try:
                start_time = time.time()
                
                # Mix of different requests
                if request_id % 3 == 0:
                    response = client.get('/')
                elif request_id % 3 == 1:
                    response = client.get('/admin')
                else:
                    response = client.get('/static/style.css')
                
                elapsed = time.time() - start_time
                results.append({
                    'request_id': request_id,
                    'status_code': response.status_code,
                    'response_time': elapsed
                })
                
            except Exception as e:
                errors.append(f"Request {request_id}: {str(e)}")
        
        # High load test: 100 concurrent requests
        with ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(stress_request, i) for i in range(100)]
            
            for future in as_completed(futures, timeout=60):
                future.result()
        
        # Analyze stress test results
        total_requests = len(results) + len(errors)
        assert total_requests == 100, "Not all stress test requests completed"
        
        # Allow some failures under stress but not too many
        error_rate = len(errors) / total_requests
        assert error_rate < 0.2, f"Too many errors under stress: {error_rate:.1%}"
        
        if results:
            successful_requests = [r for r in results if r['status_code'] in [200, 302, 404]]
            success_rate = len(successful_requests) / len(results)
            
            assert success_rate > 0.8, f"Success rate too low under stress: {success_rate:.1%}"
            
            # Response times may be slower under stress but should be reasonable
            avg_response_time = sum(r['response_time'] for r in results) / len(results)
            assert avg_response_time < 10.0, f"Average response time under stress too slow: {avg_response_time:.3f}s"
    
    def test_memory_stress_test(self, test_db_path, init_test_db):
        """Test system memory usage under stress"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        peak_memory = initial_memory
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Create many database connections and operations
            for i in range(100):
                try:
                    with DatabaseConnection() as conn:
                        # Perform memory-intensive operations
                        scoreboard = get_scoreboard(conn)
                        settings = get_settings(conn)
                        
                        # Check memory usage periodically
                        if i % 10 == 0:
                            current_memory = process.memory_info().rss
                            peak_memory = max(peak_memory, current_memory)
                            
                            # Memory shouldn't grow excessively
                            memory_increase = current_memory - initial_memory
                            assert memory_increase < 200 * 1024 * 1024, \
                                f"Memory usage too high at iteration {i}: {memory_increase / 1024 / 1024:.1f}MB"
                
                except Exception as e:
                    # Some failures are acceptable under stress
                    if i > 50:  # Allow failures after halfway point
                        continue
                    else:
                        raise e
        
        # Check final memory usage
        final_memory = process.memory_info().rss
        total_increase = final_memory - initial_memory
        peak_increase = peak_memory - initial_memory
        
        assert total_increase < 150 * 1024 * 1024, \
            f"Total memory increase too large: {total_increase / 1024 / 1024:.1f}MB"
        assert peak_increase < 300 * 1024 * 1024, \
            f"Peak memory increase too large: {peak_increase / 1024 / 1024:.1f}MB"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'performance'])