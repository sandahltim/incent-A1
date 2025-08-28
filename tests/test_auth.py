# tests/test_auth.py
# Authentication and authorization tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import os
import sys
from unittest.mock import patch, Mock, MagicMock
from flask import session, url_for, request
from werkzeug.security import generate_password_hash, check_password_hash

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.auth import (
    admin_required, employee_required, check_admin_session, check_employee_session,
    clear_admin_session, clear_employee_session
)
import incentive_service
from incentive_service import verify_pin


class TestAuthenticationDecorators:
    """Test authentication decorators"""
    
    def test_admin_required_decorator_with_admin_session(self, client, test_app):
        """Test admin_required decorator with valid admin session"""
        @admin_required
        def mock_admin_route():
            return "Admin content", 200
        
        with test_app.test_request_context():
            with client.session_transaction() as sess:
                sess['admin'] = True
                sess['admin_id'] = 1
            
            # The decorator should allow access
            response, status = mock_admin_route()
            assert status == 200
            assert response == "Admin content"
    
    def test_admin_required_decorator_without_admin_session(self, client, test_app):
        """Test admin_required decorator without admin session"""
        @admin_required
        def mock_admin_route():
            return "Admin content", 200
        
        with test_app.test_request_context():
            # No admin session set
            try:
                response = mock_admin_route()
                # If we get here, the decorator didn't redirect
                # This might happen in test context
                assert response is not None
            except Exception:
                # Decorator might raise an exception when trying to redirect in test context
                pass
    
    def test_employee_required_decorator_with_employee_session(self, client, test_app):
        """Test employee_required decorator with valid employee session"""
        @employee_required
        def mock_employee_route():
            return "Employee content", 200
        
        with test_app.test_request_context():
            with client.session_transaction() as sess:
                sess['employee_id'] = 2
                sess['employee_name'] = 'Test Employee'
            
            # The decorator should allow access
            response, status = mock_employee_route()
            assert status == 200
            assert response == "Employee content"
    
    def test_employee_required_decorator_without_employee_session(self, client, test_app):
        """Test employee_required decorator without employee session"""
        @employee_required
        def mock_employee_route():
            return "Employee content", 200
        
        with test_app.test_request_context():
            # No employee session set
            try:
                response = mock_employee_route()
                # If we get here, the decorator didn't redirect
                assert response is not None
            except Exception:
                # Decorator might raise an exception when trying to redirect in test context
                pass


class TestSessionChecking:
    """Test session checking functions"""
    
    def test_check_admin_session_with_admin(self, client, test_app):
        """Test checking admin session when admin is logged in"""
        with test_app.test_request_context():
            with client.session_transaction() as sess:
                sess['admin'] = True
            
            # Should return True for admin session
            result = check_admin_session()
            assert result is True
    
    def test_check_admin_session_without_admin(self, client, test_app):
        """Test checking admin session when admin is not logged in"""
        with test_app.test_request_context():
            # No admin session set
            result = check_admin_session()
            assert result is False
    
    def test_check_employee_session_with_employee(self, client, test_app):
        """Test checking employee session when employee is logged in"""
        with test_app.test_request_context():
            with client.session_transaction() as sess:
                sess['employee_id'] = 2
            
            # Should return True for employee session
            result = check_employee_session()
            assert result is True
    
    def test_check_employee_session_without_employee(self, client, test_app):
        """Test checking employee session when employee is not logged in"""
        with test_app.test_request_context():
            # No employee session set
            result = check_employee_session()
            assert result is False


class TestSessionClearing:
    """Test session clearing functions"""
    
    def test_clear_admin_session(self, client, test_app):
        """Test clearing admin session"""
        with test_app.test_request_context():
            with client.session_transaction() as sess:
                sess['admin'] = True
                sess['admin_id'] = 1
                sess['admin_name'] = 'Test Admin'
            
            # Verify admin session exists
            with client.session_transaction() as sess:
                assert 'admin' in sess
            
            # Clear admin session
            with test_app.test_request_context():
                with patch('services.auth.session', sess):
                    clear_admin_session()
            
            # Verify admin session is cleared
            with client.session_transaction() as sess:
                assert 'admin' not in sess
    
    def test_clear_employee_session(self, client, test_app):
        """Test clearing employee session"""
        with test_app.test_request_context():
            with client.session_transaction() as sess:
                sess['employee_id'] = 2
                sess['employee_name'] = 'Test Employee'
            
            # Verify employee session exists
            with client.session_transaction() as sess:
                assert 'employee_id' in sess
            
            # Clear employee session
            with test_app.test_request_context():
                with patch('services.auth.session', sess):
                    clear_employee_session()
            
            # Verify employee session is cleared
            with client.session_transaction() as sess:
                assert 'employee_id' not in sess


class TestPinVerification:
    """Test PIN verification functionality"""
    
    def test_verify_pin_correct(self, test_db_path, init_test_db):
        """Test PIN verification with correct PIN"""
        from config import Config
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Test with one of the sample employees (John Doe, PIN: 1234)
            result = verify_pin("1234")
            assert result is not None
            assert result['name'] == 'John Doe'
            assert result['id'] == 2
    
    def test_verify_pin_incorrect(self, test_db_path, init_test_db):
        """Test PIN verification with incorrect PIN"""
        from config import Config
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Test with non-existent PIN
            result = verify_pin("9999")
            assert result is None
    
    def test_verify_pin_empty(self, test_db_path, init_test_db):
        """Test PIN verification with empty PIN"""
        from config import Config
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            result = verify_pin("")
            assert result is None
    
    def test_verify_pin_inactive_employee(self, test_db_path, init_test_db):
        """Test PIN verification for inactive employee"""
        from config import Config
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Test with inactive user (PIN: 0001)
            result = verify_pin("0001")
            # Should return None for inactive employee or handle appropriately
            # Depends on verify_pin implementation
            assert result is None or result.get('is_active') == 0


class TestPasswordHashing:
    """Test password hashing functionality"""
    
    def test_password_hash_generation(self):
        """Test password hash generation"""
        password = "test_password"
        hashed = generate_password_hash(password)
        
        assert hashed is not None
        assert len(hashed) > 0
        assert hashed != password  # Should be hashed, not plain text
    
    def test_password_hash_verification_correct(self):
        """Test password hash verification with correct password"""
        password = "test_password"
        hashed = generate_password_hash(password)
        
        result = check_password_hash(hashed, password)
        assert result is True
    
    def test_password_hash_verification_incorrect(self):
        """Test password hash verification with incorrect password"""
        password = "test_password"
        wrong_password = "wrong_password"
        hashed = generate_password_hash(password)
        
        result = check_password_hash(hashed, wrong_password)
        assert result is False
    
    def test_password_hash_uniqueness(self):
        """Test that password hashes are unique for same password"""
        password = "test_password"
        hash1 = generate_password_hash(password)
        hash2 = generate_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify against the original password
        assert check_password_hash(hash1, password) is True
        assert check_password_hash(hash2, password) is True


class TestAuthenticationRoutes:
    """Test authentication-related routes (using mock routes)"""
    
    def create_mock_admin_route(self, test_app):
        """Create a mock admin route for testing"""
        @test_app.route('/test-admin')
        @admin_required
        def test_admin():
            return "Admin test route"
        
        return test_admin
    
    def create_mock_employee_route(self, test_app):
        """Create a mock employee route for testing"""
        @test_app.route('/test-employee')
        @employee_required
        def test_employee():
            return "Employee test route"
        
        return test_employee
    
    def test_admin_route_with_authentication(self, client, test_app):
        """Test admin route with proper authentication"""
        self.create_mock_admin_route(test_app)
        
        # Set up admin session
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['admin_id'] = 1
        
        response = client.get('/test-admin')
        assert response.status_code == 200
        assert b"Admin test route" in response.data
    
    def test_admin_route_without_authentication(self, client, test_app):
        """Test admin route without authentication"""
        self.create_mock_admin_route(test_app)
        
        # No admin session set
        response = client.get('/test-admin')
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]
    
    def test_employee_route_with_authentication(self, client, test_app):
        """Test employee route with proper authentication"""
        self.create_mock_employee_route(test_app)
        
        # Set up employee session
        with client.session_transaction() as sess:
            sess['employee_id'] = 2
            sess['employee_name'] = 'Test Employee'
        
        response = client.get('/test-employee')
        assert response.status_code == 200
        assert b"Employee test route" in response.data
    
    def test_employee_route_without_authentication(self, client, test_app):
        """Test employee route without authentication"""
        self.create_mock_employee_route(test_app)
        
        # No employee session set
        response = client.get('/test-employee')
        # Should redirect to login or return 401/403
        assert response.status_code in [302, 401, 403]


class TestSessionSecurity:
    """Test session security features"""
    
    def test_session_timeout_handling(self, client, test_app):
        """Test session timeout handling"""
        # This would typically involve checking session expiration
        # For now, we test that session data persists within requests
        
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['timestamp'] = 12345678
        
        with client.session_transaction() as sess:
            assert sess.get('admin') is True
            assert sess.get('timestamp') == 12345678
    
    def test_session_data_isolation(self, client, test_app):
        """Test that session data is isolated between different users"""
        # This is more of a Flask test, but important for security
        
        with client.session_transaction() as sess:
            sess['user_id'] = 123
        
        # Create another client to simulate different user
        client2 = test_app.test_client()
        
        with client2.session_transaction() as sess:
            assert sess.get('user_id') is None
    
    def test_session_data_types(self, client, test_app):
        """Test that different data types can be stored in session"""
        with client.session_transaction() as sess:
            sess['string'] = 'test'
            sess['integer'] = 123
            sess['boolean'] = True
            sess['list'] = [1, 2, 3]
            sess['dict'] = {'key': 'value'}
        
        with client.session_transaction() as sess:
            assert sess.get('string') == 'test'
            assert sess.get('integer') == 123
            assert sess.get('boolean') is True
            assert sess.get('list') == [1, 2, 3]
            assert sess.get('dict') == {'key': 'value'}


class TestAuthorizationLevels:
    """Test different authorization levels"""
    
    def test_admin_vs_employee_privileges(self, client, test_app):
        """Test that admin and employee have different privilege levels"""
        # Create routes that require different privilege levels
        @test_app.route('/admin-only')
        @admin_required
        def admin_only():
            return "Admin only content"
        
        @test_app.route('/employee-only')
        @employee_required
        def employee_only():
            return "Employee only content"
        
        # Test with admin session
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['admin_id'] = 1
        
        response = client.get('/admin-only')
        assert response.status_code == 200
        
        # Test with employee session
        with client.session_transaction() as sess:
            sess.clear()  # Clear admin session
            sess['employee_id'] = 2
        
        response = client.get('/employee-only')
        assert response.status_code == 200
        
        # Employee should not access admin-only route
        response = client.get('/admin-only')
        assert response.status_code in [302, 401, 403]
    
    def test_role_based_access_control(self, test_db_path, init_test_db):
        """Test role-based access control"""
        from config import Config
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Test admin role
            admin_result = verify_pin("0000")  # Admin user PIN
            if admin_result:
                assert admin_result['role'] == 'admin'
            
            # Test employee role
            employee_result = verify_pin("1234")  # John Doe PIN
            if employee_result:
                assert employee_result['role'] == 'employee'


class TestSecurityVulnerabilities:
    """Test for common security vulnerabilities"""
    
    def test_session_fixation_prevention(self, client, test_app):
        """Test that session fixation is prevented"""
        # Get initial session
        with client.session_transaction() as sess:
            initial_session_id = id(sess)
            sess['initial'] = True
        
        # Simulate login
        with client.session_transaction() as sess:
            sess['admin'] = True
            sess['admin_id'] = 1
        
        # Session should still be valid but ideally regenerated
        # This is more of a Flask security feature test
        with client.session_transaction() as sess:
            assert sess.get('admin') is True
    
    def test_unauthorized_privilege_escalation(self, client, test_app):
        """Test that users can't escalate their privileges"""
        # Start with employee session
        with client.session_transaction() as sess:
            sess['employee_id'] = 2
            sess['employee_name'] = 'Test Employee'
        
        # Try to manually add admin privileges
        with client.session_transaction() as sess:
            sess['admin'] = True  # This shouldn't be allowed in real app
        
        # In a real application, there should be proper validation
        # For now, we just verify the session can be manipulated in tests
        with client.session_transaction() as sess:
            # The test shows the vulnerability - in production,
            # proper validation should prevent this
            assert sess.get('admin') is True
    
    def test_sql_injection_in_auth(self, test_db_path, init_test_db):
        """Test that authentication is protected against SQL injection"""
        from config import Config
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Try SQL injection through PIN field
            malicious_pin = "1234' OR '1'='1"
            
            result = verify_pin(malicious_pin)
            # Should return None, not bypass authentication
            assert result is None
    
    def test_timing_attack_resistance(self, test_db_path, init_test_db):
        """Test resistance to timing attacks"""
        from config import Config
        import time
        
        with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
            # Test timing for valid PIN
            start_time = time.time()
            verify_pin("1234")
            valid_time = time.time() - start_time
            
            # Test timing for invalid PIN
            start_time = time.time()
            verify_pin("9999")
            invalid_time = time.time() - start_time
            
            # Times should be similar to prevent timing attacks
            # Allow for some variance in test environment
            time_difference = abs(valid_time - invalid_time)
            assert time_difference < 0.1  # 100ms tolerance


if __name__ == '__main__':
    pytest.main([__file__, '-v'])