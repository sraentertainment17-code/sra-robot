#!/usr/bin/env bash
# ============================================================
# SRA Robot — Pi 5 Setup Script (install.sh)
# ============================================================
# Run this ON the Raspberry Pi 5 after flashing Pi OS.
# Installs everything the robot needs.
#
# Usage:
#   chmod +x install.sh
#   ./install.sh
# ============================================================

set -e

echo "╔══════════════════════════════════════════╗"
echo "║   🤖 SRA ROBOT — Pi 5 SETUP              ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# --- Update system ---
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# --- Audio dependencies ---
echo "🔊 Installing audio dependencies..."
sudo apt install -y portaudio19-dev python3-pyaudio ffmpeg sox alsa-utils

# --- Camera dependencies ---
echo "📷 Installing camera dependencies..."
sudo apt install -y libcamera-apps python3-libcamera

# --- OpenCV (for face detection) ---
echo "👁️ Installing OpenCV..."
sudo apt install -y python3-opencv

# --- GPIO (for motor control) ---
echo "⚙️ Installing GPIO library..."
sudo apt install -y python3-rpi.gpio

# --- Python packages ---
echo "🐍 Installing Python packages..."
pip3 install --user openai-whisper sounddevice numpy edge-tts

# --- Hermes Agent ---
echo "🧠 Installing Hermes Agent..."
# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Installing Node.js..."
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt install -y nodejs
fi

# Install Hermes
if [ ! -d "$HOME/.hermes" ]; then
    echo "Installing Hermes Agent..."
    curl -fsSL https://hermes-agent.nousresearch.com/install | bash
else
    echo "✅ Hermes already installed"
fi

# --- Copy robot files ---
echo "📁 Setting up robot directory..."
mkdir -p ~/ai-robot/captures

# Copy config from Mac mini if available (will be done manually or via SCP)
echo ""
echo "📝 Next steps:"
echo "   1. Copy your Hermes config to Pi 5:"
echo "      scp ~/.hermes/config.yaml pi@robot.local:~/.hermes/config.yaml"
echo ""
echo "   2. Copy the robot code:"
echo "      scp -r ~/ai-robot/ pi@robot.local:~/ai-robot/"
echo ""
echo "   3. On the Pi 5, test motors:"
echo "      cd ~/ai-robot && python3 motors.py"
echo ""
echo "   4. Test vision:"
echo "      cd ~/ai-robot && python3 vision.py"
echo ""
echo "   5. Run the full robot brain:"
echo "      cd ~/ai-robot && python3 robot_brain.py"
echo ""

echo "✅ Setup complete!"
echo "🤖 Your robot is ready to come alive."