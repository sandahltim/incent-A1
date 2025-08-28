// enhanced-dice.js
// 3D Dice Rolling Game - Vegas Casino Edition
// Physics-based dice animation with realistic effects

class Enhanced3DDice {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.isRolling = false;
        this.diceValues = [1, 1];
        this.audioEngine = window.casinoAudio || null;
        this.rollHistory = [];
        
        this.init();
    }
    
    init() {
        this.createDiceElements();
        this.setupEventListeners();
        this.createUI();
    }
    
    createDiceElements() {
        const diceContainer = document.createElement('div');
        diceContainer.className = 'dice-container';
        diceContainer.innerHTML = `
            <div class="dice-table">
                <div class="dice dice-1" id="dice1">
                    <div class="face face-1">⚀</div>
                    <div class="face face-2">⚁</div>
                    <div class="face face-3">⚂</div>
                    <div class="face face-4">⚃</div>
                    <div class="face face-5">⚄</div>
                    <div class="face face-6">⚅</div>
                </div>
                <div class="dice dice-2" id="dice2">
                    <div class="face face-1">⚀</div>
                    <div class="face face-2">⚁</div>
                    <div class="face face-3">⚂</div>
                    <div class="face face-4">⚃</div>
                    <div class="face face-5">⚄</div>
                    <div class="face face-6">⚅</div>
                </div>
            </div>
            <div class="dice-shadow-1"></div>
            <div class="dice-shadow-2"></div>
        `;
        
        this.container.appendChild(diceContainer);
        this.addDiceStyles();
    }
    
    addDiceStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .dice-container {
                perspective: 1000px;
                display: flex;
                flex-direction: column;
                align-items: center;
                padding: 40px;
            }
            
            .dice-table {
                display: flex;
                gap: 40px;
                margin-bottom: 20px;
                position: relative;
            }
            
            .dice {
                width: 60px;
                height: 60px;
                position: relative;
                transform-style: preserve-3d;
                transition: transform 0.1s;
                cursor: pointer;
            }
            
            .dice:hover {
                transform: scale(1.05) rotateY(5deg) rotateX(5deg);
            }
            
            .face {
                position: absolute;
                width: 60px;
                height: 60px;
                background: linear-gradient(135deg, #fff, #f0f0f0);
                border: 3px solid #333;
                border-radius: 8px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 2rem;
                font-weight: bold;
                color: #333;
                box-shadow: inset 2px 2px 4px rgba(0,0,0,0.1);
            }
            
            .face-1 { transform: rotateY(0deg) translateZ(30px); }
            .face-2 { transform: rotateY(90deg) translateZ(30px); }
            .face-3 { transform: rotateY(180deg) translateZ(30px); }
            .face-4 { transform: rotateY(-90deg) translateZ(30px); }
            .face-5 { transform: rotateX(90deg) translateZ(30px); }
            .face-6 { transform: rotateX(-90deg) translateZ(30px); }
            
            .dice-shadow-1, .dice-shadow-2 {
                width: 60px;
                height: 60px;
                background: radial-gradient(ellipse, rgba(0,0,0,0.3), transparent);
                border-radius: 50%;
                position: absolute;
                bottom: -10px;
                transition: all 0.3s ease;
            }
            
            .dice-shadow-1 { left: calc(50% - 50px); }
            .dice-shadow-2 { left: calc(50% + 10px); }
            
            .rolling .dice {
                animation: diceRoll 2s ease-out;
            }
            
            .rolling .dice-1 {
                animation-delay: 0s;
            }
            
            .rolling .dice-2 {
                animation-delay: 0.1s;
            }
            
            @keyframes diceRoll {
                0% {
                    transform: rotateX(0deg) rotateY(0deg) rotateZ(0deg) translateY(0px);
                }
                25% {
                    transform: rotateX(180deg) rotateY(180deg) rotateZ(90deg) translateY(-30px);
                }
                50% {
                    transform: rotateX(360deg) rotateY(360deg) rotateZ(180deg) translateY(-20px);
                }
                75% {
                    transform: rotateX(540deg) rotateY(540deg) rotateZ(270deg) translateY(-10px);
                }
                90% {
                    transform: rotateX(700deg) rotateY(700deg) rotateZ(360deg) translateY(-5px);
                }
                100% {
                    transform: rotateX(720deg) rotateY(720deg) rotateZ(360deg) translateY(0px);
                }
            }
            
            .bounce {
                animation: diceBounce 0.6s ease-out;
            }
            
            @keyframes diceBounce {
                0% { transform: translateY(0px) scale(1); }
                30% { transform: translateY(-15px) scale(1.1); }
                60% { transform: translateY(-5px) scale(1.05); }
                100% { transform: translateY(0px) scale(1); }
            }
            
            .roll-button {
                background: linear-gradient(45deg, #FF6B35, #FF8E53);
                border: 3px solid #FF4500;
                color: white;
                font-size: 1.3rem;
                font-weight: bold;
                padding: 15px 40px;
                border-radius: 30px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 6px 20px rgba(255, 107, 53, 0.4);
                margin: 20px 0;
            }
            
            .roll-button:hover:not(:disabled) {
                transform: translateY(-2px) scale(1.05);
                box-shadow: 0 8px 25px rgba(255, 107, 53, 0.6);
            }
            
            .roll-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .dice-stats {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-top: 20px;
                padding: 15px;
                background: rgba(0, 0, 0, 0.8);
                border-radius: 10px;
                color: #FFD700;
                font-weight: bold;
                min-width: 300px;
            }
            
            .stat-item {
                text-align: center;
                padding: 8px;
                background: rgba(255, 215, 0, 0.1);
                border-radius: 5px;
            }
            
            .last-roll {
                font-size: 1.5rem;
                color: #00FF7F;
            }
            
            .winning-combination {
                background: linear-gradient(45deg, #FFD700, #FFA500);
                color: #000;
                animation: winGlow 1s ease-in-out infinite alternate;
            }
            
            @keyframes winGlow {
                from { box-shadow: 0 0 5px rgba(255, 215, 0, 0.5); }
                to { box-shadow: 0 0 20px rgba(255, 215, 0, 1); }
            }
        `;
        document.head.appendChild(style);
    }
    
    createUI() {
        const controls = document.createElement('div');
        controls.className = 'dice-controls';
        controls.innerHTML = `
            <button id="rollDice" class="roll-button">
                🎲 ROLL THE DICE! 🎲
            </button>
            <div class="dice-stats">
                <div class="stat-item">
                    <div>Last Roll</div>
                    <div class="last-roll" id="lastRoll">-</div>
                </div>
                <div class="stat-item">
                    <div>Total Rolls</div>
                    <div id="totalRolls">0</div>
                </div>
                <div class="stat-item">
                    <div>Wins</div>
                    <div id="totalWins">0</div>
                </div>
                <div class="stat-item">
                    <div>Win Rate</div>
                    <div id="winRate">0%</div>
                </div>
            </div>
        `;
        
        this.container.appendChild(controls);
    }
    
    setupEventListeners() {
        setTimeout(() => {
            const rollButton = document.getElementById('rollDice');
            if (rollButton) {
                rollButton.addEventListener('click', () => this.rollDice());
            }
            
            // Click on dice to roll
            document.querySelectorAll('.dice').forEach(dice => {
                dice.addEventListener('click', () => {
                    if (!this.isRolling) this.rollDice();
                });
            });
        }, 100);
    }
    
    async rollDice() {
        if (this.isRolling) return;
        
        this.isRolling = true;
        const rollButton = document.getElementById('rollDice');
        
        if (rollButton) {
            rollButton.disabled = true;
            rollButton.textContent = '🌟 ROLLING... 🌟';
        }
        
        // Play shake sound
        if (this.audioEngine) {
            await this.audioEngine.play('diceShake', { volume: 0.7 });
        }
        
        // Generate random values
        this.diceValues = [
            Math.floor(Math.random() * 6) + 1,
            Math.floor(Math.random() * 6) + 1
        ];
        
        // Start rolling animation
        const diceContainer = document.querySelector('.dice-table');
        diceContainer.classList.add('rolling');
        
        // Play rolling sound
        if (this.audioEngine) {
            setTimeout(() => {
                this.audioEngine.play('diceRoll1', { volume: 0.8 });
            }, 200);
        }
        
        // Wait for animation to complete
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // Stop rolling animation
        diceContainer.classList.remove('rolling');
        
        // Set final dice positions
        this.setDicePosition('dice1', this.diceValues[0]);
        this.setDicePosition('dice2', this.diceValues[1]);
        
        // Play landing sound
        if (this.audioEngine) {
            await this.audioEngine.play('diceLand', { volume: 0.9 });
        }
        
        // Add bounce effect
        document.querySelectorAll('.dice').forEach(dice => {
            dice.classList.add('bounce');
            setTimeout(() => dice.classList.remove('bounce'), 600);
        });
        
        // Process result
        await this.processRollResult();
        
        this.isRolling = false;
        if (rollButton) {
            rollButton.disabled = false;
            rollButton.textContent = '🎲 ROLL THE DICE! 🎲';
        }
    }
    
    setDicePosition(diceId, value) {
        const dice = document.getElementById(diceId);
        if (!dice) return;
        
        const rotations = {
            1: 'rotateX(0deg) rotateY(0deg)',
            2: 'rotateX(0deg) rotateY(-90deg)',
            3: 'rotateX(0deg) rotateY(-180deg)',
            4: 'rotateX(0deg) rotateY(90deg)',
            5: 'rotateX(-90deg) rotateY(0deg)',
            6: 'rotateX(90deg) rotateY(0deg)'
        };
        
        dice.style.transform = rotations[value] || rotations[1];
    }
    
    async processRollResult() {
        const sum = this.diceValues[0] + this.diceValues[1];
        const isDoubles = this.diceValues[0] === this.diceValues[1];
        const isSnakeEyes = sum === 2;
        const isBoxcars = sum === 12;
        const isLuckySeven = sum === 7;
        
        // Update stats
        this.updateStats(sum);
        
        let winType = null;
        let prize = 0;
        let message = '';
        
        // Determine win conditions (matching backend logic)
        if (isSnakeEyes) {
            winType = 'snake_eyes';
            prize = 100;
            message = '🐍 SNAKE EYES! 🐍';
        } else if (isBoxcars) {
            winType = 'boxcars';
            prize = 75;
            message = '📦 BOXCARS! 📦';
        } else if (isLuckySeven) {
            winType = 'lucky_seven';
            prize = 25;
            message = '🍀 LUCKY SEVEN! 🍀';
        } else if (isDoubles) {
            winType = 'doubles';
            prize = 15;
            message = `🎯 DOUBLES ${this.diceValues[0]}! 🎯`;
        }
        
        if (winType) {
            this.showWinCelebration(message, prize);
            
            // Play appropriate win sound
            if (this.audioEngine) {
                if (prize >= 75) {
                    await this.audioEngine.play('winBig', { volume: 1.0 });
                } else if (prize >= 25) {
                    await this.audioEngine.play('winMedium', { volume: 0.8 });
                } else {
                    await this.audioEngine.play('winSmall', { volume: 0.6 });
                }
            }
            
            // Submit win to backend
            await this.submitWin(prize, winType);
        } else {
            // Play settle sound for losing rolls
            if (this.audioEngine) {
                setTimeout(() => {
                    this.audioEngine.play('diceSettle', { volume: 0.5 });
                }, 300);
            }
        }
    }
    
    updateStats(sum) {
        const totalRollsEl = document.getElementById('totalRolls');
        const lastRollEl = document.getElementById('lastRoll');
        const totalWinsEl = document.getElementById('totalWins');
        const winRateEl = document.getElementById('winRate');
        
        // Update roll history
        this.rollHistory.push({
            dice1: this.diceValues[0],
            dice2: this.diceValues[1],
            sum: sum,
            timestamp: Date.now()
        });
        
        // Keep only last 100 rolls
        if (this.rollHistory.length > 100) {
            this.rollHistory = this.rollHistory.slice(-100);
        }
        
        const totalRolls = this.rollHistory.length;
        const totalWins = this.rollHistory.filter(roll => 
            roll.sum === 2 || roll.sum === 12 || roll.sum === 7 || 
            roll.dice1 === roll.dice2
        ).length;
        
        if (totalRollsEl) totalRollsEl.textContent = totalRolls;
        if (lastRollEl) {
            lastRollEl.textContent = `${this.diceValues[0]} + ${this.diceValues[1]} = ${sum}`;
            lastRollEl.className = 'last-roll' + (totalWins > 0 && this.rollHistory[this.rollHistory.length - 1] === this.rollHistory.filter(roll => 
                roll.sum === 2 || roll.sum === 12 || roll.sum === 7 || 
                roll.dice1 === roll.dice2
            ).slice(-1)[0] ? ' winning-combination' : '');
        }
        if (totalWinsEl) totalWinsEl.textContent = totalWins;
        if (winRateEl) {
            const winRate = totalRolls > 0 ? Math.round((totalWins / totalRolls) * 100) : 0;
            winRateEl.textContent = `${winRate}%`;
        }
    }
    
    showWinCelebration(message, prize) {
        const celebration = document.createElement('div');
        celebration.style.cssText = `
            position: fixed;
            top: 30%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(45deg, #FFD700, #FFA500, #FFD700);
            color: #000;
            padding: 25px 50px;
            border-radius: 25px;
            font-size: 1.8rem;
            font-weight: bold;
            text-align: center;
            z-index: 1000;
            box-shadow: 0 15px 40px rgba(0,0,0,0.4);
            animation: diceWinPop 4s ease-out forwards;
            border: 3px solid #FF6B35;
        `;
        
        celebration.innerHTML = `
            <div>${message}</div>
            <div style="font-size: 1.2rem; margin-top: 10px; color: #FF6B35;">
                💰 $${prize} WIN! 💰
            </div>
        `;
        
        document.body.appendChild(celebration);
        
        // Add animation keyframes
        if (!document.getElementById('dice-celebration-styles')) {
            const style = document.createElement('style');
            style.id = 'dice-celebration-styles';
            style.textContent = `
                @keyframes diceWinPop {
                    0% {
                        transform: translate(-50%, -50%) scale(0.3) rotateZ(-10deg);
                        opacity: 0;
                    }
                    15% {
                        transform: translate(-50%, -50%) scale(1.3) rotateZ(5deg);
                        opacity: 1;
                    }
                    30% {
                        transform: translate(-50%, -50%) scale(1) rotateZ(0deg);
                        opacity: 1;
                    }
                    85% {
                        transform: translate(-50%, -50%) scale(1) rotateZ(0deg);
                        opacity: 1;
                    }
                    100% {
                        transform: translate(-50%, -50%) scale(0.8) rotateZ(0deg);
                        opacity: 0;
                    }
                }
            `;
            document.head.appendChild(style);
        }
        
        // Remove after animation
        setTimeout(() => {
            if (celebration.parentNode) {
                celebration.parentNode.removeChild(celebration);
            }
        }, 4000);
    }
    
    async submitWin(amount, winType) {
        try {
            const response = await fetch('/submit_win', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    amount: amount,
                    game_type: 'dice',
                    win_type: winType,
                    dice_values: this.diceValues,
                    details: `Dice ${winType}: ${this.diceValues[0]} + ${this.diceValues[1]} = ${this.diceValues[0] + this.diceValues[1]}`
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Dice win submitted successfully:', result);
            } else {
                console.error('Failed to submit dice win:', await response.text());
            }
        } catch (error) {
            console.error('Error submitting dice win:', error);
        }
    }
}

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
    const diceContainer = document.getElementById('enhanced-dice-container');
    if (diceContainer) {
        window.enhancedDice = new Enhanced3DDice('enhanced-dice-container');
    }
});