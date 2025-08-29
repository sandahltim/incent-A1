# Deployment and Configuration Technical Documentation

**Version**: 1.0.0  
**Date**: August 29, 2025  
**Target Audience**: System Administrators, DevOps Engineers, Developers  

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation Process](#installation-process)
3. [Configuration Management](#configuration-management)
4. [Service Configuration](#service-configuration)
5. [Port Management](#port-management)
6. [Security Configuration](#security-configuration)
7. [Environment Setup](#environment-setup)
8. [Monitoring and Logging](#monitoring-and-logging)
9. [Backup Configuration](#backup-configuration)
10. [Production Deployment](#production-deployment)

## System Requirements

### Hardware Requirements

**Minimum Requirements:**
- CPU: 1 GHz ARM64 or x86_64
- RAM: 1 GB 
- Storage: 2 GB free space
- Network: 100 Mbps

**Recommended Requirements:**
- CPU: 2 GHz ARM64 or x86_64 (quad-core)
- RAM: 4 GB
- Storage: 10 GB free space (SSD preferred)
- Network: 1 Gbps

### Software Requirements

```bash
# Operating System
Linux (Ubuntu 20.04+ or Raspberry Pi OS)
Python 3.11 or higher
SQLite 3.31+
nginx (optional, for reverse proxy)
systemd (for service management)

# Python Dependencies (see requirements.txt)
Flask==2.3.2
Flask-WTF==1.1.1
Werkzeug==2.3.6
```

### System Specifications

**Current Production Environment:**
```
OS: Linux 6.12.34+rpt-rpi-2712 (Raspberry Pi)
Platform: linux
Architecture: ARM64
Python: 3.11.x
Working Directory: /home/tim/incentDev
Database: SQLite at /home/tim/incentDev/incentive.db
Service Port: 7410 (changed from 7409)
```

## Installation Process

### Automated Installation

Use the provided installation script:

```bash
# Clone or extract the application
cd /home/tim/incentDev

# Run automated setup
chmod +x install.sh
./install.sh
```

### Manual Installation Steps

#### 1. System Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 and pip
sudo apt install python3.11 python3.11-pip python3.11-venv -y

# Install system dependencies
sudo apt install sqlite3 build-essential -y

# Install optional dependencies
sudo apt install nginx supervisor htop -y
```

#### 2. Application Setup

```bash
# Create application directory
sudo mkdir -p /home/tim/incentDev
sudo chown tim:tim /home/tim/incentDev

# Navigate to application directory
cd /home/tim/incentDev

# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

#### 3. Database Initialization

```bash
# Initialize database schema
python init_db.py

# Setup dual game system
python setup_dual_game_system.py

# Verify database integrity
sqlite3 incentive.db "PRAGMA integrity_check;"
```

#### 4. Configuration Setup

```bash
# Copy configuration template
cp config.py.example config.py

# Edit configuration (see Configuration Management section)
nano config.py

# Set proper permissions
chmod 600 config.py
```

## Configuration Management

### Primary Configuration File

**File**: `/home/tim/incentDev/config.py`

```python
# config.py - Version 1.2.7
import os

class Config:
    # Base directory for the project
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # Database configuration
    INCENTIVE_DB_FILE = os.path.join(BASE_DIR, "incentive.db")
    
    # Security configuration
    SECRET_KEY = "A1RentIt2025StaticKeyForSessionsAndCSRFProtection"
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour token expiry
    
    # Application settings
    VOTE_CODE = "A1RentIt2025"
    ADMIN_SECTIONS = ['rules', 'manage_roles']
    
    # Service configuration
    SERVICE_NAME = "incent-dev.service"
    DEFAULT_PORT = 7410  # Updated from 7409
    
    # Database connection pool settings
    DB_POOL_SIZE = 10
    DB_POOL_TIMEOUT = 30
    DB_POOL_MAX_RETRIES = 3
    DB_POOL_HEALTH_CHECK_INTERVAL = 300
    DB_POOL_MAX_OVERFLOW = 5
    DB_POOL_RECYCLE_TIME = 3600
    
    # Caching system settings
    CACHE_MAX_SIZE = 2000
    CACHE_DEFAULT_TTL = 300
    CACHE_CLEANUP_INTERVAL = 60
    CACHE_ENABLED = True
    
    # Cache TTL settings (seconds)
    CACHE_TTL_SCOREBOARD = 30
    CACHE_TTL_RULES = 300
    CACHE_TTL_ROLES = 300
    CACHE_TTL_SETTINGS = 120
    CACHE_TTL_POT_INFO = 120
    CACHE_TTL_VOTING_RESULTS = 300
    CACHE_TTL_ANALYTICS = 600
    CACHE_TTL_EMPLOYEE_GAMES = 60
    CACHE_TTL_ADMIN_DATA = 600
    CACHE_TTL_HISTORY = 300
```

### Environment-Specific Configuration

```python
# config_production.py
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    
    # Security enhancements for production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Performance optimizations
    DB_POOL_SIZE = 20
    CACHE_MAX_SIZE = 5000
    
    # Logging configuration
    LOG_LEVEL = 'INFO'
    LOG_FILE = '/var/log/incentive/app.log'

# config_development.py  
class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    
    # Development-friendly settings
    WTF_CSRF_TIME_LIMIT = None  # No token expiry
    LOG_LEVEL = 'DEBUG'
    
    # Reduced caching for development
    CACHE_DEFAULT_TTL = 60
```

### Configuration Loading

```python
# app.py configuration loading
import os

config_name = os.environ.get('FLASK_CONFIG', 'development')
config_module = f'config_{config_name}'

try:
    config_class = getattr(__import__(config_module), f'{config_name.title()}Config')
    app.config.from_object(config_class)
except (ImportError, AttributeError):
    # Fallback to default config
    app.config.from_object('config.Config')
```

## Service Configuration

### Systemd Service Setup

**Service File**: `/etc/systemd/system/incent-dev.service`

```ini
[Unit]
Description=A1 Rent-It Incentive System - Development
After=network.target
Wants=network-online.target

[Service]
Type=simple
User=tim
Group=tim
WorkingDirectory=/home/tim/incentDev
Environment=PYTHONPATH=/home/tim/incentDev
Environment=FLASK_CONFIG=production
ExecStart=/home/tim/incentDev/venv/bin/python app.py
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=incent-dev

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/home/tim/incentDev
CapabilityBoundingSet=CAP_NET_BIND_SERVICE

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

### Service Management Commands

```bash
# Install service
sudo cp incent-dev.service /etc/systemd/system/
sudo systemctl daemon-reload

# Enable auto-start
sudo systemctl enable incent-dev.service

# Start service
sudo systemctl start incent-dev.service

# Check status
sudo systemctl status incent-dev.service

# View logs
sudo journalctl -u incent-dev.service -f

# Restart service
sudo systemctl restart incent-dev.service

# Stop service
sudo systemctl stop incent-dev.service
```

### Alternative Process Management

#### Using Supervisor

**Configuration**: `/etc/supervisor/conf.d/incentive.conf`

```ini
[program:incentive-app]
command=/home/tim/incentDev/venv/bin/python app.py
directory=/home/tim/incentDev
user=tim
group=tim
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/incentive.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PYTHONPATH="/home/tim/incentDev",FLASK_CONFIG="production"

[program:incentive-worker]
command=/home/tim/incentDev/venv/bin/python -m celery worker -A app.celery
directory=/home/tim/incentDev
user=tim
group=tim
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/supervisor/incentive-worker.log
```

```bash
# Supervisor management
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start incentive-app
sudo supervisorctl status incentive-app
```

## Port Management

### Port Configuration Change

The system has been updated from port 7409 to 7410:

#### Application Configuration

```python
# app.py - Updated port configuration
if __name__ == '__main__':
    # Get port from settings or environment
    port = int(os.environ.get('PORT', 7410))  # Changed from 7409
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,  # Set to False in production
        threaded=True
    )
```

#### Database Settings Update

```sql
-- Update port in database settings
UPDATE settings SET value = '7410' WHERE key = 'port';
```

#### Firewall Configuration

```bash
# UFW (Uncomplicated Firewall)
sudo ufw allow 7410/tcp
sudo ufw delete allow 7409/tcp  # Remove old port

# iptables
sudo iptables -A INPUT -p tcp --dport 7410 -j ACCEPT
sudo iptables -D INPUT -p tcp --dport 7409 -j ACCEPT  # Remove old port
```

#### Service Discovery Update

Update any service discovery or load balancer configurations:

```bash
# nginx upstream configuration
upstream incentive_app {
    server 127.0.0.1:7410;  # Updated from 7409
}

# Health check endpoints
curl http://localhost:7410/api/health
```

### Load Balancer Configuration

#### nginx Reverse Proxy

**Configuration**: `/etc/nginx/sites-available/incentive`

```nginx
upstream incentive_backend {
    server 127.0.0.1:7410 max_fails=3 fail_timeout=30s;
    # Add more backends for high availability
    # server 127.0.0.1:7411 backup;
}

server {
    listen 80;
    server_name incentive.company.com;
    
    # Redirect to HTTPS in production
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name incentive.company.com;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/incentive.crt;
    ssl_certificate_key /etc/ssl/private/incentive.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384:ECDHE-RSA-CHACHA20-POLY1305;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    
    # Static file serving
    location /static/ {
        alias /home/tim/incentDev/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Application proxy
    location / {
        proxy_pass http://incentive_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
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
        proxy_pass http://incentive_backend/api/health;
        access_log off;
    }
}
```

## Security Configuration

### SSL/TLS Configuration

#### Generate Self-Signed Certificates (Development)

```bash
# Generate private key
sudo openssl genrsa -out /etc/ssl/private/incentive.key 2048

# Generate certificate
sudo openssl req -new -x509 -key /etc/ssl/private/incentive.key \
    -out /etc/ssl/certs/incentive.crt -days 365 \
    -subj "/CN=incentive.local"

# Set permissions
sudo chmod 600 /etc/ssl/private/incentive.key
sudo chmod 644 /etc/ssl/certs/incentive.crt
```

#### Production Certificate (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx -y

# Obtain certificate
sudo certbot --nginx -d incentive.company.com

# Auto-renewal setup
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Security Headers Configuration

```python
# app.py - Security headers
from flask_talisman import Talisman

# Configure security headers
Talisman(app, {
    'force_https': True,
    'strict_transport_security': True,
    'strict_transport_security_max_age': 31536000,
    'content_security_policy': {
        'default-src': "'self'",
        'script-src': "'self' 'unsafe-inline'",
        'style-src': "'self' 'unsafe-inline'",
        'img-src': "'self' data:",
        'connect-src': "'self'"
    }
})

@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    return response
```

### File Permissions

```bash
# Set secure file permissions
cd /home/tim/incentDev

# Application files
find . -type f -name "*.py" -exec chmod 644 {} \;
find . -type f -name "*.html" -exec chmod 644 {} \;
find . -type f -name "*.css" -exec chmod 644 {} \;
find . -type f -name "*.js" -exec chmod 644 {} \;

# Configuration files (sensitive)
chmod 600 config.py
chmod 600 .env

# Database file
chmod 660 incentive.db
chown tim:tim incentive.db

# Log directory
sudo mkdir -p /var/log/incentive
sudo chown tim:tim /var/log/incentive
sudo chmod 755 /var/log/incentive

# Executable files
chmod +x install.sh
chmod +x start.sh
```

## Environment Setup

### Environment Variables

**File**: `.env` (in production)

```bash
# Application environment
FLASK_CONFIG=production
SECRET_KEY=A1RentIt2025StaticKeyForSessionsAndCSRFProtection
VOTE_CODE=A1RentIt2025

# Database configuration
DATABASE_URL=sqlite:///incentive.db
DB_POOL_SIZE=20

# Service configuration
PORT=7410
SERVICE_NAME=incent-dev.service

# Security settings
WTF_CSRF_ENABLED=true
SESSION_COOKIE_SECURE=true

# Logging configuration
LOG_LEVEL=INFO
LOG_FILE=/var/log/incentive/app.log

# Cache configuration
CACHE_ENABLED=true
CACHE_MAX_SIZE=5000

# External service URLs (if applicable)
# REDIS_URL=redis://localhost:6379/0
# SMTP_SERVER=smtp.company.com
```

### Environment Loading

```python
# Load environment variables
from dotenv import load_dotenv
import os

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'default-secret-key'
    DATABASE_URL = os.environ.get('DATABASE_URL') or 'sqlite:///incentive.db'
    PORT = int(os.environ.get('PORT', 7410))
    
    # Boolean environment variables
    DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'
    WTF_CSRF_ENABLED = os.environ.get('WTF_CSRF_ENABLED', 'True').lower() == 'true'
```

## Monitoring and Logging

### Logging Configuration

**File**: `logging_config.py`

```python
import logging
import logging.handlers
import os
from config import Config

def setup_logging():
    """Configure application logging."""
    
    # Create logs directory
    log_dir = '/var/log/incentive'
    os.makedirs(log_dir, exist_ok=True)
    
    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, Config.LOG_LEVEL, 'INFO'))
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with rotation
    file_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.handlers.RotatingFileHandler(
        filename=os.path.join(log_dir, 'error.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)
    
    # CSRF specific logging
    csrf_logger = logging.getLogger('flask_wtf.csrf')
    csrf_logger.setLevel(logging.WARNING)
    
    # Database logging
    db_logger = logging.getLogger('database')
    db_logger.setLevel(logging.INFO)
```

### System Monitoring

#### Health Check Endpoint

```python
# app.py - Health check endpoint
@app.route('/api/health')
def health_check():
    """System health check endpoint."""
    try:
        # Check database connectivity
        with DatabaseConnection() as conn:
            conn.execute("SELECT 1").fetchone()
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"
    
    # Check cache status
    cache_status = "healthy" if cache.is_healthy() else "unhealthy"
    
    # System metrics
    import psutil
    cpu_percent = psutil.cpu_percent()
    memory_percent = psutil.virtual_memory().percent
    disk_percent = psutil.disk_usage('/').percent
    
    health_data = {
        "status": "healthy" if db_status == "healthy" and cache_status == "healthy" else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "database": db_status,
        "cache": cache_status,
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent
        }
    }
    
    status_code = 200 if health_data["status"] == "healthy" else 503
    return jsonify(health_data), status_code
```

#### External Monitoring Integration

```bash
# Nagios check
#!/bin/bash
# check_incentive_health.sh

RESPONSE=$(curl -s -w "%{http_code}" http://localhost:7410/api/health)
HTTP_CODE="${RESPONSE: -3}"
BODY="${RESPONSE%???}"

if [ "$HTTP_CODE" -eq 200 ]; then
    echo "OK - Incentive system is healthy"
    exit 0
else
    echo "CRITICAL - Incentive system is unhealthy: $BODY"
    exit 2
fi
```

### Log Analysis

```bash
# Real-time log monitoring
sudo journalctl -u incent-dev.service -f

# Error analysis
sudo grep -i error /var/log/incentive/error.log | tail -50

# Performance analysis
sudo grep -i "slow query" /var/log/incentive/app.log

# CSRF failure analysis
sudo grep -i csrf /var/log/incentive/app.log | tail -20
```

## Backup Configuration

### Database Backup Script

**File**: `scripts/backup.sh`

```bash
#!/bin/bash
# Automated backup script for incentive system

set -e

# Configuration
DB_FILE="/home/tim/incentDev/incentive.db"
BACKUP_DIR="/home/tim/incentDev/backups"
LOG_FILE="/var/log/incentive/backup.log"
RETENTION_DAYS=30

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/incentive.db.bak-$TIMESTAMP"

# Log function
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_message "Starting backup process"

# Create backup
if sqlite3 "$DB_FILE" ".backup '$BACKUP_FILE'"; then
    log_message "Backup created successfully: $BACKUP_FILE"
else
    log_message "ERROR: Backup creation failed"
    exit 1
fi

# Verify backup integrity
if sqlite3 "$BACKUP_FILE" "PRAGMA integrity_check;" | grep -q "ok"; then
    log_message "Backup integrity verified"
else
    log_message "ERROR: Backup integrity check failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Compress backup
if gzip "$BACKUP_FILE"; then
    log_message "Backup compressed: ${BACKUP_FILE}.gz"
    BACKUP_FILE="${BACKUP_FILE}.gz"
else
    log_message "WARNING: Backup compression failed"
fi

# Calculate backup size
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
log_message "Backup size: $BACKUP_SIZE"

# Clean old backups
DELETED_COUNT=$(find "$BACKUP_DIR" -name "incentive.db.bak-*" -mtime +$RETENTION_DAYS -delete -print | wc -l)
if [ "$DELETED_COUNT" -gt 0 ]; then
    log_message "Cleaned up $DELETED_COUNT old backup(s)"
fi

log_message "Backup process completed successfully"

# Optional: Send notification
# curl -X POST "https://hooks.slack.com/..." -d "{'text':'Backup completed: $BACKUP_FILE'}"
```

### Cron Configuration

```bash
# Add to crontab: crontab -e
# Daily backup at 2 AM
0 2 * * * /home/tim/incentDev/scripts/backup.sh

# Weekly integrity check
0 3 * * 0 sqlite3 /home/tim/incentDev/incentive.db "PRAGMA integrity_check;" | mail -s "DB Integrity Check" admin@company.com
```

### Backup Restoration

```bash
# Restore from compressed backup
gunzip -c /home/tim/incentDev/backups/incentive.db.bak-20250829_020000.gz > incentive.db.restored

# Verify restored database
sqlite3 incentive.db.restored "PRAGMA integrity_check;"

# Replace current database (with service stopped)
sudo systemctl stop incent-dev.service
cp incentive.db incentive.db.old
cp incentive.db.restored incentive.db
sudo systemctl start incent-dev.service
```

## Production Deployment

### Pre-Deployment Checklist

```bash
# Security checklist
□ HTTPS configured and tested
□ Firewall rules configured
□ File permissions set correctly
□ Secret keys rotated
□ Debug mode disabled

# Performance checklist  
□ Database optimized and indexed
□ Connection pooling configured
□ Caching enabled
□ Static files served efficiently
□ Resource limits set

# Monitoring checklist
□ Health checks implemented
□ Logging configured and tested
□ Backup system operational
□ Monitoring alerts configured
□ Documentation updated
```

### Deployment Script

**File**: `scripts/deploy.sh`

```bash
#!/bin/bash
# Production deployment script

set -e

echo "Starting deployment process..."

# Pre-deployment checks
echo "Running pre-deployment checks..."
python -m pytest tests/ --quiet
python csrf_system_validation.py

# Backup current deployment
echo "Creating deployment backup..."
./scripts/backup.sh

# Update application
echo "Updating application files..."
# rsync or git pull would happen here

# Database migrations
echo "Running database migrations..."
python setup_dual_game_system.py --verify

# Update dependencies
echo "Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt --quiet

# Compile assets (if applicable)
echo "Compiling assets..."
# Asset compilation commands would go here

# Restart services
echo "Restarting services..."
sudo systemctl restart incent-dev.service
sudo systemctl reload nginx

# Post-deployment verification
echo "Running post-deployment tests..."
sleep 10  # Wait for service to start
curl -f http://localhost:7410/api/health || {
    echo "Health check failed! Rolling back..."
    # Rollback commands would go here
    exit 1
}

echo "Deployment completed successfully!"

# Send notification
echo "Deployment completed at $(date)" | mail -s "Deployment Success" admin@company.com
```

### Blue-Green Deployment

```bash
# Blue-Green deployment setup
# Production runs on port 7410 (blue)
# Staging runs on port 7411 (green)

# Deploy to green environment
./scripts/deploy.sh --target=green --port=7411

# Test green environment
./scripts/test.sh --target=green

# Switch traffic to green (update load balancer)
nginx -s reload

# Keep blue as rollback option
```

---

## Performance Tuning

### Database Optimization

```sql
-- Optimize SQLite for production
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA temp_store = memory;
PRAGMA mmap_size = 268435456; -- 256MB
```

### Application Tuning

```python
# app.py - Production optimizations
app.config.update(
    # Disable template auto-reloading
    TEMPLATES_AUTO_RELOAD=False,
    
    # Enable response compression
    COMPRESS_MIMETYPES=['text/html', 'text/css', 'application/json'],
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME=timedelta(hours=12)
)

# Connection pool tuning
DB_POOL_SIZE = min(20, (os.cpu_count() or 1) * 4)
```

## Related Documentation

- [CSRF Security Implementation](CSRF_SECURITY_TECHNICAL_DOCS.md)
- [Dual Game System Technical Architecture](DUAL_GAME_SYSTEM_TECHNICAL_DOCS.md)
- [Database Schema Documentation](DATABASE_SCHEMA_TECHNICAL_DOCS.md)
- [Testing and Validation Procedures](TESTING_VALIDATION_TECHNICAL_DOCS.md)

---

**Last Updated**: August 29, 2025  
**Next Review**: September 29, 2025  
**Maintained By**: System Administration Team