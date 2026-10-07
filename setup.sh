#!/bin/bash

echo "=================================================="
echo "       COMPLETE ENVIRONMENT & DEPENDENCY SETUP    "
echo "=================================================="

# 1. Terminate stale processes and free ports
echo "[1/6] Cleaning up old processes..."
pkill -9 -f "Xvfb|x11vnc|websockify|novnc" || true
fuser -k 8080/tcp 5900/tcp || true

# 2. Update System Packages & Install GUI + Chromium System Libraries
echo "[2/6] Installing System APT packages..."
sudo apt-get update -y
sudo apt-get install -y \
    xvfb \
    x11vnc \
    novnc \
    python3-pip \
    python3-venv \
    python3-websockify \
    curl \
    git \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0

# 3. Upgrade Pip & Install Python Requirements
echo "[3/6] Installing Python packages..."
python3 -m pip install --upgrade pip
pip install playwright requests

# 4. Install Playwright Chromium Binary & OS Dependencies
echo "[4/6] Installing Chromium and Playwright OS dependencies..."
playwright install chromium
playwright install-deps chromium || true

# 5. Prepare Workspace Ephemeral Directories
echo "[5/6] Preparing /tmp working folders..."
mkdir -p /tmp/downloads /tmp/extracted /tmp/chrome_session

# 6. Configure default landing page for noVNC
echo "[6/6] Setting default noVNC landing page..."
sudo ln -sf /usr/share/novnc/vnc.html /usr/share/novnc/index.html

# 7. Launch Display Stack
echo "🖥️  Launching Virtual Display (:99) and Web Proxy (8080)..."
export DISPLAY=:99
Xvfb :99 -screen 0 1280x1024x24 &
sleep 1

x11vnc -display :99 -forever -nopw -shared -bg
sleep 1

python3 -m websockify --web /usr/share/novnc 8080 localhost:5900 &
sleep 2

echo "=================================================="
echo "  ALL PACKAGES INSTALLED & ENVIRONMENT READY!"
echo "  • Virtual Display  : :99"
echo "  • Web Preview Port : 8080"
echo "  • Chromium Browser : Installed"
echo "  • Output Folders   : /tmp/downloads, /tmp/extracted"
echo "=================================================="
