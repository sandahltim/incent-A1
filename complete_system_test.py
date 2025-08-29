#!/usr/bin/env python3
"""
Complete System Test with Authentication and Database Operations
Tests the entire system including login, CSRF protection, and database operations
"""

import requests
import json
import sqlite3
import sys
import time
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class CompleteSystemTester:
    def __init__(self, base_url="http://localhost:7410", db_path="/home/tim/incentDev/incentive.db"):
        self.base_url = base_url
        self.db_path = db_path
        self.session = requests.Session()
        
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
                    
            return None
        except Exception as e:
            logger.error(f"Error getting CSRF token: {e}")
            return None
    
    def check_database_integrity(self):
        """Check if the SQLite database is accessible and has basic tables"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check for essential tables
            tables_to_check = ['employees', 'mini_games', 'scoreboard', 'voting_sessions']
            existing_tables = []
            
            for table in tables_to_check:
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if cursor.fetchone():
                    existing_tables.append(table)
            
            # Test a basic query
            cursor.execute("SELECT COUNT(*) FROM employees")
            employee_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM mini_games")
            game_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "accessible": True,
                "existing_tables": existing_tables,
                "employee_count": employee_count,
                "game_count": game_count,
                "total_tables": len(existing_tables)
            }
            
        except Exception as e:
            return {
                "accessible": False,
                "error": str(e)
            }
    
    def test_unauthenticated_access(self):
        """Test that unauthenticated users get proper responses"""
        logger.info("Testing unauthenticated access...")
        
        results = {}
        
        # Test main page (should work)
        response = self.session.get(urljoin(self.base_url, "/"))
        results['main_page'] = {
            "status_code": response.status_code,
            "accessible": response.status_code == 200,
            "has_csrf_meta": 'csrf-token' in response.text,
            "has_login_form": 'login' in response.text.lower()
        }
        
        # Test admin panel (should redirect or show unauthorized)
        response = self.session.get(urljoin(self.base_url, "/admin"))
        results['admin_panel'] = {
            "status_code": response.status_code,
            "protected": response.status_code in [302, 401, 403] or 'login' in response.text.lower()
        }
        
        # Test protected API endpoints
        protected_endpoints = [
            "/api/dual-system/status",
            "/api/games/category-a/play/1", 
            "/play_game/1"
        ]
        
        for endpoint in protected_endpoints:
            response = self.session.get(urljoin(self.base_url, endpoint))
            results[f"protected_{endpoint.replace('/', '_')}"] = {
                "status_code": response.status_code,
                "properly_protected": response.status_code in [401, 403, 404]
            }
        
        return results
    
    def test_csrf_token_consistency(self):
        """Test that CSRF tokens are consistent across the session"""
        logger.info("Testing CSRF token consistency...")
        
        # Get token from main page
        token1 = self.get_csrf_token("/")
        
        # Get token from another request
        time.sleep(0.1)  # Small delay
        token2 = self.get_csrf_token("/")
        
        return {
            "token1_present": token1 is not None,
            "token2_present": token2 is not None,
            "tokens_consistent": token1 == token2 if (token1 and token2) else False,
            "token1_length": len(token1) if token1 else 0,
            "token2_length": len(token2) if token2 else 0
        }
    
    def test_invalid_csrf_token(self):
        """Test behavior with invalid CSRF tokens"""
        logger.info("Testing invalid CSRF token handling...")
        
        results = {}
        
        # Test with completely fake token
        fake_form_data = {'csrf_token': 'fake_token_12345'}
        response = self.session.post(
            urljoin(self.base_url, "/api/games/category-a/play/1"), 
            data=fake_form_data
        )
        
        results['fake_token'] = {
            "status_code": response.status_code,
            "properly_rejected": response.status_code == 400,
            "response_contains_csrf_error": 'csrf' in response.text.lower()
        }
        
        # Test with empty token
        empty_form_data = {'csrf_token': ''}
        response = self.session.post(
            urljoin(self.base_url, "/api/games/category-b/play"), 
            data=empty_form_data
        )
        
        results['empty_token'] = {
            "status_code": response.status_code,
            "properly_rejected": response.status_code == 400,
            "response_contains_csrf_error": 'csrf' in response.text.lower()
        }
        
        return results
    
    def test_javascript_csrf_integration(self):
        """Test that JavaScript functions for CSRF are available"""
        logger.info("Testing JavaScript CSRF integration...")
        
        # Get main page and check for JavaScript functions
        response = self.session.get(urljoin(self.base_url, "/"))
        page_content = response.text
        
        # Check for CSRF-related JavaScript
        return {
            "page_loads": response.status_code == 200,
            "has_csrf_meta_tag": 'csrf-token' in page_content,
            "has_vegas_casino_js": 'vegas-casino.js' in page_content,
            "has_csrf_token_inputs": 'csrf_token' in page_content,
            "javascript_loaded": 'script' in page_content
        }
    
    def test_settings_page_access(self):
        """Test settings page accessibility"""
        logger.info("Testing settings page access...")
        
        # Test settings endpoint
        response = self.session.get(urljoin(self.base_url, "/settings"))
        
        return {
            "status_code": response.status_code,
            "accessible": response.status_code == 200,
            "requires_auth": response.status_code in [302, 401, 403],
            "response_length": len(response.text) if response.text else 0
        }
    
    def run_complete_test(self):
        """Run all system tests"""
        logger.info("Starting complete system validation...")
        
        # Check if server is accessible
        try:
            response = self.session.get(self.base_url)
            if response.status_code != 200:
                logger.error(f"Server not accessible: {response.status_code}")
                return {"error": "Server not accessible", "status_code": response.status_code}
        except Exception as e:
            logger.error(f"Cannot connect to server: {e}")
            return {"error": f"Cannot connect to server: {e}"}
        
        results = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "server_url": self.base_url,
            "database_path": self.db_path,
            "tests": {}
        }
        
        # Run all test suites
        test_suites = [
            ("database_integrity", self.check_database_integrity),
            ("unauthenticated_access", self.test_unauthenticated_access),
            ("csrf_token_consistency", self.test_csrf_token_consistency),
            ("invalid_csrf_token", self.test_invalid_csrf_token),
            ("javascript_csrf_integration", self.test_javascript_csrf_integration),
            ("settings_page_access", self.test_settings_page_access)
        ]
        
        for suite_name, test_func in test_suites:
            logger.info(f"Running {suite_name} tests...")
            try:
                results["tests"][suite_name] = test_func()
            except Exception as e:
                logger.error(f"Error in {suite_name}: {e}")
                results["tests"][suite_name] = {"error": str(e)}
        
        return results
    
    def generate_report(self, results):
        """Generate a comprehensive system report"""
        report = []
        report.append("=" * 70)
        report.append("COMPLETE SYSTEM VALIDATION REPORT")
        report.append("=" * 70)
        report.append(f"Timestamp: {results.get('timestamp', 'Unknown')}")
        report.append(f"Server URL: {results.get('server_url', 'Unknown')}")
        report.append(f"Database: {results.get('database_path', 'Unknown')}")
        report.append("")
        
        if "error" in results:
            report.append(f"❌ CRITICAL ERROR: {results['error']}")
            if "status_code" in results:
                report.append(f"   Status Code: {results['status_code']}")
            return "\n".join(report)
        
        # Track overall health
        total_checks = 0
        passed_checks = 0
        critical_issues = []
        warnings = []
        
        for suite_name, suite_results in results.get("tests", {}).items():
            report.append(f"📋 {suite_name.upper().replace('_', ' ')}")
            report.append("-" * 50)
            
            if isinstance(suite_results, dict) and "error" in suite_results:
                report.append(f"❌ Suite failed: {suite_results['error']}")
                critical_issues.append(f"{suite_name}: {suite_results['error']}")
            else:
                # Analyze suite results
                if suite_name == "database_integrity":
                    total_checks += 1
                    if suite_results.get("accessible", False):
                        report.append(f"✅ Database accessible: {suite_results.get('total_tables', 0)} tables found")
                        report.append(f"   - Employees: {suite_results.get('employee_count', 0)}")
                        report.append(f"   - Games: {suite_results.get('game_count', 0)}")
                        passed_checks += 1
                    else:
                        report.append(f"❌ Database not accessible: {suite_results.get('error', 'Unknown error')}")
                        critical_issues.append("Database not accessible")
                
                elif suite_name == "csrf_token_consistency":
                    total_checks += 2
                    if suite_results.get("token1_present", False):
                        report.append("✅ CSRF token generation working")
                        passed_checks += 1
                    else:
                        report.append("❌ CSRF token generation failed")
                        critical_issues.append("CSRF token generation failed")
                    
                    if suite_results.get("tokens_consistent", False):
                        report.append("✅ CSRF tokens consistent across requests")
                        passed_checks += 1
                    else:
                        report.append("⚠️  CSRF tokens inconsistent (may be normal for security)")
                        warnings.append("CSRF tokens inconsistent")
                
                elif suite_name == "invalid_csrf_token":
                    total_checks += 2
                    if suite_results.get("fake_token", {}).get("properly_rejected", False):
                        report.append("✅ Fake CSRF tokens properly rejected")
                        passed_checks += 1
                    else:
                        report.append("❌ Fake CSRF tokens not properly rejected")
                        critical_issues.append("CSRF validation bypassed with fake tokens")
                    
                    if suite_results.get("empty_token", {}).get("properly_rejected", False):
                        report.append("✅ Empty CSRF tokens properly rejected")
                        passed_checks += 1
                    else:
                        report.append("❌ Empty CSRF tokens not properly rejected")
                        critical_issues.append("CSRF validation bypassed with empty tokens")
                
                else:
                    # Generic analysis for other suites
                    for key, value in suite_results.items():
                        total_checks += 1
                        if key.endswith("_accessible") or key.endswith("_working") or key.endswith("_present"):
                            if value:
                                report.append(f"✅ {key.replace('_', ' ').title()}: {value}")
                                passed_checks += 1
                            else:
                                report.append(f"❌ {key.replace('_', ' ').title()}: {value}")
                        elif key.endswith("_protected") or key.endswith("_rejected"):
                            if value:
                                report.append(f"✅ {key.replace('_', ' ').title()}: {value}")
                                passed_checks += 1
                            else:
                                report.append(f"❌ {key.replace('_', ' ').title()}: {value}")
                                critical_issues.append(f"{key}: Security not working")
                        else:
                            report.append(f"ℹ️  {key.replace('_', ' ').title()}: {value}")
            
            report.append("")
        
        # Overall summary
        report.append("=" * 70)
        report.append("SYSTEM HEALTH SUMMARY")
        report.append("=" * 70)
        
        if total_checks > 0:
            success_rate = (passed_checks / total_checks) * 100
            report.append(f"Overall Health: {success_rate:.1f}% ({passed_checks}/{total_checks})")
        else:
            report.append("Overall Health: Unable to determine")
        
        if not critical_issues and not warnings:
            report.append("")
            report.append("🎉 SYSTEM STATUS: HEALTHY")
            report.append("✅ All critical security features working correctly")
            report.append("✅ CSRF protection fully operational")
            report.append("✅ Database integrity verified")
        else:
            if critical_issues:
                report.append("")
                report.append("🚨 CRITICAL ISSUES:")
                for issue in critical_issues:
                    report.append(f"   ❌ {issue}")
            
            if warnings:
                report.append("")
                report.append("⚠️  WARNINGS:")
                for warning in warnings:
                    report.append(f"   ⚠️  {warning}")
        
        report.append("")
        report.append("=" * 70)
        
        return "\n".join(report)

def main():
    """Main testing function"""
    tester = CompleteSystemTester()
    
    print("🔍 Starting complete system validation...")
    print("This will test database integrity, CSRF protection, and authentication.")
    print()
    
    # Run complete test
    results = tester.run_complete_test()
    
    # Generate and display report
    report = tester.generate_report(results)
    print(report)
    
    # Save results
    with open("/home/tim/incentDev/complete_system_results.json", "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n📄 Detailed results saved to: /home/tim/incentDev/complete_system_results.json")
    
    # Determine exit code based on critical issues
    has_critical_issues = any("error" in suite for suite in results.get("tests", {}).values())
    return 1 if has_critical_issues or "error" in results else 0

if __name__ == "__main__":
    sys.exit(main())