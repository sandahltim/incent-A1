// audio-controls.js
// Interactive Audio Control Interface for Vegas Casino
// Version: 3.0.0 - Professional Audio Controls

class AudioControls {
    constructor(audioEngine) {
        this.audioEngine = audioEngine || window.casinoAudio;
        this.container = null;
        this.visualizer = null;
        this.visualizerBars = [];
        this.isCollapsed = false;
        
        this.presets = {
            immersive: {
                name: 'Immersive',
                settings: {
                    masterVolume: 1.0,
                    effectsVolume: 0.9,
                    ambientVolume: 0.5,
                    uiVolume: 0.7,
                    musicVolume: 0.4,
                    spatialAudio: true,
                    reverb: true
                }
            },
            balanced: {
                name: 'Balanced',
                settings: {
                    masterVolume: 0.8,
                    effectsVolume: 0.7,
                    ambientVolume: 0.3,
                    uiVolume: 0.6,
                    musicVolume: 0.3,
                    spatialAudio: true,
                    reverb: false
                }
            },
            quiet: {
                name: 'Quiet',
                settings: {
                    masterVolume: 0.4,
                    effectsVolume: 0.5,
                    ambientVolume: 0.2,
                    uiVolume: 0.4,
                    musicVolume: 0.1,
                    spatialAudio: false,
                    reverb: false
                }
            },
            effects: {
                name: 'Effects Only',
                settings: {
                    masterVolume: 0.8,
                    effectsVolume: 1.0,
                    ambientVolume: 0,
                    uiVolume: 0.5,
                    musicVolume: 0,
                    spatialAudio: true,
                    reverb: true
                }
            }
        };
        
        this.init();
    }
    
    init() {
        // Wait for DOM to be ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.createInterface());
        } else {
            this.createInterface();
        }
        
        // Start visualizer
        this.startVisualizer();
    }
    
    createInterface() {
        // Create main container
        this.container = document.createElement('div');
        this.container.className = 'audio-control-panel';
        this.container.innerHTML = this.getTemplate();
        
        // Add to body
        document.body.appendChild(this.container);
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Initialize visualizer bars
        this.initializeVisualizer();
        
        // Update initial values
        this.updateInterface();
        
        // Add keyboard shortcuts
        this.setupKeyboardShortcuts();
    }
    
    getTemplate() {
        const isMuted = this.audioEngine?.preferences?.muted || false;
        const masterVolume = this.audioEngine?.preferences?.masterVolume || 1.0;
        
        return `
            <div class="audio-control-header">
                <button class="audio-toggle-btn ${isMuted ? 'muted' : ''}" id="audio-main-toggle">
                    <span class="audio-icon">${isMuted ? '🔇' : '🔊'}</span>
                </button>
                <button class="audio-collapse-btn" id="audio-collapse">⚙️</button>
            </div>
            
            <div class="audio-controls-content">
                <!-- Master Volume -->
                <div class="volume-control">
                    <div class="volume-label">
                        <span>Master Volume</span>
                        <span class="volume-value" id="master-volume-value">${Math.round(masterVolume * 100)}%</span>
                    </div>
                    <div class="volume-slider-container">
                        <div class="volume-fill" id="master-volume-fill" style="width: ${masterVolume * 100}%"></div>
                        <input type="range" class="volume-slider" id="master-volume" 
                               min="0" max="100" value="${masterVolume * 100}">
                    </div>
                </div>
                
                <!-- Audio Visualizer -->
                <div class="audio-visualizer" id="audio-visualizer">
                    ${Array(16).fill('<div class="visualizer-bar"></div>').join('')}
                </div>
                
                <!-- Category Controls -->
                <div class="audio-categories">
                    <div class="audio-category">
                        <div class="category-icon">🎰</div>
                        <div class="volume-control">
                            <div class="volume-label">
                                <span>Effects</span>
                                <span class="volume-value" id="effects-volume-value">80%</span>
                            </div>
                            <div class="volume-slider-container">
                                <div class="volume-fill" id="effects-volume-fill" style="width: 80%"></div>
                                <input type="range" class="volume-slider" id="effects-volume" 
                                       min="0" max="100" value="80">
                            </div>
                        </div>
                    </div>
                    
                    <div class="audio-category">
                        <div class="category-icon">🎵</div>
                        <div class="volume-control">
                            <div class="volume-label">
                                <span>Ambient</span>
                                <span class="volume-value" id="ambient-volume-value">40%</span>
                            </div>
                            <div class="volume-slider-container">
                                <div class="volume-fill" id="ambient-volume-fill" style="width: 40%"></div>
                                <input type="range" class="volume-slider" id="ambient-volume" 
                                       min="0" max="100" value="40">
                            </div>
                        </div>
                    </div>
                    
                    <div class="audio-category">
                        <div class="category-icon">🔔</div>
                        <div class="volume-control">
                            <div class="volume-label">
                                <span>UI Sounds</span>
                                <span class="volume-value" id="ui-volume-value">70%</span>
                            </div>
                            <div class="volume-slider-container">
                                <div class="volume-fill" id="ui-volume-fill" style="width: 70%"></div>
                                <input type="range" class="volume-slider" id="ui-volume" 
                                       min="0" max="100" value="70">
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Audio Options -->
                <div class="audio-options">
                    <label class="audio-checkbox">
                        <input type="checkbox" id="spatial-audio" ${this.audioEngine?.preferences?.spatialAudio ? 'checked' : ''}>
                        <span>3D Spatial Audio</span>
                    </label>
                    <label class="audio-checkbox">
                        <input type="checkbox" id="reverb-enabled" ${this.audioEngine?.preferences?.reverb ? 'checked' : ''}>
                        <span>Casino Reverb</span>
                    </label>
                </div>
                
                <!-- Presets -->
                <div class="audio-presets">
                    ${Object.keys(this.presets).map(key => 
                        `<button class="preset-btn" data-preset="${key}">${this.presets[key].name}</button>`
                    ).join('')}
                </div>
            </div>
        `;
    }
    
    setupEventListeners() {
        // Main toggle button
        const toggleBtn = this.container.querySelector('#audio-main-toggle');
        toggleBtn?.addEventListener('click', () => this.toggleMute());
        
        // Collapse button
        const collapseBtn = this.container.querySelector('#audio-collapse');
        collapseBtn?.addEventListener('click', () => this.toggleCollapse());
        
        // Master volume
        const masterVolume = this.container.querySelector('#master-volume');
        masterVolume?.addEventListener('input', (e) => this.updateMasterVolume(e.target.value));
        
        // Category volumes
        const effectsVolume = this.container.querySelector('#effects-volume');
        effectsVolume?.addEventListener('input', (e) => this.updateChannelVolume('effects', e.target.value));
        
        const ambientVolume = this.container.querySelector('#ambient-volume');
        ambientVolume?.addEventListener('input', (e) => this.updateChannelVolume('ambient', e.target.value));
        
        const uiVolume = this.container.querySelector('#ui-volume');
        uiVolume?.addEventListener('input', (e) => this.updateChannelVolume('ui', e.target.value));
        
        // Options
        const spatialAudio = this.container.querySelector('#spatial-audio');
        spatialAudio?.addEventListener('change', (e) => this.toggleSpatialAudio(e.target.checked));
        
        const reverb = this.container.querySelector('#reverb-enabled');
        reverb?.addEventListener('change', (e) => this.toggleReverb(e.target.checked));
        
        // Presets
        const presetBtns = this.container.querySelectorAll('.preset-btn');
        presetBtns.forEach(btn => {
            btn.addEventListener('click', () => this.applyPreset(btn.dataset.preset));
        });
    }
    
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // M - Toggle mute
            if (e.key === 'm' || e.key === 'M') {
                if (!e.target.matches('input, textarea')) {
                    this.toggleMute();
                }
            }
            
            // Arrow keys for volume (when control panel is focused)
            if (this.container.contains(document.activeElement)) {
                if (e.key === 'ArrowUp') {
                    this.adjustMasterVolume(5);
                } else if (e.key === 'ArrowDown') {
                    this.adjustMasterVolume(-5);
                }
            }
        });
    }
    
    toggleMute() {
        if (!this.audioEngine) return;
        
        const isMuted = this.audioEngine.toggleMute();
        
        // Update UI
        const toggleBtn = this.container.querySelector('#audio-main-toggle');
        const icon = toggleBtn?.querySelector('.audio-icon');
        
        if (toggleBtn) {
            toggleBtn.classList.toggle('muted', isMuted);
        }
        
        if (icon) {
            icon.textContent = isMuted ? '🔇' : '🔊';
        }
        
        // Show notification
        this.showNotification(isMuted ? 'Audio Muted' : 'Audio Enabled');
    }
    
    toggleCollapse() {
        this.isCollapsed = !this.isCollapsed;
        this.container.classList.toggle('collapsed', this.isCollapsed);
        
        const collapseBtn = this.container.querySelector('#audio-collapse');
        if (collapseBtn) {
            collapseBtn.textContent = this.isCollapsed ? '🔊' : '⚙️';
        }
    }
    
    updateMasterVolume(value) {
        const volume = value / 100;
        
        if (this.audioEngine) {
            this.audioEngine.setMasterVolume(volume);
        }
        
        // Update UI
        const valueLabel = this.container.querySelector('#master-volume-value');
        const fill = this.container.querySelector('#master-volume-fill');
        
        if (valueLabel) valueLabel.textContent = `${Math.round(value)}%`;
        if (fill) fill.style.width = `${value}%`;
        
        // Visual feedback
        this.createSoundWave();
    }
    
    updateChannelVolume(channel, value) {
        const volume = value / 100;
        
        if (this.audioEngine) {
            this.audioEngine.setChannelVolume(channel, volume);
        }
        
        // Update UI
        const valueLabel = this.container.querySelector(`#${channel}-volume-value`);
        const fill = this.container.querySelector(`#${channel}-volume-fill`);
        
        if (valueLabel) valueLabel.textContent = `${Math.round(value)}%`;
        if (fill) fill.style.width = `${value}%`;
    }
    
    adjustMasterVolume(delta) {
        const slider = this.container.querySelector('#master-volume');
        if (slider) {
            const newValue = Math.max(0, Math.min(100, parseInt(slider.value) + delta));
            slider.value = newValue;
            this.updateMasterVolume(newValue);
        }
    }
    
    toggleSpatialAudio(enabled) {
        if (this.audioEngine) {
            this.audioEngine.setSpatialAudio(enabled);
            this.showNotification(`3D Audio ${enabled ? 'Enabled' : 'Disabled'}`);
        }
    }
    
    async toggleReverb(enabled) {
        if (this.audioEngine) {
            await this.audioEngine.setReverb(enabled);
            this.showNotification(`Reverb ${enabled ? 'Enabled' : 'Disabled'}`);
            
            // Add visual effect
            this.toggleReverbIndicator(enabled);
        }
    }
    
    toggleReverbIndicator(enabled) {
        let indicator = document.querySelector('.reverb-indicator');
        
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'reverb-indicator';
            document.body.appendChild(indicator);
        }
        
        indicator.classList.toggle('reverb-active', enabled);
    }
    
    applyPreset(presetName) {
        const preset = this.presets[presetName];
        if (!preset || !this.audioEngine) return;
        
        // Apply settings
        Object.entries(preset.settings).forEach(([key, value]) => {
            if (key.includes('Volume')) {
                if (key === 'masterVolume') {
                    this.audioEngine.setMasterVolume(value);
                } else {
                    const channel = key.replace('Volume', '');
                    this.audioEngine.setChannelVolume(channel, value);
                }
            } else if (key === 'spatialAudio') {
                this.audioEngine.setSpatialAudio(value);
            } else if (key === 'reverb') {
                this.audioEngine.setReverb(value);
            }
        });
        
        // Update UI
        this.updateInterface();
        
        // Highlight active preset
        const presetBtns = this.container.querySelectorAll('.preset-btn');
        presetBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.preset === presetName);
        });
        
        // Show notification
        this.showNotification(`Preset: ${preset.name}`);
    }
    
    updateInterface() {
        if (!this.audioEngine) return;
        
        const prefs = this.audioEngine.preferences;
        
        // Update sliders
        const masterSlider = this.container.querySelector('#master-volume');
        if (masterSlider) {
            masterSlider.value = prefs.masterVolume * 100;
            this.updateMasterVolume(masterSlider.value);
        }
        
        const effectsSlider = this.container.querySelector('#effects-volume');
        if (effectsSlider) {
            effectsSlider.value = prefs.effectsVolume * 100;
            this.updateChannelVolume('effects', effectsSlider.value);
        }
        
        const ambientSlider = this.container.querySelector('#ambient-volume');
        if (ambientSlider) {
            ambientSlider.value = prefs.ambientVolume * 100;
            this.updateChannelVolume('ambient', ambientSlider.value);
        }
        
        const uiSlider = this.container.querySelector('#ui-volume');
        if (uiSlider) {
            uiSlider.value = prefs.uiVolume * 100;
            this.updateChannelVolume('ui', uiSlider.value);
        }
        
        // Update checkboxes
        const spatialCheckbox = this.container.querySelector('#spatial-audio');
        if (spatialCheckbox) spatialCheckbox.checked = prefs.spatialAudio;
        
        const reverbCheckbox = this.container.querySelector('#reverb-enabled');
        if (reverbCheckbox) reverbCheckbox.checked = prefs.reverb;
    }
    
    initializeVisualizer() {
        this.visualizer = this.container.querySelector('#audio-visualizer');
        if (this.visualizer) {
            this.visualizerBars = this.visualizer.querySelectorAll('.visualizer-bar');
        }
    }
    
    startVisualizer() {
        const animate = () => {
            this.updateVisualizer();
            requestAnimationFrame(animate);
        };
        
        requestAnimationFrame(animate);
    }
    
    updateVisualizer() {
        if (!this.audioEngine || !this.visualizerBars.length) return;
        
        const data = this.audioEngine.getVisualizationData();
        if (!data) return;
        
        // Update bars based on frequency data
        const barCount = this.visualizerBars.length;
        const step = Math.floor(data.length / barCount);
        
        this.visualizerBars.forEach((bar, index) => {
            const value = data[index * step] || 0;
            const height = (value / 255) * 100;
            bar.style.setProperty('--bar-height', `${height}%`);
            bar.style.height = `${height}%`;
        });
    }
    
    createSoundWave() {
        const indicator = document.createElement('div');
        indicator.className = 'sound-indicator';
        indicator.style.left = `${this.container.offsetLeft + 25}px`;
        indicator.style.top = `${this.container.offsetTop + 25}px`;
        
        const ring = document.createElement('div');
        ring.className = 'sound-ring';
        indicator.appendChild(ring);
        
        document.body.appendChild(indicator);
        
        setTimeout(() => {
            indicator.remove();
        }, 600);
    }
    
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `audio-notification audio-${type}`;
        notification.style.cssText = `
            position: fixed;
            bottom: 100px;
            right: 20px;
            background: ${type === 'error' ? '#FF4757' : 'rgba(255, 215, 0, 0.9)'};
            color: ${type === 'error' ? 'white' : 'black'};
            padding: 10px 20px;
            border-radius: 25px;
            font-size: 14px;
            font-weight: bold;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
            z-index: 10003;
            animation: slide-in-right 0.3s ease-out;
        `;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slide-out-right 0.3s ease-in forwards';
            setTimeout(() => notification.remove(), 300);
        }, 2000);
    }
    
    // Test audio system
    async testAudioSystem() {
        if (!this.audioEngine) return;
        
        this.showNotification('Testing Audio System...');
        
        // Play test sequence
        await this.audioEngine.playSequence([
            'buttonClick',
            'coinSingle',
            'winSmall',
            'winMedium',
            'winBig'
        ], 500);
        
        this.showNotification('Audio Test Complete!', 'success');
    }
    
    // Get audio status
    getStatus() {
        if (!this.audioEngine) {
            return { error: 'Audio engine not initialized' };
        }
        
        return this.audioEngine.getStatus();
    }
}

// Initialize audio controls when audio engine is ready
document.addEventListener('DOMContentLoaded', () => {
    // Wait a bit for audio engine to initialize
    setTimeout(() => {
        if (window.casinoAudio) {
            window.audioControls = new AudioControls(window.casinoAudio);
            console.log('🎛️ Audio controls initialized');
        }
    }, 1000);
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioControls;
}