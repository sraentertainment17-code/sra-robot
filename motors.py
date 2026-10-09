#!/usr/bin/env python3
"""
SRA Robot — Motor Control (motors.py)
=====================================
Controls 4 DC motors via L298N motor driver on Raspberry Pi 5.
Left motors (front + rear) wired to L298N Output A.
Right motors (front + rear) wired to L298N Output B.

Usage:
    from motors import RobotMotors
    robot = RobotMotors()
    robot.forward(speed=50, duration=2.0)   # forward at 50% for 2 seconds
    robot.turn_left(speed=40, duration=1.0)
    robot.stop()
    robot.cleanup()

Or run directly to test:
    python3 motors.py
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
    ON_PI = True
except ImportError:
    print("⚠️ RPi.GPIO not found — running in SIMULATION mode (no hardware)")
    ON_PI = False


class RobotMotors:
    """Controls 4-wheel DC motor robot via L298N motor driver."""

    # GPIO pin assignments (BCM numbering)
    ENA = 12   # Left motor speed (PWM)
    IN1 = 17   # Left forward
    IN2 = 27   # Left reverse
    IN3 = 22   # Right forward
    IN4 = 23   # Right reverse
    ENB = 13   # Right motor speed (PWM)

    def __init__(self):
        if ON_PI:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in [self.ENA, self.IN1, self.IN2, self.IN3, self.IN4, self.ENB]:
                GPIO.setup(pin, GPIO.OUT)

            # PWM for speed control: 1000 Hz frequency
            self.pwm_left = GPIO.PWM(self.ENA, 1000)
            self.pwm_right = GPIO.PWM(self.ENB, 1000)
            self.pwm_left.start(0)
            self.pwm_right.start(0)

        print("⚙️  Motor controller ready" + (" (SIMULATION)" if not ON_PI else ""))

    def _set_left(self, forward=True, speed=50):
        """Drive left motors forward or reverse at given speed (0-100)."""
        if ON_PI:
            GPIO.output(self.IN1, forward)
            GPIO.output(self.IN2, not forward)
            self.pwm_left.ChangeDutyCycle(speed)
        else:
            direction = "FWD" if forward else "REV"
            print(f"   LEFT  {direction} @ {speed}%")

    def _set_right(self, forward=True, speed=50):
        """Drive right motors forward or reverse at given speed (0-100)."""
        if ON_PI:
            GPIO.output(self.IN3, forward)
            GPIO.output(self.IN4, not forward)
            self.pwm_right.ChangeDutyCycle(speed)
        else:
            direction = "FWD" if forward else "REV"
            print(f"   RIGHT {direction} @ {speed}%")

    def forward(self, speed=50, duration=1.0):
        """Move forward at given speed for given duration (seconds)."""
        self._set_left(True, speed)
        self._set_right(True, speed)
        if not ON_PI:
            print(f"➡️  FORWARD @ {speed}% for {duration}s")
        time.sleep(duration)
        self.stop()

    def backward(self, speed=50, duration=1.0):
        """Move backward."""
        self._set_left(False, speed)
        self._set_right(False, speed)
        if not ON_PI:
            print(f"⬅️  BACKWARD @ {speed}% for {duration}s")
        time.sleep(duration)
        self.stop()

    def turn_left(self, speed=50, duration=0.5):
        """Turn left (right wheels forward, left wheels reverse)."""
        self._set_left(False, speed)
        self._set_right(True, speed)
        if not ON_PI:
            print(f"↪️  TURN LEFT @ {speed}% for {duration}s")
        time.sleep(duration)
        self.stop()

    def turn_right(self, speed=50, duration=0.5):
        """Turn right (left wheels forward, right wheels reverse)."""
        self._set_left(True, speed)
        self._set_right(False, speed)
        if not ON_PI:
            print(f"↩️  TURN RIGHT @ {speed}% for {duration}s")
        time.sleep(duration)
        self.stop()

    def stop(self):
        """Stop all motors."""
        if ON_PI:
            self.pwm_left.ChangeDutyCycle(0)
            self.pwm_right.ChangeDutyCycle(0)
            GPIO.output(self.IN1, False)
            GPIO.output(self.IN2, False)
            GPIO.output(self.IN3, False)
            GPIO.output(self.IN4, False)
        else:
            print("🛑 STOP")

    def cleanup(self):
        """Clean up GPIO on shutdown."""
        self.stop()
        if ON_PI:
            self.pwm_left.stop()
            self.pwm_right.stop()
            GPIO.cleanup()
        print("⚙️  Motor controller shut down")


# --- Command parser: convert text to motor actions ---
def parse_movement_command(text):
    """Parse natural language movement commands.
    Returns (action, speed, duration) or None.
    """
    text = text.lower().strip()

    # Speed detection
    speed = 50  # default
    if "fast" in text or "quick" in text:
        speed = 80
    if "slow" in text:
        speed = 30

    # Duration detection
    duration = 1.0  # default
    import re
    time_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:second|sec|s)\b', text)
    if time_match:
        duration = float(time_match.group(1))

    # Action detection
    if any(w in text for w in ["forward", "ahead", "go", "straight", "move forward"]):
        return ("forward", speed, duration)
    elif any(w in text for w in ["backward", "back", "reverse", "back up"]):
        return ("backward", speed, duration)
    elif any(w in text for w in ["left", "turn left"]):
        return ("turn_left", speed, duration)
    elif any(w in text for w in ["right", "turn right"]):
        return ("turn_right", speed, duration)
    elif any(w in text for w in ["stop", "halt", "brake"]):
        return ("stop", 0, 0)
    else:
        return None


# --- Test mode ---
if __name__ == "__main__":
    print("""
╔══════════════════════════════════════════╗
║   ⚙️  SRA ROBOT MOTOR TEST               ║
╚══════════════════════════════════════════╝
    """)

    robot = RobotMotors()

    try:
        print("Test 1: Forward 2 seconds...")
        robot.forward(speed=50, duration=2.0)

        time.sleep(0.5)

        print("Test 2: Turn right 1 second...")
        robot.turn_right(speed=50, duration=1.0)

        time.sleep(0.5)

        print("Test 3: Turn left 1 second...")
        robot.turn_left(speed=50, duration=1.0)

        time.sleep(0.5)

        print("Test 4: Backward 2 seconds...")
        robot.backward(speed=50, duration=2.0)

        print("\n✅ All motor tests passed!")

    except KeyboardInterrupt:
        print("\nInterrupted")
    finally:
        robot.cleanup()