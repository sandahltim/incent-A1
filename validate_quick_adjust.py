#!/usr/bin/env python3
"""
Quick Adjust System Validation and Testing
This script validates the quick adjust functionality and reports on any issues found.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime

# ANSI color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def check_mark(status):
    return f"{Colors.OKGREEN}✓{Colors.ENDC}" if status else f"{Colors.FAIL}✗{Colors.ENDC}"

def status_text(status):
    return f"{Colors.OKGREEN}WORKING{Colors.ENDC}" if status else f"{Colors.FAIL}NEEDS FIX{Colors.ENDC}"

print(f"\n{Colors.HEADER}{Colors.BOLD}=== QUICK ADJUST FUNCTIONALITY VALIDATION ==={Colors.ENDC}\n")
print(f"Test Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

# Test results tracking
issues_found = []
suggestions = []

# 1. DATABASE VALIDATION
print(f"{Colors.BOLD}1. DATABASE STRUCTURE{Colors.ENDC}")
print("-" * 40)

try:
    conn = sqlite3.connect('incentive.db')
    cursor = conn.cursor()
    
    # Check incentive_rules table
    cursor.execute("SELECT COUNT(*) FROM incentive_rules")
    rules_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM incentive_rules WHERE points > 0")
    positive_rules = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM incentive_rules WHERE points < 0")
    negative_rules = cursor.fetchone()[0]
    
    print(f"{check_mark(rules_count > 0)} Point rules configured: {rules_count} total")
    print(f"   - Positive rules: {positive_rules}")
    print(f"   - Negative rules: {negative_rules}")
    
    if rules_count == 0:
        issues_found.append("No point rules configured in database")
        suggestions.append("Add point rules through the admin panel")
    
    # Check employees
    cursor.execute("SELECT COUNT(*) FROM employees WHERE active = 1")
    active_employees = cursor.fetchone()[0]
    print(f"{check_mark(active_employees > 0)} Active employees: {active_employees}")
    
    # Check settings
    cursor.execute("SELECT value FROM settings WHERE key = 'cat_a_award_chance_points'")
    cat_a_chance = cursor.fetchone()
    print(f"{check_mark(cat_a_chance)} Category A award chance: {cat_a_chance[0] if cat_a_chance else 'Not set'}%")
    
    conn.close()
    
except Exception as e:
    print(f"{Colors.FAIL}Database error: {str(e)}{Colors.ENDC}")
    issues_found.append(f"Database connection error: {str(e)}")

# 2. TEMPLATE VALIDATION
print(f"\n{Colors.BOLD}2. HTML TEMPLATE COMPONENTS{Colors.ENDC}")
print("-" * 40)

template_path = 'templates/incentive.html'
if os.path.exists(template_path):
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    components = {
        'Quick adjust links': 'quick-adjust-link',
        'Modal definition': 'quickAdjustModal',
        'Form element': 'adjustPointsForm',
        'Employee dropdown': 'quick_adjust_employee_id',
        'Points input': 'quick_adjust_points',
        'Reason select': 'quick_adjust_reason',
        'Data attributes': 'data-points=',
        'Point conditions': 'Point Conditions'
    }
    
    for name, search_str in components.items():
        found = search_str in template_content
        print(f"{check_mark(found)} {name}")
        if not found:
            issues_found.append(f"Missing template component: {name}")
else:
    print(f"{Colors.FAIL}Template file not found!{Colors.ENDC}")
    issues_found.append("Template file templates/incentive.html not found")

# 3. JAVASCRIPT VALIDATION
print(f"\n{Colors.BOLD}3. JAVASCRIPT IMPLEMENTATION{Colors.ENDC}")
print("-" * 40)

js_path = 'static/script.js'
if os.path.exists(js_path):
    with open(js_path, 'r') as f:
        js_content = f.read()
    
    js_components = {
        'Click handler': 'handleQuickAdjustClick',
        'Event listeners': ".querySelectorAll('.quick-adjust-link')",
        'Modal handling': 'bootstrap.Modal',
        'Form submission': "adjustPointsForm.*addEventListener\\('submit'",
        'AJAX endpoint': 'admin_quick_adjust_points',
        'Game award check': 'game_awarded',
        'Audio feedback': 'playSlotSound',
        'Success handling': 'playJackpot'
    }
    
    for name, search_str in js_components.items():
        found = search_str in js_content
        print(f"{check_mark(found)} {name}")
        if not found and name in ['Click handler', 'Event listeners', 'Form submission']:
            issues_found.append(f"Missing JavaScript component: {name}")
else:
    print(f"{Colors.FAIL}JavaScript file not found!{Colors.ENDC}")
    issues_found.append("JavaScript file static/script.js not found")

# 4. BACKEND ROUTES
print(f"\n{Colors.BOLD}4. BACKEND IMPLEMENTATION{Colors.ENDC}")
print("-" * 40)

app_path = 'app.py'
if os.path.exists(app_path):
    with open(app_path, 'r') as f:
        app_content = f.read()
    
    backend_components = {
        'Quick adjust route': '@app.route("/quick_adjust"',
        'Admin adjust route': '@app.route("/admin/quick_adjust_points"',
        'Form class': 'QuickAdjustForm',
        'Point adjustment': 'adjust_points(',
        'Game integration': 'award_category_a_game',
        'Authentication': 'check_password_hash',
        'Session handling': "session['admin_id']"
    }
    
    for name, search_str in backend_components.items():
        found = search_str in app_content
        print(f"{check_mark(found)} {name}")
        if not found and name in ['Quick adjust route', 'Admin adjust route']:
            issues_found.append(f"Missing backend component: {name}")
else:
    print(f"{Colors.FAIL}Application file not found!{Colors.ENDC}")
    issues_found.append("Application file app.py not found")

# 5. CSS STYLING
print(f"\n{Colors.BOLD}5. CSS STYLING{Colors.ENDC}")
print("-" * 40)

css_files = ['static/style.css', 'static/casino-theme.css']
css_found = False
for css_file in css_files:
    if os.path.exists(css_file):
        with open(css_file, 'r') as f:
            css_content = f.read()
        if '.quick-adjust-link' in css_content:
            css_found = True
            print(f"{check_mark(True)} Quick adjust styles in {css_file}")
            break

if not css_found:
    print(f"{check_mark(False)} Quick adjust styles not found")
    suggestions.append("Consider adding hover effects for .quick-adjust-link class")

# 6. INTEGRATION TEST POINTS
print(f"\n{Colors.BOLD}6. INTEGRATION POINTS{Colors.ENDC}")
print("-" * 40)

integration_checks = []

# Check if forms.py has QuickAdjustForm
if os.path.exists('forms.py'):
    with open('forms.py', 'r') as f:
        if 'class QuickAdjustForm' in f.read():
            integration_checks.append(('QuickAdjustForm defined', True))
        else:
            integration_checks.append(('QuickAdjustForm defined', False))
            issues_found.append("QuickAdjustForm not found in forms.py")

# Check if incentive_service.py has adjust_points
if os.path.exists('incentive_service.py'):
    with open('incentive_service.py', 'r') as f:
        if 'def adjust_points' in f.read():
            integration_checks.append(('adjust_points function', True))
        else:
            integration_checks.append(('adjust_points function', False))
            issues_found.append("adjust_points function not found in incentive_service.py")

# Check for dual game manager
if os.path.exists('services/dual_game_manager.py'):
    integration_checks.append(('Dual game manager', True))
else:
    integration_checks.append(('Dual game manager', False))
    suggestions.append("Dual game manager service not found - mini-games may not work")

for check_name, status in integration_checks:
    print(f"{check_mark(status)} {check_name}")

# SUMMARY
print(f"\n{Colors.HEADER}{Colors.BOLD}=== VALIDATION SUMMARY ==={Colors.ENDC}\n")

if not issues_found:
    print(f"{Colors.OKGREEN}{Colors.BOLD}✓ ALL CHECKS PASSED!{Colors.ENDC}")
    print(f"\nThe quick adjust functionality appears to be {Colors.OKGREEN}FULLY FUNCTIONAL{Colors.ENDC}")
    print("\nExpected behavior:")
    print("1. Point condition items are clickable on the main page")
    print("2. Clicking opens a modal with pre-filled points and reason")
    print("3. Admin authentication is required for non-logged-in users")
    print("4. Successful submission updates points and may award Category A games")
    print("5. Visual and audio feedback confirms the action")
else:
    print(f"{Colors.FAIL}{Colors.BOLD}✗ ISSUES FOUND ({len(issues_found)}){Colors.ENDC}\n")
    for i, issue in enumerate(issues_found, 1):
        print(f"  {i}. {Colors.FAIL}{issue}{Colors.ENDC}")

if suggestions:
    print(f"\n{Colors.WARNING}{Colors.BOLD}SUGGESTIONS FOR IMPROVEMENT:{Colors.ENDC}\n")
    for i, suggestion in enumerate(suggestions, 1):
        print(f"  {i}. {Colors.WARNING}{suggestion}{Colors.ENDC}")

# TESTING CHECKLIST
print(f"\n{Colors.BOLD}MANUAL TESTING CHECKLIST:{Colors.ENDC}")
print("-" * 40)
print("[ ] Start the Flask application")
print("[ ] Navigate to the main page")
print("[ ] Verify point conditions are visible with + and - rules")
print("[ ] Click on a positive point rule")
print("[ ] Verify modal opens with pre-filled points and reason")
print("[ ] Select an employee from dropdown")
print("[ ] Add optional notes")
print("[ ] Submit the form (provide admin credentials if needed)")
print("[ ] Verify success message appears")
print("[ ] Check if employee's score updated on scoreboard")
print("[ ] Test negative point rules as well")
print("[ ] Monitor for Category A game awards (15% chance on positive)")
print("[ ] Check browser console for JavaScript errors")
print("[ ] Test on mobile device for responsive behavior")

print(f"\n{Colors.OKBLUE}Test completed at {datetime.now().strftime('%H:%M:%S')}{Colors.ENDC}\n")

# Exit with appropriate code
sys.exit(0 if not issues_found else 1)