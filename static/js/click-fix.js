/**
 * Click Fix JavaScript - Emergency fix for button click blocking issues
 * This script ensures all interactive elements are clickable
 */

(function() {
    'use strict';
    
    console.log('🔧 Click Fix: Initializing click issue fixes...');
    
    // Fix 1: Remove all click prevention from buttons
    function fixButtonClicks() {
        const buttons = document.querySelectorAll('button, .btn, input[type="submit"], input[type="button"]');
        let fixedCount = 0;
        
        buttons.forEach(btn => {
            // Remove any dataset.clicked that might be blocking
            if (btn.dataset.clicked) {
                delete btn.dataset.clicked;
                fixedCount++;
            }
            
            // Ensure button is not disabled unless it should be
            if (btn.disabled && !btn.hasAttribute('data-intentionally-disabled')) {
                btn.disabled = false;
                fixedCount++;
            }
            
            // Ensure pointer-events are enabled
            const style = window.getComputedStyle(btn);
            if (style.pointerEvents === 'none') {
                btn.style.pointerEvents = 'auto';
                fixedCount++;
            }
        });
        
        if (fixedCount > 0) {
            console.log(`🔧 Click Fix: Fixed ${fixedCount} button issues`);
        }
    }
    
    // Fix 2: Ensure vegas-wrapper doesn't block clicks
    function fixVegasWrapper() {
        const wrappers = document.querySelectorAll('.vegas-wrapper');
        wrappers.forEach(wrapper => {
            wrapper.style.pointerEvents = 'auto';
            // Ensure all children are also clickable
            const children = wrapper.querySelectorAll('button, .btn, a, input');
            children.forEach(child => {
                child.style.pointerEvents = 'auto';
                child.style.position = 'relative';
                child.style.zIndex = '10';
            });
        });
        if (wrappers.length > 0) {
            console.log(`🔧 Click Fix: Fixed ${wrappers.length} vegas-wrapper elements`);
        }
    }
    
    // Fix 3: Ensure particle canvas stays in background
    function fixParticleCanvas() {
        const canvas = document.getElementById('particleCanvas');
        if (canvas) {
            canvas.style.pointerEvents = 'none';
            canvas.style.zIndex = '-1';
            console.log('🔧 Click Fix: Fixed particle canvas positioning');
        }
    }
    
    // Fix 4: Monitor and fix new buttons added dynamically
    function setupMutationObserver() {
        const observer = new MutationObserver((mutations) => {
            let hasNewButtons = false;
            mutations.forEach((mutation) => {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === 1) { // Element node
                            if (node.matches && (node.matches('button, .btn') || 
                                node.querySelector && node.querySelector('button, .btn'))) {
                                hasNewButtons = true;
                            }
                        }
                    });
                }
            });
            
            if (hasNewButtons) {
                setTimeout(fixButtonClicks, 100);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('🔧 Click Fix: Mutation observer active');
    }
    
    // Fix 5: Override problematic event listeners
    function fixEventListeners() {
        // Store original addEventListener
        const originalAddEventListener = EventTarget.prototype.addEventListener;
        
        // Override addEventListener to detect and fix problematic click handlers
        EventTarget.prototype.addEventListener = function(type, listener, options) {
            if (type === 'click' && (this.tagName === 'BUTTON' || this.classList && this.classList.contains('btn'))) {
                // Wrap the listener to ensure it doesn't block clicks
                const wrappedListener = function(e) {
                    // Remove any click prevention for non-submit buttons
                    if (this.type !== 'submit' && this.dataset.clicked === 'true') {
                        delete this.dataset.clicked;
                    }
                    // Call original listener
                    return listener.call(this, e);
                };
                return originalAddEventListener.call(this, type, wrappedListener, options);
            }
            return originalAddEventListener.call(this, type, listener, options);
        };
    }
    
    // Fix 6: Add debug mode
    function enableDebugMode() {
        if (window.location.hash === '#debug-clicks') {
            document.body.classList.add('debug-clicks');
            console.log('🔧 Click Fix: Debug mode enabled - problematic elements highlighted in red');
            
            // Log all elements with pointer-events: none
            const blocked = document.querySelectorAll('*');
            blocked.forEach(el => {
                const style = window.getComputedStyle(el);
                if (style.pointerEvents === 'none' && el.querySelector && el.querySelector('button, .btn, a')) {
                    console.warn('🔧 Click Fix: Element blocking clicks:', el);
                }
            });
        }
    }
    
    // Fix 7: Emergency fix function that can be called manually
    window.emergencyClickFix = function() {
        console.log('🚨 Emergency Click Fix activated!');
        
        // Remove all pointer-events: none except for particle canvas
        const allElements = document.querySelectorAll('*');
        allElements.forEach(el => {
            if (el.id !== 'particleCanvas' && !el.classList.contains('particle-background')) {
                const style = window.getComputedStyle(el);
                if (style.pointerEvents === 'none') {
                    el.style.pointerEvents = 'auto';
                }
            }
        });
        
        // Fix all buttons
        fixButtonClicks();
        fixVegasWrapper();
        
        // Add click-fix-active class for CSS overrides
        document.body.classList.add('click-fix-active');
        
        console.log('✅ Emergency Click Fix complete! All buttons should now be clickable.');
    };
    
    // Initialize fixes when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initializeFixes);
    } else {
        initializeFixes();
    }
    
    function initializeFixes() {
        console.log('🔧 Click Fix: Applying fixes...');
        
        // Apply all fixes
        fixButtonClicks();
        fixVegasWrapper();
        fixParticleCanvas();
        setupMutationObserver();
        // Don't override event listeners by default as it might cause issues
        // fixEventListeners();
        enableDebugMode();
        
        // Re-run fixes after a short delay to catch any late-loading elements
        setTimeout(() => {
            fixButtonClicks();
            fixVegasWrapper();
        }, 1000);
        
        // Add global click handler to detect blocked clicks
        document.addEventListener('click', function(e) {
            if (e.target.matches('button, .btn, input[type="submit"]')) {
                if (e.defaultPrevented) {
                    console.warn('🔧 Click Fix: Click was prevented on:', e.target);
                }
            }
        }, true);
        
        console.log('✅ Click Fix: All fixes applied successfully!');
        console.log('💡 Tip: Add #debug-clicks to URL to enable debug mode');
        console.log('💡 Tip: Run emergencyClickFix() in console if clicks still don\'t work');
    }
})();