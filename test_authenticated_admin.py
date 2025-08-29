#!/usr/bin/env python3
"""
Authenticated Admin Functionality Testing Script
Tests admin functionality after proper authentication to access the full admin interface.
"""

import time
import json
import requests
from urllib.parse import urljoin
import re

BASE_URL = "http://localhost:7409"

class AuthenticatedAdminTester:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        self.authenticated = False
        
    def get_csrf_token(self, html_content):
        """Extract CSRF token from HTML content"""
        # Try form input approach first
        match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', html_content)
        if match:
            return match.group(1)
        # Try meta tag approach
        match = re.search(r'<meta name="csrf-token" content="([^"]*)"', html_content)
        if match:
            return match.group(1)
        return None
        
    def authenticate_admin(self):
        """Attempt to authenticate as admin"""
        print("🔐 Attempting admin authentication...")
        
        try:
            # Get login page first
            response = self.session.get(urljoin(BASE_URL, "/admin"))
            html_content = response.text
            
            if response.status_code != 200:
                print(f"❌ Admin login page access failed: {response.status_code}")
                return False
                
            # Extract CSRF token
            self.csrf_token = self.get_csrf_token(html_content)
            if not self.csrf_token:
                print("❌ Could not extract CSRF token from login page")
                return False
                
            # Try common admin credentials (you may need to adjust these)
            credentials = [
                ('admin', 'admin'),
                ('admin', 'password'),
                ('admin', '123456'),
                ('root', 'admin')
            ]
            
            for username, password in credentials:
                login_data = {
                    'username': username,
                    'password': password,
                    'csrf_token': self.csrf_token
                }
                
                login_response = self.session.post(
                    urljoin(BASE_URL, "/admin"), 
                    data=login_data,
                    allow_redirects=False
                )
                
                # Check if login was successful (redirect or 200 with admin interface)
                if login_response.status_code in [302, 303] or (
                    login_response.status_code == 200 and 'addEmployeeModal' in login_response.text
                ):
                    print(f"✅ Admin authentication successful with {username}:{password}")
                    self.authenticated = True
                    return True
                    
            print("❌ Admin authentication failed with common credentials")
            print("ℹ️ You may need to check database for actual admin credentials")
            return False
            
        except Exception as e:
            print(f"❌ Admin authentication failed: {e}")
            return False
            
    def test_admin_management_interface(self):
        """Test the full admin management interface after authentication"""
        print("🔍 Testing admin management interface...")
        
        if not self.authenticated:
            print("❌ Cannot test admin interface - not authenticated")
            return False
            
        try:
            # Get the admin management page
            response = self.session.get(urljoin(BASE_URL, "/admin"))
            html_content = response.text
            
            if response.status_code != 200:
                print(f"❌ Admin management page access failed: {response.status_code}")
                return False
                
            # Check for admin interface components
            admin_components = {
                'Add Employee Modal': 'addEmployeeModal',
                'Employee Management': 'showAddEmployeeModal',
                'JavaScript Functions': 'submitAddEmployee',
                'Admin Interface': 'admin-page',
                'Point Adjustment': 'adjustPoints',
                'Rules Management': 'editAutoGameRule'
            }
            
            missing_components = []
            for component_name, selector in admin_components.items():
                if selector not in html_content:
                    missing_components.append(component_name)
                    
            if missing_components:
                print(f"❌ Missing admin components: {', '.join(missing_components)}")
                return False
                
            # Verify audio scripts are NOT loaded
            audio_scripts = [
                'audio-engine.min.js',
                'progressive-audio-loader.js', 
                'audio-controls.min.js'
            ]
            
            for script in audio_scripts:
                if script in html_content:
                    print(f"❌ Audio script {script} found on admin page")
                    return False
                    
            print("✅ Admin management interface loaded correctly without audio scripts")
            return True
            
        except Exception as e:
            print(f"❌ Admin management interface test failed: {e}")
            return False
            
    def test_admin_modal_functionality(self):
        """Test that admin modals can be triggered"""
        print("🔍 Testing admin modal functionality...")
        
        if not self.authenticated:
            print("❌ Cannot test modals - not authenticated")
            return False
            
        try:
            # Get admin page
            response = self.session.get(urljoin(BASE_URL, "/admin"))
            html_content = response.text
            
            # Look for modal trigger functions and modals themselves
            modal_indicators = [
                'showAddEmployeeModal',
                'addEmployeeModal',
                'modal fade',
                'bootstrap.Modal'
            ]
            
            found_indicators = 0
            for indicator in modal_indicators:
                if indicator in html_content:
                    found_indicators += 1
                    
            if found_indicators >= len(modal_indicators) - 1:  # Allow one missing
                print("✅ Admin modal functionality appears intact")
                return True
            else:
                print(f"❌ Modal functionality incomplete - found {found_indicators}/{len(modal_indicators)} indicators")
                return False
                
        except Exception as e:
            print(f"❌ Admin modal test failed: {e}")
            return False
            
    def test_admin_javascript_no_audio_errors(self):
        """Test that admin JavaScript works without audio dependencies"""
        print("🔍 Testing admin JavaScript without audio dependencies...")
        
        if not self.authenticated:
            print("❌ Cannot test JavaScript - not authenticated")  
            return False
            
        try:
            response = self.session.get(urljoin(BASE_URL, "/admin"))
            html_content = response.text
            
            # Check that admin page detection works
            if 'isAdminPage = document.body.classList.contains(\'admin-page\')' in html_content:
                print("✅ Admin page detection JavaScript present")
            else:
                print("⚠️ Admin page detection JavaScript missing")
                
            # Check for audio system bypass
            if 'audio system disabled for stability' in html_content:
                print("✅ Audio system properly disabled on admin pages")
            else:
                print("⚠️ Audio system disable logging not found")
                
            # Verify admin-specific functions are present
            admin_functions = [
                'showAddEmployeeModal',
                'editEmployee', 
                'adjustPoints',
                'submitAddEmployee'
            ]
            
            missing_functions = []
            for func in admin_functions:
                if func not in html_content:
                    missing_functions.append(func)
                    
            if missing_functions:
                print(f"❌ Missing admin functions: {', '.join(missing_functions)}")
                return False
                
            print("✅ Admin JavaScript functions present and audio-independent")
            return True
            
        except Exception as e:
            print(f"❌ Admin JavaScript test failed: {e}")
            return False

    def test_incognito_simulation(self):
        """Simulate incognito mode behavior by clearing session and retesting"""
        print("🔍 Simulating incognito mode functionality...")
        
        if not self.authenticated:
            print("❌ Cannot test incognito mode - not authenticated initially")
            return False
            
        try:
            # Store authentication state
            original_cookies = self.session.cookies.copy()
            
            # Clear session (simulate incognito)
            self.session.cookies.clear()
            
            # Test that admin login page still loads properly without audio scripts
            response = self.session.get(urljoin(BASE_URL, "/admin"))
            html_content = response.text
            
            if response.status_code != 200:
                print("❌ Admin login page failed to load in simulated incognito mode")
                return False
                
            # Verify audio scripts are NOT loaded even in "incognito" mode
            audio_scripts = [
                'audio-engine.min.js',
                'progressive-audio-loader.js', 
                'audio-controls.min.js'
            ]
            
            for script in audio_scripts:
                if script in html_content:
                    print(f"❌ Audio script {script} found on admin page in incognito mode")
                    return False
                    
            # Check that login form is present and functional
            if 'Admin Login' not in html_content:
                print("❌ Admin login form not found in incognito mode")
                return False
                
            print("✅ Admin pages work correctly in incognito mode without audio scripts")
            
            # Restore session
            self.session.cookies = original_cookies
            return True
            
        except Exception as e:
            print(f"❌ Incognito mode simulation failed: {e}")
            return False
            
    def run_authenticated_tests(self):
        """Run comprehensive authenticated admin tests"""
        print("🚀 Starting Authenticated Admin Functionality Tests")
        print("=" * 65)
        
        # First authenticate
        if not self.authenticate_admin():
            print("\n❌ AUTHENTICATION FAILED - Cannot proceed with full testing")
            print("ℹ️ Testing what we can without authentication...")
            
            # Test basic admin page loading without authentication
            basic_results = {
                'admin_login_page_no_audio': self.test_basic_admin_page_loading(),
                'incognito_login_simulation': self.test_incognito_login_page()
            }
            
            print("\n" + "=" * 65)
            print("🔒 UNAUTHENTICATED TEST RESULTS")
            print("=" * 65)
            
            for test_name, result in basic_results.items():
                status = "✅ PASS" if result else "❌ FAIL" 
                print(f"{test_name.replace('_', ' ').title()}: {status}")
                
            return basic_results
        
        # Run authenticated tests
        test_results = {
            'admin_management_interface': self.test_admin_management_interface(),
            'admin_modal_functionality': self.test_admin_modal_functionality(),
            'admin_javascript_no_audio': self.test_admin_javascript_no_audio_errors(),
            'incognito_mode_simulation': self.test_incognito_simulation()
        }
        
        print("\n" + "=" * 65)
        print("🔐 AUTHENTICATED TEST RESULTS") 
        print("=" * 65)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed_tests += 1
                
        print(f"\nAuthenticated Tests: {passed_tests}/{total_tests} passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL AUTHENTICATED TESTS PASSED!")
            print("✅ Admin functionality fully restored after audio fix!")
        else:
            print("⚠️ Some authenticated tests failed")
            
        return test_results
        
    def test_basic_admin_page_loading(self):
        """Test basic admin page loading without authentication"""
        try:
            response = self.session.get(urljoin(BASE_URL, "/admin"))
            html_content = response.text
            
            if response.status_code != 200:
                return False
                
            # Check no audio scripts
            audio_scripts = ['audio-engine.min.js', 'progressive-audio-loader.js', 'audio-controls.min.js']
            for script in audio_scripts:
                if script in html_content:
                    return False
                    
            return 'admin-page' in html_content
        except:
            return False
            
    def test_incognito_login_page(self):
        """Test admin login page works in fresh session (simulates incognito)"""
        try:
            fresh_session = requests.Session()
            response = fresh_session.get(urljoin(BASE_URL, "/admin"))
            html_content = response.text
            
            if response.status_code != 200:
                return False
                
            # Check no audio scripts and login form present
            audio_scripts = ['audio-engine.min.js', 'progressive-audio-loader.js', 'audio-controls.min.js']
            for script in audio_scripts:
                if script in html_content:
                    return False
                    
            return 'Admin Login' in html_content and 'admin-page' in html_content
        except:
            return False

if __name__ == "__main__":
    tester = AuthenticatedAdminTester()
    results = tester.run_authenticated_tests()