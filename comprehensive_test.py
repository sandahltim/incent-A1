#!/usr/bin/env python3
"""Comprehensive testing of the Flask incentive system after restart"""

import requests
import json
import sqlite3
from datetime import datetime
from bs4 import BeautifulSoup
import time

BASE_URL = "http://localhost:7410"

class IncentiveSystemTester:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        self.test_results = []
        self.admin_logged_in = False
        
    def print_result(self, category, test_name, passed, details=""):
        """Print and store test result"""
        status = "PASS" if passed else "FAIL"
        color = "\033[92m" if passed else "\033[91m"
        reset = "\033[0m"
        print(f"  {color}[{status}]{reset} {test_name}")
        if details:
            print(f"      {details}")
        self.test_results.append({
            "category": category,
            "test": test_name,
            "passed": passed,
            "details": details
        })
        
    def test_service_status(self):
        """Test basic service availability"""
        print("\n1. SERVICE STATUS TESTS")
        print("-" * 40)
        
        # Test homepage
        try:
            response = self.session.get(BASE_URL)
            self.print_result("Service", "Homepage accessible", 
                            response.status_code == 200,
                            f"Status: {response.status_code}")
            
            # Extract CSRF token
            soup = BeautifulSoup(response.text, 'html.parser')
            csrf_meta = soup.find('meta', {'name': 'csrf-token'})
            if csrf_meta:
                self.csrf_token = csrf_meta.get('content')
                self.print_result("Service", "CSRF token available", True)
            else:
                self.print_result("Service", "CSRF token available", False)
        except Exception as e:
            self.print_result("Service", "Homepage accessible", False, str(e))
            
        # Test port 7410
        try:
            import socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 7410))
            sock.close()
            self.print_result("Service", "Port 7410 listening", result == 0)
        except Exception as e:
            self.print_result("Service", "Port 7410 listening", False, str(e))
            
    def test_authentication(self):
        """Test authentication system"""
        print("\n2. AUTHENTICATION TESTS")
        print("-" * 40)
        
        if not self.csrf_token:
            self.print_result("Auth", "Admin login", False, "No CSRF token")
            return
            
        # Test admin login
        try:
            login_data = {
                'password': 'admin',
                'csrf_token': self.csrf_token
            }
            response = self.session.post(f"{BASE_URL}/admin", 
                                        data=login_data, 
                                        allow_redirects=False)
            
            if response.status_code in [200, 302, 303]:
                # Check if we can access admin panel
                admin_response = self.session.get(f"{BASE_URL}/admin")
                if admin_response.status_code == 200 and "Admin Panel" in admin_response.text:
                    self.admin_logged_in = True
                    self.print_result("Auth", "Admin login successful", True)
                    
                    # Update CSRF token from admin page
                    soup = BeautifulSoup(admin_response.text, 'html.parser')
                    csrf_meta = soup.find('meta', {'name': 'csrf-token'})
                    if csrf_meta:
                        self.csrf_token = csrf_meta.get('content')
                else:
                    self.print_result("Auth", "Admin login successful", False, 
                                    "Could not access admin panel")
            else:
                self.print_result("Auth", "Admin login successful", False,
                                f"Login failed with status {response.status_code}")
        except Exception as e:
            self.print_result("Auth", "Admin login successful", False, str(e))
            
    def test_database_connectivity(self):
        """Test database connectivity and data integrity"""
        print("\n3. DATABASE TESTS")
        print("-" * 40)
        
        # Direct database check
        try:
            conn = sqlite3.connect("incentive.db")
            cursor = conn.cursor()
            
            # Check employees
            cursor.execute("SELECT COUNT(*) FROM employees")
            employee_count = cursor.fetchone()[0]
            self.print_result("Database", "Employee table accessible", True,
                            f"{employee_count} employees found")
            
            # Check pot value
            cursor.execute("SELECT sales_dollars, bonus_percent FROM incentive_pot WHERE id=1")
            pot_data = cursor.fetchone()
            if pot_data:
                self.print_result("Database", "Pot data accessible", True,
                                f"Sales: ${pot_data[0]}, Bonus: {pot_data[1]}%")
            else:
                self.print_result("Database", "Pot data accessible", False)
                
            # Check settings
            cursor.execute("SELECT COUNT(*) FROM settings")
            settings_count = cursor.fetchone()[0]
            self.print_result("Database", "Settings table accessible", True,
                            f"{settings_count} settings found")
            
            conn.close()
        except Exception as e:
            self.print_result("Database", "Database connection", False, str(e))
            
        # Test via API
        try:
            response = self.session.get(f"{BASE_URL}/data")
            if response.status_code == 200:
                data = response.json()
                emp_count = len(data.get('employees', []))
                self.print_result("Database", "API data endpoint", 
                                emp_count > 0,
                                f"API returned {emp_count} employees")
            else:
                self.print_result("Database", "API data endpoint", False,
                                f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("Database", "API data endpoint", False, str(e))
            
    def test_csrf_protection(self):
        """Test CSRF protection on critical endpoints"""
        print("\n4. CSRF PROTECTION TESTS")
        print("-" * 40)
        
        if not self.csrf_token:
            self.print_result("CSRF", "Token availability", False)
            return
            
        headers = {
            'X-CSRFToken': self.csrf_token,
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/json'
        }
        
        # Test without CSRF token (should fail)
        try:
            response = self.session.post(f"{BASE_URL}/check_vote",
                                        json={'rfid': 'test'},
                                        headers={'Content-Type': 'application/json'})
            self.print_result("CSRF", "Protection active (no token)",
                            response.status_code == 400,
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("CSRF", "Protection active (no token)", False, str(e))
            
        # Test with CSRF token (should work)
        try:
            response = self.session.post(f"{BASE_URL}/check_vote",
                                        json={'rfid': 'test'},
                                        headers=headers)
            self.print_result("CSRF", "Token validation",
                            response.status_code in [200, 404],
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("CSRF", "Token validation", False, str(e))
            
    def test_ui_pages(self):
        """Test UI page accessibility"""
        print("\n5. UI PAGE TESTS")
        print("-" * 40)
        
        pages = [
            ("/", "Homepage"),
            ("/admin", "Admin Panel"),
            ("/admin/analytics", "Analytics Page"),
            ("/quick_adjust", "Quick Adjust Page"),
        ]
        
        for path, name in pages:
            try:
                response = self.session.get(f"{BASE_URL}{path}")
                self.print_result("UI", f"{name} accessible",
                                response.status_code == 200,
                                f"Status: {response.status_code}")
            except Exception as e:
                self.print_result("UI", f"{name} accessible", False, str(e))
                
    def test_static_resources(self):
        """Test static resource loading"""
        print("\n6. STATIC RESOURCE TESTS")
        print("-" * 40)
        
        resources = [
            "/static/style.min.css",
            "/static/script.min.js",
            "/static/audio-ui.min.css",
            "/favicon.ico"
        ]
        
        for resource in resources:
            try:
                response = self.session.get(f"{BASE_URL}{resource}")
                self.print_result("Static", f"{resource}",
                                response.status_code == 200,
                                f"Status: {response.status_code}")
            except Exception as e:
                self.print_result("Static", f"{resource}", False, str(e))
                
    def test_mini_game_system(self):
        """Test mini-game system functionality"""
        print("\n7. MINI-GAME SYSTEM TESTS")
        print("-" * 40)
        
        if not self.admin_logged_in:
            self.print_result("MiniGame", "System test", False, "Admin not logged in")
            return
            
        headers = {
            'X-CSRFToken': self.csrf_token,
            'X-Requested-With': 'XMLHttpRequest'
        }
        
        # Test game status
        try:
            response = self.session.get(f"{BASE_URL}/cache-stats", headers=headers)
            self.print_result("MiniGame", "Cache stats endpoint",
                            response.status_code in [200, 403],
                            f"Status: {response.status_code}")
        except Exception as e:
            self.print_result("MiniGame", "Cache stats endpoint", False, str(e))
            
    def test_performance(self):
        """Test response times"""
        print("\n8. PERFORMANCE TESTS")
        print("-" * 40)
        
        endpoints = [
            ("/", "Homepage"),
            ("/data", "Data API"),
        ]
        
        for path, name in endpoints:
            try:
                start = time.time()
                response = self.session.get(f"{BASE_URL}{path}")
                elapsed = time.time() - start
                
                # Consider < 2 seconds as acceptable
                is_fast = elapsed < 2.0
                self.print_result("Performance", f"{name} response time",
                                is_fast,
                                f"{elapsed:.2f} seconds")
            except Exception as e:
                self.print_result("Performance", f"{name} response time", False, str(e))
                
    def generate_summary(self):
        """Generate test summary"""
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        categories = {}
        for result in self.test_results:
            cat = result['category']
            if cat not in categories:
                categories[cat] = {'passed': 0, 'failed': 0}
            if result['passed']:
                categories[cat]['passed'] += 1
            else:
                categories[cat]['failed'] += 1
                
        total_passed = sum(c['passed'] for c in categories.values())
        total_failed = sum(c['failed'] for c in categories.values())
        total_tests = total_passed + total_failed
        
        print(f"\nTotal Tests: {total_tests}")
        print(f"Passed: {total_passed}")
        print(f"Failed: {total_failed}")
        print(f"Success Rate: {(total_passed/total_tests*100):.1f}%")
        
        print("\nBy Category:")
        for cat, stats in categories.items():
            total = stats['passed'] + stats['failed']
            rate = (stats['passed']/total*100) if total > 0 else 0
            print(f"  {cat}: {stats['passed']}/{total} ({rate:.0f}%)")
            
        print("\n" + "="*60)
        
        if total_failed == 0:
            print("\033[92m✓ ALL TESTS PASSED - System is fully operational!\033[0m")
        elif total_failed <= 3:
            print("\033[93m⚠ MINOR ISSUES - System is mostly operational\033[0m")
        else:
            print("\033[91m✗ CRITICAL ISSUES - System needs attention\033[0m")
            
        print("="*60)
        
def main():
    print("\n" + "="*60)
    print("INCENTIVE SYSTEM COMPREHENSIVE TEST")
    print(f"URL: {BASE_URL}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    tester = IncentiveSystemTester()
    
    # Run all tests
    tester.test_service_status()
    tester.test_authentication()
    tester.test_database_connectivity()
    tester.test_csrf_protection()
    tester.test_ui_pages()
    tester.test_static_resources()
    tester.test_mini_game_system()
    tester.test_performance()
    
    # Generate summary
    tester.generate_summary()
    
if __name__ == "__main__":
    main()