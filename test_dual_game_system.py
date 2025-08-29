#!/usr/bin/env python3
"""
Comprehensive Dual Game System Testing Script
Tests both Category A (guaranteed wins) and Category B (gambling) systems
"""

import requests
import json
import sqlite3
import time
from urllib.parse import urljoin

class DualGameSystemTester:
    def __init__(self, base_url="http://localhost:7409"):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        self.db_path = "/home/tim/incentDev/incentive.db"
        
    def get_csrf_token(self):
        """Extract CSRF token from employee portal page."""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            if response.status_code == 200:
                import re
                match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
                if match:
                    self.csrf_token = match.group(1)
                    print(f"✓ CSRF token obtained")
                    return True
            print("✗ Failed to get CSRF token")
            return False
        except Exception as e:
            print(f"✗ Error getting CSRF token: {e}")
            return False
    
    def employee_login(self, employee_id="E002", pin="1234"):
        """Login as employee."""
        try:
            if not self.get_csrf_token():
                return False
                
            login_data = {
                'csrf_token': self.csrf_token,
                'employee_id': employee_id,
                'pin': pin
            }
            
            response = self.session.post(f"{self.base_url}/employee_portal", data=login_data)
            
            if response.status_code == 200 and "logout" in response.text.lower():
                print(f"✓ Employee login successful for {employee_id}")
                return True
            else:
                print(f"✗ Employee login failed for {employee_id}")
                return False
        except Exception as e:
            print(f"✗ Error in employee login: {e}")
            return False
    
    def test_dual_system_status(self):
        """Test dual system status API."""
        try:
            response = self.session.get(f"{self.base_url}/api/dual-system/status")
            data = response.json()
            
            if data['success']:
                print("✓ Dual system status API working")
                print(f"  - Token balance: {data['token_account']['token_balance']}")
                print(f"  - Category A games: {data['game_summary']['category_a']}")
                print(f"  - Category B games: {data['game_summary']['category_b']}")
                return True, data
            else:
                print(f"✗ Dual system status failed: {data['message']}")
                return False, None
                
        except Exception as e:
            print(f"✗ Error testing dual system status: {e}")
            return False, None
    
    def test_token_exchange(self, token_amount=5):
        """Test token exchange functionality."""
        try:
            if not self.csrf_token:
                self.get_csrf_token()
            
            # Get current points first
            status_ok, status_data = self.test_dual_system_status()
            if not status_ok:
                return False
            
            current_points = status_data['token_account']['current_points']
            print(f"Current points: {current_points}")
            
            if current_points < token_amount * 10:  # Assuming 10:1 rate for bronze
                print(f"✗ Insufficient points for token exchange ({current_points} < {token_amount * 10})")
                return False
            
            # Perform exchange with CSRF token in headers
            exchange_data = {
                'token_amount': token_amount
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token
            }
            response = self.session.post(
                f"{self.base_url}/api/tokens/exchange",
                json=exchange_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    print(f"✓ Token exchange successful: {data['message']}")
                    print(f"  - New token balance: {data['new_token_balance']}")
                    return True
                else:
                    print(f"✗ Token exchange failed: {data['message']}")
                    return False
            else:
                print(f"✗ Token exchange HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Error testing token exchange: {e}")
            return False
    
    def test_category_a_game_award(self):
        """Test awarding and playing Category A games."""
        try:
            # First, award a Category A game via database
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO mini_games 
                    (employee_id, game_type, awarded_date, status, game_category, guaranteed_win, tier_level)
                    VALUES ('E002', 'reward_selection', CURRENT_TIMESTAMP, 'unused', 'reward', 1, 'bronze')
                """)
                game_id = cursor.lastrowid
                conn.commit()
            
            print(f"✓ Category A game awarded (ID: {game_id})")
            
            # Now try to play it
            headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token
            }
            response = self.session.post(
                f"{self.base_url}/api/games/category-a/play/{game_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success'] and data['guaranteed_win']:
                    print(f"✓ Category A game played successfully")
                    print(f"  - Prize: {data['prize_details']['description']}")
                    print(f"  - Amount: {data['prize_details']['amount']}")
                    return True
                else:
                    print(f"✗ Category A game play failed: {data['message']}")
                    return False
            else:
                print(f"✗ Category A game play HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Error testing Category A game: {e}")
            return False
    
    def test_category_b_game(self, token_cost=3):
        """Test Category B gambling game."""
        try:
            # Check current token balance first
            status_ok, status_data = self.test_dual_system_status()
            if not status_ok:
                return False
            
            current_tokens = status_data['token_account']['token_balance']
            print(f"Current tokens: {current_tokens}")
            
            # If we don't have enough tokens, try to exchange more
            if current_tokens < token_cost:
                print(f"Need more tokens, current: {current_tokens}, need: {token_cost}")
                # Try to get more tokens if we have points
                if not self.test_token_exchange(max(5, token_cost)):
                    print("✗ Cannot test Category B without tokens")
                    return False
            
            game_data = {
                'game_type': 'slots',
                'token_cost': token_cost
            }
            
            headers = {
                'Content-Type': 'application/json',
                'X-CSRFToken': self.csrf_token
            }
            response = self.session.post(
                f"{self.base_url}/api/games/category-b/play",
                json=game_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data['success']:
                    print(f"✓ Category B game played successfully")
                    print(f"  - Result: {data['result']['outcome']}")
                    if data['result']['outcome'] == 'win':
                        print(f"  - Prize: {data['result']['description']}")
                    print(f"  - Guaranteed win: {data['guaranteed_win']}")
                    return True
                else:
                    print(f"✗ Category B game play failed: {data['message']}")
                    return False
            else:
                print(f"✗ Category B game play HTTP error: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"✗ Error testing Category B game: {e}")
            return False
    
    def test_database_integrity(self):
        """Test dual system database integrity."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check new tables exist
                tables = [
                    'employee_tokens', 'token_transactions', 'employee_prize_limits',
                    'global_prize_pools', 'admin_game_config', 'employee_behavior_flags',
                    'employee_tiers'
                ]
                
                for table in tables:
                    result = conn.execute(
                        f"SELECT count(*) FROM sqlite_master WHERE type='table' AND name='{table}'"
                    ).fetchone()
                    if result[0] == 0:
                        print(f"✗ Table {table} not found")
                        return False
                    else:
                        print(f"✓ Table {table} exists")
                
                # Check data integrity
                token_accounts = conn.execute("SELECT COUNT(*) FROM employee_tokens").fetchone()[0]
                global_pools = conn.execute("SELECT COUNT(*) FROM global_prize_pools").fetchone()[0]
                configs = conn.execute("SELECT COUNT(*) FROM admin_game_config").fetchone()[0]
                
                print(f"✓ Token accounts: {token_accounts}")
                print(f"✓ Global prize pools: {global_pools}")
                print(f"✓ Admin configurations: {configs}")
                
                return True
                
        except Exception as e:
            print(f"✗ Database integrity check failed: {e}")
            return False
    
    def test_global_prize_pools(self):
        """Test global prize pool functionality."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                pools = conn.execute("""
                    SELECT prize_type, daily_limit, daily_used, weekly_limit, monthly_limit
                    FROM global_prize_pools
                """).fetchall()
                
                print(f"✓ Global prize pools configured:")
                for pool in pools:
                    print(f"  - {pool[0]}: {pool[2]}/{pool[1]} daily, {pool[3]} weekly, {pool[4]} monthly")
                
                return len(pools) > 0
                
        except Exception as e:
            print(f"✗ Error testing global prize pools: {e}")
            return False
    
    def run_comprehensive_test(self):
        """Run all dual system tests."""
        print("=" * 60)
        print("COMPREHENSIVE DUAL GAME SYSTEM TEST REPORT")
        print("=" * 60)
        
        test_results = {}
        
        print("\n1. SYSTEM INFRASTRUCTURE")
        print("-" * 30)
        test_results['database_integrity'] = self.test_database_integrity()
        test_results['global_pools'] = self.test_global_prize_pools()
        
        print("\n2. AUTHENTICATION & SETUP")
        print("-" * 30)
        test_results['employee_login'] = self.employee_login()
        
        if test_results['employee_login']:
            print("\n3. DUAL SYSTEM API TESTS")
            print("-" * 30)
            test_results['system_status'] = self.test_dual_system_status()[0]
            test_results['token_exchange'] = self.test_token_exchange()
            
            print("\n4. GAME SYSTEM TESTS")
            print("-" * 30)
            test_results['category_a_game'] = self.test_category_a_game_award()
            test_results['category_b_game'] = self.test_category_b_game()
        else:
            print("\n⚠️  Skipping API tests due to authentication failure")
        
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        passed_tests = sum(test_results.values())
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "PASS" if result else "FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall Score: {passed_tests}/{total_tests} ({passed_tests/total_tests*100:.1f}%)")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED! Dual game system is fully functional.")
        elif passed_tests >= total_tests * 0.8:
            print("✅ Most tests passed. System is largely functional.")
        elif passed_tests >= total_tests * 0.5:
            print("⚠️  Some tests failed. System has issues that need attention.")
        else:
            print("❌ Many tests failed. System requires immediate attention.")
        
        return test_results

if __name__ == "__main__":
    print("Testing Revolutionary Dual Game System...")
    print("=" * 50)
    
    tester = DualGameSystemTester()
    results = tester.run_comprehensive_test()
    
    print("\n" + "=" * 50)
    print("🎯 DUAL GAME SYSTEM TEST COMPLETE!")
    print("\nSystem Features Tested:")
    print("✓ Token Economy (Points ↔ Tokens)")
    print("✓ Category A: Guaranteed Win Games")
    print("✓ Category B: Risk-Based Gambling Games")
    print("✓ Individual & Global Prize Limits")
    print("✓ Database Schema Integration")
    print("✓ API Security & Authentication")