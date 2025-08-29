#!/usr/bin/env python3
"""
Debug Category B error more thoroughly
"""

import requests
import re
import json
import sqlite3

def debug_category_b():
    # First, run the web test
    session = requests.Session()
    base_url = "http://localhost:7409"
    
    print("=== DEBUGGING CATEGORY B ===")
    
    # Login
    response = session.get(f"{base_url}/employee_portal")
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    csrf_token = csrf_match.group(1)
    
    login_data = {
        'csrf_token': csrf_token,
        'employee_id': 'E002',
        'pin': '1234'
    }
    session.post(f"{base_url}/employee_portal", data=login_data)
    print("✅ Logged in")
    
    # Check token balance first
    response = session.get(f"{base_url}/api/dual-system/status")
    status = response.json()
    print(f"Current tokens: {status['token_account']['token_balance']}")
    
    if status['token_account']['token_balance'] < 3:
        print("❌ Not enough tokens, aborting test")
        return
    
    # Try Category B game
    print("🎰 Attempting Category B game...")
    game_data = {'game_type': 'slots', 'token_cost': 3}
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(f"{base_url}/api/games/category-b/play", json=game_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Now try to test the dual game manager directly
    print("\n🔍 Testing dual game manager directly...")
    try:
        from services.dual_game_manager import DualGameManager
        dual_manager = DualGameManager()
        
        success, message, result = dual_manager.play_category_b_game('E002', 'slots', 3)
        print(f"Direct test result: {success}, {message}")
        if result:
            print(f"Result data: {result}")
    except Exception as e:
        print(f"❌ Direct test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_category_b()