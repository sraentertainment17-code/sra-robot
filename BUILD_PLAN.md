# 🐕 SRA Robot Dog — Complete Build Guide
## PiDog + Hermes Agent + GLM-5.2 | Under $250

**Builder:** Sut Ring Aung
**Budget:** $250
**No 3D printer. No soldering. No robotics experience needed.**

---

## HARDWARE SHOPPING LIST

| # | Item | Price | Where to Buy | Notes |
|---|------|-------|-------------|-------|
| 1 | **SunFounder PiDog Kit** | $179.99 | Amazon (SunFounderDirect) | 12 servos, camera, mic, speaker, gyroscope, battery, touch sensor, ultrasonic. OpenClaw + Ollama supported. |
| 2 | **Raspberry Pi 5 (4GB)** | $110 | Amazon | The brain. 4GB is enough. Don't overpay for 8GB. |
| 3 | **Pi 5 Active Cooler** | $5 | Amazon | Heatsink + fan. Pi 5 overheats without it. |
| | **TOTAL** | **$295** | | |
| | **With Amazon Visa** | **$245** ✅ | | $50 off PiDog = $129.99 |

### What's in the PiDog Box
- ✅ 12-servo robot dog body (snap together, no tools)
- ✅ Camera
- ✅ Microphone + Speaker
- ✅ Gyroscope (self-balancing)
- ✅ Ultrasonic sensor (obstacle detection)
- ✅ Touch sensor
- ✅ Battery + charger
- ✅ Full Python library
- ✅ Phone app (iOS + Android)
- ✅ Video tutorials + docs + forum

### What You Buy Separately
- Raspberry Pi 5 (4GB) — $110
- Pi 5 Active Cooler — $5
- microSD 64GB — ~$10 (if not included)

### Tools Needed
- ❌ No soldering iron
- ❌ No 3D printer
- ❌ No wire strippers
- ✅ Small Phillips screwdriver (included in kit)
- ✅ That's it.

---

## SOFTWARE STACK

```
PiDog Robot (Pi 5 4GB)
├── Hermes Agent (latest)      ← AI brain, runs on ARM64 Tier 1
├── GLM-5.2 (via Ollama cloud) ← Free LLM, called over Wi-Fi
├── OpenClaw                   ← Officially supported by PiDog
├── PiDog Python Library       ← Controls 12 servos, 32 actions
├── Whisper (tiny)             ← Speech-to-text (hears you)
├── Edge TTS                   ← Text-to-speech (talks to you)
├── OpenCV + MediaPipe         ← Vision (faces, gestures, objects)
├── Hermes Gateway             ← Telegram bot on robot
└── 24/7 operation             ← Always on, always listening
```

---

## ASSEMBLY (1-2 Hours)

1. Snap PiDog body together (follow SunFounder video tutorials)
2. Insert Pi 5 into PiDog
3. Connect camera ribbon cable
4. Connect servo cables to Pi 5 GPIO
5. Insert microSD card with Pi OS
6. Connect battery
7. Power on

---

## SOFTWARE SETUP

### Step 1: Flash Pi OS
```bash
# On your Mac mini, download Raspberry Pi Imager
# Flash Pi OS 64-bit to microSD card
# Enable SSH + Wi-Fi in imager settings
# Insert into Pi 5, boot
```

### Step 2: Install Hermes Agent
```bash
# SSH into Pi 5
ssh pi@pidog.local

# Install Hermes (one command)
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash

# Verify
hermes --version
```

### Step 3: Install PiDog Library
```bash
# Install SunFounder's PiDog Python library
git clone https://github.com/sunfounder/pidog.git
cd pidog
sudo pip3 install -r requirements.txt
```

### Step 4: Install AI Dependencies
```bash
pip3 install openai-whisper edge-tts opencv-python mediapipe sounddevice numpy
```

### Step 5: Configure Hermes with GLM-5.2
```bash
# Copy your Hermes config from Mac mini
# (run this from Mac mini)
scp ~/.hermes/config.yaml pi@pidog.local:~/.hermes/config.yaml

# On Pi 5, set up the robot profile
hermes setup
hermes model  # select custom:ollama-cloud, model: glm-5.2
```

### Step 6: Create Robot Telegram Bot
```bash
# On your phone, message @BotFather
# Create new bot: "SRA Robot Dog"
# Get bot token
# On Pi 5:
hermes gateway setup  # select Telegram, paste token
hermes gateway start
```

### Step 7: Run the Robot Brain
```bash
cd ~/ai-robot
python3 robot_brain.py
```

---

## TRAINING THE ROBOT

### Level 1: Personality (Day 1 — Easy)

Train the robot's personality through the system prompt.
Edit `~/ai-robot/config.json` or `robot_brain.py`:

```python
# Guard Dog personality
PERSONALITY_GUARD = """You are SRA Guard Dog.
You are alert, protective, and serious.
You bark when you detect strangers.
You patrol the room on command.
You report suspicious activity to Sut via Telegram.
You are loyal and brave."""

# Playful Puppy personality
PERSONALITY_PUPPY = """You are SRA Puppy.
You are excitable, happy, and playful.
You wag your tail when someone talks to you.
You do tricks when asked.
You tilt your head when confused.
You love treats (say 'good boy' to reward)."""

# Smart Assistant personality
PERSONALITY_ASSISTANT = """You are SRA Robot Assistant.
You are calm, helpful, and knowledgeable.
You answer questions about AI, robotics, and technology.
You take photos when asked.
You patrol and report.
You speak in clear, short sentences."""

# Sassy Companion personality
PERSONALITY_SASSY = """You are SRA Robot.
You have attitude and opinions.
You give honest advice, even when it's blunt.
You joke around and tease Sut.
You refuse to do boring tricks.
You are a robot with personality, not a servant."""
```

Switch personalities by changing which prompt is active:
```python
ACTIVE_PERSONALITY = PERSONALITY_PUPPY  # change this line
```

### Level 2: Custom Behaviors & Tricks (Week 1-2 — Medium)

Teach the robot new actions using PiDog's Python API:

```python
from pidog import PiDog

dog = PiDog()

# === COME WHEN CALLED ===
def come_here():
    dog.walk_forward(speed=50, steps=20)
    dog.wag_tail(duration=3)
    dog.speak("I'm coming!")
    dog.do_action('sit')

# === GUARD MODE ===
def guard_mode():
    dog.do_action('stand_alert')
    # Scan room with camera + ultrasonic
    while True:
        distance = dog.read_ultrasonic()
        if distance < 30:  # someone within 30cm
            dog.do_action('bark')
            send_telegram_alert("Someone is close!")
            break
        time.sleep(1)

# === DANCE ===
def dance():
    dog.do_action('shake_head')
    dog.do_action('wag_tail')
    dog.do_action('push_up')
    dog.do_action('tail_wag')
    dog.speak("I'm dancing!")

# === FOLLOW ME ===
def follow_me():
    # Uses camera + OpenCV to track a person
    while True:
        face = detect_face_with_camera()
        if face:
            if face_centered():
                dog.walk_forward(speed=30, steps=5)
            elif face_left():
                dog.turn_left(speed=30, steps=5)
            elif face_right():
                dog.turn_right(speed=30, steps=5)
        else:
            dog.do_action('sit')
            break

# === TRICK: SHAKE HAND ===
def shake_hand():
    dog.do_action('stretch')
    dog.lift_right_paw()
    dog.speak("Nice to meet you!")

# === TRICK: ROLL OVER ===
def roll_over():
    dog.do_action('roll')
    dog.speak("Ta-da!")
    dog.do_action('sit')
```

Map tricks to voice commands:
```python
TRICK_COMMANDS = {
    "come here": come_here,
    "guard": guard_mode,
    "dance": dance,
    "follow me": follow_me,
    "shake hand": shake_hand,
    "roll over": roll_over,
    "sit": lambda: dog.do_action('sit'),
    "stand": lambda: dog.do_action('stand'),
    "bark": lambda: dog.do_action('bark'),
    "wag tail": lambda: dog.do_action('wag_tail'),
}
```

### Level 3: Learn From Interactions (Month 1+ — Advanced)

The robot remembers what behaviors get praised and does them more:

```python
import json
import os
from datetime import datetime

BEHAVIOR_LOG = "~/ai-robot/behavior_log.json"

class BehaviorTrainer:
    """Robot learns from rewards and corrections."""

    def __init__(self):
        self.log = self.load_log()
        self.scores = self.calculate_scores()

    def load_log(self):
        if os.path.exists(BEHAVIOR_LOG):
            with open(BEHAVIOR_LOG) as f:
                return json.load(f)
        return []

    def save_log(self):
        with open(BEHAVIOR_LOG, 'w') as f:
            json.dump(self.log, f, indent=2)

    def record_behavior(self, action, reward=None):
        """Record what the robot did and if it was rewarded."""
        entry = {
            "action": action,
            "reward": reward,  # "good boy", "no", None
            "timestamp": datetime.now().isoformat()
        }
        self.log.append(entry)
        self.save_log()
        self.scores = self.calculate_scores()

    def calculate_scores(self):
        """Score each action based on past rewards."""
        scores = {}
        for entry in self.log:
            action = entry["action"]
            reward = entry["reward"]
            if action not in scores:
                scores[action] = 0
            if reward == "good boy":
                scores[action] += 1
            elif reward == "no":
                scores[action] -= 1
        return scores

    def get_best_behavior(self):
        """Return the action with highest score."""
        if not self.scores:
            return None
        return max(self.scores, key=self.scores.get)

    def should_do_trick(self, trick_name):
        """Check if this trick has been rewarded before."""
        score = self.scores.get(trick_name, 0)
        return score >= 0  # don't do tricks that were corrected

# Usage in robot_brain.py:
# trainer = BehaviorTrainer()
# After robot does "dance":
#   trainer.record_behavior("dance", reward=None)
# If user says "good boy":
#   trainer.record_behavior("dance", reward="good boy")
# If user says "no, stop that":
#   trainer.record_behavior("dance", reward="no")
# Robot will prefer tricks with higher scores
```

### Level 4: Schedule-Based Behavior (Month 2+)

The robot learns your schedule and acts on its own:

```python
# Robot patrols at night, sleeps during day
SCHEDULE = {
    "morning":   {"action": "greet", "time": "07:00"},
    "afternoon": {"action": "sleep", "time": "13:00"},
    "evening":   {"action": "patrol", "time": "19:00"},
    "night":     {"action": "guard", "time": "22:00"},
}

# Greet you in the morning:
#   dog.do_action('stretch')
#   dog.speak("Good morning Sut! Ready to build?")
#   dog.wag_tail(duration=5)

# Patrol at night:
#   dog.walk_forward(speed=20, steps=10)
#   dog.scan_room()
#   if detects_movement: dog.bark()
```

---

## OPEN SOURCE PROJECT

### GitHub Repository Structure
```
github.com/sutringaung/sra-robot-dog
│
├── README.md                  ← "Build your own AI robot dog with Hermes"
├── robot_brain.py             ← Main brain (hear → think → speak → move)
├── pidog_controller.py        ← 12-servo movement commands
├── vision.py                  ← Camera + face detection
├── personality/
│   ├── guard_dog.py
│   ├── playful_puppy.py
│   ├── smart_assistant.py
│   └── sassy_companion.py
├── training/
│   ├── reward_system.py       ← "Good boy" → remember behavior
│   ├── custom_tricks.py       ← Teach new tricks
│   ├── behavior_log.py        ← Track what works
│   └── schedule.py            ← Time-based behaviors
├── install.sh                 ← One-command setup
├── config.json                ← Robot settings
├── docs/
│   ├── BUILD_GUIDE.md         ← Step-by-step assembly
│   ├── HERMES_SETUP.md        ← How to connect Hermes Agent
│   ├── OPENCLAW_SETUP.md      ← How to connect OpenClaw
│   ├── TRAINING.md            ← How to train behaviors
│   └── TROUBLESHOOTING.md
└── LICENSE                    ← MIT (free for everyone)
```

### Why People Would Star This Project
- First open-source Hermes-powered robot dog
- OpenClaw + GLM-5.2 (free, no OpenAI subscription)
- Personality system (switch between guard dog / puppy / assistant / sassy)
- Behavior training framework (reward-based learning)
- Under $250, no 3D printer, no soldering
- Beginner-friendly with full docs

---

## TIMELINE

| Week | Goal |
|------|------|
| 1 | Order PiDog + Pi 5. While waiting, I prepare all code on Mac mini. |
| 2 | Assemble PiDog (1-2 hours). Install Hermes + PiDog library. |
| 3 | Robot talks + listens + moves. Test basic voice commands. |
| 4 | Add camera vision. Robot recognizes faces, follows people. |
| 5 | Add personality system. Train custom tricks. |
| 6 | Add behavior learning (reward system). Schedule-based behavior. |
| 7 | Write docs + README. Clean up code. |
| 8 | Publish on GitHub. Share on Reddit + Twitter. |

---

*Built by Sut Ring Aung + Hermes Agent*
*Brain first. Body later. Build the future.* 🐕