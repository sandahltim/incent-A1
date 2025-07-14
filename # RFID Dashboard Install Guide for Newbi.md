# RFID Dashboard Install Guide for Newbies
# Last Updated: March 16, 2025
# Made by: Tim

Yo, newbie! This guide’s gonna get the RFID Dashboard app running on your Raspberry Pi (3 or newer) so you can track inventory like a pro. Follow these steps—don’t skip shit, and you’ll be golden.

## What You Need
- Raspberry Pi (3, 3B+, 4, etc.) with power cord.
- MicroSD card (16GB or bigger).
- Computer with internet to set up the SD card.
- Network (WiFi or Ethernet) for the Pi.

## Step 1: Set Up Your Pi
1. **Get the OS**:
   - On your computer, download Raspberry Pi Imager from https://www.raspberrypi.com/software/.
   - Open it, pick “Raspberry Pi OS (32-bit)” (Bookworm), choose your SD card, click “Write.”
   - Wait 5-10 minutes—it’s flashing the SD card.
2. **Boot the Pi**:
   - Pop the SD card into your Pi, plug in power.
   - Wait 30 seconds—it’s booting up.
   - Hook up a monitor/keyboard or SSH in (default user: pi, password: raspberry—change this later!).
   - Check your Pi’s IP: In terminal, type `hostname -I`—write down the first number (e.g., 192.168.2.214).
3. **Get Online**:
   - WiFi: `sudo raspi-config`, go to Network Options > WiFi, enter your WiFi name and password.
   - Check it works: `ping google.com`—should see replies. Ctrl+C to stop.

## Step 2: Get the App Package
1. **Grab It**:
   - On the Pi’s terminal, type: `wget https://github.com/sandahltim/-rfidpi/raw/main/rfid_dash.tar.gz`
   - Wait—it’s downloading the package (~50KB).
2. **Unzip It**:
   - `tar -xzf rfid_dash.tar.gz`
   - You’ll see a bunch of files pop up—26 total.

## Step 3: Install the App
1. **Run the Install**:
   - `cd _rfidpi`
   - `./install.sh`
   - Wait 5-10 minutes—it’s setting up Python, dependencies, and the app. Grab a snack.
   - When it says “Install complete! Reboot to start or run ./start.sh,” you’re good.
2. **Reboot**:
   - `sudo reboot`
   - Wait 30 seconds—the Pi’s restarting, and the app should auto-start.

## Step 4: Check It’s Working
1. **Find Your Pi’s IP**:
   - After reboot, in terminal: `hostname -I`
   - Write down the first IP (e.g., 192.168.2.214).
2. **Open the Webpage**:
   - On any device on the same network (phone, laptop), open a browser.
   - Go to: `http://<your-pi-ip>:8101` (e.g., `http://192.168.2.214:8101`).
   - You should see a navigation bar with “Home,” “Active Rentals,” “Categories,” etc.
3. **If It’s Not Up**:
   - Back in terminal: `sudo systemctl status rfid_dash`
   - Should say “active (running).” If not, yell for help—show this to someone smarter.

## What It Does
- Starts automatically when the Pi boots.
- Restarts if it crashes—keeps running 24/7.
- Updates itself from GitHub on reboot—keeps the app fresh (your config.py stays safe).

## Troubleshooting
- **No Webpage?**:
   - Check `http://<pi-ip>:8101` again—typo?
   - `sudo systemctl status rfid_dash`—if “failed,” look at `/var/log/rfid_dash.log` (`cat /var/log/rfid_dash.log`).
- **Still Stuck?**:
   - Ask the boss ([Your Name])—they built this shit.

Done! You’re tracking inventory like a pro now—don’t fuck it up!