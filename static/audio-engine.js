// audio-engine.js
// Professional-Grade Web Audio API Engine for Vegas Casino
// Version: 3.0.0 - Immersive Spatial Audio Edition

class CasinoAudioEngine {
    constructor() {
        this.initialized = false;
        this.context = null;
        this.masterGain = null;
        this.compressor = null;
        this.analyser = null;
        this.convolver = null;
        this.listener = null;
        
        // Audio categories with individual gain controls
        this.channels = {
            master: { gain: null, volume: 1.0 },
            effects: { gain: null, volume: 0.8 },
            ambient: { gain: null, volume: 0.4 },
            ui: { gain: null, volume: 0.7 },
            music: { gain: null, volume: 0.3 },
            voice: { gain: null, volume: 1.0 }
        };
        
        // Spatial audio sources
        this.spatialSources = new Map();
        
        // Audio buffer cache
        this.bufferCache = new Map();
        this.loadingPromises = new Map();
        
        // User preferences
        this.preferences = {
            masterVolume: 1.0,
            effectsVolume: 0.8,
            ambientVolume: 0.4,
            uiVolume: 0.7,
            musicVolume: 0.3,
            voiceVolume: 1.0,
            spatialAudio: true,
            reverb: true,
            compression: true,
            adaptiveQuality: true,
            muted: false,
            reducedMotion: false
        };
        
        // Performance monitoring
        this.performance = {
            bufferLoadTime: 0,
            averageLatency: 0,
            droppedFrames: 0,
            cpuUsage: 0
        };
        
        // Sound library paths
        this.soundLibrary = {
            // UI Sounds
            buttonHover: '/static/audio/ui-hover.mp3',
            buttonClick: '/static/audio/button-click.mp3',
            buttonDisabled: '/static/audio/ui-disabled.mp3',
            modalOpen: '/static/audio/modal-open.mp3',
            modalClose: '/static/audio/modal-close.mp3',
            tabSwitch: '/static/audio/tab-switch.mp3',
            
            // Slot Machine Sounds
            slotLeverPull: '/static/audio/slot-lever-pull.mp3',
            slotReelStart: '/static/audio/slot-reel-start.mp3',
            slotReelSpin: '/static/audio/reel-spin.mp3',
            slotReelStop1: '/static/audio/slot-reel-stop-1.mp3',
            slotReelStop2: '/static/audio/slot-reel-stop-2.mp3',
            slotReelStop3: '/static/audio/slot-reel-stop-3.mp3',
            slotNearMiss: '/static/audio/slot-near-miss.mp3',
            
            // Scratch Card Sounds
            scratchStart: '/static/audio/scratch-start.mp3',
            scratchLoop: '/static/audio/scratch-loop.mp3',
            scratchReveal: '/static/audio/scratch-reveal.mp3',
            scratchComplete: '/static/audio/scratch-complete.mp3',
            
            // Roulette Sounds
            rouletteSpin: '/static/audio/roulette-spin.mp3',
            rouletteBallRoll: '/static/audio/roulette-ball-roll.mp3',
            rouletteBallBounce: '/static/audio/roulette-ball-bounce.mp3',
            rouletteBallDrop: '/static/audio/roulette-ball-drop.mp3',
            rouletteClick: '/static/audio/roulette-click.mp3',
            
            // Wheel of Fortune Sounds
            wheelStart: '/static/audio/wheel-start.mp3',
            wheelSpin: '/static/audio/wheel-spin.mp3',
            wheelTick: '/static/audio/wheel-tick.mp3',
            wheelSlowdown: '/static/audio/wheel-slowdown.mp3',
            wheelStop: '/static/audio/wheel-stop.mp3',
            
            // Dice Sounds
            diceShake: '/static/audio/dice-shake.mp3',
            diceThrow: '/static/audio/dice-throw.mp3',
            diceRoll1: '/static/audio/dice-roll-1.mp3',
            diceRoll2: '/static/audio/dice-roll-2.mp3',
            diceLand: '/static/audio/dice-land.mp3',
            diceSettle: '/static/audio/dice-settle.mp3',
            
            // Win Sounds (Progressive)
            winTiny: '/static/audio/win-tiny.mp3',
            winSmall: '/static/audio/win-small.mp3',
            winMedium: '/static/audio/win-medium.mp3',
            winBig: '/static/audio/win-big.mp3',
            winHuge: '/static/audio/win-huge.mp3',
            winMega: '/static/audio/win-mega.mp3',
            winJackpot: '/static/audio/jackpot.mp3',
            
            // Coin & Money Sounds
            coinSingle: '/static/audio/coin-single.mp3',
            coinDrop: '/static/audio/coin-drop.mp3',
            coinShower: '/static/audio/coin-shower.mp3',
            coinCascade: '/static/audio/coin-cascade.mp3',
            cashRegister: '/static/audio/cash-register.mp3',
            
            // Celebration Sounds
            fanfare1: '/static/audio/fanfare-1.mp3',
            fanfare2: '/static/audio/fanfare-2.mp3',
            fanfare3: '/static/audio/fanfare-3.mp3',
            applause: '/static/audio/applause.mp3',
            cheer: '/static/audio/cheer.mp3',
            airhorn: '/static/audio/airhorn.mp3',
            
            // Ambient Casino Sounds
            casinoAmbient1: '/static/audio/casino-ambient-1.mp3',
            casinoAmbient2: '/static/audio/casino-ambient-2.mp3',
            slotMachinesBg: '/static/audio/slot-machines-bg.mp3',
            crowdMurmur: '/static/audio/crowd-murmur.mp3',
            
            // Notification Sounds
            notificationSuccess: '/static/audio/notification-success.mp3',
            notificationError: '/static/audio/notification-error.mp3',
            notificationWarning: '/static/audio/notification-warning.mp3',
            notificationInfo: '/static/audio/notification-info.mp3',
            
            // Voice Announcements
            voiceWelcome: '/static/audio/voice-welcome.mp3',
            voiceCongratulations: '/static/audio/voice-congratulations.mp3',
            voiceJackpot: '/static/audio/voice-jackpot.mp3',
            voiceGoodLuck: '/static/audio/voice-good-luck.mp3',
            
            // Transitional Sounds
            swooshIn: '/static/audio/swoosh-in.mp3',
            swooshOut: '/static/audio/swoosh-out.mp3',
            slideIn: '/static/audio/slide-in.mp3',
            slideOut: '/static/audio/slide-out.mp3',
            fadeTransition: '/static/audio/fade-transition.mp3'
        };
        
        // Fallback to existing sounds initially
        this.fallbackSounds = {
            buttonClick: '/static/audio/button-click.mp3',
            casinoWin: '/static/audio/casino-win.mp3',
            jackpot: '/static/audio/jackpot.mp3',
            reelSpin: '/static/audio/reel-spin.mp3',
            coinDrop: '/coin-drop.mp3',
            slotPull: '/slot-pull.mp3'
        };
        
        // Audio pool for rapid-fire sounds
        this.audioPool = new Map();
        this.poolSize = 5; // Number of instances per sound
        
        // Reverb impulse responses
        this.impulseResponses = {
            smallRoom: '/static/audio/impulse/small-room.wav',
            largeHall: '/static/audio/impulse/large-hall.wav',
            cathedral: '/static/audio/impulse/cathedral.wav',
            casino: '/static/audio/impulse/casino.wav'
        };
        
        // Initialize on first user interaction
        this.initPromise = null;
        this.setupUserInteractionListener();
        
        // Load preferences from localStorage
        this.loadPreferences();
        
        // Performance monitoring
        this.startPerformanceMonitoring();
    }
    
    // Initialize Web Audio API
    async initialize() {
        if (this.initialized) return;
        
        try {
            // Create audio context
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.context = new AudioContext();
            
            // Setup master chain
            this.setupAudioGraph();
            
            // Setup spatial audio
            this.setupSpatialAudio();
            
            // Preload critical sounds
            await this.preloadCriticalSounds();
            
            // Load impulse response for reverb
            if (this.preferences.reverb) {
                await this.loadImpulseResponse('casino');
            }
            
            this.initialized = true;
            console.log('🎵 Casino Audio Engine initialized successfully');
            
            // Resume context if suspended
            if (this.context.state === 'suspended') {
                await this.context.resume();
            }
            
        } catch (error) {
            console.error('Failed to initialize audio engine:', error);
            this.fallbackToHTML5Audio();
        }
    }
    
    // Setup audio processing graph
    setupAudioGraph() {
        // Create master gain node
        this.masterGain = this.context.createGain();
        this.masterGain.gain.value = this.preferences.masterVolume;
        
        // Create dynamics compressor for consistent volume
        this.compressor = this.context.createDynamicsCompressor();
        this.compressor.threshold.value = -24;
        this.compressor.knee.value = 30;
        this.compressor.ratio.value = 12;
        this.compressor.attack.value = 0.003;
        this.compressor.release.value = 0.25;
        
        // Create analyser for visualizations
        this.analyser = this.context.createAnalyser();
        this.analyser.fftSize = 2048;
        this.analyser.smoothingTimeConstant = 0.8;
        
        // Create convolver for reverb
        this.convolver = this.context.createConvolver();
        this.convolverGain = this.context.createGain();
        this.convolverGain.gain.value = 0.3;
        this.dryGain = this.context.createGain();
        this.dryGain.gain.value = 0.7;
        
        // Setup channel gains
        for (const [name, channel] of Object.entries(this.channels)) {
            channel.gain = this.context.createGain();
            channel.gain.gain.value = channel.volume * this.preferences[`${name}Volume`] || channel.volume;
        }
        
        // Connect audio graph
        // Channels -> Compressor -> Master -> Analyser -> Destination
        this.compressor.connect(this.masterGain);
        this.masterGain.connect(this.analyser);
        this.analyser.connect(this.context.destination);
        
        // Setup reverb path (parallel processing)
        if (this.preferences.reverb) {
            this.convolver.connect(this.convolverGain);
            this.convolverGain.connect(this.masterGain);
        }
    }
    
    // Setup 3D spatial audio
    setupSpatialAudio() {
        if (!this.context.listener) {
            console.warn('Spatial audio not supported in this browser');
            return;
        }
        
        this.listener = this.context.listener;
        
        // Set default listener position (center of screen)
        if (this.listener.positionX) {
            // New API
            this.listener.positionX.value = 0;
            this.listener.positionY.value = 0;
            this.listener.positionZ.value = 0;
        } else if (this.listener.setPosition) {
            // Legacy API
            this.listener.setPosition(0, 0, 0);
        }
        
        // Set listener orientation (facing into the screen)
        if (this.listener.forwardX) {
            // New API
            this.listener.forwardX.value = 0;
            this.listener.forwardY.value = 0;
            this.listener.forwardZ.value = -1;
            this.listener.upX.value = 0;
            this.listener.upY.value = 1;
            this.listener.upZ.value = 0;
        } else if (this.listener.setOrientation) {
            // Legacy API
            this.listener.setOrientation(0, 0, -1, 0, 1, 0);
        }
    }
    
    // Load and decode audio buffer
    async loadSound(url, useCache = true) {
        // Check cache first
        if (useCache && this.bufferCache.has(url)) {
            return this.bufferCache.get(url);
        }
        
        // Check if already loading
        if (this.loadingPromises.has(url)) {
            return this.loadingPromises.get(url);
        }
        
        // Check if file exists before attempting to load
        const fallbackUrl = this.getFallbackUrl(url);
        const actualUrl = await this.getValidAudioUrl(url, fallbackUrl);
        
        if (actualUrl !== url && fallbackUrl) {
            // Use fallback without trying primary file to avoid 404 errors
            console.debug(`Using fallback audio: ${actualUrl} instead of ${url}`);
            return this.loadSound(actualUrl, useCache);
        }
        
        // Create loading promise for the valid URL
        const loadPromise = this.fetchAndDecodeAudio(actualUrl || url);
        this.loadingPromises.set(url, loadPromise);
        
        try {
            const buffer = await loadPromise;
            this.bufferCache.set(url, buffer);
            this.loadingPromises.delete(url);
            return buffer;
        } catch (error) {
            this.loadingPromises.delete(url);
            // Try fallback sound if available and not already tried
            if (fallbackUrl && fallbackUrl !== url && actualUrl === url) {
                console.warn(`Failed to load ${url}, trying fallback ${fallbackUrl}`);
                return this.loadSound(fallbackUrl, useCache);
            }
            throw error;
        }
    }
    
    // Fetch and decode audio
    async fetchAndDecodeAudio(url) {
        const startTime = performance.now();
        
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const arrayBuffer = await response.arrayBuffer();
            const audioBuffer = await this.context.decodeAudioData(arrayBuffer);
            
            this.performance.bufferLoadTime = performance.now() - startTime;
            
            return audioBuffer;
        } catch (error) {
            // Only log as error if it's not a missing file with available fallback
            const fallbackUrl = this.getFallbackUrl(url);
            if (fallbackUrl && (error.message.includes('404') || error.message.includes('416'))) {
                console.debug(`Audio file not found (will use fallback): ${url}`);
            } else {
                console.error(`Failed to load audio: ${url}`, error);
            }
            throw error;
        }
    }
    
    // Get fallback URL for missing sounds
    getFallbackUrl(url) {
        const filename = url.split('/').pop();
        
        // Map new sounds to existing fallbacks
        const fallbackMap = {
            'ui-hover.mp3': this.fallbackSounds.buttonClick,
            'slot-lever-pull.mp3': this.fallbackSounds.slotPull,
            'slot-reel-start.mp3': this.fallbackSounds.reelSpin,
            'win-tiny.mp3': this.fallbackSounds.coinDrop,
            'win-small.mp3': this.fallbackSounds.coinDrop,
            'win-medium.mp3': this.fallbackSounds.casinoWin,
            'win-big.mp3': this.fallbackSounds.casinoWin,
            'win-huge.mp3': this.fallbackSounds.jackpot,
            'win-mega.mp3': this.fallbackSounds.jackpot,
            'coin-single.mp3': this.fallbackSounds.coinDrop,
            'coin-shower.mp3': this.fallbackSounds.coinDrop,
            'coin-cascade.mp3': this.fallbackSounds.jackpot
        };
        
        return fallbackMap[filename] || null;
    }
    
    // Check if audio file exists and return valid URL
    async getValidAudioUrl(primaryUrl, fallbackUrl) {
        // List of known existing audio files to avoid HTTP requests for missing ones
        const existingFiles = [
            '/static/audio/button-click.mp3',
            '/static/audio/casino-win.mp3', 
            '/static/audio/jackpot.mp3',
            '/static/audio/reel-spin.mp3',
            '/static/coin-drop.mp3',
            '/static/slot-pull.mp3',
            '/static/win-sound.mp3'
        ];
        
        // Check if primary file exists in our known files
        if (existingFiles.includes(primaryUrl)) {
            return primaryUrl;
        }
        
        // If primary doesn't exist but we have a fallback, check fallback
        if (fallbackUrl && existingFiles.includes(fallbackUrl)) {
            return fallbackUrl;
        }
        
        // If neither exists in our known list, try a quick HEAD request for primary
        try {
            const response = await fetch(primaryUrl, { method: 'HEAD' });
            if (response.ok) {
                return primaryUrl;
            }
        } catch (error) {
            // Primary file doesn't exist, fallback to known file if available
        }
        
        // Return fallback if available, otherwise return primary (will fail gracefully)
        return fallbackUrl || primaryUrl;
    }
    
    // Play sound with options
    async play(soundName, options = {}) {
        if (!this.initialized) {
            await this.initialize();
        }
        
        if (this.preferences.muted) return;
        
        const defaults = {
            volume: 1.0,
            channel: 'effects',
            loop: false,
            rate: 1.0,
            detune: 0,
            delay: 0,
            fadeIn: 0,
            fadeOut: 0,
            pan: 0,
            spatial: false,
            position: { x: 0, y: 0, z: 0 },
            reverb: false
        };
        
        const config = { ...defaults, ...options };
        
        try {
            // Get sound URL
            const url = this.soundLibrary[soundName] || this.fallbackSounds[soundName] || soundName;
            
            // Load audio buffer
            const buffer = await this.loadSound(url);
            
            // Schedule playback
            if (config.delay > 0) {
                setTimeout(() => this.playBuffer(buffer, config), config.delay);
            } else {
                await this.playBuffer(buffer, config);
            }
            
        } catch (error) {
            console.error(`Failed to play sound: ${soundName}`, error);
            // Fallback to HTML5 audio
            this.playHTML5Audio(soundName, config);
        }
    }
    
    // Play audio buffer
    async playBuffer(buffer, config) {
        const source = this.context.createBufferSource();
        source.buffer = buffer;
        source.loop = config.loop;
        source.playbackRate.value = config.rate;
        source.detune.value = config.detune;
        
        // Create gain node for this sound
        const gainNode = this.context.createGain();
        gainNode.gain.value = config.volume;
        
        // Apply fade in
        if (config.fadeIn > 0) {
            gainNode.gain.setValueAtTime(0, this.context.currentTime);
            gainNode.gain.linearRampToValueAtTime(config.volume, this.context.currentTime + config.fadeIn);
        }
        
        // Apply fade out
        if (config.fadeOut > 0 && buffer.duration > config.fadeOut) {
            const fadeOutTime = this.context.currentTime + buffer.duration - config.fadeOut;
            gainNode.gain.setValueAtTime(config.volume, fadeOutTime);
            gainNode.gain.linearRampToValueAtTime(0, fadeOutTime + config.fadeOut);
        }
        
        // Setup spatial audio if requested
        if (config.spatial && this.preferences.spatialAudio) {
            const panner = this.createPannerNode(config.position);
            source.connect(panner);
            panner.connect(gainNode);
        } else if (config.pan !== 0) {
            // Simple stereo panning
            const panNode = this.context.createStereoPanner();
            panNode.pan.value = Math.max(-1, Math.min(1, config.pan));
            source.connect(panNode);
            panNode.connect(gainNode);
        } else {
            source.connect(gainNode);
        }
        
        // Connect to appropriate channel
        const channel = this.channels[config.channel] || this.channels.effects;
        gainNode.connect(channel.gain);
        
        // Connect to reverb if enabled
        if (config.reverb && this.convolver && this.preferences.reverb) {
            gainNode.connect(this.convolver);
        }
        
        // Connect channel to compressor
        channel.gain.connect(this.compressor);
        
        // Start playback
        source.start(0);
        
        // Store reference for stopping later
        if (config.id) {
            this.spatialSources.set(config.id, { source, gainNode });
        }
        
        // Cleanup when finished
        source.onended = () => {
            if (config.id) {
                this.spatialSources.delete(config.id);
            }
        };
        
        return source;
    }
    
    // Create 3D panner node
    createPannerNode(position) {
        const panner = this.context.createPanner();
        
        // Set panner properties
        panner.panningModel = 'HRTF';
        panner.distanceModel = 'inverse';
        panner.refDistance = 1;
        panner.maxDistance = 100;
        panner.rolloffFactor = 1;
        panner.coneInnerAngle = 360;
        panner.coneOuterAngle = 0;
        panner.coneOuterGain = 0;
        
        // Set position
        if (panner.positionX) {
            // New API
            panner.positionX.value = position.x;
            panner.positionY.value = position.y;
            panner.positionZ.value = position.z;
        } else if (panner.setPosition) {
            // Legacy API
            panner.setPosition(position.x, position.y, position.z);
        }
        
        return panner;
    }
    
    // Play sequence of sounds
    async playSequence(sounds, interval = 100) {
        for (const sound of sounds) {
            if (typeof sound === 'string') {
                await this.play(sound);
            } else {
                await this.play(sound.name, sound.options);
            }
            await this.sleep(interval);
        }
    }
    
    // Play random sound from array
    async playRandom(sounds, options = {}) {
        const sound = sounds[Math.floor(Math.random() * sounds.length)];
        return this.play(sound, options);
    }
    
    // Play layered sounds simultaneously
    async playLayered(layers) {
        const promises = layers.map(layer => {
            if (typeof layer === 'string') {
                return this.play(layer);
            } else {
                return this.play(layer.name, layer.options);
            }
        });
        
        return Promise.all(promises);
    }
    
    // Dynamic sound based on value
    async playDynamic(baseName, value, options = {}) {
        let soundName;
        
        // Determine which sound variant to play based on value
        if (baseName === 'win') {
            if (value < 5) soundName = 'winTiny';
            else if (value < 10) soundName = 'winSmall';
            else if (value < 25) soundName = 'winMedium';
            else if (value < 50) soundName = 'winBig';
            else if (value < 100) soundName = 'winHuge';
            else if (value < 500) soundName = 'winMega';
            else soundName = 'winJackpot';
        } else if (baseName === 'coin') {
            if (value === 1) soundName = 'coinSingle';
            else if (value < 10) soundName = 'coinDrop';
            else if (value < 50) soundName = 'coinShower';
            else soundName = 'coinCascade';
        } else {
            soundName = baseName;
        }
        
        // Adjust volume based on value
        const volume = Math.min(1.0, 0.5 + (value / 200));
        
        return this.play(soundName, { ...options, volume });
    }
    
    // Stop sound by ID
    stop(id) {
        const spatial = this.spatialSources.get(id);
        if (spatial) {
            spatial.source.stop();
            this.spatialSources.delete(id);
        }
    }
    
    // Stop all sounds
    stopAll() {
        for (const [id, spatial] of this.spatialSources) {
            spatial.source.stop();
        }
        this.spatialSources.clear();
    }
    
    // Fade volume
    async fadeVolume(from, to, duration = 1000) {
        const steps = 30;
        const stepTime = duration / steps;
        const stepSize = (to - from) / steps;
        
        for (let i = 0; i <= steps; i++) {
            this.setMasterVolume(from + (stepSize * i));
            await this.sleep(stepTime);
        }
    }
    
    // Set master volume
    setMasterVolume(value) {
        this.preferences.masterVolume = Math.max(0, Math.min(1, value));
        if (this.masterGain) {
            this.masterGain.gain.value = this.preferences.masterVolume;
        }
        this.savePreferences();
    }
    
    // Set channel volume
    setChannelVolume(channel, value) {
        const ch = this.channels[channel];
        if (ch) {
            const volume = Math.max(0, Math.min(1, value));
            this.preferences[`${channel}Volume`] = volume;
            if (ch.gain) {
                ch.gain.gain.value = ch.volume * volume;
            }
            this.savePreferences();
        }
    }
    
    // Toggle mute
    toggleMute() {
        this.preferences.muted = !this.preferences.muted;
        if (this.masterGain) {
            this.masterGain.gain.value = this.preferences.muted ? 0 : this.preferences.masterVolume;
        }
        this.savePreferences();
        return this.preferences.muted;
    }
    
    // Set spatial audio enabled
    setSpatialAudio(enabled) {
        this.preferences.spatialAudio = enabled;
        this.savePreferences();
    }
    
    // Set reverb enabled
    async setReverb(enabled) {
        this.preferences.reverb = enabled;
        
        if (enabled && !this.convolver.buffer) {
            await this.loadImpulseResponse('casino');
        }
        
        if (this.convolverGain) {
            this.convolverGain.gain.value = enabled ? 0.3 : 0;
        }
        
        this.savePreferences();
    }
    
    // Load impulse response for reverb
    async loadImpulseResponse(type = 'casino') {
        if (!this.convolver) return;
        
        try {
            const url = this.impulseResponses[type] || this.impulseResponses.casino;
            const buffer = await this.loadSound(url);
            this.convolver.buffer = buffer;
        } catch (error) {
            console.warn('Failed to load impulse response:', error);
            // Create synthetic reverb as fallback
            this.createSyntheticReverb();
        }
    }
    
    // Create synthetic reverb impulse
    createSyntheticReverb() {
        const length = this.context.sampleRate * 2; // 2 second reverb
        const impulse = this.context.createBuffer(2, length, this.context.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = impulse.getChannelData(channel);
            for (let i = 0; i < length; i++) {
                channelData[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / length, 2);
            }
        }
        
        this.convolver.buffer = impulse;
    }
    
    // Preload critical sounds
    async preloadCriticalSounds() {
        const criticalSounds = [
            'buttonClick',
            'coinDrop',
            'winSmall',
            'winMedium',
            'winBig',
            'slotReelSpin',
            'slotReelStop1'
        ];
        
        const promises = criticalSounds.map(sound => {
            const url = this.soundLibrary[sound] || this.fallbackSounds[sound];
            if (url) {
                return this.loadSound(url).catch(error => {
                    console.warn(`Failed to preload ${sound}:`, error);
                });
            }
        });
        
        await Promise.allSettled(promises);
    }
    
    // Preload category of sounds
    async preloadCategory(category) {
        const categoryMap = {
            ui: ['buttonHover', 'buttonClick', 'modalOpen', 'modalClose'],
            slots: ['slotLeverPull', 'slotReelStart', 'slotReelSpin', 'slotReelStop1', 'slotReelStop2', 'slotReelStop3'],
            wins: ['winTiny', 'winSmall', 'winMedium', 'winBig', 'winHuge', 'winMega', 'winJackpot'],
            coins: ['coinSingle', 'coinDrop', 'coinShower', 'coinCascade'],
            ambient: ['casinoAmbient1', 'slotMachinesBg']
        };
        
        const sounds = categoryMap[category] || [];
        const promises = sounds.map(sound => {
            const url = this.soundLibrary[sound];
            if (url) {
                return this.loadSound(url).catch(error => {
                    console.warn(`Failed to preload ${sound}:`, error);
                });
            }
        });
        
        await Promise.allSettled(promises);
    }
    
    // Create audio pool for rapid-fire sounds
    createAudioPool(soundName, size = 5) {
        if (this.audioPool.has(soundName)) return;
        
        const pool = [];
        const url = this.soundLibrary[soundName] || this.fallbackSounds[soundName];
        
        for (let i = 0; i < size; i++) {
            const audio = new Audio(url);
            audio.preload = 'auto';
            pool.push(audio);
        }
        
        this.audioPool.set(soundName, { pool, index: 0 });
    }
    
    // Play from audio pool (for rapid sounds)
    playFromPool(soundName, volume = 1.0) {
        const poolData = this.audioPool.get(soundName);
        if (!poolData) {
            this.createAudioPool(soundName);
            return this.play(soundName, { volume });
        }
        
        const audio = poolData.pool[poolData.index];
        audio.volume = volume * this.preferences.effectsVolume;
        audio.currentTime = 0;
        audio.play().catch(e => console.warn('Pool playback failed:', e));
        
        poolData.index = (poolData.index + 1) % poolData.pool.length;
    }
    
    // Fallback HTML5 audio player
    playHTML5Audio(soundName, config) {
        const url = this.soundLibrary[soundName] || this.fallbackSounds[soundName] || soundName;
        const audio = new Audio(url);
        audio.volume = config.volume * this.preferences.effectsVolume;
        audio.playbackRate = config.rate || 1.0;
        audio.loop = config.loop || false;
        
        audio.play().catch(error => {
            console.warn('HTML5 audio playback failed:', error);
        });
        
        return audio;
    }
    
    // Fallback to HTML5 audio
    fallbackToHTML5Audio() {
        console.warn('Falling back to HTML5 audio');
        this.initialized = true; // Prevent repeated init attempts
        
        // Override play method
        this.play = async (soundName, options = {}) => {
            if (this.preferences.muted) return;
            
            const config = {
                volume: options.volume || 1.0,
                loop: options.loop || false,
                rate: options.rate || 1.0
            };
            
            return this.playHTML5Audio(soundName, config);
        };
    }
    
    // Setup user interaction listener
    setupUserInteractionListener() {
        const initOnInteraction = async () => {
            if (!this.initPromise) {
                this.initPromise = this.initialize();
                
                // Remove listeners after initialization
                document.removeEventListener('click', initOnInteraction);
                document.removeEventListener('touchstart', initOnInteraction);
                document.removeEventListener('keydown', initOnInteraction);
            }
            
            return this.initPromise;
        };
        
        // Listen for user interaction
        document.addEventListener('click', initOnInteraction, { once: false });
        document.addEventListener('touchstart', initOnInteraction, { once: false });
        document.addEventListener('keydown', initOnInteraction, { once: false });
    }
    
    // Get audio visualization data
    getVisualizationData() {
        if (!this.analyser) return null;
        
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        this.analyser.getByteFrequencyData(dataArray);
        
        return dataArray;
    }
    
    // Get current audio levels
    getAudioLevels() {
        if (!this.analyser) return { peak: 0, rms: 0 };
        
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        this.analyser.getByteTimeDomainData(dataArray);
        
        let peak = 0;
        let sumSquares = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            const normalized = (dataArray[i] - 128) / 128;
            peak = Math.max(peak, Math.abs(normalized));
            sumSquares += normalized * normalized;
        }
        
        const rms = Math.sqrt(sumSquares / bufferLength);
        
        return { peak, rms };
    }
    
    // Performance monitoring
    startPerformanceMonitoring() {
        setInterval(() => {
            if (!this.context) return;
            
            // Estimate latency
            this.performance.averageLatency = this.context.baseLatency || this.context.outputLatency || 0;
            
            // Check for dropped frames (simplified)
            if (this.context.currentTime > 0) {
                const expectedTime = performance.now() / 1000;
                const audioTime = this.context.currentTime;
                const drift = Math.abs(expectedTime - audioTime);
                
                if (drift > 0.1) {
                    this.performance.droppedFrames++;
                }
            }
        }, 1000);
    }
    
    // Save preferences to localStorage
    savePreferences() {
        localStorage.setItem('casinoAudioPreferences', JSON.stringify(this.preferences));
    }
    
    // Load preferences from localStorage
    loadPreferences() {
        const saved = localStorage.getItem('casinoAudioPreferences');
        if (saved) {
            try {
                this.preferences = { ...this.preferences, ...JSON.parse(saved) };
            } catch (error) {
                console.warn('Failed to load audio preferences:', error);
            }
        }
    }
    
    // Utility sleep function
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    // Get audio engine status
    getStatus() {
        return {
            initialized: this.initialized,
            context: this.context ? {
                state: this.context.state,
                sampleRate: this.context.sampleRate,
                latency: this.performance.averageLatency
            } : null,
            buffersCached: this.bufferCache.size,
            spatialSources: this.spatialSources.size,
            preferences: this.preferences,
            performance: this.performance
        };
    }
}

// Create global instance
window.casinoAudio = new CasinoAudioEngine();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CasinoAudioEngine;
}