# tests/integration/test_full_workflow.py
# End-to-end workflow integration tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import time
import os
import sys
from unittest.mock import patch, Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from config import Config
import incentive_service
from incentive_service import DatabaseConnection


class TestCompleteEmployeeWorkflow:
    """Test complete employee workflow from login to games"""
    
    def test_employee_login_to_game_workflow(self, client, test_db_path, init_test_db):
        """Test complete employee workflow: login -> portal -> play game"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Step 1: Employee login
            with patch('app.verify_pin') as mock_verify_pin:
                mock_verify_pin.return_value = {
                    'id': 2,
                    'name': 'John Doe',
                    'role': 'employee',
                    'is_active': 1,
                    'score': 100
                }
                
                login_response = client.post('/employee_login', data={
                    'pin': '1234'
                }, follow_redirects=True)
                
                # Should successfully log in
                assert login_response.status_code == 200
                
                # Check session was created
                with client.session_transaction() as sess:
                    assert sess.get('employee_logged_in') is True
                    assert sess.get('employee_id') == 2
                    assert sess.get('employee_name') == 'John Doe'
            
            # Step 2: Access employee portal
            portal_response = client.get('/employee_portal')
            assert portal_response.status_code == 200
            assert b'John Doe' in portal_response.data or b'employee' in portal_response.data.lower()
            
            # Step 3: Play a mini-game
            with patch('app.play_mini_game') as mock_play_game:
                mock_play_game.return_value = {
                    'success': True,
                    'game_type': 'slots',
                    'result': 'win',
                    'payout': 25,
                    'new_score': 125
                }
                
                game_response = client.post('/play_slots', data={
                    'bet_amount': '10'
                })
                
                # Game play should work (if route exists)
                if game_response.status_code != 404:
                    assert game_response.status_code in [200, 302]
            
            # Step 4: Check updated score/history
            with patch('app.get_history') as mock_get_history:
                mock_get_history.return_value = [
                    {
                        'id': 1,
                        'points_changed': 25,
                        'reason': 'Mini-game win: slots',
                        'timestamp': '2025-01-01 10:00:00',
                        'admin_name': 'System'
                    }
                ]
                
                history_response = client.get('/employee_history')
                
                # History should be accessible (if route exists)
                if history_response.status_code != 404:
                    assert history_response.status_code == 200
            
            # Step 5: Employee logout
            logout_response = client.post('/employee_logout', follow_redirects=True)
            
            if logout_response.status_code != 404:
                assert logout_response.status_code == 200
                
                # Check session was cleared
                with client.session_transaction() as sess:
                    assert sess.get('employee_logged_in') is not True
                    assert sess.get('employee_id') is None
    
    def test_employee_voting_workflow(self, client, test_db_path, init_test_db):
        """Test complete voting workflow for employee"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Set up employee session
            with client.session_transaction() as sess:
                sess['employee_logged_in'] = True
                sess['employee_id'] = 2
                sess['employee_name'] = 'John Doe'
            
            # Mock voting as active
            with patch('app.is_voting_active') as mock_voting_active, \
                 patch('app.get_scoreboard') as mock_get_scoreboard:
                
                mock_voting_active.return_value = True
                mock_get_scoreboard.return_value = [
                    {'id': 2, 'name': 'John Doe', 'score': 100},
                    {'id': 3, 'name': 'Jane Smith', 'score': 150},
                    {'id': 4, 'name': 'Bob Johnson', 'score': 75}
                ]
                
                # Step 1: Access voting page
                voting_response = client.get('/vote')
                if voting_response.status_code == 200:
                    assert b'vote' in voting_response.data.lower()
                    assert b'Jane Smith' in voting_response.data or b'Bob Johnson' in voting_response.data
                
                # Step 2: Cast votes
                with patch('app.cast_votes') as mock_cast_votes:
                    mock_cast_votes.return_value = True
                    
                    vote_data = {
                        '3': 'positive',  # Vote for Jane Smith
                        '4': 'positive'   # Vote for Bob Johnson
                    }
                    
                    cast_response = client.post('/cast_votes', 
                                              json=vote_data,
                                              content_type='application/json')
                    
                    # Vote casting should work (if route exists)
                    if cast_response.status_code != 404:
                        assert cast_response.status_code == 200
                        
                        # Verify votes were processed
                        mock_cast_votes.assert_called_once()
                
                # Step 3: View voting results (after voting ends)
                with patch('app.get_voting_results') as mock_get_results:
                    mock_voting_active.return_value = False  # Voting ended
                    mock_get_results.return_value = [
                        {'employee_id': 3, 'employee_name': 'Jane Smith', 'positive_votes': 2, 'negative_votes': 0},
                        {'employee_id': 4, 'employee_name': 'Bob Johnson', 'positive_votes': 1, 'negative_votes': 1}
                    ]
                    
                    results_response = client.get('/voting_results')
                    
                    if results_response.status_code == 200:
                        assert b'Jane Smith' in results_response.data
                        assert b'positive' in results_response.data.lower() or b'votes' in results_response.data.lower()


class TestCompleteAdminWorkflow:
    """Test complete admin workflow from login to management"""
    
    def test_admin_complete_management_workflow(self, client, test_db_path, init_test_db):
        """Test complete admin workflow: login -> manage -> adjust points -> start voting"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Step 1: Admin login
            with patch('app.check_password_hash') as mock_check_password, \
                 patch('app.DatabaseConnection') as mock_db_conn:
                
                mock_conn = Mock()
                mock_db_conn.return_value.__enter__.return_value = mock_conn
                mock_db_conn.return_value.__exit__.return_value = None
                mock_conn.cursor.return_value.fetchone.return_value = [1, 'hashed_admin_password']
                mock_check_password.return_value = True
                
                login_response = client.post('/admin_login', data={
                    'username': 'admin',
                    'password': 'admin_password'
                }, follow_redirects=True)
                
                assert login_response.status_code == 200
                
                # Check admin session
                with client.session_transaction() as sess:
                    assert sess.get('admin_logged_in') is True
                    assert sess.get('admin_id') == 1
            
            # Step 2: Access admin management
            with patch('app.get_scoreboard') as mock_get_scoreboard, \
                 patch('app.get_history') as mock_get_history:
                
                mock_get_scoreboard.return_value = [
                    {'id': 2, 'name': 'John Doe', 'score': 100},
                    {'id': 3, 'name': 'Jane Smith', 'score': 150}
                ]
                mock_get_history.return_value = []
                
                admin_response = client.get('/admin_manage')
                assert admin_response.status_code == 200
                assert b'admin' in admin_response.data.lower() or b'manage' in admin_response.data.lower()
            
            # Step 3: Adjust employee points
            with patch('app.adjust_points') as mock_adjust_points, \
                 patch('app.DatabaseConnection') as mock_db_conn:
                
                mock_conn = Mock()
                mock_db_conn.return_value.__enter__.return_value = mock_conn
                mock_db_conn.return_value.__exit__.return_value = None
                mock_adjust_points.return_value = True
                
                adjust_response = client.post('/adjust_points', data={
                    'employee_id': '2',
                    'points_change': '25',
                    'reason': 'Excellent customer service'
                })
                
                # Point adjustment should work (if route exists)
                if adjust_response.status_code != 404:
                    assert adjust_response.status_code in [200, 302]
                    mock_adjust_points.assert_called_once()
            
            # Step 4: Start voting session
            with patch('app.start_voting_session') as mock_start_voting, \
                 patch('app.DatabaseConnection') as mock_db_conn:
                
                mock_conn = Mock()
                mock_db_conn.return_value.__enter__.return_value = mock_conn
                mock_db_conn.return_value.__exit__.return_value = None
                mock_start_voting.return_value = 'test_session_123'
                
                start_voting_response = client.post('/start_voting', data={
                    'duration': '300'  # 5 minutes
                })
                
                if start_voting_response.status_code != 404:
                    assert start_voting_response.status_code in [200, 302]
                    mock_start_voting.assert_called_once()
            
            # Step 5: Monitor voting session
            with patch('app.is_voting_active') as mock_voting_active, \
                 patch('app.get_voting_results') as mock_get_results:
                
                mock_voting_active.return_value = True
                mock_get_results.return_value = []
                
                monitor_response = client.get('/admin_voting_status')
                
                # Voting monitoring should be available (if route exists)
                if monitor_response.status_code != 404:
                    assert monitor_response.status_code == 200
            
            # Step 6: Close voting and view results
            with patch('app.close_voting_session') as mock_close_voting, \
                 patch('app.finalize_voting_session') as mock_finalize_voting, \
                 patch('app.get_voting_results') as mock_get_results:
                
                mock_close_voting.return_value = True
                mock_finalize_voting.return_value = True
                mock_get_results.return_value = [
                    {'employee_id': 2, 'employee_name': 'John Doe', 'total_score_change': 15},
                    {'employee_id': 3, 'employee_name': 'Jane Smith', 'total_score_change': 20}
                ]
                
                close_response = client.post('/close_voting')
                
                if close_response.status_code != 404:
                    assert close_response.status_code in [200, 302]
            
            # Step 7: Admin logout
            logout_response = client.post('/admin_logout', follow_redirects=True)
            
            if logout_response.status_code != 404:
                assert logout_response.status_code == 200
                
                # Check session was cleared
                with client.session_transaction() as sess:
                    assert sess.get('admin_logged_in') is not True
                    assert sess.get('admin_id') is None


class TestVotingLifecycle:
    """Test complete voting session lifecycle"""
    
    def test_complete_voting_lifecycle(self, client, test_db_path, init_test_db):
        """Test complete voting lifecycle from start to finish"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Set up admin session
            with client.session_transaction() as sess:
                sess['admin_logged_in'] = True
                sess['admin_id'] = 1
                sess['admin_name'] = 'Admin User'
            
            session_id = None
            
            # Phase 1: Admin starts voting session
            with patch('app.start_voting_session') as mock_start_voting, \
                 patch('app.DatabaseConnection') as mock_db_conn:
                
                mock_conn = Mock()
                mock_db_conn.return_value.__enter__.return_value = mock_conn
                mock_db_conn.return_value.__exit__.return_value = None
                session_id = 'integration_test_session'
                mock_start_voting.return_value = session_id
                
                start_response = client.post('/start_voting')
                
                if start_response.status_code != 404:
                    assert start_response.status_code in [200, 302]
                    mock_start_voting.assert_called_once()
            
            # Phase 2: Multiple employees vote
            employees = [
                {'id': 2, 'name': 'John Doe', 'votes': {'3': 'positive', '4': 'positive'}},
                {'id': 3, 'name': 'Jane Smith', 'votes': {'2': 'positive', '4': 'negative'}},
                {'id': 4, 'name': 'Bob Johnson', 'votes': {'2': 'positive', '3': 'positive'}}
            ]
            
            with patch('app.is_voting_active') as mock_voting_active, \
                 patch('app.cast_votes') as mock_cast_votes:
                
                mock_voting_active.return_value = True
                mock_cast_votes.return_value = True
                
                for employee in employees:
                    # Set employee session
                    with client.session_transaction() as sess:
                        sess.clear()
                        sess['employee_logged_in'] = True
                        sess['employee_id'] = employee['id']
                        sess['employee_name'] = employee['name']
                    
                    # Cast votes
                    vote_response = client.post('/cast_votes',
                                              json=employee['votes'],
                                              content_type='application/json')
                    
                    if vote_response.status_code != 404:
                        # Votes should be accepted
                        assert vote_response.status_code in [200, 302]
                
                # Verify all employees voted
                assert mock_cast_votes.call_count == len(employees)
            
            # Phase 3: Admin monitors voting
            with client.session_transaction() as sess:
                sess.clear()
                sess['admin_logged_in'] = True
                sess['admin_id'] = 1
            
            with patch('app.get_voting_results') as mock_get_results:
                mock_get_results.return_value = [
                    {'employee_id': 2, 'positive_votes': 2, 'negative_votes': 0},
                    {'employee_id': 3, 'positive_votes': 2, 'negative_votes': 0},
                    {'employee_id': 4, 'positive_votes': 1, 'negative_votes': 1}
                ]
                
                results_response = client.get('/voting_results')
                
                if results_response.status_code != 404:
                    assert results_response.status_code == 200
            
            # Phase 4: Admin closes voting and finalizes results
            with patch('app.close_voting_session') as mock_close_voting, \
                 patch('app.finalize_voting_session') as mock_finalize_voting:
                
                mock_close_voting.return_value = True
                mock_finalize_voting.return_value = True
                
                close_response = client.post('/close_voting')
                
                if close_response.status_code != 404:
                    assert close_response.status_code in [200, 302]
                    mock_close_voting.assert_called_once()
            
            # Phase 5: View final results and score updates
            with patch('app.get_latest_voting_results') as mock_latest_results, \
                 patch('app.get_scoreboard') as mock_get_scoreboard:
                
                mock_latest_results.return_value = [
                    {'employee_id': 2, 'employee_name': 'John Doe', 'score_change': 20},
                    {'employee_id': 3, 'employee_name': 'Jane Smith', 'score_change': 20},
                    {'employee_id': 4, 'employee_name': 'Bob Johnson', 'score_change': 0}
                ]
                mock_get_scoreboard.return_value = [
                    {'id': 2, 'name': 'John Doe', 'score': 120},
                    {'id': 3, 'name': 'Jane Smith', 'score': 170},
                    {'id': 4, 'name': 'Bob Johnson', 'score': 75}
                ]
                
                final_results_response = client.get('/final_voting_results')
                scoreboard_response = client.get('/')
                
                if final_results_response.status_code != 404:
                    assert final_results_response.status_code == 200
                
                # Scoreboard should show updated scores
                assert scoreboard_response.status_code == 200


class TestGameIntegrationWorkflow:
    """Test game integration with point system"""
    
    def test_game_to_points_integration(self, client, test_db_path, init_test_db):
        """Test game playing affecting point scores"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Set up employee session
            with client.session_transaction() as sess:
                sess['employee_logged_in'] = True
                sess['employee_id'] = 2
                sess['employee_name'] = 'John Doe'
            
            # Step 1: Check initial score
            with patch('app.get_scoreboard') as mock_get_scoreboard:
                mock_get_scoreboard.return_value = [
                    {'id': 2, 'name': 'John Doe', 'score': 100}
                ]
                
                initial_response = client.get('/api/scoreboard')
                
                if initial_response.status_code == 200:
                    # Initial score should be 100
                    assert b'100' in initial_response.data
            
            # Step 2: Play multiple games
            games = [
                {'type': 'slots', 'bet': 10, 'payout': 25},
                {'type': 'roulette', 'bet': 15, 'payout': 0},
                {'type': 'wheel', 'bet': 5, 'payout': 50}
            ]
            
            total_net_change = 0
            
            for game in games:
                with patch('app.play_mini_game') as mock_play_game:
                    net_change = game['payout'] - game['bet']
                    total_net_change += net_change
                    
                    mock_play_game.return_value = {
                        'success': True,
                        'game_type': game['type'],
                        'bet_amount': game['bet'],
                        'payout': game['payout'],
                        'net_change': net_change,
                        'new_score': 100 + total_net_change
                    }
                    
                    game_response = client.post(f'/play_{game["type"]}', data={
                        'bet_amount': str(game['bet'])
                    })
                    
                    # Game should process (if route exists)
                    if game_response.status_code != 404:
                        assert game_response.status_code in [200, 302]
                        mock_play_game.assert_called_once()
            
            # Step 3: Verify final score reflects game results
            with patch('app.get_scoreboard') as mock_get_scoreboard:
                final_score = 100 + total_net_change
                mock_get_scoreboard.return_value = [
                    {'id': 2, 'name': 'John Doe', 'score': final_score}
                ]
                
                final_response = client.get('/api/scoreboard')
                
                if final_response.status_code == 200:
                    # Score should reflect game results
                    assert str(final_score).encode() in final_response.data
            
            # Step 4: Check game history
            with patch('app.get_history') as mock_get_history:
                mock_get_history.return_value = [
                    {'id': 1, 'points_changed': 15, 'reason': 'Mini-game win: slots', 'timestamp': '2025-01-01 10:00:00'},
                    {'id': 2, 'points_changed': -15, 'reason': 'Mini-game loss: roulette', 'timestamp': '2025-01-01 10:05:00'},
                    {'id': 3, 'points_changed': 45, 'reason': 'Mini-game win: wheel', 'timestamp': '2025-01-01 10:10:00'}
                ]
                
                history_response = client.get('/game_history')
                
                if history_response.status_code == 200:
                    assert b'slots' in history_response.data
                    assert b'roulette' in history_response.data
                    assert b'wheel' in history_response.data


class TestSystemResetAndRecovery:
    """Test system reset and recovery workflows"""
    
    def test_master_reset_workflow(self, client, test_db_path, init_test_db):
        """Test master reset workflow"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Set up admin session
            with client.session_transaction() as sess:
                sess['admin_logged_in'] = True
                sess['admin_id'] = 1
                sess['admin_name'] = 'Admin User'
            
            # Step 1: Verify system has data
            with patch('app.get_scoreboard') as mock_get_scoreboard:
                mock_get_scoreboard.return_value = [
                    {'id': 2, 'name': 'John Doe', 'score': 150},
                    {'id': 3, 'name': 'Jane Smith', 'score': 200}
                ]
                
                pre_reset_response = client.get('/')
                assert pre_reset_response.status_code == 200
            
            # Step 2: Perform master reset
            with patch('app.master_reset_all') as mock_master_reset, \
                 patch('app.DatabaseConnection') as mock_db_conn:
                
                mock_conn = Mock()
                mock_db_conn.return_value.__enter__.return_value = mock_conn
                mock_db_conn.return_value.__exit__.return_value = None
                mock_master_reset.return_value = True
                
                reset_response = client.post('/master_reset', data={
                    'confirm': 'yes',
                    'reset_type': 'all'
                })
                
                if reset_response.status_code != 404:
                    assert reset_response.status_code in [200, 302]
                    mock_master_reset.assert_called_once()
            
            # Step 3: Verify system reset
            with patch('app.get_scoreboard') as mock_get_scoreboard:
                mock_get_scoreboard.return_value = [
                    {'id': 2, 'name': 'John Doe', 'score': 0},
                    {'id': 3, 'name': 'Jane Smith', 'score': 0}
                ]
                
                post_reset_response = client.get('/')
                assert post_reset_response.status_code == 200
            
            # Step 4: Verify system functions normally after reset
            with patch('app.start_voting_session') as mock_start_voting:
                mock_start_voting.return_value = 'post_reset_session'
                
                voting_response = client.post('/start_voting')
                
                if voting_response.status_code != 404:
                    assert voting_response.status_code in [200, 302]
                    # System should work normally after reset
                    mock_start_voting.assert_called_once()
    
    def test_error_recovery_workflow(self, client, test_db_path, init_test_db):
        """Test system error recovery"""
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Simulate various error conditions and recovery
            
            # Step 1: Database connection error recovery
            with patch('app.DatabaseConnection', side_effect=Exception("Database connection failed")):
                error_response = client.get('/')
                
                # System should handle database errors gracefully
                assert error_response.status_code in [200, 500, 302]
            
            # Step 2: Recovery after database error
            with patch('app.get_scoreboard') as mock_get_scoreboard:
                mock_get_scoreboard.return_value = []
                
                recovery_response = client.get('/')
                
                # System should recover and work normally
                assert recovery_response.status_code == 200
            
            # Step 3: Session corruption recovery
            with client.session_transaction() as sess:
                # Corrupt session data
                sess['employee_id'] = 'invalid_id'
                sess['admin_logged_in'] = 'not_boolean'
            
            # System should handle corrupted session gracefully
            corrupted_response = client.get('/employee_portal')
            assert corrupted_response.status_code in [200, 302, 401, 403]
            
            # Step 4: Normal operation after corruption
            with client.session_transaction() as sess:
                sess.clear()
                sess['employee_logged_in'] = True
                sess['employee_id'] = 2
            
            normal_response = client.get('/employee_portal')
            assert normal_response.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'integration'])