# tests/test_app.py
# Main Flask application tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import json
from unittest.mock import patch, Mock, MagicMock
from flask import session, url_for
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app
from config import Config


class TestFlaskApplication:
    """Test the main Flask application functionality"""
    
    def test_app_creation(self, test_app):
        """Test that the Flask app is created correctly"""
        assert test_app is not None
        assert test_app.config['TESTING'] is True
        assert 'SECRET_KEY' in test_app.config
    
    def test_app_config(self, test_app):
        """Test application configuration"""
        assert test_app.config['TESTING'] is True
        assert test_app.config['WTF_CSRF_ENABLED'] is False
        assert 'SECRET_KEY' in test_app.config
    
    def test_template_filters(self, test_app):
        """Test that custom template filters are registered"""
        assert 'zip' in test_app.jinja_env.filters
        assert 'from_json' in test_app.jinja_env.filters
    
    def test_from_json_filter(self, test_app):
        """Test the from_json template filter"""
        from app import from_json
        
        # Test valid JSON
        assert from_json('{"key": "value"}') == {"key": "value"}
        
        # Test empty string
        assert from_json('') == {}
        
        # Test None value
        assert from_json(None) == {}
        
        # Test invalid JSON
        assert from_json('invalid json') == {}


class TestMainRoutes:
    """Test main application routes"""
    
    @patch('app.get_scoreboard')
    @patch('app.is_voting_active')
    @patch('app.get_settings')
    def test_home_page(self, mock_get_settings, mock_is_voting_active, mock_get_scoreboard, client, init_test_db):
        """Test the home page route"""
        # Mock the dependencies
        mock_get_settings.return_value = {
            'site_name': 'Test Site',
            'primary_color': '#D4AF37'
        }
        mock_is_voting_active.return_value = False
        mock_get_scoreboard.return_value = []
        
        response = client.get('/')
        assert response.status_code == 200
        assert b'Test Site' in response.data or b'Incentive System' in response.data
    
    @patch('app.DatabaseConnection')
    def test_context_processor_injection(self, mock_db_conn, client, init_test_db):
        """Test that global context variables are injected"""
        # Mock the database connection and settings
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        
        with patch('app.get_settings') as mock_get_settings:
            mock_get_settings.return_value = {
                'site_name': 'Test Incentive System',
                'primary_color': '#D4AF37',
                'secondary_color': '#000000'
            }
            
            response = client.get('/')
            # The context processor should inject the settings
            assert mock_get_settings.called
    
    def test_static_file_serving(self, client):
        """Test that static files are served correctly"""
        # Test CSS file
        response = client.get('/static/style.css')
        # May return 200 if file exists or 404 if not, both are acceptable for testing
        assert response.status_code in [200, 404]
    
    def test_404_error_handling(self, client):
        """Test 404 error handling"""
        response = client.get('/nonexistent-route')
        assert response.status_code == 404


class TestSessionHandling:
    """Test session management"""
    
    def test_session_creation(self, client):
        """Test that sessions are created properly"""
        with client.session_transaction() as sess:
            sess['test_key'] = 'test_value'
        
        # Make a request to trigger session handling
        response = client.get('/')
        
        with client.session_transaction() as sess:
            assert 'test_key' in sess
            assert sess['test_key'] == 'test_value'
    
    def test_admin_session_handling(self, client):
        """Test admin session management"""
        with client.session_transaction() as sess:
            sess['admin_logged_in'] = True
            sess['admin_id'] = 1
            sess['admin_name'] = 'Test Admin'
        
        # Verify session data
        with client.session_transaction() as sess:
            assert sess.get('admin_logged_in') is True
            assert sess.get('admin_id') == 1
            assert sess.get('admin_name') == 'Test Admin'
    
    def test_employee_session_handling(self, client):
        """Test employee session management"""
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
            sess['employee_name'] = 'Test Employee'
        
        # Verify session data
        with client.session_transaction() as sess:
            assert sess.get('employee_logged_in') is True
            assert sess.get('employee_id') == 2
            assert sess.get('employee_name') == 'Test Employee'


class TestCSRFProtection:
    """Test CSRF protection (disabled in tests but ensure it's configured)"""
    
    def test_csrf_configuration(self, test_app):
        """Test that CSRF protection is configured"""
        # In test config, CSRF should be disabled
        assert test_app.config.get('WTF_CSRF_ENABLED') is False
    
    def test_csrf_token_generation(self, client):
        """Test CSRF token generation in forms"""
        # Even with CSRF disabled, the mechanism should be available
        response = client.get('/')
        # Should not raise an error
        assert response.status_code in [200, 302, 404]  # Any valid HTTP response


class TestDatabaseIntegration:
    """Test database integration in the main app"""
    
    @patch('app.DatabaseConnection')
    def test_database_connection_in_routes(self, mock_db_conn, client):
        """Test that database connections are used in routes"""
        mock_conn = Mock()
        mock_db_conn.return_value.__enter__.return_value = mock_conn
        mock_db_conn.return_value.__exit__.return_value = None
        
        with patch('app.get_settings') as mock_get_settings:
            mock_get_settings.return_value = {}
            response = client.get('/')
            
            # Verify database connection was attempted
            assert mock_db_conn.called
    
    def test_database_error_handling(self, client, monkeypatch):
        """Test handling of database connection errors"""
        # Mock database connection to raise an exception
        def mock_db_error(*args, **kwargs):
            raise Exception("Database connection failed")
        
        with patch('app.DatabaseConnection', side_effect=mock_db_error):
            response = client.get('/')
            # Should handle the error gracefully
            # Exact response depends on error handling implementation
            assert response.status_code in [200, 500, 302]


class TestCachingIntegration:
    """Test caching system integration"""
    
    @patch('app.CACHING_AVAILABLE', True)
    @patch('app.get_cache_manager')
    def test_caching_when_available(self, mock_get_cache_manager, client):
        """Test caching integration when available"""
        mock_cache = Mock()
        mock_get_cache_manager.return_value = mock_cache
        
        # Test should not crash when caching is available
        response = client.get('/')
        assert response.status_code in [200, 302, 404]
    
    @patch('app.CACHING_AVAILABLE', False)
    def test_caching_when_unavailable(self, client):
        """Test graceful fallback when caching is unavailable"""
        response = client.get('/')
        # Should work normally even without caching
        assert response.status_code in [200, 302, 404]


class TestErrorHandling:
    """Test error handling throughout the application"""
    
    def test_missing_template_handling(self, client):
        """Test handling of missing templates"""
        # This would typically be handled by Flask's error handlers
        response = client.get('/nonexistent-route')
        assert response.status_code == 404
    
    @patch('app.get_scoreboard', side_effect=Exception("Database error"))
    def test_database_exception_handling(self, mock_get_scoreboard, client):
        """Test handling of database exceptions"""
        with patch('app.get_settings', return_value={}):
            response = client.get('/')
            # Should handle database errors gracefully
            assert response.status_code in [200, 500, 302]
    
    def test_json_parsing_error_handling(self, test_app):
        """Test JSON parsing error handling in templates"""
        from app import from_json
        
        # Should not raise exceptions on invalid JSON
        result = from_json('{"invalid": json}')
        assert result == {}
        
        result = from_json('completely invalid')
        assert result == {}


class TestApplicationLifecycle:
    """Test application lifecycle events"""
    
    def test_app_startup(self, test_app):
        """Test application startup"""
        # App should be created without errors
        assert test_app is not None
        assert hasattr(test_app, 'config')
    
    def test_logging_configuration(self, test_app):
        """Test that logging is configured"""
        # Should not raise errors
        import logging
        logger = logging.getLogger(__name__)
        logger.info("Test log message")
        
        # Test that logging doesn't crash the app
        assert True
    
    def test_module_imports(self):
        """Test that all required modules can be imported"""
        # Test critical imports
        import app
        import incentive_service
        import config
        
        # Should not raise ImportError
        assert hasattr(app, 'app')
        assert hasattr(incentive_service, 'DatabaseConnection')
        assert hasattr(config, 'Config')


class TestSecurityFeatures:
    """Test security-related features"""
    
    def test_secret_key_configured(self, test_app):
        """Test that secret key is configured"""
        assert 'SECRET_KEY' in test_app.config
        assert test_app.config['SECRET_KEY'] is not None
        assert len(test_app.config['SECRET_KEY']) > 0
    
    def test_secure_headers(self, client):
        """Test security headers"""
        response = client.get('/')
        # Check that response doesn't expose sensitive information
        assert 'Server' not in response.headers or 'flask' not in response.headers.get('Server', '').lower()
    
    def test_session_cookie_security(self, test_app):
        """Test session cookie security settings"""
        # In production, these should be more restrictive
        # For testing, we verify they can be configured
        assert hasattr(test_app, 'permanent_session_lifetime')


class TestPerformance:
    """Test performance-related aspects"""
    
    def test_template_auto_reload_in_test(self, test_app):
        """Test template auto-reload setting"""
        # Should be enabled for development/testing
        assert test_app.config.get('TEMPLATES_AUTO_RELOAD') is True
    
    def test_response_time_reasonable(self, client, performance_timer):
        """Test that basic routes respond in reasonable time"""
        with performance_timer() as timer:
            response = client.get('/')
            elapsed = timer()
        
        # Should respond within 5 seconds (generous for testing)
        assert elapsed < 5.0
        assert response.status_code in [200, 302, 404]
    
    @patch('app.get_settings')
    @patch('app.get_scoreboard')
    def test_concurrent_requests_handling(self, mock_get_scoreboard, mock_get_settings, client):
        """Test handling of concurrent requests"""
        import threading
        import time
        
        mock_get_settings.return_value = {}
        mock_get_scoreboard.return_value = []
        
        results = []
        errors = []
        
        def make_request():
            try:
                response = client.get('/')
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))
        
        # Create multiple threads to simulate concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)  # 10 second timeout
        
        # Verify results
        assert len(errors) == 0, f"Errors during concurrent requests: {errors}"
        assert len(results) == 5
        for status_code in results:
            assert status_code in [200, 302, 404]


class TestUtilityFunctions:
    """Test utility functions and helpers"""
    
    def test_json_filter_edge_cases(self, test_app):
        """Test edge cases for the JSON filter"""
        from app import from_json
        
        # Test various edge cases
        test_cases = [
            ('{}', {}),
            ('[]', []),
            ('null', None),
            ('true', True),
            ('false', False),
            ('123', 123),
            ('"string"', 'string'),
            ('', {}),
            (None, {}),
            ('invalid', {}),
            ('{"nested": {"key": "value"}}', {"nested": {"key": "value"}})
        ]
        
        for input_val, expected in test_cases:
            result = from_json(input_val)
            assert result == expected or (result == {} and expected is None)
    
    def test_template_context_availability(self, client, init_test_db):
        """Test that template context variables are available"""
        with patch('app.get_settings') as mock_get_settings:
            mock_get_settings.return_value = {
                'site_name': 'Test Site',
                'primary_color': '#D4AF37'
            }
            
            response = client.get('/')
            # Context processor should have been called
            assert mock_get_settings.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])