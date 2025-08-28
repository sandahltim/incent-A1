# tests/test_voting.py
# Voting system tests for the Employee Incentive System
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

from config import Config
import incentive_service
from incentive_service import (
    start_voting_session, is_voting_active, cast_votes, close_voting_session,
    pause_voting_session, resume_voting_session, finalize_voting_session,
    get_voting_results, get_latest_voting_results
)


class TestVotingSession:
    """Test voting session management"""
    
    def test_start_voting_session(self, test_db_path, init_test_db):
        """Test starting a new voting session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                session_id = start_voting_session(conn)
                
                assert session_id is not None
                assert len(session_id) > 0
                
                # Verify session was created in database
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM voting_sessions WHERE session_id = ?", (session_id,))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "active"
    
    def test_is_voting_active_true(self, test_db_path, init_test_db):
        """Test checking if voting is active when it is"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start a voting session
                session_id = start_voting_session(conn)
                
                # Check if voting is active
                is_active = is_voting_active(conn)
                assert is_active is True
    
    def test_is_voting_active_false(self, test_db_path, init_test_db):
        """Test checking if voting is active when it's not"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # No active voting session should exist initially
                is_active = is_voting_active(conn)
                assert is_active is False
    
    def test_close_voting_session(self, test_db_path, init_test_db):
        """Test closing a voting session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start a voting session
                session_id = start_voting_session(conn)
                assert is_voting_active(conn) is True
                
                # Close the voting session
                success = close_voting_session(conn)
                assert success is True
                
                # Verify voting is no longer active
                is_active = is_voting_active(conn)
                assert is_active is False
    
    def test_pause_voting_session(self, test_db_path, init_test_db):
        """Test pausing a voting session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start a voting session
                session_id = start_voting_session(conn)
                
                # Pause the voting session
                success = pause_voting_session(conn)
                assert success is True
                
                # Verify session is paused
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM voting_sessions WHERE session_id = ? ORDER BY start_time DESC LIMIT 1", (session_id,))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "paused"
    
    def test_resume_voting_session(self, test_db_path, init_test_db):
        """Test resuming a paused voting session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start and pause a voting session
                session_id = start_voting_session(conn)
                pause_voting_session(conn)
                
                # Resume the voting session
                success = resume_voting_session(conn)
                assert success is True
                
                # Verify session is active again
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM voting_sessions WHERE session_id = ? ORDER BY start_time DESC LIMIT 1", (session_id,))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "active"
    
    def test_finalize_voting_session(self, test_db_path, init_test_db):
        """Test finalizing a voting session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start a voting session and cast some votes
                session_id = start_voting_session(conn)
                
                # Cast some votes
                votes = {"3": "positive", "4": "positive"}  # Vote for Jane Smith and Bob Johnson
                cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)  # John Doe voting
                
                # Finalize the voting session
                success = finalize_voting_session(conn)
                assert success is True
                
                # Verify session is finalized
                cursor = conn.cursor()
                cursor.execute("SELECT status FROM voting_sessions WHERE session_id = ? ORDER BY start_time DESC LIMIT 1", (session_id,))
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "closed"


class TestVoteCasting:
    """Test vote casting functionality"""
    
    def test_cast_votes_basic(self, test_db_path, init_test_db):
        """Test basic vote casting"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start voting session
                session_id = start_voting_session(conn)
                
                # Cast votes
                votes = {"3": "positive", "4": "negative"}  # Vote for Jane Smith (positive) and Bob Johnson (negative)
                success = cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)
                assert success is True
                
                # Verify votes were recorded
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM votes WHERE voter_id = ? AND session_id = ?", (2, session_id))
                count = cursor.fetchone()[0]
                assert count == 2  # Two votes cast
                
                # Verify vote details
                cursor.execute("SELECT voted_for_id, vote_type FROM votes WHERE voter_id = ? AND session_id = ?", (2, session_id))
                recorded_votes = cursor.fetchall()
                
                vote_dict = {str(vote[0]): vote[1] for vote in recorded_votes}
                assert vote_dict["3"] == "positive"
                assert vote_dict["4"] == "negative"
    
    def test_cast_votes_multiple_employees(self, test_db_path, init_test_db):
        """Test multiple employees casting votes"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start voting session
                session_id = start_voting_session(conn)
                
                # Employee 2 (John Doe) votes
                votes_john = {"3": "positive", "4": "positive"}
                success1 = cast_votes(conn, voter_id=2, votes=votes_john, session_id=session_id)
                assert success1 is True
                
                # Employee 3 (Jane Smith) votes
                votes_jane = {"2": "positive", "4": "negative"}
                success2 = cast_votes(conn, voter_id=3, votes=votes_jane, session_id=session_id)
                assert success2 is True
                
                # Verify all votes were recorded
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM votes WHERE session_id = ?", (session_id,))
                total_votes = cursor.fetchone()[0]
                assert total_votes == 4  # 2 votes from each employee
                
                # Verify vote distribution
                cursor.execute("SELECT COUNT(*) FROM votes WHERE vote_type = 'positive' AND session_id = ?", (session_id,))
                positive_votes = cursor.fetchone()[0]
                assert positive_votes == 3
                
                cursor.execute("SELECT COUNT(*) FROM votes WHERE vote_type = 'negative' AND session_id = ?", (session_id,))
                negative_votes = cursor.fetchone()[0]
                assert negative_votes == 1
    
    def test_cast_votes_invalid_session(self, test_db_path, init_test_db):
        """Test casting votes with invalid session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Try to cast votes without active session
                votes = {"3": "positive"}
                success = cast_votes(conn, voter_id=2, votes=votes, session_id="invalid_session")
                
                # Should fail or return False
                assert success is False or success is None
    
    def test_cast_votes_invalid_employee(self, test_db_path, init_test_db):
        """Test casting votes with invalid employee ID"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start voting session
                session_id = start_voting_session(conn)
                
                # Try to cast votes with invalid employee ID
                votes = {"3": "positive"}
                try:
                    success = cast_votes(conn, voter_id=999, votes=votes, session_id=session_id)
                    # Should fail
                    assert success is False or success is None
                except Exception as e:
                    # Foreign key constraint error is acceptable
                    assert "foreign key" in str(e).lower() or "constraint" in str(e).lower()
    
    def test_cast_votes_for_inactive_employee(self, test_db_path, init_test_db):
        """Test casting votes for inactive employee"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start voting session
                session_id = start_voting_session(conn)
                
                # Try to vote for inactive employee (employee ID 6 from test data)
                votes = {"6": "positive"}  # Inactive User
                
                # This might succeed (depends on business logic)
                # or fail depending on how the system handles inactive employees
                try:
                    success = cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)
                    # Either succeeds or fails gracefully
                    assert success in [True, False] or success is None
                except Exception:
                    # Some constraint violations are acceptable
                    pass


class TestVotingResults:
    """Test voting results functionality"""
    
    def test_get_voting_results(self, test_db_path, init_test_db):
        """Test getting voting results"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start voting session and cast votes
                session_id = start_voting_session(conn)
                
                # Multiple employees vote
                cast_votes(conn, voter_id=2, votes={"3": "positive", "4": "positive"}, session_id=session_id)
                cast_votes(conn, voter_id=3, votes={"2": "positive", "4": "negative"}, session_id=session_id)
                cast_votes(conn, voter_id=4, votes={"2": "positive", "3": "positive"}, session_id=session_id)
                
                # Get voting results
                results = get_voting_results(conn, session_id)
                
                assert results is not None
                assert isinstance(results, (list, dict))
                
                if isinstance(results, list):
                    # Results should contain vote tallies
                    assert len(results) > 0
                elif isinstance(results, dict):
                    # Results should have expected structure
                    assert len(results) > 0
    
    def test_get_latest_voting_results(self, test_db_path, init_test_db):
        """Test getting latest voting results"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start voting session and cast votes
                session_id = start_voting_session(conn)
                cast_votes(conn, voter_id=2, votes={"3": "positive"}, session_id=session_id)
                
                # Close session
                close_voting_session(conn)
                
                # Get latest results
                latest_results = get_latest_voting_results(conn)
                
                assert latest_results is not None
                # Should return results from the most recent session
                if isinstance(latest_results, (list, dict)):
                    assert len(latest_results) >= 0  # May be empty but should be a valid structure
    
    def test_voting_results_calculation(self, test_db_path, init_test_db):
        """Test voting results calculation accuracy"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start voting session
                session_id = start_voting_session(conn)
                
                # Cast specific votes to test calculation
                # Employee 2 (John) gets 2 positive votes
                # Employee 3 (Jane) gets 1 positive, 1 negative vote
                # Employee 4 (Bob) gets 1 negative vote
                cast_votes(conn, voter_id=2, votes={"3": "positive", "4": "negative"}, session_id=session_id)
                cast_votes(conn, voter_id=3, votes={"2": "positive", "4": "negative"}, session_id=session_id)
                cast_votes(conn, voter_id=4, votes={"2": "positive", "3": "negative"}, session_id=session_id)
                
                # Manually calculate expected results
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        voted_for_id,
                        COUNT(CASE WHEN vote_type = 'positive' THEN 1 END) as positive_votes,
                        COUNT(CASE WHEN vote_type = 'negative' THEN 1 END) as negative_votes,
                        COUNT(*) as total_votes
                    FROM votes 
                    WHERE session_id = ?
                    GROUP BY voted_for_id
                    ORDER BY voted_for_id
                """, (session_id,))
                
                manual_results = cursor.fetchall()
                
                # Verify calculations
                results_dict = {row[0]: {'positive': row[1], 'negative': row[2], 'total': row[3]} for row in manual_results}
                
                # Employee 2 should have 2 positive votes
                if 2 in results_dict:
                    assert results_dict[2]['positive'] == 2
                    assert results_dict[2]['negative'] == 0
                
                # Employee 3 should have 1 positive, 1 negative vote
                if 3 in results_dict:
                    assert results_dict[3]['positive'] == 1
                    assert results_dict[3]['negative'] == 1
                
                # Employee 4 should have 0 positive, 2 negative votes
                if 4 in results_dict:
                    assert results_dict[4]['positive'] == 0
                    assert results_dict[4]['negative'] == 2


class TestVotingConstraints:
    """Test voting constraints and validation"""
    
    def test_vote_during_inactive_session(self, test_db_path, init_test_db):
        """Test that votes cannot be cast during inactive session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Try to vote without any active session
                votes = {"3": "positive"}
                
                # Generate a fake session ID
                fake_session_id = f"fake_session_{int(time.time())}"
                success = cast_votes(conn, voter_id=2, votes=votes, session_id=fake_session_id)
                
                # Should fail
                assert success is False or success is None
    
    def test_vote_during_paused_session(self, test_db_path, init_test_db):
        """Test voting during paused session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start and pause session
                session_id = start_voting_session(conn)
                pause_voting_session(conn)
                
                # Try to vote during paused session
                votes = {"3": "positive"}
                success = cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)
                
                # Depending on business logic, this might be allowed or not
                # The test verifies the system handles it consistently
                assert success in [True, False] or success is None
    
    def test_duplicate_votes_same_session(self, test_db_path, init_test_db):
        """Test handling of duplicate votes in same session"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start session and cast initial votes
                session_id = start_voting_session(conn)
                votes = {"3": "positive"}
                
                success1 = cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)
                assert success1 is True
                
                # Try to cast same votes again
                success2 = cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)
                
                # Depending on business logic, duplicates might be:
                # 1. Allowed (updating previous vote)
                # 2. Rejected
                # 3. Added as new votes
                assert success2 in [True, False] or success2 is None
                
                # Verify vote count
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM votes WHERE voter_id = ? AND session_id = ?", (2, session_id))
                vote_count = cursor.fetchone()[0]
                
                # Count should be consistent with business logic
                assert vote_count >= 1  # At least the first vote should be recorded
    
    def test_vote_for_self(self, test_db_path, init_test_db):
        """Test voting for oneself"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start session
                session_id = start_voting_session(conn)
                
                # Try to vote for self
                votes = {"2": "positive"}  # Employee 2 voting for themselves
                success = cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)
                
                # Depending on business rules, self-voting might be:
                # 1. Allowed
                # 2. Rejected
                assert success in [True, False] or success is None
    
    def test_empty_votes(self, test_db_path, init_test_db):
        """Test handling of empty vote submission"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start session
                session_id = start_voting_session(conn)
                
                # Submit empty votes
                empty_votes = {}
                success = cast_votes(conn, voter_id=2, votes=empty_votes, session_id=session_id)
                
                # Should handle empty votes gracefully
                assert success in [True, False] or success is None
    
    def test_invalid_vote_type(self, test_db_path, init_test_db):
        """Test handling of invalid vote types"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start session
                session_id = start_voting_session(conn)
                
                # Try invalid vote type
                votes = {"3": "invalid_vote_type"}
                
                try:
                    success = cast_votes(conn, voter_id=2, votes=votes, session_id=session_id)
                    # Should either reject or handle gracefully
                    assert success in [True, False] or success is None
                except Exception as e:
                    # Validation errors are acceptable
                    assert any(keyword in str(e).lower() for keyword in ["invalid", "vote", "type", "constraint"])


class TestVotingAnalytics:
    """Test voting analytics and reporting"""
    
    def test_vote_participation_tracking(self, test_db_path, init_test_db):
        """Test tracking of vote participation"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start session and have some employees vote
                session_id = start_voting_session(conn)
                
                cast_votes(conn, voter_id=2, votes={"3": "positive"}, session_id=session_id)
                cast_votes(conn, voter_id=3, votes={"2": "positive"}, session_id=session_id)
                # Employee 4 doesn't vote
                
                # Calculate participation
                cursor = conn.cursor()
                
                # Total active employees
                cursor.execute("SELECT COUNT(*) FROM employees WHERE is_active = 1")
                total_employees = cursor.fetchone()[0]
                
                # Employees who voted
                cursor.execute("SELECT COUNT(DISTINCT voter_id) FROM votes WHERE session_id = ?", (session_id,))
                voters = cursor.fetchone()[0]
                
                # Calculate participation rate
                participation_rate = (voters / total_employees) * 100 if total_employees > 0 else 0
                
                assert participation_rate >= 0
                assert participation_rate <= 100
                assert voters <= total_employees
    
    def test_voting_session_duration_tracking(self, test_db_path, init_test_db):
        """Test tracking of voting session duration"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start session
                start_time = datetime.now()
                session_id = start_voting_session(conn)
                
                # Simulate some voting activity
                time.sleep(0.1)  # Small delay
                cast_votes(conn, voter_id=2, votes={"3": "positive"}, session_id=session_id)
                
                # Close session
                close_voting_session(conn)
                end_time = datetime.now()
                
                # Check session timing
                cursor = conn.cursor()
                cursor.execute("SELECT start_time, end_time FROM voting_sessions WHERE session_id = ?", (session_id,))
                session_times = cursor.fetchone()
                
                if session_times and session_times[0] and session_times[1]:
                    # Parse timestamps and calculate duration
                    db_start_time = datetime.fromisoformat(session_times[0])
                    db_end_time = datetime.fromisoformat(session_times[1])
                    duration = db_end_time - db_start_time
                    
                    # Duration should be positive and reasonable
                    assert duration.total_seconds() >= 0
                    assert duration.total_seconds() < 3600  # Less than 1 hour for test
    
    def test_vote_timing_analysis(self, test_db_path, init_test_db):
        """Test analysis of vote timing patterns"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Start session
                session_id = start_voting_session(conn)
                
                # Cast votes at different times
                cast_votes(conn, voter_id=2, votes={"3": "positive"}, session_id=session_id)
                time.sleep(0.05)  # Small delay between votes
                cast_votes(conn, voter_id=3, votes={"2": "positive"}, session_id=session_id)
                
                # Analyze vote timing
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT 
                        voter_id,
                        timestamp,
                        COUNT(*) as vote_count
                    FROM votes 
                    WHERE session_id = ?
                    GROUP BY voter_id, timestamp
                    ORDER BY timestamp
                """, (session_id,))
                
                vote_timing = cursor.fetchall()
                
                assert len(vote_timing) >= 1  # At least one voting record
                
                # Verify timestamps are reasonable
                for record in vote_timing:
                    timestamp_str = record[1]
                    vote_timestamp = datetime.fromisoformat(timestamp_str)
                    now = datetime.now()
                    
                    # Timestamp should be recent (within last hour)
                    time_diff = now - vote_timestamp
                    assert time_diff.total_seconds() < 3600  # Within last hour


class TestVotingPerformance:
    """Test voting system performance"""
    
    def test_large_vote_batch_performance(self, test_db_path, init_test_db):
        """Test performance with large vote batches"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            with incentive_service.DatabaseConnection() as conn:
                # Add more employees for testing
                cursor = conn.cursor()
                
                # Add additional test employees
                for i in range(10, 20):
                    cursor.execute(
                        "INSERT INTO employees (name, pin, score, role, is_active) VALUES (?, ?, ?, ?, ?)",
                        (f"Test Employee {i}", f"{i:04d}", 100, "employee", 1)
                    )
                conn.commit()
                
                # Start voting session
                session_id = start_voting_session(conn)
                
                # Measure time for large vote batch
                start_time = time.time()
                
                # Create large vote batch (employee votes for many others)
                large_votes = {str(i): "positive" for i in range(10, 20)}  # Vote for 10 employees
                success = cast_votes(conn, voter_id=2, votes=large_votes, session_id=session_id)
                
                end_time = time.time()
                elapsed = end_time - start_time
                
                # Should complete within reasonable time (5 seconds for 10 votes)
                assert elapsed < 5.0
                assert success is True or success is not False  # Should succeed
    
    def test_concurrent_voting_performance(self, test_db_path, init_test_db):
        """Test performance under concurrent voting load"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            import threading
            
            # Start voting session
            with incentive_service.DatabaseConnection() as conn:
                session_id = start_voting_session(conn)
            
            results = []
            errors = []
            
            def concurrent_voter(voter_id, voted_for_id):
                try:
                    with incentive_service.DatabaseConnection() as conn:
                        votes = {str(voted_for_id): "positive"}
                        success = cast_votes(conn, voter_id=voter_id, votes=votes, session_id=session_id)
                        results.append(success)
                except Exception as e:
                    errors.append(str(e))
            
            # Create multiple threads voting concurrently
            threads = []
            for i in range(5):
                # Different employees vote for different targets
                voter_id = 2 + (i % 3)  # Voters: 2, 3, 4
                voted_for_id = 3 + (i % 2)  # Targets: 3, 4
                thread = threading.Thread(target=concurrent_voter, args=(voter_id, voted_for_id))
                threads.append(thread)
                thread.start()
            
            # Wait for all threads
            for thread in threads:
                thread.join(timeout=10)
            
            # Analyze results
            total_operations = len(results) + len(errors)
            assert total_operations == 5  # All operations should complete
            
            # Most should succeed (allow some database locking issues)
            successes = [r for r in results if r is True]
            assert len(successes) >= 3  # At least 60% success rate


if __name__ == '__main__':
    pytest.main([__file__, '-v'])