// fortune-wheel.js
// Fortune Wheel Game - Vegas Casino Edition
// Professional wheel spinning game with physics simulation

class FortuneWheel {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.canvas = null;
        this.ctx = null;
        this.isSpinning = false;
        this.currentRotation = 0;
        this.targetRotation = 0;
        this.spinVelocity = 0;
        this.audioEngine = window.casinoAudio || null;
        
        // Wheel segments with prizes and probabilities
        this.segments = [
            { value: 5, label: '$5', color: '#FF6B6B', weight: 30, textColor: '#FFF' },
            { value: 10, label: '$10', color: '#4ECDC4', weight: 25, textColor: '#FFF' },
            { value: 25, label: '$25', color: '#45B7D1', weight: 15, textColor: '#FFF' },
            { value: 50, label: '$50', color: '#96CEB4', weight: 10, textColor: '#FFF' },
            { value: 100, label: '$100', color: '#FFD700', weight: 5, textColor: '#000' },
            { value: 'FREE', label: 'FREE SPIN', color: '#00FF7F', weight: 8, textColor: '#000' },
            { value: 'DOUBLE', label: '2X NEXT', color: '#FFA500', weight: 6, textColor: '#FFF' },
            { value: 'JACKPOT', label: 'JACKPOT', color: '#FF00FF', weight: 1, textColor: '#FFF' }
        ];
        
        this.totalWeight = this.segments.reduce((sum, seg) => sum + seg.weight, 0);
        this.wheelRadius = 200;
        this.centerX = 250;
        this.centerY = 250;
        
        this.init();
    }
    
    init() {
        this.createCanvas();
        this.drawWheel();
        this.setupEventListeners();
        this.createUI();
    }
    
    createCanvas() {
        this.canvas = document.createElement('canvas');
        this.canvas.width = 500;
        this.canvas.height = 500;
        this.canvas.style.border = '3px solid #FFD700';
        this.canvas.style.borderRadius = '50%';
        this.canvas.style.boxShadow = '0 0 30px rgba(255, 215, 0, 0.5)';
        this.ctx = this.canvas.getContext('2d');
        
        this.container.appendChild(this.canvas);
    }
    
    createUI() {
        const controls = document.createElement('div');
        controls.className = 'wheel-controls';
        controls.innerHTML = `
            <button id="spinWheel" class="btn btn-vegas spin-button">
                🎡 SPIN THE WHEEL! 🎡
            </button>
            <div class="wheel-stats">
                <div class="last-win">Last Win: <span id="lastWin">-</span></div>
                <div class="total-spins">Total Spins: <span id="totalSpins">0</span></div>
            </div>
        `;
        
        // Add CSS for the controls
        const style = document.createElement('style');
        style.textContent = `
            .wheel-controls {
                text-align: center;
                margin-top: 20px;
            }
            
            .spin-button {
                background: linear-gradient(45deg, #FFD700, #FFA500);
                border: 3px solid #FF6B35;
                color: #000;
                font-size: 1.2rem;
                font-weight: bold;
                padding: 15px 30px;
                border-radius: 25px;
                cursor: pointer;
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(255, 215, 0, 0.4);
                animation: pulseGlow 2s infinite;
            }
            
            .spin-button:hover:not(:disabled) {
                transform: scale(1.05);
                box-shadow: 0 8px 25px rgba(255, 215, 0, 0.6);
            }
            
            .spin-button:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                animation: none;
            }
            
            @keyframes pulseGlow {
                0%, 100% { box-shadow: 0 5px 15px rgba(255, 215, 0, 0.4); }
                50% { box-shadow: 0 5px 25px rgba(255, 215, 0, 0.8); }
            }
            
            .wheel-stats {
                display: flex;
                justify-content: space-around;
                margin-top: 15px;
                padding: 10px;
                background: rgba(0, 0, 0, 0.7);
                border-radius: 10px;
                color: #FFD700;
                font-weight: bold;
            }
            
            .pointer {
                position: absolute;
                top: -15px;
                left: 50%;
                transform: translateX(-50%);
                width: 0;
                height: 0;
                border-left: 15px solid transparent;
                border-right: 15px solid transparent;
                border-top: 30px solid #FF0000;
                z-index: 10;
                filter: drop-shadow(0 2px 5px rgba(0,0,0,0.5));
            }
        `;
        document.head.appendChild(style);
        
        this.container.style.position = 'relative';
        this.container.appendChild(controls);
        
        // Create pointer
        const pointer = document.createElement('div');
        pointer.className = 'pointer';
        this.container.appendChild(pointer);
    }
    
    setupEventListeners() {
        // Will be set up after UI creation
        setTimeout(() => {
            const spinButton = document.getElementById('spinWheel');
            if (spinButton) {
                spinButton.addEventListener('click', () => this.spin());
            }
        }, 100);
    }
    
    drawWheel() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        const angleStep = (2 * Math.PI) / this.segments.length;
        
        this.segments.forEach((segment, index) => {
            const startAngle = (index * angleStep) + this.currentRotation;
            const endAngle = ((index + 1) * angleStep) + this.currentRotation;
            
            // Draw segment
            this.ctx.beginPath();
            this.ctx.moveTo(this.centerX, this.centerY);
            this.ctx.arc(this.centerX, this.centerY, this.wheelRadius, startAngle, endAngle);
            this.ctx.closePath();
            this.ctx.fillStyle = segment.color;
            this.ctx.fill();
            
            // Draw segment border
            this.ctx.strokeStyle = '#FFF';
            this.ctx.lineWidth = 2;
            this.ctx.stroke();
            
            // Draw text
            this.ctx.save();
            this.ctx.translate(this.centerX, this.centerY);
            this.ctx.rotate(startAngle + angleStep / 2);
            this.ctx.fillStyle = segment.textColor;
            this.ctx.font = 'bold 16px Arial';
            this.ctx.textAlign = 'center';
            this.ctx.fillText(segment.label, this.wheelRadius * 0.7, 5);
            this.ctx.restore();
        });
        
        // Draw center circle
        this.ctx.beginPath();
        this.ctx.arc(this.centerX, this.centerY, 20, 0, 2 * Math.PI);
        this.ctx.fillStyle = '#FFD700';
        this.ctx.fill();
        this.ctx.strokeStyle = '#FFA500';
        this.ctx.lineWidth = 3;
        this.ctx.stroke();
    }
    
    async spin() {
        if (this.isSpinning) return;
        
        this.isSpinning = true;
        const spinButton = document.getElementById('spinWheel');
        if (spinButton) {
            spinButton.disabled = true;
            spinButton.textContent = '🌟 SPINNING... 🌟';
        }
        
        // Play spin sound
        if (this.audioEngine) {
            await this.audioEngine.play('wheelSpin', { volume: 0.8 });
        }
        
        // Determine result
        const winningSegment = this.selectWinningSegment();
        const targetAngle = this.calculateTargetAngle(winningSegment);
        
        // Spin animation
        const spins = 5 + Math.random() * 3; // 5-8 full rotations
        this.targetRotation = this.currentRotation + (spins * 2 * Math.PI) + targetAngle;
        
        // Animate the spin
        await this.animateSpin();
        
        // Process result
        await this.processResult(this.segments[winningSegment]);
        
        this.isSpinning = false;
        if (spinButton) {
            spinButton.disabled = false;
            spinButton.textContent = '🎡 SPIN THE WHEEL! 🎡';
        }
    }
    
    selectWinningSegment() {
        const random = Math.random() * this.totalWeight;
        let accumulator = 0;
        
        for (let i = 0; i < this.segments.length; i++) {
            accumulator += this.segments[i].weight;
            if (random <= accumulator) {
                return i;
            }
        }
        
        return 0; // Fallback
    }
    
    calculateTargetAngle(segmentIndex) {
        const angleStep = (2 * Math.PI) / this.segments.length;
        const segmentCenter = (segmentIndex + 0.5) * angleStep;
        // Point to top (12 o'clock position)
        return (2 * Math.PI) - segmentCenter + (Math.PI / 2);
    }
    
    async animateSpin() {
        return new Promise((resolve) => {
            const startRotation = this.currentRotation;
            const totalRotation = this.targetRotation - startRotation;
            const duration = 4000; // 4 seconds
            const startTime = Date.now();
            
            const animate = () => {
                const elapsed = Date.now() - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Ease out cubic for realistic deceleration
                const easeProgress = 1 - Math.pow(1 - progress, 3);
                
                this.currentRotation = startRotation + (totalRotation * easeProgress);
                this.drawWheel();
                
                // Play tick sounds
                if (this.audioEngine && elapsed % 100 < 16) { // Every ~100ms
                    this.audioEngine.play('wheelTick', { volume: 0.3 });
                }
                
                if (progress < 1) {
                    requestAnimationFrame(animate);
                } else {
                    resolve();
                }
            };
            
            animate();
        });
    }
    
    async processResult(result) {
        console.log('Wheel Result:', result);
        
        // Update stats
        const totalSpinsEl = document.getElementById('totalSpins');
        const lastWinEl = document.getElementById('lastWin');
        
        if (totalSpinsEl) {
            const currentSpins = parseInt(totalSpinsEl.textContent) || 0;
            totalSpinsEl.textContent = currentSpins + 1;
        }
        
        if (lastWinEl) {
            lastWinEl.textContent = result.label;
        }
        
        // Play result sound and show celebration
        if (result.value === 'JACKPOT') {
            if (this.audioEngine) {
                await this.audioEngine.play('winJackpot', { volume: 1.0 });
            }
            this.showCelebration('🎊 JACKPOT! 🎊', '#FF00FF');
        } else if (typeof result.value === 'number' && result.value >= 50) {
            if (this.audioEngine) {
                await this.audioEngine.play('winBig', { volume: 0.9 });
            }
            this.showCelebration(`💰 BIG WIN! ${result.label} 💰`, '#FFD700');
        } else if (result.value === 'FREE' || result.value === 'DOUBLE') {
            if (this.audioEngine) {
                await this.audioEngine.play('winMedium', { volume: 0.7 });
            }
            this.showCelebration(`🎁 BONUS! ${result.label} 🎁`, '#00FF7F');
        } else {
            if (this.audioEngine) {
                await this.audioEngine.play('winSmall', { volume: 0.6 });
            }
            this.showCelebration(`✨ You Won ${result.label}! ✨`, '#4ECDC4');
        }
        
        // Submit to backend if it's a monetary win
        if (typeof result.value === 'number') {
            await this.submitWin(result.value, 'wheel');
        }
    }
    
    showCelebration(message, color) {
        const celebration = document.createElement('div');
        celebration.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: linear-gradient(45deg, ${color}, #FFF);
            color: #000;
            padding: 20px 40px;
            border-radius: 20px;
            font-size: 1.5rem;
            font-weight: bold;
            text-align: center;
            z-index: 1000;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            animation: celebrationPop 3s ease-out forwards;
        `;
        
        celebration.textContent = message;
        document.body.appendChild(celebration);
        
        // Add animation keyframes
        if (!document.getElementById('celebration-styles')) {
            const style = document.createElement('style');
            style.id = 'celebration-styles';
            style.textContent = `
                @keyframes celebrationPop {
                    0% {
                        transform: translate(-50%, -50%) scale(0.5);
                        opacity: 0;
                    }
                    20% {
                        transform: translate(-50%, -50%) scale(1.2);
                        opacity: 1;
                    }
                    80% {
                        transform: translate(-50%, -50%) scale(1);
                        opacity: 1;
                    }
                    100% {
                        transform: translate(-50%, -50%) scale(0.8);
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
        }, 3000);
    }
    
    async submitWin(amount, gameType) {
        try {
            const response = await fetch('/submit_win', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').getAttribute('content')
                },
                body: JSON.stringify({
                    amount: amount,
                    game_type: gameType,
                    details: `Fortune Wheel win: $${amount}`
                })
            });
            
            if (response.ok) {
                const result = await response.json();
                console.log('Win submitted successfully:', result);
            } else {
                console.error('Failed to submit win:', await response.text());
            }
        } catch (error) {
            console.error('Error submitting win:', error);
        }
    }
}

// Auto-initialize if container exists
document.addEventListener('DOMContentLoaded', () => {
    const wheelContainer = document.getElementById('fortune-wheel-container');
    if (wheelContainer) {
        window.fortuneWheel = new FortuneWheel('fortune-wheel-container');
    }
});