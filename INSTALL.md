# A1 Rent-It Incentive Program - Installation Guide

## Quick Install (Recommended)

The easiest way to install the system is using the automated installer:

```bash
git clone https://github.com/sandahltim/incentive.git
cd incentive
chmod +x install.sh
./install.sh
```

The installer will:
- ✅ Check system requirements
- ✅ Install Python dependencies  
- ✅ Create and configure database
- ✅ Set up audio files for casino games
- ✅ Configure systemd service
- ✅ Start the application

---

## System Requirements

### Minimum Requirements
- **OS**: Linux (Ubuntu 20.04+ / Debian 11+ / Raspberry Pi OS)
- **Python**: 3.8 or higher
- **Memory**: 1GB RAM
- **Storage**: 2GB free space
- **Network**: Local network access

### Recommended Setup
- **Hardware**: Raspberry Pi 4B (4GB RAM) or better
- **OS**: Raspberry Pi OS Lite (64-bit)
- **Python**: 3.11+
- **Storage**: 8GB+ SD card (Class 10)
- **Network**: Static IP or Tailscale for remote access

### Required Packages
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip sqlite3 ffmpeg git curl
```

---

## Manual Installation

If you prefer to install manually or customize the setup:

### 1. Download Source Code
```bash
git clone https://github.com/sandahltim/incentive.git
cd incentive
```

### 2. Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
# Option A: Use requirements.txt (if available)
pip install -r requirements.txt

# Option B: Install manually
pip install flask==2.2.5 gunicorn==23.0.0 werkzeug==2.2.3 \
    flask-wtf==1.2.1 wtforms==3.1.2 pandas==2.2.2 matplotlib==3.9.1
```

### 4. Initialize Database
```bash
python init_db.py
```

### 5. Configure Port
```bash
python - <<EOF
from config import Config
import sqlite3
conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('port', '7409'))
conn.commit()
conn.close()
EOF
```

### 6. Set Up Audio Files
```bash
# Create audio directory
mkdir -p static/audio

# If you have existing audio files, place them in static/
# Required files: coin-drop.mp3, jackpot-horn.mp3, slot-pull.mp3, casino-win.mp3, reel-spin.mp3

# Or generate simple audio files:
python3 -c "
import math, wave, struct, subprocess, shutil
from pathlib import Path

def create_tone_wav(filename, freq=440, duration=0.5):
    sample_rate, frames = 44100, int(duration * 44100)
    with wave.open(filename, 'w') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        for i in range(frames):
            value = int(32767 * math.sin(2 * math.pi * freq * i / sample_rate) * 0.3)
            w.writeframes(struct.pack('<h', value))

static_dir = Path('static')
create_tone_wav(static_dir / 'coin-drop.wav', 600, 0.3)
create_tone_wav(static_dir / 'jackpot-horn.wav', 800, 1.0)
create_tone_wav(static_dir / 'slot-pull.wav', 200, 0.8)

# Convert to MP3 (requires ffmpeg)
for wav in ['coin-drop.wav', 'jackpot-horn.wav', 'slot-pull.wav']:
    mp3 = wav.replace('.wav', '.mp3')
    subprocess.run(['ffmpeg', '-i', f'static/{wav}', '-y', f'static/{mp3}'], capture_output=True)
    Path(f'static/{wav}').unlink()

# Create additional copies
shutil.copy('static/coin-drop.mp3', 'static/casino-win.mp3')
shutil.copy('static/jackpot-horn.mp3', 'static/reel-spin.mp3')
"
```

### 7. Create Systemd Service
```bash
sudo tee /etc/systemd/system/incent-dev.service > /dev/null <<EOF
[Unit]
Description=A1 Rent-It Incentive Program
After=network.target

[Service]
Type=simple
User=$(whoami)
Group=$(whoami)
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/start.sh
Restart=always
RestartSec=10
Environment=PORT=7409

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable incent-dev.service
sudo systemctl start incent-dev.service
```

### 8. Make Scripts Executable
```bash
chmod +x start.sh
```

---

## Configuration Options

### Port Configuration
Default port is 7409. To change:

1. **Via Database** (Recommended):
```bash
python - <<EOF
from config import Config
import sqlite3
conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('port', 'YOUR_PORT'))
conn.commit()
conn.close()
EOF
```

2. **Via Environment Variable**:
```bash
export PORT=8080
sudo systemctl restart incent-dev
```

### Security Settings
- Change default admin passwords immediately
- Use strong passwords (12+ characters)
- Consider firewall rules for port access
- Regular database backups

### Performance Tuning
Edit `start.sh` for Gunicorn workers:
```bash
# For Pi 4 (4GB RAM):
gunicorn --workers 2 --timeout 180 --bind 0.0.0.0:$PORT app:app

# For more powerful systems:
gunicorn --workers 4 --timeout 300 --bind 0.0.0.0:$PORT app:app
```

---

## Post-Installation Setup

### 1. Initial Admin Login
1. Navigate to `http://YOUR_PI_IP:7409/admin_login`
2. Login with:
   - Username: `master`
   - Password: `Master8101`

### 2. Change Default Passwords
1. Go to Admin Panel → Manage Admins
2. Change all default passwords
3. Create additional admin accounts as needed

### 3. Configure System Settings
1. Access Settings panel (Master Admin only)
2. Set backup path
3. Configure voting thresholds
4. Adjust minigame prize settings

### 4. Add Employees
1. Go to Admin Panel → Manage Employees
2. Add employee records with roles
3. Set initial point values
4. Configure role percentages

### 5. Test System
1. Test voting system
2. Play minigames
3. Verify audio works
4. Check data export functions

---

## Networking Setup

### Local Network Access
```bash
# Find your Pi's IP address
hostname -I

# Access via:
# http://PI_IP_ADDRESS:7409
```

### Static IP (Recommended)
Edit `/etc/dhcpcd.conf`:
```
interface wlan0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

### Tailscale (Remote Access)
```bash
# Install Tailscale for secure remote access
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

---

## Backup & Recovery

### Automated Backup Setup
```bash
# Create backup script
cat > backup.sh << 'EOF'
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/home/$(whoami)/backups"
mkdir -p "$BACKUP_DIR"

# Stop service
sudo systemctl stop incent-dev

# Backup database
cp incentive.db "$BACKUP_DIR/incentive_$DATE.db"

# Backup entire directory (excluding venv)
tar -czf "$BACKUP_DIR/incentive_full_$DATE.tar.gz" \
    --exclude=venv --exclude=__pycache__ .

# Start service
sudo systemctl start incent-dev

echo "Backup completed: $BACKUP_DIR/incentive_$DATE.db"
EOF

chmod +x backup.sh

# Add to crontab for daily backups
echo "0 2 * * * /home/$(whoami)/incentive/backup.sh" | crontab -
```

### Restore from Backup
```bash
# Stop service
sudo systemctl stop incent-dev

# Restore database
cp backup/incentive_YYYYMMDD_HHMMSS.db incentive.db

# Start service
sudo systemctl start incent-dev
```

---

## Troubleshooting Installation

### Common Issues

**Permission Denied**:
```bash
# Fix ownership
sudo chown -R $USER:$USER /home/$USER/incentive
chmod +x install.sh start.sh
```

**Python Module Not Found**:
```bash
# Reinstall in virtual environment
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

**Service Won't Start**:
```bash
# Check logs
sudo journalctl -u incent-dev -f

# Check start script
chmod +x start.sh
./start.sh  # Test manually
```

**Database Issues**:
```bash
# Reinitialize database
rm incentive.db
python init_db.py
```

**Audio Problems**:
```bash
# Reinstall audio files
rm static/*.mp3
# Run audio setup section from manual install
```

**Port Already in Use**:
```bash
# Check what's using the port
sudo lsof -i :7409

# Kill process or change port
sudo systemctl stop incent-dev
# Change port in database, then restart
```

### Log Locations
- **Application Logs**: `/home/tim/incentDev/logs/app.log`
- **Service Logs**: `sudo journalctl -u incent-dev`
- **Gunicorn Logs**: `/home/tim/incentDev/logs/gunicorn_*.log`

### Getting Help
1. Check logs for specific error messages
2. Verify all requirements are installed
3. Test each component individually
4. Contact system maintainer (Tim Sandahl)

---

## Upgrade Instructions

### From Previous Versions
```bash
# Backup current installation
./backup.sh

# Pull latest code
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Update database schema
python init_db.py

# Restart service
sudo systemctl restart incent-dev
```

### Major Version Updates
1. Read changelog/release notes
2. Backup entire system
3. Test in development environment first
4. Plan downtime for production update
5. Have rollback plan ready

---

## Security Considerations

### Firewall Setup
```bash
# Basic UFW setup
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 7409/tcp  # Your app port
sudo ufw allow from 192.168.1.0/24  # Local network only
```

### Regular Maintenance
- Update system packages monthly
- Rotate admin passwords quarterly
- Monitor logs for suspicious activity
- Regular database backups
- Test restore procedures

### Access Control
- Use strong passwords
- Limit admin accounts
- Consider VPN for remote access
- Regular security audits