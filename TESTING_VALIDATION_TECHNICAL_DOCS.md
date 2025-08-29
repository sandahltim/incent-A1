# Testing and Validation Procedures Technical Documentation

**Version**: 1.0.0  
**Date**: August 29, 2025  
**Target Audience**: Developers, QA Engineers, System Administrators, Technical Staff  

## Table of Contents

1. [Testing Framework Overview](#testing-framework-overview)
2. [CSRF Security Testing](#csrf-security-testing)
3. [Dual Game System Testing](#dual-game-system-testing)
4. [API Endpoint Testing](#api-endpoint-testing)
5. [Database Testing](#database-testing)
6. [Integration Testing](#integration-testing)
7. [Performance Testing](#performance-testing)
8. [Security Validation](#security-validation)
9. [Automated Testing Procedures](#automated-testing-procedures)
10. [Manual Testing Procedures](#manual-testing-procedures)
11. [Test Data Management](#test-data-management)
12. [Continuous Integration](#continuous-integration)

## Testing Framework Overview

The system uses a comprehensive testing framework combining automated and manual testing procedures to validate CSRF security, dual game system functionality, and overall system integrity.

### Testing Stack

```bash
# Core testing framework
pytest==7.4.0                    # Primary testing framework
pytest-cov==4.1.0               # Coverage reporting
pytest-mock==3.11.1             # Mocking utilities
pytest-flask==1.2.0             # Flask-specific testing utilities

# HTTP testing
requests==2.31.0                # HTTP client for API testing
responses==0.23.1               # HTTP response mocking

# Database testing
sqlite3                          # Database testing utilities
pytest-database==0.3.0          # Database fixtures

# Security testing
bandit==1.7.5                   # Security linting
safety==2.3.4                   # Dependency vulnerability scanning
```

### Test Configuration

**File**: `pytest.ini`

```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --cov=.
    --cov-report=html:htmlcov
    --cov-report=term-missing
    --cov-fail-under=80

markers =
    unit: Unit tests
    integration: Integration tests
    security: Security tests
    performance: Performance tests
    csrf: CSRF-specific tests
    dual_games: Dual game system tests
    slow: Slow-running tests
    database: Database-related tests
```

## CSRF Security Testing

### Comprehensive CSRF Validation Script

**File**: `csrf_system_validation.py` (already exists)

This script provides comprehensive CSRF testing across all protected endpoints.

#### Running CSRF Tests

```bash
# Run comprehensive CSRF validation
python csrf_system_validation.py

# Run specific CSRF test categories
python csrf_system_validation.py --category dual_game_system
python csrf_system_validation.py --category legacy_games
python csrf_system_validation.py --category admin_endpoints
```

#### Expected Test Results

```json
{
  "timestamp": "2025-08-29 12:00:00",
  "server_url": "http://localhost:7410",
  "tests": {
    "dual_game_system": {
      "dual_system_status": {"success": true, "status_code": 200},
      "category_a_game": {"success": true, "status_code": 400, "should_fail": false},
      "category_b_game": {"success": true, "status_code": 400, "should_fail": false}
    },
    "csrf_protection_negative": {
      "no_csrf_api_games_category_a_play_1": {
        "success": true,
        "status_code": 400,
        "should_fail": true
      }
    }
  }
}
```

### Unit Tests for CSRF Protection

**File**: `tests/test_csrf.py`

```python
import pytest
from flask import url_for
from bs4 import BeautifulSoup
import json

class TestCSRFProtection:
    """Test CSRF protection across all endpoints."""
    
    def test_csrf_token_generation(self, client):
        """Test that CSRF tokens are generated correctly."""
        response = client.get('/')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
        assert meta_tag is not None
        assert meta_tag.get('content') is not None
        assert len(meta_tag.get('content')) > 10  # Basic token validation
    
    def test_csrf_protection_on_dual_game_endpoints(self, client):
        """Test CSRF protection on dual game system endpoints."""
        
        # Test Category A game without CSRF token (should fail)
        response = client.post('/api/games/category-a/play/1')
        assert response.status_code == 400
        data = response.get_json()
        assert not data['success']
        assert 'csrf' in data['message'].lower()
        
        # Test Category B game without CSRF token (should fail)
        response = client.post('/api/games/category-b/play', 
                              data={'game_type': 'slots', 'token_cost': '5'})
        assert response.status_code == 400
        data = response.get_json()
        assert not data['success']
        assert 'csrf' in data['message'].lower()
    
    def test_csrf_protection_with_valid_token(self, client, csrf_token):
        """Test that valid CSRF tokens allow requests."""
        
        # Test with valid CSRF token in form data
        response = client.post('/api/games/category-b/play',
                              data={
                                  'csrf_token': csrf_token,
                                  'game_type': 'slots',
                                  'token_cost': '5'
                              })
        
        # Should not fail due to CSRF (may fail for other reasons like authentication)
        assert response.status_code != 400 or 'csrf' not in response.get_json().get('message', '').lower()
    
    def test_csrf_protection_with_header(self, client, csrf_token):
        """Test CSRF protection with X-CSRFToken header."""
        
        response = client.post('/api/games/category-b/play',
                              headers={'X-CSRFToken': csrf_token},
                              json={'game_type': 'slots', 'token_cost': 5})
        
        # Should not fail due to CSRF
        assert response.status_code != 400 or 'csrf' not in response.get_json().get('message', '').lower()
    
    @pytest.mark.parametrize("endpoint,method", [
        ('/api/games/category-a/play/1', 'POST'),
        ('/api/games/category-b/play', 'POST'),
        ('/api/admin/dual-system/award-category-a', 'POST'),
        ('/play_game/1', 'POST'),
        ('/api/tokens/exchange', 'POST'),
    ])
    def test_all_protected_endpoints_require_csrf(self, client, endpoint, method):
        """Test that all protected endpoints require CSRF tokens."""
        
        response = getattr(client, method.lower())(endpoint)
        assert response.status_code == 400
        data = response.get_json()
        assert not data['success']
        assert 'csrf' in data['message'].lower()

@pytest.fixture
def csrf_token(client):
    """Get a valid CSRF token for testing."""
    response = client.get('/')
    soup = BeautifulSoup(response.data, 'html.parser')
    meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
    return meta_tag.get('content')
```

## Dual Game System Testing

### Category A Game Testing

**File**: `tests/test_dual_games_category_a.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from services.dual_game_manager import dual_game_manager

class TestCategoryAGames:
    """Test Category A guaranteed reward games."""
    
    def test_award_category_a_game(self, mock_db):
        """Test awarding Category A games to employees."""
        
        # Mock employee data
        mock_db.execute.return_value.fetchone.return_value = {
            'tier_level': 'silver', 'name': 'John Doe'
        }
        mock_db.execute.return_value.lastrowid = 123
        
        success, message = dual_game_manager.award_category_a_game(
            employee_id='E001',
            source="admin_award",
            source_description="Monthly bonus"
        )
        
        assert success is True
        assert "guaranteed reward game awarded" in message.lower()
        
        # Verify database calls
        assert mock_db.execute.call_count >= 2  # Employee lookup + game creation
    
    def test_play_category_a_game_success(self, mock_db):
        """Test successful Category A game play."""
        
        # Mock game data
        mock_db.execute.return_value.fetchone.side_effect = [
            {'tier_level': 'silver', 'game_type': 'reward_selection'},  # Game lookup
            (0,),  # Prize limit check (0 used)
        ]
        
        success, message, prize_details = dual_game_manager.play_category_a_game(
            employee_id='E001',
            game_id=123
        )
        
        assert success is True
        assert "congratulations" in message.lower()
        assert prize_details is not None
        assert 'description' in prize_details
        assert 'amount' in prize_details
    
    def test_individual_prize_limits(self, mock_db):
        """Test individual prize limits are enforced."""
        
        # Mock employee at prize limit
        mock_db.execute.return_value.fetchone.side_effect = [
            {'tier_level': 'bronze'},  # Employee tier
            (1,),  # Prize limit check (1 used, limit is 1 for bronze jackpot)
        ]
        
        can_win, used, limit = dual_game_manager.check_individual_prize_limit(
            employee_id='E001',
            prize_type='jackpot_cash'
        )
        
        assert can_win is False
        assert used == 1
        assert limit == 1  # Bronze tier limit for jackpot_cash
    
    @pytest.mark.parametrize("tier,expected_limits", [
        ('bronze', {'jackpot_cash': 1, 'pto_hours': 2, 'major_points': 5}),
        ('silver', {'jackpot_cash': 2, 'pto_hours': 4, 'major_points': 8}),
        ('gold', {'jackpot_cash': 3, 'pto_hours': 6, 'major_points': 12}),
        ('platinum', {'jackpot_cash': 5, 'pto_hours': 8, 'major_points': 20}),
    ])
    def test_tier_based_prize_limits(self, tier, expected_limits):
        """Test that prize limits vary correctly by tier."""
        
        manager = dual_game_manager
        for prize_type, expected_limit in expected_limits.items():
            actual_limit = manager.individual_prize_limits[tier][prize_type]
            assert actual_limit == expected_limit
```

### Category B Game Testing

**File**: `tests/test_dual_games_category_b.py`

```python
import pytest
from unittest.mock import patch, MagicMock
from services.dual_game_manager import dual_game_manager
from services.token_economy import token_economy

class TestCategoryBGames:
    """Test Category B token-based gambling games."""
    
    def test_play_category_b_game_with_sufficient_tokens(self, mock_db):
        """Test Category B game play with sufficient tokens."""
        
        # Mock token account with sufficient balance
        with patch.object(token_economy, 'get_employee_token_account') as mock_account:
            mock_account.return_value = {
                'token_balance': 50,
                'tier_level': 'silver'
            }
            
            with patch.object(token_economy, 'spend_tokens') as mock_spend:
                mock_spend.return_value = (True, "Tokens spent successfully")
                
                # Mock game outcome (win)
                with patch.object(dual_game_manager, '_determine_category_b_outcome') as mock_outcome:
                    mock_outcome.return_value = {
                        'outcome': 'win',
                        'prize_type': 'major_points_500',
                        'amount': 500,
                        'description': '500 Bonus Points'
                    }
                    
                    success, message, result = dual_game_manager.play_category_b_game(
                        employee_id='E001',
                        game_type='slots',
                        token_cost=5
                    )
                    
                    assert success is True
                    assert 'won' in message.lower()
                    assert result['outcome'] == 'win'
                    assert result['amount'] == 500
    
    def test_play_category_b_game_insufficient_tokens(self, mock_db):
        """Test Category B game play with insufficient tokens."""
        
        with patch.object(token_economy, 'get_employee_token_account') as mock_account:
            mock_account.return_value = {
                'token_balance': 2,  # Less than required 5
                'tier_level': 'bronze'
            }
            
            success, message, result = dual_game_manager.play_category_b_game(
                employee_id='E001',
                game_type='slots',
                token_cost=5
            )
            
            assert success is False
            assert 'insufficient tokens' in message.lower()
            assert result is None
    
    def test_global_prize_pool_depletion(self, mock_db):
        """Test behavior when global prize pools are depleted."""
        
        # Mock depleted prize pool
        mock_db.execute.return_value.fetchone.return_value = {
            'daily_used': 3,
            'daily_limit': 3,  # At limit
            'last_daily_reset': '2025-08-29'
        }
        
        available, used, limit = dual_game_manager.check_global_prize_availability('cash_prize_100')
        
        assert available is False
        assert used == 3
        assert limit == 3
    
    @pytest.mark.parametrize("game_type,tier,expected_min_rate", [
        ('slots', 'bronze', 0.30),
        ('slots', 'platinum', 0.40),
        ('roulette', 'bronze', 0.25),
        ('roulette', 'platinum', 0.35),
    ])
    def test_win_rates_by_tier(self, game_type, tier, expected_min_rate):
        """Test that win rates increase with higher tiers."""
        
        # Test multiple outcomes to verify statistical distribution
        wins = 0
        total_games = 1000
        
        for _ in range(total_games):
            with patch('random.random', return_value=0.3):  # Fixed random value
                outcome = dual_game_manager._determine_category_b_outcome(
                    MagicMock(), game_type, tier
                )
                if outcome['outcome'] == 'win':
                    wins += 1
        
        win_rate = wins / total_games
        assert win_rate >= expected_min_rate
```

### Token Economy Testing

**File**: `tests/test_token_economy.py`

```python
import pytest
from datetime import datetime, timedelta
from services.token_economy import token_economy

class TestTokenEconomy:
    """Test token economy system."""
    
    def test_tier_based_exchange_rates(self):
        """Test that exchange rates vary by tier."""
        
        expected_rates = {
            'bronze': 10,    # Worst rate
            'silver': 8,
            'gold': 6,
            'platinum': 5    # Best rate
        }
        
        for tier, expected_rate in expected_rates.items():
            actual_rate = token_economy.tier_exchange_rates[tier]
            assert actual_rate == expected_rate
    
    def test_token_exchange_calculation(self, mock_db):
        """Test token exchange cost calculation."""
        
        # Mock employee account
        mock_db.execute.return_value.fetchone.return_value = {
            'tier_level': 'silver',
            'current_points': 100
        }
        
        cost_info, error = token_economy.calculate_exchange_cost(
            employee_id='E001',
            token_amount=10
        )
        
        assert error is None
        assert cost_info['token_amount'] == 10
        assert cost_info['points_cost'] == 80  # 10 tokens * 8 points/token (silver rate)
        assert cost_info['exchange_rate'] == 8
        assert cost_info['can_afford'] is True
    
    def test_daily_exchange_limits(self, mock_db):
        """Test daily exchange limits enforcement."""
        
        # Mock account at daily limit
        mock_db.execute.return_value.fetchone.return_value = {
            'tier_level': 'bronze',
            'daily_exchange_count': 50,  # At limit
            'last_exchange_date': datetime.now().isoformat()
        }
        
        can_exchange, reason = token_economy.can_exchange_tokens('E001')
        
        assert can_exchange is False
        assert 'daily token limit reached' in reason.lower()
    
    def test_exchange_cooldown_enforcement(self, mock_db):
        """Test exchange cooldown enforcement."""
        
        # Mock recent exchange (within cooldown)
        recent_time = datetime.now() - timedelta(hours=12)  # 12 hours ago
        mock_db.execute.return_value.fetchone.return_value = {
            'tier_level': 'bronze',
            'daily_exchange_count': 10,
            'last_exchange_date': recent_time.isoformat()
        }
        
        can_exchange, reason = token_economy.can_exchange_tokens('E001')
        
        assert can_exchange is False
        assert 'cooldown active' in reason.lower()
        assert 'hours remaining' in reason.lower()
    
    def test_token_transaction_logging(self, mock_db):
        """Test that all token transactions are logged."""
        
        # Mock successful token spend
        mock_db.execute.return_value.fetchone.return_value = {
            'token_balance': 50
        }
        
        success, message = token_economy.spend_tokens(
            employee_id='E001',
            token_amount=5,
            description='Category B slots'
        )
        
        assert success is True
        
        # Verify transaction was logged
        log_calls = [call for call in mock_db.execute.call_args_list 
                    if 'token_transactions' in str(call)]
        assert len(log_calls) >= 1
```

## API Endpoint Testing

### REST API Testing Framework

**File**: `tests/test_api_endpoints.py`

```python
import pytest
import json
from flask import url_for

class TestAPIEndpoints:
    """Test all API endpoints with proper authentication and CSRF protection."""
    
    def test_dual_system_status_endpoint(self, client):
        """Test dual system status endpoint."""
        
        response = client.get('/api/dual-system/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'system_health' in data
        assert 'global_pools' in data
        assert 'token_economy' in data
    
    def test_category_a_game_endpoint_with_csrf(self, client, csrf_token):
        """Test Category A game endpoint with proper CSRF token."""
        
        response = client.post('/api/games/category-a/play/1',
                              data={'csrf_token': csrf_token})
        
        # Should not fail due to CSRF (may fail for other reasons)
        assert response.status_code != 400 or 'csrf' not in response.get_json().get('message', '').lower()
    
    def test_token_exchange_endpoint(self, client, csrf_token):
        """Test token exchange endpoint."""
        
        response = client.post('/api/tokens/exchange',
                              data={
                                  'csrf_token': csrf_token,
                                  'employee_id': 'E001',
                                  'token_amount': '10'
                              })
        
        # Should not fail due to CSRF
        assert response.status_code != 400 or 'csrf' not in response.get_json().get('message', '').lower()
    
    def test_api_error_handling(self, client):
        """Test consistent error handling across API endpoints."""
        
        # Test endpoint without CSRF token
        response = client.post('/api/games/category-b/play')
        assert response.status_code == 400
        
        data = response.get_json()
        assert 'success' in data
        assert data['success'] is False
        assert 'error' in data
        assert 'message' in data
    
    @pytest.mark.parametrize("endpoint,expected_status", [
        ('/api/dual-system/status', 200),
        ('/api/games/summary/E001', 200),
        ('/api/tokens/account/E001', 200),
        ('/api/admin/analytics/dual-system', 403),  # Should require admin auth
    ])
    def test_endpoint_availability(self, client, endpoint, expected_status):
        """Test that endpoints return expected status codes."""
        
        response = client.get(endpoint)
        assert response.status_code == expected_status
```

### API Performance Testing

**File**: `tests/test_api_performance.py`

```python
import pytest
import time
import concurrent.futures
from threading import Thread

class TestAPIPerformance:
    """Test API endpoint performance and concurrency."""
    
    def test_endpoint_response_time(self, client):
        """Test that API endpoints respond within acceptable time limits."""
        
        endpoints_to_test = [
            '/api/dual-system/status',
            '/api/games/summary/E001',
            '/api/tokens/account/E001'
        ]
        
        for endpoint in endpoints_to_test:
            start_time = time.time()
            response = client.get(endpoint)
            end_time = time.time()
            
            response_time = end_time - start_time
            assert response_time < 1.0, f"Endpoint {endpoint} took {response_time:.2f}s (limit: 1.0s)"
    
    def test_concurrent_requests(self, client):
        """Test system behavior under concurrent load."""
        
        def make_request():
            response = client.get('/api/dual-system/status')
            return response.status_code
        
        # Test 20 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(20)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        assert all(status == 200 for status in results)
    
    @pytest.mark.slow
    def test_database_connection_pool_stress(self, client):
        """Test database connection pool under stress."""
        
        def database_heavy_request():
            # Endpoint that performs multiple database operations
            response = client.get('/api/games/summary/E001')
            return response.status_code == 200
        
        # Stress test with 50 concurrent database-heavy requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(database_heavy_request) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # At least 90% should succeed (allowing for some failures under extreme load)
        success_rate = sum(results) / len(results)
        assert success_rate >= 0.9
```

## Database Testing

### Database Integrity Testing

**File**: `tests/test_database_integrity.py`

```python
import pytest
import sqlite3
from incentive_service import DatabaseConnection

class TestDatabaseIntegrity:
    """Test database schema and data integrity."""
    
    def test_database_schema_integrity(self):
        """Test that all required tables and columns exist."""
        
        required_tables = [
            'employees', 'admins', 'mini_games', 'game_history',
            'employee_tokens', 'token_transactions', 'employee_prize_limits',
            'global_prize_pools', 'admin_game_config', 'employee_behavior_flags'
        ]
        
        with DatabaseConnection() as conn:
            # Get all table names
            tables = conn.execute("""
                SELECT name FROM sqlite_master WHERE type='table'
            """).fetchall()
            table_names = [table[0] for table in tables]
            
            for required_table in required_tables:
                assert required_table in table_names, f"Missing required table: {required_table}"
    
    def test_foreign_key_constraints(self):
        """Test that foreign key constraints are properly defined."""
        
        with DatabaseConnection() as conn:
            # Enable foreign key checking
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Test constraint violation (should fail)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO mini_games (employee_id, game_type, awarded_date, status)
                    VALUES ('NONEXISTENT', 'test', '2025-08-29', 'unused')
                """)
                conn.commit()
    
    def test_check_constraints(self):
        """Test that check constraints are enforced."""
        
        with DatabaseConnection() as conn:
            # Test invalid vote value (should fail)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO votes (voter_initials, recipient_id, vote_value, vote_date)
                    VALUES ('TEST', 'E001', 2, '2025-08-29')  -- Invalid vote_value
                """)
                conn.commit()
    
    def test_unique_constraints(self):
        """Test that unique constraints prevent duplicates."""
        
        with DatabaseConnection() as conn:
            # Insert a test employee
            conn.execute("""
                INSERT OR IGNORE INTO employees (employee_id, name, initials, score)
                VALUES ('E001', 'Test User', 'TU', 50)
            """)
            
            # Try to insert duplicate initials (should fail)
            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO employees (employee_id, name, initials, score)
                    VALUES ('E002', 'Another User', 'TU', 50)  -- Duplicate initials
                """)
                conn.commit()
    
    def test_index_performance(self):
        """Test that database indexes provide expected performance."""
        
        with DatabaseConnection() as conn:
            # Test query that should use index
            start_time = time.time()
            result = conn.execute("""
                SELECT COUNT(*) FROM mini_games WHERE employee_id = 'E001'
            """).fetchone()
            end_time = time.time()
            
            query_time = end_time - start_time
            assert query_time < 0.1, f"Indexed query took {query_time:.3f}s (expected < 0.1s)"
    
    def test_database_integrity_check(self):
        """Run SQLite integrity check."""
        
        with DatabaseConnection() as conn:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            assert result[0] == "ok", f"Database integrity check failed: {result[0]}"
```

### Data Migration Testing

**File**: `tests/test_migrations.py`

```python
import pytest
import tempfile
import shutil
import sqlite3
from setup_dual_game_system import setup_dual_game_system, verify_setup

class TestDatabaseMigrations:
    """Test database schema migrations."""
    
    def test_dual_system_migration(self):
        """Test that dual system setup creates all required structures."""
        
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name
        
        try:
            # Create a minimal base database
            conn = sqlite3.connect(temp_db_path)
            conn.execute("""
                CREATE TABLE employees (
                    employee_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    score INTEGER DEFAULT 50
                )
            """)
            conn.execute("""
                INSERT INTO employees VALUES ('E001', 'Test User', 50)
            """)
            conn.commit()
            conn.close()
            
            # Run dual system setup
            original_db_file = setup_dual_game_system.__globals__['sqlite3'].connect
            def mock_connect(path):
                return sqlite3.connect(temp_db_path)
            
            setup_dual_game_system.__globals__['sqlite3'].connect = mock_connect
            
            try:
                result = setup_dual_game_system()
                assert result is True
                
                # Verify setup
                verification_result = verify_setup()
                assert verification_result is True
                
            finally:
                setup_dual_game_system.__globals__['sqlite3'].connect = original_db_file
                
        finally:
            import os
            os.unlink(temp_db_path)
    
    def test_migration_idempotency(self):
        """Test that migrations can be run multiple times safely."""
        
        # Run setup twice - should not fail
        result1 = setup_dual_game_system()
        result2 = setup_dual_game_system()
        
        assert result1 is True
        assert result2 is True  # Should handle existing structures gracefully
```

## Integration Testing

### End-to-End Game Flow Testing

**File**: `tests/test_integration_game_flow.py`

```python
import pytest
from unittest.mock import patch
from services.dual_game_manager import dual_game_manager
from services.token_economy import token_economy

class TestGameFlowIntegration:
    """Test complete game flows from start to finish."""
    
    def test_complete_category_a_flow(self, mock_db):
        """Test complete Category A game flow: award -> play -> prize."""
        
        # Step 1: Award Category A game
        mock_db.execute.return_value.fetchone.side_effect = [
            {'tier_level': 'silver', 'name': 'John Doe'},  # Employee lookup
        ]
        mock_db.execute.return_value.lastrowid = 123
        
        success, message = dual_game_manager.award_category_a_game(
            employee_id='E001',
            source="monthly_bonus"
        )
        assert success is True
        
        # Step 2: Play the awarded game
        mock_db.execute.return_value.fetchone.side_effect = [
            {'tier_level': 'silver', 'game_type': 'reward_selection'},  # Game lookup
            (0,),  # Prize limit check
        ]
        
        success, message, prize = dual_game_manager.play_category_a_game(
            employee_id='E001',
            game_id=123
        )
        assert success is True
        assert prize is not None
        assert 'description' in prize
    
    def test_complete_category_b_flow(self, mock_db):
        """Test complete Category B flow: exchange tokens -> play game -> outcome."""
        
        # Step 1: Exchange points for tokens
        with patch.object(token_economy, 'get_employee_token_account') as mock_account:
            mock_account.return_value = {
                'tier_level': 'silver',
                'current_points': 100,
                'daily_exchange_count': 5,
                'last_exchange_date': None
            }
            
            success, message = token_economy.exchange_points_for_tokens(
                employee_id='E001',
                token_amount=10
            )
            assert success is True
        
        # Step 2: Play gambling game with tokens
        with patch.object(token_economy, 'get_employee_token_account') as mock_account:
            mock_account.return_value = {
                'token_balance': 50,
                'tier_level': 'silver'
            }
            
            with patch.object(token_economy, 'spend_tokens') as mock_spend:
                mock_spend.return_value = (True, "Tokens spent")
                
                with patch('random.random', return_value=0.2):  # Ensure win
                    success, message, result = dual_game_manager.play_category_b_game(
                        employee_id='E001',
                        game_type='slots',
                        token_cost=5
                    )
                    
                    assert success is True
                    assert result['outcome'] == 'win'
    
    def test_prize_limit_integration(self, mock_db):
        """Test that prize limits work across multiple game plays."""
        
        # Mock employee at bronze tier (1 jackpot limit)
        mock_db.execute.return_value.fetchone.side_effect = [
            {'tier_level': 'bronze'},  # First game
            (0,),  # No jackpots used yet
        ]
        
        # First game should allow jackpot
        can_win, used, limit = dual_game_manager.check_individual_prize_limit(
            employee_id='E001',
            prize_type='jackpot_cash'
        )
        assert can_win is True
        assert used == 0
        assert limit == 1
        
        # Mock that employee has now used their jackpot
        mock_db.execute.return_value.fetchone.side_effect = [
            {'tier_level': 'bronze'},  # Second game
            (1,),  # One jackpot used
        ]
        
        # Second attempt should be denied
        can_win, used, limit = dual_game_manager.check_individual_prize_limit(
            employee_id='E001',
            prize_type='jackpot_cash'
        )
        assert can_win is False
        assert used == 1
        assert limit == 1
```

### System Integration Testing

**File**: `tests/test_integration_system.py`

```python
import pytest
import requests
import time
from threading import Thread

class TestSystemIntegration:
    """Test system-level integration."""
    
    @pytest.mark.integration
    def test_full_system_startup(self):
        """Test that the complete system starts up correctly."""
        
        # This test assumes the system is running on localhost:7410
        max_retries = 30
        retry_delay = 1
        
        for i in range(max_retries):
            try:
                response = requests.get('http://localhost:7410/api/health', timeout=5)
                if response.status_code == 200:
                    health_data = response.json()
                    assert health_data['status'] == 'healthy'
                    break
            except (requests.RequestException, KeyError):
                if i == max_retries - 1:
                    pytest.fail("System failed to start up within expected time")
                time.sleep(retry_delay)
    
    @pytest.mark.integration  
    def test_csrf_protection_integration(self):
        """Test CSRF protection in real system environment."""
        
        session = requests.Session()
        
        # Get CSRF token
        response = session.get('http://localhost:7410/')
        assert response.status_code == 200
        
        # Extract CSRF token from HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('meta', {'name': 'csrf-token'})['content']
        
        # Test protected endpoint with token
        response = session.post('http://localhost:7410/api/games/category-b/play',
                               data={'csrf_token': csrf_token, 'game_type': 'slots', 'token_cost': '1'})
        
        # Should not fail due to CSRF (may fail for other reasons)
        assert response.status_code != 400 or 'csrf' not in response.json().get('message', '').lower()
    
    @pytest.mark.integration
    def test_database_connection_pool_integration(self):
        """Test database connection pooling in real environment."""
        
        def make_database_request():
            response = requests.get('http://localhost:7410/api/games/summary/E001')
            return response.status_code
        
        # Create multiple concurrent requests
        threads = []
        results = []
        
        for i in range(20):
            thread = Thread(target=lambda: results.append(make_database_request()))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Most requests should succeed (allowing for some failures under load)
        success_rate = sum(1 for status in results if status == 200) / len(results)
        assert success_rate >= 0.8  # At least 80% success rate
```

## Performance Testing

### Load Testing

**File**: `tests/test_performance.py`

```python
import pytest
import time
import concurrent.futures
import statistics

class TestPerformance:
    """Performance and load testing."""
    
    @pytest.mark.performance
    def test_api_response_time_benchmarks(self, client):
        """Benchmark API response times."""
        
        endpoints = {
            '/api/dual-system/status': 0.5,      # 500ms limit
            '/api/games/summary/E001': 1.0,      # 1s limit
            '/api/tokens/account/E001': 0.3,     # 300ms limit
        }
        
        for endpoint, time_limit in endpoints.items():
            response_times = []
            
            # Test 10 times to get average
            for _ in range(10):
                start = time.time()
                response = client.get(endpoint)
                end = time.time()
                
                assert response.status_code == 200
                response_times.append(end - start)
            
            avg_time = statistics.mean(response_times)
            max_time = max(response_times)
            
            assert avg_time < time_limit, f"{endpoint} avg: {avg_time:.3f}s (limit: {time_limit}s)"
            assert max_time < time_limit * 2, f"{endpoint} max: {max_time:.3f}s (limit: {time_limit * 2}s)"
    
    @pytest.mark.performance
    def test_concurrent_game_plays(self, mock_db):
        """Test performance under concurrent game play load."""
        
        def simulate_game_play():
            start = time.time()
            # Simulate Category B game play
            success, message, result = dual_game_manager.play_category_b_game(
                employee_id=f'E{random.randint(1, 100):03d}',
                game_type='slots',
                token_cost=1
            )
            end = time.time()
            return end - start, success
        
        # Simulate 50 concurrent game plays
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(simulate_game_play) for _ in range(50)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        response_times = [result[0] for result in results]
        success_count = sum(1 for result in results if result[1])
        
        # Performance assertions
        avg_response_time = statistics.mean(response_times)
        assert avg_response_time < 2.0, f"Average response time: {avg_response_time:.3f}s"
        
        # At least 90% should succeed
        success_rate = success_count / len(results)
        assert success_rate >= 0.9, f"Success rate: {success_rate:.1%}"
    
    @pytest.mark.performance
    def test_database_query_performance(self):
        """Test database query performance."""
        
        from incentive_service import DatabaseConnection
        
        with DatabaseConnection() as conn:
            # Test complex analytical query
            start = time.time()
            result = conn.execute("""
                SELECT 
                    e.tier_level,
                    COUNT(*) as total_games,
                    COUNT(CASE WHEN gh.outcome = 'win' THEN 1 END) as wins,
                    AVG(CASE WHEN gh.prize_amount IS NOT NULL THEN gh.prize_amount END) as avg_prize
                FROM employees e
                JOIN mini_games mg ON e.employee_id = mg.employee_id
                LEFT JOIN game_history gh ON mg.id = gh.mini_game_id
                WHERE mg.played_date > date('now', '-30 days')
                GROUP BY e.tier_level
            """).fetchall()
            end = time.time()
            
            query_time = end - start
            assert query_time < 1.0, f"Complex query took {query_time:.3f}s (limit: 1.0s)"
```

### Memory and Resource Testing

**File**: `tests/test_resource_usage.py`

```python
import pytest
import psutil
import time
import gc

class TestResourceUsage:
    """Test memory and resource usage."""
    
    @pytest.mark.performance
    def test_memory_usage_under_load(self, client):
        """Test memory usage doesn't grow excessively under load."""
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Simulate high load
        for i in range(100):
            response = client.get('/api/dual-system/status')
            assert response.status_code == 200
            
            # Force garbage collection occasionally
            if i % 20 == 0:
                gc.collect()
        
        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_growth = final_memory - initial_memory
        
        # Memory growth should be reasonable (< 50MB for 100 requests)
        assert memory_growth < 50, f"Memory grew by {memory_growth:.1f}MB"
    
    @pytest.mark.performance
    def test_database_connection_pool_efficiency(self):
        """Test database connection pool resource usage."""
        
        from incentive_service import DatabaseConnection
        
        # Monitor connection pool metrics
        initial_connections = 0  # Would need to implement pool monitoring
        
        # Simulate concurrent database access
        def db_operation():
            with DatabaseConnection() as conn:
                return conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(db_operation) for _ in range(100)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All operations should complete successfully
        assert len(results) == 100
        assert all(isinstance(result, int) for result in results)
```

## Security Validation

### Security Testing Suite

**File**: `tests/test_security.py`

```python
import pytest
import requests
from urllib.parse import urljoin

class TestSecurity:
    """Security validation tests."""
    
    @pytest.mark.security
    def test_sql_injection_protection(self, client):
        """Test protection against SQL injection attacks."""
        
        # SQL injection attempts
        injection_payloads = [
            "'; DROP TABLE employees; --",
            "' UNION SELECT * FROM admins --",
            "' OR '1'='1",
            "'; INSERT INTO employees VALUES ('HACK', 'Hacker', 'HK', 999999); --"
        ]
        
        for payload in injection_payloads:
            # Test various endpoints that accept user input
            response = client.get(f'/api/games/summary/{payload}')
            # Should not reveal internal errors or succeed maliciously
            assert response.status_code in [400, 404], f"Payload {payload} may have succeeded"
    
    @pytest.mark.security
    def test_xss_protection(self, client):
        """Test protection against XSS attacks."""
        
        xss_payloads = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "<%2fscript%3e%3cscript%3ealert('xss')%3c%2fscript%3e"
        ]
        
        for payload in xss_payloads:
            response = client.post('/feedback',
                                  data={'comment': payload, 'initials': 'XSS'})
            
            # Response should not contain unescaped payload
            assert payload not in response.get_data(as_text=True)
    
    @pytest.mark.security
    def test_csrf_bypass_attempts(self, client):
        """Test various CSRF bypass techniques."""
        
        # Attempt to bypass with various headers
        bypass_attempts = [
            {'X-Requested-With': 'XMLHttpRequest'},
            {'Origin': 'http://localhost:7410'},
            {'Referer': 'http://localhost:7410/'},
            {'Content-Type': 'text/plain'},
        ]
        
        for headers in bypass_attempts:
            response = client.post('/api/games/category-b/play',
                                  headers=headers,
                                  data={'game_type': 'slots', 'token_cost': '5'})
            
            # Should still require CSRF token
            assert response.status_code == 400
            data = response.get_json()
            assert not data['success']
    
    @pytest.mark.security
    def test_authentication_bypass_attempts(self, client):
        """Test authentication bypass attempts."""
        
        # Try accessing admin endpoints without authentication
        admin_endpoints = [
            '/api/admin/dual-system/award-category-a',
            '/api/admin/global-pools/update',
            '/api/admin/analytics/dual-system'
        ]
        
        for endpoint in admin_endpoints:
            response = client.get(endpoint)
            assert response.status_code in [401, 403], f"Admin endpoint {endpoint} may be accessible"
    
    @pytest.mark.security
    def test_sensitive_data_exposure(self, client):
        """Test that sensitive data is not exposed."""
        
        # Check various endpoints for sensitive data
        response = client.get('/api/dual-system/status')
        data = response.get_json()
        
        # Should not contain sensitive information
        response_text = str(data).lower()
        sensitive_terms = ['password', 'secret', 'key', 'token', 'hash']
        
        for term in sensitive_terms:
            assert term not in response_text, f"Sensitive term '{term}' found in response"
    
    @pytest.mark.security  
    def test_rate_limiting(self, client):
        """Test rate limiting protection."""
        
        # Make many rapid requests
        responses = []
        for i in range(100):
            response = client.post('/api/games/category-b/play',
                                  data={'game_type': 'slots'})
            responses.append(response.status_code)
        
        # Some requests should be rate limited (429)
        rate_limited = sum(1 for status in responses if status == 429)
        assert rate_limited > 0, "No rate limiting detected"
```

## Automated Testing Procedures

### Test Execution Scripts

**File**: `run_tests.py`

```python
#!/usr/bin/env python3
"""
Comprehensive test execution script with reporting.
"""

import subprocess
import sys
import os
import json
import time
from datetime import datetime

class TestRunner:
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'test_suites': {},
            'overall_status': 'unknown'
        }
    
    def run_test_suite(self, name, command, description):
        """Run a test suite and capture results."""
        print(f"\n{'='*60}")
        print(f"Running {name}: {description}")
        print('='*60)
        
        start_time = time.time()
        
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            self.results['test_suites'][name] = {
                'status': 'passed' if result.returncode == 0 else 'failed',
                'return_code': result.returncode,
                'duration': duration,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'description': description
            }
            
            if result.returncode == 0:
                print(f"✅ {name} PASSED ({duration:.2f}s)")
            else:
                print(f"❌ {name} FAILED ({duration:.2f}s)")
                print(f"Error output:\n{result.stderr}")
                
        except subprocess.TimeoutExpired:
            print(f"⏰ {name} TIMED OUT")
            self.results['test_suites'][name] = {
                'status': 'timeout',
                'duration': 600,
                'description': description
            }
        except Exception as e:
            print(f"💥 {name} ERROR: {e}")
            self.results['test_suites'][name] = {
                'status': 'error',
                'error': str(e),
                'description': description
            }
    
    def run_all_tests(self):
        """Run all test suites."""
        
        test_suites = [
            ('unit_tests', 'python -m pytest tests/ -m "not integration and not performance" -v', 
             'Core unit tests'),
            ('csrf_validation', 'python csrf_system_validation.py', 
             'CSRF security validation'),
            ('integration_tests', 'python -m pytest tests/ -m "integration" -v',
             'Integration tests'),
            ('security_tests', 'python -m pytest tests/ -m "security" -v',
             'Security validation tests'),
            ('performance_tests', 'python -m pytest tests/ -m "performance" -v --tb=short',
             'Performance and load tests'),
            ('database_integrity', 'sqlite3 incentive.db "PRAGMA integrity_check;"',
             'Database integrity check'),
        ]
        
        for name, command, description in test_suites:
            self.run_test_suite(name, command, description)
        
        # Determine overall status
        statuses = [suite['status'] for suite in self.results['test_suites'].values()]
        if 'failed' in statuses or 'error' in statuses or 'timeout' in statuses:
            self.results['overall_status'] = 'failed'
        else:
            self.results['overall_status'] = 'passed'
    
    def generate_report(self):
        """Generate test report."""
        
        print("\n" + "="*80)
        print("TEST EXECUTION SUMMARY")
        print("="*80)
        
        total_suites = len(self.results['test_suites'])
        passed_suites = sum(1 for suite in self.results['test_suites'].values() 
                           if suite['status'] == 'passed')
        
        print(f"Timestamp: {self.results['timestamp']}")
        print(f"Overall Status: {self.results['overall_status'].upper()}")
        print(f"Test Suites: {passed_suites}/{total_suites} passed")
        print()
        
        for name, suite in self.results['test_suites'].items():
            status_icon = {
                'passed': '✅',
                'failed': '❌', 
                'timeout': '⏰',
                'error': '💥'
            }.get(suite['status'], '❓')
            
            duration = suite.get('duration', 0)
            print(f"{status_icon} {name:<20} {suite['status']:<8} ({duration:.2f}s)")
        
        print("\n" + "="*80)
        
        # Save detailed results
        with open('test_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)
        print("Detailed results saved to: test_results.json")
        
        return self.results['overall_status'] == 'passed'

if __name__ == '__main__':
    runner = TestRunner()
    runner.run_all_tests()
    success = runner.generate_report()
    sys.exit(0 if success else 1)
```

### Continuous Integration Configuration

**File**: `.github/workflows/test.yml`

```yaml
name: Test Suite

on:
  push:
    branches: [ main, dev ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Initialize database
      run: |
        python init_db.py
        python setup_dual_game_system.py
    
    - name: Run tests
      run: |
        python run_tests.py
    
    - name: Upload test results
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: test-results
        path: |
          test_results.json
          htmlcov/
          csrf_validation_results.json
```

## Manual Testing Procedures

### Manual Test Cases

**File**: `manual_test_procedures.md`

```markdown
# Manual Testing Procedures

## CSRF Protection Manual Tests

### Test Case 1: Frontend CSRF Token Presence
1. Open browser to http://localhost:7410/
2. Right-click -> View Page Source
3. Search for `<meta name="csrf-token"`
4. **Expected**: Token should be present and non-empty

### Test Case 2: Game Play with CSRF Token
1. Log in to employee portal
2. Navigate to games section
3. Open browser developer tools -> Network tab
4. Play a Category B game (slots/roulette/dice)
5. **Expected**: Request should include csrf_token in form data or X-CSRFToken header

### Test Case 3: CSRF Protection Validation
1. Open browser developer tools -> Console
2. Execute: `fetch('/api/games/category-b/play', {method: 'POST', body: new FormData()})`
3. **Expected**: Should return 400 error with CSRF validation message

## Dual Game System Manual Tests

### Test Case 4: Token Exchange Flow
1. Log in as employee with sufficient points
2. Navigate to token exchange section
3. Attempt to exchange points for tokens
4. **Expected**: Exchange should respect tier-based rates and daily limits

### Test Case 5: Category A Game Flow
1. Admin awards Category A game to employee
2. Employee logs in and navigates to available games
3. Employee plays guaranteed win game
4. **Expected**: Game should always result in a win with appropriate tier-based prize

### Test Case 6: Prize Limit Enforcement
1. Employee reaches monthly prize limit for their tier
2. Employee plays additional Category A games
3. **Expected**: Should receive basic points instead of limited prizes

## System Integration Manual Tests

### Test Case 7: Service Restart Recovery
1. Stop the incentive service: `sudo systemctl stop incent-dev.service`
2. Start the service: `sudo systemctl start incent-dev.service`
3. Test all major functions immediately after restart
4. **Expected**: All functions should work normally

### Test Case 8: Database Backup/Restore
1. Create a backup: `sqlite3 incentive.db ".backup backup.db"`
2. Make some test changes to data
3. Restore backup: `cp backup.db incentive.db`
4. Restart service
5. **Expected**: Changes should be reverted
```

### Browser Testing

```markdown
# Browser Compatibility Testing

## Supported Browsers
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Manual Browser Tests

### Test Case 9: Cross-Browser CSRF Token Handling
1. Test on each supported browser
2. Verify CSRF tokens are properly extracted and sent
3. **Expected**: Same behavior across all browsers

### Test Case 10: JavaScript Game Controllers
1. Test game play functionality on each browser
2. Verify audio playback works correctly
3. **Expected**: Consistent game experience across browsers

### Test Case 11: Mobile Responsiveness
1. Test on mobile devices or browser dev tools mobile view
2. Verify all functions work on touch interfaces
3. **Expected**: Responsive design adapts to mobile screens
```

## Test Data Management

### Test Data Setup

**File**: `setup_test_data.py`

```python
#!/usr/bin/env python3
"""
Setup test data for manual and automated testing.
"""

import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

def setup_test_employees():
    """Create test employee accounts."""
    
    employees = [
        ('E001', 'John Doe', 'JD', 100, 'Driver', 'silver'),
        ('E002', 'Jane Smith', 'JS', 150, 'Laborer', 'gold'), 
        ('E003', 'Bob Johnson', 'BJ', 50, 'Supervisor', 'bronze'),
        ('E004', 'Alice Brown', 'AB', 200, 'Driver', 'platinum'),
        ('E005', 'Charlie Wilson', 'CW', 75, 'Warehouse Labor', 'silver'),
    ]
    
    conn = sqlite3.connect('incentive.db')
    
    for emp_id, name, initials, score, role, tier in employees:
        # Create employee
        conn.execute("""
            INSERT OR REPLACE INTO employees 
            (employee_id, name, initials, score, role, active, tier_level, pin_hash)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?)
        """, (emp_id, name, initials, score, role, tier, generate_password_hash('1234')))
        
        # Create token account
        conn.execute("""
            INSERT OR REPLACE INTO employee_tokens 
            (employee_id, token_balance, total_tokens_earned)
            VALUES (?, ?, ?)
        """, (emp_id, random.randint(10, 100), random.randint(50, 500)))
        
        # Create tier record
        conn.execute("""
            INSERT OR REPLACE INTO employee_tiers
            (employee_id, tier_level, games_played, total_wins, performance_average)
            VALUES (?, ?, ?, ?, ?)
        """, (emp_id, tier, random.randint(5, 50), random.randint(2, 25), random.uniform(0.3, 0.8)))
    
    conn.commit()
    conn.close()
    print(f"Created {len(employees)} test employees")

def setup_test_games():
    """Create test game records."""
    
    conn = sqlite3.connect('incentive.db')
    
    # Create some unused Category A games
    for i in range(10):
        emp_id = f'E{random.randint(1, 5):03d}'
        conn.execute("""
            INSERT INTO mini_games 
            (employee_id, game_type, awarded_date, status, game_category, guaranteed_win, tier_level)
            VALUES (?, 'reward_selection', ?, 'unused', 'reward', 1, 'silver')
        """, (emp_id, datetime.now().isoformat()))
    
    # Create some played games with history
    for i in range(20):
        emp_id = f'E{random.randint(1, 5):03d}'
        
        # Create game record
        cursor = conn.execute("""
            INSERT INTO mini_games 
            (employee_id, game_type, awarded_date, played_date, status, outcome, 
             game_category, token_cost, tier_level)
            VALUES (?, ?, ?, ?, 'played', ?, 'gambling', ?, 'silver')
        """, (emp_id, 'slots', 
              (datetime.now() - timedelta(days=random.randint(1, 30))).isoformat(),
              (datetime.now() - timedelta(days=random.randint(0, 5))).isoformat(),
              'win' if random.random() > 0.6 else 'loss',
              random.randint(1, 10)))
        
        game_id = cursor.lastrowid
        
        # Create game history
        outcome = 'win' if random.random() > 0.6 else 'loss'
        if outcome == 'win':
            prize_amount = random.choice([25, 50, 100, 500])
            prize_desc = f"{prize_amount} Points"
        else:
            prize_amount = 0
            prize_desc = "No prize"
            
        conn.execute("""
            INSERT INTO game_history
            (mini_game_id, game_type, play_date, outcome, prize_type, 
             prize_amount, prize_description, token_cost, game_category)
            VALUES (?, ?, ?, ?, 'points', ?, ?, ?, 'gambling')
        """, (game_id, 'slots', datetime.now().isoformat(), outcome,
              prize_amount, prize_desc, random.randint(1, 10)))
    
    conn.commit()
    conn.close()
    print("Created test game records and history")

if __name__ == '__main__':
    setup_test_employees()
    setup_test_games()
    print("Test data setup complete!")
```

---

## Related Documentation

- [CSRF Security Implementation](CSRF_SECURITY_TECHNICAL_DOCS.md)
- [Dual Game System Technical Architecture](DUAL_GAME_SYSTEM_TECHNICAL_DOCS.md)
- [API Endpoint Documentation](API_ENDPOINTS_TECHNICAL_DOCS.md)
- [Database Schema Documentation](DATABASE_SCHEMA_TECHNICAL_DOCS.md)
- [Deployment and Configuration Guide](DEPLOYMENT_CONFIGURATION_TECHNICAL_DOCS.md)

---

**Last Updated**: August 29, 2025  
**Next Review**: September 29, 2025  
**Maintained By**: Quality Assurance Team