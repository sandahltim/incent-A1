# tests/conftest.py
# Pytest configuration and shared fixtures for the Employee Incentive System test suite
# Version: 1.0.0

import pytest
import os
import sys
import tempfile
import sqlite3
import shutil
from unittest.mock import Mock, patch, MagicMock
from contextlib import contextmanager
import threading
import time
from datetime import datetime, timedelta

# Add the parent directory to the Python path to import the application modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import application modules
import app
from app import app as flask_app
import incentive_service
from config import Config
from services.cache import get_cache_manager, get_invalidation_manager
from services.analytics import AnalyticsService
from services.auth import AuthService


class TestConfig:
    """Test configuration class"""
    TESTING = True
    SECRET_KEY = 'test-secret-key-for-testing-only'
    WTF_CSRF_ENABLED = False  # Disable CSRF for testing
    DATABASE_URL = None  # Will be set per test
    INCENTIVE_DB_FILE = None  # Will be set per test


@pytest.fixture(scope="session")
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp(prefix="incentive_test_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def test_db_path(temp_dir):
    """Create a temporary database file path"""
    return os.path.join(temp_dir, "test_incentive.db")


@pytest.fixture
def test_config(test_db_path):
    """Create test configuration"""
    config = TestConfig()
    config.INCENTIVE_DB_FILE = test_db_path
    config.DATABASE_URL = f"sqlite:///{test_db_path}"
    return config


@pytest.fixture
def test_app(test_config):
    """Create a test Flask application"""
    # Patch the config before creating the app
    with patch.object(Config, 'INCENTIVE_DB_FILE', test_config.INCENTIVE_DB_FILE), \
         patch.object(Config, 'DATABASE_URL', test_config.DATABASE_URL), \
         patch.object(Config, 'TESTING', True), \
         patch.object(Config, 'WTF_CSRF_ENABLED', False):
        
        # Create a new Flask app instance for testing
        test_app = app.Flask(__name__)
        test_app.config.from_object(test_config)
        
        # Initialize CSRF protection but disable it for testing
        from flask_wtf.csrf import CSRFProtect
        csrf = CSRFProtect(test_app)
        
        # Add the same context processors and filters as the main app
        test_app.jinja_env.filters['zip'] = zip
        test_app.jinja_env.filters['from_json'] = app.from_json
        
        yield test_app


@pytest.fixture
def client(test_app):
    """Create a test client"""
    return test_app.test_client()


@pytest.fixture
def app_context(test_app):
    """Create application context"""
    with test_app.app_context():
        yield test_app


@pytest.fixture
def request_context(test_app):
    """Create request context"""
    with test_app.test_request_context():
        yield test_app


@pytest.fixture
def init_test_db(test_db_path):
    """Initialize test database with schema and sample data"""
    # Create the database directory if it doesn't exist
    os.makedirs(os.path.dirname(test_db_path), exist_ok=True)
    
    # Create database and initialize schema
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    # Create tables (based on init_db.py schema)
    cursor.execute('''
        CREATE TABLE employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            pin TEXT NOT NULL UNIQUE,
            score INTEGER DEFAULT 0,
            role TEXT DEFAULT 'employee',
            is_active INTEGER DEFAULT 1,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id INTEGER NOT NULL,
            voted_for_id INTEGER NOT NULL,
            vote_type TEXT NOT NULL,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT,
            FOREIGN KEY (voter_id) REFERENCES employees (id),
            FOREIGN KEY (voted_for_id) REFERENCES employees (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE voting_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT UNIQUE NOT NULL,
            status TEXT DEFAULT 'active',
            start_time TEXT DEFAULT CURRENT_TIMESTAMP,
            end_time TEXT,
            paused_time TEXT,
            total_paused_duration INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE point_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            points_changed INTEGER NOT NULL,
            reason TEXT,
            admin_id INTEGER,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id),
            FOREIGN KEY (admin_id) REFERENCES employees (id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            points INTEGER NOT NULL,
            display_order INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE mini_game_plays (
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
    
    cursor.execute('''
        CREATE TABLE settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            value TEXT,
            description TEXT,
            last_updated TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (employee_id) REFERENCES employees (id)
        )
    ''')
    
    # Insert sample employees
    sample_employees = [
        ("Admin User", "0000", 0, "admin", 1),
        ("John Doe", "1234", 100, "employee", 1),
        ("Jane Smith", "5678", 150, "employee", 1),
        ("Bob Johnson", "9999", 75, "employee", 1),
        ("Alice Wilson", "1111", 200, "employee", 1),
        ("Inactive User", "0001", 50, "employee", 0)
    ]
    
    cursor.executemany(
        "INSERT INTO employees (name, pin, score, role, is_active) VALUES (?, ?, ?, ?, ?)",
        sample_employees
    )
    
    # Insert sample rules
    sample_rules = [
        ("Punctuality", "Arriving on time for work", 10, 1, 1),
        ("Customer Service", "Providing excellent customer service", 15, 2, 1),
        ("Teamwork", "Working well with team members", 12, 3, 1),
        ("Initiative", "Taking initiative on projects", 20, 4, 1)
    ]
    
    cursor.executemany(
        "INSERT INTO rules (title, description, points, display_order, is_active) VALUES (?, ?, ?, ?, ?)",
        sample_rules
    )
    
    # Insert sample settings
    sample_settings = [
        ("site_name", "Test Incentive System", "Site name for testing"),
        ("primary_color", "#D4AF37", "Primary theme color"),
        ("money_threshold", "50", "Minimum points needed for money prize"),
        ("scoreboard_spin_duration", "10", "Duration of scoreboard spin animation"),
        ("vote_time_limit", "300", "Time limit for voting in seconds")
    ]
    
    cursor.executemany(
        "INSERT INTO settings (key, value, description) VALUES (?, ?, ?)",
        sample_settings
    )
    
    conn.commit()
    conn.close()
    
    yield test_db_path
    
    # Cleanup
    if os.path.exists(test_db_path):
        os.remove(test_db_path)


@pytest.fixture
def mock_cache_manager():
    """Mock cache manager for testing"""
    cache_manager = Mock()
    cache_manager.get.return_value = None
    cache_manager.set.return_value = True
    cache_manager.delete.return_value = True
    cache_manager.clear.return_value = True
    cache_manager.get_stats.return_value = {
        'hits': 0, 'misses': 0, 'sets': 0, 'deletes': 0, 'size': 0
    }
    return cache_manager


@pytest.fixture
def mock_invalidation_manager():
    """Mock cache invalidation manager for testing"""
    invalidation_manager = Mock()
    invalidation_manager.invalidate_pattern.return_value = True
    invalidation_manager.invalidate_tags.return_value = True
    invalidation_manager.register_dependency.return_value = True
    return invalidation_manager


@pytest.fixture
def mock_analytics_service():
    """Mock analytics service for testing"""
    analytics = Mock(spec=AnalyticsService)
    analytics.track_event.return_value = True
    analytics.track_vote.return_value = True
    analytics.track_mini_game.return_value = True
    analytics.get_stats.return_value = {}
    return analytics


@pytest.fixture
def mock_auth_service():
    """Mock authentication service for testing"""
    auth = Mock(spec=AuthService)
    auth.verify_pin.return_value = True
    auth.is_admin.return_value = False
    auth.is_employee_active.return_value = True
    auth.hash_pin.return_value = "hashed_pin"
    return auth


@pytest.fixture
def db_connection(test_db_path, init_test_db):
    """Create a database connection for testing"""
    with patch.object(Config, 'INCENTIVE_DB_FILE', test_db_path):
        conn = sqlite3.connect(test_db_path)
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()


@pytest.fixture
def admin_session(client):
    """Create an admin session for testing admin functionality"""
    with client.session_transaction() as sess:
        sess['admin_logged_in'] = True
        sess['admin_id'] = 1
        sess['admin_name'] = 'Admin User'


@pytest.fixture
def employee_session(client):
    """Create an employee session for testing employee functionality"""
    with client.session_transaction() as sess:
        sess['employee_id'] = 2
        sess['employee_name'] = 'John Doe'
        sess['employee_logged_in'] = True


@pytest.fixture
def voting_session_active(db_connection):
    """Create an active voting session"""
    cursor = db_connection.cursor()
    session_id = f"test_session_{int(time.time())}"
    cursor.execute(
        "INSERT INTO voting_sessions (session_id, status, start_time) VALUES (?, 'active', ?)",
        (session_id, datetime.now().isoformat())
    )
    db_connection.commit()
    yield session_id


@contextmanager
def temporary_file(content="", suffix=".tmp"):
    """Context manager for creating temporary files"""
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
        f.write(content)
        temp_path = f.name
    
    try:
        yield temp_path
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


@pytest.fixture
def mock_connection_pool():
    """Mock database connection pool for testing"""
    pool = Mock()
    mock_connection = Mock()
    mock_connection.cursor.return_value = Mock()
    mock_connection.commit.return_value = None
    mock_connection.rollback.return_value = None
    mock_connection.close.return_value = None
    
    pool.get_connection.return_value = mock_connection
    pool.return_connection.return_value = None
    pool.close_all.return_value = None
    pool.get_stats.return_value = {
        'active_connections': 0,
        'available_connections': 5,
        'total_connections': 5
    }
    
    return pool


# Performance testing helpers
@pytest.fixture
def performance_timer():
    """Context manager for timing operations"""
    @contextmanager
    def timer():
        start_time = time.time()
        yield lambda: time.time() - start_time
    
    return timer


# Mock data generators
def generate_mock_employees(count=10):
    """Generate mock employee data"""
    employees = []
    for i in range(count):
        employees.append({
            'id': i + 1,
            'name': f'Employee {i + 1}',
            'pin': f'{i:04d}',
            'score': i * 10,
            'role': 'employee',
            'is_active': 1
        })
    return employees


def generate_mock_votes(employee_count=5, vote_count=20):
    """Generate mock vote data"""
    votes = []
    for i in range(vote_count):
        votes.append({
            'id': i + 1,
            'voter_id': (i % employee_count) + 1,
            'voted_for_id': ((i + 1) % employee_count) + 1,
            'vote_type': 'positive',
            'timestamp': datetime.now().isoformat(),
            'session_id': 'test_session'
        })
    return votes


# Pytest configuration
def pytest_configure(config):
    """Configure pytest settings"""
    config.addinivalue_line(
        "markers", 
        "integration: marks tests as integration tests (may be slower)"
    )
    config.addinivalue_line(
        "markers", 
        "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", 
        "mobile: marks tests as mobile/responsive tests"
    )
    config.addinivalue_line(
        "markers", 
        "database: marks tests that require database access"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test names"""
    for item in items:
        # Add integration marker for integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add performance marker for performance tests
        if "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)
        
        # Add mobile marker for mobile tests
        if "mobile" in item.name.lower():
            item.add_marker(pytest.mark.mobile)
        
        # Add database marker for database tests
        if "database" in item.name.lower() or "db" in item.name.lower():
            item.add_marker(pytest.mark.database)


# Test utilities
class TestUtils:
    """Utility class for common test operations"""
    
    @staticmethod
    def create_test_employee(conn, name="Test Employee", pin="1234", score=100, role="employee"):
        """Create a test employee in the database"""
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO employees (name, pin, score, role) VALUES (?, ?, ?, ?)",
            (name, pin, score, role)
        )
        conn.commit()
        return cursor.lastrowid
    
    @staticmethod
    def create_test_vote(conn, voter_id, voted_for_id, vote_type="positive", session_id="test"):
        """Create a test vote in the database"""
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO votes (voter_id, voted_for_id, vote_type, session_id) VALUES (?, ?, ?, ?)",
            (voter_id, voted_for_id, vote_type, session_id)
        )
        conn.commit()
        return cursor.lastrowid
    
    @staticmethod
    def create_voting_session(conn, session_id="test_session", status="active"):
        """Create a test voting session"""
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO voting_sessions (session_id, status) VALUES (?, ?)",
            (session_id, status)
        )
        conn.commit()
        return cursor.lastrowid


@pytest.fixture
def test_utils():
    """Provide test utility functions"""
    return TestUtils