// vegas-casino.js
// Version: 2.0.0 - Vegas Casino Supreme Edition
// Professional casino gaming experience with enhanced minigames and slot machines

class VegasCasino {
    constructor() {
        this.soundEnabled = true;
        this.isSpinning = false;
        this.jackpotThreshold = 100;
        this.animations = new Map();
        this.gameState = {
            credits: 0,
            level: 1,
            totalWins: 0,
            currentStreak: 0
        };
        
        // Use professional audio engine if available
        this.audioEngine = window.casinoAudio || null;
        
        // Legacy sound fallback
        this.sounds = {
            coin: new Audio('/static/coin-drop.mp3'),
            jackpot: new Audio('/static/jackpot-horn.mp3'),
            slot: new Audio('/static/slot-pull.mp3'),
            win: new Audio('/static/casino-win.mp3'),
            spin: new Audio('/static/reel-spin.mp3')
        };
        
        this.initializeSounds();
        this.setupEventListeners();
        this.loadGameState();
        this.initializeAudioEngine();
    }
    
    initializeSounds() {
        Object.values(this.sounds).forEach(audio => {
            audio.volume = 0.6;
            audio.preload = 'auto';
        });
    }
    
    async playSound(soundName, volume = 0.6) {
        if (!this.soundEnabled) return;
        
        // Use professional audio engine if available
        if (this.audioEngine) {
            const soundMap = {
                coin: 'coinDrop',
                jackpot: 'winJackpot',
                slot: 'slotLeverPull',
                win: 'winMedium',
                spin: 'slotReelSpin'
            };
            
            const engineSound = soundMap[soundName] || soundName;
            await this.audioEngine.play(engineSound, {
                volume: volume,
                channel: 'effects'
            });
        } else if (this.sounds[soundName]) {
            // Fallback to legacy sounds
            try {
                const audio = this.sounds[soundName];
                audio.volume = volume;
                audio.currentTime = 0;
                await audio.play();
            } catch (error) {
                console.warn(`Sound playback failed for ${soundName}:`, error);
            }
        }
    }
    
    // Enhanced Slot Machine with proper reel mechanics and spatial audio
    async spinSlotMachine(reels, duration = 3000) {
        if (this.isSpinning) return false;
        
        this.isSpinning = true;
        
        // Enhanced slot pull with mechanical sounds
        if (this.audioEngine) {
            await this.audioEngine.playSequence([
                'slotLeverPull',
                { name: 'slotReelStart', options: { delay: 200 } }
            ]);
        } else {
            this.playSound('slot');
        }
        
        const reelElements = document.querySelectorAll('.reel');
        const slotMachine = document.querySelector('.slot-machine');
        
        if (slotMachine) {
            slotMachine.classList.add('spinning');
        }
        
        // Start spinning animation
        reelElements.forEach((reel, index) => {
            reel.classList.add('spinning');
            this.animateReel(reel, duration + (index * 500));
        });
        
        // Stop reels sequentially
        for (let i = 0; i < reelElements.length; i++) {
            await this.stopReel(reelElements[i], reels[i], i * 500 + duration);
        }
        
        if (slotMachine) {
            slotMachine.classList.remove('spinning');
        }
        
        this.isSpinning = false;
        return true;
    }
    
    animateReel(reelElement, duration) {
        const symbols = ['🍒', '🍋', '🍊', '🍇', '💎', '⭐', '🔔', '💰'];
        let animationId;
        let startTime;
        let tickCount = 0;
        
        const animate = (currentTime) => {
            if (!startTime) startTime = currentTime;
            const elapsed = currentTime - startTime;
            
            if (elapsed < duration) {
                const randomSymbol = symbols[Math.floor(Math.random() * symbols.length)];
                const container = reelElement.querySelector('.symbol-container');
                if (container) {
                    container.textContent = randomSymbol;
                    
                    // Add reel tick sounds
                    if (this.audioEngine && tickCount % 3 === 0) {
                        this.audioEngine.playFromPool('buttonClick', 0.2);
                    }
                    tickCount++;
                }
                animationId = requestAnimationFrame(animate);
            }
        };
        
        animationId = requestAnimationFrame(animate);
        this.animations.set(reelElement, animationId);
    }
    
    async stopReel(reelElement, finalValue, delay) {
        await this.sleep(delay);
        
        // Cancel animation
        const animationId = this.animations.get(reelElement);
        if (animationId) {
            cancelAnimationFrame(animationId);
            this.animations.delete(reelElement);
        }
        
        // Set final value
        const container = reelElement.querySelector('.symbol-container');
        if (container) {
            container.textContent = finalValue;
        }
        
        reelElement.classList.remove('spinning');
        reelElement.classList.add('stopping');
        
        // Enhanced reel stop sound with positional audio
        const reelIndex = parseInt(reelElement.dataset.reelIndex || 0);
        if (this.audioEngine) {
            const stopSound = `slotReelStop${Math.min(3, reelIndex + 1)}`;
            await this.audioEngine.play(stopSound, {
                volume: 0.7,
                pan: (reelIndex - 1) * 0.4,
                channel: 'effects'
            });
        } else {
            this.playSound('coin');
        }
        
        // Check for jackpot
        if (this.isJackpotValue(finalValue)) {
            this.triggerJackpotEffect(reelElement);
        }
        
        setTimeout(() => {
            reelElement.classList.remove('stopping');
        }, 500);
    }
    
    isJackpotValue(value) {
        return typeof value === 'number' && value >= this.jackpotThreshold;
    }
    
    triggerJackpotEffect(element) {
        // Enhanced jackpot celebration with layered audio
        if (this.audioEngine) {
            this.audioEngine.playLayered([
                { name: 'winJackpot', options: { volume: 1.0 } },
                { name: 'fanfare3', options: { volume: 0.8, delay: 300 } },
                { name: 'coinCascade', options: { volume: 0.7, delay: 800 } },
                { name: 'applause', options: { volume: 0.6, delay: 1500 } }
            ]);
        } else {
            this.playSound('jackpot');
        }
        
        element.classList.add('jackpot-winner');
        
        // Create confetti burst
        this.createConfettiBurst(element);
        
        // Screen flash effect
        document.body.classList.add('jackpot-flash');
        setTimeout(() => {
            document.body.classList.remove('jackpot-flash');
            element.classList.remove('jackpot-winner');
        }, 3000);
    }
    
    createConfettiBurst(centerElement) {
        const rect = centerElement.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;
        
        for (let i = 0; i < 50; i++) {
            setTimeout(() => {
                this.createConfettiPiece(centerX, centerY);
            }, i * 50);
        }
    }
    
    createConfettiPiece(x, y) {
        const confetti = document.createElement('div');
        confetti.className = 'confetti';
        
        const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'];
        confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
        confetti.style.left = x + 'px';
        confetti.style.top = y + 'px';
        confetti.style.position = 'fixed';
        confetti.style.zIndex = '9999';
        
        // Random trajectory
        const angle = Math.random() * Math.PI * 2;
        const velocity = 100 + Math.random() * 100;
        const vx = Math.cos(angle) * velocity;
        const vy = Math.sin(angle) * velocity;
        
        confetti.style.setProperty('--vx', vx + 'px');
        confetti.style.setProperty('--vy', vy + 'px');
        
        document.body.appendChild(confetti);
        
        setTimeout(() => {
            if (confetti.parentNode) {
                confetti.parentNode.removeChild(confetti);
            }
        }, 3000);
    }
    
    // Mini Games System with Enhanced Audio
    async playSlotGame(gameId) {
        const gameConfig = await this.getGameConfig();
        const symbols = ['🍒', '🍋', '⭐', '💎', '🔔'];
        
        // Play slot game initiation sound
        if (this.audioEngine) {
            await this.audioEngine.play('slotLeverPull', {
                volume: 0.7,
                channel: 'effects'
            });
        }
        
        const result = {
            reels: [
                symbols[Math.floor(Math.random() * symbols.length)],
                symbols[Math.floor(Math.random() * symbols.length)],
                symbols[Math.floor(Math.random() * symbols.length)]
            ],
            win: false,
            prize: 0
        };
        
        // Check for wins
        if (result.reels[0] === result.reels[1] && result.reels[1] === result.reels[2]) {
            result.win = true;
            result.prize = this.calculateSlotPrize(result.reels[0], gameConfig);
        } else if (result.reels[0] === result.reels[1] || result.reels[1] === result.reels[2]) {
            result.win = true;
            result.prize = this.calculateSlotPrize(result.reels[0], gameConfig) / 2;
        }
        
        await this.processGameResult(gameId, result);
        return result;
    }
    
    async playScratchGame(gameId) {
        // Play scratch card sound effect
        if (this.audioEngine) {
            await this.audioEngine.playSequence([
                'scratchStart',
                { name: 'scratchLoop', options: { loop: false, duration: 1500 } },
                { name: 'scratchReveal', options: { delay: 1600 } }
            ]);
        }
        
        const prizes = [
            { type: 'points', amount: 5, chance: 40 },
            { type: 'points', amount: 10, chance: 25 },
            { type: 'points', amount: 25, chance: 15 },
            { type: 'bonus', desc: 'Extra Break', chance: 10 },
            { type: 'bonus', desc: 'Gift Card', value: 25, chance: 10 }
        ];
        
        const totalChance = prizes.reduce((sum, prize) => sum + prize.chance, 0);
        const random = Math.random() * totalChance;
        
        let accumulator = 0;
        const selectedPrize = prizes.find(prize => {
            accumulator += prize.chance;
            return random <= accumulator;
        });
        
        const result = {
            win: selectedPrize !== undefined,
            prize: selectedPrize || { type: 'none', amount: 0 }
        };
        
        await this.processGameResult(gameId, result);
        return result;
    }
    
    async playRouletteGame(gameId) {
        // Enhanced roulette sounds
        if (this.audioEngine) {
            await this.audioEngine.playSequence([
                'rouletteSpin',
                { name: 'rouletteBallRoll', options: { loop: false, duration: 2000 } },
                { name: 'rouletteBallBounce', options: { delay: 2100, volume: 0.6 } },
                { name: 'rouletteBallDrop', options: { delay: 2500 } }
            ]);
        }
        
        const numbers = Array.from({length: 37}, (_, i) => i); // 0-36
        const winningNumber = numbers[Math.floor(Math.random() * numbers.length)];
        
        const result = {
            number: winningNumber,
            color: this.getRouletteColor(winningNumber),
            win: false,
            prize: 0
        };
        
        // Simple win condition - even numbers win small prize
        if (winningNumber % 2 === 0 && winningNumber !== 0) {
            result.win = true;
            result.prize = 5;
        }
        
        // Special jackpot numbers
        if ([7, 17, 27].includes(winningNumber)) {
            result.win = true;
            result.prize = 25;
        }
        
        await this.processGameResult(gameId, result);
        return result;
    }
    
    calculateSlotPrize(symbol, config) {
        const prizeMap = {
            '🍒': 5,
            '🍋': 10,
            '⭐': 15,
            '💎': 50,
            '🔔': 100
        };
        return prizeMap[symbol] || 0;
    }
    
    getRouletteColor(number) {
        if (number === 0) return 'green';
        const redNumbers = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36];
        return redNumbers.includes(number) ? 'red' : 'black';
    }
    
    async processGameResult(gameId, result) {
        try {
            const formData = new FormData();
            const csrfToken = this.getCSRFToken();
            if (csrfToken) {
                formData.append('csrf_token', csrfToken);
            }
            
            const response = await fetch(`/play_game/${gameId}`, {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                if (result.win) {
                    this.celebrateWin(result);
                }
                return data;
            }
        } catch (error) {
            console.error('Game processing error:', error);
        }
    }
    
    celebrateWin(result) {
        this.gameState.totalWins++;
        this.gameState.currentStreak++;
        
        // Dynamic win celebration based on prize amount
        if (this.audioEngine) {
            this.audioEngine.playDynamic('win', result.prize, {
                channel: 'effects',
                reverb: true
            });
            
            // Add coin sounds for point wins
            if (result.prize > 0) {
                setTimeout(() => {
                    this.audioEngine.playDynamic('coin', result.prize, {
                        channel: 'effects'
                    });
                }, 500);
            }
        } else {
            // Legacy sound fallback
            if (result.prize >= 25) {
                this.playSound('jackpot');
                this.triggerJackpotEffect(document.body);
            } else {
                this.playSound('win');
            }
        }
        
        this.showWinNotification(result);
        this.saveGameState();
    }
    
    showWinNotification(result) {
        const notification = document.createElement('div');
        notification.className = 'win-notification';
        notification.innerHTML = `
            <div class="win-content">
                <h3>🎉 WINNER! 🎉</h3>
                <p>You won ${result.prize} ${result.prize.type || 'points'}!</p>
            </div>
        `;
        
        notification.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(145deg, #FFD700, #B8860B);
            color: #000;
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(255, 215, 0, 0.5);
            z-index: 10000;
            text-align: center;
            animation: jackpotPulse 1s ease-in-out;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 3000);
    }
    
    // Utility Functions
    async getGameConfig() {
        try {
            const response = await fetch('/api/game-config');
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            console.error('Failed to load game config:', error);
        }
        
        // Default config
        return {
            prizes: {
                points: { amount: 5, chance: 20 },
                bonus: { desc: 'Extra Break', chance: 10 }
            }
        };
    }
    
    getCSRFToken() {
        // Try to get CSRF token from meta tag first, then from any form
        let token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (!token) {
            token = document.querySelector('input[name="csrf_token"]')?.value;
        }
        return token || '';
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
    
    saveGameState() {
        localStorage.setItem('vegasCasinoState', JSON.stringify(this.gameState));
    }
    
    loadGameState() {
        const saved = localStorage.getItem('vegasCasinoState');
        if (saved) {
            try {
                this.gameState = { ...this.gameState, ...JSON.parse(saved) };
            } catch (error) {
                console.warn('Failed to load game state:', error);
            }
        }
    }
    
    async initializeAudioEngine() {
        if (this.audioEngine) {
            // Preload game sounds
            await this.audioEngine.preloadCategory('slots');
            await this.audioEngine.preloadCategory('wins');
            await this.audioEngine.preloadCategory('coins');
            
            // Create audio pools for rapid sounds
            this.audioEngine.createAudioPool('wheelTick', 10);
            this.audioEngine.createAudioPool('diceLand', 5);
        }
    }
    
    setupEventListeners() {
        // Sound toggle with audio engine integration
        document.addEventListener('click', (e) => {
            if (e.target.matches('.sound-toggle')) {
                this.soundEnabled = !this.soundEnabled;
                e.target.textContent = this.soundEnabled ? '🔊' : '🔇';
                
                // Toggle audio engine mute
                if (this.audioEngine) {
                    if (!this.soundEnabled) {
                        this.audioEngine.setMasterVolume(0);
                    } else {
                        this.audioEngine.setMasterVolume(this.audioEngine.preferences.masterVolume);
                    }
                }
            }
        });
        
        // Mini game buttons with enhanced audio feedback
        document.addEventListener('click', async (e) => {
            // Play button hover sound
            if (e.target.matches('button') && this.audioEngine) {
                this.audioEngine.playFromPool('buttonClick', 0.4);
            }
            
            if (e.target.matches('.play-slot-game')) {
                const gameId = e.target.dataset.gameId;
                if (gameId) {
                    const result = await this.playSlotGame(gameId);
                    this.displayGameResult(result);
                }
            }
            
            if (e.target.matches('.play-scratch-game')) {
                const gameId = e.target.dataset.gameId;
                if (gameId) {
                    const result = await this.playScratchGame(gameId);
                    this.displayGameResult(result);
                }
            }
            
            if (e.target.matches('.play-roulette-game')) {
                const gameId = e.target.dataset.gameId;
                if (gameId) {
                    const result = await this.playRouletteGame(gameId);
                    this.displayGameResult(result);
                }
            }
        });
    }
    
    displayGameResult(result) {
        console.log('Game Result:', result);
        // Display result in UI
    }
}

// Initialize Vegas Casino when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.vegasCasino = new VegasCasino();
    console.log('🎰 Vegas Casino initialized!');
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = VegasCasino;
}