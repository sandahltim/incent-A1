# Makefile for Employee Incentive System
# Version: 1.0.0

.PHONY: help install test test-unit test-integration test-performance test-coverage test-html clean lint format

# Default target
help:
	@echo "Employee Incentive System - Available Commands:"
	@echo "==============================================="
	@echo "install         - Install dependencies"
	@echo "install-test    - Install test dependencies"
	@echo "test            - Run all tests"
	@echo "test-unit       - Run unit tests only"
	@echo "test-integration - Run integration tests only"
	@echo "test-performance - Run performance tests only"
	@echo "test-mobile     - Run mobile tests only"
	@echo "test-api        - Run API tests only"
	@echo "test-games      - Run game tests only"
	@echo "test-voting     - Run voting tests only"
	@echo "test-coverage   - Run tests with coverage report"
	@echo "test-html       - Run tests with HTML report"
	@echo "test-fast       - Run tests in parallel"
	@echo "lint            - Run code linting"
	@echo "format          - Format code"
	@echo "clean           - Clean test artifacts"
	@echo "docs            - Generate documentation"
	@echo "backup          - Create database backup"

# Installation targets
install:
	pip install -r requirements.txt

install-test:
	pip install -r requirements.txt
	pip install -r requirements-test.txt

# Test targets
test:
	python run_tests.py --all

test-unit:
	python run_tests.py --unit

test-integration:
	python run_tests.py --integration

test-performance:
	python run_tests.py --performance

test-mobile:
	python run_tests.py --mobile

test-api:
	python run_tests.py --api

test-games:
	python run_tests.py --games

test-voting:
	python run_tests.py --voting

test-coverage:
	python run_tests.py --all --coverage-html

test-html:
	python run_tests.py --all --html --coverage-html

test-fast:
	python run_tests.py --all --parallel

test-verbose:
	python run_tests.py --all --verbose

test-quiet:
	python run_tests.py --all --quiet

# Code quality targets
lint:
	python run_tests.py --lint

format:
	@echo "Formatting Python code..."
	@if command -v black > /dev/null; then \
		black app.py incentive_service.py tests/ --line-length 88; \
	else \
		echo "Black not installed. Run: pip install black"; \
	fi
	@if command -v isort > /dev/null; then \
		isort app.py incentive_service.py tests/; \
	else \
		echo "isort not installed. Run: pip install isort"; \
	fi

# Cleanup targets
clean:
	@echo "Cleaning test artifacts..."
	rm -rf htmlcov/
	rm -rf .pytest_cache/
	rm -rf tests/__pycache__/
	rm -rf tests/*/__pycache__/
	rm -f tests/junit.xml
	rm -f tests/report.html
	rm -f tests/pytest.log
	rm -f .coverage
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# Development targets
dev-setup: install-test
	@echo "Setting up development environment..."
	@if command -v pre-commit > /dev/null; then \
		pre-commit install; \
		echo "Pre-commit hooks installed"; \
	else \
		echo "Pre-commit not available. Install with: pip install pre-commit"; \
	fi

# Database targets
backup:
	@echo "Creating database backup..."
	@if [ -f incentive.db ]; then \
		cp incentive.db "backups/incentive.db.bak-$$(date +%Y%m%d_%H%M%S)"; \
		echo "Backup created in backups/ directory"; \
	else \
		echo "No database file found"; \
	fi

backup-test:
	@echo "Creating test database..."
	python -c "from tests.conftest import *; import tempfile; import os; temp_dir = tempfile.mkdtemp(); test_db = os.path.join(temp_dir, 'test.db'); print(f'Test database created at: {test_db}')"

# Documentation targets
docs:
	@echo "Generating documentation..."
	@if [ -f tests/README.md ]; then \
		echo "Test documentation available at: tests/README.md"; \
	fi
	@echo "Application documentation available in README.md"

# CI/CD targets
ci-test: install-test test-coverage
	@echo "CI tests completed"

# Production targets
prod-check:
	@echo "Running production readiness checks..."
	python run_tests.py --check-deps
	python run_tests.py --lint
	python run_tests.py --all --quiet

# Monitoring targets
check-deps:
	pip check

security-check:
	@if command -v safety > /dev/null; then \
		safety check; \
	else \
		echo "Safety not installed. Run: pip install safety"; \
	fi
	@if command -v bandit > /dev/null; then \
		bandit -r app.py incentive_service.py; \
	else \
		echo "Bandit not installed. Run: pip install bandit"; \
	fi

# Quick development commands
quick-test:
	pytest tests/ -x -v

watch-tests:
	@if command -v ptw > /dev/null; then \
		ptw -- tests/ -v; \
	else \
		echo "pytest-watch not installed. Run: pip install pytest-watch"; \
		echo "Running tests once instead..."; \
		make test; \
	fi

# Help for specific test types
help-tests:
	@echo "Test Categories Available:"
	@echo "========================="
	@echo "Unit Tests:"
	@echo "  - test_app.py: Flask application core"
	@echo "  - test_database.py: Database operations"
	@echo "  - test_auth.py: Authentication system"
	@echo "  - test_caching.py: Cache performance"
	@echo ""
	@echo "Feature Tests:"
	@echo "  - test_games.py: Mini-games (slots, roulette, etc.)"
	@echo "  - test_voting.py: Voting system lifecycle"
	@echo "  - test_api.py: REST API endpoints"
	@echo "  - test_mobile.py: Mobile responsiveness"
	@echo ""
	@echo "Integration Tests:"
	@echo "  - integration/test_full_workflow.py: End-to-end workflows"
	@echo "  - integration/test_admin_flows.py: Admin operations"
	@echo ""
	@echo "Performance Tests:"
	@echo "  - test_performance.py: Load testing, benchmarks"