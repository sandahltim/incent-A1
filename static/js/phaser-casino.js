// phaser-casino.js
// Version: 3.0.0 - Professional Phaser.js Casino Gaming System
// Complete Vegas-style casino experience with advanced graphics and physics

class PhaserCasinoEngine {
    constructor() {
        this.config = {
            type: Phaser.AUTO,
            parent: 'phaser-game-container',
            width: 1280,
            height: 720,
            backgroundColor: '#1a0033',
            scale: {
                mode: Phaser.Scale.FIT,
                autoCenter: Phaser.Scale.CENTER_BOTH,
                min: {
                    width: 640,
                    height: 360
                },
                max: {
                    width: 1920,
                    height: 1080
                }
            },
            physics: {
                default: 'matter',
                matter: {
                    gravity: { y: 0.8 },
                    debug: false
                }
            },
            audio: {
                disableWebAudio: false
            },
            fps: {
                target: 60,
                forceSetTimeOut: false
            },
            scene: []
        };
        
        this.game = null;
        this.currentScene = null;
        this.playerData = {
            points: 0,
            level: 1,
            totalWins: 0,
            currentStreak: 0,
            achievements: [],
            unlockedGames: ['slots', 'wheel', 'dice', 'scratch']
        };
        
        this.csrfToken = this.getCSRFToken();
        this.audioEngine = window.casinoAudio || null;
        this.initialized = false;
    }
    
    async init() {
        if (this.initialized) return;
        
        // Register all game scenes
        this.config.scene = [
            BootScene,
            PreloaderScene,
            MainMenuScene,
            SlotMachineScene,
            WheelOfFortuneScene,
            DiceGameScene,
            ScratchCardScene,
            JackpotCelebrationScene
        ];
        
        // Create Phaser game instance
        this.game = new Phaser.Game(this.config);
        
        // Load player data
        this.loadPlayerData();
        
        // Setup global event handlers
        this.setupGlobalEvents();
        
        this.initialized = true;
        console.log('🎰 Phaser Casino Engine initialized!');
    }
    
    loadPlayerData() {
        const saved = localStorage.getItem('phaserCasinoData');
        if (saved) {
            try {
                this.playerData = { ...this.playerData, ...JSON.parse(saved) };
            } catch (error) {
                console.warn('Failed to load player data:', error);
            }
        }
    }
    
    savePlayerData() {
        localStorage.setItem('phaserCasinoData', JSON.stringify(this.playerData));
    }
    
    setupGlobalEvents() {
        // Listen for game events
        this.game.events.on('gameWin', (data) => {
            this.handleGameWin(data);
        });
        
        this.game.events.on('jackpotWin', (data) => {
            this.triggerJackpot(data);
        });
        
        // Integration with existing system
        document.addEventListener('phaserGameRequest', (event) => {
            this.launchGame(event.detail.gameType);
        });
    }
    
    launchGame(gameType) {
        if (!this.game) {
            this.init().then(() => {
                this.switchToGame(gameType);
            });
        } else {
            this.switchToGame(gameType);
        }
    }
    
    switchToGame(gameType) {
        const sceneMap = {
            'slots': 'SlotMachineScene',
            'wheel': 'WheelOfFortuneScene',
            'dice': 'DiceGameScene',
            'scratch': 'ScratchCardScene'
        };
        
        const sceneName = sceneMap[gameType];
        if (sceneName && this.game.scene.getScene(sceneName)) {
            this.game.scene.start(sceneName, { 
                playerData: this.playerData,
                csrfToken: this.csrfToken 
            });
        }
    }
    
    async handleGameWin(data) {
        const { amount, gameType, winType } = data;
        
        this.playerData.totalWins++;
        this.playerData.currentStreak++;
        this.playerData.points += amount;
        
        // Send to backend
        await this.submitGameResult(gameType, amount, winType);
        
        // Save locally
        this.savePlayerData();
        
        // Update UI
        this.updateDisplays();
        
        // Check for achievements
        this.checkAchievements();
    }
    
    async submitGameResult(gameType, amount, winType) {
        try {
            const formData = new FormData();
            formData.append('csrf_token', this.csrfToken);
            formData.append('game_type', gameType);
            formData.append('amount', amount);
            formData.append('win_type', winType);
            
            const response = await fetch('/api/game-result', {
                method: 'POST',
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                return data;
            }
        } catch (error) {
            console.error('Failed to submit game result:', error);
        }
    }
    
    triggerJackpot(data) {
        // Switch to jackpot celebration scene
        this.game.scene.start('JackpotCelebrationScene', {
            amount: data.amount,
            gameType: data.gameType,
            playerData: this.playerData
        });
    }
    
    updateDisplays() {
        // Update DOM elements with new values
        const pointsEl = document.getElementById('playerPoints');
        const winsEl = document.getElementById('totalWins');
        const streakEl = document.getElementById('currentStreak');
        
        if (pointsEl) pointsEl.textContent = this.playerData.points;
        if (winsEl) winsEl.textContent = this.playerData.totalWins;
        if (streakEl) streakEl.textContent = this.playerData.currentStreak;
    }
    
    checkAchievements() {
        const achievements = [];
        
        if (this.playerData.totalWins >= 10 && !this.playerData.achievements.includes('winner10')) {
            achievements.push({ id: 'winner10', name: 'Lucky 10', description: 'Win 10 games' });
        }
        
        if (this.playerData.currentStreak >= 5 && !this.playerData.achievements.includes('streak5')) {
            achievements.push({ id: 'streak5', name: 'Hot Streak', description: 'Win 5 games in a row' });
        }
        
        achievements.forEach(achievement => {
            this.playerData.achievements.push(achievement.id);
            this.showAchievementUnlock(achievement);
        });
        
        if (achievements.length > 0) {
            this.savePlayerData();
        }
    }
    
    showAchievementUnlock(achievement) {
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
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }
    
    getCSRFToken() {
        let token = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
        if (!token) {
            token = document.querySelector('input[name="csrf_token"]')?.value;
        }
        return token || '';
    }
    
    destroy() {
        if (this.game) {
            this.game.destroy(true);
            this.game = null;
        }
        this.initialized = false;
    }
}

// Boot Scene - Initial setup
class BootScene extends Phaser.Scene {
    constructor() {
        super({ key: 'BootScene' });
    }
    
    preload() {
        // Create loading bar graphics
        const width = this.cameras.main.width;
        const height = this.cameras.main.height;
        
        const progressBar = this.add.graphics();
        const progressBox = this.add.graphics();
        progressBox.fillStyle(0x222222, 0.8);
        progressBox.fillRect(width/2 - 160, height/2 - 25, 320, 50);
        
        const loadingText = this.make.text({
            x: width / 2,
            y: height / 2 - 50,
            text: 'Initializing Vegas Casino...',
            style: {
                font: '20px monospace',
                fill: '#ffffff'
            }
        });
        loadingText.setOrigin(0.5, 0.5);
        
        const percentText = this.make.text({
            x: width / 2,
            y: height / 2,
            text: '0%',
            style: {
                font: '18px monospace',
                fill: '#ffffff'
            }
        });
        percentText.setOrigin(0.5, 0.5);
        
        this.load.on('progress', (value) => {
            percentText.setText(parseInt(value * 100) + '%');
            progressBar.clear();
            progressBar.fillStyle(0xffffff, 1);
            progressBar.fillRect(width/2 - 150, height/2 - 15, 300 * value, 30);
        });
        
        this.load.on('complete', () => {
            progressBar.destroy();
            progressBox.destroy();
            loadingText.destroy();
            percentText.destroy();
        });
    }
    
    create() {
        this.scene.start('PreloaderScene');
    }
}

// Preloader Scene - Load all game assets
class PreloaderScene extends Phaser.Scene {
    constructor() {
        super({ key: 'PreloaderScene' });
    }
    
    preload() {
        // Load sprite sheets and images
        this.createAssets();
        
        // Load audio if not using external audio engine
        if (!window.casinoAudio) {
            this.loadAudio();
        }
        
        // Initialize enhanced audio system
        if (window.PhaserAudioIntegration) {
            this.audioEnhancement = window.PhaserAudioIntegration.enhance(this, 'menu');
        }
    }
    
    createAssets() {
        // Generate procedural graphics for games
        // Since we don't have image files, we'll create them programmatically
        
        // Create slot machine symbols
        this.createSlotSymbols();
        
        // Create wheel segments
        this.createWheelSegments();
        
        // Create dice faces
        this.createDiceFaces();
        
        // Create scratch card textures
        this.createScratchCardTextures();
        
        // Create particle effects
        this.createParticleTextures();
    }
    
    createSlotSymbols() {
        const symbols = ['cherry', 'lemon', 'orange', 'grape', 'diamond', 'star', 'bell', 'seven'];
        const colors = ['#FF0000', '#FFFF00', '#FFA500', '#800080', '#00FFFF', '#FFD700', '#C0C0C0', '#FF0000'];
        const emojis = ['🍒', '🍋', '🍊', '🍇', '💎', '⭐', '🔔', '7️⃣'];
        
        symbols.forEach((symbol, index) => {
            const graphics = this.make.graphics({ x: 0, y: 0, add: false });
            
            // Background
            graphics.fillStyle(0x2a0845, 1);
            graphics.fillRoundedRect(0, 0, 120, 120, 15);
            
            // Border
            graphics.lineStyle(4, Phaser.Display.Color.HexStringToColor(colors[index]).color, 1);
            graphics.strokeRoundedRect(2, 2, 116, 116, 15);
            
            // Inner glow
            graphics.fillStyle(Phaser.Display.Color.HexStringToColor(colors[index]).color, 0.3);
            graphics.fillRoundedRect(10, 10, 100, 100, 10);
            
            // Generate texture
            graphics.generateTexture('symbol_' + symbol, 120, 120);
            graphics.destroy();
            
            // Add emoji text overlay (we'll add this in the game scene)
            this.textures.addBase64('emoji_' + symbol, this.createEmojiTexture(emojis[index], colors[index]));
        });
    }
    
    createEmojiTexture(emoji, color) {
        const canvas = document.createElement('canvas');
        canvas.width = 80;
        canvas.height = 80;
        const ctx = canvas.getContext('2d');
        
        ctx.font = '60px Arial';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(emoji, 40, 40);
        
        return canvas.toDataURL();
    }
    
    createWheelSegments() {
        const segments = [
            { value: 5, color: '#FF6B6B', label: '$5' },
            { value: 10, color: '#4ECDC4', label: '$10' },
            { value: 15, color: '#45B7D1', label: '$15' },
            { value: 25, color: '#96CEB4', label: '$25' },
            { value: 50, color: '#FFEAA7', label: '$50' },
            { value: 100, color: '#DDA0DD', label: '$100' },
            { value: 'JACKPOT', color: '#FFD700', label: 'JACKPOT' },
            { value: 0, color: '#95A5A6', label: 'Try Again' }
        ];
        
        // Create wheel texture
        const graphics = this.make.graphics({ x: 0, y: 0, add: false });
        const centerX = 300;
        const centerY = 300;
        const radius = 280;
        
        segments.forEach((segment, index) => {
            const startAngle = (index * 2 * Math.PI) / segments.length - Math.PI / 2;
            const endAngle = ((index + 1) * 2 * Math.PI) / segments.length - Math.PI / 2;
            
            graphics.fillStyle(Phaser.Display.Color.HexStringToColor(segment.color).color, 1);
            graphics.slice(centerX, centerY, radius, startAngle, endAngle, false);
            graphics.fillPath();
            
            // Add border
            graphics.lineStyle(3, 0x000000, 1);
            graphics.strokePath();
        });
        
        // Center circle
        graphics.fillStyle(0x2C3E50, 1);
        graphics.fillCircle(centerX, centerY, 40);
        graphics.lineStyle(4, 0xFFD700, 1);
        graphics.strokeCircle(centerX, centerY, 40);
        
        graphics.generateTexture('wheel', 600, 600);
        graphics.destroy();
        
        // Store segment data for later use
        this.registry.set('wheelSegments', segments);
    }
    
    createDiceFaces() {
        const faces = 6;
        const dotPositions = [
            [[50, 50]], // 1
            [[25, 25], [75, 75]], // 2
            [[25, 25], [50, 50], [75, 75]], // 3
            [[25, 25], [25, 75], [75, 25], [75, 75]], // 4
            [[25, 25], [25, 75], [50, 50], [75, 25], [75, 75]], // 5
            [[25, 25], [25, 50], [25, 75], [75, 25], [75, 50], [75, 75]] // 6
        ];
        
        for (let i = 1; i <= faces; i++) {
            const graphics = this.make.graphics({ x: 0, y: 0, add: false });
            
            // Dice background
            graphics.fillStyle(0xFFFFFF, 1);
            graphics.fillRoundedRect(0, 0, 100, 100, 10);
            
            // Border
            graphics.lineStyle(2, 0x000000, 1);
            graphics.strokeRoundedRect(0, 0, 100, 100, 10);
            
            // Dots
            graphics.fillStyle(0x000000, 1);
            dotPositions[i - 1].forEach(([x, y]) => {
                graphics.fillCircle(x, y, 8);
            });
            
            graphics.generateTexture('dice_' + i, 100, 100);
            graphics.destroy();
        }
    }
    
    createScratchCardTextures() {
        // Create scratch card background
        const graphics = this.make.graphics({ x: 0, y: 0, add: false });
        
        // Card background
        graphics.fillStyle(0xFFD700, 1);
        graphics.fillRoundedRect(0, 0, 300, 200, 15);
        
        // Decorative border
        graphics.lineStyle(4, 0x8B7355, 1);
        graphics.strokeRoundedRect(2, 2, 296, 196, 15);
        
        // Inner pattern
        for (let i = 0; i < 10; i++) {
            for (let j = 0; j < 6; j++) {
                graphics.fillStyle(0xFFA500, 0.3);
                graphics.fillCircle(30 + i * 30, 30 + j * 30, 5);
            }
        }
        
        graphics.generateTexture('scratchCard', 300, 200);
        graphics.destroy();
        
        // Create scratch surface
        const scratchGraphics = this.make.graphics({ x: 0, y: 0, add: false });
        scratchGraphics.fillStyle(0xC0C0C0, 1);
        scratchGraphics.fillRoundedRect(0, 0, 300, 200, 15);
        
        // Add text pattern
        scratchGraphics.fillStyle(0x808080, 1);
        for (let i = 0; i < 5; i++) {
            scratchGraphics.fillRect(20 + i * 55, 80, 45, 40);
        }
        
        scratchGraphics.generateTexture('scratchSurface', 300, 200);
        scratchGraphics.destroy();
    }
    
    createParticleTextures() {
        // Create coin particle
        const coinGraphics = this.make.graphics({ x: 0, y: 0, add: false });
        coinGraphics.fillStyle(0xFFD700, 1);
        coinGraphics.fillCircle(16, 16, 16);
        coinGraphics.lineStyle(2, 0xB8860B, 1);
        coinGraphics.strokeCircle(16, 16, 16);
        coinGraphics.fillStyle(0xB8860B, 1);
        coinGraphics.fillRect(11, 8, 10, 16);
        coinGraphics.generateTexture('particle_coin', 32, 32);
        coinGraphics.destroy();
        
        // Create star particle
        const starGraphics = this.make.graphics({ x: 0, y: 0, add: false });
        starGraphics.fillStyle(0xFFD700, 1);
        starGraphics.beginPath();
        starGraphics.moveTo(16, 0);
        for (let i = 0; i < 10; i++) {
            const radius = i % 2 === 0 ? 16 : 8;
            const angle = (i * Math.PI) / 5 - Math.PI / 2;
            starGraphics.lineTo(16 + Math.cos(angle) * radius, 16 + Math.sin(angle) * radius);
        }
        starGraphics.closePath();
        starGraphics.fillPath();
        starGraphics.generateTexture('particle_star', 32, 32);
        starGraphics.destroy();
        
        // Create sparkle particle
        const sparkleGraphics = this.make.graphics({ x: 0, y: 0, add: false });
        sparkleGraphics.fillStyle(0xFFFFFF, 1);
        sparkleGraphics.fillCircle(8, 8, 3);
        sparkleGraphics.fillStyle(0xFFFFFF, 0.5);
        sparkleGraphics.fillCircle(8, 8, 8);
        sparkleGraphics.generateTexture('particle_sparkle', 16, 16);
        sparkleGraphics.destroy();
    }
    
    loadAudio() {
        // Load audio files if needed
        this.load.audio('spin', '/static/audio/slot-reel-spin.mp3');
        this.load.audio('stop', '/static/audio/slot-reel-stop-1.mp3');
        this.load.audio('win', '/static/audio/win-medium.mp3');
        this.load.audio('jackpot', '/static/audio/win-jackpot.mp3');
        this.load.audio('coin', '/static/audio/coin-drop.mp3');
        this.load.audio('wheel_tick', '/static/audio/wheel-tick.mp3');
        this.load.audio('dice_roll', '/static/audio/dice-roll-1.mp3');
        this.load.audio('scratch', '/static/audio/scratch-loop.mp3');
    }
    
    create() {
        // Assets loaded, start main menu
        this.scene.start('MainMenuScene');
    }
}

// Main Menu Scene
class MainMenuScene extends Phaser.Scene {
    constructor() {
        super({ key: 'MainMenuScene' });
    }
    
    create() {
        const { width, height } = this.cameras.main;
        
        // Background gradient
        this.createBackground();
        
        // Title
        const title = this.add.text(width / 2, 100, 'VEGAS CASINO', {
            font: '72px Arial Black',
            fill: '#FFD700',
            stroke: '#000000',
            strokeThickness: 8,
            shadow: {
                offsetX: 5,
                offsetY: 5,
                color: '#000000',
                blur: 10,
                fill: true
            }
        });
        title.setOrigin(0.5);
        
        // Subtitle
        const subtitle = this.add.text(width / 2, 180, 'Choose Your Game', {
            font: '32px Arial',
            fill: '#FFFFFF',
            stroke: '#000000',
            strokeThickness: 4
        });
        subtitle.setOrigin(0.5);
        
        // Game buttons
        const games = [
            { name: 'SLOT MACHINE', scene: 'SlotMachineScene', icon: '🎰' },
            { name: 'WHEEL OF FORTUNE', scene: 'WheelOfFortuneScene', icon: '🎡' },
            { name: 'DICE ROLL', scene: 'DiceGameScene', icon: '🎲' },
            { name: 'SCRATCH CARDS', scene: 'ScratchCardScene', icon: '🎟️' }
        ];
        
        games.forEach((game, index) => {
            this.createGameButton(width / 2, 280 + index * 100, game);
        });
        
        // Add animated particles
        this.createParticleEffects();
    }
    
    createBackground() {
        const { width, height } = this.cameras.main;
        
        const graphics = this.add.graphics();
        
        // Create gradient background
        const color1 = Phaser.Display.Color.HexStringToColor('#1a0033');
        const color2 = Phaser.Display.Color.HexStringToColor('#330066');
        
        for (let i = 0; i < height; i++) {
            const color = Phaser.Display.Color.Interpolate.ColorWithColor(
                color1, color2, height, i
            );
            graphics.fillStyle(color.color, 1);
            graphics.fillRect(0, i, width, 1);
        }
    }
    
    createGameButton(x, y, gameData) {
        const button = this.add.container(x, y);
        
        // Button background
        const bg = this.add.graphics();
        bg.fillStyle(0x2C3E50, 1);
        bg.fillRoundedRect(-200, -35, 400, 70, 20);
        bg.lineStyle(3, 0xFFD700, 1);
        bg.strokeRoundedRect(-200, -35, 400, 70, 20);
        
        // Button text
        const text = this.add.text(0, 0, `${gameData.icon} ${gameData.name}`, {
            font: '28px Arial',
            fill: '#FFFFFF'
        });
        text.setOrigin(0.5);
        
        button.add([bg, text]);
        button.setInteractive(new Phaser.Geom.Rectangle(-200, -35, 400, 70), Phaser.Geom.Rectangle.Contains);
        
        // Hover effects
        button.on('pointerover', () => {
            bg.clear();
            bg.fillStyle(0x34495E, 1);
            bg.fillRoundedRect(-200, -35, 400, 70, 20);
            bg.lineStyle(3, 0xFFD700, 1);
            bg.strokeRoundedRect(-200, -35, 400, 70, 20);
            text.setScale(1.1);
        });
        
        button.on('pointerout', () => {
            bg.clear();
            bg.fillStyle(0x2C3E50, 1);
            bg.fillRoundedRect(-200, -35, 400, 70, 20);
            bg.lineStyle(3, 0xFFD700, 1);
            bg.strokeRoundedRect(-200, -35, 400, 70, 20);
            text.setScale(1);
        });
        
        button.on('pointerdown', () => {
            this.scene.start(gameData.scene);
        });
    }
    
    createParticleEffects() {
        const particles = this.add.particles(0, 0, 'particle_sparkle', {
            x: { min: 0, max: this.cameras.main.width },
            y: 0,
            lifespan: 4000,
            speedY: { min: 50, max: 100 },
            scale: { start: 1, end: 0 },
            quantity: 1,
            frequency: 500,
            alpha: { start: 1, end: 0 },
            blendMode: 'ADD'
        });
    }
}

// Slot Machine Scene
class SlotMachineScene extends Phaser.Scene {
    constructor() {
        super({ key: 'SlotMachineScene' });
        this.reels = [];
        this.symbols = ['cherry', 'lemon', 'orange', 'grape', 'diamond', 'star', 'bell', 'seven'];
        this.isSpinning = false;
        this.credits = 100;
        this.bet = 1;
        this.winAmount = 0;
    }
    
    create() {
        const { width, height } = this.cameras.main;
        
        // Initialize enhanced audio for slots
        if (window.PhaserAudioIntegration) {
            this.audioEnhancement = window.PhaserAudioIntegration.enhance(this, 'slots');
        }
        
        // Background
        this.createSlotMachineBackground();
        
        // Title
        this.add.text(width / 2, 50, 'SLOT MACHINE', {
            font: '48px Arial Black',
            fill: '#FFD700',
            stroke: '#000000',
            strokeThickness: 6
        }).setOrigin(0.5);
        
        // Create slot machine frame
        this.createSlotFrame(width / 2, height / 2);
        
        // Create reels
        this.createReels(width / 2, height / 2);
        
        // Create controls
        this.createControls(width / 2, height - 100);
        
        // Create info display
        this.createInfoDisplay();
        
        // Back button
        this.createBackButton();
    }
    
    createSlotMachineBackground() {
        const { width, height } = this.cameras.main;
        
        const graphics = this.add.graphics();
        
        // Gradient background
        const color1 = Phaser.Display.Color.HexStringToColor('#2C0A4D');
        const color2 = Phaser.Display.Color.HexStringToColor('#000000');
        
        for (let i = 0; i < height; i++) {
            const color = Phaser.Display.Color.Interpolate.ColorWithColor(
                color1, color2, height, i
            );
            graphics.fillStyle(color.color, 1);
            graphics.fillRect(0, i, width, 1);
        }
        
        // Add decorative lights
        for (let i = 0; i < 20; i++) {
            const x = Phaser.Math.Between(50, width - 50);
            const y = Phaser.Math.Between(50, height - 50);
            const radius = Phaser.Math.Between(20, 40);
            
            graphics.fillStyle(0xFFD700, Phaser.Math.FloatBetween(0.1, 0.3));
            graphics.fillCircle(x, y, radius);
        }
    }
    
    createSlotFrame(x, y) {
        const frame = this.add.graphics();
        
        // Outer frame
        frame.fillStyle(0x8B4513, 1);
        frame.fillRoundedRect(x - 250, y - 200, 500, 400, 20);
        
        // Inner frame
        frame.fillStyle(0x000000, 1);
        frame.fillRoundedRect(x - 230, y - 180, 460, 360, 15);
        
        // Reel windows
        for (let i = 0; i < 3; i++) {
            frame.fillStyle(0x1a1a1a, 1);
            frame.fillRect(x - 200 + i * 140, y - 150, 120, 300);
            
            // Window border
            frame.lineStyle(4, 0xFFD700, 1);
            frame.strokeRect(x - 200 + i * 140, y - 150, 120, 300);
        }
        
        // Payline
        frame.lineStyle(3, 0xFF0000, 1);
        frame.beginPath();
        frame.moveTo(x - 210, y);
        frame.lineTo(x + 210, y);
        frame.strokePath();
    }
    
    createReels(x, y) {
        for (let i = 0; i < 3; i++) {
            const reelContainer = this.add.container(x - 140 + i * 140, y);
            const reelSymbols = [];
            
            // Create symbol strip (visible symbols plus buffer)
            for (let j = -2; j <= 2; j++) {
                const symbolIndex = Phaser.Math.Between(0, this.symbols.length - 1);
                const symbol = this.symbols[symbolIndex];
                
                // Symbol background
                const symbolBg = this.add.sprite(0, j * 100, 'symbol_' + symbol);
                symbolBg.setScale(0.9);
                
                reelSymbols.push({ bg: symbolBg, type: symbol });
            }
            
            reelContainer.add(reelSymbols.map(s => s.bg));
            
            // Mask for reel window
            const mask = this.add.graphics();
            mask.fillRect(x - 200 + i * 140, y - 150, 120, 300);
            const maskGeom = new Phaser.Display.Masks.GeometryMask(this, mask);
            reelContainer.setMask(maskGeom);
            
            this.reels.push({
                container: reelContainer,
                symbols: reelSymbols,
                targetY: 0,
                velocity: 0,
                spinning: false
            });
        }
    }
    
    createControls(x, y) {
        // Bet controls
        const betMinus = this.createButton(x - 150, y, '-', () => this.adjustBet(-1));
        const betPlus = this.createButton(x - 50, y, '+', () => this.adjustBet(1));
        
        this.betText = this.add.text(x - 100, y, `BET: ${this.bet}`, {
            font: '24px Arial',
            fill: '#FFFFFF'
        }).setOrigin(0.5);
        
        // Spin button
        const spinButton = this.add.container(x + 50, y);
        const spinBg = this.add.graphics();
        spinBg.fillStyle(0xFF0000, 1);
        spinBg.fillCircle(0, 0, 40);
        spinBg.lineStyle(4, 0xFFD700, 1);
        spinBg.strokeCircle(0, 0, 40);
        
        const spinText = this.add.text(0, 0, 'SPIN', {
            font: '24px Arial Black',
            fill: '#FFFFFF'
        }).setOrigin(0.5);
        
        spinButton.add([spinBg, spinText]);
        spinButton.setInteractive(new Phaser.Geom.Circle(0, 0, 40), Phaser.Geom.Circle.Contains);
        
        spinButton.on('pointerdown', () => this.spin());
        spinButton.on('pointerover', () => spinBg.setScale(1.1));
        spinButton.on('pointerout', () => spinBg.setScale(1));
        
        this.spinButton = spinButton;
    }
    
    createButton(x, y, text, callback) {
        const button = this.add.container(x, y);
        
        const bg = this.add.graphics();
        bg.fillStyle(0x2C3E50, 1);
        bg.fillRoundedRect(-25, -20, 50, 40, 10);
        bg.lineStyle(2, 0xFFD700, 1);
        bg.strokeRoundedRect(-25, -20, 50, 40, 10);
        
        const label = this.add.text(0, 0, text, {
            font: '24px Arial',
            fill: '#FFFFFF'
        }).setOrigin(0.5);
        
        button.add([bg, label]);
        button.setInteractive(new Phaser.Geom.Rectangle(-25, -20, 50, 40), Phaser.Geom.Rectangle.Contains);
        button.on('pointerdown', callback);
        
        return button;
    }
    
    createInfoDisplay() {
        const { width } = this.cameras.main;
        
        this.creditsText = this.add.text(50, 50, `CREDITS: ${this.credits}`, {
            font: '24px Arial',
            fill: '#FFD700'
        });
        
        this.winText = this.add.text(width - 50, 50, `WIN: ${this.winAmount}`, {
            font: '24px Arial',
            fill: '#00FF00'
        }).setOrigin(1, 0);
    }
    
    createBackButton() {
        const backButton = this.add.text(50, this.cameras.main.height - 50, '← BACK', {
            font: '24px Arial',
            fill: '#FFFFFF',
            backgroundColor: '#2C3E50',
            padding: { x: 15, y: 10 }
        });
        
        backButton.setInteractive();
        backButton.on('pointerdown', () => this.scene.start('MainMenuScene'));
        backButton.on('pointerover', () => backButton.setScale(1.1));
        backButton.on('pointerout', () => backButton.setScale(1));
    }
    
    adjustBet(amount) {
        this.bet = Phaser.Math.Clamp(this.bet + amount, 1, 10);
        this.betText.setText(`BET: ${this.bet}`);
    }
    
    spin() {
        if (this.isSpinning || this.credits < this.bet) return;
        
        this.isSpinning = true;
        this.credits -= this.bet;
        this.creditsText.setText(`CREDITS: ${this.credits}`);
        this.winAmount = 0;
        this.winText.setText(`WIN: ${this.winAmount}`);
        
        // Play lever pull sound with spatial positioning
        if (this.playAudio) {
            this.playAudio('leverPull', { spatial: true, position: { x: 0, y: -100 } });
        }
        
        // Start spinning each reel with delay
        this.reels.forEach((reel, index) => {
            this.time.delayedCall(index * 200, () => {
                // Play reel start sound for each reel
                if (this.playAudio && index === 0) {
                    this.playAudio('reelStart');
                    this.playAudio('reelSpin', { loop: true });
                }
                this.startReelSpin(reel, 2000 + index * 500);
            });
        });
        
        // Check results after all reels stop
        this.time.delayedCall(3500, () => this.checkWin());
    }
    
    startReelSpin(reel, duration) {
        reel.spinning = true;
        reel.velocity = 20;
        
        // Spin animation
        const spinTween = this.tweens.add({
            targets: reel,
            velocity: { from: 20, to: 0 },
            duration: duration,
            ease: 'Cubic.easeOut',
            onUpdate: () => {
                reel.container.y += reel.velocity;
                
                // Wrap symbols
                reel.symbols.forEach(symbol => {
                    if (symbol.bg.y > 200) {
                        symbol.bg.y -= 500;
                        // Change symbol when wrapping
                        const newSymbol = this.symbols[Phaser.Math.Between(0, this.symbols.length - 1)];
                        symbol.bg.setTexture('symbol_' + newSymbol);
                        symbol.type = newSymbol;
                    }
                });
            },
            onComplete: () => {
                reel.spinning = false;
                // Play reel stop sound with sequential timing
                if (this.playAudio) {
                    this.playAudio('reelStop');
                }
                this.snapReel(reel);
            }
        });
    }
    
    snapReel(reel) {
        // Snap to nearest position
        const snapY = Math.round(reel.container.y / 100) * 100;
        
        this.tweens.add({
            targets: reel.container,
            y: snapY,
            duration: 200,
            ease: 'Back.easeOut'
        });
    }
    
    checkWin() {
        // Get center symbols (at payline)
        const results = this.reels.map(reel => {
            const centerSymbol = reel.symbols.find(s => 
                Math.abs(s.bg.y + reel.container.y) < 50
            );
            return centerSymbol ? centerSymbol.type : null;
        });
        
        // Check for wins
        let winMultiplier = 0;
        let winType = null;
        
        // Three of a kind
        if (results[0] === results[1] && results[1] === results[2]) {
            winMultiplier = this.getSymbolValue(results[0]) * 10;
            winType = winMultiplier >= 50 ? 'jackpot' : 'bigWin';
            this.showWinAnimation('JACKPOT!', winMultiplier);
            // Play appropriate win audio
            if (this.playAudio) {
                this.playAudio(winType);
            }
        }
        // Two of a kind
        else if (results[0] === results[1] || results[1] === results[2] || results[0] === results[2]) {
            const matchSymbol = results[0] === results[1] ? results[0] : results[1];
            winMultiplier = this.getSymbolValue(matchSymbol) * 2;
            winType = winMultiplier >= 20 ? 'mediumWin' : 'smallWin';
            this.showWinAnimation('WINNER!', winMultiplier);
            // Play appropriate win audio
            if (this.playAudio) {
                this.playAudio(winType);
            }
        } else {
            // Near miss detection
            if (results[0] === results[1] || results[1] === results[2]) {
                if (this.playAudio) {
                    this.playAudio('nearMiss');
                }
            }
        }
        
        if (winMultiplier > 0) {
            this.winAmount = this.bet * winMultiplier;
            this.credits += this.winAmount;
            this.creditsText.setText(`CREDITS: ${this.credits}`);
            this.winText.setText(`WIN: ${this.winAmount}`);
            
            // Trigger game win event
            this.game.events.emit('gameWin', {
                amount: this.winAmount,
                gameType: 'slots',
                winType: winMultiplier >= 50 ? 'jackpot' : 'regular'
            });
        }
        
        this.isSpinning = false;
    }
    
    getSymbolValue(symbol) {
        const values = {
            'cherry': 1,
            'lemon': 2,
            'orange': 3,
            'grape': 4,
            'bell': 5,
            'star': 7,
            'diamond': 10,
            'seven': 20
        };
        return values[symbol] || 1;
    }
    
    showWinAnimation(text, multiplier) {
        const { width, height } = this.cameras.main;
        
        // Win text
        const winAnnouncement = this.add.text(width / 2, height / 2, text, {
            font: '72px Arial Black',
            fill: '#FFD700',
            stroke: '#FF0000',
            strokeThickness: 8
        }).setOrigin(0.5);
        
        // Scale animation
        this.tweens.add({
            targets: winAnnouncement,
            scale: { from: 0, to: 1.5 },
            alpha: { from: 1, to: 0 },
            duration: 2000,
            ease: 'Bounce.easeOut',
            onComplete: () => winAnnouncement.destroy()
        });
        
        // Particle celebration
        if (multiplier >= 50) {
            this.createCelebrationParticles();
        }
    }
    
    createCelebrationParticles() {
        const { width, height } = this.cameras.main;
        
        // Coin shower
        const coins = this.add.particles(width / 2, -50, 'particle_coin', {
            x: { min: -200, max: 200 },
            y: { min: 0, max: height + 100 },
            scale: { start: 1, end: 0.5 },
            rotate: { min: 0, max: 360 },
            lifespan: 3000,
            speedY: { min: 200, max: 400 },
            quantity: 50,
            frequency: 50,
            gravityY: 200
        });
        
        this.time.delayedCall(3000, () => coins.destroy());
    }
}

// Wheel of Fortune Scene
class WheelOfFortuneScene extends Phaser.Scene {
    constructor() {
        super({ key: 'WheelOfFortuneScene' });
        this.wheel = null;
        this.pointer = null;
        this.isSpinning = false;
        this.segments = [];
    }
    
    create() {
        const { width, height } = this.cameras.main;
        
        // Initialize enhanced audio for wheel
        if (window.PhaserAudioIntegration) {
            this.audioEnhancement = window.PhaserAudioIntegration.enhance(this, 'wheel');
        }
        
        // Background
        this.createWheelBackground();
        
        // Title
        this.add.text(width / 2, 50, 'WHEEL OF FORTUNE', {
            font: '48px Arial Black',
            fill: '#FFD700',
            stroke: '#000000',
            strokeThickness: 6
        }).setOrigin(0.5);
        
        // Get segments from registry
        this.segments = this.registry.get('wheelSegments') || this.createDefaultSegments();
        
        // Create wheel
        this.createWheel(width / 2, height / 2);
        
        // Create pointer
        this.createPointer(width / 2, height / 2 - 320);
        
        // Create spin button
        this.createSpinButton(width / 2, height - 100);
        
        // Back button
        this.createBackButton();
        
        // Info display
        this.createInfoDisplay();
    }
    
    createWheelBackground() {
        const { width, height } = this.cameras.main;
        
        const graphics = this.add.graphics();
        
        // Radial gradient effect
        for (let i = 0; i < 50; i++) {
            const alpha = 1 - (i / 50);
            graphics.fillStyle(0x4B0082, alpha * 0.1);
            graphics.fillCircle(width / 2, height / 2, 400 - i * 8);
        }
    }
    
    createDefaultSegments() {
        return [
            { value: 5, color: '#FF6B6B', label: '$5' },
            { value: 10, color: '#4ECDC4', label: '$10' },
            { value: 15, color: '#45B7D1', label: '$15' },
            { value: 25, color: '#96CEB4', label: '$25' },
            { value: 50, color: '#FFEAA7', label: '$50' },
            { value: 100, color: '#DDA0DD', label: '$100' },
            { value: 'JACKPOT', color: '#FFD700', label: 'JACKPOT' },
            { value: 0, color: '#95A5A6', label: 'Try Again' }
        ];
    }
    
    createWheel(x, y) {
        // Create wheel container
        this.wheel = this.add.container(x, y);
        
        // Wheel background
        const wheelBg = this.add.sprite(0, 0, 'wheel');
        this.wheel.add(wheelBg);
        
        // Add segment labels
        this.segments.forEach((segment, index) => {
            const angle = (index * 360 / this.segments.length) + (180 / this.segments.length);
            const labelRadius = 200;
            const labelX = Math.cos(Phaser.Math.DegToRad(angle - 90)) * labelRadius;
            const labelY = Math.sin(Phaser.Math.DegToRad(angle - 90)) * labelRadius;
            
            const label = this.add.text(labelX, labelY, segment.label, {
                font: '24px Arial Black',
                fill: '#000000',
                stroke: '#FFFFFF',
                strokeThickness: 2
            });
            label.setOrigin(0.5);
            label.setRotation(Phaser.Math.DegToRad(angle));
            
            this.wheel.add(label);
        });
        
        // Add center cap
        const centerCap = this.add.graphics();
        centerCap.fillStyle(0x2C3E50, 1);
        centerCap.fillCircle(0, 0, 40);
        centerCap.lineStyle(4, 0xFFD700, 1);
        centerCap.strokeCircle(0, 0, 40);
        this.wheel.add(centerCap);
        
        // Add decorative bolts
        for (let i = 0; i < 8; i++) {
            const boltAngle = (i * 45) * Math.PI / 180;
            const boltX = Math.cos(boltAngle) * 25;
            const boltY = Math.sin(boltAngle) * 25;
            
            const bolt = this.add.graphics();
            bolt.fillStyle(0xC0C0C0, 1);
            bolt.fillCircle(boltX, boltY, 4);
            this.wheel.add(bolt);
        }
    }
    
    createPointer(x, y) {
        const pointer = this.add.graphics();
        
        // Pointer triangle
        pointer.fillStyle(0xFF0000, 1);
        pointer.beginPath();
        pointer.moveTo(0, 0);
        pointer.lineTo(-30, 50);
        pointer.lineTo(30, 50);
        pointer.closePath();
        pointer.fillPath();
        
        // Pointer border
        pointer.lineStyle(3, 0xFFD700, 1);
        pointer.strokePath();
        
        pointer.x = x;
        pointer.y = y;
        
        this.pointer = pointer;
        
        // Add pulsing animation
        this.tweens.add({
            targets: pointer,
            scale: { from: 1, to: 1.1 },
            duration: 500,
            yoyo: true,
            repeat: -1
        });
    }
    
    createSpinButton(x, y) {
        const spinButton = this.add.container(x, y);
        
        const bg = this.add.graphics();
        bg.fillStyle(0x00FF00, 1);
        bg.fillRoundedRect(-100, -30, 200, 60, 20);
        bg.lineStyle(4, 0xFFD700, 1);
        bg.strokeRoundedRect(-100, -30, 200, 60, 20);
        
        const text = this.add.text(0, 0, 'SPIN THE WHEEL!', {
            font: '24px Arial Black',
            fill: '#000000'
        }).setOrigin(0.5);
        
        spinButton.add([bg, text]);
        spinButton.setInteractive(new Phaser.Geom.Rectangle(-100, -30, 200, 60), Phaser.Geom.Rectangle.Contains);
        
        spinButton.on('pointerdown', () => this.spinWheel());
        spinButton.on('pointerover', () => {
            bg.clear();
            bg.fillStyle(0x00CC00, 1);
            bg.fillRoundedRect(-100, -30, 200, 60, 20);
            bg.lineStyle(4, 0xFFD700, 1);
            bg.strokeRoundedRect(-100, -30, 200, 60, 20);
        });
        spinButton.on('pointerout', () => {
            bg.clear();
            bg.fillStyle(0x00FF00, 1);
            bg.fillRoundedRect(-100, -30, 200, 60, 20);
            bg.lineStyle(4, 0xFFD700, 1);
            bg.strokeRoundedRect(-100, -30, 200, 60, 20);
        });
        
        this.spinButton = spinButton;
    }
    
    createBackButton() {
        const backButton = this.add.text(50, this.cameras.main.height - 50, '← BACK', {
            font: '24px Arial',
            fill: '#FFFFFF',
            backgroundColor: '#2C3E50',
            padding: { x: 15, y: 10 }
        });
        
        backButton.setInteractive();
        backButton.on('pointerdown', () => this.scene.start('MainMenuScene'));
    }
    
    createInfoDisplay() {
        this.resultText = this.add.text(this.cameras.main.width / 2, 150, '', {
            font: '32px Arial',
            fill: '#FFFFFF',
            stroke: '#000000',
            strokeThickness: 4
        }).setOrigin(0.5);
    }
    
    spinWheel() {
        if (this.isSpinning) return;
        
        this.isSpinning = true;
        this.resultText.setText('');
        
        // Play wheel start sound
        if (this.playAudio) {
            this.playAudio('wheelStart');
            // Start spinning sound loop
            this.time.delayedCall(200, () => {
                this.playAudio('wheelSpin', { loop: true, pitchVariation: true });
            });
        }
        
        // Calculate random spin
        const spins = Phaser.Math.Between(5, 8);
        const extraRotation = Phaser.Math.Between(0, 360);
        const totalRotation = spins * 360 + extraRotation;
        
        // Track tick timing for audio
        this.lastTickAngle = 0;
        
        // Spin animation with physics-like easing
        this.tweens.add({
            targets: this.wheel,
            rotation: this.wheel.rotation + Phaser.Math.DegToRad(totalRotation),
            duration: 4000,
            ease: 'Cubic.easeOut',
            onUpdate: (tween) => {
                // Calculate segment angle for tick sounds
                const currentAngle = Math.floor(Phaser.Math.RadToDeg(this.wheel.rotation) / 45) * 45;
                if (currentAngle !== this.lastTickAngle && tween.progress < 0.9) {
                    this.lastTickAngle = currentAngle;
                    // Play tick with pitch based on speed
                    if (this.playAudio) {
                        const pitch = 0.8 + (1 - tween.progress) * 0.4;
                        this.playAudio('wheelTick', { 
                            pitch: pitch,
                            volume: 0.3 + (1 - tween.progress) * 0.3,
                            spatial: true,
                            position: { x: 0, y: 0 }
                        });
                    }
                }
                
                // Play slowdown sound in final phase
                if (tween.progress > 0.7 && !this.slowdownPlayed) {
                    this.slowdownPlayed = true;
                    if (this.playAudio) {
                        this.playAudio('wheelSlowdown');
                    }
                }
            },
            onComplete: () => this.wheelStopped()
        });
    }
    
    wheelStopped() {
        // Play wheel stop sound
        if (this.playAudio) {
            this.playAudio('wheelStop');
        }
        
        // Reset slowdown flag
        this.slowdownPlayed = false;
        
        // Calculate which segment we landed on
        const rotation = Phaser.Math.Wrap(Phaser.Math.RadToDeg(this.wheel.rotation), 0, 360);
        const segmentAngle = 360 / this.segments.length;
        const adjustedRotation = Phaser.Math.Wrap(360 - rotation + segmentAngle / 2, 0, 360);
        const segmentIndex = Math.floor(adjustedRotation / segmentAngle);
        const segment = this.segments[segmentIndex];
        
        // Show result
        this.showResult(segment);
        
        this.isSpinning = false;
    }
    
    showResult(segment) {
        let resultMessage = '';
        let winAmount = 0;
        
        if (segment.value === 'JACKPOT') {
            resultMessage = 'JACKPOT!!! $500';
            winAmount = 500;
            // Play jackpot audio with full spatial spread
            if (this.playAudio) {
                this.playAudio('jackpotReveal', { reverb: 2.5, spread: 360 });
            }
            this.createJackpotCelebration();
        } else if (segment.value > 0) {
            resultMessage = `You Won ${segment.label}!`;
            winAmount = segment.value;
            // Play prize reveal audio
            if (this.playAudio) {
                this.playAudio('prizeReveal', { delay: 500 });
            }
            this.createWinCelebration();
        } else {
            resultMessage = 'Try Again!';
        }
        
        this.resultText.setText(resultMessage);
        
        if (winAmount > 0) {
            // Trigger game win event
            this.game.events.emit('gameWin', {
                amount: winAmount,
                gameType: 'wheel',
                winType: segment.value === 'JACKPOT' ? 'jackpot' : 'regular'
            });
        }
    }
    
    createWinCelebration() {
        const { width, height } = this.cameras.main;
        
        // Star burst
        const stars = this.add.particles(width / 2, height / 2, 'particle_star', {
            speed: { min: 200, max: 400 },
            scale: { start: 1, end: 0 },
            lifespan: 1000,
            quantity: 30,
            emitting: false
        });
        
        stars.explode();
    }
    
    createJackpotCelebration() {
        const { width, height } = this.cameras.main;
        
        // Massive celebration
        const emitters = [];
        
        // Coins from top
        emitters.push(this.add.particles(width / 2, -50, 'particle_coin', {
            x: { min: -300, max: 300 },
            speedY: { min: 200, max: 400 },
            scale: { start: 1, end: 0.5 },
            rotate: { min: 0, max: 360 },
            lifespan: 4000,
            quantity: 100,
            frequency: 20,
            gravityY: 300
        }));
        
        // Stars explosion
        emitters.push(this.add.particles(width / 2, height / 2, 'particle_star', {
            speed: { min: 300, max: 600 },
            scale: { start: 1.5, end: 0 },
            lifespan: 2000,
            quantity: 50,
            emitting: false
        }));
        
        emitters[1].explode();
        
        // Flash effect
        const flash = this.add.rectangle(width / 2, height / 2, width, height, 0xFFFFFF);
        flash.setAlpha(0);
        
        this.tweens.add({
            targets: flash,
            alpha: { from: 0, to: 0.8 },
            duration: 100,
            yoyo: true,
            onComplete: () => flash.destroy()
        });
        
        // Clean up after celebration
        this.time.delayedCall(5000, () => {
            emitters.forEach(emitter => emitter.destroy());
        });
    }
}

// Dice Game Scene
class DiceGameScene extends Phaser.Scene {
    constructor() {
        super({ key: 'DiceGameScene' });
        this.dice = [];
        this.isRolling = false;
        this.credits = 100;
        this.bet = 5;
    }
    
    create() {
        const { width, height } = this.cameras.main;
        
        // Initialize enhanced audio for dice
        if (window.PhaserAudioIntegration) {
            this.audioEnhancement = window.PhaserAudioIntegration.enhance(this, 'dice');
        }
        
        // Background
        this.createDiceBackground();
        
        // Title
        this.add.text(width / 2, 50, 'DICE ROLL', {
            font: '48px Arial Black',
            fill: '#FFD700',
            stroke: '#000000',
            strokeThickness: 6
        }).setOrigin(0.5);
        
        // Create dice table
        this.createDiceTable(width / 2, height / 2);
        
        // Create dice
        this.createDice(width / 2, height / 2);
        
        // Create controls
        this.createControls(width / 2, height - 100);
        
        // Create payout table
        this.createPayoutTable(width - 200, 150);
        
        // Info display
        this.createInfoDisplay();
        
        // Back button
        this.createBackButton();
    }
    
    createDiceBackground() {
        const { width, height } = this.cameras.main;
        
        const graphics = this.add.graphics();
        
        // Green felt background
        graphics.fillStyle(0x0F5132, 1);
        graphics.fillRect(0, 0, width, height);
        
        // Table texture
        for (let i = 0; i < 50; i++) {
            for (let j = 0; j < 30; j++) {
                graphics.fillStyle(0x0A3622, Phaser.Math.FloatBetween(0.1, 0.3));
                graphics.fillCircle(i * 30, j * 30, 2);
            }
        }
    }
    
    createDiceTable(x, y) {
        const table = this.add.graphics();
        
        // Table surface
        table.fillStyle(0x0A3622, 1);
        table.fillRoundedRect(x - 300, y - 200, 600, 400, 30);
        
        // Table border
        table.lineStyle(8, 0x8B4513, 1);
        table.strokeRoundedRect(x - 300, y - 200, 600, 400, 30);
        
        // Inner border
        table.lineStyle(4, 0xFFD700, 1);
        table.strokeRoundedRect(x - 280, y - 180, 560, 360, 25);
        
        // Betting area
        table.fillStyle(0x000000, 0.3);
        table.fillRoundedRect(x - 250, y - 150, 500, 300, 20);
    }
    
    createDice(x, y) {
        // Create two dice with physics bodies
        for (let i = 0; i < 2; i++) {
            const dieX = x - 60 + i * 120;
            const dieY = y;
            
            const die = this.matter.add.sprite(dieX, dieY, 'dice_1');
            die.setScale(1.2);
            die.setBounce(0.8);
            die.setFriction(0.5);
            
            // Add custom properties
            die.value = 1;
            die.isRolling = false;
            
            this.dice.push(die);
        }
    }
    
    createControls(x, y) {
        // Roll button
        const rollButton = this.add.container(x, y);
        
        const bg = this.add.graphics();
        bg.fillStyle(0xFF0000, 1);
        bg.fillRoundedRect(-80, -30, 160, 60, 20);
        bg.lineStyle(4, 0xFFD700, 1);
        bg.strokeRoundedRect(-80, -30, 160, 60, 20);
        
        const text = this.add.text(0, 0, 'ROLL DICE!', {
            font: '24px Arial Black',
            fill: '#FFFFFF'
        }).setOrigin(0.5);
        
        rollButton.add([bg, text]);
        rollButton.setInteractive(new Phaser.Geom.Rectangle(-80, -30, 160, 60), Phaser.Geom.Rectangle.Contains);
        
        rollButton.on('pointerdown', () => this.rollDice());
        
        this.rollButton = rollButton;
        
        // Bet controls
        this.createBetControls(x - 200, y);
    }
    
    createBetControls(x, y) {
        const betMinus = this.createButton(x - 50, y, '-', () => this.adjustBet(-5));
        const betPlus = this.createButton(x + 50, y, '+', () => this.adjustBet(5));
        
        this.betText = this.add.text(x, y, `BET: $${this.bet}`, {
            font: '24px Arial',
            fill: '#FFFFFF'
        }).setOrigin(0.5);
    }
    
    createButton(x, y, text, callback) {
        const button = this.add.container(x, y);
        
        const bg = this.add.graphics();
        bg.fillStyle(0x2C3E50, 1);
        bg.fillRoundedRect(-25, -20, 50, 40, 10);
        
        const label = this.add.text(0, 0, text, {
            font: '24px Arial',
            fill: '#FFFFFF'
        }).setOrigin(0.5);
        
        button.add([bg, label]);
        button.setInteractive(new Phaser.Geom.Rectangle(-25, -20, 50, 40), Phaser.Geom.Rectangle.Contains);
        button.on('pointerdown', callback);
        
        return button;
    }
    
    createPayoutTable(x, y) {
        const payoutBg = this.add.graphics();
        payoutBg.fillStyle(0x000000, 0.7);
        payoutBg.fillRoundedRect(x - 150, y, 300, 200, 15);
        payoutBg.lineStyle(2, 0xFFD700, 1);
        payoutBg.strokeRoundedRect(x - 150, y, 300, 200, 15);
        
        this.add.text(x, y + 20, 'PAYOUTS', {
            font: '24px Arial Black',
            fill: '#FFD700'
        }).setOrigin(0.5);
        
        const payouts = [
            { name: 'Snake Eyes (1,1)', payout: '20x' },
            { name: 'Boxcars (6,6)', payout: '15x' },
            { name: 'Lucky 7', payout: '5x' },
            { name: 'Any Doubles', payout: '3x' }
        ];
        
        payouts.forEach((payout, index) => {
            this.add.text(x - 130, y + 60 + index * 30, payout.name, {
                font: '16px Arial',
                fill: '#FFFFFF'
            });
            
            this.add.text(x + 120, y + 60 + index * 30, payout.payout, {
                font: '16px Arial',
                fill: '#00FF00'
            }).setOrigin(1, 0);
        });
    }
    
    createInfoDisplay() {
        this.creditsText = this.add.text(50, 50, `CREDITS: $${this.credits}`, {
            font: '24px Arial',
            fill: '#FFD700'
        });
        
        this.resultText = this.add.text(this.cameras.main.width / 2, 150, '', {
            font: '32px Arial',
            fill: '#FFFFFF',
            stroke: '#000000',
            strokeThickness: 4
        }).setOrigin(0.5);
    }
    
    createBackButton() {
        const backButton = this.add.text(50, this.cameras.main.height - 50, '← BACK', {
            font: '24px Arial',
            fill: '#FFFFFF',
            backgroundColor: '#2C3E50',
            padding: { x: 15, y: 10 }
        });
        
        backButton.setInteractive();
        backButton.on('pointerdown', () => this.scene.start('MainMenuScene'));
    }
    
    adjustBet(amount) {
        this.bet = Phaser.Math.Clamp(this.bet + amount, 5, 50);
        this.betText.setText(`BET: $${this.bet}`);
    }
    
    rollDice() {
        if (this.isRolling || this.credits < this.bet) return;
        
        this.isRolling = true;
        this.credits -= this.bet;
        this.creditsText.setText(`CREDITS: $${this.credits}`);
        this.resultText.setText('');
        
        // Play dice shake sound
        if (this.playAudio) {
            this.playAudio('diceShake', { loop: true, pitchVariation: true });
            // Stop shake and play throw after brief shake
            this.time.delayedCall(500, () => {
                if (this.stopAudio) this.stopAudio();
                this.playAudio('diceThrow', { spatial: true, trajectory: true });
            });
        }
        
        // Apply random force to each die
        this.dice.forEach((die, index) => {
            // Random initial velocity
            const forceX = Phaser.Math.FloatBetween(-5, 5);
            const forceY = Phaser.Math.FloatBetween(-10, -15);
            die.setVelocity(forceX, forceY);
            
            // Random rotation
            const torque = Phaser.Math.FloatBetween(-0.5, 0.5);
            die.setAngularVelocity(torque);
            
            // Start rolling animation
            die.isRolling = true;
            this.startDiceAnimation(die, index);
        });
        
        // Check result after dice settle
        this.time.delayedCall(3000, () => this.checkDiceResult());
    }
    
    startDiceAnimation(die, index) {
        // Track collisions for audio
        let lastCollisionTime = 0;
        
        // Animate through dice faces while rolling
        const animInterval = this.time.addEvent({
            delay: 100,
            callback: () => {
                if (die.isRolling) {
                    const face = Phaser.Math.Between(1, 6);
                    die.setTexture('dice_' + face);
                    die.value = face;
                    
                    // Play rolling sound when dice bounces
                    const currentTime = Date.now();
                    if (die.body.velocity.y > 2 && currentTime - lastCollisionTime > 200) {
                        lastCollisionTime = currentTime;
                        if (this.playAudio) {
                            this.playAudio('diceRoll', {
                                randomPitch: [0.8, 1.2],
                                volume: Math.min(0.6, Math.abs(die.body.velocity.y) / 20),
                                spatial: true,
                                position: { x: die.x, y: die.y }
                            });
                        }
                    }
                }
            },
            loop: true
        });
        
        // Stop animation after settling
        this.time.delayedCall(2000 + index * 200, () => {
            // Play dice land sound
            if (this.playAudio) {
                this.playAudio('diceLand', {
                    spatial: true,
                    position: { x: die.x, y: die.y },
                    surface: 'felt'
                });
            }
        });
        
        this.time.delayedCall(2500, () => {
            die.isRolling = false;
            animInterval.destroy();
            
            // Final face
            const finalFace = Phaser.Math.Between(1, 6);
            die.setTexture('dice_' + finalFace);
            die.value = finalFace;
            die.setAngularVelocity(0);
            
            // Play settle sound
            if (this.playAudio) {
                this.playAudio('diceSettle', {
                    delay: 100,
                    volume: 0.5
                });
            }
        });
    }
    
    checkDiceResult() {
        const die1 = this.dice[0].value;
        const die2 = this.dice[1].value;
        const total = die1 + die2;
        
        let winAmount = 0;
        let resultMessage = `Rolled ${die1} + ${die2} = ${total}`;
        let audioEvent = null;
        
        // Check for special combinations
        if (die1 === 1 && die2 === 1) {
            // Snake eyes
            winAmount = this.bet * 20;
            resultMessage += ' - SNAKE EYES!';
            audioEvent = 'snakeEyes';
        } else if (die1 === 6 && die2 === 6) {
            // Boxcars
            winAmount = this.bet * 15;
            resultMessage += ' - BOXCARS!';
            audioEvent = 'boxcars';
        } else if (total === 7) {
            // Lucky 7
            winAmount = this.bet * 5;
            resultMessage += ' - LUCKY 7!';
            audioEvent = 'diceWin';
        } else if (die1 === die2) {
            // Doubles
            winAmount = this.bet * 3;
            resultMessage += ' - DOUBLES!';
            audioEvent = 'diceWin';
        }
        
        this.resultText.setText(resultMessage);
        
        // Play appropriate audio event
        if (audioEvent && this.playAudio) {
            this.playAudio(audioEvent, { special: true });
        }
        
        if (winAmount > 0) {
            this.credits += winAmount;
            this.creditsText.setText(`CREDITS: $${this.credits}`);
            
            // Win animation
            this.createDiceWinEffect(winAmount);
            
            // Trigger game win event
            this.game.events.emit('gameWin', {
                amount: winAmount,
                gameType: 'dice',
                winType: winAmount >= this.bet * 10 ? 'big' : 'regular'
            });
        }
        
        this.isRolling = false;
    }
    
    createDiceWinEffect(amount) {
        const { width, height } = this.cameras.main;
        
        // Flash dice
        this.dice.forEach(die => {
            this.tweens.add({
                targets: die,
                scale: { from: 1.2, to: 1.5 },
                alpha: { from: 1, to: 0.5 },
                duration: 200,
                yoyo: true,
                repeat: 3
            });
        });
        
        // Win text
        const winText = this.add.text(width / 2, height / 2 - 100, `+$${amount}`, {
            font: '48px Arial Black',
            fill: '#00FF00',
            stroke: '#000000',
            strokeThickness: 6
        }).setOrigin(0.5);
        
        this.tweens.add({
            targets: winText,
            y: winText.y - 50,
            alpha: { from: 1, to: 0 },
            duration: 2000,
            onComplete: () => winText.destroy()
        });
    }
}

// Scratch Card Scene
class ScratchCardScene extends Phaser.Scene {
    constructor() {
        super({ key: 'ScratchCardScene' });
        this.scratchCard = null;
        this.scratchSurface = null;
        this.isScratching = false;
        this.scratchProgress = 0;
        this.prize = 0;
        this.credits = 100;
    }
    
    create() {
        const { width, height } = this.cameras.main;
        
        // Initialize enhanced audio for scratch cards
        if (window.PhaserAudioIntegration) {
            this.audioEnhancement = window.PhaserAudioIntegration.enhance(this, 'scratch');
        }
        
        // Background
        this.createScratchBackground();
        
        // Title
        this.add.text(width / 2, 50, 'SCRATCH CARDS', {
            font: '48px Arial Black',
            fill: '#FFD700',
            stroke: '#000000',
            strokeThickness: 6
        }).setOrigin(0.5);
        
        // Create scratch card
        this.createScratchCard(width / 2, height / 2);
        
        // Create controls
        this.createControls(width / 2, height - 100);
        
        // Info display
        this.createInfoDisplay();
        
        // Back button
        this.createBackButton();
    }
    
    createScratchBackground() {
        const { width, height } = this.cameras.main;
        
        const graphics = this.add.graphics();
        
        // Gradient background
        const color1 = Phaser.Display.Color.HexStringToColor('#1E3A8A');
        const color2 = Phaser.Display.Color.HexStringToColor('#312E81');
        
        for (let i = 0; i < height; i++) {
            const color = Phaser.Display.Color.Interpolate.ColorWithColor(
                color1, color2, height, i
            );
            graphics.fillStyle(color.color, 1);
            graphics.fillRect(0, i, width, 1);
        }
    }
    
    createScratchCard(x, y) {
        // Card container
        const cardContainer = this.add.container(x, y);
        
        // Card background (prize layer)
        this.scratchCard = this.add.sprite(0, 0, 'scratchCard');
        cardContainer.add(this.scratchCard);
        
        // Generate random prize
        this.generatePrize();
        
        // Prize text (hidden under scratch surface)
        const prizeText = this.add.text(0, 0, `$${this.prize}`, {
            font: '48px Arial Black',
            fill: '#FF0000',
            stroke: '#FFD700',
            strokeThickness: 4
        }).setOrigin(0.5);
        cardContainer.add(prizeText);
        
        // Create scratch surface
        this.createScratchSurface(x, y);
    }
    
    createScratchSurface(x, y) {
        // Create render texture for scratch effect
        this.scratchSurface = this.add.renderTexture(x, y, 300, 200);
        this.scratchSurface.setOrigin(0.5);
        
        // Fill with scratch surface texture
        this.scratchSurface.draw('scratchSurface', 150, 100);
        
        // Enable scratching
        this.scratchSurface.setInteractive();
        
        // Scratch brush
        const brush = this.make.graphics({ x: 0, y: 0, add: false });
        brush.fillStyle(0xFFFFFF, 1);
        brush.fillCircle(0, 0, 20);
        brush.generateTexture('brush', 40, 40);
        
        // Handle scratching
        let scratching = false;
        
        this.input.on('pointerdown', (pointer) => {
            if (this.scratchSurface.getBounds().contains(pointer.x, pointer.y)) {
                scratching = true;
                this.isScratching = true;
                // Play scratch start sound
                if (this.playAudio) {
                    this.playAudio('scratchStart');
                    // Start scratch loop
                    this.scratchLoopEvent = this.time.delayedCall(100, () => {
                        this.playAudio('scratchLoop', { loop: true, followPointer: true });
                    });
                }
            }
        });
        
        this.input.on('pointermove', (pointer) => {
            if (scratching) {
                // Convert to local coordinates
                const localX = pointer.x - this.scratchSurface.x + 150;
                const localY = pointer.y - this.scratchSurface.y + 100;
                
                // Erase (scratch) at pointer position
                this.scratchSurface.erase('brush', localX, localY);
                
                // Update scratch progress
                this.updateScratchProgress();
            }
        });
        
        this.input.on('pointerup', () => {
            if (scratching) {
                scratching = false;
                // Stop scratch loop
                if (this.stopAudio) {
                    this.stopAudio();
                }
            }
        });
    }
    
    generatePrize() {
        const prizes = [0, 5, 10, 15, 20, 25, 50, 100];
        const weights = [30, 25, 20, 10, 7, 5, 2, 1];
        
        // Weighted random selection
        const totalWeight = weights.reduce((a, b) => a + b, 0);
        let random = Phaser.Math.FloatBetween(0, totalWeight);
        
        for (let i = 0; i < prizes.length; i++) {
            random -= weights[i];
            if (random <= 0) {
                this.prize = prizes[i];
                break;
            }
        }
    }
    
    updateScratchProgress() {
        // Simple progress tracking (could be more sophisticated)
        this.scratchProgress += 0.5;
        
        // Check if card is sufficiently scratched
        if (this.scratchProgress >= 30 && !this.revealed) {
            this.revealPrize();
        }
    }
    
    revealPrize() {
        this.revealed = true;
        
        // Play reveal sound
        if (this.playAudio) {
            this.playAudio('scratchReveal');
        }
        
        // Auto-clear remaining surface
        this.tweens.add({
            targets: this.scratchSurface,
            alpha: 0,
            duration: 500,
            onComplete: () => {
                this.scratchSurface.destroy();
                // Play complete sound
                if (this.playAudio) {
                    this.playAudio('scratchComplete');
                }
                this.showPrizeResult();
            }
        });
    }
    
    showPrizeResult() {
        if (this.prize > 0) {
            this.credits += this.prize;
            this.creditsText.setText(`CREDITS: $${this.credits}`);
            
            // Play appropriate win sound
            if (this.playAudio) {
                if (this.prize >= 50) {
                    this.playAudio('bigPrize');
                } else {
                    this.playAudio('prizeWin');
                }
            }
            
            // Win animation
            this.createScratchWinEffect();
            
            // Trigger game win event
            this.game.events.emit('gameWin', {
                amount: this.prize,
                gameType: 'scratch',
                winType: this.prize >= 50 ? 'big' : 'regular'
            });
        } else {
            // No win
            this.resultText.setText('Try Again!');
        }
    }
    
    createScratchWinEffect() {
        const { width, height } = this.cameras.main;
        
        // Sparkle particles
        const sparkles = this.add.particles(width / 2, height / 2, 'particle_sparkle', {
            speed: { min: 100, max: 200 },
            scale: { start: 1, end: 0 },
            lifespan: 1000,
            quantity: 20,
            emitting: false
        });
        
        sparkles.explode();
        
        // Win message
        const winMessage = this.add.text(width / 2, height / 2 - 150, `YOU WON $${this.prize}!`, {
            font: '36px Arial Black',
            fill: '#00FF00',
            stroke: '#000000',
            strokeThickness: 6
        }).setOrigin(0.5);
        
        this.tweens.add({
            targets: winMessage,
            scale: { from: 0, to: 1.2 },
            duration: 500,
            ease: 'Back.easeOut'
        });
    }
    
    createControls(x, y) {
        const newCardButton = this.add.container(x, y);
        
        const bg = this.add.graphics();
        bg.fillStyle(0x4CAF50, 1);
        bg.fillRoundedRect(-100, -30, 200, 60, 20);
        bg.lineStyle(4, 0xFFD700, 1);
        bg.strokeRoundedRect(-100, -30, 200, 60, 20);
        
        const text = this.add.text(0, 0, 'NEW CARD ($5)', {
            font: '24px Arial Black',
            fill: '#FFFFFF'
        }).setOrigin(0.5);
        
        newCardButton.add([bg, text]);
        newCardButton.setInteractive(new Phaser.Geom.Rectangle(-100, -30, 200, 60), Phaser.Geom.Rectangle.Contains);
        
        newCardButton.on('pointerdown', () => this.getNewCard());
    }
    
    createInfoDisplay() {
        this.creditsText = this.add.text(50, 50, `CREDITS: $${this.credits}`, {
            font: '24px Arial',
            fill: '#FFD700'
        });
        
        this.resultText = this.add.text(this.cameras.main.width / 2, 150, '', {
            font: '32px Arial',
            fill: '#FFFFFF',
            stroke: '#000000',
            strokeThickness: 4
        }).setOrigin(0.5);
    }
    
    createBackButton() {
        const backButton = this.add.text(50, this.cameras.main.height - 50, '← BACK', {
            font: '24px Arial',
            fill: '#FFFFFF',
            backgroundColor: '#2C3E50',
            padding: { x: 15, y: 10 }
        });
        
        backButton.setInteractive();
        backButton.on('pointerdown', () => this.scene.start('MainMenuScene'));
    }
    
    getNewCard() {
        if (this.credits < 5) return;
        
        // Reset for new card
        this.credits -= 5;
        this.creditsText.setText(`CREDITS: $${this.credits}`);
        this.scratchProgress = 0;
        this.revealed = false;
        this.resultText.setText('');
        
        // Recreate scratch card
        this.createScratchCard(this.cameras.main.width / 2, this.cameras.main.height / 2);
    }
}

// Jackpot Celebration Scene
class JackpotCelebrationScene extends Phaser.Scene {
    constructor() {
        super({ key: 'JackpotCelebrationScene' });
    }
    
    init(data) {
        this.jackpotAmount = data.amount || 1000;
        this.gameType = data.gameType || 'unknown';
        this.playerData = data.playerData || {};
    }
    
    create() {
        const { width, height } = this.cameras.main;
        
        // Dark overlay
        const overlay = this.add.rectangle(width / 2, height / 2, width, height, 0x000000, 0.8);
        
        // Jackpot text
        const jackpotText = this.add.text(width / 2, height / 2 - 100, 'JACKPOT!!!', {
            font: '96px Arial Black',
            fill: '#FFD700',
            stroke: '#FF0000',
            strokeThickness: 10,
            shadow: {
                offsetX: 5,
                offsetY: 5,
                color: '#000000',
                blur: 15,
                fill: true
            }
        }).setOrigin(0.5);
        
        // Amount text
        const amountText = this.add.text(width / 2, height / 2, `$${this.jackpotAmount}`, {
            font: '72px Arial Black',
            fill: '#00FF00',
            stroke: '#FFFFFF',
            strokeThickness: 8
        }).setOrigin(0.5);
        
        // Game type text
        const gameText = this.add.text(width / 2, height / 2 + 80, `Won on ${this.gameType.toUpperCase()}!`, {
            font: '36px Arial',
            fill: '#FFFFFF'
        }).setOrigin(0.5);
        
        // Animations
        this.tweens.add({
            targets: jackpotText,
            scale: { from: 0, to: 1.2 },
            duration: 1000,
            ease: 'Bounce.easeOut'
        });
        
        this.tweens.add({
            targets: amountText,
            scale: { from: 0, to: 1 },
            delay: 500,
            duration: 1000,
            ease: 'Elastic.easeOut'
        });
        
        // Massive particle celebration
        this.createMassiveCelebration();
        
        // Continue button
        this.time.delayedCall(5000, () => {
            const continueBtn = this.add.text(width / 2, height - 100, 'CONTINUE', {
                font: '32px Arial',
                fill: '#FFFFFF',
                backgroundColor: '#4CAF50',
                padding: { x: 30, y: 15 }
            }).setOrigin(0.5);
            
            continueBtn.setInteractive();
            continueBtn.on('pointerdown', () => this.scene.start('MainMenuScene'));
        });
    }
    
    createMassiveCelebration() {
        const { width, height } = this.cameras.main;
        
        // Multiple coin fountains
        for (let i = 0; i < 5; i++) {
            const x = Phaser.Math.Between(100, width - 100);
            
            this.add.particles(x, height + 50, 'particle_coin', {
                speedY: { min: -800, max: -600 },
                speedX: { min: -200, max: 200 },
                scale: { start: 1.5, end: 0.5 },
                rotate: { min: 0, max: 360 },
                lifespan: 4000,
                quantity: 10,
                frequency: 100,
                gravityY: 500
            });
        }
        
        // Star explosions
        const centerX = width / 2;
        const centerY = height / 2;
        
        for (let i = 0; i < 8; i++) {
            this.time.delayedCall(i * 300, () => {
                const stars = this.add.particles(centerX, centerY, 'particle_star', {
                    speed: { min: 400, max: 800 },
                    scale: { start: 2, end: 0 },
                    lifespan: 2000,
                    quantity: 30,
                    emitting: false,
                    tint: [0xFFD700, 0xFFA500, 0xFF6347, 0xFF1493]
                });
                
                stars.explode();
            });
        }
        
        // Sparkle rain
        this.add.particles(0, 0, 'particle_sparkle', {
            x: { min: 0, max: width },
            speedY: { min: 100, max: 200 },
            scale: { start: 1, end: 0 },
            lifespan: 5000,
            quantity: 2,
            frequency: 100,
            alpha: { start: 1, end: 0 },
            blendMode: 'ADD'
        });
    }
}

// Initialize the Phaser Casino Engine when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Create container for Phaser game if it doesn't exist
    if (!document.getElementById('phaser-game-container')) {
        const container = document.createElement('div');
        container.id = 'phaser-game-container';
        container.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 9999;
            display: none;
            background: rgba(0, 0, 0, 0.95);
        `;
        document.body.appendChild(container);
    }
    
    // Initialize engine
    window.phaserCasino = new PhaserCasinoEngine();
    
    // Integration with existing system
    window.launchPhaserGame = (gameType) => {
        const container = document.getElementById('phaser-game-container');
        container.style.display = 'block';
        window.phaserCasino.launchGame(gameType);
    };
    
    window.closePhaserGame = () => {
        const container = document.getElementById('phaser-game-container');
        container.style.display = 'none';
        if (window.phaserCasino.game) {
            window.phaserCasino.game.scene.stop();
        }
    };
    
    console.log('🎮 Phaser Casino Engine ready!');
});

// Export for module use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { PhaserCasinoEngine };
}