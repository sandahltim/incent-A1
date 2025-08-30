/*!
 * Dual Game Engine JavaScript
 * Professional casino game engine with CSRF protection
 * Handles Category A and Category B game interactions
 */

class DualGameEngine {
    constructor() {
        this.csrfToken = this.getCSRFToken();
        this.employeeId = this.getEmployeeId();
        this.soundEnabled = window.soundOn || false;
        this.animations = new Map();
        this.gameStates = new Map();
        this.refreshInterval = null;
        
        this.init();
    }

    /**
     * Initialize the dual game engine
     */
    async init() {
        console.log('🎮 Initializing Dual Game Engine...');
        
        try {
            this.setupEventListeners();
            this.setupSoundSystem();
            this.startAutoRefresh();
            
            console.log('✅ Dual Game Engine Ready!');
        } catch (error) {
            console.error('❌ Failed to initialize Dual Game Engine:', error);
        }
    }

    /**
     * Get CSRF token from meta tag
     */
    getCSRFToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        if (!metaTag) {
            console.warn('⚠️ CSRF token not found in meta tags');
            return null;
        }
        return metaTag.getAttribute('content');
    }

    /**
     * Get employee ID from various sources
     */
    getEmployeeId() {
        // Try to get from data attribute
        const dashboardElement = document.querySelector('[data-employee-id]');
        if (dashboardElement) {
            return dashboardElement.getAttribute('data-employee-id');
        }
        
        // Try to get from session or other sources
        return window.employeeId || null;
    }

    /**
     * Setup event listeners for game interactions
     */
    setupEventListeners() {
        // Token exchange form
        const exchangeForm = document.getElementById('exchangeForm');
        if (exchangeForm) {
            exchangeForm.addEventListener('submit', (e) => this.handleTokenExchange(e));
        }

        // Points to exchange input
        const pointsInput = document.getElementById('pointsToExchange');
        if (pointsInput) {
            pointsInput.addEventListener('input', (e) => this.updateExchangePreview(e));
        }

        // Game buttons
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-game-action]')) {
                this.handleGameAction(e);
            }
        });

        // Modal events
        document.addEventListener('show.bs.modal', (e) => this.handleModalShow(e));
        document.addEventListener('hide.bs.modal', (e) => this.handleModalHide(e));
    }

    /**
     * Setup sound system integration
     */
    setupSoundSystem() {
        if (window.casinoAudio) {
            console.log('🔊 Casino Audio System Detected');
            this.audioEngine = window.casinoAudio;
        } else {
            console.log('🔇 No audio engine available');
            this.audioEngine = {
                playSound: (sound) => console.log(`🎵 Would play: ${sound}`),
                stopAll: () => {},
                setVolume: (vol) => {}
            };
        }
    }

    /**
     * Start auto refresh for real-time updates
     */
    startAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }

        this.refreshInterval = setInterval(async () => {
            try {
                await this.refreshEmployeeData();
            } catch (error) {
                console.error('Error during auto refresh:', error);
            }
        }, 30000); // Refresh every 30 seconds
    }

    /**
     * Handle token exchange form submission
     */
    async handleTokenExchange(event) {
        event.preventDefault();
        
        if (!this.validateCSRF()) return;

        const formData = new FormData(event.target);
        const pointsToExchange = parseInt(formData.get('points_amount') || 0);

        if (pointsToExchange <= 0) {
            this.showNotification('Please enter a valid amount of points', 'error');
            return;
        }

        this.showLoadingOverlay(true);

        try {
            const response = await fetch('/api/dual_game/exchange', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    employee_id: this.employeeId,
                    points_amount: pointsToExchange
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showNotification(`Successfully exchanged ${pointsToExchange} points for ${result.tokens_received} tokens!`, 'success');
                this.audioEngine.playSound('cash-register');
                this.triggerCelebration('exchange');
                
                // Reset form
                event.target.reset();
                this.updateExchangePreview({ target: { value: '' } });
                
                // Refresh data
                await this.refreshEmployeeData();
            } else {
                this.showNotification(result.error || 'Exchange failed', 'error');
                this.audioEngine.playSound('notification-error');
            }
        } catch (error) {
            console.error('Token exchange error:', error);
            this.showNotification('Exchange failed. Please try again.', 'error');
            this.audioEngine.playSound('notification-error');
        } finally {
            this.showLoadingOverlay(false);
        }
    }

    /**
     * Update exchange preview calculation
     */
    updateExchangePreview(event) {
        const pointsAmount = parseInt(event.target.value) || 0;
        const exchangeRateElement = document.getElementById('exchangeRate');
        const tokensPreview = document.getElementById('tokensToReceive');
        
        if (!exchangeRateElement || !tokensPreview) return;

        const exchangeRate = parseInt(exchangeRateElement.textContent) || 10;
        const tokensToReceive = Math.floor(pointsAmount / exchangeRate);
        
        tokensPreview.textContent = `${tokensToReceive} Tokens`;
        tokensPreview.style.color = tokensToReceive > 0 ? '#32cd32' : '#ffd700';
    }

    /**
     * Handle various game actions
     */
    async handleGameAction(event) {
        event.preventDefault();
        
        const action = event.target.getAttribute('data-game-action');
        const gameType = event.target.getAttribute('data-game-type');
        const gameId = event.target.getAttribute('data-game-id');

        switch (action) {
            case 'play-category-a':
                await this.playCategoryAGame(gameId);
                break;
            case 'play-category-b':
                await this.playCategoryBGame(gameType);
                break;
            case 'set-bet':
                this.setBetAmount(gameType, event.target.getAttribute('data-bet-amount'));
                break;
            default:
                console.log(`Unknown game action: ${action}`);
        }
    }

    /**
     * Play Category A (guaranteed win) game
     */
    async playCategoryAGame(gameId) {
        if (!this.validateCSRF()) return;
        if (!gameId) {
            this.showNotification('Invalid game selection', 'error');
            return;
        }

        this.showLoadingOverlay(true, 'Playing your guaranteed win game...');

        try {
            const response = await fetch(`/api/dual_game/play/${gameId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    employee_id: this.employeeId,
                    game_type: 'category_a'
                })
            });

            const result = await response.json();

            if (response.ok && result.success) {
                await this.showGameResult({
                    type: 'category-a',
                    win: true,
                    prize: result.prize,
                    message: result.message
                });
                
                this.audioEngine.playSound('fanfare-1');
                this.triggerCelebration('category-a-win');
                
                // Refresh data and remove played game
                await this.refreshEmployeeData();
                this.removePlayedGame(gameId);
            } else {
                this.showNotification(result.message || 'Game failed to play', 'error');
                this.audioEngine.playSound('notification-error');
            }
        } catch (error) {
            console.error('Category A game error:', error);
            this.showNotification('Game failed. Please try again.', 'error');
            this.audioEngine.playSound('notification-error');
        } finally {
            this.showLoadingOverlay(false);
        }
    }

    /**
     * Play Category B (gambling) game
     */
    async playCategoryBGame(gameType) {
        if (!this.validateCSRF()) return;
        if (!gameType) {
            this.showNotification('Invalid game type', 'error');
            return;
        }

        const betAmount = this.getBetAmount(gameType);
        if (!betAmount || betAmount <= 0) {
            this.showNotification('Please set a valid bet amount', 'error');
            return;
        }

        // Check token balance
        const tokenBalance = this.getCurrentTokenBalance();
        if (betAmount > tokenBalance) {
            this.showNotification('Insufficient tokens for this bet', 'error');
            return;
        }

        this.disableGameControls(gameType);
        
        try {
            // Animate the game first
            await this.animateGame(gameType);
            
            // Then process the actual bet
            const response = await fetch(`/api/dual_game/play/${gameType}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    employee_id: this.employeeId,
                    bet_amount: betAmount,
                    game_type: 'category_b'
                })
            });

            const result = await response.json();

            if (response.ok) {
                await this.showGameResult({
                    type: 'category-b',
                    gameType: gameType,
                    win: result.win,
                    betAmount: betAmount,
                    winAmount: result.tokens_won || 0,
                    lossAmount: result.tokens_lost || betAmount,
                    message: result.message
                });

                if (result.win) {
                    this.audioEngine.playSound('casino-win');
                    this.triggerCelebration('category-b-win');
                } else {
                    this.audioEngine.playSound('notification-warning');
                }

                // Refresh data
                await this.refreshEmployeeData();
            } else {
                this.showNotification(result.error || 'Game failed', 'error');
                this.audioEngine.playSound('notification-error');
            }
        } catch (error) {
            console.error('Category B game error:', error);
            this.showNotification('Game failed. Please try again.', 'error');
            this.audioEngine.playSound('notification-error');
        } finally {
            this.enableGameControls(gameType);
        }
    }

    /**
     * Animate specific game types
     */
    async animateGame(gameType) {
        switch (gameType) {
            case 'slots':
                return await this.animateSlots();
            case 'dice':
                return await this.animateDice();
            case 'wheel':
                return await this.animateWheel();
            case 'blackjack':
                return await this.animateBlackjack();
            default:
                return await new Promise(resolve => setTimeout(resolve, 1000));
        }
    }

    /**
     * Animate slot machine
     */
    async animateSlots() {
        const reels = document.querySelectorAll('.slot-reel');
        if (!reels.length) return;

        const symbols = ['🍒', '🍋', '🔔', '⭐', '💎', '7️⃣', '🍊', '🎰'];
        
        this.audioEngine.playSound('slot-reel-start');
        
        // Start spinning all reels
        reels.forEach(reel => {
            reel.classList.add('reel-spinning');
        });

        // Stop reels one by one with delay
        for (let i = 0; i < reels.length; i++) {
            await new Promise(resolve => setTimeout(resolve, 500 + (i * 300)));
            
            reels[i].classList.remove('reel-spinning');
            reels[i].textContent = symbols[Math.floor(Math.random() * symbols.length)];
            
            this.audioEngine.playSound(`slot-reel-stop-${i + 1}`);
        }
    }

    /**
     * Animate dice game
     */
    async animateDice() {
        const dice1 = document.getElementById('dice1');
        const dice2 = document.getElementById('dice2');
        
        if (!dice1 || !dice2) return;

        const diceSymbols = ['⚀', '⚁', '⚂', '⚃', '⚄', '⚅'];
        
        dice1.classList.add('rolling');
        dice2.classList.add('rolling');
        
        this.audioEngine.playSound('dice-shake');
        
        // Roll animation
        let rollCount = 0;
        const rollInterval = setInterval(() => {
            dice1.textContent = diceSymbols[Math.floor(Math.random() * 6)];
            dice2.textContent = diceSymbols[Math.floor(Math.random() * 6)];
            rollCount++;
            
            if (rollCount >= 15) {
                clearInterval(rollInterval);
                dice1.classList.remove('rolling');
                dice2.classList.remove('rolling');
                
                // Final result
                const die1Value = Math.floor(Math.random() * 6);
                const die2Value = Math.floor(Math.random() * 6);
                dice1.textContent = diceSymbols[die1Value];
                dice2.textContent = diceSymbols[die2Value];

                this.audioEngine.playSound('dice-land');
            }
        }, 100);

        return new Promise(resolve => setTimeout(resolve, 2000));
    }

    /**
     * Animate wheel of fortune
     */
    async animateWheel() {
        const wheel = document.getElementById('fortuneWheel');
        if (!wheel) return;

        wheel.classList.add('spinning');
        this.audioEngine.playSound('wheel-start');

        await new Promise(resolve => setTimeout(resolve, 3000));
        
        wheel.classList.remove('spinning');
        
        // Random final rotation
        const finalRotation = Math.floor(Math.random() * 360) + 1440; // At least 4 full rotations
        wheel.style.transform = `rotate(${finalRotation}deg)`;

        this.audioEngine.playSound('wheel-stop');
    }

    /**
     * Animate blackjack (simple version)
     */
    async animateBlackjack() {
        // For blackjack, we'd implement card dealing animation
        // This is a simplified version
        this.audioEngine.playSound('card-shuffle');
        await new Promise(resolve => setTimeout(resolve, 1500));
    }

    /**
     * Show game result modal
     */
    async showGameResult(result) {
        const resultModal = this.createResultModal(result);
        document.body.appendChild(resultModal);
        
        // Show with animation
        requestAnimationFrame(() => {
            resultModal.style.display = 'flex';
            resultModal.classList.add('fade-in');
        });

        // Auto-close after 5 seconds or wait for user interaction
        return new Promise(resolve => {
            const closeBtn = resultModal.querySelector('.close-result-btn');
            const autoCloseTimeout = setTimeout(() => {
                this.closeResultModal(resultModal);
                resolve();
            }, 5000);

            closeBtn.addEventListener('click', () => {
                clearTimeout(autoCloseTimeout);
                this.closeResultModal(resultModal);
                resolve();
            });
        });
    }

    /**
     * Create result modal element
     */
    createResultModal(result) {
        const modal = document.createElement('div');
        modal.className = 'game-result-overlay';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;

        const isWin = result.win;
        const bgGradient = isWin ? 
            'linear-gradient(145deg, #1a4d1a, #2d4d2d)' : 
            'linear-gradient(145deg, #4d1a1a, #2d2d2d)';
        const borderColor = isWin ? '#32cd32' : '#dc143c';
        const textColor = isWin ? '#32cd32' : '#dc143c';

        modal.innerHTML = `
            <div class="game-result-content" style="
                background: ${bgGradient};
                border: 3px solid ${borderColor};
                border-radius: 20px;
                padding: 40px;
                text-align: center;
                color: #fff;
                max-width: 500px;
                width: 90%;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.8);
            ">
                <div class="result-icon" style="font-size: 4rem; margin-bottom: 20px;">
                    ${isWin ? '🎉' : '😔'}
                </div>
                <h2 class="result-title" style="color: ${textColor}; margin-bottom: 20px; font-size: 2rem;">
                    ${isWin ? 'CONGRATULATIONS!' : 'Better Luck Next Time!'}
                </h2>
                <div class="result-details" style="font-size: 1.2rem; margin: 20px 0;">
                    ${this.formatResultDetails(result)}
                </div>
                <button class="close-result-btn btn-casino" style="margin-top: 20px;">
                    Continue Playing
                </button>
            </div>
        `;

        // Add fade in animation
        setTimeout(() => {
            modal.style.opacity = '1';
        }, 10);

        return modal;
    }

    /**
     * Format result details based on game type
     */
    formatResultDetails(result) {
        if (result.type === 'category-a') {
            return `
                <div>🎁 Prize: <strong>${result.prize || 'Special Reward'}</strong></div>
                <div style="margin-top: 10px; color: #ffd700;">
                    ${result.message || 'Your guaranteed prize has been added to your account!'}
                </div>
            `;
        } else {
            if (result.win) {
                return `
                    <div>💰 Bet: <strong>${result.betAmount} tokens</strong></div>
                    <div style="color: #32cd32; font-size: 1.5rem; margin: 10px 0;">
                        Won: <strong>+${result.winAmount} tokens</strong>
                    </div>
                    <div>Net Gain: <strong style="color: #32cd32;">+${result.winAmount - result.betAmount} tokens</strong></div>
                `;
            } else {
                return `
                    <div>💸 Bet Lost: <strong>${result.lossAmount} tokens</strong></div>
                    <div style="margin-top: 10px; color: #ffd700;">
                        ${result.message || 'Try again with better luck!'}
                    </div>
                `;
            }
        }
    }

    /**
     * Close result modal
     */
    closeResultModal(modal) {
        modal.style.opacity = '0';
        setTimeout(() => {
            if (modal.parentNode) {
                modal.parentNode.removeChild(modal);
            }
        }, 300);
    }

    /**
     * Trigger celebration effects
     */
    triggerCelebration(type) {
        switch (type) {
            case 'exchange':
                this.triggerConfetti('#ffd700', '#ff6b35');
                break;
            case 'category-a-win':
                this.triggerConfetti('#32cd32', '#90ee90');
                this.createFloatingText('GUARANTEED WIN! 🎁', '#32cd32');
                break;
            case 'category-b-win':
                this.triggerConfetti('#dc143c', '#ff6347');
                this.createFloatingText('JACKPOT! 💰', '#ffd700');
                break;
        }
    }

    /**
     * Trigger confetti effect
     */
    triggerConfetti(primaryColor, secondaryColor) {
        if (window.confetti) {
            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 },
                colors: [primaryColor, secondaryColor, '#fff']
            });
        }
    }

    /**
     * Create floating text animation
     */
    createFloatingText(text, color) {
        const floatingText = document.createElement('div');
        floatingText.textContent = text;
        floatingText.style.cssText = `
            position: fixed;
            top: 30%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 3rem;
            font-weight: bold;
            color: ${color};
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            z-index: 9999;
            pointer-events: none;
            animation: floatUp 3s ease-out forwards;
        `;

        // Add CSS animation
        if (!document.getElementById('floatingTextStyles')) {
            const style = document.createElement('style');
            style.id = 'floatingTextStyles';
            style.textContent = `
                @keyframes floatUp {
                    0% { opacity: 1; transform: translate(-50%, -50%) scale(0.8); }
                    50% { opacity: 1; transform: translate(-50%, -60%) scale(1.2); }
                    100% { opacity: 0; transform: translate(-50%, -80%) scale(1.4); }
                }
            `;
            document.head.appendChild(style);
        }

        document.body.appendChild(floatingText);
        
        setTimeout(() => {
            if (floatingText.parentNode) {
                floatingText.parentNode.removeChild(floatingText);
            }
        }, 3000);
    }

    /**
     * Utility Methods
     */
    validateCSRF() {
        if (!this.csrfToken) {
            this.showNotification('Security token missing. Please refresh the page.', 'error');
            return false;
        }
        return true;
    }

    getBetAmount(gameType) {
        const betInput = document.getElementById(`${gameType}Bet`);
        return betInput ? parseInt(betInput.value) || 0 : 0;
    }

    setBetAmount(gameType, amount) {
        const betInput = document.getElementById(`${gameType}Bet`);
        if (betInput) {
            betInput.value = amount;
        }
    }

    getCurrentTokenBalance() {
        const balanceElement = document.getElementById('tokenBalance');
        return balanceElement ? parseInt(balanceElement.textContent) || 0 : 0;
    }

    disableGameControls(gameType) {
        const gameContainer = document.getElementById(`${gameType}Game`);
        if (gameContainer) {
            const buttons = gameContainer.querySelectorAll('button');
            buttons.forEach(btn => btn.disabled = true);
        }
    }

    enableGameControls(gameType) {
        const gameContainer = document.getElementById(`${gameType}Game`);
        if (gameContainer) {
            const buttons = gameContainer.querySelectorAll('button');
            buttons.forEach(btn => btn.disabled = false);
        }
    }

    removePlayedGame(gameId) {
        const gameCard = document.querySelector(`[data-game-id="${gameId}"]`);
        if (gameCard) {
            gameCard.style.transition = 'opacity 0.5s ease';
            gameCard.style.opacity = '0';
            setTimeout(() => {
                if (gameCard.parentNode) {
                    gameCard.parentNode.removeChild(gameCard);
                }
            }, 500);
        }
    }

    async refreshEmployeeData() {
        if (!this.employeeId) return;

        try {
            const response = await fetch(`/dual-games/api/employee-stats/${this.employeeId}`);
            const data = await response.json();
            
            if (response.ok) {
                this.updateDashboardData(data);
            }
        } catch (error) {
            console.error('Error refreshing employee data:', error);
        }
    }

    updateDashboardData(data) {
        // Update balance displays
        const elements = {
            pointsBalance: data.points_balance,
            tokenBalance: data.token_balance,
            exchangeRate: data.exchange_rate,
            winRate: data.win_rate,
            categoryBOdds: data.win_odds
        };

        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element && value !== undefined) {
                element.textContent = value;
            }
        });

        // Update tier badge
        const tierElement = document.getElementById('userTier');
        if (tierElement && data.tier) {
            tierElement.textContent = data.tier.toUpperCase();
            tierElement.className = `tier-badge tier-${data.tier.toLowerCase()}`;
        }
    }

    handleModalShow(event) {
        const modal = event.target;
        const modalId = modal.id;
        
        if (modalId === 'categoryAModal') {
            this.loadCategoryAContent();
        } else if (modalId === 'categoryBModal') {
            this.loadCategoryBContent();
        }
    }

    handleModalHide(event) {
        // Cleanup when modals are hidden
        this.stopAllAnimations();
    }

    async loadCategoryAContent() {
        const content = document.getElementById('categoryAContent');
        if (!content) return;

        content.innerHTML = '<div class="text-center"><div class="casino-spinner"></div><p>Loading Category A games...</p></div>';

        try {
            const response = await fetch(`/dual-games/api/available-games/${this.employeeId}`);
            const data = await response.json();
            
            if (response.ok && data.category_a) {
                this.renderCategoryAGames(data.category_a);
            } else {
                content.innerHTML = '<div class="text-center"><p>No Category A games available at this time.</p></div>';
            }
        } catch (error) {
            console.error('Error loading Category A games:', error);
            content.innerHTML = '<div class="text-center"><p class="text-danger">Error loading games. Please try again.</p></div>';
        }
    }

    async loadCategoryBContent() {
        const content = document.getElementById('categoryBContent');
        if (!content) return;

        // Category B games are always available, so we can render them immediately
        this.renderCategoryBGames();
    }

    renderCategoryAGames(games) {
        const content = document.getElementById('categoryAContent');
        if (!content) return;

        if (games.length === 0) {
            content.innerHTML = '<div class="text-center"><p>No Category A games available. Check back later!</p></div>';
            return;
        }

        content.innerHTML = games.map(game => `
            <div class="casino-card category-a-card mb-3">
                <h5 class="text-center mb-3">${game.name}</h5>
                <p>${game.description}</p>
                <div class="prize-info mb-3">
                    <strong>Prize:</strong> ${game.prize_type} - ${game.prize_value}
                </div>
                <button class="btn-casino btn-category-a w-100" 
                        data-game-action="play-category-a" 
                        data-game-id="${game.id}">
                    🎁 Play & Win Now!
                </button>
            </div>
        `).join('');
    }

    renderCategoryBGames() {
        const content = document.getElementById('categoryBContent');
        if (!content) return;

        // This would normally come from the API, but for now we'll use the existing HTML
        // The Category B games are already rendered in the template
    }

    stopAllAnimations() {
        // Stop any running animations
        document.querySelectorAll('.reel-spinning, .rolling, .spinning').forEach(element => {
            element.classList.remove('reel-spinning', 'rolling', 'spinning');
        });
    }

    showLoadingOverlay(show, message = 'Processing...') {
        let overlay = document.getElementById('loadingOverlay');
        
        if (show) {
            if (!overlay) {
                overlay = document.createElement('div');
                overlay.id = 'loadingOverlay';
                overlay.style.cssText = `
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(0, 0, 0, 0.8);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    z-index: 9998;
                    color: #fff;
                `;
                overlay.innerHTML = `
                    <div class="text-center">
                        <div class="casino-spinner large"></div>
                        <h4 class="mt-3">${message}</h4>
                    </div>
                `;
                document.body.appendChild(overlay);
            }
            overlay.style.display = 'flex';
        } else {
            if (overlay) {
                overlay.style.display = 'none';
            }
        }
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `casino-toast ${type}`;
        notification.textContent = message;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    // Cleanup method
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        this.stopAllAnimations();
    }
}

// Global instance for external access
let dualGameEngine = null;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if we're on a dual game page
    if (document.querySelector('[data-dual-game]') || 
        document.body.classList.contains('dual-game-body') ||
        window.location.pathname.includes('dual-games')) {
        
        console.log('🎮 Dual Game page detected, initializing engine...');
        dualGameEngine = new DualGameEngine();
        
        // Make it globally accessible
        window.dualGameEngine = dualGameEngine;
    }
});

// Cleanup on page unload
window.addEventListener('beforeunload', function() {
    if (dualGameEngine) {
        dualGameEngine.destroy();
    }
});