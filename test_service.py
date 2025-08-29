#!/usr/bin/env python3
"""Comprehensive Flask Service Testing Script"""

import requests
import json
import sys
from datetime import datetime
from bs4 import BeautifulSoup

BASE_URL = "http://localhost:7410"
session = requests.Session()

def print_test(test_name, status, details=""):
    """Print test result with formatting"""
    symbol = "✓" if status else "✗"
    color = "\033[92m" if status else "\033[91m"
    reset = "\033[0m"
    print(f"{color}[{symbol}]{reset} {test_name}")
    if details:
        print(f"    {details}")

def test_homepage():
    """Test homepage accessibility"""
    try:
        response = session.get(f"{BASE_URL}/")
        return response.status_code == 200, f"Status: {response.status_code}"
    except Exception as e:
        return False, str(e)

def test_login_page():
    """Test login page and get CSRF token"""
    try:
        response = session.get(f"{BASE_URL}/login")
        if response.status_code != 200:
            return False, f"Status: {response.status_code}", None
        
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_token = soup.find('input', {'name': 'csrf_token'})
        if csrf_token:
            return True, "CSRF token found", csrf_token.get('value')
        return False, "No CSRF token found", None
    except Exception as e:
        return False, str(e), None

def test_login(csrf_token):
    """Test login with admin credentials"""
    try:
        login_data = {
            'username': 'admin',
            'password': 'admin',
            'csrf_token': csrf_token
        }
        response = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
        if response.status_code in [302, 303]:
            # Check if redirected to dashboard
            follow_response = session.get(f"{BASE_URL}/admin")
            return follow_response.status_code == 200, f"Login successful, admin page status: {follow_response.status_code}"
        return False, f"Login failed, status: {response.status_code}"
    except Exception as e:
        return False, str(e)

def test_api_endpoints():
    """Test critical API endpoints with CSRF protection"""
    results = []
    
    # Get CSRF token for API calls
    try:
        response = session.get(f"{BASE_URL}/admin")
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        csrf_token = csrf_meta.get('content') if csrf_meta else None
        
        if not csrf_token:
            return [(False, "Failed to get CSRF token for API calls")]
    except Exception as e:
        return [(False, f"Error getting CSRF token: {str(e)}")]
    
    # Test endpoints
    api_tests = [
        ("GET", "/api/game/stats", None, "Game stats endpoint"),
        ("GET", "/api/dual/leaderboard", None, "Dual game leaderboard"),
        ("GET", "/api/analytics/overview", None, "Analytics overview"),
        ("GET", "/api/analytics/charts/points", None, "Points chart data"),
        ("GET", "/api/settings/general", None, "General settings"),
    ]
    
    headers = {
        'X-CSRFToken': csrf_token,
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    for method, endpoint, data, description in api_tests:
        try:
            if method == "GET":
                response = session.get(f"{BASE_URL}{endpoint}", headers=headers)
            else:
                response = session.post(f"{BASE_URL}{endpoint}", json=data, headers=headers)
            
            success = response.status_code in [200, 201]
            details = f"{description} - Status: {response.status_code}"
            if success and response.headers.get('content-type', '').startswith('application/json'):
                try:
                    json_data = response.json()
                    details += f" - Valid JSON response"
                except:
                    success = False
                    details += f" - Invalid JSON response"
            results.append((success, details))
        except Exception as e:
            results.append((False, f"{description} - Error: {str(e)}"))
    
    return results

def test_settings_page():
    """Test settings page accessibility"""
    try:
        response = session.get(f"{BASE_URL}/admin/settings")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            # Check for settings form elements
            has_form = soup.find('form', {'id': 'settings-form'}) is not None
            has_tabs = soup.find('div', {'class': 'tab-content'}) is not None
            if has_form and has_tabs:
                return True, "Settings page loaded with form and tabs"
            elif has_form:
                return True, "Settings page loaded with form"
            else:
                return False, "Settings page missing expected elements"
        return False, f"Status: {response.status_code}"
    except Exception as e:
        return False, str(e)

def test_database_operations():
    """Test database connectivity through API"""
    try:
        response = session.get(f"{BASE_URL}/api/employees")
        if response.status_code == 200:
            employees = response.json()
            return True, f"Database accessible, {len(employees)} employees found"
        return False, f"Status: {response.status_code}"
    except Exception as e:
        return False, str(e)

def test_minigames():
    """Test mini-game endpoints"""
    results = []
    
    # Get CSRF token
    try:
        response = session.get(f"{BASE_URL}/admin")
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_meta = soup.find('meta', {'name': 'csrf-token'})
        csrf_token = csrf_meta.get('content') if csrf_meta else None
    except:
        csrf_token = None
    
    headers = {
        'X-CSRFToken': csrf_token,
        'X-Requested-With': 'XMLHttpRequest'
    } if csrf_token else {}
    
    # Test mini-game endpoints
    minigame_tests = [
        ("GET", "/api/minigame/status", "Mini-game status"),
        ("GET", "/api/minigame/leaderboard", "Mini-game leaderboard"),
        ("GET", "/api/game/config", "Game configuration"),
    ]
    
    for method, endpoint, description in minigame_tests:
        try:
            response = session.get(f"{BASE_URL}{endpoint}", headers=headers)
            success = response.status_code == 200
            details = f"{description} - Status: {response.status_code}"
            results.append((success, details))
        except Exception as e:
            results.append((False, f"{description} - Error: {str(e)}"))
    
    return results

def test_static_resources():
    """Test static resource availability"""
    static_tests = [
        "/static/css/main.css",
        "/static/js/admin.js",
        "/static/js/common.js",
    ]
    results = []
    
    for resource in static_tests:
        try:
            response = session.get(f"{BASE_URL}{resource}")
            success = response.status_code == 200
            details = f"{resource} - Status: {response.status_code}"
            results.append((success, details))
        except Exception as e:
            results.append((False, f"{resource} - Error: {str(e)}"))
    
    return results

def main():
    print("\n" + "="*60)
    print("Flask Service Comprehensive Test Suite")
    print(f"Testing: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60 + "\n")
    
    all_passed = True
    
    # Test 1: Homepage
    print("1. BASIC CONNECTIVITY")
    success, details = test_homepage()
    print_test("Homepage accessibility", success, details)
    all_passed = all_passed and success
    
    # Test 2: Login page and CSRF
    success, details, csrf_token = test_login_page()
    print_test("Login page and CSRF token", success, details)
    all_passed = all_passed and success
    
    # Test 3: Authentication
    print("\n2. AUTHENTICATION")
    if csrf_token:
        success, details = test_login(csrf_token)
        print_test("Admin login", success, details)
        all_passed = all_passed and success
    else:
        print_test("Admin login", False, "No CSRF token available")
        all_passed = False
    
    # Test 4: API Endpoints
    print("\n3. API ENDPOINTS WITH CSRF")
    api_results = test_api_endpoints()
    for success, details in api_results:
        print_test("API Test", success, details)
        all_passed = all_passed and success
    
    # Test 5: Settings Page
    print("\n4. UI PAGES")
    success, details = test_settings_page()
    print_test("Settings page accessibility", success, details)
    all_passed = all_passed and success
    
    # Test 6: Database
    print("\n5. DATABASE CONNECTIVITY")
    success, details = test_database_operations()
    print_test("Database operations", success, details)
    all_passed = all_passed and success
    
    # Test 7: Mini-games
    print("\n6. MINI-GAME SYSTEM")
    minigame_results = test_minigames()
    for success, details in minigame_results:
        print_test("Mini-game Test", success, details)
        all_passed = all_passed and success
    
    # Test 8: Static Resources
    print("\n7. STATIC RESOURCES")
    static_results = test_static_resources()
    for success, details in static_results:
        print_test("Static Resource", success, details)
        all_passed = all_passed and success
    
    # Summary
    print("\n" + "="*60)
    if all_passed:
        print("\033[92m✓ ALL TESTS PASSED\033[0m")
        print("The Flask service is fully operational on port 7410")
    else:
        print("\033[91m✗ SOME TESTS FAILED\033[0m")
        print("Please review the failed tests above")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())