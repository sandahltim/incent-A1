#!/usr/bin/bash
echo "🎰 Setting up A1 Rent-It Incentive Program with Vegas Casino Games..."

# System requirements check
echo "Checking system requirements..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 is required but not installed. Please install Python3 and try again."
    exit 1
fi

if ! command -v sqlite3 &> /dev/null; then
    echo "❌ SQLite3 is required but not installed. Installing..."
    sudo apt update && sudo apt install -y sqlite3
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️  FFmpeg not found. Installing for audio file support..."
    sudo apt install -y ffmpeg
fi

# Prompt for port
read -p "Enter port for server [7409]: " PORT
PORT=${PORT:-7409}

echo "📦 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "📥 Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
else
    pip install flask gunicorn werkzeug flask-wtf wtforms pandas matplotlib
fi

echo "🗄️  Initializing database..."
python init_db.py

echo "💾 Storing port configuration..."
python - <<EOF
from config import Config
import sqlite3
conn = sqlite3.connect(Config.INCENTIVE_DB_FILE)
conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ('port', '$PORT'))
conn.commit()
conn.close()
EOF

echo "🔧 Setting up audio files..."
# Create audio directory if it doesn't exist
mkdir -p static/audio

# Check if audio files exist and are properly sized
if [ ! -s "static/coin-drop.mp3" ] || [ ! -s "static/jackpot-horn.mp3" ] || [ ! -s "static/slot-pull.mp3" ]; then
    echo "⚠️  Audio files missing or corrupted. Attempting to download/create..."
    python3 - <<'AUDIO_SCRIPT'
import subprocess
import os
from pathlib import Path
import math
import wave
import struct

def create_simple_tone_wav(filename, frequency=440, duration=0.5):
    """Create a simple tone WAV file"""
    sample_rate = 44100
    frames = int(duration * sample_rate)
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        
        for i in range(frames):
            value = int(32767 * math.sin(2 * math.pi * frequency * i / sample_rate) * 0.3)
            wav_file.writeframes(struct.pack('<h', value))
    print(f"Created: {filename}")

static_dir = Path('static')

# Create simple tones
create_simple_tone_wav(static_dir / 'jackpot-horn.wav', frequency=800, duration=1.0)
create_simple_tone_wav(static_dir / 'slot-pull.wav', frequency=200, duration=0.8) 
create_simple_tone_wav(static_dir / 'coin-drop.wav', frequency=600, duration=0.3)

# Convert to MP3 if ffmpeg available
for wav_file in ['jackpot-horn.wav', 'slot-pull.wav', 'coin-drop.wav']:
    mp3_file = wav_file.replace('.wav', '.mp3')
    try:
        subprocess.run(['ffmpeg', '-i', f'static/{wav_file}', '-y', f'static/{mp3_file}'], 
                      capture_output=True, check=True)
        os.remove(f'static/{wav_file}')
        print(f"Converted: {mp3_file}")
    except:
        print(f"FFmpeg conversion failed for {wav_file}")

# Create copies for additional audio files
try:
    import shutil
    shutil.copy('static/coin-drop.mp3', 'static/casino-win.mp3')
    shutil.copy('static/jackpot-horn.mp3', 'static/reel-spin.mp3')
    print("Created additional audio files")
except Exception as e:
    print(f"Error creating additional files: {e}")
AUDIO_SCRIPT
    echo "✅ Audio files configured"
fi

# Make start script executable
chmod +x start.sh

# Configure systemd service to run the app on boot
echo "⚙️  Configuring systemd service..."
APP_DIR="$(pwd)"
SERVICE_NAME="incent-dev.service"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"
sudo tee "$SERVICE_PATH" >/dev/null <<SERVICE
[Unit]
Description=A1 Rent-It Incentive Program
After=network.target

[Service]
Type=simple
User=tim
Group=tim
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/start.sh
Restart=always
RestartSec=10
Environment=PORT=$PORT

[Install]
WantedBy=multi-user.target
SERVICE

sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl start "$SERVICE_NAME"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📊 System Details:"
echo "   Port: $PORT"
echo "   Service: $SERVICE_NAME"
echo "   Database: $(pwd)/incentive.db"
echo ""
echo "🌐 Access URLs:"
echo "   Employee Portal: http://$(hostname):$PORT/"
echo "   Admin Login: http://$(hostname):$PORT/admin_login"
echo ""
echo "🔑 Default Credentials:"
echo "   Master Admin: username 'master', password 'Master8101'"
echo "   Regular Admin: username 'admin1', password 'Broadway8101'"
echo ""
echo "🎰 Features Available:"
echo "   ✅ Employee voting system"
echo "   ✅ Point management"
echo "   ✅ Vegas-style casino minigames"
echo "   ✅ Audio system with casino sounds"
echo "   ✅ Comprehensive reporting"
echo ""
echo "🔧 Service Management:"
echo "   Status: sudo systemctl status $SERVICE_NAME"
echo "   Restart: sudo systemctl restart $SERVICE_NAME"
echo "   Logs: sudo journalctl -u $SERVICE_NAME -f"
echo ""
echo "📚 Documentation:"
echo "   README.md - Complete system documentation"
echo "   USAGE.md - User guide and troubleshooting"
