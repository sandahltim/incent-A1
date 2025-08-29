#!/usr/bin/env python3
"""
Simple CSRF debug script to understand the exact error
"""

import requests
import re

# Test the dual game system CSRF issue
def debug_csrf():
    session = requests.Session()
    base_url = "http://localhost:7409"
    
    print("=== CSRF DEBUG TEST ===")
    
    # Step 1: Login as employee to get session
    print("\n1. Getting CSRF token from employee portal...")
    response = session.get(f"{base_url}/employee_portal")
    if response.status_code != 200:
        print(f"❌ Failed to get employee portal: {response.status_code}")
        return
    
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    if not csrf_match:
        print("❌ Could not extract CSRF token")
        return
        
    csrf_token = csrf_match.group(1)
    print(f"✅ CSRF token: {csrf_token[:20]}...")
    
    # Step 2: Login
    print("\n2. Logging in as E002...")
    login_data = {
        'csrf_token': csrf_token,
        'employee_id': 'E002',
        'pin': '1234'
    }
    response = session.post(f"{base_url}/employee_portal", data=login_data)
    if "logout" not in response.text.lower():
        print("❌ Login failed")
        return
    print("✅ Login successful")
    
    # Step 3: Test Category A endpoint with CSRF
    print("\n3. Testing Category A game endpoint...")
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    response = session.post(f"{base_url}/api/games/category-a/play/31", headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    
    if response.status_code != 200:
        print(f"❌ Category A failed: {response.status_code}")
        print(f"Response: {response.text}")
    else:
        print(f"✅ Category A success: {response.json()}")
    
    # Step 4: Test working endpoint for comparison
    print("\n4. Testing working game endpoint for comparison...")
    response = session.post(f"{base_url}/play_game/31", headers=headers)
    print(f"Status Code: {response.status_code}")
    if response.status_code != 200:
        print(f"Working endpoint also fails: {response.status_code}")
        print(f"Response: {response.text}")
    else:
        print(f"✅ Working endpoint success")

if __name__ == "__main__":
    debug_csrf()