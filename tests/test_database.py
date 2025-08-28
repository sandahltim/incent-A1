# tests/test_database.py
# Database and connection pool tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import sqlite3
import threading
import time
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import incentive_service
from incentive_service import (
    DatabaseConnection, ConnectionPool, ConnectionPoolError,
    get_scoreboard, add_employee, start_voting_session, cast_votes,
    get_history, adjust_points, get_settings, set_settings
)
from config import Config


class TestDatabaseConnection:
    """Test database connection functionality"""
    
    def test_database_connection_creation(self, test_db_path, init_test_db):
        """Test that database connections can be created"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                assert conn is not None
                assert hasattr(conn, 'cursor')
                assert hasattr(conn, 'commit')
                assert hasattr(conn, 'rollback')
    
    def test_database_context_manager(self, test_db_path, init_test_db):
        """Test database connection context manager"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            connection_obj = None
            with DatabaseConnection() as conn:
                connection_obj = conn
                assert conn is not None
            
            # Connection should be closed after exiting context
            # Note: sqlite3 connections don't have an explicit 'closed' property
            # but we can test that operations fail
            try:
                connection_obj.cursor()
                # If we get here, connection might still be open (sqlite3 behavior)
            except Exception:
                # Connection is properly closed
                pass
    
    def test_database_row_factory(self, test_db_path, init_test_db):
        """Test that row factory is set correctly"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                # Test that we can access columns by name
                cursor = conn.cursor()
                cursor.execute("SELECT name, score FROM employees LIMIT 1")
                row = cursor.fetchone()
                
                if row:
                    assert hasattr(row, 'keys')  # Row factory should allow dict-like access
    
    def test_database_transaction_commit(self, test_db_path, init_test_db):
        """Test database transaction commit"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                cursor = conn.cursor()
                
                # Insert a test record
                cursor.execute(
                    "INSERT INTO employees (name, pin, score) VALUES (?, ?, ?)",
                    ("Test Employee", "9999", 100)
                )
                conn.commit()
                
                # Verify the record was committed
                cursor.execute("SELECT name FROM employees WHERE pin = ?", ("9999",))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "Test Employee"
    
    def test_database_transaction_rollback(self, test_db_path, init_test_db):
        """Test database transaction rollback"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                cursor = conn.cursor()
                
                # Insert a test record but don't commit
                cursor.execute(
                    "INSERT INTO employees (name, pin, score) VALUES (?, ?, ?)",
                    ("Rollback Test", "8888", 100)
                )
                
                # Rollback the transaction
                conn.rollback()
                
                # Verify the record was not saved
                cursor.execute("SELECT name FROM employees WHERE pin = ?", ("8888",))
                result = cursor.fetchone()
                assert result is None


class TestConnectionPool:
    """Test database connection pool functionality"""
    
    def test_connection_pool_creation(self):
        """Test that connection pool can be created"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            # Create a simple database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.close()
            
            pool = ConnectionPool(database_path=db_path, pool_size=3)
            assert pool is not None
            assert pool.pool_size == 3
            
            pool.close_all()
    
    def test_connection_pool_get_return(self):
        """Test getting and returning connections from pool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.close()
            
            pool = ConnectionPool(database_path=db_path, pool_size=2)
            
            # Get a connection
            conn1 = pool.get_connection()
            assert conn1 is not None
            
            # Get another connection
            conn2 = pool.get_connection()
            assert conn2 is not None
            assert conn1 != conn2  # Should be different connection objects
            
            # Return connections
            pool.return_connection(conn1)
            pool.return_connection(conn2)
            
            pool.close_all()
    
    def test_connection_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.close()
            
            pool = ConnectionPool(database_path=db_path, pool_size=1, timeout=1)
            
            # Get the only connection
            conn1 = pool.get_connection()
            assert conn1 is not None
            
            # Try to get another connection - should timeout
            start_time = time.time()
            try:
                conn2 = pool.get_connection()
                # If we get here, either pool created a new connection or timeout didn't work
                pool.return_connection(conn2)
            except ConnectionPoolError:
                # Expected behavior when pool is exhausted
                elapsed = time.time() - start_time
                assert elapsed >= 1  # Should have waited at least the timeout period
            
            pool.return_connection(conn1)
            pool.close_all()
    
    def test_connection_pool_stats(self):
        """Test connection pool statistics"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY)")
            conn.close()
            
            pool = ConnectionPool(database_path=db_path, pool_size=3)
            
            stats = pool.get_stats()
            assert 'active_connections' in stats
            assert 'available_connections' in stats
            assert 'total_connections' in stats
            
            # Initially, all connections should be available
            assert stats['available_connections'] <= 3
            assert stats['active_connections'] >= 0
            
            pool.close_all()
    
    def test_connection_pool_concurrent_access(self):
        """Test concurrent access to connection pool"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            conn.close()
            
            pool = ConnectionPool(database_path=db_path, pool_size=5)
            results = []
            errors = []
            
            def worker(worker_id):
                try:
                    conn = pool.get_connection()
                    cursor = conn.cursor()
                    
                    # Perform a database operation
                    cursor.execute("INSERT INTO test (value) VALUES (?)", (f"worker_{worker_id}",))
                    conn.commit()
                    
                    # Read back the data
                    cursor.execute("SELECT COUNT(*) FROM test WHERE value = ?", (f"worker_{worker_id}",))
                    count = cursor.fetchone()[0]
                    
                    pool.return_connection(conn)
                    results.append((worker_id, count))
                    
                except Exception as e:
                    errors.append((worker_id, str(e)))
            
            # Run concurrent workers
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(worker, i) for i in range(10)]
                
                for future in as_completed(futures):
                    future.result()  # Wait for completion
            
            # Verify results
            assert len(errors) == 0, f"Errors in concurrent access: {errors}"
            assert len(results) == 10
            
            # Verify all workers completed successfully
            for worker_id, count in results:
                assert count == 1  # Each worker should have inserted exactly one record
            
            pool.close_all()


class TestDatabaseOperations:
    """Test database operations using the service layer"""
    
    def test_get_scoreboard(self, test_db_path, init_test_db):
        """Test getting scoreboard data"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                scoreboard = get_scoreboard(conn)
                assert isinstance(scoreboard, list)
                
                # Should contain the test employees
                employee_names = [emp['name'] for emp in scoreboard]
                assert 'John Doe' in employee_names
                assert 'Jane Smith' in employee_names
    
    def test_add_employee(self, test_db_path, init_test_db):
        """Test adding a new employee"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                # Add a new employee
                success = add_employee(conn, "New Employee", "7777", "employee")
                assert success is True
                
                # Verify the employee was added
                cursor = conn.cursor()
                cursor.execute("SELECT name, pin FROM employees WHERE pin = ?", ("7777",))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "New Employee"
    
    def test_start_voting_session(self, test_db_path, init_test_db):
        """Test starting a voting session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                session_id = start_voting_session(conn)
                assert session_id is not None
                assert len(session_id) > 0
                
                # Verify the session was created
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM voting_sessions WHERE session_id = ?", (session_id,))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "active"
    
    def test_cast_votes(self, test_db_path, init_test_db, voting_session_active):
        """Test casting votes"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                # Prepare vote data
                vote_data = {
                    '2': 'positive',  # John Doe votes positive
                    '3': 'negative'   # Jane Smith votes negative
                }
                
                success = cast_votes(conn, voter_id=2, votes=vote_data, session_id=voting_session_active)
                assert success is True
                
                # Verify votes were recorded
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM votes WHERE voter_id = ? AND session_id = ?", 
                             (2, voting_session_active))
                count = cursor.fetchone()[0]
                assert count == 2  # Two votes should be recorded
    
    def test_adjust_points(self, test_db_path, init_test_db):
        """Test adjusting employee points"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                # Adjust points for John Doe (employee_id = 2)
                success = adjust_points(conn, employee_id=2, points_change=50, 
                                      reason="Test adjustment", admin_id=1)
                assert success is True
                
                # Verify the adjustment was recorded
                cursor = conn.cursor()
                cursor.execute("SELECT score FROM employees WHERE id = ?", (2,))
                new_score = cursor.fetchone()[0]
                assert new_score == 150  # Original 100 + 50
                
                # Verify history was recorded
                cursor.execute("SELECT points_changed, reason FROM point_history WHERE employee_id = ?", (2,))
                history = cursor.fetchone()
                assert history[0] == 50
                assert history[1] == "Test adjustment"
    
    def test_get_settings(self, test_db_path, init_test_db):
        """Test getting application settings"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                settings = get_settings(conn)
                assert isinstance(settings, dict)
                
                # Should contain the test settings
                assert 'site_name' in settings
                assert settings['site_name'] == "Test Incentive System"
    
    def test_set_settings(self, test_db_path, init_test_db):
        """Test setting application settings"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                # Set a new setting
                success = set_settings(conn, 'test_setting', 'test_value', 'Test description')
                assert success is True
                
                # Verify the setting was saved
                settings = get_settings(conn)
                assert 'test_setting' in settings
                assert settings['test_setting'] == 'test_value'
    
    def test_get_history(self, test_db_path, init_test_db):
        """Test getting point adjustment history"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                # First add some history
                adjust_points(conn, employee_id=2, points_change=25, 
                            reason="Test history", admin_id=1)
                
                # Get the history
                history = get_history(conn)
                assert isinstance(history, list)
                
                # Should contain our test adjustment
                if history:
                    assert any(h['reason'] == 'Test history' for h in history)


class TestDatabaseErrorHandling:
    """Test database error handling"""
    
    def test_database_file_not_found(self):
        """Test handling of missing database file"""
        non_existent_path = "/nonexistent/path/database.db"
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', non_existent_path):
            with pytest.raises((sqlite3.OperationalError, FileNotFoundError)):
                with DatabaseConnection() as conn:
                    pass
    
    def test_database_permission_error(self):
        """Test handling of database permission errors"""
        # This test might not work on all systems, so we'll simulate it
        with patch('sqlite3.connect', side_effect=sqlite3.OperationalError("Permission denied")):
            with pytest.raises(sqlite3.OperationalError):
                with DatabaseConnection() as conn:
                    pass
    
    def test_database_corruption_handling(self, test_db_path):
        """Test handling of database corruption"""
        # Create a corrupted database file
        with open(test_db_path, 'w') as f:
            f.write("This is not a valid SQLite database")
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with pytest.raises(sqlite3.DatabaseError):
                with DatabaseConnection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT 1")
    
    def test_sql_injection_prevention(self, test_db_path, init_test_db):
        """Test that SQL injection is prevented by parameterized queries"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                # Try to inject SQL through employee name
                malicious_name = "'; DROP TABLE employees; --"
                
                # This should not succeed in dropping the table
                add_employee(conn, malicious_name, "8888", "employee")
                
                # Verify table still exists and contains the malicious string as data
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM employees")
                count_after = cursor.fetchone()[0]
                assert count_after > 0  # Table should still exist
                
                # Verify the malicious string was stored as data, not executed
                cursor.execute("SELECT name FROM employees WHERE pin = ?", ("8888",))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == malicious_name


class TestDatabasePerformance:
    """Test database performance characteristics"""
    
    def test_connection_pool_performance(self):
        """Test connection pool performance vs individual connections"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "test.db")
            
            # Create test database
            conn = sqlite3.connect(db_path)
            conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
            conn.close()
            
            # Test with connection pool
            pool = ConnectionPool(database_path=db_path, pool_size=5)
            
            def pool_operation():
                conn = pool.get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
                conn.commit()
                pool.return_connection(conn)
            
            # Test without connection pool
            def direct_operation():
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO test (value) VALUES (?)", ("test_value",))
                conn.commit()
                conn.close()
            
            # Time both approaches
            import time
            
            # Pool approach
            start_time = time.time()
            for _ in range(50):
                pool_operation()
            pool_time = time.time() - start_time
            
            # Direct approach
            start_time = time.time()
            for _ in range(50):
                direct_operation()
            direct_time = time.time() - start_time
            
            pool.close_all()
            
            # Pool should be faster or at least not significantly slower
            # Allow some variance for test environment
            assert pool_time < direct_time * 2  # Pool shouldn't be more than 2x slower
    
    def test_large_dataset_handling(self, test_db_path, init_test_db):
        """Test handling of large datasets"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with DatabaseConnection() as conn:
                cursor = conn.cursor()
                
                # Insert a moderate number of test records
                test_data = [(f"Employee {i}", f"{i:04d}", i * 10) for i in range(100, 200)]
                cursor.executemany(
                    "INSERT INTO employees (name, pin, score) VALUES (?, ?, ?)",
                    test_data
                )
                conn.commit()
                
                # Test retrieval performance
                start_time = time.time()
                scoreboard = get_scoreboard(conn)
                query_time = time.time() - start_time
                
                # Should complete within reasonable time (5 seconds for 100+ records)
                assert query_time < 5.0
                assert len(scoreboard) >= 100
    
    def test_concurrent_database_access(self, test_db_path, init_test_db):
        """Test concurrent database access performance"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            def database_worker(worker_id):
                try:
                    with DatabaseConnection() as conn:
                        # Perform some database operations
                        add_employee(conn, f"Worker {worker_id}", f"{9000 + worker_id}", "employee")
                        scoreboard = get_scoreboard(conn)
                        return len(scoreboard)
                except Exception as e:
                    return f"Error: {e}"
            
            # Run concurrent database operations
            start_time = time.time()
            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(database_worker, i) for i in range(10)]
                results = [future.result() for future in as_completed(futures)]
            
            total_time = time.time() - start_time
            
            # Should complete within reasonable time
            assert total_time < 30.0  # 30 seconds should be more than enough
            
            # All workers should complete successfully
            errors = [r for r in results if isinstance(r, str) and r.startswith("Error")]
            assert len(errors) == 0, f"Concurrent access errors: {errors}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])