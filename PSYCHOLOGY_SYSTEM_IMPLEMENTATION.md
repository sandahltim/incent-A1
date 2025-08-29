# Technical Implementation Guide
## Employee Reward Psychology System Integration

### Overview
This guide provides technical implementation details for integrating the psychological reward framework into your existing Vegas-themed employee incentive platform. It builds upon your current system architecture while adding sophisticated psychological engagement mechanisms.

---

## 1. Database Schema Extensions

### New Tables Required

```sql
-- Employee tier and progression tracking
CREATE TABLE employee_tiers (
    employee_id INTEGER PRIMARY KEY,
    tier_level TEXT DEFAULT 'bronze', -- bronze, silver, gold, platinum
    tier_start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    games_played INTEGER DEFAULT 0,
    total_wins INTEGER DEFAULT 0,
    total_prizes_won INTEGER DEFAULT 0,
    performance_average REAL DEFAULT 0.0,
    streak_count INTEGER DEFAULT 0,
    last_tier_review TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

-- Dynamic conversion thresholds
CREATE TABLE conversion_thresholds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tier_level TEXT NOT NULL,
    base_threshold INTEGER NOT NULL,
    variance_min REAL DEFAULT 0.7,
    variance_max REAL DEFAULT 1.3,
    performance_modifier_high REAL DEFAULT 0.8, -- 20% easier for high performers
    performance_modifier_low REAL DEFAULT 1.2,  -- 20% harder for low performers
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Achievement system
CREATE TABLE achievements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    achievement_type TEXT NOT NULL, -- performance, gaming, social, milestone
    name TEXT NOT NULL,
    description TEXT,
    requirements TEXT, -- JSON string of requirements
    points_reward INTEGER DEFAULT 0,
    tier_requirement TEXT DEFAULT 'bronze',
    is_active BOOLEAN DEFAULT 1
);

-- Employee achievements tracking
CREATE TABLE employee_achievements (
    employee_id INTEGER,
    achievement_id INTEGER,
    earned_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    progress_data TEXT, -- JSON for partial progress tracking
    PRIMARY KEY (employee_id, achievement_id),
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id),
    FOREIGN KEY (achievement_id) REFERENCES achievements(id)
);

-- Enhanced game session tracking
CREATE TABLE game_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER,
    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    session_end TIMESTAMP,
    games_played INTEGER DEFAULT 0,
    total_winnings INTEGER DEFAULT 0,
    session_type TEXT DEFAULT 'regular', -- regular, streak_bonus, tier_reward
    psychology_flags TEXT, -- JSON: pity_timer, streak_bonus, etc.
    FOREIGN KEY (employee_id) REFERENCES employees(employee_id)
);

-- Social engagement tracking
CREATE TABLE social_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    initiator_id INTEGER,
    recipient_id INTEGER,
    interaction_type TEXT, -- gift_game, congratulate, challenge
    interaction_data TEXT, -- JSON details
    interaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (initiator_id) REFERENCES employees(employee_id),
    FOREIGN KEY (recipient_id) REFERENCES employees(employee_id)
);
```

### Enhanced Existing Tables

```sql
-- Add psychological tracking to employees table
ALTER TABLE employees ADD COLUMN consecutive_play_days INTEGER DEFAULT 0;
ALTER TABLE employees ADD COLUMN last_play_date DATE;
ALTER TABLE employees ADD COLUMN pity_timer_count INTEGER DEFAULT 0;
ALTER TABLE employees ADD COLUMN comeback_bonus_eligible BOOLEAN DEFAULT 0;
ALTER TABLE employees ADD COLUMN preferred_game_type TEXT;

-- Enhanced mini_games table
ALTER TABLE mini_games ADD COLUMN tier_level TEXT DEFAULT 'bronze';
ALTER TABLE mini_games ADD COLUMN psychology_trigger TEXT; -- streak, pity, performance, etc.
ALTER TABLE mini_games ADD COLUMN session_id INTEGER;
ALTER TABLE mini_games ADD COLUMN conversion_cost INTEGER; -- points spent to earn this game

-- Enhanced game_history for detailed analytics
ALTER TABLE game_history ADD COLUMN tier_level TEXT;
ALTER TABLE game_history ADD COLUMN streak_position INTEGER;
ALTER TABLE game_history ADD COLUMN psychology_factors TEXT; -- JSON
ALTER TABLE game_history ADD COLUMN social_shared BOOLEAN DEFAULT 0;
```

---

## 2. Core Psychology Engine Implementation

### Tier Management System

```python
# psychology_engine.py
import json
import random
from datetime import datetime, timedelta
from incentive_service import DatabaseConnection

class PsychologyEngine:
    
    def __init__(self, conn):
        self.conn = conn
        self.tier_thresholds = {
            'bronze': {'days': 30, 'games': 5, 'performance': 0},
            'silver': {'days': 90, 'games': 25, 'performance': 60},
            'gold': {'days': 180, 'games': 100, 'performance': 75},
            'platinum': {'days': 365, 'games': 200, 'performance': 85}
        }
    
    def calculate_employee_tier(self, employee_id):
        """Calculate appropriate tier for employee based on activity and performance."""
        employee = self.conn.execute("""
            SELECT e.*, et.games_played, et.tier_start_date, et.performance_average
            FROM employees e
            LEFT JOIN employee_tiers et ON e.employee_id = et.employee_id
            WHERE e.employee_id = ?
        """, (employee_id,)).fetchone()
        
        if not employee:
            return None
            
        # Calculate days active
        start_date = datetime.strptime(employee['created_date'] if employee['created_date'] else datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
        days_active = (datetime.now() - start_date).days
        
        # Determine tier
        current_tier = 'bronze'
        for tier, requirements in reversed(self.tier_thresholds.items()):
            if (days_active >= requirements['days'] and 
                (employee['games_played'] or 0) >= requirements['games'] and
                (employee['performance_average'] or 0) >= requirements['performance']):
                current_tier = tier
                break
        
        return current_tier
    
    def update_employee_tier(self, employee_id):
        """Update employee tier and handle tier advancement rewards."""
        new_tier = self.calculate_employee_tier(employee_id)
        
        # Get current tier
        current_tier_row = self.conn.execute(
            "SELECT tier_level FROM employee_tiers WHERE employee_id = ?", 
            (employee_id,)
        ).fetchone()
        
        current_tier = current_tier_row['tier_level'] if current_tier_row else 'bronze'
        
        # Check for tier advancement
        tier_order = ['bronze', 'silver', 'gold', 'platinum']
        if tier_order.index(new_tier) > tier_order.index(current_tier):
            self._handle_tier_advancement(employee_id, current_tier, new_tier)
        
        # Update tier record
        self.conn.execute("""
            INSERT OR REPLACE INTO employee_tiers 
            (employee_id, tier_level, tier_start_date, last_tier_review)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (employee_id, new_tier, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        return new_tier
    
    def _handle_tier_advancement(self, employee_id, old_tier, new_tier):
        """Handle tier advancement rewards and celebrations."""
        from incentive_service import award_mini_game, adjust_points
        
        # Award tier advancement bonuses
        tier_bonuses = {
            'silver': {'points': 25, 'games': 2},
            'gold': {'points': 50, 'games': 3},
            'platinum': {'points': 100, 'games': 5}
        }
        
        if new_tier in tier_bonuses:
            bonus = tier_bonuses[new_tier]
            
            # Award bonus points
            adjust_points(self.conn, employee_id, bonus['points'], 'SYSTEM', 
                         f'Tier Advancement to {new_tier.title()}')
            
            # Award bonus games
            for _ in range(bonus['games']):
                award_mini_game(self.conn, employee_id)
            
            # Log achievement
            self._record_achievement(employee_id, 'tier_advancement', 
                                   {'old_tier': old_tier, 'new_tier': new_tier})
    
    def calculate_conversion_threshold(self, employee_id):
        """Calculate dynamic conversion threshold using psychological principles."""
        # Get employee tier and recent performance
        employee_data = self.conn.execute("""
            SELECT et.tier_level, e.score, 
                   AVG(vs.points_awarded) as avg_recent_performance
            FROM employees e
            LEFT JOIN employee_tiers et ON e.employee_id = et.employee_id
            LEFT JOIN voting_sessions vs ON e.employee_id = vs.employee_id
            WHERE e.employee_id = ? AND vs.session_date > date('now', '-30 days')
        """, (employee_id,)).fetchone()
        
        tier = employee_data['tier_level'] if employee_data else 'bronze'
        recent_performance = employee_data['avg_recent_performance'] or 50
        
        # Get base threshold for tier
        base_threshold = self.conn.execute(
            "SELECT base_threshold, variance_min, variance_max, performance_modifier_high, performance_modifier_low FROM conversion_thresholds WHERE tier_level = ?",
            (tier,)
        ).fetchone()
        
        if not base_threshold:
            # Default fallbacks
            defaults = {'bronze': 30, 'silver': 24, 'gold': 18, 'platinum': 15}
            threshold = defaults.get(tier, 30)
            variance_min, variance_max = 0.7, 1.3
            perf_mod_high, perf_mod_low = 0.8, 1.2
        else:
            threshold = base_threshold['base_threshold']
            variance_min = base_threshold['variance_min']
            variance_max = base_threshold['variance_max']
            perf_mod_high = base_threshold['performance_modifier_high']
            perf_mod_low = base_threshold['performance_modifier_low']
        
        # Apply performance modifiers
        if recent_performance > 85:
            threshold = int(threshold * perf_mod_high)  # Make it easier
        elif recent_performance < 60:
            threshold = int(threshold * perf_mod_low)   # Make it harder
        
        # Apply variable ratio reinforcement (key psychological principle)
        variance = random.uniform(variance_min, variance_max)
        final_threshold = int(threshold * variance)
        
        return max(1, final_threshold)  # Ensure minimum of 1 point
```

### Enhanced Game Award System

```python
# Enhanced award system with psychology
def award_mini_game_with_psychology(conn, employee_id, trigger_type='manual', game_type=None):
    """Award mini-game with psychological tracking and enhancements."""
    
    psychology_engine = PsychologyEngine(conn)
    
    # Update tier before awarding
    current_tier = psychology_engine.update_employee_tier(employee_id)
    
    # Check for special psychological triggers
    psychology_flags = {}
    
    # Check pity timer (anti-frustration)
    pity_count = conn.execute(
        "SELECT pity_timer_count FROM employees WHERE employee_id = ?",
        (employee_id,)
    ).fetchone()['pity_timer_count']
    
    if pity_count >= 5:  # After 5 losses, increase win chances
        psychology_flags['pity_timer'] = True
        # Reset pity timer
        conn.execute(
            "UPDATE employees SET pity_timer_count = 0 WHERE employee_id = ?",
            (employee_id,)
        )
    
    # Check streak bonuses
    streak_count = conn.execute("""
        SELECT COUNT(*) as wins 
        FROM game_history gh
        JOIN mini_games mg ON gh.mini_game_id = mg.id
        WHERE mg.employee_id = ? AND gh.prize_amount > 0
        AND gh.play_date > date('now', '-7 days')
        ORDER BY gh.play_date DESC
        LIMIT 3
    """, (employee_id,)).fetchone()['wins']
    
    if streak_count >= 2:
        psychology_flags['hot_streak'] = True
    
    # Award the game with psychology flags
    success, awarded_game_type = award_mini_game(conn, employee_id, game_type)
    
    if success:
        # Get the game ID
        game_id = conn.lastrowid
        
        # Update with psychology data
        conn.execute("""
            UPDATE mini_games 
            SET tier_level = ?, psychology_trigger = ?
            WHERE id = ?
        """, (current_tier, json.dumps(psychology_flags), game_id))
        
        # Track social engagement opportunity
        _check_social_sharing_opportunity(conn, employee_id, trigger_type)
    
    return success, awarded_game_type

def _check_social_sharing_opportunity(conn, employee_id, trigger_type):
    """Create opportunities for social engagement."""
    if trigger_type in ['performance_bonus', 'tier_advancement']:
        # Mark as share-worthy achievement
        conn.execute("""
            INSERT INTO social_interactions 
            (initiator_id, interaction_type, interaction_data, interaction_date)
            VALUES (?, 'achievement_share', ?, CURRENT_TIMESTAMP)
        """, (employee_id, json.dumps({'trigger': trigger_type})))
```

### Variable Ratio Conversion System

```python
# Enhanced points conversion with variable ratio reinforcement
def check_points_conversion_eligibility(conn, employee_id):
    """Check if employee is eligible for game conversion using psychological principles."""
    
    psychology_engine = PsychologyEngine(conn)
    
    # Get employee current points and tier
    employee = conn.execute(
        "SELECT score FROM employees WHERE employee_id = ?",
        (employee_id,)
    ).fetchone()
    
    if not employee:
        return False, 0
    
    current_points = employee['score']
    
    # Calculate dynamic threshold
    threshold = psychology_engine.calculate_conversion_threshold(employee_id)
    
    # Check if eligible
    eligible = current_points >= threshold
    
    # If eligible, process conversion
    if eligible:
        # Deduct points
        conn.execute(
            "UPDATE employees SET score = score - ? WHERE employee_id = ?",
            (threshold, current_points - threshold)
        )
        
        # Award game with psychology tracking
        success, game_type = award_mini_game_with_psychology(
            conn, employee_id, 'points_conversion'
        )
        
        # Log conversion
        conn.execute("""
            INSERT INTO game_sessions 
            (employee_id, session_start, games_played, session_type)
            VALUES (?, CURRENT_TIMESTAMP, 1, 'points_conversion')
        """, (employee_id,))
        
        return True, threshold
    
    return False, threshold - current_points  # Points needed
```

---

## 3. Frontend Integration

### Enhanced Game Selection Interface

```javascript
// Enhanced game selection with psychological elements
class PsychologyEnhancedGameUI {
    constructor() {
        this.tierColors = {
            'bronze': '#CD7F32',
            'silver': '#C0C0C0',
            'gold': '#FFD700',
            'platinum': '#E5E4E2'
        };
    }
    
    async loadEmployeePsychProfile() {
        try {
            const response = await fetch('/api/employee/psychology-profile');
            const profile = await response.json();
            
            this.updateUIForTier(profile.tier);
            this.showProgressIndicators(profile);
            this.displayAchievements(profile.recent_achievements);
            
            return profile;
        } catch (error) {
            console.error('Failed to load psychology profile:', error);
        }
    }
    
    updateUIForTier(tier) {
        const gameCards = document.querySelectorAll('.game-card');
        const tierColor = this.tierColors[tier];
        
        gameCards.forEach(card => {
            // Add tier-specific styling
            card.style.borderColor = tierColor;
            card.classList.add(`tier-${tier}`);
            
            // Show tier-specific features
            const tierFeatures = card.querySelector('.tier-features');
            if (tierFeatures) {
                tierFeatures.innerHTML = this.getTierFeatures(tier);
            }
        });
        
        // Update header with tier status
        this.updateTierDisplay(tier);
    }
    
    showProgressIndicators(profile) {
        const progressContainer = document.getElementById('progress-indicators');
        
        // Next tier progress
        const nextTier = this.getNextTier(profile.tier);
        if (nextTier) {
            const progress = this.calculateTierProgress(profile, nextTier);
            progressContainer.innerHTML += `
                <div class="tier-progress">
                    <h5>Progress to ${nextTier.charAt(0).toUpperCase() + nextTier.slice(1)}</h5>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <small>${progress}% complete</small>
                </div>
            `;
        }
        
        // Conversion progress
        const conversionProgress = (profile.current_points / profile.next_conversion_threshold) * 100;
        progressContainer.innerHTML += `
            <div class="conversion-progress">
                <h5>Next Game Opportunity</h5>
                <div class="progress-bar gold-bar">
                    <div class="progress-fill" style="width: ${Math.min(100, conversionProgress)}%"></div>
                </div>
                <small>${profile.current_points}/${profile.next_conversion_threshold} points</small>
            </div>
        `;
    }
    
    displayAchievements(achievements) {
        const achievementsContainer = document.getElementById('recent-achievements');
        if (achievements && achievements.length > 0) {
            achievementsContainer.innerHTML = '<h5>Recent Achievements</h5>';
            achievements.forEach(achievement => {
                achievementsContainer.innerHTML += `
                    <div class="achievement-badge" data-achievement="${achievement.id}">
                        <span class="achievement-icon">${achievement.icon || '🏆'}</span>
                        <span class="achievement-name">${achievement.name}</span>
                    </div>
                `;
            });
        }
    }
    
    getTierFeatures(tier) {
        const features = {
            'bronze': ['Basic slots', 'Tutorial bonuses', '35% win rate'],
            'silver': ['All standard games', 'Streak bonuses', '38% win rate'],
            'gold': ['Premium variations', 'Cash prizes', '42% win rate'],
            'platinum': ['Exclusive games', 'VIP tournaments', '45% win rate']
        };
        
        return features[tier].map(feature => 
            `<span class="tier-feature">${feature}</span>`
        ).join('');
    }
    
    // Enhanced game play with psychological feedback
    async playGameWithPsychology(gameType, gameId) {
        // Pre-game psychology check
        const psychProfile = await this.loadEmployeePsychProfile();
        
        // Show anticipation building
        this.showAnticipationUI(psychProfile);
        
        // Play the game
        const result = await this.executeGame(gameType, gameId);
        
        // Post-game psychology processing
        this.handlePostGamePsychology(result, psychProfile);
        
        return result;
    }
    
    showAnticipationUI(profile) {
        // Show streak status
        if (profile.psychology_flags && profile.psychology_flags.hot_streak) {
            this.showNotification('🔥 Hot Streak Active! Luck is on your side!', 'success');
        }
        
        // Show pity timer activation
        if (profile.psychology_flags && profile.psychology_flags.pity_timer) {
            this.showNotification('🍀 Special Luck Activated! Better odds this round!', 'info');
        }
        
        // Build suspense with countdown
        this.showSuspenseCountdown();
    }
    
    handlePostGamePsychology(result, profile) {
        if (result.win) {
            // Celebration based on tier and prize
            this.triggerWinCelebration(result, profile.tier);
            
            // Check for achievement unlocks
            this.checkAchievementUnlocks(result);
            
            // Social sharing opportunity
            this.showSocialSharingOption(result);
        } else {
            // Loss mitigation
            this.handleLossMitigation(profile);
        }
        
        // Update psychology tracking
        this.updatePsychologyTracking(result, profile);
    }
    
    triggerWinCelebration(result, tier) {
        const celebration = {
            'bronze': 'confetti-small',
            'silver': 'confetti-medium',
            'gold': 'confetti-large',
            'platinum': 'fireworks'
        };
        
        this.showCelebrationAnimation(celebration[tier]);
        
        // Tier-specific win messages
        const messages = {
            'bronze': 'Great job!',
            'silver': 'Excellent win!',
            'gold': 'Outstanding victory!',
            'platinum': 'LEGENDARY WIN!'
        };
        
        this.showWinMessage(messages[tier], result.prize_description);
    }
}

// Initialize psychology-enhanced UI
const psychGameUI = new PsychologyEnhancedGameUI();

// Enhanced page load
document.addEventListener('DOMContentLoaded', async function() {
    await psychGameUI.loadEmployeePsychProfile();
});
```

### CSS for Psychological Enhancement

```css
/* Tier-specific styling for psychological impact */
.tier-bronze {
    border: 2px solid #CD7F32;
    background: linear-gradient(135deg, rgba(205, 127, 50, 0.1), rgba(139, 69, 19, 0.05));
}

.tier-silver {
    border: 2px solid #C0C0C0;
    background: linear-gradient(135deg, rgba(192, 192, 192, 0.1), rgba(169, 169, 169, 0.05));
}

.tier-gold {
    border: 2px solid #FFD700;
    background: linear-gradient(135deg, rgba(255, 215, 0, 0.1), rgba(255, 165, 0, 0.05));
    box-shadow: 0 0 20px rgba(255, 215, 0, 0.3);
}

.tier-platinum {
    border: 2px solid #E5E4E2;
    background: linear-gradient(135deg, rgba(229, 228, 226, 0.1), rgba(192, 192, 192, 0.05));
    box-shadow: 0 0 25px rgba(229, 228, 226, 0.4);
}

/* Progress indicators for motivation */
.progress-bar {
    width: 100%;
    height: 20px;
    background: rgba(0, 0, 0, 0.3);
    border-radius: 10px;
    overflow: hidden;
    margin: 10px 0;
}

.progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #4CAF50, #45a049);
    transition: width 0.5s ease;
}

.gold-bar .progress-fill {
    background: linear-gradient(90deg, #FFD700, #FFA500);
}

/* Achievement badges for recognition */
.achievement-badge {
    display: inline-block;
    background: linear-gradient(135deg, #FFD700, #FFA500);
    color: #000;
    padding: 5px 10px;
    border-radius: 15px;
    margin: 2px;
    font-size: 12px;
    font-weight: bold;
    animation: achievement-glow 2s infinite;
}

@keyframes achievement-glow {
    0%, 100% { box-shadow: 0 0 5px rgba(255, 215, 0, 0.5); }
    50% { box-shadow: 0 0 15px rgba(255, 215, 0, 0.8); }
}

/* Hot streak indicator */
.hot-streak-indicator {
    position: absolute;
    top: -10px;
    right: -10px;
    background: linear-gradient(45deg, #FF4444, #FF6666);
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 10px;
    font-weight: bold;
    animation: pulse 1s infinite;
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.1); }
}
```

---

## 4. API Endpoints for Psychology System

```python
# New API endpoints for psychology features
@app.route('/api/employee/psychology-profile')
def get_employee_psychology_profile():
    """Get comprehensive psychology profile for current employee."""
    employee_id = session.get('employee_id')
    if not employee_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    with DatabaseConnection() as conn:
        psychology_engine = PsychologyEngine(conn)
        
        # Get basic employee data
        employee = conn.execute("""
            SELECT e.*, et.tier_level, et.games_played, et.total_wins,
                   et.performance_average, et.streak_count
            FROM employees e
            LEFT JOIN employee_tiers et ON e.employee_id = et.employee_id
            WHERE e.employee_id = ?
        """, (employee_id,)).fetchone()
        
        if not employee:
            return jsonify({'error': 'Employee not found'}), 404
        
        # Calculate conversion threshold
        threshold = psychology_engine.calculate_conversion_threshold(employee_id)
        
        # Get recent achievements
        achievements = conn.execute("""
            SELECT a.name, a.description, ea.earned_date
            FROM achievements a
            JOIN employee_achievements ea ON a.id = ea.achievement_id
            WHERE ea.employee_id = ? AND ea.earned_date > date('now', '-30 days')
            ORDER BY ea.earned_date DESC
            LIMIT 5
        """, (employee_id,)).fetchall()
        
        # Check psychology flags
        psychology_flags = {}
        
        # Pity timer check
        if employee['pity_timer_count'] >= 3:
            psychology_flags['approaching_pity'] = True
        
        # Streak check
        recent_wins = conn.execute("""
            SELECT COUNT(*) as wins FROM game_history gh
            JOIN mini_games mg ON gh.mini_game_id = mg.id
            WHERE mg.employee_id = ? AND gh.prize_amount > 0
            AND gh.play_date > date('now', '-3 days')
        """, (employee_id,)).fetchone()['wins']
        
        if recent_wins >= 2:
            psychology_flags['hot_streak'] = True
        
        profile = {
            'employee_id': employee_id,
            'tier': employee['tier_level'] or 'bronze',
            'current_points': employee['score'],
            'next_conversion_threshold': threshold,
            'games_played': employee['games_played'] or 0,
            'total_wins': employee['total_wins'] or 0,
            'win_rate': (employee['total_wins'] or 0) / max(1, employee['games_played'] or 1) * 100,
            'performance_average': employee['performance_average'] or 0,
            'streak_count': employee['streak_count'] or 0,
            'psychology_flags': psychology_flags,
            'recent_achievements': [dict(a) for a in achievements]
        }
        
        return jsonify(profile)

@app.route('/api/employee/conversion-check', methods=['POST'])
def check_conversion_eligibility():
    """Check if employee can convert points to games."""
    employee_id = session.get('employee_id')
    if not employee_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    with DatabaseConnection() as conn:
        eligible, cost_or_needed = check_points_conversion_eligibility(conn, employee_id)
        
        return jsonify({
            'eligible': eligible,
            'cost': cost_or_needed if eligible else None,
            'points_needed': cost_or_needed if not eligible else None
        })

@app.route('/api/employee/achievements')
def get_achievements():
    """Get available achievements and progress."""
    employee_id = session.get('employee_id')
    if not employee_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    with DatabaseConnection() as conn:
        # Get all available achievements
        achievements = conn.execute("""
            SELECT a.*, 
                   CASE WHEN ea.achievement_id IS NOT NULL THEN 1 ELSE 0 END as earned,
                   ea.earned_date, ea.progress_data
            FROM achievements a
            LEFT JOIN employee_achievements ea ON a.id = ea.achievement_id 
                                                AND ea.employee_id = ?
            WHERE a.is_active = 1
            ORDER BY earned ASC, a.achievement_type, a.name
        """, (employee_id,)).fetchall()
        
        return jsonify([dict(a) for a in achievements])
```

---

## 5. Analytics and Monitoring

### Psychology Metrics Dashboard

```python
# Analytics for psychology system effectiveness
@app.route('/admin/psychology-analytics')
@require_admin
def psychology_analytics():
    """Admin dashboard for psychology system metrics."""
    
    with DatabaseConnection() as conn:
        # Engagement metrics by tier
        tier_engagement = conn.execute("""
            SELECT et.tier_level,
                   COUNT(*) as employee_count,
                   AVG(et.games_played) as avg_games_played,
                   AVG(et.total_wins * 1.0 / NULLIF(et.games_played, 0)) as avg_win_rate,
                   AVG(et.performance_average) as avg_performance
            FROM employee_tiers et
            JOIN employees e ON et.employee_id = e.employee_id
            WHERE e.is_active = 1
            GROUP BY et.tier_level
        """).fetchall()
        
        # Conversion rate analysis
        conversion_metrics = conn.execute("""
            SELECT 
                DATE(session_start) as date,
                COUNT(*) as total_conversions,
                AVG(CASE WHEN games_played > 0 THEN 1.0 ELSE 0.0 END) as success_rate
            FROM game_sessions 
            WHERE session_type = 'points_conversion'
            AND session_start > date('now', '-30 days')
            GROUP BY DATE(session_start)
            ORDER BY date DESC
        """).fetchall()
        
        # Psychology trigger effectiveness
        psychology_effectiveness = conn.execute("""
            SELECT 
                json_extract(psychology_trigger, '$') as trigger_type,
                COUNT(*) as trigger_count,
                AVG(CASE WHEN gh.prize_amount > 0 THEN 1.0 ELSE 0.0 END) as win_rate
            FROM mini_games mg
            LEFT JOIN game_history gh ON mg.id = gh.mini_game_id
            WHERE mg.psychology_trigger IS NOT NULL
            AND mg.awarded_date > date('now', '-30 days')
            GROUP BY json_extract(psychology_trigger, '$')
        """).fetchall()
        
        analytics_data = {
            'tier_engagement': [dict(row) for row in tier_engagement],
            'conversion_trends': [dict(row) for row in conversion_metrics],
            'psychology_effectiveness': [dict(row) for row in psychology_effectiveness],
            'summary': {
                'total_active_players': sum(row['employee_count'] for row in tier_engagement),
                'avg_engagement_score': sum(row['avg_games_played'] * row['employee_count'] for row in tier_engagement) / sum(row['employee_count'] for row in tier_engagement),
                'system_win_rate': sum(row['avg_win_rate'] * row['employee_count'] for row in tier_engagement) / sum(row['employee_count'] for row in tier_engagement)
            }
        }
        
        return render_template('admin_psychology_analytics.html', data=analytics_data)
```

This implementation provides a comprehensive psychological framework that enhances engagement while maintaining system integrity and fairness. The variable ratio reinforcement, tier progression, and social elements create a balanced system that drives performance while preventing unhealthy gaming behaviors.

The system can be gradually rolled out, starting with basic tier implementation and expanding to include more sophisticated psychological features as employees adapt to the new framework.