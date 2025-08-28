// minigames-controller.js
// Main controller for the enhanced Vegas casino minigames

class MinigamesController {
    constructor() {
        this.currentGame = null;
        this.playerStats = {
            points: 0,
            gamesPlayed: 0,
            totalWinnings: 0,
            currentStreak: 0
        };
        this.challenges = {
            gamesProgress: 0,
            winsProgress: 0,
            streakProgress: 0
        };
        this.progressiveJackpot = 500.00;
        this.jackpotTimer = null;
        
        this.init();
    }
    
    init() {
        this.loadPlayerStats();
        this.startJackpotTimer();
        this.initializeAudioFeedback();
        this.setupEventListeners();
        this.updateDisplays();
    }
    
    setupEventListeners() {
        // Listen for wins from individual games
        document.addEventListener('gameWin', (event) => {
            this.handleGameWin(event.detail);
        });
        
        // Listen for game completions
        document.addEventListener('gameComplete', (event) => {
            this.handleGameComplete(event.detail);
        });
        
        // Jackpot updates
        document.addEventListener('jackpotUpdate', (event) => {
            this.updateJackpot(event.detail.amount);
        });
    }
    
    loadPlayerStats() {
        // Load from localStorage or server
        const saved = localStorage.getItem('minigamesStats');
        if (saved) {
            this.playerStats = { ...this.playerStats, ...JSON.parse(saved) };
        }
    }
    
    savePlayerStats() {
        localStorage.setItem('minigamesStats', JSON.stringify(this.playerStats));
    }
    
    handleGameWin(winData) {
        const { amount, gameType, winType } = winData;
        
        // Update player stats
        this.playerStats.totalWinnings += amount;
        this.playerStats.currentStreak++;
        
        // Update challenges
        this.challenges.winsProgress++;
        this.challenges.streakProgress = Math.max(this.challenges.streakProgress, this.playerStats.currentStreak);
        
        // Check for jackpot trigger
        if (Math.random() < 0.001) { // 0.1% chance
            this.triggerJackpot(gameType);
        }
        
        // Add to recent wins
        this.addRecentWin(amount, gameType);
        
        // Update displays
        this.updateDisplays();
        this.checkChallenges();
        this.savePlayerStats();
        
        // Celebrate big wins
        if (amount >= 50) {
            this.celebrateBigWin(amount, gameType);
        }
    }
    
    handleGameComplete(gameData) {
        const { gameType, won } = gameData;
        
        this.playerStats.gamesPlayed++;
        
        // Track different games played
        const playedGames = JSON.parse(localStorage.getItem('playedGames') || '[]');
        if (!playedGames.includes(gameType)) {
            playedGames.push(gameType);
            localStorage.setItem('playedGames', JSON.stringify(playedGames));
            this.challenges.gamesProgress = playedGames.length;
        }
        
        // Reset streak on loss
        if (!won) {
            this.playerStats.currentStreak = 0;
        }
        
        this.updateDisplays();
        this.checkChallenges();
        this.savePlayerStats();
    }
    
    updateDisplays() {
        // Update player stats display
        const pointsEl = document.getElementById('playerPoints');
        const gamesPlayedEl = document.getElementById('gamesPlayed');
        const totalWinningsEl = document.getElementById('totalWinnings');
        
        if (pointsEl) pointsEl.textContent = this.playerStats.points;
        if (gamesPlayedEl) gamesPlayedEl.textContent = this.playerStats.gamesPlayed;
        if (totalWinningsEl) totalWinningsEl.textContent = `$${this.playerStats.totalWinnings.toFixed(2)}`;
        
        // Update challenge progress
        const gamesProgressEl = document.getElementById('gamesProgress');
        const winsProgressEl = document.getElementById('winsProgress');
        const streakProgressEl = document.getElementById('streakProgress');
        
        if (gamesProgressEl) gamesProgressEl.textContent = `${this.challenges.gamesProgress}/3`;
        if (winsProgressEl) winsProgressEl.textContent = `${this.challenges.winsProgress}/5`;
        if (streakProgressEl) streakProgressEl.textContent = `${this.challenges.streakProgress}/3`;
        
        // Update jackpot display
        const jackpotEl = document.getElementById('progressiveJackpot');
        if (jackpotEl) jackpotEl.textContent = `$${this.progressiveJackpot.toFixed(2)}`;
    }
    
    checkChallenges() {
        // Check if challenges are completed
        if (this.challenges.gamesProgress >= 3) {
            this.completeChallenge('games', 15);
        }
        
        if (this.challenges.winsProgress >= 5) {
            this.completeChallenge('wins', 25);
        }
        
        if (this.challenges.streakProgress >= 3) {
            this.completeChallenge('streak', 30);
        }
    }
    
    completeChallenge(type, reward) {
        const completed = JSON.parse(localStorage.getItem('completedChallenges') || '[]');
        const today = new Date().toDateString();
        const challengeKey = `${type}_${today}`;
        
        if (!completed.includes(challengeKey)) {
            completed.push(challengeKey);
            localStorage.setItem('completedChallenges', JSON.stringify(completed));
            
            this.playerStats.points += reward;
            this.showChallengeComplete(type, reward);
        }
    }
    
    showChallengeComplete(type, reward) {
        const celebration = document.createElement('div');
        celebration.style.cssText = `
            position: fixed;
            top: 20%;
            right: 20px;
            background: linear-gradient(45deg, #4ECDC4, #45B7D1);
            color: white;
            padding: 1rem 2rem;
            border-radius: 15px;
            font-weight: bold;
            z-index: 10000;
            animation: slideInRight 0.5s ease-out, fadeOut 0.5s ease-in 3s forwards;
            box-shadow: 0 10px 30px rgba(76, 205, 196, 0.5);
        `;
        
        celebration.innerHTML = `
            <div style="font-size: 1.2rem;">🎯 Challenge Complete!</div>
            <div style="margin-top: 0.5rem;">+${reward} points</div>
        `;
        
        document.body.appendChild(celebration);
        
        // Add animations
        if (!document.getElementById('challenge-styles')) {
            const style = document.createElement('style');
            style.id = 'challenge-styles';
            style.textContent = `
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes fadeOut {
                    to { opacity: 0; transform: translateX(100%); }
                }
            `;
            document.head.appendChild(style);
        }
        
        setTimeout(() => {
            if (celebration.parentNode) {
                celebration.parentNode.removeChild(celebration);
            }
        }, 4000);
    }
    
    triggerJackpot(gameType) {
        const jackpotAmount = this.progressiveJackpot;
        
        // Reset progressive jackpot
        this.progressiveJackpot = 500.00;
        this.updateDisplays();
        
        // Show massive celebration
        this.showJackpotCelebration(jackpotAmount, gameType);
        
        // Add to player winnings
        this.playerStats.totalWinnings += jackpotAmount;
        this.savePlayerStats();
        
        // Play jackpot sound
        if (window.casinoAudio) {
            window.casinoAudio.play('winJackpot', { volume: 1.0 });
        }
        
        // Add to recent wins
        this.addRecentWin(jackpotAmount, gameType, 'JACKPOT');
    }
    
    showJackpotCelebration(amount, gameType) {
        const celebration = document.createElement('div');
        celebration.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(255, 215, 0, 0.9);
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            z-index: 20000;
            animation: jackpotCelebration 6s ease-out forwards;
        `;
        
        celebration.innerHTML = `
            <div style="font-family: 'Orbitron', monospace; font-size: 4rem; font-weight: 900; color: #FF6B35; text-shadow: 3px 3px 6px rgba(0,0,0,0.5); margin-bottom: 2rem; animation: jackpotBounce 1s ease-in-out infinite;">
                🏆 JACKPOT! 🏆
            </div>
            <div style="font-size: 3rem; font-weight: bold; color: #000; margin-bottom: 1rem;">
                $${amount.toFixed(2)}
            </div>
            <div style="font-size: 1.5rem; color: #333; text-transform: uppercase;">
                Winner on ${gameType}!
            </div>
        `;
        
        document.body.appendChild(celebration);
        
        // Add jackpot animation
        if (!document.getElementById('jackpot-styles')) {
            const style = document.createElement('style');
            style.id = 'jackpot-styles';
            style.textContent = `
                @keyframes jackpotCelebration {
                    0% { opacity: 0; transform: scale(0.5); }
                    15% { opacity: 1; transform: scale(1.1); }
                    85% { opacity: 1; transform: scale(1); }
                    100% { opacity: 0; transform: scale(0.8); }
                }
                @keyframes jackpotBounce {
                    0%, 100% { transform: scale(1) rotateZ(0deg); }
                    50% { transform: scale(1.1) rotateZ(2deg); }
                }
            `;
            document.head.appendChild(style);
        }
        
        setTimeout(() => {
            if (celebration.parentNode) {
                celebration.parentNode.removeChild(celebration);
            }
        }, 6000);
    }
    
    celebrateBigWin(amount, gameType) {
        // Trigger confetti effect
        if (window.confetti) {
            window.confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 }
            });
        }
        
        // Play celebration sound
        if (window.casinoAudio) {
            window.casinoAudio.play('winBig', { volume: 0.9 });
        }
    }
    
    addRecentWin(amount, gameType, special = null) {
        const winsFeed = document.getElementById('winsFeed');
        if (!winsFeed) return;
        
        const winItem = document.createElement('div');
        winItem.className = 'win-item';
        
        const specialText = special ? ` ${special}` : '';
        winItem.innerHTML = `
            <span class="winner">You</span> won 
            <span class="amount">$${amount.toFixed(2)}</span>${specialText} on 
            <span class="game">${gameType}</span>!
        `;
        
        winsFeed.insertBefore(winItem, winsFeed.firstChild);
        
        // Keep only last 10 wins
        const wins = winsFeed.children;
        while (wins.length > 10) {
            winsFeed.removeChild(wins[wins.length - 1]);
        }
        
        // Highlight new win
        winItem.style.animation = 'newWinHighlight 3s ease-out';
        
        if (!document.getElementById('win-highlight-styles')) {
            const style = document.createElement('style');
            style.id = 'win-highlight-styles';
            style.textContent = `
                @keyframes newWinHighlight {
                    0% { background: rgba(255, 215, 0, 0.5); transform: scale(1.02); }
                    100% { background: rgba(255, 215, 0, 0.1); transform: scale(1); }
                }
            `;
            document.head.appendChild(style);
        }
    }
    
    startJackpotTimer() {
        // Progressive jackpot grows over time
        this.jackpotTimer = setInterval(() => {
            this.progressiveJackpot += 0.25; // Grows by $0.25 every second
            
            const timerEl = document.getElementById('jackpotTimer');
            if (timerEl) {
                const nextDrop = new Date(Date.now() + (Math.random() * 3600000)); // Random time within next hour
                const minutes = Math.floor((nextDrop - Date.now()) / 60000);
                const seconds = Math.floor(((nextDrop - Date.now()) % 60000) / 1000);
                timerEl.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
            
            this.updateDisplays();
        }, 1000);
    }
    
    initializeAudioFeedback() {
        // Set up audio feedback for UI interactions
        document.addEventListener('click', (event) => {
            if (event.target.classList.contains('play-game-btn') || 
                event.target.classList.contains('back-btn')) {
                if (window.casinoAudio) {
                    window.casinoAudio.play('uiHover', { volume: 0.3 });
                }
            }
        });
    }
    
    updateJackpot(increment) {
        this.progressiveJackpot += increment;
        this.updateDisplays();
    }
}

// Game navigation functions
function showGame(gameId) {
    const gameSelection = document.querySelector('.games-grid');
    const gameArea = document.getElementById('gameArea');
    const gameContainer = document.getElementById(`${gameId}-container`);
    const gameTitle = document.getElementById('currentGameTitle');
    const gameInstructions = document.getElementById('gameInstructions');
    
    // Hide game selection
    if (gameSelection) gameSelection.style.display = 'none';
    
    // Show game area
    if (gameArea) gameArea.style.display = 'block';
    
    // Hide all game containers
    document.querySelectorAll('.game-container').forEach(container => {
        container.style.display = 'none';
    });
    
    // Show selected game
    if (gameContainer) gameContainer.style.display = 'block';
    
    // Update title and instructions
    const gameInfo = {
        'fortune-wheel': {
            title: '🎡 Fortune Wheel',
            instructions: 'Click the spin button to spin the wheel! Land on prizes, bonuses, or the JACKPOT!'
        },
        'enhanced-dice': {
            title: '🎲 3D Dice Roll',
            instructions: 'Roll the dice for Snake Eyes ($100), Boxcars ($75), Lucky Seven ($25), or Doubles ($15)!'
        },
        'vegas-slots': {
            title: '🎰 Vegas Slots',
            instructions: 'Spin the reels and match symbols to win! Three of a kind pays the most!'
        },
        'scratch-cards': {
            title: '🎟️ Scratch Cards',
            instructions: 'Click to scratch off the card and reveal your prize!'
        }
    };
    
    const info = gameInfo[gameId] || { title: 'Game', instructions: 'Have fun!' };
    if (gameTitle) gameTitle.textContent = info.title;
    if (gameInstructions) gameInstructions.textContent = info.instructions;
    
    // Play selection sound
    if (window.casinoAudio) {
        window.casinoAudio.play('uiHover', { volume: 0.5 });
    }
}

function showGameSelection() {
    const gameSelection = document.querySelector('.games-grid');
    const gameArea = document.getElementById('gameArea');
    
    if (gameSelection) gameSelection.style.display = 'grid';
    if (gameArea) gameArea.style.display = 'none';
}

// Enhanced slots functions
function spinSlots() {
    const reels = document.querySelectorAll('#vegas-slots-container .reel');
    const spinButton = document.querySelector('#vegas-slots-container .spin-button');
    
    if (!reels.length || !spinButton) return;
    
    spinButton.disabled = true;
    spinButton.textContent = '🌟 SPINNING... 🌟';
    
    const symbols = ['🍒', '🍋', '⭐', '💎', '🔔', '🍇', '🎰'];
    const results = [];
    
    reels.forEach((reel, index) => {
        reel.classList.add('spinning');
        
        setTimeout(() => {
            const symbol = symbols[Math.floor(Math.random() * symbols.length)];
            results.push(symbol);
            reel.textContent = symbol;
            reel.classList.remove('spinning');
            
            // Check for win when all reels stop
            if (results.length === reels.length) {
                setTimeout(() => {
                    checkSlotWin(results);
                    spinButton.disabled = false;
                    spinButton.textContent = '🎰 SPIN THE REELS! 🎰';
                }, 500);
            }
        }, 1000 + (index * 500));
    });
    
    // Update spin count
    const totalSpinsEl = document.getElementById('totalSpins');
    if (totalSpinsEl) {
        const currentSpins = parseInt(totalSpinsEl.textContent) || 0;
        totalSpinsEl.textContent = currentSpins + 1;
    }
}

function checkSlotWin(results) {
    const lastWinEl = document.getElementById('lastSlotWin');
    let won = false;
    let winAmount = 0;
    
    // Check for three of a kind
    if (results[0] === results[1] && results[1] === results[2]) {
        won = true;
        winAmount = 50;
        if (lastWinEl) lastWinEl.textContent = `3x ${results[0]} - $${winAmount}`;
    }
    // Check for two of a kind
    else if (results[0] === results[1] || results[1] === results[2] || results[0] === results[2]) {
        won = true;
        winAmount = 10;
        if (lastWinEl) lastWinEl.textContent = `2x Match - $${winAmount}`;
    }
    else {
        if (lastWinEl) lastWinEl.textContent = 'No Win';
    }
    
    if (won && window.minigamesController) {
        window.minigamesController.handleGameWin({
            amount: winAmount,
            gameType: 'Vegas Slots',
            winType: 'slot_win'
        });
    }
    
    // Dispatch game complete event
    document.dispatchEvent(new CustomEvent('gameComplete', {
        detail: { gameType: 'Vegas Slots', won: won }
    }));
}

// Scratch card functions
function newScratchCard() {
    const scratchCard = document.getElementById('scratchCard');
    const scratchSurface = scratchCard?.querySelector('.scratch-surface');
    const hiddenPrize = scratchCard?.querySelector('.hidden-prize');
    
    if (!scratchSurface || !hiddenPrize) return;
    
    // Reset card
    scratchSurface.style.opacity = '1';
    scratchSurface.textContent = 'Scratch Here!';
    
    // Generate random prize
    const prizes = ['$5', '$10', '$15', '$25', '$50'];
    const randomPrize = prizes[Math.floor(Math.random() * prizes.length)];
    hiddenPrize.textContent = randomPrize;
    
    // Add scratch effect
    scratchCard.onclick = () => {
        scratchSurface.style.opacity = '0';
        const amount = parseInt(randomPrize.replace('$', ''));
        
        if (window.minigamesController) {
            window.minigamesController.handleGameWin({
                amount: amount,
                gameType: 'Scratch Cards',
                winType: 'scratch_win'
            });
        }
        
        // Dispatch game complete event
        document.dispatchEvent(new CustomEvent('gameComplete', {
            detail: { gameType: 'Scratch Cards', won: true }
        }));
    };
}

// Initialize controller when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.minigamesController = new MinigamesController();
    
    // Initialize scratch card
    newScratchCard();
});