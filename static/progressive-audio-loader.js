
// Progressive Audio Loader - Version 4.0.0
// Optimized for A1 Rent-It Incentive System

class ProgressiveAudioLoader {
    constructor() {
        this.audioContext = null;
        this.loadedBuffers = new Map();
        this.loadingPromises = new Map();
        this.loadingQueue = [];
        this.isLoading = false;
        
        this.init();
    }
    
    async init() {
        try {
            // Initialize Web Audio API
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            
            // Load audio manifest
            const manifest = await this.loadManifest();
            this.priorities = manifest.priorities;
            
            // Start progressive loading
            await this.startProgressiveLoading();
            
            console.log('✅ Progressive Audio Loader initialized');
        } catch (error) {
            console.error('❌ Progressive Audio Loader failed:', error);
        }
    }
    
    async loadManifest() {
        try {
            const response = await fetch('/static/audio/audio-manifest.json');
            return await response.json();
        } catch (error) {
            console.warn('Audio manifest not found, using defaults');
            return {
                priorities: {
                    critical: ['button-click.mp3', 'coin-drop.mp3', 'casino-win.mp3'],
                    important: ['jackpot.mp3', 'reel-spin.mp3'],
                    background: []
                }
            };
        }
    }
    
    async startProgressiveLoading() {
        // Load critical sounds immediately
        await this.loadPriorityGroup('critical');
        
        // Load important sounds after a short delay
        setTimeout(() => this.loadPriorityGroup('important'), 1000);
        
        // Load background sounds when page is idle
        if (window.requestIdleCallback) {
            window.requestIdleCallback(() => this.loadPriorityGroup('background'));
        } else {
            setTimeout(() => this.loadPriorityGroup('background'), 3000);
        }
    }
    
    async loadPriorityGroup(priority) {
        const files = this.priorities[priority] || [];
        const loadPromises = files.map(file => this.loadAudioFile(file));
        
        try {
            await Promise.all(loadPromises);
            console.log(`✅ Loaded ${priority} audio files (${files.length} files)`);
        } catch (error) {
            console.warn(`⚠️ Some ${priority} audio files failed to load:`, error);
        }
    }
    
    async loadAudioFile(filename) {
        // Avoid loading same file multiple times
        if (this.loadedBuffers.has(filename) || this.loadingPromises.has(filename)) {
            return this.loadingPromises.get(filename) || Promise.resolve();
        }
        
        const loadPromise = this.fetchAndDecodeAudio(filename);
        this.loadingPromises.set(filename, loadPromise);
        
        try {
            const buffer = await loadPromise;
            this.loadedBuffers.set(filename, buffer);
            this.loadingPromises.delete(filename);
            return buffer;
        } catch (error) {
            console.warn(`Failed to load audio: ${filename}`, error);
            this.loadingPromises.delete(filename);
            throw error;
        }
    }
    
    async fetchAndDecodeAudio(filename) {
        const response = await fetch(`/static/audio/${filename}`);
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        
        const arrayBuffer = await response.arrayBuffer();
        return await this.audioContext.decodeAudioData(arrayBuffer);
    }
    
    // Play audio with fallback
    async playAudio(filename, options = {}) {
        try {
            // Try to get pre-loaded buffer
            let buffer = this.loadedBuffers.get(filename);
            
            // If not loaded, load it now (blocking)
            if (!buffer) {
                console.log(`Loading audio on-demand: ${filename}`);
                buffer = await this.loadAudioFile(filename);
            }
            
            // Play the audio
            const source = this.audioContext.createBufferSource();
            const gainNode = this.audioContext.createGain();
            
            source.buffer = buffer;
            source.connect(gainNode);
            gainNode.connect(this.audioContext.destination);
            
            gainNode.gain.value = options.volume || 0.5;
            source.start();
            
            return source;
        } catch (error) {
            console.warn(`Audio playback failed: ${filename}`, error);
            return null;
        }
    }
    
    // Get loading statistics
    getStats() {
        return {
            loaded: this.loadedBuffers.size,
            loading: this.loadingPromises.size,
            totalCritical: this.priorities.critical?.length || 0,
            totalImportant: this.priorities.important?.length || 0,
            totalBackground: this.priorities.background?.length || 0
        };
    }
}

// Global instance
window.progressiveAudioLoader = new ProgressiveAudioLoader();

// Export for compatibility with existing audio engine
if (window.CasinoAudioEngine) {
    window.CasinoAudioEngine.prototype.progressiveLoader = window.progressiveAudioLoader;
}
