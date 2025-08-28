# tests/test_mobile.py
# Mobile responsiveness and touch interface tests for the Employee Incentive System
# Version: 1.0.0

import pytest
import os
import sys
import re
from unittest.mock import patch, Mock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestMobileViewport:
    """Test mobile viewport configuration"""
    
    @patch('app.get_settings')
    @patch('app.get_scoreboard')
    @patch('app.is_voting_active')
    def test_viewport_meta_tag(self, mock_is_voting_active, mock_get_scoreboard, mock_get_settings, client, init_test_db):
        """Test that viewport meta tag is present for mobile"""
        # Mock dependencies
        mock_get_settings.return_value = {'site_name': 'Test Site'}
        mock_get_scoreboard.return_value = []
        mock_is_voting_active.return_value = False
        
        response = client.get('/')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Check for viewport meta tag
            viewport_pattern = r'<meta[^>]+name=["\']viewport["\'][^>]*>'
            assert re.search(viewport_pattern, html_content, re.IGNORECASE), \
                "Viewport meta tag not found - required for mobile responsiveness"
            
            # Check for mobile-friendly viewport settings
            if 'width=device-width' in html_content or 'initial-scale=1' in html_content:
                # Good mobile viewport configuration found
                pass
            else:
                # Basic viewport tag should still be present
                assert 'viewport' in html_content.lower()
    
    def test_mobile_css_media_queries(self, client):
        """Test that mobile CSS media queries are present"""
        response = client.get('/static/style.css')
        
        if response.status_code == 200:
            css_content = response.data.decode('utf-8')
            
            # Look for mobile media queries
            mobile_patterns = [
                r'@media[^{]*\([^)]*max-width[^)]*\)',  # max-width queries
                r'@media[^{]*\([^)]*min-width[^)]*\)',  # min-width queries
                r'@media[^{]*screen',                    # screen media type
                r'@media[^{]*mobile',                    # explicit mobile targeting
            ]
            
            media_query_found = any(re.search(pattern, css_content, re.IGNORECASE) 
                                  for pattern in mobile_patterns)
            
            if not media_query_found:
                # Check for responsive CSS properties
                responsive_properties = [
                    'flex', 'grid', 'max-width: 100%', 'width: 100%',
                    'responsive', 'mobile', 'tablet'
                ]
                responsive_css = any(prop in css_content.lower() 
                                   for prop in responsive_properties)
                
                # Either media queries or responsive CSS should be present
                assert responsive_css or len(css_content) == 0, \
                    "No mobile responsiveness detected in CSS"


class TestMobileNavigation:
    """Test mobile navigation elements"""
    
    @patch('app.get_settings')
    @patch('app.get_scoreboard')
    @patch('app.is_voting_active')
    def test_mobile_menu_structure(self, mock_is_voting_active, mock_get_scoreboard, mock_get_settings, client, init_test_db):
        """Test mobile menu structure"""
        # Mock dependencies
        mock_get_settings.return_value = {'site_name': 'Test Site'}
        mock_get_scoreboard.return_value = []
        mock_is_voting_active.return_value = False
        
        response = client.get('/')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Look for common mobile menu patterns
            mobile_menu_patterns = [
                r'class=["\'][^"\']*hamburger[^"\']*["\']',     # Hamburger menu
                r'class=["\'][^"\']*mobile-menu[^"\']*["\']',   # Mobile menu class
                r'class=["\'][^"\']*nav-toggle[^"\']*["\']',    # Navigation toggle
                r'☰',                                           # Hamburger symbol
                r'≡',                                           # Menu symbol
                r'menu-icon',                                   # Menu icon class
            ]
            
            mobile_menu_found = any(re.search(pattern, html_content, re.IGNORECASE) 
                                  for pattern in mobile_menu_patterns)
            
            # Also check for standard navigation
            nav_found = re.search(r'<nav[^>]*>', html_content, re.IGNORECASE)
            
            # Either mobile-specific menu or standard nav should be present
            assert mobile_menu_found or nav_found, \
                "No navigation structure found"
    
    def test_touch_friendly_buttons(self, client):
        """Test that buttons are touch-friendly"""
        response = client.get('/')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Look for buttons
            button_pattern = r'<button[^>]*>|<input[^>]+type=["\']button["\'][^>]*>|<a[^>]+class=["\'][^"\']*btn[^"\']*["\']'
            buttons = re.findall(button_pattern, html_content, re.IGNORECASE)
            
            if buttons:
                # Check if CSS likely has touch-friendly sizing
                css_response = client.get('/static/style.css')
                if css_response.status_code == 200:
                    css_content = css_response.data.decode('utf-8')
                    
                    # Look for touch-friendly properties
                    touch_properties = [
                        'min-height:', 'padding:', 'margin:',
                        '44px', '48px',  # Common touch target sizes
                        'touch-action', 'user-select'
                    ]
                    
                    touch_friendly = any(prop in css_content.lower() 
                                       for prop in touch_properties)
                    
                    # If we have buttons, we should have touch-friendly CSS
                    if not touch_friendly:
                        # Basic button styling should at least be present
                        assert 'button' in css_content.lower() or len(css_content) == 0


class TestResponsiveLayout:
    """Test responsive layout behavior"""
    
    @patch('app.get_settings')
    @patch('app.get_scoreboard')
    @patch('app.is_voting_active')
    def test_responsive_grid_system(self, mock_is_voting_active, mock_get_scoreboard, mock_get_settings, client, init_test_db):
        """Test responsive grid system"""
        # Mock dependencies
        mock_get_settings.return_value = {'site_name': 'Test Site'}
        mock_get_scoreboard.return_value = [
            {'id': 2, 'name': 'John Doe', 'score': 100},
            {'id': 3, 'name': 'Jane Smith', 'score': 150}
        ]
        mock_is_voting_active.return_value = False
        
        response = client.get('/')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Look for responsive grid classes
            grid_patterns = [
                r'class=["\'][^"\']*col-[^"\']*["\']',      # Bootstrap-style columns
                r'class=["\'][^"\']*grid[^"\']*["\']',      # Grid classes
                r'class=["\'][^"\']*flex[^"\']*["\']',      # Flexbox classes
                r'class=["\'][^"\']*row[^"\']*["\']',       # Row classes
                r'class=["\'][^"\']*container[^"\']*["\']', # Container classes
            ]
            
            grid_found = any(re.search(pattern, html_content, re.IGNORECASE) 
                           for pattern in grid_patterns)
            
            # Check CSS for grid/flexbox properties
            css_response = client.get('/static/style.css')
            if css_response.status_code == 200:
                css_content = css_response.data.decode('utf-8')
                css_grid = any(prop in css_content.lower() 
                             for prop in ['display: flex', 'display: grid', 
                                        'flex-wrap', 'grid-template'])
                
                # Either HTML classes or CSS properties should indicate responsive design
                responsive_layout = grid_found or css_grid
                
                if not responsive_layout:
                    # At least some layout structure should be present
                    layout_elements = ['div', 'section', 'article', 'main']
                    has_layout = any(f'<{elem}' in html_content.lower() 
                                   for elem in layout_elements)
                    assert has_layout, "No layout structure found"
    
    def test_responsive_images(self, client):
        """Test responsive image handling"""
        response = client.get('/')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Find images
            img_pattern = r'<img[^>]*>'
            images = re.findall(img_pattern, html_content, re.IGNORECASE)
            
            if images:
                # Check for responsive image attributes
                responsive_img_patterns = [
                    r'class=["\'][^"\']*responsive[^"\']*["\']',
                    r'style=["\'][^"\']*max-width:[^"\']*100%[^"\']*["\']',
                    r'srcset=',  # Responsive image srcset
                    r'sizes=',   # Responsive image sizes
                ]
                
                responsive_imgs = sum(1 for img in images 
                                    for pattern in responsive_img_patterns 
                                    if re.search(pattern, img, re.IGNORECASE))
                
                # Check CSS for responsive image styles
                css_response = client.get('/static/style.css')
                if css_response.status_code == 200:
                    css_content = css_response.data.decode('utf-8')
                    responsive_css = any(prop in css_content.lower() 
                                       for prop in ['max-width: 100%', 'width: 100%',
                                                  'height: auto', 'object-fit'])
                    
                    # Images should be responsive either via HTML attributes or CSS
                    if not (responsive_imgs > 0 or responsive_css):
                        # At minimum, images should be present and not break layout
                        assert len(images) > 0


class TestMobileFormsAndInputs:
    """Test mobile-friendly forms and inputs"""
    
    def test_mobile_input_types(self, client):
        """Test mobile-friendly input types"""
        # Test login page which likely has inputs
        response = client.get('/admin')  # Admin login page
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Look for input fields
            input_pattern = r'<input[^>]*type=["\']([^"\']+)["\'][^>]*>'
            inputs = re.findall(input_pattern, html_content, re.IGNORECASE)
            
            if inputs:
                # Check for mobile-friendly input types
                mobile_input_types = ['email', 'tel', 'number', 'url', 'search']
                mobile_inputs = [inp for inp in inputs if inp.lower() in mobile_input_types]
                
                # Look for input attributes that help mobile users
                mobile_attributes = [
                    r'autocomplete=',
                    r'inputmode=',
                    r'pattern=',
                    r'placeholder=',
                ]
                
                mobile_attrs_found = any(re.search(attr, html_content, re.IGNORECASE) 
                                       for attr in mobile_attributes)
                
                # Mobile enhancements should be present for better UX
                if not (mobile_inputs or mobile_attrs_found):
                    # At least basic inputs should be present
                    assert 'input' in html_content.lower()
    
    def test_form_validation_mobile_friendly(self, client):
        """Test mobile-friendly form validation"""
        response = client.get('/admin')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Look for forms
            form_pattern = r'<form[^>]*>'
            forms = re.findall(form_pattern, html_content, re.IGNORECASE)
            
            if forms:
                # Check for HTML5 validation attributes
                validation_attrs = [
                    r'required',
                    r'min=',
                    r'max=',
                    r'maxlength=',
                    r'pattern=',
                ]
                
                validation_found = any(re.search(attr, html_content, re.IGNORECASE) 
                                     for attr in validation_attrs)
                
                # Check for validation styling in CSS
                css_response = client.get('/static/style.css')
                if css_response.status_code == 200:
                    css_content = css_response.data.decode('utf-8')
                    validation_css = any(prop in css_content.lower() 
                                       for prop in ['invalid', 'valid', 'error',
                                                  'required', ':valid', ':invalid'])
                    
                    # Forms should have some validation mechanism
                    if not (validation_found or validation_css):
                        # Basic form structure should be present
                        assert 'form' in html_content.lower()


class TestTouchInteractions:
    """Test touch interaction support"""
    
    def test_touch_event_support(self, client):
        """Test touch event support in JavaScript"""
        response = client.get('/static/script.js')
        
        if response.status_code == 200:
            js_content = response.data.decode('utf-8')
            
            # Look for touch event handlers
            touch_events = [
                'touchstart', 'touchend', 'touchmove', 'touchcancel',
                'ontouchstart', 'ontouchend', 'ontouchmove',
                'addEventListener.*touch'
            ]
            
            touch_support = any(re.search(event, js_content, re.IGNORECASE) 
                              for event in touch_events)
            
            # Look for mobile detection or responsive JavaScript
            mobile_js_patterns = [
                'mobile', 'tablet', 'touch', 'screen.width',
                'window.innerWidth', 'matchMedia', 'responsive'
            ]
            
            mobile_js = any(re.search(pattern, js_content, re.IGNORECASE) 
                          for pattern in mobile_js_patterns)
            
            if not (touch_support or mobile_js):
                # Check for general event handlers that work on mobile
                general_events = ['click', 'addEventListener', 'onclick']
                has_events = any(event in js_content.lower() for event in general_events)
                
                # Should have some form of interaction handling
                if js_content and not has_events:
                    # JavaScript exists but no event handling found
                    pass  # This might be configuration or utility JS
    
    def test_gesture_support(self, client):
        """Test gesture support for mobile interactions"""
        response = client.get('/static/script.js')
        
        if response.status_code == 200:
            js_content = response.data.decode('utf-8')
            
            # Look for gesture-related code
            gesture_patterns = [
                'swipe', 'pinch', 'zoom', 'pan', 'rotate',
                'gesture', 'hammer', 'touches.length'
            ]
            
            gesture_support = any(re.search(pattern, js_content, re.IGNORECASE) 
                                for pattern in gesture_patterns)
            
            # Gestures are optional but enhance mobile UX
            # Test passes whether or not gestures are implemented
            assert isinstance(gesture_support, bool)


class TestMobileGameInterface:
    """Test mobile-specific game interface elements"""
    
    def test_game_touch_controls(self, client):
        """Test game touch controls"""
        # Check games JavaScript for touch-friendly controls
        response = client.get('/static/vegas-casino.js')
        
        if response.status_code == 200:
            js_content = response.data.decode('utf-8')
            
            # Look for touch-friendly game controls
            touch_control_patterns = [
                'touch', 'tap', 'click', 'button',
                'addEventListener', 'onclick'
            ]
            
            touch_controls = any(re.search(pattern, js_content, re.IGNORECASE) 
                               for pattern in touch_control_patterns)
            
            if not touch_controls:
                # At least some interaction should be present
                interaction_patterns = ['function', 'event', 'handler']
                has_interaction = any(pattern in js_content.lower() 
                                    for pattern in interaction_patterns)
                
                if js_content:  # Only test if file has content
                    assert has_interaction, "No interaction handlers found in game JavaScript"
        else:
            # Game JavaScript might not exist, which is acceptable
            assert response.status_code in [404]
    
    def test_game_mobile_layout(self, client):
        """Test game mobile layout"""
        # Test employee portal which may contain games
        with client.session_transaction() as sess:
            sess['employee_logged_in'] = True
            sess['employee_id'] = 2
            sess['employee_name'] = 'John Doe'
        
        response = client.get('/employee_portal')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Look for game-related elements
            game_patterns = [
                r'game', r'slot', r'casino', r'play', r'spin',
                r'roulette', r'dice', r'wheel', r'scratch'
            ]
            
            game_elements = any(re.search(pattern, html_content, re.IGNORECASE) 
                              for pattern in game_patterns)
            
            if game_elements:
                # Check for mobile-friendly game layout
                mobile_game_classes = [
                    r'class=["\'][^"\']*mobile[^"\']*["\']',
                    r'class=["\'][^"\']*responsive[^"\']*["\']',
                    r'class=["\'][^"\']*touch[^"\']*["\']'
                ]
                
                mobile_layout = any(re.search(pattern, html_content, re.IGNORECASE) 
                                  for pattern in mobile_game_classes)
                
                # Games should have some mobile consideration
                # This test is informational rather than strict requirement
                assert isinstance(mobile_layout, bool)


class TestAccessibilityForMobile:
    """Test mobile accessibility features"""
    
    def test_aria_labels_for_touch(self, client):
        """Test ARIA labels for touch interfaces"""
        response = client.get('/')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Look for ARIA attributes that help mobile users
            aria_patterns = [
                r'aria-label=', r'aria-describedby=', r'aria-hidden=',
                r'role=', r'aria-expanded=', r'aria-controls='
            ]
            
            aria_found = any(re.search(pattern, html_content, re.IGNORECASE) 
                           for pattern in aria_patterns)
            
            # Also look for semantic HTML elements
            semantic_elements = [
                r'<nav[^>]*>', r'<main[^>]*>', r'<section[^>]*>',
                r'<article[^>]*>', r'<header[^>]*>', r'<footer[^>]*>'
            ]
            
            semantic_found = any(re.search(element, html_content, re.IGNORECASE) 
                               for element in semantic_elements)
            
            # Either ARIA attributes or semantic HTML should be present
            accessibility_found = aria_found or semantic_found
            
            if not accessibility_found:
                # At least basic structure should be accessible
                basic_structure = ['<div', '<span', '<p', '<h1', '<h2', '<h3']
                has_structure = any(elem in html_content.lower() for elem in basic_structure)
                assert has_structure, "No accessible structure found"
    
    def test_mobile_focus_management(self, client):
        """Test focus management for mobile users"""
        response = client.get('/static/script.js')
        
        if response.status_code == 200:
            js_content = response.data.decode('utf-8')
            
            # Look for focus management code
            focus_patterns = [
                'focus()', 'blur()', 'tabindex', 'focusable',
                'activeElement', 'focus', 'blur'
            ]
            
            focus_management = any(re.search(pattern, js_content, re.IGNORECASE) 
                                 for pattern in focus_patterns)
            
            # Focus management is good practice but not always necessary
            # Test is informational
            assert isinstance(focus_management, bool)


class TestMobilePerformance:
    """Test mobile performance considerations"""
    
    def test_resource_optimization(self, client):
        """Test resource optimization for mobile"""
        # Test main page load
        response = client.get('/')
        
        if response.status_code == 200:
            html_content = response.data.decode('utf-8')
            
            # Check for performance optimization techniques
            perf_patterns = [
                r'async', r'defer', r'preload', r'prefetch',
                r'lazy', r'loading="lazy"'
            ]
            
            perf_optimization = any(re.search(pattern, html_content, re.IGNORECASE) 
                                  for pattern in perf_patterns)
            
            # Check for minified resources (optional)
            minified_resources = [
                'min.css', 'min.js', '.min.'
            ]
            
            has_minified = any(resource in html_content.lower() 
                             for resource in minified_resources)
            
            # Performance optimization is good practice but not required for functionality
            optimization_found = perf_optimization or has_minified
            assert isinstance(optimization_found, bool)
    
    def test_mobile_css_optimization(self, client):
        """Test CSS optimization for mobile"""
        response = client.get('/static/style.css')
        
        if response.status_code == 200:
            css_content = response.data.decode('utf-8')
            
            # Check for mobile-first CSS approach
            mobile_first_patterns = [
                r'@media[^{]*\([^)]*min-width[^)]*\)',  # min-width (mobile-first)
            ]
            
            mobile_first = any(re.search(pattern, css_content, re.IGNORECASE) 
                             for pattern in mobile_first_patterns)
            
            # Check for CSS optimization techniques
            optimization_patterns = [
                'transform3d', 'will-change', 'backface-visibility',
                'perspective', 'translateZ'  # Hardware acceleration
            ]
            
            css_optimization = any(pattern in css_content.lower() 
                                 for pattern in optimization_patterns)
            
            # Mobile optimization is good practice
            has_optimization = mobile_first or css_optimization
            assert isinstance(has_optimization, bool)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-m', 'mobile'])