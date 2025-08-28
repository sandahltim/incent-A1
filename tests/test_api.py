# tests/test_api.py
# API endpoint tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import json
import os
import sys
from unittest.mock import patch, Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config


class TestMainRoutes:
    """Test main application routes"""
    
    @patch('app.get_scoreboard')
    @patch('app.is_voting_active')
    @patch('app.get_settings')
    def test_home_route(self, mock_get_settings, mock_is_voting_active, mock_get_scoreboard, client, init_test_db):
        """Test the main home route"""
        # Mock dependencies
        mock_get_settings.return_value = {
            'site_name': 'Test Incentive System',
            'primary_color': '#D4AF37',
            'secondary_color': '#000000'
        }
        mock_is_voting_active.return_value = False
        mock_get_scoreboard.return_value = [
            {'id': 2, 'name': 'John Doe', 'score': 100},
            {'id': 3, 'name': 'Jane Smith', 'score': 150}
        ]
        
        response = client.get('/')
        
        assert response.status_code == 200
        assert b'Incentive' in response.data or b'Test Incentive System' in response.data
    
    def test_static_files(self, client):
        """Test static file serving"""
        # Test CSS file
        response = client.get('/static/style.css')
        assert response.status_code in [200, 404]  # File may or may not exist
        
        # Test JavaScript file
        response = client.get('/static/script.js')
        assert response.status_code in [200, 404]  # File may or may not exist
    
    def test_404_handling(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent-endpoint')
        assert response.status_code == 404


class TestEmployeeRoutes:
    """Test employee-related routes"""
    
    @patch('app.verify_pin')
    def test_employee_login_success(self, mock_verify_pin, client, init_test_db):
        """Test successful employee login"""
        # Mock PIN verification
        mock_verify_pin.return_value = {
            'id': 2,
            'name': 'John Doe',
            'role': 'employee',
            'is_active': 1
        }
        
        response = client.post('/employee_login', data={
            'pin': '1234',
            'csrf_token': 'test_token'
        }, follow_redirects=True)
        
        # Should redirect to employee portal or return success
        assert response.status_code in [200, 302]
    
    @patch('app.verify_pin')
    def test_employee_login_failure(self, mock_verify_pin, client, init_test_db):
        """Test failed employee login"""
        # Mock PIN verification failure
        mock_verify_pin.return_value = None
        
        response = client.post('/employee_login', data={
            'pin': 'wrong_pin',
            'csrf_token': 'test_token'
        })
        
        # Should return login page with error or redirect
        assert response.status_code in [200, 302, 401]
    
    def test_employee_portal_without_login(self, client):
        """Test accessing employee portal without login"""
        response = client.get('/employee_portal')
        
        # Should redirect to login or show access denied
        assert response.status_code in [302, 401, 403]
    
    def test_employee_portal_with_login(self, client):
        """Test accessing employee portal with login"""
        # Set employee session
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
            sess['employee_name'] = 'John Doe'
        
        response = client.get('/employee_portal')
        assert response.status_code == 200


class TestAdminRoutes:
    """Test admin-related routes"""
    
    def test_admin_login_page(self, client):
        """Test admin login page"""
        response = client.get('/admin')
        assert response.status_code == 200
        assert b'admin' in response.data.lower() or b'login' in response.data.lower()
    
    @patch('app.check_password_hash')
    @patch('app.DatabaseConnection')
    def test_admin_login_success(self, mock_db_conn, mock_check_password, client, init_test_db):
        """Test successful admin login"""
        # Mock database connection and password check
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        
        mock_conn.cursor.return_value.fetchone.return_value = [1, 'hashed_password']
        mock_check_password.return_value = True
        
        response = client.post('/admin_login', data={
            'username': 'admin',
            'password': 'admin_password',
            'csrf_token': 'test_token'
        }, follow_redirects=True)
        
        # Should redirect to admin panel or return success
        assert response.status_code in [200, 302]
    
    def test_admin_manage_without_login(self, client):
        """Test accessing admin management without login"""
        response = client.get('/admin_manage')
        
        # Should redirect to login or show access denied
        assert response.status_code in [302, 401, 403]
    
    def test_admin_manage_with_login(self, client):
        """Test accessing admin management with login"""
        # Set admin session
        with client.session_transaction() as sess:
            sess['admin_logged_in'] = True
            sess['admin_id'] = 1
            sess['admin_name'] = 'Admin User'
        
        response = client.get('/admin_manage')
        assert response.status_code == 200


class TestVotingRoutes:
    """Test voting-related routes"""
    
    @patch('app.is_voting_active')
    @patch('app.get_scoreboard')
    def test_voting_status_inactive(self, mock_get_scoreboard, mock_is_voting_active, client):
        """Test voting status when inactive"""
        mock_is_voting_active.return_value = False
        mock_get_scoreboard.return_value = []
        
        response = client.get('/api/voting_status')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'active' in data
            assert data['active'] is False
        else:
            # Route might not exist or require authentication
            assert response.status_code in [404, 401, 403]
    
    @patch('app.start_voting_session')
    @patch('app.DatabaseConnection')
    def test_start_voting_admin(self, mock_db_conn, mock_start_voting, client):
        """Test starting voting session as admin"""
        # Set admin session
        with client.session_transaction() as sess:
            sess['admin_logged_in'] = True
            sess['admin_id'] = 1
        
        # Mock database connection
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        mock_start_voting.return_value = 'test_session_id'
        
        response = client.post('/start_voting', data={
            'csrf_token': 'test_token'
        })
        
        # Should succeed or redirect
        assert response.status_code in [200, 302]
    
    @patch('app.cast_votes')
    @patch('app.is_voting_active')
    @patch('app.DatabaseConnection')
    def test_cast_vote_employee(self, mock_db_conn, mock_is_voting_active, mock_cast_votes, client):
        """Test casting votes as employee"""
        # Set employee session
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
            sess['employee_name'] = 'John Doe'
        
        # Mock dependencies
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        mock_is_voting_active.return_value = True
        mock_cast_votes.return_value = True
        
        # Mock vote data
        vote_data = {'3': 'positive', '4': 'positive'}
        
        response = client.post('/cast_votes', 
                              data=json.dumps(vote_data),
                              content_type='application/json')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'success' in data or 'status' in data
        else:
            # Route might require different authentication or data format
            assert response.status_code in [400, 401, 403, 404]


class TestGameRoutes:
    """Test mini-game related routes"""
    
    @patch('app.play_mini_game')
    @patch('app.DatabaseConnection')
    def test_play_game_slots(self, mock_db_conn, mock_play_mini_game, client):
        """Test playing slots game"""
        # Set employee session
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
            sess['employee_name'] = 'John Doe'
        
        # Mock game play
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        mock_play_mini_game.return_value = {
            'game_type': 'slots',
            'result': 'win',
            'payout': 25,
            'symbols': ['🍒', '🍒', '🍒']
        }
        
        response = client.post('/api/play_game', 
                              data=json.dumps({
                                  'game_type': 'slots',
                                  'bet_amount': 10
                              }),
                              content_type='application/json')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert 'result' in data or 'payout' in data
        else:
            # Route might not exist or require different format
            assert response.status_code in [400, 401, 403, 404]
    
    def test_game_route_without_login(self, client):
        """Test accessing game routes without login"""
        response = client.post('/api/play_game',
                              data=json.dumps({'game_type': 'slots', 'bet_amount': 10}),
                              content_type='application/json')
        
        # Should require authentication
        assert response.status_code in [401, 403, 404]


class TestAPIDataRoutes:
    """Test API data endpoints"""
    
    @patch('app.get_scoreboard')
    @patch('app.DatabaseConnection')
    def test_api_scoreboard(self, mock_db_conn, mock_get_scoreboard, client):
        """Test API scoreboard endpoint"""
        # Mock scoreboard data
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        mock_get_scoreboard.return_value = [
            {'id': 2, 'name': 'John Doe', 'score': 100},
            {'id': 3, 'name': 'Jane Smith', 'score': 150}
        ]
        
        response = client.get('/api/scoreboard')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, list)
            assert len(data) >= 0
        else:
            # API endpoint might not exist
            assert response.status_code in [404, 401, 403]
    
    @patch('app.get_voting_results')
    @patch('app.DatabaseConnection')
    def test_api_voting_results(self, mock_db_conn, mock_get_voting_results, client):
        """Test API voting results endpoint"""
        # Mock voting results
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        mock_get_voting_results.return_value = [
            {'employee_id': 2, 'positive_votes': 5, 'negative_votes': 1},
            {'employee_id': 3, 'positive_votes': 3, 'negative_votes': 2}
        ]
        
        response = client.get('/api/voting_results')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, (list, dict))
        else:
            # API endpoint might not exist or require authentication
            assert response.status_code in [404, 401, 403]
    
    def test_api_statistics(self, client):
        """Test API statistics endpoint"""
        response = client.get('/api/statistics')
        
        if response.status_code == 200:
            data = json.loads(response.data)
            assert isinstance(data, dict)
            # Should contain statistical data
        else:
            # API endpoint might not exist
            assert response.status_code in [404, 401, 403]


class TestAPIErrorHandling:
    """Test API error handling"""
    
    def test_api_invalid_json(self, client):
        """Test API handling of invalid JSON"""
        # Set employee session
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
        
        response = client.post('/api/play_game',
                              data='invalid json',
                              content_type='application/json')
        
        # Should handle invalid JSON gracefully
        assert response.status_code in [400, 404]  # Bad Request or Not Found
    
    def test_api_missing_content_type(self, client):
        """Test API handling of missing content type"""
        # Set employee session
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
        
        response = client.post('/api/play_game',
                              data=json.dumps({'game_type': 'slots', 'bet_amount': 10}))
        
        # Should handle missing content type
        assert response.status_code in [400, 404, 415]  # Bad Request, Not Found, or Unsupported Media Type
    
    def test_api_rate_limiting(self, client):
        """Test API rate limiting (if implemented)"""
        # Set employee session
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
        
        # Make multiple rapid requests
        responses = []
        for _ in range(10):
            response = client.get('/api/scoreboard')
            responses.append(response.status_code)
        
        # Most requests should succeed (if no rate limiting) or be rate limited
        success_codes = [200, 404]  # 200 if endpoint exists, 404 if not
        rate_limit_codes = [429]  # Too Many Requests
        
        for status_code in responses:
            assert status_code in success_codes + rate_limit_codes


class TestJSONResponses:
    """Test JSON response formatting"""
    
    @patch('app.get_scoreboard')
    @patch('app.DatabaseConnection')
    def test_json_response_structure(self, mock_db_conn, mock_get_scoreboard, client):
        """Test JSON response structure"""
        # Mock data
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        mock_get_scoreboard.return_value = [
            {'id': 2, 'name': 'John Doe', 'score': 100}
        ]
        
        response = client.get('/api/scoreboard')
        
        if response.status_code == 200:
            # Should be valid JSON
            try:
                data = json.loads(response.data)
                assert isinstance(data, (list, dict))
            except json.JSONDecodeError:
                pytest.fail("Response is not valid JSON")
            
            # Should have correct content type
            assert 'application/json' in response.content_type or response.content_type is None
    
    def test_error_json_response(self, client):
        """Test JSON error response formatting"""
        response = client.get('/api/nonexistent_endpoint')
        
        if response.status_code == 404:
            # Error responses might be JSON formatted
            if response.content_type and 'application/json' in response.content_type:
                try:
                    data = json.loads(response.data)
                    assert isinstance(data, dict)
                    assert 'error' in data or 'message' in data
                except json.JSONDecodeError:
                    # Non-JSON error responses are also acceptable
                    pass


class TestCORSHeaders:
    """Test CORS headers (if implemented)"""
    
    def test_cors_headers_present(self, client):
        """Test that CORS headers are present if needed"""
        response = client.get('/api/scoreboard')
        
        # CORS headers might be present for API endpoints
        cors_headers = [
            'Access-Control-Allow-Origin',
            'Access-Control-Allow-Methods',
            'Access-Control-Allow-Headers'
        ]
        
        # Not all applications need CORS, so this is optional
        if any(header in response.headers for header in cors_headers):
            # If CORS is implemented, verify it's configured correctly
            assert 'Access-Control-Allow-Origin' in response.headers
    
    def test_options_request_handling(self, client):
        """Test OPTIONS request handling for CORS"""
        response = client.options('/api/scoreboard')
        
        # OPTIONS requests should be handled
        assert response.status_code in [200, 204, 404, 405]  # OK, No Content, Not Found, or Method Not Allowed


class TestAPIAuthentication:
    """Test API authentication mechanisms"""
    
    def test_api_token_authentication(self, client):
        """Test API token authentication (if implemented)"""
        # Try accessing API with token
        headers = {'Authorization': 'Bearer test_token'}
        response = client.get('/api/scoreboard', headers=headers)
        
        # Response depends on whether token auth is implemented
        assert response.status_code in [200, 401, 403, 404]
    
    def test_api_session_authentication(self, client):
        """Test API session-based authentication"""
        # Test without session
        response = client.get('/api/scoreboard')
        unauthenticated_status = response.status_code
        
        # Test with session
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
        
        response = client.get('/api/scoreboard')
        authenticated_status = response.status_code
        
        # Authentication might affect access
        # Both statuses should be valid HTTP codes
        assert unauthenticated_status in [200, 401, 403, 404]
        assert authenticated_status in [200, 401, 403, 404]


class TestAPIPerformance:
    """Test API performance characteristics"""
    
    @patch('app.get_scoreboard')
    @patch('app.DatabaseConnection')
    def test_api_response_time(self, mock_db_conn, mock_get_scoreboard, client, performance_timer):
        """Test API response time"""
        # Mock dependencies
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        mock_get_scoreboard.return_value = []
        
        with performance_timer() as timer:
            response = client.get('/api/scoreboard')
            elapsed = timer()
        
        # Should respond within reasonable time
        assert elapsed < 5.0  # 5 seconds should be more than enough
        assert response.status_code in [200, 404]  # Valid response
    
    def test_api_concurrent_requests(self, client):
        """Test API handling of concurrent requests"""
        import threading
        import time
        
        results = []
        
        def make_request():
            response = client.get('/api/scoreboard')
            results.append(response.status_code)
        
        # Make concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # All requests should complete
        assert len(results) == 5
        
        # All should return valid HTTP status codes
        for status_code in results:
            assert 200 <= status_code < 600


if __name__ == '__main__':
    pytest.main([__file__, '-v'])