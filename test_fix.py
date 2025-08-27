#!/usr/bin/env python3
"""
Test the mini-game bug fix
"""

import requests
import json
import re
import sqlite3
import time

class GameFixTester:
    def __init__(self, base_url="http://localhost:7409"):
        self.base_url = base_url
        self.session = requests.Session()
        self.db_path = "/home/tim/incentDev/incentive.db"
    
    def test_game_play_fix(self):
        """Test the fixed game play functionality"""
        print("🎮 TESTING MINI-GAME BUG FIX")
        print("=" * 50)
        
        # Step 1: Login
        print("1. Logging in as E002...")
        if not self.login():
            return False
        
        # Step 2: Find a game to play
        print("2. Finding game to play...")
        game_info = self.find_game()
        if not game_info:
            return False
        
        # Step 3: Play the game
        print(f"3. Playing {game_info['type']} game (ID: {game_info['id']})...")
        result = self.play_game(game_info['id'])
        if result:
            print("✅ Game played successfully!")
            print(f"   Game outcome: {result.get('message', 'Unknown')}")
            
            if result.get('result', {}).get('win'):
                print("🎉 Player won the game!")
                points = result.get('result', {}).get('prize_amount', 0)
                if points > 0:
                    print(f"   Awarded {points} points")
            
            # Step 4: Verify database update
            print("4. Verifying database update...")
            if self.verify_database_update(game_info['id']):
                print("✅ Database updated correctly")
                return True
            else:
                print("❌ Database update failed")
                return False
        else:
            print("❌ Game play failed")
            return False
    
    def login(self):
        """Login as employee E002"""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
            if not csrf_match:
                return False
            
            login_data = {
                'csrf_token': csrf_match.group(1),
                'employee_id': 'E002',
                'pin': '8101'
            }
            
            response = self.session.post(f"{self.base_url}/employee_portal", data=login_data)
            return "logout" in response.text.lower()
            
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False
    
    def find_game(self):
        """Find an unused game"""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            game_matches = re.findall(r'playMiniGame\((\d+), \'(\w+)\'\)', response.text)
            
            if game_matches:
                game_id, game_type = game_matches[0]
                return {'id': int(game_id), 'type': game_type}
            else:
                print("❌ No unused games found")
                return None
                
        except Exception as e:
            print(f"❌ Game finding error: {e}")
            return None
    
    def play_game(self, game_id):
        """Play a mini-game"""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
            if not csrf_match:
                return None
            
            game_data = {
                'csrf_token': csrf_match.group(1)
            }
            
            response = self.session.post(
                f"{self.base_url}/play_game/{game_id}",
                data=game_data
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"❌ Game failed with status {response.status_code}")
                try:
                    error = response.json()
                    print(f"   Error: {error}")
                except:
                    print(f"   Response: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Game play error: {e}")
            return None
    
    def verify_database_update(self, game_id):
        """Verify game was recorded in database"""
        try:
            # Wait a moment for database to update
            time.sleep(1)
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT status, outcome FROM mini_games WHERE id = ?", (game_id,))
            result = cursor.fetchone()
            conn.close()
            
            if result:
                status, outcome = result
                return status == 'played' and outcome is not None
            return False
            
        except Exception as e:
            print(f"❌ Database verification error: {e}")
            return False

if __name__ == "__main__":
    tester = GameFixTester()
    success = tester.test_game_play_fix()
    
    if success:
        print("\n🎉 BUG FIX SUCCESSFUL! Mini-games are working correctly.")
    else:
        print("\n❌ Bug fix failed or other issues remain.")