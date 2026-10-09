# SRA Robot — Systemd Service Files
# ===================================
# These files make the robot brain and debug monitor run as
# system services on the Pi 5 — they start automatically on boot
# and restart on crash.

# ─── 1. Robot Brain Service ───
# File: /etc/systemd/system/sra-robot-brain.service
# Install: sudo cp sra-robot-brain.service /etc/systemd/system/
#          sudo systemctl enable sra-robot-brain
#          sudo systemctl start sra-robot-brain

"""
[Unit]
Description=SRA Robot Dog — Brain Service
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ai-robot
ExecStart=/usr/bin/python3 /home/pi/ai-robot/robot_brain.py
Restart=on-failure
RestartSec=10
StandardOutput=append:/home/pi/ai-robot/logs/robot_brain.log
StandardError=append:/home/pi/ai-robot/logs/robot_brain.log
Environment=SRA_DEBUG_BOT_TOKEN=${SRA_DEBUG_BOT_TOKEN}
Environment=SRA_ALERT_CHAT_ID=${SRA_ALERT_CHAT_ID}

[Install]
WantedBy=multi-user.target
"""

# ─── 2. Debug Monitor Service ───
# File: /etc/systemd/system/sra-debug-monitor.service
# Install: sudo cp sra-debug-monitor.service /etc/systemd/system/
#          sudo systemctl enable sra-debug-monitor
#          sudo systemctl start sra-debug-monitor

"""
[Unit]
Description=SRA Robot Dog — Debug Monitor
After=network-online.target sra-robot-brain.service
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ai-robot
ExecStart=/usr/bin/python3 /home/pi/ai-robot/debug_monitor.py
Restart=always
RestartSec=15
StandardOutput=append:/home/pi/ai-robot/logs/debug_monitor.log
StandardError=append:/home/pi/ai-robot/logs/debug_monitor.log
Environment=SRA_DEBUG_BOT_TOKEN=${SRA_DEBUG_BOT_TOKEN}
Environment=SRA_ALERT_CHAT_ID=${SRA_ALERT_CHAT_ID}

[Install]
WantedBy=multi-user.target
"""

# ─── 3. Debug Telegram Bot Service ───
# File: /etc/systemd/system/sra-debug-bot.service

"""
[Unit]
Description=SRA Robot Dog — Debug Telegram Bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/ai-robot
ExecStart=/usr/bin/python3 /home/pi/ai-robot/debug_bot.py
Restart=always
RestartSec=15
StandardOutput=append:/home/pi/ai-robot/logs/debug_bot.log
StandardError=append:/home/pi/ai-robot/logs/debug_bot.log
EnvironmentFile=/home/pi/ai-robot/.env

[Install]
WantedBy=multi-user.target
"""

# ─── 4. Environment file ───
# File: /home/pi/ai-robot/.env
# Fill in your tokens

"""
# Telegram debug bot token (from @BotFather)
SRA_DEBUG_BOT_TOKEN=your_debug_bot_token_here

# Your Telegram chat ID (message @userinfobot to get it)
SRA_ALERT_CHAT_ID=your_chat_id_here

# Hermes LLM config (same as Mac mini)
OLLAMA_API_KEY=your_ollama_key_here
OLLAMA_BASE_URL=https://ollama.com/v1
"""