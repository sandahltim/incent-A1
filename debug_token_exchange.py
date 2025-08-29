#!/usr/bin/env python3
"""
Debug token exchange issue specifically
"""

import requests
import re
import json

def debug_token_exchange():
    session = requests.Session()
    base_url = "http://localhost:7409"
    
    print("=== TOKEN EXCHANGE DEBUG ===")
    
    # Step 1: Login
    print("\n1. Getting CSRF and logging in...")
    response = session.get(f"{base_url}/employee_portal")
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    csrf_token = csrf_match.group(1)
    
    login_data = {
        'csrf_token': csrf_token,
        'employee_id': 'E002',
        'pin': '1234'
    }
    session.post(f"{base_url}/employee_portal", data=login_data)
    print("✅ Logged in successfully")
    
    # Step 2: Check current status
    print("\n2. Checking dual system status...")
    response = session.get(f"{base_url}/api/dual-system/status")
    status_data = response.json()
    print(f"Current points: {status_data['token_account']['current_points']}")
    print(f"Token balance: {status_data['token_account']['token_balance']}")
    print(f"Can exchange tokens: {status_data['can_exchange_tokens']}")
    print(f"Exchange message: {status_data['exchange_message']}")
    
    # Step 3: Attempt token exchange
    print("\n3. Attempting token exchange...")
    exchange_data = {'token_amount': 5}
    headers = {
        'Content-Type': 'application/json',
        'X-CSRFToken': csrf_token
    }
    
    print(f"Request data: {json.dumps(exchange_data)}")
    print(f"Headers: {headers}")
    
    response = session.post(f"{base_url}/api/tokens/exchange", json=exchange_data, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Step 4: Check what the token economy says
    print("\n4. Checking token economy service directly...")
    try:
        from services.token_economy import TokenEconomy
        token_economy = TokenEconomy()
        
        # Check if employee can exchange
        can_exchange, message = token_economy.can_exchange_tokens('E002')
        print(f"Can exchange (direct check): {can_exchange}")
        print(f"Message (direct check): {message}")
        
        # Get account details
        account = token_economy.get_employee_token_account('E002')
        print(f"Account details: {account}")
        
        # Try direct exchange
        if can_exchange:
            success, msg = token_economy.exchange_points_for_tokens('E002', 5)
            print(f"Direct exchange result: {success}, {msg}")
        
    except Exception as e:
        print(f"Error in direct token economy check: {e}")

if __name__ == "__main__":
    debug_token_exchange()