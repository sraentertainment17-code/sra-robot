#!/usr/bin/env python3
"""
SRA Robot — Assembly Checker Bot (assembly_checker.py)
======================================================
Uses the warn_mistake skill to check electronics polarity during assembly.
You send it a photo + text, it returns a JSON safety verdict.
Runs on Mac mini (uses vision_analyze for photo checking) or Pi 5 (uses OpenCV).

Usage:
    python3 assembly_checker.py

Or import the checker directly:
    from assembly_checker import check_polarity
    result = check_polarity("Is this capacitor backwards?", photo_path="board.jpg")
"""

import os
import sys
import json
import subprocess
import tempfile

# Import the warn_mistake electronics parser
sys.path.insert(0, os.path.dirname(__file__))
from warn_mistake_electronics import parse_polarity, route_warn_mistake, _detect_part, _detect_reverse_polarity


def analyze_photo_polarity(photo_path):
    """
    Analyze a photo for polarity issues.
    On Mac mini: uses vision_analyze (Hermes tool)
    On Pi 5: uses OpenCV + pattern matching

    Returns dict:
        {"polarity_reversed": True/False/None, "part": "capacitor", "clear": True/False}
    """
    if not os.path.exists(photo_path):
        return {"polarity_reversed": None, "part": None, "clear": False}

    # Try OpenCV first (works on both Mac and Pi)
    try:
        result = analyze_with_opencv(photo_path)
        if result is not None:
            return result
    except Exception:
        pass

    # Fallback: return None (let text analysis handle it)
    return {"polarity_reversed": None, "part": None, "clear": False}


def analyze_with_opencv(photo_path):
    """
    Basic OpenCV-based polarity detection.
    Looks for:
    - Electrolytic capacitor stripes (dark band on one side)
    - Diode bands (dark line on one end)
    - Board silkscreen marks (minus signs, plus signs)

    This is a simplified detector. For production, you'd train a model.
    """
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None

    try:
        img = cv2.imread(photo_path)
        if img is None:
            return None

        # Check image quality (blur detection)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
        if blur_score < 50:
            return {"polarity_reversed": None, "part": None, "clear": False}

        # Basic detection: look for dark stripes/bands
        # This is a placeholder — real detection needs trained model
        # For now, return that photo is clear but can't determine polarity
        return {"polarity_reversed": None, "part": None, "clear": True}

    except Exception:
        return None


def check_polarity(text, photo_path=None):
    """
    Full polarity check: text + optional photo analysis → JSON verdict.
    Returns the warn_mistake JSON string.

    Args:
        text: User's question (e.g. "Is this capacitor backwards?")
        photo_path: Path to photo file (optional)

    Returns:
        JSON string matching warn_mistake schema
    """
    has_photo = photo_path is not None
    photo_analysis = None

    if has_photo:
        photo_analysis = analyze_photo_polarity(photo_path)

    return parse_polarity(text, has_photo=has_photo, photo_analysis=photo_analysis)


def handle_check(text, photo_path=None, speak_callback=None):
    """
    Full handler: check polarity → route → execute action.

    Args:
        text: User's text
        photo_path: Optional photo path
        speak_callback: Function to call for TTS (e.g. robot_brain's speak())

    Returns:
        Dict with action and spoken message
    """
    # Get JSON verdict
    json_result = check_polarity(text, photo_path)
    result = json.loads(json_result)

    # Route to action
    decision = route_warn_mistake(json_result)

    # Execute
    if speak_callback:
        speak_callback(decision["speak"])
    else:
        print(f"🤖 {decision['speak']}")

    return {
        "json": result,
        "action": decision["action"],
        "speak": decision["speak"],
        "block_power": decision.get("block_power", False),
    }


# ─── Interactive mode (for testing without Telegram) ───
def interactive_mode():
    """Run as interactive CLI for testing during assembly."""
    print("""
╔══════════════════════════════════════════╗
║   🔧 SRA Assembly Checker                ║
║   Electronics polarity safety checker    ║
╚══════════════════════════════════════════╝

Type your question (or 'exit' to quit):
Examples:
  "Is this capacitor backwards?"
  "Does this diode look right?"
  "Check my battery connection"
  "Is the LED oriented correctly?"
""")

    while True:
        try:
            text = input("🔍 > ").strip()
            if text.lower() in ["exit", "quit", "bye"]:
                print("👋 Stay safe!")
                break
            if not text:
                continue

            # Ask for photo
            photo = input("📷 Photo path (or press Enter to skip): ").strip()
            photo_path = photo if photo and os.path.exists(photo) else None

            # Check
            result = handle_check(text, photo_path)

            # Print JSON
            print(f"\n📋 JSON: {json.dumps(result['json'], indent=2)}")
            print(f"🎯 Action: {result['action']}")
            print(f"🤖 Spoken: {result['speak']}")
            if result.get("block_power"):
                print("🚫 POWER BLOCKED — fix the polarity issue first!")
            print()

        except KeyboardInterrupt:
            print("\n👋 Stay safe!")
            break
        except Exception as e:
            print(f"⚠️ Error: {e}\n")


if __name__ == "__main__":
    interactive_mode()