#!/usr/bin/env python3
"""
Comprehensive Settings Page Testing Script
Tests all aspects of the newly overhauled settings page
"""

import os
import sys
import json
import re
from pathlib import Path
from typing import Dict, List, Tuple

# Add colors for output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")

def print_section(text):
    print(f"\n{Colors.OKCYAN}{Colors.BOLD}[{text}]{Colors.ENDC}")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

class SettingsPageTester:
    def __init__(self):
        self.base_path = Path("/home/tim/incentDev")
        self.template_path = self.base_path / "templates" / "settings.html"
        self.css_path = self.base_path / "static" / "css" / "settings-enhanced.css"
        self.errors = []
        self.warnings = []
        self.successes = []
        
    def test_template_syntax(self):
        """Test Jinja2 template syntax and structure"""
        print_section("TEMPLATE SYNTAX VALIDATION")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for basic template structure
        if "{% extends" in content:
            print_success("Template properly extends base.html")
        else:
            self.errors.append("Template doesn't extend base template")
            
        # Check for block definitions
        blocks = re.findall(r'{% block (\w+) %}', content)
        required_blocks = ['content', 'extra_head']
        for block in required_blocks:
            if block in blocks:
                print_success(f"Block '{block}' is defined")
            else:
                self.errors.append(f"Required block '{block}' is missing")
                
        # Check for CSRF tokens
        csrf_tokens = re.findall(r'csrf_token|render_csrf_token', content)
        if csrf_tokens:
            print_success(f"Found {len(csrf_tokens)} CSRF token references")
        else:
            self.errors.append("No CSRF tokens found - forms may not be secure")
            
        # Check for form definitions
        forms = re.findall(r'<form[^>]*>', content)
        print_info(f"Found {len(forms)} forms in template")
        
        # Check for proper form methods
        post_forms = re.findall(r'<form[^>]*method="POST"[^>]*>', content)
        if post_forms:
            print_success(f"Found {len(post_forms)} POST forms")
        else:
            self.warnings.append("No POST forms found")
            
    def test_tab_structure(self):
        """Test tab navigation structure"""
        print_section("TAB NAVIGATION STRUCTURE")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for tab navigation
        tabs = re.findall(r'data-bs-target="#([^"]+)"', content)
        tab_panes = re.findall(r'<div[^>]*id="([^"]+)"[^>]*role="tabpanel"', content)
        
        print_info(f"Found {len(tabs)} tab buttons")
        print_info(f"Found {len(tab_panes)} tab panes")
        
        expected_tabs = ['voting-section', 'games-section', 'visual-section', 'system-section']
        for tab in expected_tabs:
            if tab in tabs:
                print_success(f"Tab '{tab}' is defined")
                if tab in tab_panes:
                    print_success(f"Tab pane for '{tab}' exists")
                else:
                    self.errors.append(f"Tab pane for '{tab}' is missing")
            else:
                self.errors.append(f"Tab button for '{tab}' is missing")
                
    def test_form_validation(self):
        """Test form fields and validation attributes"""
        print_section("FORM VALIDATION")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for required fields
        required_fields = re.findall(r'required=True|required', content)
        print_info(f"Found {len(required_fields)} required fields")
        
        # Check for input types
        input_types = re.findall(r'type="(\w+)"', content)
        type_counts = {}
        for t in input_types:
            type_counts[t] = type_counts.get(t, 0) + 1
            
        print_info("Input type distribution:")
        for t, count in type_counts.items():
            print(f"  - {t}: {count}")
            
        # Check for form validation attributes
        validation_attrs = ['min=', 'max=', 'step=', 'pattern=']
        for attr in validation_attrs:
            count = content.count(attr)
            if count > 0:
                print_success(f"Found {count} instances of '{attr}' validation")
                
    def test_javascript_functionality(self):
        """Test JavaScript code in template"""
        print_section("JAVASCRIPT FUNCTIONALITY")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for script tags
        scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        if scripts:
            print_success(f"Found {len(scripts)} script blocks")
            
            # Check for key functions
            if 'populateSettingValue' in content:
                print_success("populateSettingValue function exists")
            else:
                self.warnings.append("populateSettingValue function not found")
                
            if 'addEventListener' in content:
                print_success("Event listeners are being added")
            else:
                self.warnings.append("No event listeners found")
                
            # Check for JSON handling
            if 'JSON.parse' in content or 'JSON.stringify' in content:
                print_success("JSON handling is implemented")
            else:
                self.warnings.append("No JSON handling found")
        else:
            self.errors.append("No JavaScript code found in template")
            
    def test_css_integration(self):
        """Test CSS file and styling"""
        print_section("CSS STYLING")
        
        # Check if CSS file exists
        if self.css_path.exists():
            print_success("settings-enhanced.css file exists")
            
            with open(self.css_path, 'r') as f:
                css_content = f.read()
                
            # Check for key CSS classes
            key_classes = [
                '.settings-page',
                '.settings-navigation',
                '.settings-card',
                '.settings-content',
                '.threshold-section',
                '.tier-rates'
            ]
            
            for cls in key_classes:
                if cls in css_content:
                    print_success(f"CSS class '{cls}' is defined")
                else:
                    self.warnings.append(f"CSS class '{cls}' not found")
                    
            # Check for responsive design
            media_queries = re.findall(r'@media[^{]+', css_content)
            if media_queries:
                print_success(f"Found {len(media_queries)} media queries for responsive design")
                for query in media_queries:
                    print_info(f"  {query.strip()}")
            else:
                self.warnings.append("No media queries found - may not be responsive")
                
        else:
            self.errors.append("CSS file settings-enhanced.css not found")
            
    def test_new_features(self):
        """Test implementation of new features"""
        print_section("NEW FEATURES IMPLEMENTATION")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for dual game system
        if 'Dual Game System' in content:
            print_success("Dual Game System section exists")
            if 'Category A' in content and 'Category B' in content:
                print_success("Both Category A and B are implemented")
            else:
                self.errors.append("Missing Category A or B implementation")
        else:
            self.errors.append("Dual Game System not found")
            
        # Check for token exchange
        if 'Token Exchange' in content:
            print_success("Token Exchange System section exists")
            if 'exchange_rate' in content:
                print_success("Exchange rate configuration found")
            else:
                self.warnings.append("Exchange rate configuration not found")
        else:
            self.errors.append("Token Exchange System not found")
            
        # Check for Phaser.js configuration
        if 'Phaser' in content:
            print_success("Phaser.js configuration section exists")
            if 'physics_engine' in content:
                print_success("Physics engine configuration found")
            else:
                self.warnings.append("Physics engine configuration not found")
        else:
            self.errors.append("Phaser.js configuration not found")
            
        # Check for enhanced audio system
        if 'Enhanced Audio System' in content or 'Audio System' in content:
            print_success("Enhanced Audio System section exists")
            if 'master_volume' in content:
                print_success("Volume controls found")
            else:
                self.warnings.append("Volume controls not found")
        else:
            self.warnings.append("Enhanced Audio System section not found")
            
    def test_accessibility(self):
        """Test accessibility features"""
        print_section("ACCESSIBILITY")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for ARIA attributes
        aria_attrs = re.findall(r'aria-[a-z]+', content)
        if aria_attrs:
            print_success(f"Found {len(set(aria_attrs))} unique ARIA attributes")
        else:
            self.warnings.append("No ARIA attributes found")
            
        # Check for labels
        labels = re.findall(r'<label[^>]*for="([^"]+)"', content)
        inputs = re.findall(r'<input[^>]*id="([^"]+)"', content)
        selects = re.findall(r'<select[^>]*id="([^"]+)"', content)
        
        form_elements = set(inputs + selects)
        labeled_elements = set(labels)
        
        unlabeled = form_elements - labeled_elements
        if unlabeled:
            self.warnings.append(f"{len(unlabeled)} form elements without labels")
            for elem in list(unlabeled)[:5]:
                print_warning(f"  - {elem}")
        else:
            print_success("All form elements have labels")
            
        # Check for alt text on images/icons
        if '<img' in content:
            imgs_with_alt = re.findall(r'<img[^>]*alt="[^"]*"[^>]*>', content)
            imgs_total = re.findall(r'<img[^>]*>', content)
            if len(imgs_with_alt) == len(imgs_total):
                print_success("All images have alt text")
            else:
                self.warnings.append(f"{len(imgs_total) - len(imgs_with_alt)} images without alt text")
                
    def test_security(self):
        """Test security features"""
        print_section("SECURITY")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for CSRF protection
        csrf_count = content.count('csrf_token')
        form_count = content.count('<form')
        
        if csrf_count >= form_count:
            print_success(f"All {form_count} forms have CSRF protection")
        else:
            self.errors.append(f"Only {csrf_count} of {form_count} forms have CSRF tokens")
            
        # Check for password fields
        password_fields = re.findall(r'type="password"', content)
        if password_fields:
            print_info(f"Found {len(password_fields)} password fields")
            # Check if they have proper attributes
            for i, field in enumerate(password_fields):
                print_info(f"  - Password field {i+1}")
                
        # Check for dangerous operations
        if 'Master Reset' in content:
            if 'confirm(' in content:
                print_success("Master Reset has confirmation dialog")
            else:
                self.errors.append("Master Reset lacks confirmation dialog")
                
    def test_database_integration(self):
        """Test database field references"""
        print_section("DATABASE INTEGRATION")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for settings references
        settings_refs = re.findall(r'settings\.get\([\'"]([^\'"]+)[\'"]', content)
        if settings_refs:
            print_success(f"Found {len(settings_refs)} settings references")
            unique_settings = set(settings_refs)
            print_info(f"Unique settings keys: {len(unique_settings)}")
            
        # Check for form data references
        form_data_refs = re.findall(r'\.data', content)
        if form_data_refs:
            print_success(f"Found {len(form_data_refs)} form data references")
            
    def test_responsive_design(self):
        """Test responsive design implementation"""
        print_section("RESPONSIVE DESIGN")
        
        with open(self.template_path, 'r') as f:
            content = f.read()
            
        # Check for Bootstrap responsive classes
        responsive_classes = [
            'col-sm-', 'col-md-', 'col-lg-', 'col-xl-',
            'd-none', 'd-sm-', 'd-md-', 'd-lg-',
            'table-responsive'
        ]
        
        for cls in responsive_classes:
            count = content.count(cls)
            if count > 0:
                print_success(f"Found {count} instances of '{cls}' responsive class")
                
        # Check CSS for mobile breakpoints
        if self.css_path.exists():
            with open(self.css_path, 'r') as f:
                css_content = f.read()
                
            breakpoints = [
                ('576px', 'Mobile'),
                ('768px', 'Tablet'),
                ('1200px', 'Desktop')
            ]
            
            for breakpoint, device in breakpoints:
                if breakpoint in css_content:
                    print_success(f"{device} breakpoint ({breakpoint}) is defined")
                else:
                    self.warnings.append(f"{device} breakpoint ({breakpoint}) not found")
                    
    def generate_report(self):
        """Generate final test report"""
        print_header("TESTING SUMMARY REPORT")
        
        total_tests = len(self.successes) + len(self.warnings) + len(self.errors)
        
        print(f"\n{Colors.BOLD}Total Tests Run: {total_tests}{Colors.ENDC}")
        print(f"{Colors.OKGREEN}Passed: {len(self.successes)}{Colors.ENDC}")
        print(f"{Colors.WARNING}Warnings: {len(self.warnings)}{Colors.ENDC}")
        print(f"{Colors.FAIL}Errors: {len(self.errors)}{Colors.ENDC}")
        
        if self.errors:
            print(f"\n{Colors.FAIL}{Colors.BOLD}CRITICAL ERRORS FOUND:{Colors.ENDC}")
            for i, error in enumerate(self.errors, 1):
                print(f"{Colors.FAIL}{i}. {error}{Colors.ENDC}")
                
        if self.warnings:
            print(f"\n{Colors.WARNING}{Colors.BOLD}WARNINGS:{Colors.ENDC}")
            for i, warning in enumerate(self.warnings, 1):
                print(f"{Colors.WARNING}{i}. {warning}{Colors.ENDC}")
                
        if not self.errors:
            print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ Settings page passes all critical tests!{Colors.ENDC}")
        else:
            print(f"\n{Colors.FAIL}{Colors.BOLD}✗ Settings page has {len(self.errors)} critical issues that need fixing{Colors.ENDC}")
            
        # Recommendations
        print(f"\n{Colors.OKCYAN}{Colors.BOLD}RECOMMENDATIONS:{Colors.ENDC}")
        recommendations = []
        
        if len(self.errors) > 0:
            recommendations.append("Fix all critical errors before deployment")
        if len(self.warnings) > 5:
            recommendations.append("Address warnings to improve quality")
        if 'No media queries' in str(self.warnings):
            recommendations.append("Add responsive design for mobile devices")
        if 'No ARIA' in str(self.warnings):
            recommendations.append("Improve accessibility with ARIA attributes")
            
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                print(f"{i}. {rec}")
        else:
            print("Settings page is well-implemented and ready for use!")
            
    def run_all_tests(self):
        """Run all test suites"""
        print_header("SETTINGS PAGE COMPREHENSIVE TESTING")
        print(f"Testing: {self.template_path}")
        print(f"CSS: {self.css_path}")
        
        # Run all test methods
        test_methods = [
            self.test_template_syntax,
            self.test_tab_structure,
            self.test_form_validation,
            self.test_javascript_functionality,
            self.test_css_integration,
            self.test_new_features,
            self.test_accessibility,
            self.test_security,
            self.test_database_integration,
            self.test_responsive_design
        ]
        
        for test in test_methods:
            try:
                test()
            except Exception as e:
                self.errors.append(f"Test {test.__name__} failed: {str(e)}")
                print_error(f"Test {test.__name__} crashed: {str(e)}")
                
        # Generate final report
        self.generate_report()

if __name__ == "__main__":
    tester = SettingsPageTester()
    tester.run_all_tests()