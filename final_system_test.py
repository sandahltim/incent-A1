#!/usr/bin/env python3
"""
Final System Test - Tests all critical functionality of the incentive app
including the quick adjust modal click issue
"""

import requests
import time
# Selenium imports (optional)
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
import json

class IncentiveAppTester:
    def __init__(self, base_url="http://localhost:7411"):
        self.base_url = base_url
        self.results = []
        
    def log_result(self, test_name, passed, details=""):
        result = {
            "test": test_name,
            "passed": passed,
            "details": details,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self.results.append(result)
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
        if details:
            print(f"  Details: {details}")
    
    def test_server_running(self):
        """Test if the server is running"""
        try:
            response = requests.get(self.base_url, timeout=5)
            self.log_result("Server Running", response.status_code == 200, 
                          f"Status code: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            self.log_result("Server Running", False, str(e))
            return False
    
    def test_api_endpoints(self):
        """Test API endpoints"""
        endpoints = [
            ("/api/scoreboard", "GET"),
            ("/api/analytics/dashboard?days=7", "GET"),
            ("/api/analytics/minigames?days=7", "GET"),
        ]
        
        for endpoint, method in endpoints:
            try:
                url = self.base_url + endpoint
                if method == "GET":
                    response = requests.get(url, timeout=5)
                    success = response.status_code == 200
                    self.log_result(f"API Endpoint {endpoint}", success,
                                  f"Status: {response.status_code}")
            except Exception as e:
                self.log_result(f"API Endpoint {endpoint}", False, str(e))
    
    def test_page_elements(self):
        """Test that critical page elements exist"""
        try:
            response = requests.get(self.base_url)
            html = response.text
            
            # Check for critical elements
            elements = {
                "Quick Adjust Links": 'class="rule-item positive-rule quick-adjust-link"',
                "Quick Adjust Modal": 'id="quickAdjustModal"',
                "Adjust Points Form": 'id="adjustPointsForm"',
                "Scoreboard Table": 'id="scoreboardTable"',
                "Analytics Dashboard": 'class="analytics-dashboard"',
            }
            
            for name, selector in elements.items():
                exists = selector in html
                self.log_result(f"Element: {name}", exists,
                              f"Found in HTML" if exists else "NOT FOUND")
                
        except Exception as e:
            self.log_result("Page Elements Test", False, str(e))
    
    def test_javascript_files(self):
        """Test that JavaScript files load"""
        scripts = [
            "/static/script.min.js",
            "/static/js/click-fix.js",
            "/static/js/quick-adjust-fix.js",
        ]
        
        for script in scripts:
            try:
                url = self.base_url + script
                response = requests.get(url, timeout=5)
                success = response.status_code == 200 and len(response.text) > 100
                self.log_result(f"JavaScript File: {script}", success,
                              f"Size: {len(response.text)} bytes")
            except Exception as e:
                self.log_result(f"JavaScript File: {script}", False, str(e))
    
    def test_css_files(self):
        """Test that CSS files load"""
        styles = [
            "/static/style.min.css",
            "/static/css/click-fix.css",
        ]
        
        for style in styles:
            try:
                url = self.base_url + style
                response = requests.get(url, timeout=5)
                success = response.status_code == 200 and len(response.text) > 100
                self.log_result(f"CSS File: {style}", success,
                              f"Size: {len(response.text)} bytes")
            except Exception as e:
                self.log_result(f"CSS File: {style}", False, str(e))
    
    def test_quick_adjust_selenium(self):
        """Test quick adjust functionality with Selenium (if available)"""
        if not SELENIUM_AVAILABLE:
            self.log_result("Selenium Test", False, "Selenium not installed - skipping browser tests")
            return
        
        try:
            # Try to use Selenium for browser testing
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(self.base_url)
            
            # Wait for page to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "quick-adjust-link"))
            )
            
            # Find all quick-adjust links
            links = driver.find_elements(By.CLASS_NAME, "quick-adjust-link")
            self.log_result("Selenium: Quick Adjust Links Found", len(links) > 0,
                          f"Found {len(links)} links")
            
            if links:
                # Try clicking the first link
                links[0].click()
                time.sleep(1)
                
                # Check if modal is visible
                try:
                    modal = driver.find_element(By.ID, "quickAdjustModal")
                    modal_visible = modal.is_displayed()
                    self.log_result("Selenium: Modal Opens on Click", modal_visible,
                                  "Modal visibility after click")
                except NoSuchElementException:
                    self.log_result("Selenium: Modal Opens on Click", False,
                                  "Modal not found after click")
            
            driver.quit()
            
        except ImportError:
            self.log_result("Selenium Test", False, "Selenium not installed")
        except Exception as e:
            self.log_result("Selenium Test", False, f"Error: {str(e)}")
    
    def generate_report(self):
        """Generate a test report"""
        print("\n" + "="*60)
        print("INCENTIVE APP TEST REPORT")
        print("="*60)
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Base URL: {self.base_url}")
        print("\nTest Results Summary:")
        print("-"*60)
        
        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"])
        
        print(f"Total Tests: {len(self.results)}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/len(self.results)*100):.1f}%")
        
        if failed > 0:
            print("\nFailed Tests:")
            print("-"*60)
            for result in self.results:
                if not result["passed"]:
                    print(f"• {result['test']}: {result['details']}")
        
        print("\n" + "="*60)
        print("RECOMMENDATIONS:")
        print("-"*60)
        
        # Check for specific issues
        modal_tests = [r for r in self.results if "modal" in r["test"].lower()]
        modal_failures = [r for r in modal_tests if not r["passed"]]
        
        if modal_failures:
            print("🔧 MODAL ISSUES DETECTED:")
            print("  1. Check browser console for JavaScript errors")
            print("  2. Verify Bootstrap is loaded correctly")
            print("  3. Test with debugQuickAdjust() in browser console")
            print("  4. Try emergencyClickFix() in browser console")
        
        js_tests = [r for r in self.results if "javascript" in r["test"].lower()]
        js_failures = [r for r in js_tests if not r["passed"]]
        
        if js_failures:
            print("🔧 JAVASCRIPT ISSUES DETECTED:")
            print("  1. Check if JavaScript files are being served correctly")
            print("  2. Verify no syntax errors in JS files")
            print("  3. Check browser console for loading errors")
        
        print("\n" + "="*60)
        
        # Save report to file
        with open("test_report.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print("\nDetailed report saved to: test_report.json")
    
    def run_all_tests(self):
        """Run all tests"""
        print("Starting Incentive App Tests...")
        print("="*60)
        
        # Check if server is running first
        if not self.test_server_running():
            print("\n⚠️  Server is not running! Please start the app first.")
            return
        
        # Run all tests
        self.test_api_endpoints()
        self.test_page_elements()
        self.test_javascript_files()
        self.test_css_files()
        self.test_quick_adjust_selenium()  # Will skip if Selenium not available
        
        # Generate report
        self.generate_report()


if __name__ == "__main__":
    import sys
    
    # Check if custom URL provided
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:7411"
    
    tester = IncentiveAppTester(base_url)
    tester.run_all_tests()