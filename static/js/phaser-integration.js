// phaser-integration.js
// Integration layer between Phaser.js games and existing Vegas Casino system

class PhaserIntegration {
    constructor() {
        this.phaserEngine = null;
        this.currentGame = null;
        this.isInitialized = false;
        this.config = {
            enablePhaser: true,
            fallbackToLegacy: true,
            debugMode: false,
            performanceMonitoring: false
        };
        
        // Check for Phaser.js availability
        this.phaserAvailable = typeof Phaser !== 'undefined';
        
        // Integration with existing systems
        this.vegasCasino = window.vegasCasino || null;
        this.minigamesController = window.minigamesController || null;
        this.audioEngine = window.casinoAudio || null;
        
        this.init();
    }
    
    async init() {
        // Load Phaser.js if not already loaded
        if (!this.phaserAvailable) {
            await this.loadPhaserLibrary();
        }
        
        // Initialize Phaser engine
        if (this.phaserAvailable && this.config.enablePhaser) {
            this.initializePhaserEngine();
        }
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Setup UI enhancements
        this.enhanceUI();
        
        // Initialize performance monitoring if enabled
        if (this.config.performanceMonitoring) {
            this.initPerformanceMonitor();
        }
        
        this.isInitialized = true;
        console.log('🎮 Phaser Integration initialized!');
    }
    
    async loadPhaserLibrary() {
        return new Promise((resolve, reject) => {
            // Check if we're using npm/node_modules
            const phaserPath = '/node_modules/phaser/dist/phaser.min.js';
            const cdnPath = 'https://cdn.jsdelivr.net/npm/phaser@3.70.0/dist/phaser.min.js';
            
            const script = document.createElement('script');
            script.src = phaserPath;
            script.onerror = () => {
                // Fallback to CDN
                script.src = cdnPath;
                script.onerror = () => {
                    console.warn('Failed to load Phaser.js');
                    this.phaserAvailable = false;
                    resolve(false);
                };
            };
            
            script.onload = () => {
                this.phaserAvailable = true;
                resolve(true);
            };
            
            document.head.appendChild(script);
        });
    }
    
    initializePhaserEngine() {
        // Load the Phaser Casino Engine
        if (typeof PhaserCasinoEngine !== 'undefined') {
            this.phaserEngine = new PhaserCasinoEngine();
        } else if (window.phaserCasino) {
            this.phaserEngine = window.phaserCasino;
        } else {
            console.warn('Phaser Casino Engine not found, falling back to legacy games');
            this.config.enablePhaser = false;
        }
    }
    
    setupEventListeners() {
        // Override existing game launch functions
        this.overrideGameLaunchers();
        
        // Listen for game selection events
        document.addEventListener('click', (e) => {
            // Check for Phaser game triggers
            if (e.target.matches('.play-game-btn[data-phaser="true"]')) {
                e.preventDefault();
                const gameType = e.target.dataset.game;
                this.launchPhaserGame(gameType);
            }
            
            // Check for legacy game triggers with Phaser upgrade
            if (e.target.matches('.play-slot-game, .play-scratch-game, .play-roulette-game')) {
                if (this.config.enablePhaser && this.phaserEngine) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    let gameType = 'slots';
                    if (e.target.matches('.play-scratch-game')) gameType = 'scratch';
                    if (e.target.matches('.play-roulette-game')) gameType = 'wheel';
                    
                    this.launchPhaserGame(gameType);
                }
            }
        });
        
        // Integration with minigames controller
        if (window.showGame) {
            const originalShowGame = window.showGame;
            window.showGame = (gameId) => {
                if (this.shouldUsePhaserForGame(gameId)) {
                    this.launchPhaserGame(this.mapGameIdToPhaser(gameId));
                } else {
                    originalShowGame(gameId);
                }
            };
        }
        
        // Listen for Phaser game events
        if (this.phaserEngine && this.phaserEngine.game) {
            this.phaserEngine.game.events.on('gameWin', (data) => {
                this.handlePhaserGameWin(data);
            });
            
            this.phaserEngine.game.events.on('gameComplete', (data) => {
                this.handlePhaserGameComplete(data);
            });
        }
    }
    
    overrideGameLaunchers() {
        // Override slot machine functions
        if (window.spinSlots) {
            const originalSpinSlots = window.spinSlots;
            window.spinSlots = () => {
                if (this.config.enablePhaser && this.phaserEngine) {
                    this.launchPhaserGame('slots');
                } else {
                    originalSpinSlots();
                }
            };
        }
        
        // Override scratch card functions
        if (window.newScratchCard) {
            const originalNewScratchCard = window.newScratchCard;
            window.newScratchCard = () => {
                if (this.config.enablePhaser && this.phaserEngine) {
                    this.launchPhaserGame('scratch');
                } else {
                    originalNewScratchCard();
                }
            };
        }
    }
    
    enhanceUI() {
        // Add Phaser launch buttons to existing game cards
        const gameCards = document.querySelectorAll('.game-card');
        gameCards.forEach(card => {
            const gameType = this.detectGameType(card);
            if (gameType && this.shouldUsePhaserForGame(gameType)) {
                this.addPhaserBadge(card);
                this.enhanceGameCard(card, gameType);
            }
        });
        
        // Create Phaser game container if it doesn't exist
        if (!document.getElementById('phaser-game-container')) {
            this.createPhaserContainer();
        }
        
        // Add performance monitor if in debug mode
        if (this.config.debugMode) {
            this.createPerformanceMonitor();
        }
    }
    
    detectGameType(card) {
        const id = card.id || '';
        const classes = card.className || '';
        const content = card.textContent || '';
        
        if (id.includes('fortune') || content.includes('Wheel')) return 'wheel';
        if (id.includes('dice') || content.includes('Dice')) return 'dice';
        if (id.includes('slot') || content.includes('Slot')) return 'slots';
        if (id.includes('scratch') || content.includes('Scratch')) return 'scratch';
        
        return null;
    }
    
    shouldUsePhaserForGame(gameId) {
        if (!this.config.enablePhaser || !this.phaserEngine) return false;
        
        const phaserGames = ['slots', 'wheel', 'dice', 'scratch', 'fortune-wheel', 
                            'enhanced-dice', 'vegas-slots', 'scratch-cards'];
        
        return phaserGames.includes(gameId);
    }
    
    mapGameIdToPhaser(gameId) {
        const mapping = {
            'fortune-wheel': 'wheel',
            'enhanced-dice': 'dice',
            'vegas-slots': 'slots',
            'scratch-cards': 'scratch'
        };
        
        return mapping[gameId] || gameId;
    }
    
    addPhaserBadge(card) {
        if (card.querySelector('.phaser-badge')) return;
        
        const badge = document.createElement('div');
        badge.className = 'phaser-badge';
        badge.innerHTML = '✨ ENHANCED';
        badge.style.cssText = `
            position: absolute;
            top: 10px;
            right: 10px;
            background: linear-gradient(145deg, #FFD700, #FFA500);
            color: #000;
            padding: 5px 10px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
            animation: pulse 2s infinite;
            z-index: 10;
        `;
        
        card.style.position = 'relative';
        card.appendChild(badge);
    }
    
    enhanceGameCard(card, gameType) {
        // Add hover effects
        card.addEventListener('mouseenter', () => {
            if (this.audioEngine) {
                this.audioEngine.play('uiHover', { volume: 0.3 });
            }
        });
        
        // Modify play button to use Phaser
        const playButton = card.querySelector('.play-game-btn, button');
        if (playButton) {
            playButton.dataset.phaser = 'true';
            playButton.dataset.game = gameType;
        }
    }
    
    createPhaserContainer() {
        const container = document.createElement('div');
        container.id = 'phaser-game-container';
        container.className = 'phaser-game-container';
        
        // Add close button
        const closeBtn = document.createElement('button');
        closeBtn.className = 'phaser-close-btn';
        closeBtn.innerHTML = '✕';
        closeBtn.onclick = () => this.closePhaserGame();
        
        container.appendChild(closeBtn);
        document.body.appendChild(container);
    }
    
    createPerformanceMonitor() {
        const monitor = document.createElement('div');
        monitor.className = 'phaser-performance';
        monitor.id = 'phaser-performance';
        monitor.innerHTML = `
            <div class="phaser-performance-stat">FPS: <span id="phaser-fps">60</span></div>
            <div class="phaser-performance-stat">Memory: <span id="phaser-memory">0</span> MB</div>
            <div class="phaser-performance-stat">Draw Calls: <span id="phaser-draws">0</span></div>
        `;
        
        document.body.appendChild(monitor);
    }
    
    async launchPhaserGame(gameType) {
        // Show loading screen
        this.showLoadingScreen();
        
        // Initialize Phaser engine if needed
        if (!this.phaserEngine) {
            await this.initializePhaserEngine();
        }
        
        if (!this.phaserEngine) {
            console.error('Failed to initialize Phaser engine');
            this.hideLoadingScreen();
            
            // Fallback to legacy game
            if (this.config.fallbackToLegacy) {
                this.launchLegacyGame(gameType);
            }
            return;
        }
        
        // Show Phaser container
        const container = document.getElementById('phaser-game-container');
        if (container) {
            container.classList.add('active');
            container.style.display = 'flex';
        }
        
        // Launch the game
        this.phaserEngine.launchGame(gameType);
        this.currentGame = gameType;
        
        // Hide loading screen after a short delay
        setTimeout(() => {
            this.hideLoadingScreen();
        }, 1000);
        
        // Track game launch
        this.trackGameLaunch(gameType);
    }
    
    closePhaserGame() {
        const container = document.getElementById('phaser-game-container');
        if (container) {
            container.classList.remove('active');
            container.style.display = 'none';
        }
        
        if (this.phaserEngine && this.phaserEngine.game) {
            // Stop current scene
            const currentScene = this.phaserEngine.game.scene.getScenes(true)[0];
            if (currentScene) {
                this.phaserEngine.game.scene.stop(currentScene.scene.key);
            }
        }
        
        this.currentGame = null;
        
        // Play close sound
        if (this.audioEngine) {
            this.audioEngine.play('modalClose', { volume: 0.5 });
        }
    }
    
    launchLegacyGame(gameType) {
        // Fallback to original game functions
        switch(gameType) {
            case 'slots':
                if (window.spinSlots) window.spinSlots();
                break;
            case 'wheel':
                if (window.showGame) window.showGame('fortune-wheel');
                break;
            case 'dice':
                if (window.showGame) window.showGame('enhanced-dice');
                break;
            case 'scratch':
                if (window.newScratchCard) window.newScratchCard();
                break;
        }
    }
    
    showLoadingScreen() {
        let loading = document.getElementById('phaser-loading');
        if (!loading) {
            loading = document.createElement('div');
            loading.id = 'phaser-loading';
            loading.className = 'phaser-loading';
            loading.innerHTML = `
                <div class="phaser-loading-spinner"></div>
                <div class="phaser-loading-text">Loading Game...</div>
            `;
            document.body.appendChild(loading);
        }
        
        loading.style.display = 'flex';
    }
    
    hideLoadingScreen() {
        const loading = document.getElementById('phaser-loading');
        if (loading) {
            loading.style.display = 'none';
        }
    }
    
    handlePhaserGameWin(data) {
        // Integration with existing win handling
        if (this.minigamesController) {
            this.minigamesController.handleGameWin(data);
        }
        
        // Update Vegas Casino state
        if (this.vegasCasino) {
            this.vegasCasino.celebrateWin({
                prize: data.amount,
                type: data.winType
            });
        }
        
        // Send to backend
        this.submitGameResult(data);
    }
    
    handlePhaserGameComplete(data) {
        // Integration with existing completion handling
        if (this.minigamesController) {
            this.minigamesController.handleGameComplete(data);
        }
        
        // Update statistics
        this.updateGameStatistics(data);
    }
    
    async submitGameResult(data) {
        try {
            const formData = new FormData();
            const csrfToken = this.getCSRFToken();
            
            if (csrfToken) {
                formData.append('csrf_token', csrfToken);
            }
            
            formData.append('game_type', data.gameType);
            formData.append('amount', data.amount);
            formData.append('win_type', data.winType);
            
            const response = await fetch('/api/game-result', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const result = await response.json();
                this.handleBackendResponse(result);
            }
        } catch (error) {
            console.error('Failed to submit game result:', error);
        }
    }
    
    handleBackendResponse(data) {
        // Update UI with backend response
        if (data.new_balance !== undefined) {
            const balanceEl = document.getElementById('playerPoints');
            if (balanceEl) {
                balanceEl.textContent = data.new_balance;
            }
        }
        
        if (data.achievement) {
            this.showAchievement(data.achievement);
        }
    }
    
    showAchievement(achievement) {
        // Create achievement notification
        const notification = document.createElement('div');
        notification.className = 'achievement-unlock';
        notification.innerHTML = `
            <div class="achievement-icon">🏆</div>
            <div class="achievement-content">
                <div class="achievement-title">Achievement Unlocked!</div>
                <div class="achievement-name">${achievement.name}</div>
                <div class="achievement-desc">${achievement.description}</div>
            </div>
        `;
        
        document.body.appendChild(notification);
        
        // Play achievement sound
        if (this.audioEngine) {
            this.audioEngine.play('fanfare2', { volume: 0.7 });
        }
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
    
    updateGameStatistics(data) {
        // Update local storage statistics
        const stats = JSON.parse(localStorage.getItem('gameStatistics') || '{}');
        
        if (!stats[data.gameType]) {
            stats[data.gameType] = {
                played: 0,
                won: 0,
                totalWinnings: 0
            };
        }
        
        stats[data.gameType].played++;
        if (data.won) {
            stats[data.gameType].won++;
            stats[data.gameType].totalWinnings += data.amount || 0;
        }
        
        localStorage.setItem('gameStatistics', JSON.stringify(stats));
    }
    
    trackGameLaunch(gameType) {
        // Analytics tracking
        if (window.gtag) {
            window.gtag('event', 'game_launch', {
                game_type: gameType,
                engine: 'phaser',
                timestamp: new Date().toISOString()
            });
        }
        
        // Custom tracking
        const launches = JSON.parse(localStorage.getItem('gameLaunches') || '[]');
        launches.push({
            game: gameType,
            time: Date.now(),
            engine: 'phaser'
        });
        
        // Keep only last 100 launches
        if (launches.length > 100) {
            launches.shift();
        }
        
        localStorage.setItem('gameLaunches', JSON.stringify(launches));
    }
    
    initPerformanceMonitor() {
        if (!this.phaserEngine || !this.phaserEngine.game) return;
        
        setInterval(() => {
            if (this.phaserEngine.game && this.currentGame) {
                const fps = this.phaserEngine.game.loop.actualFps;
                const fpsEl = document.getElementById('phaser-fps');
                if (fpsEl) {
                    fpsEl.textContent = Math.round(fps);
                }
                
                // Memory usage (if available)
                if (performance.memory) {
                    const memoryMB = (performance.memory.usedJSHeapSize / 1048576).toFixed(1);
                    const memoryEl = document.getElementById('phaser-memory');
                    if (memoryEl) {
                        memoryEl.textContent = memoryMB;
                    }
                }
            }
        }, 1000);
    }
    
    getCSRFToken() {
        let token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (!token) {
            token = document.querySelector('input[name="csrf_token"]')?.value;
        }
        return token || '';
    }
    
    // Public API
    setConfig(config) {
        this.config = { ...this.config, ...config };
    }
    
    toggleDebugMode() {
        this.config.debugMode = !this.config.debugMode;
        const monitor = document.getElementById('phaser-performance');
        if (monitor) {
            monitor.classList.toggle('show', this.config.debugMode);
        }
    }
    
    isReady() {
        return this.isInitialized && this.phaserEngine !== null;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.phaserIntegration = new PhaserIntegration();
    
    // Expose public API
    window.launchPhaserGame = (gameType) => {
        if (window.phaserIntegration) {
            window.phaserIntegration.launchPhaserGame(gameType);
        }
    };
    
    window.closePhaserGame = () => {
        if (window.phaserIntegration) {
            window.phaserIntegration.closePhaserGame();
        }
    };
    
    console.log('🎮 Phaser Integration Layer ready!');
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = PhaserIntegration;
}