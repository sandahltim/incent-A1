// Vegas Casino Confetti Implementation - Performance Optimized
let lastConfettiTime = 0;
let activeConfettiCount = 0;
const MAX_ACTIVE_CONFETTI = 150; // Global limit to prevent performance issues
const MIN_CONFETTI_INTERVAL = 500; // Minimum 500ms between confetti bursts

function confetti(opts = {}) {
    // Performance throttling - prevent rapid fire confetti
    const now = Date.now();
    if (now - lastConfettiTime < MIN_CONFETTI_INTERVAL) {
        console.log('Confetti throttled to prevent performance issues');
        return;
    }
    
    // Reduced default particle count for better performance
    const defaults = {
        particleCount: 30, // Reduced from 100 to 30
        spread: 70,
        origin: { y: 0.6 }
    };
    
    const options = { ...defaults, ...opts };
    
    // Limit total confetti particles on screen
    if (activeConfettiCount >= MAX_ACTIVE_CONFETTI) {
        console.log('Max confetti limit reached, skipping burst');
        return;
    }
    
    lastConfettiTime = now;
    
    // Create confetti burst with reduced intervals for smoother performance
    for (let i = 0; i < options.particleCount; i++) {
        setTimeout(() => {
            createConfettiPiece(options.origin, options.spread);
        }, i * 20); // Increased from 10ms to 20ms to reduce intensity
    }
}

function createConfettiPiece(origin, spread) {
    // Check if we're at the limit
    if (activeConfettiCount >= MAX_ACTIVE_CONFETTI) {
        return;
    }
    
    activeConfettiCount++;
    
    const confetti = document.createElement('div');
    confetti.className = 'confetti-particle';
    confetti.style.cssText = `
        position: fixed;
        width: 8px;
        height: 8px;
        background: ${getRandomColor()};
        pointer-events: none;
        z-index: 10000;
        border-radius: ${Math.random() > 0.5 ? '50%' : '2px'};
    `;
    
    // Calculate position
    const centerX = (origin.x || 0.5) * window.innerWidth;
    const centerY = (origin.y || 0.5) * window.innerHeight;
    
    // Random spread
    const angle = (Math.random() - 0.5) * spread * (Math.PI / 180);
    const velocity = 80 + Math.random() * 120; // Reduced velocity range
    const vx = Math.cos(angle) * velocity;
    const vy = Math.sin(angle) * velocity - Math.random() * 80;
    
    confetti.style.left = centerX + 'px';
    confetti.style.top = centerY + 'px';
    
    document.body.appendChild(confetti);
    
    // Animate with optimized performance
    let posX = 0;
    let posY = 0;
    let velX = vx;
    let velY = vy;
    let gravity = 600; // Reduced gravity for smoother animation
    let animationFrames = 0;
    const maxFrames = 180; // Limit animation frames to ~3 seconds at 60fps
    
    const animate = () => {
        if (animationFrames >= maxFrames) {
            confetti.remove();
            activeConfettiCount--;
            return;
        }
        
        const dt = 0.016; // ~60fps
        
        velY += gravity * dt;
        posX += velX * dt;
        posY += velY * dt;
        animationFrames++;
        
        // Use transform3d for better GPU acceleration
        confetti.style.transform = `translate3d(${posX}px, ${posY}px, 0) rotate(${posX}deg)`;
        confetti.style.opacity = Math.max(0, 1 - (posY / window.innerHeight));
        
        if (posY < window.innerHeight && confetti.style.opacity > 0.1) {
            requestAnimationFrame(animate);
        } else {
            confetti.remove();
            activeConfettiCount--;
        }
    };
    
    requestAnimationFrame(animate);
}

function getRandomColor() {
    const colors = ['#FFD700', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFA500'];
    return colors[Math.floor(Math.random() * colors.length)];
}

// Performance monitoring function
function getConfettiStats() {
    return {
        activeCount: activeConfettiCount,
        maxCount: MAX_ACTIVE_CONFETTI,
        lastTriggerTime: lastConfettiTime,
        throttleInterval: MIN_CONFETTI_INTERVAL
    };
}

// Emergency cleanup function
function clearAllConfetti() {
    const particles = document.querySelectorAll('.confetti-particle');
    particles.forEach(particle => particle.remove());
    activeConfettiCount = 0;
    console.log('All confetti cleared for performance');
}

// Make it globally available
window.confetti = confetti;
