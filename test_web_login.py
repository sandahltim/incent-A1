#!/usr/bin/env python3
"""
Test Employee Portal Web Login
Tests the actual web login process with proper session handling
"""

import requests
from bs4 import BeautifulSoup

def test_web_login():
    """Test the actual web login process"""
    
    base_url = "http://127.0.0.1:5002"
    employee_id = "E001"
    pin = "8101"
    
    print("Testing Employee Portal Web Login")
    print("=" * 40)
    
    # Start a session to maintain cookies
    session = requests.Session()
    
    try:
        # First, get the login page to obtain CSRF token
        print(f"1. Getting login page from {base_url}/employee_portal...")
        response = session.get(f"{base_url}/employee_portal")
        
        if response.status_code != 200:
            print(f"ERROR: Failed to get login page. Status: {response.status_code}")
            return False
        
        print("   Login page retrieved successfully")
        
        # Parse the HTML to find CSRF token
        soup = BeautifulSoup(response.text, 'html.parser')
        csrf_input = soup.find('input', {'name': 'csrf_token'})
        
        if not csrf_input:
            print("ERROR: CSRF token not found in login page")
            return False
        
        csrf_token = csrf_input.get('value')
        print(f"   CSRF token found: {csrf_token[:20]}...")
        
        # Prepare login data
        login_data = {
            'csrf_token': csrf_token,
            'employee_id': employee_id,
            'pin': pin,
            'submit': 'Access'
        }
        
        # Attempt login
        print(f"\n2. Attempting login with employee {employee_id}...")
        response = session.post(
            f"{base_url}/employee_portal",
            data=login_data,
            allow_redirects=True
        )
        
        if response.status_code != 200:
            print(f"ERROR: Login request failed. Status: {response.status_code}")
            return False
        
        print("   Login request completed")
        
        # Check if login was successful
        if "Welcome Back" in response.text or "Change PIN" in response.text:
            print(f"\nSUCCESS: Employee {employee_id} logged in successfully!")
            
            # Check for employee name in response
            if "Tim Sandahl" in response.text:
                print("   Employee name 'Tim Sandahl' found in response")
            
            # Check for features available after login
            features = []
            if "Change PIN" in response.text:
                features.append("Change PIN")
            if "Mini-Games" in response.text or "mini-games" in response.text:
                features.append("Mini-Games")
            if "Logout" in response.text:
                features.append("Logout")
            if "Your Performance Dashboard" in response.text:
                features.append("Analytics Dashboard")
            
            if features:
                print(f"   Available features: {', '.join(features)}")
            
            return True
        else:
            # Check for error messages
            if "Invalid ID or PIN" in response.text:
                print("ERROR: Login failed - Invalid ID or PIN")
            elif "alert-danger" in response.text:
                soup = BeautifulSoup(response.text, 'html.parser')
                error_div = soup.find('div', class_='alert-danger')
                if error_div:
                    print(f"ERROR: {error_div.get_text(strip=True)}")
            else:
                print("ERROR: Login appears to have failed (no welcome message found)")
            
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to Flask app. Is it running on port 5002?")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = test_web_login()
    sys.exit(0 if success else 1)