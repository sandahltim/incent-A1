#!/usr/bin/env python3
"""
Quick test of just Category B game functionality
"""

import requests
import re
import json

def test_category_b():
    session = requests.Session()
    base_url = "http://localhost:7409"
    
    print("=== CATEGORY B TEST ===")
    
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
    
    # Check status
    response = session.get(f"{base_url}/api/dual-system/status")
    status = response.json()
    print(f"Current tokens: {status['token_account']['token_balance']}")
    
    # Test Category B game
    game_data = {'game_type': 'slots', 'token_cost': 3}
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    print("\nTesting Category B...")
    response = session.post(f"{base_url}/api/games/category-b/play", json=game_data, headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_category_b()