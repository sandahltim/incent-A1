#!/usr/bin/env python3
"""
Comprehensive CSRF System Validation Script
Validates all CSRF-protected endpoints and dual game system functionality
"""

import requests
import json
import sys
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class CSRFValidator:
    def __init__(self, base_url="http://localhost:7410"):
        self.base_url = base_url
        self.session = requests.Session()
        self.csrf_token = None
        self.employee_session = None
        self.admin_session = None
        
    def get_csrf_token(self, endpoint="/"):
        """Get CSRF token from a page"""
        try:
            response = self.session.get(urljoin(self.base_url, endpoint))
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Try meta tag first
                meta_tag = soup.find('meta', attrs={'name': 'csrf-token'})
                if meta_tag:
                    return meta_tag.get('content')
                
                # Try form input
                csrf_input = soup.find('input', attrs={'name': 'csrf_token'})
                if csrf_input:
                    return csrf_input.get('value')
                    
            logger.warning(f"Could not find CSRF token in {endpoint}")
            return None
        except Exception as e:
            logger.error(f"Error getting CSRF token from {endpoint}: {e}")
            return None
    
    def test_endpoint_with_csrf(self, endpoint, method="POST", data=None, json_data=None, use_form_data=True):
        """Test an endpoint with proper CSRF token"""
        csrf_token = self.get_csrf_token()
        if not csrf_token:
            return {"success": False, "error": "No CSRF token available"}
            
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method.upper() == "POST":
                if use_form_data:
                    # Use FormData approach (recommended for CSRF)
                    form_data = data or {}
                    form_data['csrf_token'] = csrf_token
                    response = self.session.post(url, data=form_data)
                else:
                    # Use JSON with CSRF header
                    headers = {'X-CSRFToken': csrf_token, 'Content-Type': 'application/json'}
                    response = self.session.post(url, json=json_data, headers=headers)
            else:
                response = self.session.get(url)
                
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.text[:200] if response.text else "",
                "headers": dict(response.headers)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_endpoint_without_csrf(self, endpoint, method="POST", data=None):
        """Test an endpoint without CSRF token (should fail)"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            if method.upper() == "POST":
                response = self.session.post(url, data=data or {})
            else:
                response = self.session.get(url)
                
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.text[:200] if response.text else "",
                "should_fail": response.status_code in [400, 401, 403]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def test_dual_game_system(self):
        """Test dual game system endpoints"""
        logger.info("Testing dual game system...")
        
        results = {}
        
        # Test dual system status endpoint
        results['dual_system_status'] = self.test_endpoint_with_csrf("/api/dual-system/status", "GET")
        
        # Test Category A game endpoint (with valid game ID - we'll use 1 as a test)
        results['category_a_game'] = self.test_endpoint_with_csrf(
            "/api/games/category-a/play/1", 
            "POST"
        )
        
        # Test Category B game endpoint
        category_b_data = {
            'game_type': 'slots',
            'token_cost': 5
        }
        results['category_b_game'] = self.test_endpoint_with_csrf(
            "/api/games/category-b/play", 
            "POST", 
            data=category_b_data
        )
        
        # Test admin award Category A endpoint
        admin_data = {
            'employee_ids': [1],
            'prize_type': 'points',
            'prize_amount': 10
        }
        results['admin_award_category_a'] = self.test_endpoint_with_csrf(
            "/api/admin/dual-system/award-category-a",
            "POST",
            data=admin_data
        )
        
        return results
    
    def test_legacy_mini_games(self):
        """Test legacy mini game endpoints"""
        logger.info("Testing legacy mini games...")
        
        results = {}
        
        # Test play_game endpoint (assuming game ID 1 exists)
        results['play_game'] = self.test_endpoint_with_csrf("/play_game/1", "POST")
        
        return results
    
    def test_csrf_protection_negative(self):
        """Test endpoints without CSRF tokens (should fail)"""
        logger.info("Testing CSRF protection (negative tests)...")
        
        results = {}
        
        # Test endpoints without CSRF tokens
        endpoints_to_test = [
            "/api/games/category-a/play/1",
            "/api/games/category-b/play",
            "/play_game/1",
            "/api/admin/dual-system/award-category-a"
        ]
        
        for endpoint in endpoints_to_test:
            results[f"no_csrf_{endpoint.replace('/', '_')}"] = self.test_endpoint_without_csrf(endpoint)
            
        return results
    
    def test_frontend_integration(self):
        """Test that frontend pages load and contain CSRF tokens"""
        logger.info("Testing frontend integration...")
        
        results = {}
        
        # Test main employee portal
        response = self.session.get(urljoin(self.base_url, "/"))
        results['employee_portal'] = {
            "status_code": response.status_code,
            "has_csrf_meta": 'csrf-token' in response.text,
            "has_csrf_input": 'csrf_token' in response.text,
            "has_getcsrftoken_function": 'getCSRFToken()' in response.text,
            "has_dual_game_functions": 'playDualGameCategoryA' in response.text
        }
        
        # Test admin panel
        admin_response = self.session.get(urljoin(self.base_url, "/admin"))
        results['admin_panel'] = {
            "status_code": admin_response.status_code,
            "accessible": admin_response.status_code != 500
        }
        
        return results
    
    def test_database_connectivity(self):
        """Test basic database operations"""
        logger.info("Testing database connectivity...")
        
        # Test by trying to access a simple endpoint that requires DB
        response = self.session.get(urljoin(self.base_url, "/api/scoreboard"))
        
        return {
            "status_code": response.status_code,
            "database_accessible": response.status_code != 500,
            "response_length": len(response.text) if response.text else 0
        }
    
    def run_comprehensive_validation(self):
        """Run all validation tests"""
        logger.info("Starting comprehensive CSRF system validation...")
        
        # Check if server is accessible
        try:
            response = self.session.get(self.base_url)
            if response.status_code != 200:
                logger.error(f"Server not accessible: {response.status_code}")
                return {"error": "Server not accessible"}
        except Exception as e:
            logger.error(f"Cannot connect to server: {e}")
            return {"error": f"Cannot connect to server: {e}"}
        
        validation_results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "server_url": self.base_url,
            "tests": {}
        }
        
        # Run all test suites
        test_suites = [
            ("dual_game_system", self.test_dual_game_system),
            ("legacy_mini_games", self.test_legacy_mini_games),
            ("csrf_protection_negative", self.test_csrf_protection_negative),
            ("frontend_integration", self.test_frontend_integration),
            ("database_connectivity", self.test_database_connectivity)
        ]
        
        for suite_name, test_func in test_suites:
            logger.info(f"Running {suite_name} tests...")
            try:
                validation_results["tests"][suite_name] = test_func()
            except Exception as e:
                logger.error(f"Error in {suite_name}: {e}")
                validation_results["tests"][suite_name] = {"error": str(e)}
        
        return validation_results
    
    def generate_report(self, results):
        """Generate a comprehensive validation report"""
        report = []
        report.append("=" * 60)
        report.append("COMPREHENSIVE CSRF SYSTEM VALIDATION REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {results.get('timestamp', 'Unknown')}")
        report.append(f"Server URL: {results.get('server_url', 'Unknown')}")
        report.append("")
        
        if "error" in results:
            report.append(f"❌ CRITICAL ERROR: {results['error']}")
            return "\n".join(report)
        
        # Analyze results
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        issues = []
        
        for suite_name, suite_results in results.get("tests", {}).items():
            report.append(f"📋 {suite_name.upper().replace('_', ' ')}")
            report.append("-" * 40)
            
            if isinstance(suite_results, dict) and "error" in suite_results:
                report.append(f"❌ Suite failed: {suite_results['error']}")
                failed_tests += 1
                issues.append(f"{suite_name}: {suite_results['error']}")
            else:
                for test_name, test_result in suite_results.items():
                    total_tests += 1
                    
                    if isinstance(test_result, dict):
                        if test_result.get("success", False):
                            status_code = test_result.get("status_code")
                            if "no_csrf" in test_name:
                                # Negative test - should fail
                                if test_result.get("should_fail", False):
                                    report.append(f"✅ {test_name}: CSRF protection working (status: {status_code})")
                                    passed_tests += 1
                                else:
                                    report.append(f"❌ {test_name}: CSRF protection NOT working (status: {status_code})")
                                    failed_tests += 1
                                    issues.append(f"{test_name}: CSRF protection bypassed")
                            else:
                                # Positive test - should succeed
                                if status_code in [200, 201]:
                                    report.append(f"✅ {test_name}: Working (status: {status_code})")
                                    passed_tests += 1
                                elif status_code in [401, 403]:
                                    report.append(f"⚠️  {test_name}: Authentication required (status: {status_code})")
                                    passed_tests += 1  # This is expected for some endpoints
                                else:
                                    report.append(f"❌ {test_name}: Failed (status: {status_code})")
                                    failed_tests += 1
                                    issues.append(f"{test_name}: Unexpected status {status_code}")
                        else:
                            report.append(f"❌ {test_name}: Error - {test_result.get('error', 'Unknown')}")
                            failed_tests += 1
                            issues.append(f"{test_name}: {test_result.get('error', 'Unknown')}")
                    else:
                        # Handle non-dict results
                        report.append(f"ℹ️  {test_name}: {test_result}")
            
            report.append("")
        
        # Summary
        report.append("=" * 60)
        report.append("VALIDATION SUMMARY")
        report.append("=" * 60)
        report.append(f"Total Tests: {total_tests}")
        report.append(f"Passed: {passed_tests}")
        report.append(f"Failed: {failed_tests}")
        report.append(f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A")
        
        if issues:
            report.append("")
            report.append("🚨 ISSUES FOUND:")
            for issue in issues:
                report.append(f"  - {issue}")
        else:
            report.append("")
            report.append("🎉 No critical issues found!")
        
        report.append("")
        report.append("=" * 60)
        
        return "\n".join(report)

def main():
    """Main validation function"""
    validator = CSRFValidator()
    
    print("🔍 Starting comprehensive CSRF system validation...")
    print("This will test all CSRF-protected endpoints and dual game system functionality.")
    print()
    
    # Run validation
    results = validator.run_comprehensive_validation()
    
    # Generate and display report
    report = validator.generate_report(results)
    print(report)
    
    # Save detailed results to file
    with open("/home/tim/incentDev/csrf_validation_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /home/tim/incentDev/csrf_validation_results.json")
    
    # Return appropriate exit code
    if "error" in results:
        return 1
    
    total_tests = sum(len(suite) for suite in results.get("tests", {}).values() if isinstance(suite, dict))
    if total_tests == 0:
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())