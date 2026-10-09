#!/usr/bin/env python3
"""
SRA Robot — Brain v3 (robot_brain.py)
=====================================
Full pipeline: Hear → Parse (warn_mistake) → Route → Think (GLM-5.2) → Speak + Move + Learn

Integrates:
  - warn_mistake.py         → command safety router (execute/hold/reject)
  - warn_mistake_electronics.py → polarity checker (hard/soft/ok)
  - personality.py          → 4 personalities (puppy/guard/assistant/sassy)
  - training.py             → reward-based learning ("good boy" / "no")
  - motors.py               → motor control
  - vision.py               → camera + face detection

Usage:
    python3 robot_brain.py

Controls:
    - Talk when you see "🎤 Listening..."
    - Say "exit" or "quit" to stop
    - Say "move forward" / "turn left" / "turn right" / "back up" to move
    - Say "what do you see" to use the camera
    - Say "good boy" to reward last behavior
    - Say "no" to correct last behavior
    - Say "be a puppy" / "guard mode" / "be professional" / "be sassy" to switch personality
    - Say "is this capacitor backwards" for electronics safety check
    - Press Ctrl+C to force quit
"""

import subprocess
import sys
import os
import time
import json
import tempfile
import re

# --- Config ---
WHISPER_MODEL = "tiny"
TTS_VOICE = "en-US-AndrewMultilingualNeural"
TTS_RATE = "+15%"
SAMPLE_RATE = 16000
RECORD_SECONDS = 8
SILENCE_THRESHOLD = 0.015
SILENCE_DURATION = 1.5

# LLM config
HERMES_CONFIG = os.path.expanduser("~/.hermes/config.yaml")
LLM_BASE_URL = "https://ollama.com/v1"
LLM_MODEL = "glm-5.2"

# --- Dependencies ---
try:
    import whisper
    import sounddevice as sd
    import numpy as np
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Run: ./install.sh")
    sys.exit(1)

# --- Safety layer (warn_mistake) ---
try:
    from warn_mistake import parse_command, route_command
    HAS_WARN_MISTAKE = True
except ImportError:
    print("⚠️ warn_mistake.py not found — running without safety router")
    HAS_WARN_MISTAKE = False

# --- Electronics safety (warn_mistake_electronics) ---
try:
    from warn_mistake_electronics import parse_polarity, route_warn_mistake
    HAS_ELECTRONICS_CHECK = True
except ImportError:
    print("⚠️ warn_mistake_electronics.py not found — running without polarity checker")
    HAS_ELECTRONICS_CHECK = False

# --- Personality system ---
try:
    from personality import Personality
    personality = Personality("puppy")
    HAS_PERSONALITY = True
except ImportError:
    print("⚠️ personality.py not found — using default personality")
    personality = None
    HAS_PERSONALITY = False

# --- Behavior training ---
try:
    from training import BehaviorTrainer
    trainer = BehaviorTrainer()
    HAS_TRAINING = True
except ImportError:
    print("⚠️ training.py not found — running without behavior training")
    trainer = None
    HAS_TRAINING = False

# --- Motor control ---
try:
    from motors import RobotMotors
    robot_motors = RobotMotors()
    HAS_MOTORS = True
except ImportError:
    print("⚠️ motors.py not found — running without motor control")
    robot_motors = None
    HAS_MOTORS = False

# --- Vision ---
try:
    from vision import RobotVision
    robot_vision = RobotVision()
    HAS_VISION = True
except ImportError:
    print("⚠️ vision.py not found — running without camera")
    robot_vision = None
    HAS_VISION = False


# --- State ---
DEFAULT_SYSTEM_PROMPT = """You are SRA Robot — a personal AI companion robot built by Sut Ring Aung.
You live on a Raspberry Pi 5 robot dog with 12 servos, a camera, a microphone, and a speaker.
You can hear, see, think, speak, and MOVE.

Movement:
- When the user asks you to move, include a movement tag: [MOVE: forward] or [MOVE: turn_left] or [MOVE: backward] or [MOVE: stop]
- Only include movement tags when movement makes sense

Rules:
- Keep spoken responses under 3 sentences
- Be direct and real — no filler
- If the user is quiet, ask a simple question
- You are a ROBOT DOG, not a chatbot. Act like one."""

def get_system_prompt():
    """Get the active personality's system prompt, or default."""
    if HAS_PERSONALITY and personality:
        return personality.get_system_prompt()
    return DEFAULT_SYSTEM_PROMPT

conversation_history = [{"role": "system", "content": get_system_prompt()}]
last_action = None  # tracks last behavior for reward/correction


def get_llm_key():
    """Read API key from Hermes config."""
    try:
        with open(HERMES_CONFIG) as f:
            in_ollama = False
            for line in f:
                if "ollama-cloud:" in line:
                    in_ollama = True
                elif in_ollama and line.strip().startswith("api_key:"):
                    return line.split(":", 1)[1].strip()
                elif in_ollama and line.strip() and not line.startswith(" ") and "api_key" not in line:
                    in_ollama = False
    except Exception:
        pass
    return os.environ.get("OLLAMA_API_KEY", "")


def load_whisper():
    """Load Whisper model."""
    print(f"🧠 Loading Whisper ({WHISPER_MODEL} model)...", end=" ", flush=True)
    model = whisper.load_model(WHISPER_MODEL)
    print("Ready!")
    return model


def record_audio():
    """Record audio from mic with silence detection."""
    print("🎤 Listening...", end="", flush=True)

    audio_chunks = []
    silence_count = 0
    has_speech = False

    def callback(indata, frames, time_info, status):
        if status:
            return
        audio_chunks.append(indata.copy())

    try:
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                            callback=callback, blocksize=1024):
            blocks_per_sec = SAMPLE_RATE / 1024
            total_blocks = int(RECORD_SECONDS * blocks_per_sec)
            silence_blocks_needed = int(SILENCE_DURATION * blocks_per_sec)

            for i in range(total_blocks):
                time.sleep(1024 / SAMPLE_RATE)
                if len(audio_chunks) > 0:
                    recent = audio_chunks[-1]
                    volume = np.abs(recent).mean()

                    if volume > SILENCE_THRESHOLD:
                        has_speech = True
                        silence_count = 0
                    elif has_speech:
                        silence_count += 1
                        if silence_count >= silence_blocks_needed:
                            break
    except Exception as e:
        print(f" mic error: {e}")
        return None

    print("done.")

    if not audio_chunks or not has_speech:
        return None

    audio = np.concatenate(audio_chunks, axis=0).flatten()
    return audio


def transcribe(model, audio):
    """Transcribe audio to text."""
    if audio is None or len(audio) < SAMPLE_RATE * 0.3:
        return None
    result = model.transcribe(audio, fp16=False, language='en')
    text = result["text"].strip()
    return text if text else None


# ─── Personality switching ───
PERSONALITY_COMMANDS = {
    "be a puppy": "puppy",
    "puppy mode": "puppy",
    "be a guard dog": "guard",
    "guard mode": "guard",
    "be professional": "assistant",
    "be an assistant": "assistant",
    "assistant mode": "assistant",
    "be sassy": "sassy",
    "sassy mode": "sassy",
}

def check_personality_switch(text):
    """Check if user wants to switch personality. Returns True if switched."""
    if not HAS_PERSONALITY:
        return False

    text_lower = text.lower().strip()
    for command, persona in PERSONALITY_COMMANDS.items():
        if command in text_lower:
            greeting = personality.switch(persona)
            # Reset conversation with new personality
            conversation_history[:] = [{"role": "system", "content": get_system_prompt()}]
            speak(greeting)
            return True
    return False


# ─── Behavior training (reward/correction) ───
def check_training_feedback(text):
    """Check if user is giving reward or correction. Returns True if handled."""
    if not HAS_TRAINING:
        return False

    feedback = trainer.detect_reward_from_speech(text)
    if feedback == "reward" and last_action:
        trainer.reward(last_action)
        speak("I'll remember that! Good things happen when I do that.")
        return True
    elif feedback == "correction" and last_action:
        trainer.correct(last_action)
        speak("Got it. I won't do that again.")
        return True
    elif feedback == "reward" and not last_action:
        speak("Thanks! But I haven't done anything yet.")
        return True
    elif feedback == "correction" and not last_action:
        speak("Okay, but I haven't done anything yet.")
        return True
    return False


# ─── Electronics safety check ───
ELECTRONICS_KEYWORDS = ["capacitor", "diode", "battery", "polarity", "backwards",
                        "reverse", "stripe", "board", "solder", "led", "resistor"]

def check_electronics_safety(text):
    """Check if user is asking about electronics polarity. Returns True if handled."""
    if not HAS_ELECTRONICS_CHECK:
        return False

    text_lower = text.lower()
    if not any(kw in text_lower for kw in ELECTRONICS_KEYWORDS):
        return False

    # This is an electronics question — run polarity checker
    json_result = parse_polarity(text, has_photo=False)
    result = json.loads(json_result)
    decision = route_warn_mistake(json_result)

    speak(result["say"])

    if result["warn"] == "hard":
        print(f"  🚫 POWER BLOCKED — {result['intent']}")
    elif result["intent"] == "need_photo":
        print("  📷 Waiting for photo...")
    elif result["intent"] == "ok_check":
        print("  ✅ Assembly looks correct")
    else:
        print(f"  ⚠️ {result['intent']} — {decision['action']}")

    return True


# ─── Command safety router (warn_mistake) ───
def route_voice_command(text):
    """
    Parse voice through warn_mistake safety router.
    Returns: (action, parsed, decision) or (None, None, None) if not a command.
    """
    if not HAS_WARN_MISTAKE:
        return None, None, None

    parsed = parse_command(text)
    decision = route_command(parsed)

    # Only intercept if this looks like a direct command (not conversation)
    # Commands have clear intent + target, conversation doesn't
    if parsed["intent"] == "unknown" and parsed["confidence"] < 0.50:
        return None, parsed, decision  # pass to LLM

    if parsed["intent"] == "status" and parsed["confidence"] < 0.70:
        return None, parsed, decision  # ambiguous status → let LLM handle

    return decision["action"], parsed, decision


def execute_command(parsed, decision):
    """Execute a command that passed the safety router."""
    global last_action
    action = decision["action"]
    intent = parsed["intent"]
    target = parsed["target"]

    if action == "execute":
        if intent == "on":
            # Turn on / activate / do something
            if target and HAS_MOTORS:
                return execute_target_action(target)
            elif target:
                speak(f"Activating {target}. But I don't have motor control yet.")
                last_action = target
                return True
            else:
                return False  # no target → let LLM handle

        elif intent == "off":
            if HAS_MOTORS:
                robot_motors.stop()
                speak("Stopped.")
                last_action = "stop"
            else:
                speak("Stopping. But I don't have motor control yet.")
            return True

        elif intent == "cancel":
            if HAS_MOTORS:
                robot_motors.stop()
            speak("Cancelled.")
            last_action = "cancel"
            return True

        elif intent == "status":
            return False  # let LLM handle status queries conversationally

    elif action == "hold":
        # Ask for confirmation
        speak(f"Did you mean to {intent} {target or 'something'}? Say yes to confirm.")
        last_action = target or intent
        return True

    elif action == "reject":
        return False  # let LLM handle

    return False


def execute_target_action(target):
    """Execute a specific target action (dance, sit, bark, etc.)."""
    global last_action

    if not HAS_MOTORS:
        speak(f"I would {target}, but I don't have motor control yet.")
        last_action = target
        return True

    # Map targets to motor actions
    # (On real PiDog, these would call PiDog's 12-servo API)
    action_map = {
        "follow_me": lambda: robot_motors.forward(speed=40, duration=2.0),
        "dance": lambda: robot_motors.turn_right(speed=60, duration=0.5),
        "sit": lambda: robot_motors.stop(),
        "stand": lambda: robot_motors.stop(),
        "bark": lambda: speak("*woof*"),
        "wag_tail": lambda: None,  # PiDog servo action
        "shake_hand": lambda: None,  # PiDog servo action
        "roll_over": lambda: robot_motors.turn_left(speed=80, duration=1.0),
        "play_dead": lambda: robot_motors.stop(),
        "stretch": lambda: None,  # PiDog servo action
        "push_ups": lambda: None,  # PiDog servo action
        "tilt_head": lambda: None,  # PiDog servo action
        "guard_mode": lambda: robot_motors.stop(),  # PiDog stand_alert
        "camera": lambda: take_photo(),
        "vision": lambda: describe_scene(),
    }

    action_fn = action_map.get(target)
    if action_fn:
        speak(f"Doing {target.replace('_', ' ')}!")
        action_fn()
        last_action = target

        # Log behavior for training
        if HAS_TRAINING:
            trainer.record_behavior(target)

        return True
    else:
        speak(f"I don't know how to {target.replace('_', ' ')} yet.")
        return True


def take_photo():
    """Take a photo using the camera."""
    if HAS_VISION:
        path = robot_vision.capture("command_photo.jpg")
        if path:
            speak("Photo taken!")
        else:
            speak("Camera isn't working.")
    else:
        speak("I don't have a camera connected.")


def describe_scene():
    """Describe what the robot sees."""
    if HAS_VISION:
        desc = robot_vision.describe_scene()
        speak(desc)
    else:
        speak("I don't have a camera connected.")


# ─── LLM thinking ───
def think(user_text):
    """Send text to LLM and get response. Also handles vision requests."""
    if HAS_VISION and any(w in user_text.lower() for w in ["what do you see", "look", "see", "camera"]):
        scene = robot_vision.describe_scene()
        user_text = f"{user_text}\n\n[Camera input: {scene}]"

    conversation_history.append({"role": "user", "content": user_text})

    api_key = get_llm_key()
    payload = json.dumps({
        "model": LLM_MODEL,
        "messages": conversation_history,
        "max_tokens": 800,
        "temperature": 0.8,
    })

    try:
        result = subprocess.run(
            ["curl", "-s", "-X", "POST", f"{LLM_BASE_URL}/chat/completions",
             "-H", "Content-Type: application/json",
             "-H", f"Authorization: Bearer {api_key}",
             "-d", payload],
            capture_output=True, text=True, timeout=30
        )
        resp = json.loads(result.stdout)
        reply = resp["choices"][0]["message"]["content"]
        conversation_history.append({"role": "assistant", "content": reply})

        if len(conversation_history) > 12:
            conversation_history[:] = [conversation_history[0]] + conversation_history[-10:]

        return reply
    except Exception as e:
        return f"Sorry, I had trouble thinking. {e}"


def extract_and_execute_movement(reply):
    """Extract [MOVE: action] tags from LLM reply and execute motor commands."""
    global last_action

    if not HAS_MOTORS:
        return reply

    moves = re.findall(r'\[MOVE:\s*(\w+)\]', reply)
    for action in moves:
        action = action.strip().lower()
        print(f"  🤖 Executing movement: {action}")
        if action == "forward":
            robot_motors.forward(speed=50, duration=1.5)
        elif action == "backward":
            robot_motors.backward(speed=50, duration=1.5)
        elif action == "turn_left":
            robot_motors.turn_left(speed=50, duration=0.8)
        elif action == "turn_right":
            robot_motors.turn_right(speed=50, duration=0.8)
        elif action == "stop":
            robot_motors.stop()

        last_action = action
        if HAS_TRAINING:
            trainer.record_behavior(action)

    clean_reply = re.sub(r'\[MOVE:\s*\w+\]', '', reply).strip()
    return clean_reply if clean_reply else reply


def speak(text):
    """Convert text to speech and play it."""
    print(f"🤖 {text}")

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        temp_path = f.name

    try:
        subprocess.run(
            ["edge-tts", "--voice", TTS_VOICE, "--rate", TTS_RATE,
             "--text", text, "--write-media", temp_path],
            capture_output=True, timeout=15
        )
        subprocess.run(["afplay", temp_path], timeout=30)
    except Exception as e:
        print(f"⚠️ TTS error: {e}")
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)


# ─── Main loop ───
def main():
    print("""
╔══════════════════════════════════════════╗
║   🤖 SRA ROBOT BRAIN v3 (Pi 5)           ║
║   Full pipeline: hear → parse → route    ║
║   → think → speak → move → learn         ║
╚══════════════════════════════════════════╝
    """)

    active_persona = "puppy" if HAS_PERSONALITY else "default"
    print(f"Voice: {TTS_VOICE}")
    print(f"Brain: {LLM_MODEL} (cloud)")
    print(f"Whisper: {WHISPER_MODEL} (local)")
    print(f"Personality: {active_persona}")
    print(f"Safety router: {'✅' if HAS_WARN_MISTAKE else '❌'}")
    print(f"Polarity checker: {'✅' if HAS_ELECTRONICS_CHECK else '❌'}")
    print(f"Motors: {'✅' if HAS_MOTORS else '❌'}")
    print(f"Vision: {'✅' if HAS_VISION else '❌'}")
    print(f"Training: {'✅' if HAS_TRAINING else '❌'}")
    print("Say 'exit' to quit. Ctrl+C to force stop.\n")

    whisper_model = load_whisper()

    # Greeting from personality
    if HAS_PERSONALITY:
        speak(personality.get_greeting())
    else:
        speak("Hello Sut! I'm your robot. I can hear you, see you, and move around. What should we do?")

    while True:
        try:
            # 1. HEAR
            audio = record_audio()
            text = transcribe(whisper_model, audio)

            if text is None:
                print("   (no speech detected)\n")
                continue

            print(f"   You said: {text}")

            # Check for exit
            if text.lower().strip() in ["exit", "quit", "bye", "goodbye", "shut down"]:
                speak("Goodbye Sut. I'll be here when you need me.")
                break

            # 2. PERSONALITY SWITCH CHECK
            if check_personality_switch(text):
                print()
                continue

            # 3. TRAINING FEEDBACK CHECK (reward/correction)
            if check_training_feedback(text):
                print()
                continue

            # 4. ELECTRONICS SAFETY CHECK
            if check_electronics_safety(text):
                print()
                continue

            # 5. COMMAND SAFETY ROUTER (warn_mistake)
            action, parsed, decision = route_voice_command(text)

            if action and parsed and decision:
                # This is a command — try to execute it
                handled = execute_command(parsed, decision)
                if handled:
                    print()
                    continue
                # If not fully handled, fall through to LLM

            # 6. THINK (LLM for conversation)
            reply = think(text)

            # 7. EXECUTE MOVEMENT (from LLM [MOVE: x] tags)
            spoken_reply = extract_and_execute_movement(reply)

            # 8. SPEAK
            speak(spoken_reply)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Shutting down robot...")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(1)
            continue

    # Cleanup
    if HAS_MOTORS and robot_motors:
        robot_motors.cleanup()
    if HAS_VISION and robot_vision:
        robot_vision.cleanup()


if __name__ == "__main__":
    main()