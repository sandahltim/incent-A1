#!/usr/bin/env python3
"""
Admin Page Functionality Testing Script
Tests the critical admin functions that were affected by the audio system interference.
"""

import time
import json
import requests
from urllib.parse import urljoin

BASE_URL = "http://localhost:7409"

class AdminTester:
    def __init__(self):
        self.session = requests.Session()
        self.csrf_token = None
        
    def get_csrf_token(self, html_content):
        """Extract CSRF token from HTML content"""
        import re
        match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', html_content)
        if match:
            return match.group(1)
        # Try meta tag approach
        match = re.search(r'<meta name="csrf-token" content="([^"]*)"', html_content)
        if match:
            return match.group(1)
        return None
        
    def test_admin_page_loading(self):
        """Test admin page loads without audio scripts"""
        print("🔍 Testing admin page loading...")
        
        try:
            response = self.session.get(urljoin(BASE_URL, "/admin"))
            html_content = response.text
            
            # Check that admin page loads successfully
            if response.status_code != 200:
                print(f"❌ Admin page loading failed: {response.status_code}")
                return False
                
            # Verify admin page class is present
            if 'admin-page' not in html_content:
                print("❌ Admin page class not found")
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
                    
            # Verify Add Employee modal is present
            if 'addEmployeeModal' not in html_content:
                print("❌ Add Employee modal not found")
                return False
                
            print("✅ Admin page loads correctly without audio scripts")
            return True
            
        except Exception as e:
            print(f"❌ Admin page loading test failed: {e}")
            return False
            
    def test_main_page_audio_retention(self):
        """Test main page retains audio scripts"""
        print("🔍 Testing main page audio script retention...")
        
        try:
            response = self.session.get(BASE_URL)
            html_content = response.text
            
            if response.status_code != 200:
                print(f"❌ Main page loading failed: {response.status_code}")
                return False
                
            # Verify audio scripts ARE loaded on main page
            audio_scripts = [
                'audio-engine.min.js',
                'progressive-audio-loader.js', 
                'audio-controls.min.js'
            ]
            
            for script in audio_scripts:
                if script not in html_content:
                    print(f"❌ Audio script {script} missing from main page")
                    return False
                    
            print("✅ Main page retains audio scripts correctly")
            return True
            
        except Exception as e:
            print(f"❌ Main page audio test failed: {e}")
            return False
            
    def test_employee_portal_audio_retention(self):
        """Test employee portal retains audio scripts"""
        print("🔍 Testing employee portal audio script retention...")
        
        try:
            response = self.session.get(urljoin(BASE_URL, "/employee_portal"))
            html_content = response.text
            
            if response.status_code != 200:
                print(f"❌ Employee portal loading failed: {response.status_code}")
                return False
                
            # Verify audio scripts ARE loaded on employee portal
            audio_scripts = [
                'audio-engine.min.js',
                'progressive-audio-loader.js', 
                'audio-controls.min.js'
            ]
            
            for script in audio_scripts:
                if script not in html_content:
                    print(f"❌ Audio script {script} missing from employee portal")
                    return False
                    
            print("✅ Employee portal retains audio scripts correctly")
            return True
            
        except Exception as e:
            print(f"❌ Employee portal audio test failed: {e}")
            return False
            
    def test_admin_api_endpoints(self):
        """Test critical admin API endpoints respond correctly"""
        print("🔍 Testing admin API endpoints...")
        
        try:
            # First get admin page to establish session
            admin_response = self.session.get(urljoin(BASE_URL, "/admin"))
            self.csrf_token = self.get_csrf_token(admin_response.text)
            
            if not self.csrf_token:
                print("❌ Could not extract CSRF token")
                return False
                
            # Test employee list endpoint (should be accessible)
            employees_response = self.session.get(urljoin(BASE_URL, "/api/employees"))
            if employees_response.status_code == 200:
                print("✅ Employee list API endpoint accessible")
            else:
                print(f"⚠️ Employee list API returned: {employees_response.status_code}")
                
            # Test admin authentication check
            auth_response = self.session.get(urljoin(BASE_URL, "/admin"))
            if auth_response.status_code == 200:
                print("✅ Admin page accessible")
            else:
                print(f"❌ Admin page access failed: {auth_response.status_code}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Admin API endpoint test failed: {e}")
            return False
            
    def test_javascript_console_errors(self):
        """Test for JavaScript console errors (basic check)"""
        print("🔍 Testing for JavaScript compatibility...")
        
        try:
            # Get admin page HTML
            admin_response = self.session.get(urljoin(BASE_URL, "/admin"))
            html_content = admin_response.text
            
            # Look for common JavaScript error patterns
            error_indicators = [
                'ReferenceError',
                'TypeError: Cannot read',
                'Uncaught Error',
                'casinoAudio is not defined'
            ]
            
            # These shouldn't be in the HTML content
            for indicator in error_indicators:
                if indicator in html_content:
                    print(f"⚠️ Potential JavaScript error indicator found: {indicator}")
                    
            # Verify admin-specific JavaScript is present
            if 'showAddEmployeeModal' in html_content:
                print("✅ Admin JavaScript functions present")
            else:
                print("❌ Admin JavaScript functions missing")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ JavaScript compatibility test failed: {e}")
            return False
            
    def run_all_tests(self):
        """Run comprehensive admin functionality tests"""
        print("🚀 Starting Admin Functionality Validation Tests")
        print("=" * 60)
        
        test_results = {
            'admin_page_loading': self.test_admin_page_loading(),
            'main_page_audio': self.test_main_page_audio_retention(),
            'employee_portal_audio': self.test_employee_portal_audio_retention(),
            'admin_api_endpoints': self.test_admin_api_endpoints(),
            'javascript_compatibility': self.test_javascript_console_errors()
        }
        
        print("\n" + "=" * 60)
        print("🏁 TEST RESULTS SUMMARY")
        print("=" * 60)
        
        passed_tests = 0
        total_tests = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
            if result:
                passed_tests += 1
                
        print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
        
        if passed_tests == total_tests:
            print("🎉 ALL TESTS PASSED - Admin functionality restored!")
        else:
            print("⚠️ Some tests failed - manual investigation needed")
            
        return test_results

if __name__ == "__main__":
    tester = AdminTester()
    results = tester.run_all_tests()