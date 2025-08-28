# 🚀 Vegas Casino System Deployment Guide

## System Requirements

### Hardware Requirements
- **CPU**: 2+ cores (ARM64 or x86_64)
- **RAM**: 2GB minimum, 4GB recommended
- **Storage**: 5GB minimum, 10GB recommended
- **Network**: 100 Mbps for optimal audio streaming

### Software Requirements
- **OS**: Linux (Ubuntu 20.04+ / Raspberry Pi OS)
- **Python**: 3.11+
- **Database**: SQLite 3.35+
- **Web Server**: Nginx (optional but recommended)
- **Process Manager**: systemd

---

## 🏗️ Installation Steps

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.11 python3.11-venv python3-pip sqlite3 nginx git

# Create application user
sudo useradd -m -s /bin/bash casino
sudo usermod -a -G www-data casino
```

### 2. Application Setup

```bash
# Clone repository
cd /opt
sudo git clone https://github.com/sandahltim/incent-A1.git incentive-casino
sudo chown -R casino:casino incentive-casino
cd incentive-casino

# Switch to user
sudo su - casino
cd /opt/incentive-casino

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Install audio processing dependencies (optional)
pip install pydub soundfile librosa
```

### 3. Database Initialization

```bash
# Initialize database
python3 init_db.py

# Import sample data (optional)
python3 -c "
from app import DatabaseConnection
import json

# Initialize prize system
with DatabaseConnection() as conn:
    default_prizes = [
        ('dice_small_win', 'Dice Small Win', 5.0, 10.0, 1, 'system'),
        ('wheel_jackpot', 'Fortune Wheel Jackpot', 500.0, 0.1, 1, 'system'),
        # ... add all 12 prize types
    ]
    
    for prize_type, description, base_value, rate, managed, updated_by in default_prizes:
        conn.execute('''
            INSERT OR IGNORE INTO prize_values 
            (prize_type, prize_description, base_dollar_value, point_to_dollar_rate, is_system_managed, updated_by)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (prize_type, description, base_value, rate, managed, updated_by))
    
    conn.commit()
    print('Database initialized with casino system')
"
```

### 4. Audio System Setup

```bash
# Verify audio files exist
ls static/audio/*.mp3 | wc -l  # Should show 69 files

# Test audio system
python3 test_audio_integration.py

# Generate missing audio files (if needed)
python3 generate_audio_files.py

# Set proper permissions
chmod -R 644 static/audio/*
```

### 5. Configuration

```bash
# Create environment configuration
cat > .env << EOF
FLASK_ENV=production
DATABASE_URL=sqlite:///incentive.db
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
AUDIO_CACHE_SIZE=100MB
MAX_CONCURRENT_GAMES=500
PROGRESSIVE_JACKPOT_SEED=500.00
JACKPOT_CONTRIBUTION_RATE=0.01
WTF_CSRF_TIME_LIMIT=3600
SESSION_COOKIE_SECURE=True
SESSION_COOKIE_HTTPONLY=True
EOF

# Set proper permissions
chmod 600 .env
```

---

## 🔧 Service Configuration

### 1. Systemd Service Setup

```bash
# Create service file
sudo tee /etc/systemd/system/incentive-casino.service > /dev/null << EOF
[Unit]
Description=Vegas Casino Employee Incentive System
After=network.target

[Service]
Type=exec
User=casino
Group=casino
WorkingDirectory=/opt/incentive-casino
Environment=PATH=/opt/incentive-casino/venv/bin
ExecStart=/opt/incentive-casino/venv/bin/gunicorn --workers 4 --timeout 180 --bind 0.0.0.0:7409 app:app
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security settings
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/incentive-casino
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable incentive-casino.service
sudo systemctl start incentive-casino.service
sudo systemctl status incentive-casino.service
```

### 2. Nginx Configuration

```bash
# Remove default site
sudo rm -f /etc/nginx/sites-enabled/default

# Create casino site configuration
sudo tee /etc/nginx/sites-available/incentive-casino > /dev/null << 'EOF'
server {
    listen 80;
    server_name your-domain.com;  # Replace with your domain
    
    # Redirect HTTP to HTTPS (optional)
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;  # Replace with your domain
    
    # SSL configuration (if using HTTPS)
    # ssl_certificate /path/to/cert.pem;
    # ssl_certificate_key /path/to/key.pem;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Audio files optimization
    location ~* \.(mp3|ogg|wav|m4a)$ {
        root /opt/incentive-casino;
        expires 1y;
        add_header Cache-Control "public, immutable";
        add_header Access-Control-Allow-Origin "*";
        
        # Enable gzip for audio (if pre-compressed)
        gzip_static on;
        
        # Range requests for audio streaming
        add_header Accept-Ranges bytes;
    }
    
    # Static assets caching
    location /static/ {
        root /opt/incentive-casino;
        expires 30d;
        add_header Cache-Control "public";
        
        # Compress static files
        gzip on;
        gzip_types text/css application/javascript image/svg+xml;
    }
    
    # Main application proxy
    location / {
        proxy_pass http://127.0.0.1:7409;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (for real-time features)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Health check endpoint
    location /health {
        proxy_pass http://127.0.0.1:7409;
        access_log off;
    }
}
EOF

# Enable site
sudo ln -s /etc/nginx/sites-available/incentive-casino /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Start nginx
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl status nginx
```

---

## 🔒 Security Hardening

### 1. Firewall Configuration

```bash
# Configure UFW firewall
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing

# Allow SSH (adjust port as needed)
sudo ufw allow 22/tcp

# Allow HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Allow application port (if not using nginx proxy)
# sudo ufw allow 7409/tcp

# Enable firewall
sudo ufw --force enable
sudo ufw status
```

### 2. SSL Certificate (Recommended)

```bash
# Install Certbot for Let's Encrypt
sudo apt install -y certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d your-domain.com

# Test auto-renewal
sudo certbot renew --dry-run

# Set up automatic renewal
echo "0 12 * * * /usr/bin/certbot renew --quiet" | sudo crontab -
```

### 3. Database Security

```bash
# Set proper database permissions
chmod 640 /opt/incentive-casino/incentive.db
chown casino:casino /opt/incentive-casino/incentive.db

# Create database backup directory
mkdir -p /opt/incentive-casino/backups
chmod 750 /opt/incentive-casino/backups
```

---

## 📊 Monitoring Setup

### 1. Log Configuration

```bash
# Create log directories
sudo mkdir -p /var/log/incentive-casino
sudo chown casino:casino /var/log/incentive-casino

# Configure logrotate
sudo tee /etc/logrotate.d/incentive-casino > /dev/null << EOF
/var/log/incentive-casino/*.log {
    daily
    missingok
    rotate 52
    compress
    notifempty
    create 644 casino casino
    postrotate
        systemctl reload incentive-casino.service > /dev/null 2>&1 || true
    endscript
}
EOF
```

### 2. Health Monitoring

```bash
# Create health check script
tee /opt/incentive-casino/healthcheck.sh > /dev/null << 'EOF'
#!/bin/bash
HEALTH_URL="http://localhost:7409/health"
LOG_FILE="/var/log/incentive-casino/health.log"

# Check application health
response=$(curl -s -o /dev/null -w "%{http_code}" "$HEALTH_URL" 2>/dev/null)

timestamp=$(date '+%Y-%m-%d %H:%M:%S')

if [ "$response" = "200" ]; then
    echo "$timestamp - Health check passed" >> "$LOG_FILE"
    exit 0
else
    echo "$timestamp - Health check failed (HTTP $response)" >> "$LOG_FILE"
    
    # Restart service if health check fails
    systemctl restart incentive-casino.service
    echo "$timestamp - Service restarted" >> "$LOG_FILE"
    exit 1
fi
EOF

chmod +x /opt/incentive-casino/healthcheck.sh

# Add to crontab for monitoring every 5 minutes
(crontab -l 2>/dev/null; echo "*/5 * * * * /opt/incentive-casino/healthcheck.sh") | crontab -
```

### 3. System Monitoring

```bash
# Install system monitoring tools
sudo apt install -y htop iotop nethogs

# Create system stats script
tee /opt/incentive-casino/system_stats.sh > /dev/null << 'EOF'
#!/bin/bash
LOG_FILE="/var/log/incentive-casino/system.log"
timestamp=$(date '+%Y-%m-%d %H:%M:%S')

# Get system stats
cpu_usage=$(top -bn1 | grep "Cpu(s)" | awk '{print $2}' | sed 's/%us,//')
memory_usage=$(free | grep Mem | awk '{printf("%.1f", $3/$2 * 100.0)}')
disk_usage=$(df -h / | awk 'NR==2{printf "%s", $5}')

# Log stats
echo "$timestamp - CPU: ${cpu_usage}%, Memory: ${memory_usage}%, Disk: ${disk_usage}" >> "$LOG_FILE"

# Check for high resource usage
if (( $(echo "$memory_usage > 90" | bc -l) )); then
    echo "$timestamp - WARNING: High memory usage (${memory_usage}%)" >> "$LOG_FILE"
fi
EOF

chmod +x /opt/incentive-casino/system_stats.sh

# Monitor every 15 minutes
(crontab -l 2>/dev/null; echo "*/15 * * * * /opt/incentive-casino/system_stats.sh") | crontab -
```

---

## 💾 Backup Configuration

### 1. Database Backup

```bash
# Create backup script
tee /opt/incentive-casino/backup_db.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/incentive-casino/backups"
DB_PATH="/opt/incentive-casino/incentive.db"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Create database backup
sqlite3 "$DB_PATH" ".backup $BACKUP_DIR/incentive_${DATE}.db"

# Compress backup
gzip "$BACKUP_DIR/incentive_${DATE}.db"

# Clean up old backups (keep 30 days)
find "$BACKUP_DIR" -name "incentive_*.db.gz" -mtime +30 -delete

echo "$(date) - Database backup completed: incentive_${DATE}.db.gz"
EOF

chmod +x /opt/incentive-casino/backup_db.sh

# Schedule daily backups at 2 AM
(crontab -l 2>/dev/null; echo "0 2 * * * /opt/incentive-casino/backup_db.sh") | crontab -
```

### 2. Full System Backup

```bash
# Create full backup script
tee /opt/incentive-casino/backup_full.sh > /dev/null << 'EOF'
#!/bin/bash
BACKUP_DIR="/opt/incentive-casino/backups"
SOURCE_DIR="/opt/incentive-casino"
DATE=$(date +%Y%m%d_%H%M%S)

# Create full application backup (excluding venv and logs)
tar -czf "$BACKUP_DIR/full_backup_${DATE}.tar.gz" \
    --exclude="venv" \
    --exclude="logs" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude="backups" \
    -C "$(dirname $SOURCE_DIR)" "$(basename $SOURCE_DIR)"

# Clean up old full backups (keep 7 days)
find "$BACKUP_DIR" -name "full_backup_*.tar.gz" -mtime +7 -delete

echo "$(date) - Full backup completed: full_backup_${DATE}.tar.gz"
EOF

chmod +x /opt/incentive-casino/backup_full.sh

# Schedule weekly full backups on Sundays at 1 AM
(crontab -l 2>/dev/null; echo "0 1 * * 0 /opt/incentive-casino/backup_full.sh") | crontab -
```

---

## 🚀 Performance Optimization

### 1. System Tuning

```bash
# Optimize for web application workload
sudo tee -a /etc/sysctl.conf > /dev/null << EOF
# Network optimizations
net.core.somaxconn = 1024
net.ipv4.tcp_max_syn_backlog = 2048
net.ipv4.tcp_syncookies = 1

# Memory optimizations
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF

# Apply changes
sudo sysctl -p
```

### 2. Database Optimization

```bash
# Create database optimization script
tee /opt/incentive-casino/optimize_db.sh > /dev/null << 'EOF'
#!/bin/bash
DB_PATH="/opt/incentive-casino/incentive.db"

echo "Optimizing database..."

sqlite3 "$DB_PATH" << SQL
-- Analyze tables for query optimization
ANALYZE;

-- Vacuum database to reclaim space
VACUUM;

-- Update statistics
ANALYZE sqlite_master;

-- Create performance indexes if they don't exist
CREATE INDEX IF NOT EXISTS idx_mini_games_employee_date ON mini_games(employee_id, played_date);
CREATE INDEX IF NOT EXISTS idx_mini_game_payouts_date ON mini_game_payouts(payout_date);
CREATE INDEX IF NOT EXISTS idx_employees_active ON employees(active, score);
CREATE INDEX IF NOT EXISTS idx_score_history_date ON score_history(employee_id, date);

.quit
SQL

echo "Database optimization completed"
EOF

chmod +x /opt/incentive-casino/optimize_db.sh

# Run weekly optimization
(crontab -l 2>/dev/null; echo "0 3 * * 1 /opt/incentive-casino/optimize_db.sh") | crontab -
```

---

## 🧪 Testing & Validation

### 1. Post-Deployment Testing

```bash
# Run comprehensive test suite
cd /opt/incentive-casino
source venv/bin/activate

# Test all components
python -m pytest tests/ -v

# Test specific game functionality
python test_audio_integration.py
python test_minigames.py

# Performance testing
python benchmark_performance.py --quick

# Test health endpoints
curl -I http://localhost:7409/health
curl -I http://localhost:7409/minigames
curl -I http://localhost:7409/employee_portal
```

### 2. Load Testing

```bash
# Install load testing tools
pip install locust requests

# Create load test script
tee load_test.py > /dev/null << 'EOF'
from locust import HttpUser, task, between
import random

class CasinoUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def view_main_page(self):
        self.client.get("/")
    
    @task(2)
    def view_employee_portal(self):
        self.client.get("/employee_portal")
    
    @task(1)
    def view_minigames(self):
        self.client.get("/minigames")
    
    @task(1)
    def health_check(self):
        self.client.get("/health")
EOF

# Run load test
locust -f load_test.py --host=http://localhost:7409 --users=50 --spawn-rate=5 --run-time=5m
```

---

## 🔄 Updates & Maintenance

### 1. Application Updates

```bash
# Create update script
tee /opt/incentive-casino/update_app.sh > /dev/null << 'EOF'
#!/bin/bash
cd /opt/incentive-casino

echo "Starting application update..."

# Backup current version
cp -r . ../incentive-casino-backup-$(date +%Y%m%d)

# Pull latest changes
git fetch origin
git checkout btedev  # or main branch
git pull origin btedev

# Update Python dependencies
source venv/bin/activate
pip install -r requirements.txt

# Run database migrations (if any)
python -c "
from app import DatabaseConnection
# Run any necessary migrations here
print('Database migrations completed')
"

# Test the application
python -m pytest tests/test_app.py -x

# Restart service
sudo systemctl restart incentive-casino.service

# Verify service is running
sleep 5
curl -f http://localhost:7409/health || {
    echo "Health check failed, rolling back..."
    sudo systemctl stop incentive-casino.service
    cp -r ../incentive-casino-backup-$(date +%Y%m%d)/* .
    sudo systemctl start incentive-casino.service
    exit 1
}

echo "Application update completed successfully"
EOF

chmod +x /opt/incentive-casino/update_app.sh
```

### 2. Maintenance Mode

```bash
# Create maintenance mode toggle
tee /opt/incentive-casino/maintenance.sh > /dev/null << 'EOF'
#!/bin/bash

MAINTENANCE_FILE="/opt/incentive-casino/MAINTENANCE_MODE"

case "$1" in
    enable)
        touch "$MAINTENANCE_FILE"
        echo "Maintenance mode enabled"
        ;;
    disable)
        rm -f "$MAINTENANCE_FILE"
        echo "Maintenance mode disabled"
        ;;
    status)
        if [ -f "$MAINTENANCE_FILE" ]; then
            echo "Maintenance mode: ENABLED"
        else
            echo "Maintenance mode: DISABLED"
        fi
        ;;
    *)
        echo "Usage: $0 {enable|disable|status}"
        exit 1
        ;;
esac
EOF

chmod +x /opt/incentive-casino/maintenance.sh
```

---

## 📞 Troubleshooting

### Common Issues

#### Service Won't Start
```bash
# Check service status
sudo systemctl status incentive-casino.service

# Check logs
sudo journalctl -u incentive-casino.service -f

# Check port availability
sudo netstat -tlnp | grep 7409

# Manually test application
cd /opt/incentive-casino
source venv/bin/activate
python app.py
```

#### Audio Files Not Loading
```bash
# Check file permissions
ls -la static/audio/

# Test audio files
file static/audio/*.mp3

# Check nginx audio serving
curl -I http://localhost/static/audio/button-click.mp3

# Regenerate missing files
python generate_audio_files.py
```

#### Database Issues
```bash
# Check database integrity
sqlite3 incentive.db "PRAGMA integrity_check;"

# Check database permissions
ls -la incentive.db*

# Restore from backup
gunzip -c backups/incentive_YYYYMMDD_HHMMSS.db.gz > incentive.db
```

### Performance Issues
```bash
# Monitor system resources
htop
iotop -a

# Check application performance
curl -w "@curl-format.txt" -s http://localhost:7409/health

# Optimize database
./optimize_db.sh

# Clear application caches
rm -rf __pycache__/
rm -rf static/temp_audio/
```

---

## 📋 Post-Deployment Checklist

- [ ] Service is running and enabled
- [ ] Nginx is configured and running
- [ ] SSL certificate is installed (if applicable)
- [ ] Firewall rules are configured
- [ ] Database is initialized with sample data
- [ ] All 69 audio files are present and accessible
- [ ] Backup scripts are scheduled
- [ ] Monitoring and health checks are active
- [ ] Load testing passes with acceptable performance
- [ ] All game functionality tested and working
- [ ] Admin panel accessible and functional
- [ ] Employee portal responsive on mobile devices
- [ ] Progressive jackpot system operational
- [ ] Audio system working across different browsers
- [ ] Security headers configured
- [ ] Log rotation configured
- [ ] Update procedures documented and tested

---

*Deployment completed! Your Vegas Casino Employee Incentive System is ready for production use.*

*Last updated: August 28, 2025*  
*Version: 3.0.0 - Professional Vegas Casino Experience*