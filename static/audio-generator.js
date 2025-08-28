// audio-generator.js
// Professional Audio Synthesis Generator for Vegas Casino
// Creates all missing audio files using Web Audio API

class AudioGenerator {
    constructor() {
        this.context = null;
        this.sampleRate = 44100;
        this.generatedAudios = new Map();
        
        // Initialize audio context
        this.initAudioContext();
    }

    async initAudioContext() {
        try {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.context = new AudioContext();
            
            if (this.context.state === 'suspended') {
                await this.context.resume();
            }
        } catch (error) {
            console.error('Failed to initialize audio context:', error);
        }
    }

    // Generate sine wave
    generateSine(frequency, duration, options = {}) {
        const {
            volume = 0.3,
            attack = 0.01,
            decay = 0.1,
            sustain = 0.7,
            release = 0.3,
            modulation = null
        } = options;

        const sampleCount = Math.floor(duration * this.sampleRate);
        const buffer = this.context.createBuffer(2, sampleCount, this.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            
            for (let i = 0; i < sampleCount; i++) {
                const time = i / this.sampleRate;
                const progress = i / sampleCount;
                
                // ADSR envelope
                let envelope = 1;
                const attackTime = attack * duration;
                const decayTime = attackTime + (decay * duration);
                const releaseTime = (1 - release) * duration;
                
                if (time < attackTime) {
                    envelope = time / attackTime;
                } else if (time < decayTime) {
                    envelope = 1 - ((time - attackTime) / (decay * duration)) * (1 - sustain);
                } else if (time > releaseTime) {
                    envelope = sustain * (1 - (time - releaseTime) / (release * duration));
                } else {
                    envelope = sustain;
                }
                
                // Apply modulation if specified
                let freq = frequency;
                if (modulation) {
                    freq += modulation.depth * Math.sin(2 * Math.PI * modulation.frequency * time);
                }
                
                // Generate sample
                const sample = Math.sin(2 * Math.PI * freq * time) * envelope * volume;
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    // Generate noise (white/pink/brown)
    generateNoise(duration, type = 'white', options = {}) {
        const { volume = 0.2, filterFreq = null } = options;
        const sampleCount = Math.floor(duration * this.sampleRate);
        const buffer = this.context.createBuffer(2, sampleCount, this.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            let b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0; // for pink noise
            
            for (let i = 0; i < sampleCount; i++) {
                let sample;
                
                switch (type) {
                    case 'pink':
                        // Pink noise (1/f)
                        const white = Math.random() * 2 - 1;
                        b0 = 0.99886 * b0 + white * 0.0555179;
                        b1 = 0.99332 * b1 + white * 0.0750759;
                        b2 = 0.96900 * b2 + white * 0.1538520;
                        b3 = 0.86650 * b3 + white * 0.3104856;
                        b4 = 0.55000 * b4 + white * 0.5329522;
                        b5 = -0.7616 * b5 - white * 0.0168980;
                        sample = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362;
                        sample *= 0.11;
                        b6 = white * 0.115926;
                        break;
                        
                    case 'brown':
                        // Brown noise
                        sample = (Math.random() * 2 - 1);
                        sample = (b0 + (0.02 * sample)) / 1.02;
                        b0 = sample;
                        sample *= 3.5;
                        break;
                        
                    default:
                        // White noise
                        sample = (Math.random() * 2 - 1);
                }
                
                channelData[i] = sample * volume;
            }
        }
        
        return buffer;
    }

    // Generate complex casino sounds
    async generateUIHover() {
        const duration = 0.1;
        const buffer = this.context.createBuffer(2, Math.floor(duration * this.sampleRate), this.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            const sampleCount = channelData.length;
            
            for (let i = 0; i < sampleCount; i++) {
                const time = i / this.sampleRate;
                const progress = i / sampleCount;
                
                // Soft bell-like tone
                const freq1 = 800 + (200 * Math.exp(-time * 10));
                const freq2 = 1200 + (300 * Math.exp(-time * 15));
                
                const envelope = Math.exp(-time * 8);
                const sample = (
                    Math.sin(2 * Math.PI * freq1 * time) * 0.4 +
                    Math.sin(2 * Math.PI * freq2 * time) * 0.2
                ) * envelope * 0.3;
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    async generateSlotLeverPull() {
        const duration = 0.8;
        const buffer = this.context.createBuffer(2, Math.floor(duration * this.sampleRate), this.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            const sampleCount = channelData.length;
            
            for (let i = 0; i < sampleCount; i++) {
                const time = i / this.sampleRate;
                
                let sample = 0;
                
                // Mechanical click at start
                if (time < 0.1) {
                    const clickEnv = Math.exp(-time * 30);
                    sample += (Math.random() * 2 - 1) * clickEnv * 0.3;
                    sample += Math.sin(2 * Math.PI * 150 * time) * clickEnv * 0.2;
                }
                
                // Lever spring sound
                if (time > 0.1 && time < 0.6) {
                    const springTime = time - 0.1;
                    const springFreq = 80 + 40 * Math.sin(2 * Math.PI * 3 * springTime);
                    const springEnv = Math.exp(-springTime * 3);
                    sample += Math.sin(2 * Math.PI * springFreq * springTime) * springEnv * 0.25;
                }
                
                // Final thunk
                if (time > 0.6) {
                    const thunkTime = time - 0.6;
                    const thunkEnv = Math.exp(-thunkTime * 15);
                    sample += (Math.random() * 2 - 1) * thunkEnv * 0.4;
                    sample += Math.sin(2 * Math.PI * 60 * thunkTime) * thunkEnv * 0.3;
                }
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    async generateSlotReelStop() {
        const duration = 0.3;
        const buffer = this.context.createBuffer(2, Math.floor(duration * this.sampleRate), this.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            const sampleCount = channelData.length;
            
            for (let i = 0; i < sampleCount; i++) {
                const time = i / this.sampleRate;
                
                // Mechanical stop sound
                const envelope = Math.exp(-time * 12);
                let sample = (Math.random() * 2 - 1) * envelope * 0.3;
                
                // Add some metallic resonance
                sample += Math.sin(2 * Math.PI * 200 * time) * envelope * 0.15;
                sample += Math.sin(2 * Math.PI * 400 * time) * envelope * 0.1;
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    async generateDiceRoll() {
        const duration = 0.6;
        const buffer = this.context.createBuffer(2, Math.floor(duration * this.sampleRate), this.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            const sampleCount = channelData.length;
            
            for (let i = 0; i < sampleCount; i++) {
                const time = i / this.sampleRate;
                let sample = 0;
                
                // Random impacts for dice bouncing
                const impactRate = 8 * (1 - time / duration); // Slowing down
                if (Math.random() < (impactRate / this.sampleRate) * 100) {
                    const impactEnv = Math.exp(-((time % 0.1) * 20));
                    sample += (Math.random() * 2 - 1) * impactEnv * 0.4;
                    
                    // Add some tone for dice material
                    const freq = 300 + Math.random() * 200;
                    sample += Math.sin(2 * Math.PI * freq * time) * impactEnv * 0.2;
                }
                
                // General rolling sound
                const rollEnv = 1 - Math.pow(time / duration, 2);
                sample += (Math.random() * 2 - 1) * rollEnv * 0.1;
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    async generateWinSound(tier = 'small') {
        const durations = { tiny: 0.3, small: 0.5, medium: 0.8, big: 1.2, huge: 1.5, mega: 2.0, jackpot: 3.0 };
        const duration = durations[tier] || 0.5;
        
        const buffer = this.context.createBuffer(2, Math.floor(duration * this.sampleRate), this.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            const sampleCount = channelData.length;
            
            for (let i = 0; i < sampleCount; i++) {
                const time = i / this.sampleRate;
                const progress = time / duration;
                
                let sample = 0;
                
                // Rising arpeggio
                const notes = [261.63, 329.63, 392.00, 523.25, 659.25]; // C major arpeggio
                const noteIndex = Math.floor(progress * notes.length);
                if (noteIndex < notes.length) {
                    const noteFreq = notes[noteIndex];
                    const noteTime = (progress * notes.length) % 1;
                    const noteEnv = Math.exp(-noteTime * (tier === 'jackpot' ? 2 : 4));
                    
                    sample += Math.sin(2 * Math.PI * noteFreq * time) * noteEnv * 0.3;
                    sample += Math.sin(2 * Math.PI * noteFreq * 2 * time) * noteEnv * 0.1; // Octave
                }
                
                // Add sparkle for bigger wins
                if (tier !== 'tiny' && tier !== 'small') {
                    const sparkleRate = tier === 'jackpot' ? 50 : 20;
                    if (Math.random() < (sparkleRate / this.sampleRate)) {
                        const sparkleFreq = 1000 + Math.random() * 2000;
                        const sparkleEnv = Math.exp(-((time % 0.05) * 30));
                        sample += Math.sin(2 * Math.PI * sparkleFreq * time) * sparkleEnv * 0.15;
                    }
                }
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    async generateCoinSound(type = 'single') {
        const durations = { single: 0.2, drop: 0.3, shower: 1.5, cascade: 2.5 };
        const duration = durations[type] || 0.3;
        
        const buffer = this.context.createBuffer(2, Math.floor(duration * this.sampleRate), this.sampleRate);
        
        for (let channel = 0; channel < 2; channel++) {
            const channelData = buffer.getChannelData(channel);
            const sampleCount = channelData.length;
            
            for (let i = 0; i < sampleCount; i++) {
                const time = i / this.sampleRate;
                let sample = 0;
                
                if (type === 'single' || type === 'drop') {
                    // Single coin drop
                    const envelope = Math.exp(-time * 8);
                    const freq = 800 + 400 * Math.exp(-time * 20);
                    sample = Math.sin(2 * Math.PI * freq * time) * envelope * 0.4;
                    
                    // Add metallic ring
                    sample += Math.sin(2 * Math.PI * (freq * 1.5) * time) * envelope * 0.2;
                } else {
                    // Multiple coins
                    const density = type === 'cascade' ? 100 : 30;
                    if (Math.random() < (density / this.sampleRate)) {
                        const coinEnv = Math.exp(-((time % 0.1) * 15));
                        const freq = 600 + Math.random() * 800;
                        sample += Math.sin(2 * Math.PI * freq * time) * coinEnv * 0.2;
                    }
                }
                
                channelData[i] = sample;
            }
        }
        
        return buffer;
    }

    // Audio conversion utility
    audioBufferToWav(buffer) {
        const length = buffer.length;
        const numberOfChannels = buffer.numberOfChannels;
        const sampleRate = buffer.sampleRate;
        const arrayBuffer = new ArrayBuffer(44 + length * numberOfChannels * 2);
        const view = new DataView(arrayBuffer);
        
        // WAV header
        const writeString = (offset, string) => {
            for (let i = 0; i < string.length; i++) {
                view.setUint8(offset + i, string.charCodeAt(i));
            }
        };
        
        writeString(0, 'RIFF');
        view.setUint32(4, 36 + length * numberOfChannels * 2, true);
        writeString(8, 'WAVE');
        writeString(12, 'fmt ');
        view.setUint32(16, 16, true);
        view.setUint16(20, 1, true);
        view.setUint16(22, numberOfChannels, true);
        view.setUint32(24, sampleRate, true);
        view.setUint32(28, sampleRate * numberOfChannels * 2, true);
        view.setUint16(32, numberOfChannels * 2, true);
        view.setUint16(34, 16, true);
        writeString(36, 'data');
        view.setUint32(40, length * numberOfChannels * 2, true);
        
        // Convert float32 to int16
        const channelData = [];
        for (let channel = 0; channel < numberOfChannels; channel++) {
            channelData.push(buffer.getChannelData(channel));
        }
        
        let offset = 44;
        for (let i = 0; i < length; i++) {
            for (let channel = 0; channel < numberOfChannels; channel++) {
                const sample = Math.max(-1, Math.min(1, channelData[channel][i]));
                view.setInt16(offset, sample * 0x7FFF, true);
                offset += 2;
            }
        }
        
        return arrayBuffer;
    }

    // Download generated audio
    downloadAudio(buffer, filename) {
        const wavData = this.audioBufferToWav(buffer);
        const blob = new Blob([wavData], { type: 'audio/wav' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    // Generate all missing sounds
    async generateAllSounds() {
        if (!this.context) {
            console.error('Audio context not initialized');
            return;
        }

        const soundDefinitions = {
            'ui-hover.mp3': () => this.generateUIHover(),
            'ui-disabled.mp3': () => this.generateSine(200, 0.15, { volume: 0.2 }),
            'modal-open.mp3': () => this.generateSine(440, 0.3, { attack: 0.1, release: 0.2 }),
            'modal-close.mp3': () => this.generateSine(330, 0.2, { attack: 0.05, release: 0.15 }),
            'tab-switch.mp3': () => this.generateSine(523, 0.15, { volume: 0.25 }),
            
            'slot-lever-pull.mp3': () => this.generateSlotLeverPull(),
            'slot-reel-start.mp3': () => this.generateSine(110, 0.5, { modulation: { frequency: 2, depth: 10 } }),
            'slot-reel-stop-1.mp3': () => this.generateSlotReelStop(),
            'slot-reel-stop-2.mp3': () => this.generateSlotReelStop(),
            'slot-reel-stop-3.mp3': () => this.generateSlotReelStop(),
            'slot-near-miss.mp3': () => this.generateSine(220, 0.5, { modulation: { frequency: 0.5, depth: 20 } }),
            
            'scratch-start.mp3': () => this.generateNoise(0.2, 'pink', { volume: 0.3 }),
            'scratch-loop.mp3': () => this.generateNoise(0.5, 'pink', { volume: 0.2 }),
            'scratch-reveal.mp3': () => this.generateSine(880, 0.4, { attack: 0.1 }),
            'scratch-complete.mp3': () => this.generateWinSound('small'),
            
            'roulette-spin.mp3': () => this.generateNoise(2.0, 'brown', { volume: 0.15 }),
            'roulette-ball-roll.mp3': () => this.generateSine(400, 1.0, { modulation: { frequency: 8, depth: 50 } }),
            'roulette-ball-bounce.mp3': () => this.generateNoise(0.8, 'white', { volume: 0.2 }),
            'roulette-ball-drop.mp3': () => this.generateSine(200, 0.4, { attack: 0.05, release: 0.35 }),
            'roulette-click.mp3': () => this.generateSine(800, 0.1, { volume: 0.2 }),
            
            'wheel-start.mp3': () => this.generateSine(150, 0.5, { attack: 0.2 }),
            'wheel-spin.mp3': () => this.generateNoise(1.0, 'pink', { volume: 0.15 }),
            'wheel-tick.mp3': () => this.generateSine(600, 0.05, { volume: 0.3 }),
            'wheel-slowdown.mp3': () => this.generateNoise(2.0, 'pink', { volume: 0.1 }),
            'wheel-stop.mp3': () => this.generateSine(300, 0.5, { attack: 0.1, release: 0.4 }),
            
            'dice-shake.mp3': () => this.generateNoise(0.8, 'white', { volume: 0.2 }),
            'dice-throw.mp3': () => this.generateNoise(0.4, 'pink', { volume: 0.25 }),
            'dice-roll-1.mp3': () => this.generateDiceRoll(),
            'dice-roll-2.mp3': () => this.generateDiceRoll(),
            'dice-land.mp3': () => this.generateSine(300, 0.2, { volume: 0.3 }),
            'dice-settle.mp3': () => this.generateSine(200, 0.3, { attack: 0.1, release: 0.2 }),
            
            'win-tiny.mp3': () => this.generateWinSound('tiny'),
            'win-small.mp3': () => this.generateWinSound('small'),
            'win-medium.mp3': () => this.generateWinSound('medium'),
            'win-big.mp3': () => this.generateWinSound('big'),
            'win-huge.mp3': () => this.generateWinSound('huge'),
            'win-mega.mp3': () => this.generateWinSound('mega'),
            
            'coin-single.mp3': () => this.generateCoinSound('single'),
            'coin-shower.mp3': () => this.generateCoinSound('shower'),
            'coin-cascade.mp3': () => this.generateCoinSound('cascade'),
            'cash-register.mp3': () => this.generateSine(523, 0.6, { attack: 0.1 }),
            
            'fanfare-1.mp3': () => this.generateWinSound('medium'),
            'fanfare-2.mp3': () => this.generateWinSound('big'),
            'fanfare-3.mp3': () => this.generateWinSound('huge'),
            'applause.mp3': () => this.generateNoise(3.0, 'pink', { volume: 0.2 }),
            'cheer.mp3': () => this.generateNoise(2.5, 'white', { volume: 0.25 }),
            'airhorn.mp3': () => this.generateSine(200, 1.0, { volume: 0.4 }),
            
            'casino-ambient-1.mp3': () => this.generateNoise(5.0, 'pink', { volume: 0.1 }),
            'casino-ambient-2.mp3': () => this.generateNoise(5.0, 'brown', { volume: 0.1 }),
            'slot-machines-bg.mp3': () => this.generateNoise(5.0, 'pink', { volume: 0.08 }),
            'crowd-murmur.mp3': () => this.generateNoise(5.0, 'brown', { volume: 0.05 }),
            
            'notification-success.mp3': () => this.generateSine(660, 0.4, { attack: 0.1 }),
            'notification-error.mp3': () => this.generateSine(220, 0.3, { volume: 0.3 }),
            'notification-warning.mp3': () => this.generateSine(440, 0.35, { modulation: { frequency: 3, depth: 20 } }),
            'notification-info.mp3': () => this.generateSine(523, 0.25, { volume: 0.3 }),
            
            'swoosh-in.mp3': () => this.generateNoise(0.3, 'pink', { volume: 0.15 }),
            'swoosh-out.mp3': () => this.generateNoise(0.3, 'pink', { volume: 0.15 }),
            'slide-in.mp3': () => this.generateSine(330, 0.4, { attack: 0.2 }),
            'slide-out.mp3': () => this.generateSine(220, 0.4, { attack: 0.2 }),
            'fade-transition.mp3': () => this.generateSine(440, 0.5, { attack: 0.25, release: 0.25 })
        };

        console.log('🎵 Starting audio generation...');
        let count = 0;
        
        for (const [filename, generator] of Object.entries(soundDefinitions)) {
            try {
                console.log(`Generating ${filename}...`);
                const buffer = await generator();
                this.generatedAudios.set(filename, buffer);
                count++;
            } catch (error) {
                console.error(`Failed to generate ${filename}:`, error);
            }
        }
        
        console.log(`✅ Generated ${count} audio files`);
        return count;
    }

    // Download all generated sounds
    downloadAll() {
        console.log('📥 Downloading all generated sounds...');
        
        for (const [filename, buffer] of this.generatedAudios) {
            this.downloadAudio(buffer, filename);
        }
        
        console.log('✅ All downloads initiated');
    }

    // Get generated audio as blob URL for immediate use
    getAudioBlobUrl(filename) {
        const buffer = this.generatedAudios.get(filename);
        if (!buffer) return null;
        
        const wavData = this.audioBufferToWav(buffer);
        const blob = new Blob([wavData], { type: 'audio/wav' });
        return URL.createObjectURL(blob);
    }
}

// Global instance for easy access
window.audioGenerator = new AudioGenerator();

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AudioGenerator;
}