#!/usr/bin/env python3
"""
SRA Robot — Debug Monitor (debug_monitor.py)
=============================================
Runs as a background daemon on the Pi 5 alongside the robot brain.
Watches for crashes, logs errors, auto-restarts the brain, and alerts
via Telegram debug bot.

Usage:
    # Start as background service
    python3 debug_monitor.py &

    # Or via systemd (recommended for Pi 5)
    sudo systemctl enable sra-debug-monitor
    sudo systemctl start sra-debug-monitor
"""

import os
import sys
import time
import json
import subprocess
import signal
from datetime import datetime
from pathlib import Path

# ─── Config ───
ROBOT_BRAIN_SCRIPT = os.path.expanduser("~/ai-robot/robot_brain.py")
LOG_DIR = os.path.expanduser("~/ai-robot/logs")
LOG_FILE = os.path.join(LOG_DIR, "debug_monitor.log")
BRAIN_LOG_FILE = os.path.join(LOG_DIR, "robot_brain.log")
CRASH_LOG_FILE = os.path.join(LOG_DIR, "crashes.json")
HEALTH_CHECK_INTERVAL = 10  # seconds between health checks
MAX_RESTARTS_PER_HOUR = 5   # prevent restart loops
RESTART_COOLDOWN = 60       # seconds between restarts
TELEGRAM_DEBUG_BOT_TOKEN = ""  # Set via env var or config
ALERT_CHAT_ID = ""  # Your Telegram chat ID

# ─── State ───
restart_times = []
last_heartbeat = time.time()
brain_process = None

class DebugLogger:
    """Structured logging for the debug monitor."""

    def __init__(self, log_file):
        self.log_file = log_file
        os.makedirs(os.path.dirname(log_file), exist_ok=True)

    def log(self, level, message, data=None):
        """Log a structured entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        }
        if data:
            entry["data"] = data

        # Write to file
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Also print to stderr
        print(f"[{level}] {message}", file=sys.stderr)

    def info(self, msg, data=None):
        self.log("INFO", msg, data)

    def warn(self, msg, data=None):
        self.log("WARN", msg, data)

    def error(self, msg, data=None):
        self.log("ERROR", msg, data)

    def critical(self, msg, data=None):
        self.log("CRITICAL", msg, data)


logger = DebugLogger(LOG_FILE)


def send_telegram_alert(message):
    """Send alert to Telegram debug bot."""
    token = os.environ.get("SRA_DEBUG_BOT_TOKEN", TELEGRAM_DEBUG_BOT_TOKEN)
    chat_id = os.environ.get("SRA_ALERT_CHAT_ID", ALERT_CHAT_ID)

    if not token or not chat_id:
        logger.warn("Telegram alert skipped — no bot token or chat ID configured")
        return

    try:
        subprocess.run(
            ["curl", "-s", "-X", "POST",
             f"https://api.telegram.org/bot{token}/sendMessage",
             "-d", f"chat_id={chat_id}",
             "-d", f"text={message}",
             "-d", "parse_mode=Markdown"],
            capture_output=True, timeout=10
        )
        logger.info(f"Telegram alert sent: {message[:50]}...")
    except Exception as e:
        logger.error(f"Failed to send Telegram alert: {e}")


def record_crash(reason, error_output=""):
    """Record a crash event."""
    crash_entry = {
        "timestamp": datetime.now().isoformat(),
        "reason": reason,
        "error_output": error_output[-500:] if error_output else "",
        "restart_count": len(restart_times),
    }

    # Append to crash log
    crashes = []
    if os.path.exists(CRASH_LOG_FILE):
        try:
            with open(CRASH_LOG_FILE) as f:
                crashes = json.load(f)
        except (json.JSONDecodeError, IOError):
            crashes = []

    crashes.append(crash_entry)

    # Keep last 100 crashes
    crashes = crashes[-100:]

    with open(CRASH_LOG_FILE, "w") as f:
        json.dump(crashes, f, indent=2)

    logger.critical(f"Crash recorded: {reason}", crash_entry)
    send_telegram_alert(f"🚨 *SRA Robot Crash*\nReason: {reason}\nTime: {crash_entry['timestamp']}")


def start_brain():
    """Start the robot brain process."""
    global brain_process

    logger.info("Starting robot brain...")

    try:
        brain_process = subprocess.Popen(
            [sys.executable, ROBOT_BRAIN_SCRIPT],
            stdout=open(BRAIN_LOG_FILE, "a"),
            stderr=subprocess.STDOUT,
            cwd=os.path.dirname(ROBOT_BRAIN_SCRIPT),
        )
        logger.info(f"Robot brain started (PID: {brain_process.pid})")
        send_telegram_alert("🟢 SRA Robot brain started")
        return True
    except Exception as e:
        logger.error(f"Failed to start robot brain: {e}")
        send_telegram_alert(f"🔴 Failed to start robot brain: {e}")
        return False


def stop_brain():
    """Stop the robot brain process."""
    global brain_process

    if brain_process and brain_process.poll() is None:
        logger.info("Stopping robot brain...")
        brain_process.terminate()
        try:
            brain_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            brain_process.kill()
            logger.warn("Robot brain force-killed")
        logger.info("Robot brain stopped")

    brain_process = None


def restart_brain(reason="automatic restart"):
    """Restart the robot brain with crash protection."""
    global restart_times

    now = time.time()

    # Clean old restart times (older than 1 hour)
    restart_times = [t for t in restart_times if now - t < 3600]

    # Check restart limit
    if len(restart_times) >= MAX_RESTARTS_PER_HOUR:
        logger.critical(f"Max restarts ({MAX_RESTARTS_PER_HOUR}/hour) reached — stopping")
        send_telegram_alert(f"🔴 SRA Robot: Max restarts reached ({MAX_RESTARTS_PER_HOUR}/hr). Manual intervention needed.")
        return False

    # Cooldown
    if restart_times and now - restart_times[-1] < RESTART_COOLDOWN:
        wait = RESTART_COOLDOWN - (now - restart_times[-1])
        logger.warn(f"Cooldown: waiting {wait:.0f}s before restart")
        time.sleep(wait)

    restart_times.append(now)
    stop_brain()
    time.sleep(2)
    return start_brain()


def check_brain_health():
    """Check if the robot brain is healthy."""
    global brain_process

    if brain_process is None:
        return False, "process not started"

    poll = brain_process.poll()
    if poll is not None:
        # Process has exited
        return False, f"process exited with code {poll}"

    # Check CPU/memory via /proc (Pi 5 Linux)
    try:
        with open(f"/proc/{brain_process.pid}/status") as f:
            status = f.read()
        # Check if process is a zombie
        if "Z" in status.split("\n")[0]:
            return False, "process is zombie"
    except (IOError, FileNotFoundError):
        return False, "process disappeared"

    return True, "healthy"


def check_system_health():
    """Check Pi 5 system health."""
    checks = {}

    # CPU temperature (Pi 5)
    try:
        with open("/sys/class/thermal/thermal_zone0/temp") as f:
            temp = int(f.read().strip()) / 1000.0
            checks["cpu_temp_c"] = temp
            if temp > 85:
                checks["cpu_warning"] = "OVERHEATING"
    except (IOError, FileNotFoundError):
        pass

    # Memory
    try:
        with open("/proc/meminfo") as f:
            meminfo = f.read()
        for line in meminfo.split("\n"):
            if line.startswith("MemAvailable:"):
                mem_kb = int(line.split()[1])
                checks["mem_available_mb"] = mem_kb // 1024
                if checks["mem_available_mb"] < 200:
                    checks["mem_warning"] = "LOW MEMORY"
    except (IOError, FileNotFoundError):
        pass

    # Disk space
    try:
        result = subprocess.run(["df", "/"], capture_output=True, text=True, timeout=5)
        lines = result.stdout.split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            checks["disk_used_pct"] = parts[4].rstrip("%")
    except Exception:
        pass

    # Battery (PiDog battery level — if accessible)
    # TODO: Add PiDog battery check via PiDog library

    return checks


def health_report():
    """Generate a full health report."""
    brain_ok, brain_msg = check_brain_health()
    system = check_system_health()

    report = {
        "timestamp": datetime.now().isoformat(),
        "brain": {"healthy": brain_ok, "message": brain_msg, "pid": brain_process.pid if brain_process else None},
        "system": system,
        "restarts_this_hour": len([t for t in restart_times if time.time() - t < 3600]),
    }
    return report


def handle_signal(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum} — shutting down debug monitor")
    stop_brain()
    send_telegram_alert("🟡 SRA Robot debug monitor shutting down")
    sys.exit(0)


def main():
    """Main debug monitor loop."""
    os.makedirs(LOG_DIR, exist_ok=True)

    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info("=" * 50)
    logger.info("SRA Robot Debug Monitor starting")
    logger.info(f"Brain script: {ROBOT_BRAIN_SCRIPT}")
    logger.info(f"Log dir: {LOG_DIR}")
    logger.info(f"Health check interval: {HEALTH_CHECK_INTERVAL}s")
    logger.info("=" * 50)

    # Start the brain
    if not start_brain():
        logger.critical("Failed to start brain on initial boot — exiting")
        sys.exit(1)

    # Main monitoring loop
    health_check_count = 0
    last_health_alert = 0

    while True:
        try:
            time.sleep(HEALTH_CHECK_INTERVAL)
            health_check_count += 1

            # Check brain health
            brain_ok, brain_msg = check_brain_health()

            if not brain_ok:
                # Brain crashed — record and restart
                error_output = ""
                try:
                    if brain_process:
                        error_output = brain_process.stdout.read() if brain_process.stdout else ""
                except Exception:
                    pass

                record_crash(brain_msg, error_output)

                # Attempt restart
                if not restart_brain(f"brain {brain_msg}"):
                    logger.critical("Restart failed — entering safe mode")
                    send_telegram_alert("🔴 SRA Robot: Restart failed. Entering safe mode. Manual fix needed.")
                    break
                continue

            # Periodic health check (every 6 cycles = ~60 seconds)
            if health_check_count % 6 == 0:
                report = health_report()

                # Alert on system issues
                system = report.get("system", {})
                now = time.time()

                if system.get("cpu_warning") == "OVERHEATING" and now - last_health_alert > 300:
                    temp = system.get("cpu_temp_c", "?")
                    send_telegram_alert(f"⚠️ SRA Robot: CPU overheating ({temp}°C)")
                    last_health_alert = now

                if system.get("mem_warning") == "LOW MEMORY" and now - last_health_alert > 300:
                    mem = system.get("mem_available_mb", "?")
                    send_telegram_alert(f"⚠️ SRA Robot: Low memory ({mem}MB available)")
                    last_health_alert = now

                # Log health status
                logger.info(f"Health OK — brain: {brain_msg}, temp: {system.get('cpu_temp_c', 'N/A')}°C, "
                           f"mem: {system.get('mem_available_mb', 'N/A')}MB, "
                           f"restarts: {report['restarts_this_hour']}")

        except Exception as e:
            logger.error(f"Debug monitor error: {e}")
            time.sleep(5)


if __name__ == "__main__":
    main()