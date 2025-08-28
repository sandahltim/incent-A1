# 🛠️ Developer Guide - Vegas Casino System

## Overview

This guide covers the technical implementation of the professional Vegas casino gaming system, including architecture, APIs, audio engine, game mechanics, and deployment procedures.

---

## 🏗️ System Architecture

### Core Components

```
├── Flask Application (app.py)
├── Game Engine (static/casino-js/)
│   ├── fortune-wheel.js      # Physics-based wheel game
│   ├── enhanced-dice.js      # 3D dice with realistic physics
│   ├── vegas-casino.js       # Core casino functionality
│   └── minigames-controller.js # Game state management
├── Audio System (static/audio/)
│   ├── audio-engine.js       # Professional Web Audio API
│   ├── audio-controls.js     # UI controls and mixing
│   └── audio/ (69 MP3 files) # Complete sound library
├── Templates (templates/)
│   ├── minigames.html        # Standalone casino portal
│   ├── employee_portal.html  # Integrated employee interface
│   └── base.html             # Audio-enabled base template
└── Database Schema
    ├── mini_games            # Game session tracking
    ├── mini_game_payouts     # Prize distribution
    ├── prize_values          # Reward configuration
    └── game_odds             # Probability management
```

### Technology Stack

- **Backend**: Python 3.11+ Flask with SQLite
- **Frontend**: HTML5, CSS3, JavaScript ES6+, Bootstrap 5
- **Audio**: Web Audio API with spatial positioning
- **Graphics**: CSS3 animations, Canvas API for wheels
- **Mobile**: Responsive design with touch optimization
- **Testing**: Pytest with comprehensive coverage

---

## 🎮 Game Engine Architecture

### Core Game Classes

#### FortuneWheel Class
```javascript
class FortuneWheel {
    constructor(containerId) {
        this.segments = [
            { value: 5, label: '$5', color: '#FF6B6B', weight: 30 },
            { value: 'JACKPOT', label: 'JACKPOT', color: '#FF00FF', weight: 1 }
            // ... 8 total segments
        ];
        this.wheelRadius = 200;
        this.currentRotation = 0;
        this.isSpinning = false;
    }
    
    // Physics simulation
    async spin() {
        const winningSegment = this.selectWinningSegment();
        const targetAngle = this.calculateTargetAngle(winningSegment);
        const spins = 5 + Math.random() * 3; // 5-8 full rotations
        await this.animateSpin();
    }
}
```

#### Enhanced3DDice Class
```javascript
class Enhanced3DDice {
    constructor(containerId) {
        this.diceValues = [1, 1];
        this.rollHistory = [];
        this.isRolling = false;
    }
    
    // 3D CSS transforms for realistic dice
    setDicePosition(diceId, value) {
        const rotations = {
            1: 'rotateX(0deg) rotateY(0deg)',
            2: 'rotateX(0deg) rotateY(-90deg)',
            // ... all 6 faces
        };
        dice.style.transform = rotations[value];
    }
}
```

### Game State Management

#### MinigamesController Class
```javascript
class MinigamesController {
    constructor() {
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
    }
    
    // Event handling for cross-game features
    handleGameWin(winData) {
        this.updateStats(winData);
        this.checkChallenges();
        this.checkJackpotTrigger();
    }
}
```

---

## 🎵 Professional Audio System

### Audio Engine Architecture

#### CasinoAudioEngine Class
```javascript
class CasinoAudioEngine {
    constructor() {
        this.audioContext = null;
        this.bufferCache = new Map();
        this.loadingPromises = new Map();
        this.channels = {
            master: { gain: null, volume: 1.0 },
            effects: { gain: null, volume: 0.8 },
            ui: { gain: null, volume: 0.6 },
            ambient: { gain: null, volume: 0.4 },
            voice: { gain: null, volume: 0.9 }
        };
        this.spatialNodes = new Map();
    }
    
    // Advanced audio loading with fallbacks
    async loadSound(url, useCache = true) {
        const fallbackUrl = this.getFallbackUrl(url);
        const actualUrl = await this.getValidAudioUrl(url, fallbackUrl);
        
        if (actualUrl !== url && fallbackUrl) {
            console.debug(`Using fallback audio: ${actualUrl}`);
            return this.loadSound(actualUrl, useCache);
        }
        
        return this.fetchAndDecodeAudio(actualUrl || url);
    }
}
```

### Audio File Organization

```
static/audio/
├── ui/                    # Interface sounds (6 files)
│   ├── ui-hover.mp3
│   ├── button-click.mp3
│   └── modal-*.mp3
├── games/                 # Game mechanics (23 files)
│   ├── dice-*.mp3        # Dice rolling sounds (6 files)
│   ├── slot-*.mp3        # Slot machine sounds (7 files)
│   ├── wheel-*.mp3       # Fortune wheel sounds (5 files)
│   └── scratch-*.mp3     # Scratch card sounds (4 files)
├── wins/                  # Win celebrations (7 files)
│   ├── win-tiny.mp3
│   ├── win-mega.mp3
│   └── win-jackpot.mp3
├── coins/                 # Money sounds (5 files)
└── ambient/               # Background audio (4 files)
```

### Audio Manifest System

```json
{
  "audio_manifest": {
    "version": "3.0.0",
    "total_sounds": 69,
    "categories": {
      "ui": {
        "sounds": [
          {
            "file": "ui-hover.mp3",
            "fallback": "button-click.mp3",
            "description": "Subtle hover sound for buttons",
            "volume": 0.3,
            "channel": "ui"
          }
        ]
      }
    },
    "existing_files": [
      "button-click.mp3",
      "casino-win.mp3", 
      "jackpot.mp3",
      "reel-spin.mp3"
    ]
  }
}
```

---

## 🎯 Game Mechanics & Probability

### Prize System Configuration

#### Database Schema
```sql
CREATE TABLE prize_values (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prize_type TEXT NOT NULL,
    prize_description TEXT NOT NULL,
    base_dollar_value REAL NOT NULL,
    point_to_dollar_rate REAL NOT NULL,
    is_system_managed INTEGER DEFAULT 1,
    updated_by TEXT,
    updated_at DATETIME
);
```

#### Default Prize Configuration
```python
default_prizes = [
    ('dice_small_win', 'Dice Small Win', 5.0, 10.0),
    ('dice_jackpot', 'Dice Jackpot', 200.0, 0.5),
    ('slot_small_win', 'Slot Small Win', 10.0, 8.0),
    ('wheel_jackpot', 'Fortune Wheel Jackpot', 500.0, 0.1),
    # ... 12 total prize tiers
]
```

### Probability Management

#### Fortune Wheel Odds
```javascript
segments: [
    { value: 5, weight: 30 },      // 30% chance
    { value: 10, weight: 25 },     // 25% chance  
    { value: 25, weight: 15 },     // 15% chance
    { value: 50, weight: 10 },     // 10% chance
    { value: 100, weight: 5 },     // 5% chance
    { value: 'JACKPOT', weight: 1 } // 1% chance
]
```

#### Dice Game Logic
```python
def play_dice_game(conn, config):
    dice_values = [random.randint(1, 6), random.randint(1, 6)]
    total = sum(dice_values)
    
    # Win conditions with probabilities
    if total == 2:  # Snake Eyes (2.78% chance)
        return create_win_outcome(100, 'snake_eyes')
    elif total == 12:  # Boxcars (2.78% chance)  
        return create_win_outcome(75, 'boxcars')
    elif total == 7:  # Lucky Seven (16.67% chance)
        return create_win_outcome(25, 'lucky_seven')
    elif dice_values[0] == dice_values[1]:  # Doubles (16.67% chance)
        return create_win_outcome(15, 'doubles')
    else:
        return create_loss_outcome()
```

### Progressive Jackpot System

#### Server-Side Implementation
```python
class ProgressiveJackpot:
    def __init__(self):
        self.current_amount = 500.00
        self.contribution_rate = 0.01  # 1% of all plays
        self.trigger_chance = 0.001    # 0.1% per game
        
    def add_contribution(self, game_cost):
        self.current_amount += game_cost * self.contribution_rate
        
    def check_trigger(self):
        return random.random() < self.trigger_chance
        
    def payout(self):
        amount = self.current_amount
        self.current_amount = 500.00  # Reset to minimum
        return amount
```

---

## 🔌 API Endpoints

### Game Management API

#### Start Game Session
```
POST /play_game/<int:game_id>
Content-Type: application/json

{
  "employee_id": "E001",
  "game_type": "dice",
  "bet_amount": 0
}

Response:
{
  "success": true,
  "outcome": {
    "win": true,
    "prize_type": "points",
    "prize_amount": 25,
    "game_details": {
      "dice_values": [3, 4],
      "win_type": "lucky_seven"
    }
  }
}
```

#### Minigames Analytics
```
GET /api/analytics/minigames?days=30

Response:
{
  "summary": {
    "total_games_played": 1247,
    "total_prizes_awarded": 89234.50,
    "unique_players": 45,
    "win_rate": 32.4
  },
  "game_breakdown": {
    "dice": { "plays": 523, "wins": 147, "total_payout": 2150.00 },
    "wheel": { "plays": 412, "wins": 156, "total_payout": 1875.50 }
  },
  "trends": [...]
}
```

#### Employee Game History
```
GET /api/analytics/employee/<employee_id>

Response:
{
  "personal_stats": {
    "rank": 3,
    "total_games": 45,
    "total_winnings": 245.00,
    "win_rate": 28.9,
    "favorite_game": "dice"
  },
  "recent_games": [
    {
      "game_type": "dice",
      "outcome": "win",
      "prize_amount": 25.00,
      "timestamp": "2025-08-28T10:30:15Z"
    }
  ]
}
```

### Admin Management API

#### Award Game to Employee
```
POST /admin/award_game
Content-Type: application/json

{
  "employee_id": "E001", 
  "game_type": "dice",
  "reason": "Excellent customer service"
}

Response:
{
  "success": true,
  "game_id": 1234,
  "message": "Game awarded to John Doe"
}
```

#### Update Game Odds
```
POST /admin/update_game_odds
Content-Type: application/json

{
  "game_type": "dice",
  "odds": {
    "snake_eyes": 2.78,
    "lucky_seven": 16.67,
    "doubles": 16.67
  }
}
```

#### Bulk Prize Configuration
```
POST /admin/update_game_prize
Content-Type: application/json

{
  "prizes": [
    {
      "prize_type": "dice_jackpot",
      "base_dollar_value": 200.00,
      "point_to_dollar_rate": 0.5
    }
  ]
}
```

---

## 🎨 Frontend Implementation

### CSS Animation System

#### 3D Dice Rolling
```css
.dice {
    width: 60px;
    height: 60px;
    position: relative;
    transform-style: preserve-3d;
    transition: transform 0.1s;
}

.face {
    position: absolute;
    width: 60px;
    height: 60px;
    background: linear-gradient(135deg, #fff, #f0f0f0);
    border: 3px solid #333;
}

.face-1 { transform: rotateY(0deg) translateZ(30px); }
.face-6 { transform: rotateX(-90deg) translateZ(30px); }

@keyframes diceRoll {
    0% { transform: rotateX(0deg) rotateY(0deg) rotateZ(0deg); }
    100% { transform: rotateX(720deg) rotateY(720deg) rotateZ(360deg); }
}
```

#### Fortune Wheel Canvas
```javascript
drawWheel() {
    const angleStep = (2 * Math.PI) / this.segments.length;
    
    this.segments.forEach((segment, index) => {
        const startAngle = (index * angleStep) + this.currentRotation;
        const endAngle = ((index + 1) * angleStep) + this.currentRotation;
        
        // Draw segment
        this.ctx.beginPath();
        this.ctx.arc(this.centerX, this.centerY, this.wheelRadius, startAngle, endAngle);
        this.ctx.fillStyle = segment.color;
        this.ctx.fill();
        
        // Draw text
        this.ctx.save();
        this.ctx.rotate(startAngle + angleStep / 2);
        this.ctx.fillText(segment.label, this.wheelRadius * 0.7, 5);
        this.ctx.restore();
    });
}
```

### Responsive Design Implementation

#### Mobile-First CSS Grid
```css
.casino-games-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    padding: 2rem;
}

@media (max-width: 768px) {
    .casino-games-grid {
        grid-template-columns: 1fr;
        padding: 1rem;
    }
    
    .btn-vegas {
        padding: 1rem 2rem;
        font-size: 1.1rem;
        min-height: 60px; /* Touch-friendly */
    }
}
```

#### Touch Optimization
```javascript
// Touch event handling for mobile
document.addEventListener('touchstart', function(e) {
    // Prevent zoom on double-tap
    e.preventDefault();
    
    // Handle touch input for games
    if (e.target.classList.contains('dice')) {
        if (!this.isRolling) this.rollDice();
    }
}, { passive: false });
```

---

## 🧪 Testing Framework

### Unit Testing

#### Game Logic Tests
```python
def test_dice_game_snake_eyes():
    """Test Snake Eyes win condition"""
    # Mock dice roll to return [1, 1]
    with patch('random.randint', return_value=1):
        outcome = play_dice_game(mock_conn, {})
        
        assert outcome['win'] == True
        assert outcome['prize_amount'] == 100
        assert outcome['win_type'] == 'snake_eyes'

def test_wheel_probability_distribution():
    """Test Fortune Wheel segment probabilities"""
    results = {}
    for _ in range(10000):
        segment = wheel.selectWinningSegment()
        results[segment] = results.get(segment, 0) + 1
    
    # Check that probabilities are within expected ranges
    assert 2800 <= results['5'] <= 3200  # 30% ± 2%
    assert 80 <= results['JACKPOT'] <= 120  # 1% ± 0.2%
```

#### Audio System Tests
```python
def test_audio_fallback_system():
    """Test that missing audio files use fallbacks"""
    audio_engine = CasinoAudioEngine()
    
    # Test with non-existent file
    result = audio_engine.getValidAudioUrl('missing-sound.mp3', 'button-click.mp3')
    assert result == 'button-click.mp3'
    
    # Test with existing file
    result = audio_engine.getValidAudioUrl('button-click.mp3', None)
    assert result == 'button-click.mp3'
```

### Integration Testing

#### Full Game Flow Tests
```python
def test_complete_game_flow(client, auth):
    """Test complete game from award to payout"""
    # Admin awards game
    response = client.post('/admin/award_game', json={
        'employee_id': 'E001',
        'game_type': 'dice',
        'reason': 'Test award'
    })
    assert response.json['success'] == True
    game_id = response.json['game_id']
    
    # Employee plays game
    response = client.post(f'/play_game/{game_id}')
    outcome = response.json['outcome']
    
    # Verify game is marked as played
    response = client.get('/employee_portal')
    assert game_id not in [g['id'] for g in response.context['unused_games']]
```

### Performance Testing

#### Load Testing
```python
def test_concurrent_game_sessions():
    """Test system under concurrent load"""
    import concurrent.futures
    
    def play_game_session():
        return requests.post('http://localhost:7409/play_game/1')
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(play_game_session) for _ in range(100)]
        results = [f.result() for f in futures]
    
    success_rate = sum(1 for r in results if r.status_code == 200) / len(results)
    assert success_rate >= 0.95  # 95% success rate under load
```

---

## 🚀 Deployment Guide

### Production Setup

#### Environment Configuration
```bash
# .env file
FLASK_ENV=production
DATABASE_URL=sqlite:///incentive.db
AUDIO_CACHE_SIZE=100MB
MAX_CONCURRENT_GAMES=500
PROGRESSIVE_JACKPOT_SEED=500.00
JACKPOT_CONTRIBUTION_RATE=0.01
```

#### Systemd Service Configuration
```ini
[Unit]
Description=RFID Incentive Program - Vegas Casino
After=network.target

[Service]
Type=exec
User=tim
WorkingDirectory=/home/tim/incentDev
ExecStart=/home/tim/incentDev/venv/bin/gunicorn --workers 4 --timeout 180 --bind 0.0.0.0:7409 app:app
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

#### Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    # Audio file optimization
    location ~* \.(mp3|ogg|wav)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
        gzip_static on;
    }
    
    # Game assets
    location /static/ {
        expires 30d;
        add_header Cache-Control "public";
    }
    
    # Proxy to Flask app
    location / {
        proxy_pass http://127.0.0.1:7409;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Database Migrations

#### Schema Updates
```python
def migrate_to_casino_v3():
    """Migrate database to support Vegas casino features"""
    migrations = [
        """
        CREATE TABLE IF NOT EXISTS prize_values (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prize_type TEXT NOT NULL,
            prize_description TEXT NOT NULL,
            base_dollar_value REAL NOT NULL,
            point_to_dollar_rate REAL NOT NULL,
            is_system_managed INTEGER DEFAULT 1,
            updated_by TEXT,
            updated_at DATETIME
        );
        """,
        """
        ALTER TABLE mini_games ADD COLUMN audio_enabled INTEGER DEFAULT 1;
        """,
        """
        CREATE INDEX idx_mini_games_employee_date ON mini_games(employee_id, played_date);
        """
    ]
    
    for migration in migrations:
        conn.execute(migration)
```

### Performance Optimization

#### Audio Preloading Strategy
```javascript
class AudioPreloader {
    constructor() {
        this.priorityFiles = [
            'button-click.mp3',
            'casino-win.mp3', 
            'dice-roll-1.mp3',
            'wheel-spin.mp3'
        ];
    }
    
    async preloadPriorityAudio() {
        const promises = this.priorityFiles.map(file => 
            window.casinoAudio.loadSound(`/static/audio/${file}`)
        );
        
        await Promise.all(promises);
        console.log('Priority audio preloaded');
    }
}
```

#### Database Connection Pooling
```python
class DatabaseConnectionPool:
    def __init__(self, db_path, pool_size=10):
        self.db_path = db_path
        self.pool_size = pool_size
        self.connections = queue.Queue(maxsize=pool_size)
        self._initialize_pool()
    
    def _initialize_pool(self):
        for _ in range(self.pool_size):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connections.put(conn)
```

---

## 🔧 Maintenance & Monitoring

### Health Checks

#### System Status Endpoint
```python
@app.route('/health')
def health_check():
    checks = {
        'database': check_database_connection(),
        'audio_files': check_audio_files_exist(),
        'game_engine': check_game_functionality(),
        'progressive_jackpot': check_jackpot_system()
    }
    
    status = 'healthy' if all(checks.values()) else 'degraded'
    return jsonify({'status': status, 'checks': checks})
```

#### Audio System Monitoring
```javascript
class AudioMonitor {
    constructor() {
        this.metrics = {
            filesLoaded: 0,
            loadErrors: 0,
            playbackErrors: 0,
            cacheHits: 0,
            cacheMisses: 0
        };
    }
    
    logMetrics() {
        console.log('Audio System Metrics:', this.metrics);
        
        // Send to monitoring service
        fetch('/api/audio-metrics', {
            method: 'POST',
            body: JSON.stringify(this.metrics)
        });
    }
}
```

### Backup Procedures

#### Database Backup Script
```bash
#!/bin/bash
# backup_casino_db.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/tim/incentDev/backups"
DB_PATH="/home/tim/incentDev/incentive.db"

# Create compressed backup
sqlite3 $DB_PATH ".backup $BACKUP_DIR/incentive_${DATE}.db"
gzip "$BACKUP_DIR/incentive_${DATE}.db"

# Clean up old backups (keep 30 days)
find $BACKUP_DIR -name "incentive_*.db.gz" -mtime +30 -delete

echo "Backup completed: incentive_${DATE}.db.gz"
```

#### Audio Asset Backup
```bash
#!/bin/bash
# backup_audio_assets.sh

AUDIO_DIR="/home/tim/incentDev/static/audio"
BACKUP_DIR="/home/tim/incentDev/backups/audio"
DATE=$(date +%Y%m%d)

# Create timestamped backup
tar -czf "$BACKUP_DIR/audio_assets_${DATE}.tar.gz" -C "$AUDIO_DIR" .

echo "Audio assets backed up: audio_assets_${DATE}.tar.gz"
```

---

## 📊 Analytics & Reporting

### Game Performance Metrics

#### Key Performance Indicators
```python
def get_casino_kpis(days=30):
    """Get key performance indicators for casino system"""
    with DatabaseConnection() as conn:
        metrics = {}
        
        # Player engagement
        metrics['daily_active_users'] = conn.execute("""
            SELECT COUNT(DISTINCT employee_id) 
            FROM mini_games 
            WHERE played_date >= date('now', '-{} days')
        """.format(days)).fetchone()[0]
        
        # Revenue metrics
        metrics['total_prizes_awarded'] = conn.execute("""
            SELECT COALESCE(SUM(dollar_value), 0) 
            FROM mini_game_payouts 
            WHERE payout_date >= date('now', '-{} days')
        """.format(days)).fetchone()[0]
        
        # Game popularity
        game_stats = conn.execute("""
            SELECT game_type, COUNT(*) as plays, 
                   AVG(CASE WHEN outcome LIKE '%"win":true%' THEN 1.0 ELSE 0.0 END) as win_rate
            FROM mini_games 
            WHERE played_date >= date('now', '-{} days')
            GROUP BY game_type
        """.format(days)).fetchall()
        
        metrics['game_stats'] = [dict(row) for row in game_stats]
        
    return metrics
```

#### Real-Time Dashboard
```javascript
class CasinoDashboard {
    constructor() {
        this.wsConnection = null;
        this.charts = {};
        this.refreshInterval = 30000; // 30 seconds
    }
    
    async initializeDashboard() {
        // Setup WebSocket for real-time updates
        this.wsConnection = new WebSocket('ws://localhost:7409/casino-metrics');
        
        this.wsConnection.onmessage = (event) => {
            const metrics = JSON.parse(event.data);
            this.updateCharts(metrics);
        };
        
        // Initialize charts
        this.charts.playerActivity = new Chart('playerActivityChart', {
            type: 'line',
            data: { labels: [], datasets: [] }
        });
        
        this.charts.gamePopularity = new Chart('gamePopularityChart', {
            type: 'doughnut',
            data: { labels: [], datasets: [] }
        });
    }
}
```

---

## 🔒 Security Considerations

### Input Validation

#### Server-Side Game Validation
```python
def validate_game_play(employee_id, game_id, client_data):
    """Validate game play attempt for security"""
    
    # Check if employee exists and is active
    employee = get_employee(employee_id)
    if not employee or not employee.active:
        raise SecurityError("Invalid employee")
    
    # Verify game ownership
    game = get_mini_game(game_id)
    if game.employee_id != employee_id:
        raise SecurityError("Game ownership mismatch")
    
    # Check if game already played
    if game.status == 'played':
        raise SecurityError("Game already completed")
    
    # Validate timing (prevent rapid-fire requests)
    if game.awarded_date > datetime.now() - timedelta(seconds=1):
        raise SecurityError("Game played too quickly after award")
    
    # Server-side random generation (never trust client)
    outcome = generate_game_outcome(game.game_type)
    
    return outcome
```

#### CSRF Protection
```python
from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
csrf.init_app(app)

# All game endpoints require CSRF token
@app.route('/play_game/<int:game_id>', methods=['POST'])
@csrf.exempt  # Handle manually for API endpoints
def play_game(game_id):
    token = request.headers.get('X-CSRFToken')
    if not validate_csrf_token(token):
        return jsonify({'error': 'Invalid CSRF token'}), 403
```

### Audit Logging

#### Game Action Logging
```python
def log_game_action(employee_id, action, game_data, outcome=None):
    """Log all game actions for audit trail"""
    log_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'employee_id': employee_id,
        'action': action,  # 'game_awarded', 'game_played', 'prize_won'
        'game_data': game_data,
        'outcome': outcome,
        'ip_address': request.remote_addr,
        'user_agent': request.headers.get('User-Agent')
    }
    
    # Store in audit table
    with DatabaseConnection() as conn:
        conn.execute("""
            INSERT INTO audit_log (timestamp, employee_id, action, details, ip_address)
            VALUES (?, ?, ?, ?, ?)
        """, (log_entry['timestamp'], employee_id, action, 
              json.dumps(log_entry), request.remote_addr))
```

---

## 🔄 Continuous Integration

### Automated Testing Pipeline

#### GitHub Actions Workflow
```yaml
name: Casino System CI/CD

on:
  push:
    branches: [ main, btedev ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.11'
        
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-test.txt
        
    - name: Run unit tests
      run: pytest tests/ -v --cov=app --cov-report=xml
      
    - name: Test game mechanics
      run: python -m pytest tests/test_games.py::test_all_games_playable
      
    - name: Audio system test
      run: python test_audio_integration.py
      
    - name: Performance benchmarks
      run: python benchmark_performance.py --quick
      
    - name: Upload coverage
      uses: codecov/codecov-action@v1
```

### Code Quality Checks

#### Pre-commit Hooks
```bash
# .pre-commit-config.yaml
repos:
-   repo: https://github.com/psf/black
    rev: 22.3.0
    hooks:
    -   id: black
        language_version: python3.11
        
-   repo: https://github.com/pycqa/flake8
    rev: 4.0.1
    hooks:
    -   id: flake8
        args: ['--max-line-length=88', '--ignore=E203,W503']
        
-   repo: local
    hooks:
    -   id: test-game-functionality
        name: Test Game Functionality
        entry: python -m pytest tests/test_games.py -x
        language: system
        pass_filenames: false
```

---

## 📞 Support & Troubleshooting

### Common Issues

#### Audio Not Playing
```javascript
// Debug audio issues
console.log('Audio Context State:', window.casinoAudio?.audioContext?.state);
console.log('Available Audio Files:', Object.keys(window.casinoAudio?.bufferCache || {}));

// Force audio context activation (required by browsers)
document.addEventListener('click', function enableAudio() {
    if (window.casinoAudio?.audioContext?.state === 'suspended') {
        window.casinoAudio.audioContext.resume();
        console.log('Audio context resumed');
    }
    document.removeEventListener('click', enableAudio);
}, { once: true });
```

#### Game Not Responding
```python
# Server-side debugging
def debug_game_state(game_id):
    with DatabaseConnection() as conn:
        game = conn.execute(
            "SELECT * FROM mini_games WHERE id = ?", (game_id,)
        ).fetchone()
        
        if not game:
            return {"error": "Game not found"}
            
        return {
            "game_id": game_id,
            "status": game['status'],
            "employee_id": game['employee_id'],
            "game_type": game['game_type'],
            "awarded_date": game['awarded_date'],
            "played_date": game['played_date'],
            "can_play": game['status'] == 'awarded'
        }
```

### Monitoring Dashboards

#### System Health Dashboard
```html
<!-- Admin monitoring dashboard -->
<div class="casino-health-dashboard">
    <div class="metric-card">
        <h3>Active Games</h3>
        <div class="metric-value" id="activeGames">-</div>
    </div>
    
    <div class="metric-card">
        <h3>Audio System</h3>
        <div class="metric-status" id="audioStatus">-</div>
    </div>
    
    <div class="metric-card">
        <h3>Database Health</h3>
        <div class="metric-status" id="dbStatus">-</div>
    </div>
    
    <div class="metric-card">
        <h3>Progressive Jackpot</h3>
        <div class="metric-value" id="jackpotValue">-</div>
    </div>
</div>
```

---

*Last updated: August 28, 2025*  
*Version: 3.0.0 - Professional Vegas Casino System*  
*For developer questions, contact: Tim Sandahl*