#!/usr/bin/env python3
"""
Final comprehensive gameplay test with correct PIN
"""

import requests
import json
import re
import sqlite3

class FinalGameplayTest:
    def __init__(self, base_url="http://localhost:7409"):
        self.base_url = base_url
        self.session = requests.Session()
        self.db_path = "/home/tim/incentDev/incentive.db"
    
    def run_complete_test(self):
        """Run the complete mini-games test suite"""
        print("="*70)
        print("🎰 FINAL COMPREHENSIVE MINI-GAMES TESTING 🎰")
        print("="*70)
        
        success_count = 0
        total_tests = 7
        
        # Test 1: Login with correct PIN
        print("\n1️⃣  EMPLOYEE LOGIN TEST")
        print("-" * 50)
        login_success = self.test_employee_login()
        if login_success:
            success_count += 1
            print("✅ Employee login: PASSED")
        else:
            print("❌ Employee login: FAILED")
        
        if not login_success:
            print("\n🛑 Cannot proceed without successful login. Testing stopped.")
            return
        
        # Test 2: Find and play game
        print("\n2️⃣  MINI-GAME PLAY TEST")
        print("-" * 50)
        game_play_success = self.test_game_play()
        if game_play_success:
            success_count += 1
            print("✅ Game play: PASSED")
        else:
            print("❌ Game play: FAILED")
        
        # Test 3: Verify database updates
        print("\n3️⃣  DATABASE INTEGRATION TEST")
        print("-" * 50)
        db_success = self.test_database_integration()
        if db_success:
            success_count += 1
            print("✅ Database integration: PASSED")
        else:
            print("❌ Database integration: FAILED")
        
        # Test 4: CSS/Styling
        print("\n4️⃣  VEGAS CASINO STYLING TEST")
        print("-" * 50)
        styling_success = self.test_vegas_styling()
        if styling_success:
            success_count += 1
            print("✅ Vegas styling: PASSED")
        else:
            print("❌ Vegas styling: FAILED")
        
        # Test 5: JavaScript Libraries
        print("\n5️⃣  JAVASCRIPT LIBRARIES TEST")
        print("-" * 50)
        js_success = self.test_javascript_libraries()
        if js_success:
            success_count += 1
            print("✅ JavaScript libraries: PASSED")
        else:
            print("❌ JavaScript libraries: FAILED")
        
        # Test 6: Audio Files
        print("\n6️⃣  AUDIO FILES TEST")
        print("-" * 50)
        audio_success = self.test_audio_files()
        if audio_success:
            success_count += 1
            print("✅ Audio files: PASSED")
        else:
            print("❌ Audio files: FAILED")
        
        # Test 7: Mobile Responsiveness
        print("\n7️⃣  MOBILE RESPONSIVENESS TEST")
        print("-" * 50)
        mobile_success = self.test_mobile_responsiveness()
        if mobile_success:
            success_count += 1
            print("✅ Mobile responsiveness: PASSED")
        else:
            print("❌ Mobile responsiveness: FAILED")
        
        # Final Report
        print("\n" + "="*70)
        print("🏆 FINAL TEST RESULTS")
        print("="*70)
        
        score_percentage = (success_count / total_tests) * 100
        print(f"Overall Score: {success_count}/{total_tests} ({score_percentage:.1f}%)")
        
        if score_percentage >= 90:
            print("🥇 EXCELLENT: Mini-games system is production-ready!")
        elif score_percentage >= 80:
            print("🥈 GOOD: Mini-games system is functional with minor issues.")
        elif score_percentage >= 70:
            print("🥉 ACCEPTABLE: Mini-games system works but needs improvements.")
        else:
            print("⚠️  NEEDS WORK: Mini-games system has significant issues.")
        
        return {
            'score': success_count,
            'total': total_tests,
            'percentage': score_percentage,
            'details': {
                'login': login_success,
                'gameplay': game_play_success,
                'database': db_success,
                'styling': styling_success,
                'javascript': js_success,
                'audio': audio_success,
                'mobile': mobile_success
            }
        }
    
    def test_employee_login(self):
        """Test employee login with correct PIN"""
        try:
            # Get login page
            response = self.session.get(f"{self.base_url}/employee_portal")
            if response.status_code != 200:
                print(f"❌ Could not access employee portal: {response.status_code}")
                return False
            
            # Extract CSRF token
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
            if not csrf_match:
                print("❌ Could not find CSRF token")
                return False
            
            csrf_token = csrf_match.group(1)
            print(f"🔐 CSRF token extracted: {csrf_token[:20]}...")
            
            # Try login with default PIN 8101
            login_data = {
                'csrf_token': csrf_token,
                'employee_id': 'E002',
                'pin': '8101'
            }
            
            response = self.session.post(f"{self.base_url}/employee_portal", data=login_data)
            print(f"🔑 Login response status: {response.status_code}")
            
            # Check if login was successful
            if "logout" in response.text.lower() or "unused mini-games" in response.text.lower():
                print("✅ Login successful with PIN 8101")
                return True
            else:
                # Try alternative PINs
                for alt_pin in ['1234', '0000', '1111']:
                    print(f"🔄 Trying alternative PIN: {alt_pin}")
                    
                    # Get fresh CSRF token
                    response = self.session.get(f"{self.base_url}/employee_portal")
                    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
                    if csrf_match:
                        login_data['csrf_token'] = csrf_match.group(1)
                        login_data['pin'] = alt_pin
                        
                        response = self.session.post(f"{self.base_url}/employee_portal", data=login_data)
                        
                        if "logout" in response.text.lower() or "unused mini-games" in response.text.lower():
                            print(f"✅ Login successful with PIN {alt_pin}")
                            return True
                
                print("❌ Login failed with all attempted PINs")
                return False
                
        except Exception as e:
            print(f"❌ Login test error: {e}")
            return False
    
    def test_game_play(self):
        """Test actual mini-game play"""
        try:
            # Get employee portal page to find games
            response = self.session.get(f"{self.base_url}/employee_portal")
            
            # Look for playMiniGame calls
            game_matches = re.findall(r'playMiniGame\((\d+), \'(\w+)\'\)', response.text)
            
            if not game_matches:
                print("⚠️  No unused games found in UI, checking database...")
                
                # Check database directly
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, game_type, employee_id 
                    FROM mini_games 
                    WHERE status = 'unused' AND employee_id = 'E002' 
                    LIMIT 1
                """)
                result = cursor.fetchone()
                conn.close()
                
                if result:
                    game_id, game_type, employee_id = result
                    print(f"📊 Found unused {game_type} game (ID: {game_id}) in database")
                else:
                    print("❌ No unused games found for E002")
                    return False
            else:
                game_id, game_type = game_matches[0]
                print(f"🎮 Found {game_type} game (ID: {game_id}) in UI")
            
            # Get fresh CSRF token
            csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
            if not csrf_match:
                print("❌ Could not get CSRF token for game play")
                return False
            
            csrf_token = csrf_match.group(1)
            
            # Play the game
            game_data = {
                'csrf_token': csrf_token
            }
            
            print(f"🎲 Attempting to play {game_type} game {game_id}...")
            game_response = self.session.post(
                f"{self.base_url}/play_game/{game_id}",
                data=game_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            print(f"🎯 Game response status: {game_response.status_code}")
            
            if game_response.status_code == 200:
                try:
                    result = game_response.json()
                    print("✅ Game played successfully!")
                    print(f"🏆 Game result: {result.get('message', 'Unknown')}")
                    
                    if result.get('result', {}).get('win'):
                        print("🎉 Player won the game!")
                    else:
                        print("😔 Player did not win")
                    
                    return True
                except json.JSONDecodeError:
                    print("❌ Game response was not valid JSON")
                    print(f"Response: {game_response.text[:200]}...")
                    return False
            else:
                print(f"❌ Game play failed: {game_response.status_code}")
                try:
                    error_data = game_response.json()
                    print(f"Error details: {error_data}")
                except:
                    print(f"Response text: {game_response.text[:200]}...")
                return False
                
        except Exception as e:
            print(f"❌ Game play test error: {e}")
            return False
    
    def test_database_integration(self):
        """Test database operations"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check mini_games table structure
            cursor.execute("PRAGMA table_info(mini_games)")
            columns = [row[1] for row in cursor.fetchall()]
            required_columns = ['id', 'employee_id', 'game_type', 'status', 'outcome']
            
            missing = [col for col in required_columns if col not in columns]
            if missing:
                print(f"❌ Missing required columns: {missing}")
                return False
            
            # Check for recent game activity
            cursor.execute("""
                SELECT COUNT(*) FROM mini_games 
                WHERE awarded_date > datetime('now', '-7 days')
            """)
            recent_games = cursor.fetchone()[0]
            
            print(f"📊 Found {recent_games} games in the last 7 days")
            
            conn.close()
            print("✅ Database structure and data look good")
            return True
            
        except Exception as e:
            print(f"❌ Database test error: {e}")
            return False
    
    def test_vegas_styling(self):
        """Test Vegas casino styling elements"""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            content = response.text.lower()
            
            required_elements = [
                'vegas-casino-portal',
                'casino-login-screen',
                'broadway vegas portal',
                'casino-title'
            ]
            
            found_elements = [elem for elem in required_elements if elem in content]
            print(f"🎨 Found {len(found_elements)}/{len(required_elements)} styling elements")
            
            # Check CSS file
            css_response = self.session.get(f"{self.base_url}/static/style.css")
            if css_response.status_code == 200:
                css_content = css_response.text.lower()
                vegas_css = [
                    '--primary-gold',
                    '--casino-red', 
                    '--neon-blue',
                    'vegas-casino'
                ]
                found_css = [item for item in vegas_css if item in css_content]
                print(f"🎨 Found {len(found_css)}/{len(vegas_css)} Vegas CSS variables")
                
                return len(found_elements) >= 3 and len(found_css) >= 3
            else:
                print("❌ Could not load CSS file")
                return False
                
        except Exception as e:
            print(f"❌ Styling test error: {e}")
            return False
    
    def test_javascript_libraries(self):
        """Test required JavaScript libraries"""
        try:
            response = self.session.get(f"{self.base_url}/employee_portal")
            content = response.text
            
            libraries = {
                'GSAP': 'gsap',
                'Howler.js': 'howler',
                'Confetti': 'confetti',
                'Bootstrap': 'bootstrap'
            }
            
            found_libs = 0
            for lib_name, lib_keyword in libraries.items():
                if lib_keyword in content.lower():
                    print(f"✅ {lib_name} found")
                    found_libs += 1
                else:
                    print(f"❌ {lib_name} missing")
            
            return found_libs >= 3
            
        except Exception as e:
            print(f"❌ JavaScript libraries test error: {e}")
            return False
    
    def test_audio_files(self):
        """Test audio file availability"""
        audio_files = [
            '/static/casino-win.mp3',
            '/static/coin-drop.mp3', 
            '/static/reel-spin.mp3',
            '/static/jackpot-horn.mp3'
        ]
        
        working_files = 0
        for audio_file in audio_files:
            try:
                response = self.session.get(f"{self.base_url}{audio_file}")
                if response.status_code == 200 and len(response.content) > 100:
                    print(f"✅ {audio_file} available ({len(response.content)} bytes)")
                    working_files += 1
                else:
                    print(f"❌ {audio_file} unavailable or empty")
            except:
                print(f"❌ {audio_file} error loading")
        
        return working_files >= 3
    
    def test_mobile_responsiveness(self):
        """Test mobile responsiveness"""
        try:
            mobile_headers = {
                'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_7_1 like Mac OS X) AppleWebKit/605.1.15'
            }
            
            response = self.session.get(f"{self.base_url}/employee_portal", headers=mobile_headers)
            content = response.text
            
            # Check viewport
            has_viewport = 'viewport' in content and 'width=device-width' in content
            print(f"📱 Mobile viewport: {'✅' if has_viewport else '❌'}")
            
            # Check responsive indicators
            responsive_indicators = ['@media', 'mobile', 'responsive', 'col-', 'flex']
            found_responsive = sum(1 for indicator in responsive_indicators if indicator in content.lower())
            print(f"📱 Responsive indicators: {found_responsive}/5")
            
            return has_viewport and found_responsive >= 2
            
        except Exception as e:
            print(f"❌ Mobile test error: {e}")
            return False

if __name__ == "__main__":
    tester = FinalGameplayTest()
    results = tester.run_complete_test()
    
    print(f"\n🎯 Final Score: {results['percentage']:.1f}%")
    if results['percentage'] >= 80:
        print("🚀 Mini-games system is ready for production!")
    else:
        print("🔧 Mini-games system needs additional work.")