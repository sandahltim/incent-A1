/**
 * Audio Promise Fix
 * Resolves audio promise rejections and play request interruptions
 * Version: 1.0.0
 */

(function() {
    'use strict';
    
    console.log('🔊 Audio Promise Fix: Initializing...');
    
    // Track active audio elements and their states
    const activeAudioElements = new Map();
    const audioPlayQueue = [];
    let isProcessingQueue = false;
    
    /**
     * Safely stop an audio element before playing new audio
     */
    function stopAudio(audio) {
        if (!audio) return Promise.resolve();
        
        return new Promise((resolve) => {
            try {
                // Pause the audio
                audio.pause();
                
                // Reset to beginning
                audio.currentTime = 0;
                
                // Remove from active elements
                activeAudioElements.delete(audio);
                
                // Small delay to ensure browser processes the stop
                setTimeout(resolve, 10);
            } catch (error) {
                // Silently handle stop errors
                resolve();
            }
        });
    }
    
    /**
     * Enhanced safe play function with proper promise handling
     */
    function enhancedSafePlay(audio, label = 'Audio') {
        if (!audio) {
            return Promise.reject(new Error('No audio element provided'));
        }
        
        // Return a properly handled promise
        return new Promise((resolve, reject) => {
            // Check if this audio is already playing
            if (activeAudioElements.has(audio)) {
                const state = activeAudioElements.get(audio);
                if (state === 'playing') {
                    // Stop the current playback before starting new one
                    stopAudio(audio).then(() => {
                        enhancedSafePlay(audio, label).then(resolve).catch(reject);
                    });
                    return;
                }
            }
            
            // Mark as pending
            activeAudioElements.set(audio, 'pending');
            
            // Ensure audio is loaded
            if (audio.readyState < 2) {
                audio.load();
            }
            
            // Create play promise
            const playPromise = audio.play();
            
            if (playPromise !== undefined) {
                playPromise
                    .then(() => {
                        // Mark as playing
                        activeAudioElements.set(audio, 'playing');
                        
                        // Set up ended listener
                        audio.addEventListener('ended', () => {
                            activeAudioElements.delete(audio);
                        }, { once: true });
                        
                        console.log(`✅ ${label} playing successfully`);
                        resolve();
                    })
                    .catch((error) => {
                        // Remove from active elements
                        activeAudioElements.delete(audio);
                        
                        // Handle specific error types
                        if (error.name === 'AbortError') {
                            // This happens when play is interrupted
                            console.debug(`⚠️ ${label} play interrupted - retrying...`);
                            
                            // Retry after a small delay
                            setTimeout(() => {
                                enhancedSafePlay(audio, label).then(resolve).catch(reject);
                            }, 50);
                        } else if (error.name === 'NotAllowedError') {
                            // User interaction required
                            console.debug(`🔇 ${label} requires user interaction`);
                            resolve(); // Don't reject, just resolve silently
                        } else if (error.name === 'NotSupportedError') {
                            console.warn(`❌ ${label} format not supported`);
                            resolve(); // Don't reject for unsupported formats
                        } else {
                            // Other errors
                            console.debug(`Audio error for ${label}:`, error.message);
                            resolve(); // Still resolve to prevent uncaught promises
                        }
                    });
            } else {
                // No promise returned (old browser)
                activeAudioElements.set(audio, 'playing');
                resolve();
            }
        });
    }
    
    /**
     * Override the global safePlay function if it exists
     */
    if (typeof window.safePlay === 'function') {
        const originalSafePlay = window.safePlay;
        window.safePlay = function(audio, label) {
            return enhancedSafePlay(audio, label);
        };
        console.log('✅ Enhanced safePlay function');
    }
    
    /**
     * Fix AudioInteractionManager.safePlay
     */
    if (window.AudioInteractionManager && window.AudioInteractionManager.safePlay) {
        const originalManagerSafePlay = window.AudioInteractionManager.safePlay;
        window.AudioInteractionManager.safePlay = function(audio, label) {
            if (!audio) return Promise.reject(new Error('No audio element provided'));
            
            const userHasInteracted = this.hasUserInteracted();
            
            if (userHasInteracted) {
                return enhancedSafePlay(audio, label);
            } else {
                // Queue for when user interacts
                this.queueAudioAction(() => {
                    enhancedSafePlay(audio, label).catch(() => {
                        // Silently handle queued audio failures
                    });
                });
                return Promise.resolve(); // Always return resolved promise
            }
        };
        console.log('✅ Enhanced AudioInteractionManager.safePlay');
    }
    
    /**
     * Fix the jackpot audio specifically
     */
    function fixJackpotAudio() {
        const originalPlayJackpot = window.playJackpot;
        if (typeof originalPlayJackpot === 'function') {
            window.playJackpot = function() {
                if (!window.soundOn) return Promise.resolve();
                
                // Stop any currently playing jackpot sound
                if (window.jackpotAudio) {
                    stopAudio(window.jackpotAudio).then(() => {
                        // Call original function
                        const result = originalPlayJackpot.call(this);
                        // Ensure it returns a promise
                        return result instanceof Promise ? result : Promise.resolve(result);
                    });
                } else {
                    // Call original function
                    const result = originalPlayJackpot.call(this);
                    // Ensure it returns a promise
                    return result instanceof Promise ? result : Promise.resolve(result);
                }
            };
            console.log('✅ Fixed playJackpot function');
        }
    }
    
    /**
     * Fix the audio engine play method
     */
    function fixAudioEngine() {
        if (window.casinoAudio && window.casinoAudio.play) {
            const originalPlay = window.casinoAudio.play;
            window.casinoAudio.play = async function(soundName, options = {}) {
                try {
                    const result = await originalPlay.call(this, soundName, options);
                    return result;
                } catch (error) {
                    // Handle the error gracefully
                    if (error && error.name === 'AbortError') {
                        console.debug(`Audio ${soundName} was interrupted, retrying...`);
                        // Retry once after a delay
                        await new Promise(resolve => setTimeout(resolve, 100));
                        try {
                            return await originalPlay.call(this, soundName, options);
                        } catch (retryError) {
                            console.debug(`Audio ${soundName} retry failed:`, retryError.message);
                            return Promise.resolve(); // Don't throw
                        }
                    }
                    console.debug(`Audio engine play error for ${soundName}:`, error.message);
                    return Promise.resolve(); // Don't throw
                }
            };
            console.log('✅ Fixed audio engine play method');
        }
    }
    
    /**
     * Prevent multiple rapid audio plays
     */
    function debounceAudioPlay(func, wait = 100) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            return new Promise((resolve) => {
                timeout = setTimeout(() => {
                    const result = func.apply(this, args);
                    if (result instanceof Promise) {
                        result.then(resolve).catch(() => resolve());
                    } else {
                        resolve(result);
                    }
                }, wait);
            });
        };
    }
    
    /**
     * Fix rainCoins function to handle audio properly
     */
    function fixRainCoins() {
        const originalRainCoins = window.rainCoins;
        if (typeof originalRainCoins === 'function') {
            window.rainCoins = function() {
                try {
                    // Call original function
                    const result = originalRainCoins.call(this);
                    
                    // If it plays audio, ensure promises are handled
                    if (window.soundOn && typeof window.playJackpot === 'function') {
                        // Debounce jackpot sound to prevent interruptions
                        const debouncedJackpot = debounceAudioPlay(window.playJackpot, 200);
                        debouncedJackpot().catch(() => {
                            // Silently handle any errors
                        });
                    }
                    
                    return result;
                } catch (error) {
                    console.error('❌ Confetti error (handled):', error);
                    // Don't throw the error further
                }
            };
            console.log('✅ Fixed rainCoins function');
        }
    }
    
    /**
     * Global promise rejection handler for any missed audio promises
     */
    function setupGlobalErrorHandlers() {
        // Handle unhandled promise rejections
        window.addEventListener('unhandledrejection', function(event) {
            // Check if it's an audio-related error
            if (event.reason && (
                event.reason.name === 'AbortError' ||
                event.reason.message?.includes('play()') ||
                event.reason.message?.includes('audio') ||
                event.reason.message?.includes('Audio')
            )) {
                console.debug('Caught unhandled audio promise:', event.reason.message);
                event.preventDefault(); // Prevent the error from showing in console
            }
        });
        
        // Handle errors from audio elements directly
        document.addEventListener('error', function(event) {
            if (event.target && event.target.tagName === 'AUDIO') {
                console.debug('Audio element error handled:', event.target.src);
                event.stopPropagation();
            }
        }, true);
        
        console.log('✅ Global error handlers installed');
    }
    
    /**
     * Initialize all fixes
     */
    function initialize() {
        console.log('🚀 Audio Promise Fix: Applying fixes...');
        
        // Apply all fixes
        fixJackpotAudio();
        fixAudioEngine();
        fixRainCoins();
        setupGlobalErrorHandlers();
        
        // Monitor for audio elements added to DOM
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.tagName === 'AUDIO') {
                        // Add error handler to new audio elements
                        node.addEventListener('error', (e) => {
                            console.debug('New audio element error handled:', node.src);
                            e.stopPropagation();
                        });
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        console.log('✅ Audio Promise Fix initialized successfully!');
        console.log('💡 Audio errors will now be handled gracefully');
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initialize);
    } else {
        // DOM is already loaded
        initialize();
    }
    
    // Also initialize after a delay to catch late-loading scripts
    setTimeout(initialize, 1000);
    
})();