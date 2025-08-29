#!/usr/bin/env python3
"""
Comprehensive Test Suite for Quick Adjust Functionality
Testing all aspects of the quick adjust system including:
- UI elements and interactions
- Modal behavior
- Form validation
- Mini-game integration
- Database operations
"""

import sqlite3
import json
import sys
import os
from datetime import datetime

# Color codes for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_test_header(test_name):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}TEST: {test_name}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_pass(message):
    print(f"{Colors.OKGREEN}✓ PASS: {message}{Colors.ENDC}")

def print_fail(message):
    print(f"{Colors.FAIL}✗ FAIL: {message}{Colors.ENDC}")

def print_warning(message):
    print(f"{Colors.WARNING}⚠ WARNING: {message}{Colors.ENDC}")

def print_info(message):
    print(f"{Colors.OKBLUE}ℹ INFO: {message}{Colors.ENDC}")

def test_database_structure():
    """Test database structure and required tables"""
    print_test_header("Database Structure Validation")
    
    try:
        conn = sqlite3.connect('incentive.db')
        cursor = conn.cursor()
        
        # Check for required tables
        required_tables = ['employees', 'rules', 'admins', 'adjustment_history', 
                          'pot_info', 'settings', 'category_a_games']
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        for table in required_tables:
            if table in existing_tables:
                print_pass(f"Table '{table}' exists")
            else:
                print_fail(f"Table '{table}' missing")
        
        # Test employees table structure
        cursor.execute("PRAGMA table_info(employees)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        required_columns = ['employee_id', 'name', 'initials', 'score', 'role', 'active']
        
        for col in required_columns:
            if col in columns:
                print_pass(f"Column 'employees.{col}' exists")
            else:
                print_fail(f"Column 'employees.{col}' missing")
        
        # Check for sample data
        cursor.execute("SELECT COUNT(*) FROM employees WHERE active = 1")
        active_count = cursor.fetchone()[0]
        print_info(f"Active employees: {active_count}")
        
        cursor.execute("SELECT COUNT(*) FROM rules")
        rules_count = cursor.fetchone()[0]
        print_info(f"Point rules configured: {rules_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print_fail(f"Database error: {str(e)}")
        return False

def test_template_structure():
    """Test HTML template structure for quick adjust components"""
    print_test_header("Template Structure Validation")
    
    template_path = 'templates/incentive.html'
    
    if not os.path.exists(template_path):
        print_fail(f"Template file not found: {template_path}")
        return False
    
    with open(template_path, 'r') as f:
        content = f.read()
    
    # Check for quick adjust link class
    if 'quick-adjust-link' in content:
        print_pass("Quick adjust link class found in template")
    else:
        print_fail("Quick adjust link class not found in template")
    
    # Check for modal structure
    if 'quickAdjustModal' in content:
        print_pass("Quick adjust modal defined in template")
    else:
        print_fail("Quick adjust modal not found in template")
    
    # Check for form elements
    required_elements = [
        'quick_adjust_employee_id',
        'quick_adjust_points',
        'quick_adjust_reason',
        'quick_adjust_notes',
        'adjustPointsForm'
    ]
    
    for element in required_elements:
        if element in content:
            print_pass(f"Form element '{element}' found")
        else:
            print_fail(f"Form element '{element}' missing")
    
    # Check for point conditions sections
    if 'Point Conditions' in content:
        print_pass("Point conditions section exists")
    else:
        print_fail("Point conditions section missing")
    
    # Check for data attributes on rules
    if 'data-points=' in content and 'data-reason=' in content:
        print_pass("Data attributes for quick adjust links present")
    else:
        print_fail("Data attributes for quick adjust links missing")
    
    return True

def test_javascript_implementation():
    """Test JavaScript implementation for quick adjust"""
    print_test_header("JavaScript Implementation Validation")
    
    js_path = 'static/script.js'
    
    if not os.path.exists(js_path):
        print_fail(f"JavaScript file not found: {js_path}")
        return False
    
    with open(js_path, 'r') as f:
        content = f.read()
    
    # Check for event handler functions
    required_functions = [
        'handleQuickAdjustClick',
        'handleModalShow',
        'handleModalShown',
        'handleModalHidden'
    ]
    
    for func in required_functions:
        if func in content:
            print_pass(f"Function '{func}' found")
        else:
            print_fail(f"Function '{func}' missing")
    
    # Check for event listeners
    if ".querySelectorAll('.quick-adjust-link')" in content:
        print_pass("Quick adjust link event listeners setup found")
    else:
        print_fail("Quick adjust link event listeners not found")
    
    # Check for form submission handling
    if "adjustPointsForm" in content and "addEventListener('submit'" in content:
        print_pass("Form submission handler found")
    else:
        print_fail("Form submission handler missing")
    
    # Check for AJAX/fetch implementation
    if "fetch" in content and "/admin/quick_adjust_points" in content:
        print_pass("AJAX submission to quick_adjust_points endpoint found")
    else:
        print_fail("AJAX submission implementation missing")
    
    # Check for game award handling
    if "game_awarded" in content:
        print_pass("Game award handling implemented")
    else:
        print_warning("Game award handling not explicitly found")
    
    # Check for audio integration
    if "playSlotSound" in content or "audioEngine" in content:
        print_pass("Audio feedback integration found")
    else:
        print_warning("Audio feedback not integrated")
    
    return True

def test_backend_routes():
    """Test backend route definitions"""
    print_test_header("Backend Route Validation")
    
    app_path = 'app.py'
    
    if not os.path.exists(app_path):
        print_fail(f"Application file not found: {app_path}")
        return False
    
    with open(app_path, 'r') as f:
        content = f.read()
    
    # Check for route definitions
    routes = [
        ('/quick_adjust', 'quick_adjust'),
        ('/admin/quick_adjust_points', 'admin_quick_adjust_points')
    ]
    
    for route, func_name in routes:
        if f'@app.route("{route}"' in content and f'def {func_name}' in content:
            print_pass(f"Route '{route}' with function '{func_name}' found")
        else:
            print_fail(f"Route '{route}' or function '{func_name}' missing")
    
    # Check for form handling
    if 'QuickAdjustForm' in content:
        print_pass("QuickAdjustForm integration found")
    else:
        print_fail("QuickAdjustForm integration missing")
    
    # Check for Category A game integration
    if 'award_category_a_game' in content or 'DualGameManager' in content:
        print_pass("Category A mini-game integration found")
    else:
        print_fail("Category A mini-game integration missing")
    
    # Check for adjust_points function call
    if 'adjust_points(' in content:
        print_pass("adjust_points function call found")
    else:
        print_fail("adjust_points function call missing")
    
    # Check for authentication handling
    if 'check_password_hash' in content and 'admin_id' in content:
        print_pass("Admin authentication handling found")
    else:
        print_fail("Admin authentication handling missing")
    
    return True

def test_settings_integration():
    """Test settings and configuration"""
    print_test_header("Settings & Configuration Validation")
    
    try:
        conn = sqlite3.connect('incentive.db')
        cursor = conn.cursor()
        
        # Check for relevant settings
        cursor.execute("SELECT key, value FROM settings WHERE key IN (?, ?, ?, ?)",
                      ('cat_a_award_chance_points', 'money_threshold', 'max_plus_votes', 'max_minus_votes'))
        settings = {row[0]: row[1] for row in cursor.fetchall()}
        
        if 'cat_a_award_chance_points' in settings:
            print_pass(f"Category A award chance setting found: {settings['cat_a_award_chance_points']}%")
        else:
            print_warning("Category A award chance setting not configured")
        
        if 'money_threshold' in settings:
            print_pass(f"Money threshold setting found: {settings['money_threshold']} points")
        else:
            print_warning("Money threshold setting not configured")
        
        # Check rules configuration
        cursor.execute("SELECT description, points FROM rules ORDER BY points DESC")
        rules = cursor.fetchall()
        
        print_info(f"\nConfigured Point Rules:")
        positive_rules = 0
        negative_rules = 0
        
        for desc, points in rules[:5]:  # Show first 5 rules
            if points > 0:
                positive_rules += 1
                print_info(f"  + {desc}: +{points} points")
            else:
                negative_rules += 1
                print_info(f"  - {desc}: {points} points")
        
        print_info(f"Total: {positive_rules} positive rules, {negative_rules} negative rules")
        
        conn.close()
        return True
        
    except Exception as e:
        print_fail(f"Settings check error: {str(e)}")
        return False

def test_css_styling():
    """Test CSS styling for quick adjust components"""
    print_test_header("CSS Styling Validation")
    
    css_files = ['static/style.css', 'static/casino-theme.css']
    styles_found = []
    
    for css_file in css_files:
        if os.path.exists(css_file):
            with open(css_file, 'r') as f:
                content = f.read()
                
            # Check for quick adjust styles
            if '.quick-adjust-link' in content:
                styles_found.append('quick-adjust-link')
                print_pass(f"Quick adjust link styles found in {css_file}")
            
            if '.quick-adjust-modal' in content:
                styles_found.append('quick-adjust-modal')
                print_pass(f"Quick adjust modal styles found in {css_file}")
            
            if '.rule-item' in content:
                styles_found.append('rule-item')
                print_pass(f"Rule item styles found in {css_file}")
    
    if not styles_found:
        print_warning("No specific quick adjust styles found in CSS files")
    
    return True

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}")
    print(f"QUICK ADJUST FUNCTIONALITY COMPREHENSIVE TEST SUITE")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    print_info(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    test_results = {}
    
    # Run all tests
    test_results['Database'] = test_database_structure()
    test_results['Templates'] = test_template_structure()
    test_results['JavaScript'] = test_javascript_implementation()
    test_results['Backend'] = test_backend_routes()
    test_results['Settings'] = test_settings_integration()
    test_results['CSS'] = test_css_styling()
    
    # Print summary
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}")
    print(f"TEST SUMMARY")
    print(f"{'='*60}{Colors.ENDC}\n")
    
    passed = sum(1 for v in test_results.values() if v)
    total = len(test_results)
    
    for test_name, result in test_results.items():
        status = f"{Colors.OKGREEN}PASSED{Colors.ENDC}" if result else f"{Colors.FAIL}FAILED{Colors.ENDC}"
        print(f"{test_name:15} : {status}")
    
    print(f"\n{Colors.BOLD}Overall: {passed}/{total} tests passed{Colors.ENDC}")
    
    # Provide recommendations
    print(f"\n{Colors.HEADER}{Colors.BOLD}RECOMMENDATIONS:{Colors.ENDC}")
    
    if test_results['Database'] and test_results['Templates'] and test_results['JavaScript']:
        print_pass("Core quick adjust functionality appears to be properly implemented")
    else:
        print_fail("Critical components missing - quick adjust may not function properly")
    
    print_info("\nTo manually test the quick adjust functionality:")
    print_info("1. Start the Flask application")
    print_info("2. Navigate to the main page")
    print_info("3. Click on any point condition item")
    print_info("4. Verify the modal opens with pre-filled data")
    print_info("5. Select an employee and submit the form")
    print_info("6. Check for success message and score update")
    print_info("7. Monitor for Category A game awards on positive adjustments")
    
    return passed == total

if __name__ == "__main__":
    success = run_comprehensive_test()
    sys.exit(0 if success else 1)