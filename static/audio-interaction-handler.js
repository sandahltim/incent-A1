/**
 * Audio Interaction Handler
 * Manages user interaction requirements for browser autoplay policies
 * Ensures audio only plays after user interaction
 */

(function() {
    'use strict';
    
    // Track user interaction state
    let userHasInteracted = false;
    let pendingAudioActions = [];
    let audioContext = null;
    
    // Create a singleton audio interaction manager
    window.AudioInteractionManager = {
        // Check if user has interacted - FORCE DISABLE AUDIO
        hasUserInteracted: function() {
            return false; // Force disable all audio
        },
        
        // Initialize audio context (required for some browsers)
        initAudioContext: function() {
            if (!audioContext) {
                try {
                    const AudioContext = window.AudioContext || window.webkitAudioContext;
                    audioContext = new AudioContext();
                    
                    // Resume context if suspended
                    if (audioContext.state === 'suspended') {
                        audioContext.resume();
                    }
                } catch (e) {
                    console.warn('Failed to create AudioContext:', e);
                }
            }
            return audioContext;
        },
        
        // Queue audio action for when user interacts
        queueAudioAction: function(action) {
            if (userHasInteracted) {
                // Execute immediately if user has already interacted
                try {
                    action();
                } catch (e) {
                    console.warn('Audio action failed:', e);
                }
            } else {
                // Queue for later
                pendingAudioActions.push(action);
            }
        },
        
        // Safe audio play wrapper
        safePlay: function(audio, label) {
            if (!audio) return Promise.reject('No audio element provided');
            
            // Ensure audio is ready
            if (audio.readyState < 2) {
                audio.load();
            }
            
            if (userHasInteracted) {
                // User has interacted, safe to play
                return audio.play().catch(err => {
                    console.warn(`${label || 'Audio'} playback failed:`, err);
                    return Promise.reject(err);
                });
            } else {
                // Queue for when user interacts
                this.queueAudioAction(() => {
                    audio.play().catch(err => {
                        console.warn(`${label || 'Audio'} playback deferred failed:`, err);
                    });
                });
                return Promise.resolve(); // Return resolved promise for compatibility
            }
        },
        
        // Mark that user has interacted
        markUserInteraction: function() {
            if (!userHasInteracted) {
                userHasInteracted = true;
                console.log('User interaction detected - audio enabled');
                
                // Initialize audio context if needed
                this.initAudioContext();
                
                // Execute all pending audio actions
                while (pendingAudioActions.length > 0) {
                    const action = pendingAudioActions.shift();
                    try {
                        action();
                    } catch (e) {
                        console.warn('Queued audio action failed:', e);
                    }
                }
                
                // Notify audio engine if it exists
                if (window.casinoAudio && window.casinoAudio.handleUserInteraction) {
                    window.casinoAudio.handleUserInteraction();
                }
            }
        },
        
        // Reset interaction state (useful for testing)
        reset: function() {
            userHasInteracted = false;
            pendingAudioActions = [];
            if (audioContext) {
                audioContext.close();
                audioContext = null;
            }
        }
    };
    
    // Detect user interaction events
    const interactionEvents = [
        'click', 'touchstart', 'touchend', 'keydown', 'mousedown'
    ];
    
    // Add interaction listeners
    function addInteractionListeners() {
        interactionEvents.forEach(eventType => {
            document.addEventListener(eventType, handleInteraction, { 
                once: false, // Keep listening for ongoing interactions
                passive: true,
                capture: true 
            });
        });
    }
    
    // Handle user interaction
    function handleInteraction(event) {
        // Don't count programmatic clicks
        if (event.isTrusted) {
            window.AudioInteractionManager.markUserInteraction();
        }
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', addInteractionListeners);
    } else {
        addInteractionListeners();
    }
    
    // Also check for interaction on window focus (user switching tabs back)
    window.addEventListener('focus', function() {
        if (document.hasFocus()) {
            // User returned to tab, but still need actual interaction
            console.log('Window focused - waiting for user interaction to enable audio');
        }
    });
    
    // Handle visibility change
    document.addEventListener('visibilitychange', function() {
        if (!document.hidden && audioContext && audioContext.state === 'suspended') {
            // Try to resume audio context when page becomes visible
            audioContext.resume().catch(e => {
                console.warn('Failed to resume audio context on visibility change:', e);
            });
        }
    });
    
})();