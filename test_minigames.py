#!/usr/bin/env python3
"""
Comprehensive Mini-Games Testing Script
Tests the enhanced Vegas casino mini-games system
"""

import requests
import json
import sqlite3
import time
from urllib.parse import urljoin

class MiniGamesDebugger:
    def __init__(self, base_url="http://localhost:7409"):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        self.db_path = "/home/tim/incentDev/incentive.db"
        
    def get_csrf_token(self):
        """Extract CSRF token from employee portal page"""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            if response.status_code == 200:
                import re
                match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
                    print(f"✓ CSRF token obtained: {self.csrf_token[:20]}...")
                    return True
            print("✗ Failed to get CSRF token")
            return False
        except Exception as e:
            print(f"✗ Error getting CSRF token: {e}")
            return False
    
    def test_employee_login(self, employee_id="E002", pin="1234"):
        """Test employee login functionality"""
        try:
            if not self.get_csrf_token():
                return False
                
            login_data = {
                'csrf_token': self.csrf_token,
                'employee_id': employee_id,
                'pin': pin
            }
            
            response = self.session.post(f"{self.base_url}/employee_portal", data=login_data)
            
            if response.status_code == 200:
                # Check if login was successful by looking for logout button or employee content
                if "logout" in response.text.lower() or "unused mini-games" in response.text.lower():
                    print(f"✓ Employee login successful for {employee_id}")
                    return True
                else:
                    print(f"✗ Employee login failed - incorrect credentials for {employee_id}")
                    return False
            else:
                print(f"✗ Employee login failed - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error testing employee login: {e}")
            return False
    
    def check_casino_styling(self):
        """Check if Vegas casino styling is applied"""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            if response.status_code == 200:
                content = response.text.lower()
                
                vegas_elements = [
                    'vegas-casino-portal',
                    'casino-login-screen', 
                    'broadway vegas portal',
                    'casino-title',
                    'vegas-marquee'
                ]
                
                found_elements = [elem for elem in vegas_elements if elem in content]
                
                print(f"✓ Found {len(found_elements)}/{len(vegas_elements)} Vegas styling elements")
                for elem in found_elements:
                    print(f"  - {elem}")
                    
                if len(found_elements) >= len(vegas_elements) // 2:
                    print("✓ Vegas casino styling is properly applied")
                    return True
                else:
                    print("✗ Vegas casino styling is incomplete")
                    return False
            else:
                print(f"✗ Could not check styling - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error checking casino styling: {e}")
            return False
    
    def check_javascript_libraries(self):
        """Check if required JavaScript libraries are loaded"""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            if response.status_code == 200:
                content = response.text
                
                libraries = {
                    'GSAP': 'gsap',
                    'Howler.js': 'howler', 
                    'Confetti': 'confetti',
                    'Bootstrap': 'bootstrap'
                }
                
                found_libs = {}
                for lib_name, lib_keyword in libraries.items():
                    if lib_keyword in content.lower():
                        found_libs[lib_name] = True
                        print(f"✓ {lib_name} library found")
                    else:
                        found_libs[lib_name] = False
                        print(f"✗ {lib_name} library missing")
                
                return all(found_libs.values())
            else:
                print(f"✗ Could not check libraries - HTTP {response.status_code}")
                return False
        except Exception as e:
            print(f"✗ Error checking JavaScript libraries: {e}")
            return False
    
    def check_static_files(self):
        """Check if static files (CSS, JS, audio) are accessible"""
        static_files = [
            '/static/style.css',
            '/static/vegas-casino.js',
            '/static/casino-win.mp3',
            '/static/coin-drop.mp3',
            '/static/reel-spin.mp3',
            '/static/jackpot-horn.mp3',
            '/static/slot-pull.mp3'
        ]
        
        accessible_files = 0
        for file_path in static_files:
            try:
                response = self.session.get(f"{self.base_url}{file_path}")
                if response.status_code == 200:
                    file_size = len(response.content)
                    print(f"✓ {file_path} accessible ({file_size} bytes)")
                    accessible_files += 1
                else:
                    print(f"✗ {file_path} not accessible - HTTP {response.status_code}")
            except Exception as e:
                print(f"✗ Error accessing {file_path}: {e}")
        
        success_rate = accessible_files / len(static_files)
        print(f"Static files accessibility: {accessible_files}/{len(static_files)} ({success_rate*100:.1f}%)")
        return success_rate >= 0.8
    
    def check_database_integrity(self):
        """Check mini_games table and employee data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check mini_games table structure
            cursor.execute("PRAGMA table_info(mini_games)")
            columns = [row[1] for row in cursor.fetchall()]
            expected_columns = ['id', 'employee_id', 'game_type', 'awarded_date', 'played_date', 'status', 'outcome']
            
            missing_columns = [col for col in expected_columns if col not in columns]
            if missing_columns:
                print(f"✗ Missing columns in mini_games table: {missing_columns}")
                return False
            else:
                print("✓ Mini_games table structure is correct")
            
            # Check for test data
            cursor.execute("SELECT COUNT(*) FROM mini_games")
            game_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mini_games WHERE status = 'unused'")
            unused_count = cursor.fetchone()[0]
            
            print(f"✓ Database contains {game_count} mini-games ({unused_count} unused)")
            
            conn.close()
            return True
            
        except Exception as e:
            print(f"✗ Database integrity check failed: {e}")
            return False
    
    def test_mini_game_endpoint(self, game_id=None):
        """Test the mini-game playing endpoint"""
        try:
            # Get an unused game ID if not provided
            if not game_id:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM mini_games WHERE status = 'unused' LIMIT 1")
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    game_id = result[0]
                else:
                    print("✗ No unused games available for testing")
                    return False
            
            # Test the endpoint without authentication first
            response = self.session.get(f"{self.base_url}/play_game/{game_id}")
            if response.status_code == 405:
                print("✓ Play game endpoint exists (requires POST)")
            else:
                print(f"? Play game endpoint status: {response.status_code}")
            
            # Test with POST but without proper authentication (should fail)
            response = self.session.post(f"{self.base_url}/play_game/{game_id}")
            if response.status_code in [401, 403, 302]:
                print("✓ Play game endpoint properly requires authentication")
                return True
            elif response.status_code == 400:
                print("✓ Play game endpoint requires proper data format")
                return True
            else:
                print(f"? Unexpected response from play game endpoint: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Error testing mini-game endpoint: {e}")
            return False
    
    def test_mobile_responsive(self):
        """Test mobile viewport responsiveness"""
        try:
            # Test with mobile user agent
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'
            }
            
            response = self.session.get(f"{self.base_url}/employee_portal", headers=mobile_headers)
            if response.status_code == 200:
                content = response.text
                
                # Check for responsive viewport meta tag
                if 'viewport' in content and 'width=device-width' in content:
                    print("✓ Mobile viewport meta tag found")
                else:
                    print("✗ Mobile viewport meta tag missing")
                
                # Check for responsive CSS classes
                responsive_indicators = ['responsive', '@media', 'mobile-', 'col-', 'flex']
                found_indicators = [ind for ind in responsive_indicators if ind in content]
                
                if found_indicators:
                    print(f"✓ Found responsive design indicators: {found_indicators}")
                    return True
                else:
                    print("✗ No responsive design indicators found")
                    return False
            else:
                print(f"✗ Could not test mobile responsive - HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Error testing mobile responsiveness: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run all tests and provide summary"""
        print("="*60)
        print("COMPREHENSIVE MINI-GAMES SYSTEM DEBUG REPORT")
        print("="*60)
        
        test_results = {}
        
        print("\n1. INFRASTRUCTURE TESTS")
        print("-"*30)
        test_results['csrf_token'] = self.get_csrf_token()
        test_results['static_files'] = self.check_static_files()
        test_results['database'] = self.check_database_integrity()
        
        print("\n2. USER INTERFACE TESTS") 
        print("-"*30)
        test_results['casino_styling'] = self.check_casino_styling()
        test_results['js_libraries'] = self.check_javascript_libraries()
        test_results['mobile_responsive'] = self.test_mobile_responsive()
        
        print("\n3. FUNCTIONALITY TESTS")
        print("-"*30)
        test_results['employee_login'] = self.test_employee_login()
        test_results['mini_game_endpoint'] = self.test_mini_game_endpoint()
        
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "PASS" if result else "FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall Score: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Mini-games system is fully functional.")
        elif passed_tests >= total_tests * 0.8:
            print("✅ Most tests passed. System is largely functional with minor issues.")
        elif passed_tests >= total_tests * 0.5:
            print("⚠️  Some tests failed. System has moderate issues that need attention.")
        else:
            print("❌ Many tests failed. System has significant issues requiring immediate attention.")
        
        return test_results

if __name__ == "__main__":
    debugger = MiniGamesDebugger()
    results = debugger.run_comprehensive_test()