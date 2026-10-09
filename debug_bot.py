#!/usr/bin/env python3
"""
SRA Robot — Telegram Debug Bot (debug_bot.py)
=============================================
A lightweight Telegram bot that runs on the Pi 5 alongside the robot.
Sends alerts when the robot crashes, and accepts debug commands.

Commands (sent to your debug bot):
    /status   — Full health report
    /restart  — Restart the robot brain
    /stop     — Stop the robot brain
    /logs     — Show recent logs (last 20 lines)
    /crashes  — Show recent crashes
    /health   — System health (CPU temp, memory, disk)
    /tail     — Live tail of brain output

Usage:
    python3 debug_bot.py

Env vars:
    SRA_DEBUG_BOT_TOKEN — Telegram bot token from @BotFather
    SRA_ALERT_CHAT_ID   — Your Telegram chat ID (for alerts)
"""

import os
import sys
import json
import time
import subprocess
import threading
from datetime import datetime
from pathlib import Path

try:
    import telebot
except ImportError:
    print("❌ python-telegram-bot not installed")
    print("Install: pip3 install pyTelegramBotAPI")
    sys.exit(1)

# ─── Config ───
BOT_TOKEN = os.environ.get("SRA_DEBUG_BOT_TOKEN", "")
ALERT_CHAT_ID = os.environ.get("SRA_ALERT_CHAT_ID", "")
LOG_DIR = os.path.expanduser("~/ai-robot/logs")
BRAIN_LOG = os.path.join(LOG_DIR, "robot_brain.log")
CRASH_LOG = os.path.join(LOG_DIR, "crashes.json")
MONITOR_LOG = os.path.join(LOG_DIR, "debug_monitor.log")

if not BOT_TOKEN:
    print("❌ Set SRA_DEBUG_BOT_TOKEN environment variable")
    print("Get a token from @BotFather on Telegram")
    sys.exit(1)

bot = telebot.TeleBot(BOT_TOKEN)


def get_system_health():
    """Get Pi 5 system health."""
    health = {"timestamp": datetime.now().isoformat()}

    # CPU temp
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            health["cpu_temp_c"] = int(f.read().strip()) / 1000.0
    except (IOError, FileNotFoundError):
        health["cpu_temp_c"] = "N/A"

    # Memory
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    health["mem_available_mb"] = int(line.split()[1]) // 1024
                elif line.startswith("MemTotal:"):
                    health["mem_total_mb"] = int(line.split()[1]) // 1024
    except (IOError, FileNotFoundError):
        pass

    # Disk
    try:
        result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.strip().split("\n")
        if len(lines) > 1:
            health["disk"] = lines[1]
    except Exception:
        pass

    # Uptime
    try:
        with open("/proc/uptime") as f:
            uptime_seconds = float(f.read().split()[0])
            hours = int(uptime_seconds // 3600)
            mins = int((uptime_seconds % 3600) // 60)
            health["uptime"] = f"{hours}h {mins}m"
    except (IOError, FileNotFoundError):
        pass

    # Brain process status
    try:
        result = subprocess.run(["pgrep", "-f", "robot_brain.py"], capture_output=True, text=True)
        pids = result.stdout.strip().split("\n")
        health["brain_running"] = bool(pids and pids[0])
        health["brain_pid"] = pids[0] if health["brain_running"] else None
    except Exception:
        health["brain_running"] = False

    return health


def read_log_tail(log_file, lines=20):
    """Read the last N lines of a log file."""
    if not os.path.exists(log_file):
        return f"Log file not found: {log_file}"

    try:
        with open(log_file) as f:
            all_lines = f.readlines()
        return "".join(all_lines[-lines:])
    except IOError as e:
        return f"Error reading log: {e}"


def read_crashes(count=5):
    """Read recent crash entries."""
    if not os.path.exists(CRASH_LOG):
        return "No crashes recorded 🎉"

    try:
        with open(CRASH_LOG) as f:
            crashes = json.load(f)

        if not crashes:
            return "No crashes recorded 🎉"

        recent = crashes[-count:]
        output = []
        for c in reversed(recent):
            output.append(f"🕐 {c['timestamp']}\n   Reason: {c['reason']}\n   Restarts: {c['restart_count']}")

        return "\n\n".join(output)
    except (json.JSONDecodeError, IOError) as e:
        return f"Error reading crashes: {e}"


# ─── Bot Commands ───

@bot.message_handler(commands=['start', 'help'])
def cmd_help(message):
    bot.reply_to(message, """🤖 *SRA Robot Debug Bot*

Commands:
/status   — Full health report
/health   — System health (CPU, memory, disk)
/restart  — Restart the robot brain
/stop     — Stop the robot brain
/logs     — Recent brain logs (last 20 lines)
/crashes  — Recent crash history
/tail     — Live brain output (30 lines)
/help     — This message

Alerts are sent automatically when the robot crashes or system issues occur.
""", parse_mode="Markdown")


@bot.message_handler(commands=['status'])
def cmd_status(message):
    health = get_system_health()

    status_emoji = "🟢" if health.get("brain_running") else "🔴"

    report = f"""{status_emoji} *SRA Robot Status*

*Brain:* {'Running (PID ' + health.get('brain_pid', '?') + ')' if health.get('brain_running') else 'Stopped'}
*CPU Temp:* {health.get('cpu_temp_c', 'N/A')}°C
*Memory:* {health.get('mem_available_mb', '?')}MB / {health.get('mem_total_mb', '?')}MB
*Uptime:* {health.get('uptime', 'N/A')}
*Disk:*
`{health.get('disk', 'N/A')}`
*Time:* {health.get('timestamp', 'N/A')}"""

    bot.reply_to(message, report, parse_mode="Markdown")


@bot.message_handler(commands=['health'])
def cmd_health(message):
    health = get_system_health()

    temp = health.get("cpu_temp_c", 0)
    temp_emoji = "🟢" if isinstance(temp, (int, float)) and temp < 70 else "🟡" if isinstance(temp, (int, float)) and temp < 85 else "🔴"

    mem = health.get("mem_available_mb", 0)
    mem_emoji = "🟢" if isinstance(mem, (int, float)) and mem > 500 else "🟡" if isinstance(mem, (int, float)) and mem > 200 else "🔴"

    report = f"""🏥 *System Health*

{temp_emoji} *CPU Temperature:* {temp}°C
{mem_emoji} *Memory Available:* {mem}MB / {health.get('mem_total_mb', '?')}MB
⏱ *Uptime:* {health.get('uptime', 'N/A')}
💾 *Disk:*
`{health.get('disk', 'N/A')}`"""

    bot.reply_to(message, report, parse_mode="Markdown")


@bot.message_handler(commands=['restart'])
def cmd_restart(message):
    bot.reply_to(message, "🔄 Restarting robot brain...")

    # Kill existing brain process
    try:
        subprocess.run(["pkill", "-f", "robot_brain.py"], capture_output=True, timeout=5)
        time.sleep(2)

        # Start new brain process
        brain_script = os.path.expanduser("~/ai-robot/robot_brain.py")
        subprocess.Popen(
            [sys.executable, brain_script],
            stdout=open(BRAIN_LOG, "a"),
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(brain_script),
        )
        time.sleep(3)

        # Check if it started
        result = subprocess.run(["pgrep", "-f", "robot_brain.py"], capture_output=True, text=True)
        if result.stdout.strip():
            bot.reply_to(message, "✅ Robot brain restarted successfully!")
        else:
            bot.reply_to(message, "❌ Robot brain failed to start. Check /logs")
    except Exception as e:
        bot.reply_to(message, f"❌ Restart error: {e}")


@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    bot.reply_to(message, "🛑 Stopping robot brain...")

    try:
        subprocess.run(["pkill", "-f", "robot_brain.py"], capture_output=True, timeout=5)
        time.sleep(2)

        result = subprocess.run(["pgrep", "-f", "robot_brain.py"], capture_output=True, text=True)
        if not result.stdout.strip():
            bot.reply_to(message, "✅ Robot brain stopped.")
        else:
            bot.reply_to(message, "⚠️ Brain still running — try /restart")
    except Exception as e:
        bot.reply_to(message, f"❌ Stop error: {e}")


@bot.message_handler(commands=['logs'])
def cmd_logs(message):
    logs = read_log_tail(BRAIN_LOG, 20)
    if len(logs) > 4000:
        logs = logs[-4000:]
    bot.reply_to(message, f"📋 *Recent Brain Logs:*\n```\n{logs}\n```", parse_mode="Markdown")


@bot.message_handler(commands=['crashes'])
def cmd_crashes(message):
    crashes = read_crashes(5)
    bot.reply_to(message, f"💥 *Recent Crashes:*\n\n{crashes}", parse_mode="Markdown")


@bot.message_handler(commands=['tail'])
def cmd_tail(message):
    logs = read_log_tail(BRAIN_LOG, 30)
    if len(logs) > 4000:
        logs = logs[-4000:]
    bot.reply_to(message, f"📊 *Brain Output (last 30 lines):*\n```\n{logs}\n```", parse_mode="Markdown")


# ─── Alert Sender ───
def send_alert(text):
    """Send an alert message to the configured chat."""
    if ALERT_CHAT_ID:
        try:
            bot.send_message(ALERT_CHAT_ID, text, parse_mode="Markdown")
        except Exception as e:
            print(f"Alert send error: {e}", file=sys.stderr)


# ─── Main ───
def main():
    os.makedirs(LOG_DIR, exist_ok=True)

    print(f"""
╔══════════════════════════════════════════╗
║   🤖 SRA Robot Debug Bot                 ║
║   Telegram: your debug bot handle          ║
╚══════════════════════════════════════════╝
    """)

    print(f"Bot token: {'✅ configured' if BOT_TOKEN else '❌ missing'}")
    print(f"Alert chat: {'✅ configured' if ALERT_CHAT_ID else '❌ missing'}")
    print(f"Log dir: {LOG_DIR}")
    print()

    if not ALERT_CHAT_ID:
        print("⚠️  SRA_ALERT_CHAT_ID not set — alerts will not be sent")
        print("   Get your chat ID by messaging @userinfobot on Telegram")
        print()

    print("Starting debug bot... (Ctrl+C to stop)")

    try:
        bot.infinity_polling(timeout=30, long_polling_timeout=20)
    except KeyboardInterrupt:
        print("\n👋 Debug bot shutting down...")
    except Exception as e:
        print(f"❌ Bot error: {e}")
        send_alert(f"🔴 SRA Debug Bot crashed: {e}")


if __name__ == "__main__":
    main()