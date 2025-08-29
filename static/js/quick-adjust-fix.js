/**
 * Quick Adjust Click Fix
 * Fixes the critical issue where rule clicks don't trigger the modal
 */

(function() {
    'use strict';
    
    console.log('🔧 Quick Adjust Fix: Initializing...');
    
    // Debug function to check modal and elements
    function debugQuickAdjust() {
        const modal = document.getElementById('quickAdjustModal');
        const links = document.querySelectorAll('.quick-adjust-link');
        const form = document.getElementById('adjustPointsForm');
        
        console.log('Debug Info:');
        console.log('- Modal found:', !!modal);
        console.log('- Quick adjust links found:', links.length);
        console.log('- Form found:', !!form);
        
        if (modal) {
            console.log('- Modal parent:', modal.parentNode?.tagName);
            console.log('- Modal display:', window.getComputedStyle(modal).display);
            console.log('- Modal z-index:', window.getComputedStyle(modal).zIndex);
        }
        
        links.forEach((link, index) => {
            const computed = window.getComputedStyle(link);
            console.log(`Link ${index + 1}:`, {
                text: link.textContent.trim(),
                points: link.dataset.points,
                reason: link.dataset.reason,
                pointerEvents: computed.pointerEvents,
                cursor: computed.cursor,
                zIndex: computed.zIndex
            });
        });
        
        return { modal, links, form };
    }
    
    // Enhanced click handler that provides better feedback
    function enhancedQuickAdjustHandler(e) {
        e.preventDefault();
        e.stopPropagation();
        
        console.log('🎯 Quick Adjust Click detected!');
        
        const element = e.currentTarget;
        const points = element.getAttribute('data-points') || '';
        const reason = element.getAttribute('data-reason') || 'Other';
        
        console.log('Click data:', { points, reason });
        
        // Check if we're on the main page
        if (window.location.pathname !== '/') {
            console.log('Not on main page, redirecting...');
            sessionStorage.setItem('quickAdjustData', JSON.stringify({ points, reason }));
            window.location.href = '/';
            return;
        }
        
        // Find the modal
        const modal = document.getElementById('quickAdjustModal');
        if (!modal) {
            console.error('❌ Modal not found!');
            alert('Error: Quick Adjust feature is not available. Please refresh the page.');
            return;
        }
        
        // Check if user is admin
        const isAdmin = document.body.dataset.isAdmin === 'true' || 
                       document.querySelector('a[href*="admin_logout"]') !== null;
        
        console.log('Is admin:', isAdmin);
        
        // If not admin, show informative message
        if (!isAdmin) {
            // Show the modal anyway - it has username/password fields for non-admins
            console.log('Non-admin user - modal will show authentication fields');
        }
        
        // Ensure modal is in the correct place
        if (modal.parentNode !== document.body) {
            console.log('Moving modal to body');
            document.body.appendChild(modal);
        }
        
        // Try to show modal using Bootstrap
        try {
            if (typeof bootstrap !== 'undefined') {
                // Clear any existing modal instances
                const existingInstance = bootstrap.Modal.getInstance(modal);
                if (existingInstance) {
                    existingInstance.dispose();
                }
                
                // Create new modal instance
                const bsModal = new bootstrap.Modal(modal, {
                    backdrop: 'static',
                    keyboard: false,
                    focus: true
                });
                
                // Set form values before showing
                setTimeout(() => {
                    const pointsInput = modal.querySelector('#quick_adjust_points');
                    const reasonSelect = modal.querySelector('#quick_adjust_reason');
                    
                    if (pointsInput) {
                        pointsInput.value = points;
                        console.log('Set points to:', points);
                    }
                    
                    if (reasonSelect) {
                        // Try to find matching option
                        const options = Array.from(reasonSelect.options);
                        const matchingOption = options.find(opt => 
                            opt.text.toLowerCase().includes(reason.toLowerCase()) ||
                            opt.value.toLowerCase().includes(reason.toLowerCase())
                        );
                        
                        if (matchingOption) {
                            reasonSelect.value = matchingOption.value;
                            console.log('Set reason to:', matchingOption.value);
                        } else {
                            reasonSelect.value = 'Other';
                            console.log('Reason not found, defaulted to Other');
                        }
                    }
                    
                    // Focus first input
                    const firstInput = modal.querySelector('input:not([type="hidden"]):not([disabled]), select:not([disabled])');
                    if (firstInput) {
                        firstInput.focus();
                    }
                }, 100);
                
                // Show the modal
                bsModal.show();
                console.log('✅ Modal shown successfully');
                
                // Add visual feedback
                element.style.backgroundColor = 'rgba(0, 255, 0, 0.1)';
                setTimeout(() => {
                    element.style.backgroundColor = '';
                }, 500);
                
            } else {
                throw new Error('Bootstrap not available');
            }
        } catch (error) {
            console.error('Error showing modal:', error);
            
            // Fallback: Try to show modal without Bootstrap
            modal.style.display = 'block';
            modal.classList.add('show');
            modal.setAttribute('aria-modal', 'true');
            modal.setAttribute('role', 'dialog');
            
            // Create backdrop manually
            const backdrop = document.createElement('div');
            backdrop.className = 'modal-backdrop fade show';
            document.body.appendChild(backdrop);
            
            console.log('Showed modal using fallback method');
        }
    }
    
    // Function to attach event listeners
    function attachEventListeners() {
        const links = document.querySelectorAll('.quick-adjust-link');
        let attached = 0;
        
        links.forEach(link => {
            // Remove any existing listeners first
            link.removeEventListener('click', enhancedQuickAdjustHandler);
            
            // Add new listener
            link.addEventListener('click', enhancedQuickAdjustHandler);
            
            // Add visual indicator that it's clickable
            link.style.cursor = 'pointer';
            link.title = 'Click to quickly adjust points';
            
            // Add hover effect
            link.addEventListener('mouseenter', function() {
                this.style.transform = 'scale(1.02)';
                this.style.boxShadow = '0 4px 8px rgba(255, 215, 0, 0.3)';
            });
            
            link.addEventListener('mouseleave', function() {
                this.style.transform = '';
                this.style.boxShadow = '';
            });
            
            attached++;
        });
        
        console.log(`✅ Attached listeners to ${attached} quick-adjust links`);
        return attached;
    }
    
    // Monitor for dynamic content changes
    function setupMutationObserver() {
        const observer = new MutationObserver((mutations) => {
            let shouldReattach = false;
            
            mutations.forEach(mutation => {
                if (mutation.addedNodes.length > 0) {
                    mutation.addedNodes.forEach(node => {
                        if (node.nodeType === 1) {
                            if (node.classList?.contains('quick-adjust-link') ||
                                node.querySelector?.('.quick-adjust-link')) {
                                shouldReattach = true;
                            }
                        }
                    });
                }
            });
            
            if (shouldReattach) {
                setTimeout(attachEventListeners, 100);
            }
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('🔍 Mutation observer active for quick-adjust links');
    }
    
    // Initialize when DOM is ready
    function initialize() {
        console.log('🚀 Quick Adjust Fix: Starting initialization');
        
        // Debug current state
        const debugInfo = debugQuickAdjust();
        
        // Attach event listeners
        const attached = attachEventListeners();
        
        if (attached === 0) {
            console.warn('⚠️ No quick-adjust links found! Will retry...');
            // Retry after a delay
            setTimeout(() => {
                attachEventListeners();
            }, 1000);
        }
        
        // Setup observer for future changes
        setupMutationObserver();
        
        // Add debug command to window
        window.debugQuickAdjust = debugQuickAdjust;
        window.fixQuickAdjust = attachEventListeners;
        
        console.log('✅ Quick Adjust Fix initialized!');
        console.log('💡 Run debugQuickAdjust() to see current state');
        console.log('💡 Run fixQuickAdjust() to reattach listeners');
    }
    
    // Check if DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        // DOM is already loaded
        initialize();
    }
    
    // Also run after a delay to catch any late-loading content
    setTimeout(initialize, 2000);
    
})();