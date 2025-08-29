#!/usr/bin/env python3
"""
Test the complete Category B flow: exchange tokens then play
"""

import requests
import re
import json

def test_complete_flow():
    session = requests.Session()
    base_url = "http://localhost:7409"
    
    print("=== COMPLETE CATEGORY B FLOW TEST ===")
    
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
    
    # Check initial status
    response = session.get(f"{base_url}/api/dual-system/status")
    status = response.json()
    print(f"Initial - Points: {status['token_account']['current_points']}, Tokens: {status['token_account']['token_balance']}")
    
    # Exchange tokens if we have enough points
    if status['token_account']['current_points'] >= 50:
        print("\n🔄 Exchanging tokens...")
        exchange_data = {'token_amount': 10}
        headers = {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrf_token
        }
        
        response = session.post(f"{base_url}/api/tokens/exchange", json=exchange_data, headers=headers)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Token exchange successful: {data['message']}")
            print(f"New token balance: {data['new_token_balance']}")
        else:
            print(f"❌ Token exchange failed: {response.status_code} - {response.text}")
            return
    else:
        print("❌ Not enough points for token exchange")
        return
    
    # Test Category B game
    print("\n🎰 Playing Category B game...")
    game_data = {'game_type': 'slots', 'token_cost': 3}
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(f"{base_url}/api/games/category-b/play", json=game_data, headers=headers)
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Category B game played successfully!")
        print(f"Result: {data}")
    else:
        print(f"❌ Category B game failed: {response.text}")

if __name__ == "__main__":
    test_complete_flow()