#!/usr/bin/env python3
"""
Test session-based authentication for mini-games
"""

import requests
import json
import re

class SessionTester:
    def __init__(self, base_url="http://localhost:7409"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def full_login_and_play_test(self):
        """Complete login flow and game play test"""
        print("="*60)
        print("SESSION-BASED GAME PLAY TEST")
        print("="*60)
        
        # Step 1: Get login page and extract CSRF token
        print("1. Getting employee portal page...")
        response = self.session.get(f"{self.base_url}/employee_portal")
        print(f"   Status: {response.status_code}")
        
        if response.status_code != 200:
            print("✗ Failed to get employee portal")
            return
        
        # Extract CSRF token
        csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
        if not csrf_match:
            print("✗ Could not find CSRF token")
            return
        
        csrf_token = csrf_match.group(1)
        print(f"   CSRF token: {csrf_token[:20]}...")
        
        # Step 2: Submit login form
        print("\n2. Logging in as employee E002...")
        login_data = {
            'csrf_token': csrf_token,
            'employee_id': 'E002',
            'pin': '1234'
        }
        
        response = self.session.post(
            f"{self.base_url}/employee_portal",
            data=login_data,
            allow_redirects=True
        )
        print(f"   Login response status: {response.status_code}")
        
        # Check if login was successful by looking for employee content
        if "logout" in response.text.lower() or "unused mini-games" in response.text.lower():
            print("✓ Login successful!")
            
            # Extract game information from the page
            game_matches = re.findall(r'playMiniGame\((\d+), \'(\w+)\'\)', response.text)
            if game_matches:
                game_id, game_type = game_matches[0]
                print(f"   Found game: ID {game_id}, Type {game_type}")
                
                # Step 3: Play the game
                print(f"\n3. Playing {game_type} game (ID: {game_id})...")
                
                # Get fresh CSRF token from the page after login
                csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
                if csrf_match:
                    fresh_csrf = csrf_match.group(1)
                    
                    game_data = {
                        'csrf_token': fresh_csrf
                    }
                    
                    game_response = self.session.post(
                        f"{self.base_url}/play_game/{game_id}",
                        data=game_data,
                        headers={
                            'Content-Type': 'application/x-www-form-urlencoded'
                        }
                    )
                    
                    print(f"   Game response status: {game_response.status_code}")
                    
                    if game_response.status_code == 200:
                        try:
                            result = game_response.json()
                            print("✓ Game played successfully!")
                            print(f"   Result: {json.dumps(result, indent=4)}")
                            
                            # Step 4: Verify the game was marked as played
                            print("\n4. Checking employee portal after game...")
                            check_response = self.session.get(f"{self.base_url}/employee_portal")
                            if "played mini-games" in check_response.text.lower():
                                print("✓ Game appears in played games section")
                            else:
                                print("⚠️ Could not verify game in played section")
                                
                        except json.JSONDecodeError:
                            print("✗ Game response was not valid JSON")
                            print(f"   Response: {game_response.text[:200]}...")
                    else:
                        print(f"✗ Game play failed: {game_response.status_code}")
                        try:
                            error_data = game_response.json()
                            print(f"   Error: {error_data}")
                        except:
                            print(f"   Response text: {game_response.text[:200]}...")
                else:
                    print("✗ Could not get fresh CSRF token")
            else:
                print("⚠️ No playable games found")
                # Still check the page structure
                if "unused mini-games" in response.text.lower():
                    print("   But 'Unused Mini-Games' section exists")
                if "played mini-games" in response.text.lower():
                    print("   And 'Played Mini-Games' section exists")
        else:
            print("✗ Login failed - checking response...")
            if "invalid" in response.text.lower() or "incorrect" in response.text.lower():
                print("   Reason: Invalid credentials")
            else:
                print(f"   Response length: {len(response.text)} chars")
                print(f"   Contains 'broadway vegas': {'broadway vegas' in response.text.lower()}")
    
    def test_authentication_flow(self):
        """Test the complete authentication flow"""
        print("\n" + "="*60)
        print("AUTHENTICATION FLOW ANALYSIS")
        print("="*60)
        
        # Test 1: Unauthenticated game access
        print("1. Testing unauthenticated game access...")
        response = self.session.post(f"{self.base_url}/play_game/1")
        print(f"   Status: {response.status_code}")
        if response.status_code == 401:
            print("✓ Properly blocks unauthenticated access")
        
        # Test 2: Session persistence
        print("\n2. Testing session persistence...")
        # Login first
        csrf_response = self.session.get(f"{self.base_url}/employee_portal")
        csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', csrf_response.text)
        
        if csrf_match:
            login_data = {
                'csrf_token': csrf_match.group(1),
                'employee_id': 'E002',
                'pin': '1234'
            }
            
            login_response = self.session.post(f"{self.base_url}/employee_portal", data=login_data)
            
            # Now test if session persists across requests
            test_response = self.session.get(f"{self.base_url}/employee_portal")
            if "logout" in test_response.text.lower():
                print("✓ Session persists across requests")
            else:
                print("✗ Session does not persist")
        
        # Test 3: Logout functionality
        print("\n3. Testing logout functionality...")
        csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', test_response.text)
        if csrf_match:
            logout_data = {'csrf_token': csrf_match.group(1)}
            logout_response = self.session.post(f"{self.base_url}/employee/logout", data=logout_data)
            print(f"   Logout status: {logout_response.status_code}")
            
            # Verify logout worked
            check_response = self.session.get(f"{self.base_url}/employee_portal")
            if "enter your credentials" in check_response.text.lower():
                print("✓ Logout successful")
            else:
                print("⚠️ Logout may not have worked properly")

if __name__ == "__main__":
    tester = SessionTester()
    tester.full_login_and_play_test()
    tester.test_authentication_flow()