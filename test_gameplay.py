#!/usr/bin/env python3
"""
Test actual mini-game gameplay functionality
"""

import requests
import json
import sqlite3
import re
from datetime import datetime

class GameplayTester:
    def __init__(self, base_url="http://localhost:7409"):
        self.base_url = base_url
        self.session = requests.Session()
        self.db_path = "/home/tim/incentDev/incentive.db"
    
    def login_employee(self, employee_id="E002", pin="1234"):
        """Login as an employee"""
        try:
            # Get initial page and CSRF token
            response = self.session.get(f"{self.base_url}/employee_portal")
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
            
            if not csrf_match:
                print("✗ Could not extract CSRF token")
                return False
            
            csrf_token = csrf_match.group(1)
            
            # Attempt login
            login_data = {
                'csrf_token': csrf_token,
                'employee_id': employee_id,
                'pin': pin
            }
            
            response = self.session.post(f"{self.base_url}/employee_portal", data=login_data)
            
            if "logout" in response.text.lower() or "unused mini-games" in response.text.lower():
                print(f"✓ Successfully logged in as {employee_id}")
                return True
            else:
                print(f"✗ Login failed for {employee_id}")
                return False
                
        except Exception as e:
            print(f"✗ Login error: {e}")
            return False
    
    def find_unused_game(self):
        """Find an unused mini-game from database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, game_type, employee_id 
                FROM mini_games 
                WHERE status = 'unused' 
                ORDER BY awarded_date DESC 
                LIMIT 1
            """)
            result = cursor.fetchone()
            conn.close()
            
            if result:
                game_id, game_type, employee_id = result
                print(f"✓ Found unused {game_type} game (ID: {game_id}) for employee {employee_id}")
                return {'id': game_id, 'type': game_type, 'employee_id': employee_id}
            else:
                print("✗ No unused games found")
                return None
                
        except Exception as e:
            print(f"✗ Database error: {e}")
            return None
    
    def play_game(self, game_id):
        """Actually play a mini-game"""
        try:
            # First, get the employee portal to get fresh CSRF token
            response = self.session.get(f"{self.base_url}/employee_portal")
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
            
            if not csrf_match:
                print("✗ Could not get CSRF token for game play")
                return None
            
            csrf_token = csrf_match.group(1)
            
            # Play the game using form data (not JSON)
            game_data = {
                'csrf_token': csrf_token
            }
            
            print(f"Attempting to play game {game_id}...")
            response = self.session.post(
                f"{self.base_url}/play_game/{game_id}", 
                data=game_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            )
            
            print(f"Game play response status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    print("✓ Game played successfully!")
                    print(f"Game Result: {json.dumps(result, indent=2)}")
                    return result
                except json.JSONDecodeError:
                    print("✗ Game response was not valid JSON")
                    print(f"Response text: {response.text[:500]}...")
                    return None
            else:
                print(f"✗ Game play failed with status {response.status_code}")
                print(f"Response: {response.text[:500]}...")
                return None
                
        except Exception as e:
            print(f"✗ Game play error: {e}")
            return None
    
    def verify_game_result_in_db(self, game_id):
        """Verify the game result was saved in database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT status, outcome, played_date 
                FROM mini_games 
                WHERE id = ?
            """, (game_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                status, outcome, played_date = result
                print(f"✓ Game {game_id} database status: {status}")
                if outcome:
                    try:
                        outcome_data = json.loads(outcome)
                        print(f"✓ Game outcome saved: {outcome_data.get('win', 'Unknown')}")
                        return True
                    except:
                        print("✗ Game outcome data is corrupted")
                        return False
                else:
                    print("✗ No game outcome recorded")
                    return False
            else:
                print(f"✗ Game {game_id} not found in database")
                return False
                
        except Exception as e:
            print(f"✗ Database verification error: {e}")
            return False
    
    def test_all_game_types(self):
        """Test each type of mini-game"""
        game_types_tested = []
        
        # Test each game type we can find
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT game_type FROM mini_games WHERE status = 'played' LIMIT 3")
        available_types = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        print(f"Available game types in database: {available_types}")
        
        for game_type in available_types:
            print(f"\n--- Testing {game_type.upper()} Game Logic ---")
            self.test_game_type_logic(game_type)
            game_types_tested.append(game_type)
        
        return game_types_tested
    
    def test_game_type_logic(self, game_type):
        """Test game type specific logic by examining database results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                SELECT outcome 
                FROM mini_games 
                WHERE game_type = ? AND status = 'played' AND outcome IS NOT NULL
                LIMIT 5
            """, (game_type,))
            results = cursor.fetchall()
            conn.close()
            
            if not results:
                print(f"✗ No played {game_type} games found")
                return
            
            print(f"✓ Found {len(results)} played {game_type} games")
            
            for i, (outcome_json,) in enumerate(results, 1):
                try:
                    outcome = json.loads(outcome_json)
                    print(f"  Game {i}:")
                    
                    if game_type == 'slot':
                        reels = outcome.get('result', {}).get('reels', [])
                        win = outcome.get('win', False)
                        print(f"    - Reels: {reels}")
                        print(f"    - Win: {win}")
                        
                    elif game_type == 'scratch':
                        grid = outcome.get('result', {}).get('grid', [])
                        win = outcome.get('win', False)
                        print(f"    - Grid size: {len(grid)}x{len(grid[0]) if grid else 0}")
                        print(f"    - Win: {win}")
                        
                    elif game_type == 'roulette':
                        number = outcome.get('result', {}).get('number', 'N/A')
                        color = outcome.get('result', {}).get('color', 'N/A')
                        win = outcome.get('win', False)
                        print(f"    - Number: {number}, Color: {color}")
                        print(f"    - Win: {win}")
                    
                    if outcome.get('win'):
                        prize_amount = outcome.get('prize_amount', 0)
                        prize_type = outcome.get('prize_type', 'unknown')
                        print(f"    - Prize: {prize_amount} {prize_type}")
                        
                except json.JSONDecodeError:
                    print(f"  Game {i}: Invalid JSON outcome")
                    
        except Exception as e:
            print(f"✗ Error testing {game_type} logic: {e}")
    
    def performance_test(self):
        """Test performance of game endpoints"""
        print("\n--- Performance Testing ---")
        
        import time
        
        # Test multiple rapid requests
        start_time = time.time()
        
        for i in range(5):
            response = self.session.get(f"{self.base_url}/employee_portal")
            if response.status_code != 200:
                print(f"✗ Request {i+1} failed: {response.status_code}")
                return False
        
        end_time = time.time()
        avg_response_time = (end_time - start_time) / 5
        
        print(f"✓ Average response time: {avg_response_time:.3f} seconds")
        
        if avg_response_time < 1.0:
            print("✓ Performance is excellent (< 1s)")
        elif avg_response_time < 2.0:
            print("✓ Performance is good (< 2s)")
        else:
            print("⚠️ Performance is slow (> 2s)")
        
        return avg_response_time < 3.0
    
    def run_gameplay_tests(self):
        """Run complete gameplay test suite"""
        print("="*60)
        print("MINI-GAMES GAMEPLAY TESTING")
        print("="*60)
        
        # Step 1: Login
        print("\n1. Employee Login Test")
        print("-"*30)
        if not self.login_employee():
            print("❌ Cannot continue without successful login")
            return
        
        # Step 2: Find and play a game
        print("\n2. Game Play Test")
        print("-"*30)
        unused_game = self.find_unused_game()
        
        if unused_game:
            # Ensure we're logged in as the correct employee
            if unused_game['employee_id'] != 'E002':
                print(f"Switching to employee {unused_game['employee_id']}...")
                if not self.login_employee(unused_game['employee_id'], "1234"):
                    print("Could not login as game owner, trying default employee")
            
            result = self.play_game(unused_game['id'])
            
            if result:
                print("✓ Game played successfully")
                # Verify in database
                self.verify_game_result_in_db(unused_game['id'])
            else:
                print("✗ Game play failed")
        else:
            print("⚠️ No unused games available - testing with historical data")
        
        # Step 3: Test all game types
        print("\n3. Game Types Analysis")
        print("-"*30)
        game_types = self.test_all_game_types()
        
        # Step 4: Performance test
        print("\n4. Performance Testing")
        print("-"*30)
        perf_result = self.performance_test()
        
        print("\n" + "="*60)
        print("GAMEPLAY TEST SUMMARY")
        print("="*60)
        
        print(f"✓ Game types analyzed: {len(game_types)}")
        print(f"✓ Performance test: {'PASS' if perf_result else 'FAIL'}")
        
        if unused_game and result:
            print("✓ Full gameplay cycle completed successfully")
        else:
            print("⚠️ Gameplay test completed with limitations")

if __name__ == "__main__":
    tester = GameplayTester()
    tester.run_gameplay_tests()