// phaser-audio-enhancement.js
// Professional Audio Architecture Enhancement for Phaser.js Casino Games
// Version: 1.0.0 - Immersive Vegas Casino Audio Experience

class PhaserAudioEnhancement {
    constructor() {
        this.initialized = false;
        this.audioEngine = null;
        this.phaserSound = null;
        this.context = null;
        
        // Advanced audio configuration
        this.config = {
            // Spatial Audio Settings
            spatial: {
                enabled: true,
                listenerPosition: { x: 0, y: 0, z: 0 },
                maxDistance: 1000,
                refDistance: 100,
                rolloffFactor: 1,
                coneInnerAngle: 360,
                coneOuterAngle: 360,
                coneOuterGain: 0
            },
            
            // Dynamic Range Compression
            compression: {
                enabled: true,
                threshold: -24,
                knee: 30,
                ratio: 12,
                attack: 0.003,
                release: 0.25
            },
            
            // Reverb Settings
            reverb: {
                enabled: true,
                wetGain: 0.15,
                dryGain: 0.85,
                roomSize: 'large',
                decay: 2.5,
                preDelay: 0.03
            },
            
            // Audio Layers
            layers: {
                background: { volume: 0.3, pan: 0, loop: true },
                effects: { volume: 0.8, pan: 0, loop: false },
                ui: { volume: 0.7, pan: 0, loop: false },
                ambient: { volume: 0.4, pan: 0, loop: true },
                celebration: { volume: 1.0, pan: 0, loop: false }
            },
            
            // Performance Optimization
            performance: {
                maxSimultaneousSounds: 32,
                audioPoolSize: 10,
                preloadPriority: ['critical', 'common', 'rare'],
                adaptiveQuality: true,
                mobileOptimization: true
            }
        };
        
        // Game-specific audio mappings
        this.gameAudioMaps = {
            slots: {
                layers: {
                    background: ['casinoAmbient1', 'slotMachinesBg'],
                    ambient: ['crowdMurmur']
                },
                events: {
                    leverPull: {
                        sounds: ['slotLeverPull'],
                        volume: 0.9,
                        spatial: true,
                        position: { x: 0, y: -100 }
                    },
                    reelStart: {
                        sounds: ['slotReelStart'],
                        volume: 0.8,
                        pitch: 1.0
                    },
                    reelSpin: {
                        sounds: ['slotReelSpin'],
                        volume: 0.6,
                        loop: true,
                        fadeDuration: 500
                    },
                    reelStop: {
                        sounds: ['slotReelStop1', 'slotReelStop2', 'slotReelStop3'],
                        volume: 0.7,
                        sequential: true,
                        delay: 200
                    },
                    nearMiss: {
                        sounds: ['slotNearMiss'],
                        volume: 0.8,
                        pitch: 0.9
                    },
                    smallWin: {
                        sounds: ['winSmall', 'coinDrop'],
                        volume: 0.8,
                        pitch: 1.1
                    },
                    mediumWin: {
                        sounds: ['winMedium', 'coinShower', 'fanfare1'],
                        volume: 0.9,
                        spatial: true,
                        spread: 180
                    },
                    bigWin: {
                        sounds: ['winBig', 'coinCascade', 'fanfare2', 'applause'],
                        volume: 1.0,
                        spatial: true,
                        spread: 360
                    },
                    jackpot: {
                        sounds: ['winJackpot', 'voiceJackpot', 'airhorn', 'cheer'],
                        volume: 1.0,
                        spatial: true,
                        spread: 360,
                        reverb: 2.0
                    }
                }
            },
            
            wheel: {
                layers: {
                    background: ['casinoAmbient2'],
                    ambient: ['crowdMurmur']
                },
                events: {
                    wheelStart: {
                        sounds: ['wheelStart'],
                        volume: 0.8,
                        pitch: 1.0
                    },
                    wheelSpin: {
                        sounds: ['wheelSpin'],
                        volume: 0.6,
                        loop: true,
                        pitchVariation: true
                    },
                    wheelTick: {
                        sounds: ['wheelTick'],
                        volume: 0.5,
                        pitchRange: [0.9, 1.1],
                        spatial: true
                    },
                    wheelSlowdown: {
                        sounds: ['wheelSlowdown'],
                        volume: 0.7,
                        fadeDuration: 2000
                    },
                    wheelStop: {
                        sounds: ['wheelStop'],
                        volume: 0.8
                    },
                    prizeReveal: {
                        sounds: ['cashRegister', 'fanfare1'],
                        volume: 0.9,
                        delay: 500
                    },
                    jackpotReveal: {
                        sounds: ['winJackpot', 'voiceJackpot', 'fanfare3'],
                        volume: 1.0,
                        reverb: 2.5
                    }
                }
            },
            
            dice: {
                layers: {
                    background: ['casinoAmbient1'],
                    ambient: ['crowdMurmur']
                },
                events: {
                    diceShake: {
                        sounds: ['diceShake'],
                        volume: 0.7,
                        loop: true,
                        pitchVariation: true
                    },
                    diceThrow: {
                        sounds: ['diceThrow'],
                        volume: 0.8,
                        spatial: true,
                        trajectory: true
                    },
                    diceRoll: {
                        sounds: ['diceRoll1', 'diceRoll2'],
                        volume: 0.6,
                        randomPitch: [0.8, 1.2],
                        spatial: true
                    },
                    diceLand: {
                        sounds: ['diceLand'],
                        volume: 0.7,
                        spatial: true,
                        surface: 'felt'
                    },
                    diceSettle: {
                        sounds: ['diceSettle'],
                        volume: 0.5,
                        delay: 100
                    },
                    diceWin: {
                        sounds: ['winMedium', 'coinShower'],
                        volume: 0.9
                    },
                    snakeEyes: {
                        sounds: ['winHuge', 'fanfare2', 'voiceCongratulations'],
                        volume: 1.0,
                        special: true
                    },
                    boxcars: {
                        sounds: ['winBig', 'fanfare1', 'applause'],
                        volume: 1.0,
                        special: true
                    }
                }
            },
            
            scratch: {
                layers: {
                    background: ['casinoAmbient2']
                },
                events: {
                    scratchStart: {
                        sounds: ['scratchStart'],
                        volume: 0.7
                    },
                    scratchLoop: {
                        sounds: ['scratchLoop'],
                        volume: 0.6,
                        loop: true,
                        followPointer: true
                    },
                    scratchReveal: {
                        sounds: ['scratchReveal'],
                        volume: 0.8,
                        pitch: 1.1
                    },
                    scratchComplete: {
                        sounds: ['scratchComplete'],
                        volume: 0.7
                    },
                    prizeWin: {
                        sounds: ['winSmall', 'coinDrop'],
                        volume: 0.8
                    },
                    bigPrize: {
                        sounds: ['winBig', 'fanfare1', 'coinCascade'],
                        volume: 1.0
                    }
                }
            }
        };
        
        // Audio state management
        this.activeLoops = new Map();
        this.spatialSources = new Map();
        this.audioQueue = [];
        this.currentGame = null;
        
        // Performance metrics
        this.metrics = {
            totalSoundsPlayed: 0,
            simultaneousSounds: 0,
            droppedSounds: 0,
            averageLatency: 0,
            loadTime: {}
        };
    }
    
    // Initialize enhancement system
    async initialize(phaserGame, existingAudioEngine) {
        if (this.initialized) return;
        
        console.log('🎵 Initializing Phaser Audio Enhancement System...');
        
        // Reference existing systems
        this.phaserSound = phaserGame.sound;
        this.audioEngine = existingAudioEngine || window.casinoAudio;
        
        // Get Web Audio context from Phaser or create new
        if (this.phaserSound && this.phaserSound.context) {
            this.context = this.phaserSound.context;
        } else if (this.audioEngine && this.audioEngine.context) {
            this.context = this.audioEngine.context;
        } else {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.context = new AudioContext();
        }
        
        // Setup audio processing chain
        this.setupAudioProcessingChain();
        
        // Setup spatial audio system
        this.setupSpatialAudioSystem();
        
        // Preload critical sounds
        await this.preloadCriticalSounds();
        
        // Setup mobile optimizations
        this.setupMobileOptimizations();
        
        // Initialize performance monitoring
        this.initializePerformanceMonitoring();
        
        this.initialized = true;
        console.log('✅ Phaser Audio Enhancement System initialized!');
    }
    
    // Setup advanced audio processing chain
    setupAudioProcessingChain() {
        // Master gain
        this.masterGain = this.context.createGain();
        this.masterGain.gain.value = 1.0;
        
        // Compressor for dynamic range
        this.compressor = this.context.createDynamicsCompressor();
        this.compressor.threshold.value = this.config.compression.threshold;
        this.compressor.knee.value = this.config.compression.knee;
        this.compressor.ratio.value = this.config.compression.ratio;
        this.compressor.attack.value = this.config.compression.attack;
        this.compressor.release.value = this.config.compression.release;
        
        // Reverb convolver
        this.convolver = this.context.createConvolver();
        this.convolverGain = this.context.createGain();
        this.convolverGain.gain.value = this.config.reverb.wetGain;
        
        // Dry signal path
        this.dryGain = this.context.createGain();
        this.dryGain.gain.value = this.config.reverb.dryGain;
        
        // Connect the chain
        this.masterGain.connect(this.compressor);
        this.compressor.connect(this.dryGain);
        this.dryGain.connect(this.context.destination);
        
        // Reverb send
        if (this.config.reverb.enabled) {
            this.compressor.connect(this.convolver);
            this.convolver.connect(this.convolverGain);
            this.convolverGain.connect(this.context.destination);
            
            // Generate reverb impulse
            this.generateReverbImpulse();
        }
        
        // Analyzer for visualization
        this.analyser = this.context.createAnalyser();
        this.analyser.fftSize = 2048;
        this.compressor.connect(this.analyser);
    }
    
    // Generate synthetic reverb impulse response
    generateReverbImpulse() {
        const length = this.context.sampleRate * this.config.reverb.decay;
        const impulse = this.context.createBuffer(2, length, this.context.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = impulse.getChannelData(channel);
            for (let i = 0; i < length; i++) {
                channelData[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, 2);
            }
        }
        
        this.convolver.buffer = impulse;
    }
    
    // Setup 3D spatial audio system
    setupSpatialAudioSystem() {
        if (!this.context.listener) return;
        
        this.listener = this.context.listener;
        
        // Set listener position (player position)
        if (this.listener.positionX) {
            this.listener.positionX.value = this.config.spatial.listenerPosition.x;
            this.listener.positionY.value = this.config.spatial.listenerPosition.y;
            this.listener.positionZ.value = this.config.spatial.listenerPosition.z;
        } else {
            // Fallback for older browsers
            this.listener.setPosition(
                this.config.spatial.listenerPosition.x,
                this.config.spatial.listenerPosition.y,
                this.config.spatial.listenerPosition.z
            );
        }
        
        // Set listener orientation (looking into screen)
        if (this.listener.forwardX) {
            this.listener.forwardX.value = 0;
            this.listener.forwardY.value = 0;
            this.listener.forwardZ.value = -1;
            this.listener.upX.value = 0;
            this.listener.upY.value = 1;
            this.listener.upZ.value = 0;
        } else {
            // Fallback for older browsers
            this.listener.setOrientation(0, 0, -1, 0, 1, 0);
        }
    }
    
    // Create spatial audio source
    createSpatialSource(x = 0, y = 0, z = 0) {
        const panner = this.context.createPanner();
        
        panner.panningModel = 'HRTF';
        panner.distanceModel = 'inverse';
        panner.refDistance = this.config.spatial.refDistance;
        panner.maxDistance = this.config.spatial.maxDistance;
        panner.rolloffFactor = this.config.spatial.rolloffFactor;
        panner.coneInnerAngle = this.config.spatial.coneInnerAngle;
        panner.coneOuterAngle = this.config.spatial.coneOuterAngle;
        panner.coneOuterGain = this.config.spatial.coneOuterGain;
        
        // Set position
        if (panner.positionX) {
            panner.positionX.value = x;
            panner.positionY.value = y;
            panner.positionZ.value = z;
        } else {
            panner.setPosition(x, y, z);
        }
        
        return panner;
    }
    
    // Play enhanced audio for game event
    async playGameAudio(gameType, eventName, options = {}) {
        const gameMap = this.gameAudioMaps[gameType];
        if (!gameMap || !gameMap.events[eventName]) {
            console.warn(`No audio mapping for ${gameType}.${eventName}`);
            return;
        }
        
        const eventConfig = gameMap.events[eventName];
        const mergedOptions = { ...eventConfig, ...options };
        
        // Handle sequential sounds
        if (mergedOptions.sequential) {
            return this.playSequentialSounds(eventConfig.sounds, mergedOptions);
        }
        
        // Handle multiple simultaneous sounds
        const promises = eventConfig.sounds.map((soundKey, index) => {
            const delay = mergedOptions.delay ? mergedOptions.delay * index : 0;
            return this.playEnhancedSound(soundKey, {
                ...mergedOptions,
                delay
            });
        });
        
        return Promise.all(promises);
    }
    
    // Play enhanced single sound with all effects
    async playEnhancedSound(soundKey, options = {}) {
        // Check if we should use existing audio engine
        if (this.audioEngine && this.audioEngine.play) {
            // Integrate with existing engine but add enhancements
            const sound = await this.audioEngine.play(soundKey, {
                volume: options.volume || 1.0,
                loop: options.loop || false
            });
            
            // Add spatial positioning if needed
            if (options.spatial && sound) {
                this.applySpatialPositioning(sound, options);
            }
            
            // Add pitch variation if needed
            if (options.pitchVariation || options.pitch) {
                this.applyPitchVariation(sound, options);
            }
            
            return sound;
        }
        
        // Fallback to Phaser sound system
        if (this.phaserSound) {
            const config = {
                volume: options.volume || 1.0,
                loop: options.loop || false,
                delay: options.delay || 0
            };
            
            // Add pitch variation
            if (options.pitch) {
                config.rate = options.pitch;
            } else if (options.pitchVariation) {
                config.rate = 0.9 + Math.random() * 0.2;
            } else if (options.randomPitch) {
                config.rate = options.randomPitch[0] + 
                    Math.random() * (options.randomPitch[1] - options.randomPitch[0]);
            }
            
            // Add spatial positioning
            if (options.spatial && options.position) {
                config.pan = this.calculatePan(options.position.x);
            }
            
            return this.phaserSound.play(soundKey, config);
        }
    }
    
    // Play sequential sounds with timing
    async playSequentialSounds(sounds, options) {
        for (let i = 0; i < sounds.length; i++) {
            await this.playEnhancedSound(sounds[i], {
                ...options,
                delay: i * (options.delay || 200)
            });
            
            // Wait for delay between sounds
            if (options.delay && i < sounds.length - 1) {
                await this.wait(options.delay);
            }
        }
    }
    
    // Apply spatial positioning to sound
    applySpatialPositioning(sound, options) {
        if (!sound || !options.position) return;
        
        // Create or get spatial source
        const spatialId = `${sound.key}_${Date.now()}`;
        const panner = this.createSpatialSource(
            options.position.x || 0,
            options.position.y || 0,
            options.position.z || 0
        );
        
        // Store for later updates
        this.spatialSources.set(spatialId, {
            panner,
            sound,
            options
        });
        
        // Apply spread if specified
        if (options.spread) {
            this.applySpatialSpread(panner, options.spread);
        }
        
        // Apply trajectory if specified
        if (options.trajectory) {
            this.applySpatialTrajectory(spatialId, options);
        }
    }
    
    // Apply spatial spread for immersive effects
    applySpatialSpread(panner, spread) {
        const angle = (Math.random() - 0.5) * spread;
        const distance = this.config.spatial.refDistance * (0.5 + Math.random() * 0.5);
        
        const x = Math.sin(angle * Math.PI / 180) * distance;
        const z = Math.cos(angle * Math.PI / 180) * distance;
        
        if (panner.positionX) {
            panner.positionX.value = x;
            panner.positionZ.value = z;
        } else {
            panner.setPosition(x, 0, z);
        }
    }
    
    // Apply moving trajectory for spatial sound
    applySpatialTrajectory(spatialId, options) {
        const spatial = this.spatialSources.get(spatialId);
        if (!spatial) return;
        
        const startX = options.position.x || 0;
        const startY = options.position.y || 0;
        const endX = options.trajectoryEnd?.x || 0;
        const endY = options.trajectoryEnd?.y || 0;
        const duration = options.trajectoryDuration || 1000;
        
        const startTime = Date.now();
        
        const updatePosition = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const x = startX + (endX - startX) * progress;
            const y = startY + (endY - startY) * progress;
            
            if (spatial.panner.positionX) {
                spatial.panner.positionX.value = x;
                spatial.panner.positionY.value = y;
            } else {
                spatial.panner.setPosition(x, y, 0);
            }
            
            if (progress < 1) {
                requestAnimationFrame(updatePosition);
            } else {
                this.spatialSources.delete(spatialId);
            }
        };
        
        updatePosition();
    }
    
    // Apply pitch variation effects
    applyPitchVariation(sound, options) {
        if (!sound) return;
        
        if (options.pitchVariation) {
            // Random pitch variation
            const variation = 0.9 + Math.random() * 0.2;
            if (sound.setRate) sound.setRate(variation);
        } else if (options.pitchRange) {
            // Pitch within range
            const pitch = options.pitchRange[0] + 
                Math.random() * (options.pitchRange[1] - options.pitchRange[0]);
            if (sound.setRate) sound.setRate(pitch);
        } else if (options.pitch) {
            // Fixed pitch
            if (sound.setRate) sound.setRate(options.pitch);
        }
    }
    
    // Start background layers for game
    async startGameLayers(gameType) {
        const gameMap = this.gameAudioMaps[gameType];
        if (!gameMap || !gameMap.layers) return;
        
        // Stop current game layers
        this.stopAllLayers();
        
        // Start background layer
        if (gameMap.layers.background) {
            for (const soundKey of gameMap.layers.background) {
                const loop = await this.playEnhancedSound(soundKey, {
                    volume: this.config.layers.background.volume,
                    loop: true,
                    fadeIn: 1000
                });
                this.activeLoops.set(`bg_${soundKey}`, loop);
            }
        }
        
        // Start ambient layer
        if (gameMap.layers.ambient) {
            for (const soundKey of gameMap.layers.ambient) {
                const loop = await this.playEnhancedSound(soundKey, {
                    volume: this.config.layers.ambient.volume,
                    loop: true,
                    fadeIn: 2000
                });
                this.activeLoops.set(`amb_${soundKey}`, loop);
            }
        }
        
        this.currentGame = gameType;
    }
    
    // Stop all background layers
    stopAllLayers() {
        this.activeLoops.forEach((sound, key) => {
            if (sound && sound.stop) {
                // Fade out instead of abrupt stop
                this.fadeOutSound(sound, 500);
            }
        });
        this.activeLoops.clear();
    }
    
    // Fade in sound
    fadeInSound(sound, duration = 1000) {
        if (!sound || !sound.volume) return;
        
        const startVolume = 0;
        const endVolume = sound.volume.value || 1.0;
        const startTime = Date.now();
        
        sound.volume.value = startVolume;
        
        const fade = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            sound.volume.value = startVolume + (endVolume - startVolume) * progress;
            
            if (progress < 1) {
                requestAnimationFrame(fade);
            }
        };
        
        fade();
    }
    
    // Fade out sound
    fadeOutSound(sound, duration = 500) {
        if (!sound || !sound.volume) return;
        
        const startVolume = sound.volume.value || 1.0;
        const startTime = Date.now();
        
        const fade = () => {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            sound.volume.value = startVolume * (1 - progress);
            
            if (progress < 1) {
                requestAnimationFrame(fade);
            } else {
                if (sound.stop) sound.stop();
            }
        };
        
        fade();
    }
    
    // Calculate stereo pan from x position
    calculatePan(x, screenWidth = 1280) {
        return Math.max(-1, Math.min(1, (x - screenWidth / 2) / (screenWidth / 2)));
    }
    
    // Preload critical sounds for instant playback
    async preloadCriticalSounds() {
        const criticalSounds = [
            'buttonClick', 'coinDrop', 'winSmall', 'winMedium', 'winBig',
            'slotReelSpin', 'wheelTick', 'diceRoll1', 'scratchLoop'
        ];
        
        const promises = criticalSounds.map(sound => {
            if (this.audioEngine && this.audioEngine.preload) {
                return this.audioEngine.preload(sound);
            }
            return Promise.resolve();
        });
        
        await Promise.all(promises);
    }
    
    // Setup mobile-specific optimizations
    setupMobileOptimizations() {
        if (!this.isMobile()) return;
        
        // Reduce simultaneous sounds on mobile
        this.config.performance.maxSimultaneousSounds = 16;
        
        // Disable reverb on mobile for performance
        this.config.reverb.enabled = false;
        
        // Reduce spatial audio complexity
        this.config.spatial.maxDistance = 500;
        
        // Use lower quality settings
        if (this.analyser) {
            this.analyser.fftSize = 512;
        }
        
        // Setup touch-to-enable audio
        this.setupTouchAudioEnable();
    }
    
    // Setup touch handler for mobile audio enabling
    setupTouchAudioEnable() {
        const enableAudio = () => {
            if (this.context.state === 'suspended') {
                this.context.resume();
            }
            document.removeEventListener('touchstart', enableAudio);
            document.removeEventListener('click', enableAudio);
        };
        
        document.addEventListener('touchstart', enableAudio);
        document.addEventListener('click', enableAudio);
    }
    
    // Initialize performance monitoring
    initializePerformanceMonitoring() {
        setInterval(() => {
            this.updatePerformanceMetrics();
        }, 1000);
    }
    
    // Update performance metrics
    updatePerformanceMetrics() {
        // Count active sounds
        this.metrics.simultaneousSounds = this.activeLoops.size + this.spatialSources.size;
        
        // Check for dropped sounds
        if (this.metrics.simultaneousSounds > this.config.performance.maxSimultaneousSounds) {
            this.metrics.droppedSounds++;
        }
        
        // Calculate average latency
        if (this.context) {
            this.metrics.averageLatency = this.context.baseLatency || this.context.outputLatency || 0;
        }
    }
    
    // Check if running on mobile device
    isMobile() {
        return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
    }
    
    // Utility: wait for specified milliseconds
    wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // Get performance report
    getPerformanceReport() {
        return {
            initialized: this.initialized,
            currentGame: this.currentGame,
            activeLayers: this.activeLoops.size,
            spatialSources: this.spatialSources.size,
            metrics: this.metrics,
            context: {
                state: this.context?.state,
                sampleRate: this.context?.sampleRate,
                latency: this.context?.baseLatency
            }
        };
    }
    
    // Cleanup and destroy
    destroy() {
        this.stopAllLayers();
        this.spatialSources.clear();
        this.activeLoops.clear();
        
        if (this.context && this.context.state !== 'closed') {
            this.context.close();
        }
        
        this.initialized = false;
    }
}

// Integration with Phaser scenes
class PhaserAudioIntegration {
    static enhance(scene, gameType) {
        // Get or create enhancement instance
        if (!window.phaserAudioEnhancement) {
            window.phaserAudioEnhancement = new PhaserAudioEnhancement();
        }
        
        const audioEnhancement = window.phaserAudioEnhancement;
        
        // Initialize if needed
        if (!audioEnhancement.initialized) {
            audioEnhancement.initialize(scene.game, window.casinoAudio);
        }
        
        // Start game layers
        audioEnhancement.startGameLayers(gameType);
        
        // Add audio methods to scene
        scene.playAudio = (eventName, options) => {
            return audioEnhancement.playGameAudio(gameType, eventName, options);
        };
        
        scene.stopAudio = () => {
            audioEnhancement.stopAllLayers();
        };
        
        // Add scene cleanup
        scene.events.on('shutdown', () => {
            audioEnhancement.stopAllLayers();
        });
        
        return audioEnhancement;
    }
}

// Auto-initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('🎵 Phaser Audio Enhancement System loaded');
    
    // Create global instance
    window.PhaserAudioEnhancement = PhaserAudioEnhancement;
    window.PhaserAudioIntegration = PhaserAudioIntegration;
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PhaserAudioEnhancement, PhaserAudioIntegration };
}