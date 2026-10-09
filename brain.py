#!/usr/bin/env python3
"""
SRA Robot Brain v1 — Voice Conversation Loop
=============================================
Hears you (mic) → thinks (Hermes LLM) → speaks back (Edge TTS)
This is Phase 1: THE BRAIN. No body yet.

Usage:
    python3 brain.py

Controls:
    - Talk when you see "🎤 Listening..."
    - Say "exit" or "quit" to stop
    - Press Ctrl+C to force quit

Requirements:
    - AirPods Pro 2 (or any mic) connected
    - Edge TTS installed (pip install edge-tts)
    - Whisper installed (pip install openai-whisper)
    - Hermes gateway running on localhost:18789
"""

import subprocess
import sys
import os
import time
import json
import tempfile
import threading
import queue

# --- Config ---
WHISPER_MODEL = "base"        # tiny < base < small < medium < large (base is good balance)
TTS_VOICE = "en-US-AndrewMultilingualNeural"  # warm male voice
TTS_RATE = "+15%"              # slightly faster
SAMPLE_RATE = 16000            # whisper needs 16kHz
RECORD_SECONDS = 8             # max seconds per utterance
SILENCE_THRESHOLD = 0.01       # below this = silence (auto-stop)
SILENCE_DURATION = 1.5        # seconds of silence before stopping recording
# LLM endpoint — read from Hermes config (key never hard-coded)
HERMES_CONFIG = os.path.expanduser("~/.hermes/config.yaml")
LLM_BASE_URL = "https://ollama.com/v1"
LLM_MODEL = "glm-5.2"

def get_llm_key():
    """Read API key from Hermes config without exposing it."""
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
SYSTEM_PROMPT = """You are SRA Robot — a personal AI companion built by your owner.
You are warm, concise, and speak in short sentences (like talking, not texting).
You have opinions and personality. You're excited about AI and robotics.
Keep responses under 3 sentences when spoken. Be direct and real.
If the user is quiet, ask a simple question to keep the conversation going."""

# --- State ---
conversation_history = [
    {"role": "system", "content": SYSTEM_PROMPT}
]

# --- Dependencies ---
try:
    import whisper
    import sounddevice as sd
    import numpy as np
except ImportError as e:
    print(f"❌ Missing dependency: {e}")
    print("Install with: pip3 install openai-whisper sounddevice numpy")
    sys.exit(1)


def load_whisper():
    """Load Whisper speech recognition model."""
    print(f"🧠 Loading Whisper ({WHISPER_MODEL} model)...", end=" ", flush=True)
    model = whisper.load_model(WHISPER_MODEL)
    print("Ready!")
    return model


def record_audio(model=None):
    """Record audio from mic with silence detection. Returns audio numpy array."""
    print("🎤 Listening...", end="", flush=True)
    
    audio_chunks = []
    silence_count = 0
    has_speech = False
    
    def callback(indata, frames, time_info, status):
        if status:
            return
        audio_chunks.append(indata.copy())
    
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype='float32',
                        callback=callback, blocksize=1024):
        # Record up to RECORD_SECONDS, stop early on silence
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
    
    print("done.")
    
    if not audio_chunks or not has_speech:
        return None
    
    audio = np.concatenate(audio_chunks, axis=0).flatten()
    return audio


def transcribe(model, audio):
    """Transcribe audio to text using Whisper."""
    if audio is None or len(audio) < SAMPLE_RATE * 0.3:  # less than 0.3s
        return None
    result = model.transcribe(audio, fp16=False, language='en')
    text = result["text"].strip()
    return text if text else None


def think(user_text):
    """Send text to Hermes LLM and get a response."""
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
        # Keep history short (last 10 messages + system)
        if len(conversation_history) > 12:
            conversation_history[:] = [conversation_history[0]] + conversation_history[-10:]
        return reply
    except Exception as e:
        return f"Sorry, I had trouble thinking. {e}"


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
        # Play the audio
        subprocess.run(["afplay", temp_path], timeout=30)
    except Exception as e:
        print(f"⚠️ TTS error: {e}")
    finally:
        os.unlink(temp_path)


def main():
    print("""
╔══════════════════════════════════════════╗
║   🤖 SRA ROBOT BRAIN v1                  ║
║   Brain first. Body later.               ║
╚══════════════════════════════════════════╝
    """)
    print("Voice: Andrew (en-US) | Model: Whisper base + GLM-5.2")
    print("Say 'exit' to quit. Ctrl+C to force stop.\n")
    
    # Load Whisper
    whisper_model = load_whisper()
    
    # Greeting
    speak("Hello! I'm your robot brain. I'm alive and ready to talk. What's on your mind?")
    
    # Main conversation loop
    while True:
        try:
            # Record
            audio = record_audio()
            
            # Transcribe
            text = transcribe(whisper_model, audio)
            
            if text is None:
                print("   (no speech detected)\n")
                continue
            
            print(f"   You said: {text}")
            
            # Check for exit
            if text.lower().strip() in ["exit", "quit", "bye", "goodbye", "shut down"]:
                speak("Goodbye! I'll be here when you need me.")
                break
            
            # Think
            reply = think(text)
            
            # Speak
            speak(reply)
            
            print()  # spacing
            
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down robot brain...")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}")
            time.sleep(1)
            continue


if __name__ == "__main__":
    main()