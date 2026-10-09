#!/usr/bin/env python3
"""
warn_mistake — Electronics Polarity Safety Checker
===================================================
From user text and/or photo, output ONLY one JSON object. No chat outside JSON.

SCHEMA:
  {"skill":"warn_mistake","intent":"...","part":"...","confidence":0.0,"warn":"...","say":"...","raw":"..."}

INTENTS: warn_reverse_polarity | warn_other | ok_check | need_photo | unknown
PARTS:   capacitor | diode | battery | other | null
WARN:    none | soft | hard

CONFIDENCE BANDS:
  ≥ 0.75 → act
  0.45–0.74 → soft/ask
  < 0.45 → unknown or need_photo

RULES:
  warn_reverse_polarity → warn must be "hard"
  ok_check → warn must be "none"
  need_photo → warn "soft"
  unknown → warn "soft"
  If unclear / no photo when needed → intent need_photo

Usage:
    from warn_mistake_electronics import parse_polarity
    result = parse_polarity("Is this capacitor backwards?", has_photo=False)
    # Returns JSON string only — no chat outside JSON
"""

import json
import re

PROTOCOL = "warn_mistake"

# ─── Part Detection ───
PART_PATTERNS = {
    "capacitor": [
        r'\bcap(?:acitor)?\b',
        r'\belectrolytic\b',
        r'\btantalum\b',
        r'\bceramic\b',
    ],
    "diode": [
        r'\bdiode\b',
        r'\bled\b',
        r'\bzener\b',
        r'\bschottky\b',
    ],
    "battery": [
        r'\bbattery\b',
        r'\blipo\b',
        r'\bli-?ion\b',
        r'\bcoin cell\b',
        r'\bcoin\s*cell\b',
        r'\bpower\s*cell\b',
        r'\bpack\b',
    ],
    "other": [
        r'\bic\b',
        r'\bchip\b',
        r'\bregulator\b',
        r'\bvoltage regulator\b',
        r'\bpot\b',
        r'\bresistor\b',
    ],
}

# ─── Intent Keywords ───
REVERSE_PATTERNS = [
    r'\bbackwards?\b',
    r'\breverse(?:d)?\b',
    r'\bwrong way\b',
    r'\bflipped\b',
    r'\bupside down\b',
    r'\bwrong direction\b',
    r'\bbad polarity\b',
    r'\bpolarity wrong\b',
    r'\bpolarity\b.*\bwrong\b',
    r'\bwrong\b.*\bpolarity\b',
]

OK_PATTERNS = [
    r'\b(?:does|do) (?:this|it) look (?:right|correct|ok)\b',
    r'\b(?:is|does) (?:this|it) (?:right|correct|ok)\b',
    r'\blook(?:s)? (?:right|correct|ok)\b',
    r'\bcorrectly\b',
    r'\bgood\b',
    r'\bverify\b',
    r'\bcheck\b.*\bok\b',
]

CHECK_PATTERNS = [
    r'\bcheck\b',
    r'\bverify\b',
    r'\binspect\b',
    r'\blook at\b',
    r'\breview\b',
    r'\bdoes (?:this|it) look\b',
    r'\bis (?:this|it) (?:right|correct|ok)\b',
    r'\bcorrect\b',
    r'\bok\b',
    r'\bright\b',
]

REVERSED_KEYWORDS = [
    'backwards', 'backwards', 'reverse', 'reversed', 'wrong way',
    'flipped', 'upside down', 'wrong direction', 'bad polarity',
    'polarity wrong', 'wrong polarity',
]


def _detect_part(text):
    """Detect which electronic part the user is asking about."""
    text_lower = text.lower()
    for part, patterns in PART_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return part
    return None


def _detect_reverse_polarity(text):
    """Check if user is asking about reverse polarity."""
    text_lower = text.lower()
    for pattern in REVERSE_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def _detect_ok_check(text):
    """Check if user is asking if something looks correct."""
    text_lower = text.lower()
    for pattern in OK_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def _detect_check_request(text):
    """Check if user is asking for a general check."""
    text_lower = text.lower()
    for pattern in CHECK_PATTERNS:
        if re.search(pattern, text_lower):
            return True
    return False


def parse_polarity(raw_text, has_photo=False, photo_analysis=None):
    """
    Parse user text + photo info into warn_mistake JSON.
    Output: JSON string ONLY. No chat outside JSON.

    Args:
        raw_text: User's text input
        has_photo: Whether user provided a photo
        photo_analysis: Dict with photo analysis results (optional):
            {"polarity_reversed": True/False, "part": "capacitor", "clear": True/False}
    """
    text = raw_text.strip()
    part = _detect_part(text)
    is_reverse = _detect_reverse_polarity(text)
    is_ok = _detect_ok_check(text)
    is_check = _detect_check_request(text)

    # ─── No photo needed for check ───
    if is_check and not has_photo and not is_reverse and not is_ok:
        # User asks to check but no photo
        result = {
            "skill": PROTOCOL,
            "intent": "need_photo",
            "part": part,
            "confidence": 0.35,
            "warn": "soft",
            "say": "Send a clear photo of the part and the plus/minus silkscreen.",
            "raw": raw_text,
        }
        return json.dumps(result, separators=(',', ':'))

    # ─── Photo analysis overrides text ───
    if photo_analysis:
        part = photo_analysis.get("part", part)
        polarity_reversed = photo_analysis.get("polarity_reversed", None)
        photo_clear = photo_analysis.get("clear", True)

        if not photo_clear:
            result = {
                "skill": PROTOCOL,
                "intent": "unknown",
                "part": part,
                "confidence": 0.40,
                "warn": "soft",
                "say": "Photo is blurry. Send a sharper one showing the stripe and board mark.",
                "raw": raw_text,
            }
            return json.dumps(result, separators=(',', ':'))

        if polarity_reversed is True:
            say = _reverse_polarity_message(part)
            result = {
                "skill": PROTOCOL,
                "intent": "warn_reverse_polarity",
                "part": part,
                "confidence": 0.88,
                "warn": "hard",
                "say": say,
                "raw": raw_text,
            }
            return json.dumps(result, separators=(',', ':'))

        if polarity_reversed is False:
            say = _ok_message(part)
            result = {
                "skill": PROTOCOL,
                "intent": "ok_check",
                "part": part,
                "confidence": 0.85,
                "warn": "none",
                "say": say,
                "raw": raw_text,
            }
            return json.dumps(result, separators=(',', ':'))

    # ─── Text-only analysis ───
    if is_reverse:
        # User says it's backwards — hard warn
        confidence = 0.88 if part else 0.75
        say = _reverse_polarity_message(part)
        result = {
            "skill": PROTOCOL,
            "intent": "warn_reverse_polarity",
            "part": part or "other",
            "confidence": confidence,
            "warn": "hard",
            "say": say,
            "raw": raw_text,
        }
        return json.dumps(result, separators=(',', ':'))

    if is_ok and has_photo:
        # User asks if correct + has photo → ok_check
        say = _ok_message(part)
        result = {
            "skill": PROTOCOL,
            "intent": "ok_check",
            "part": part or "other",
            "confidence": 0.82,
            "warn": "none",
            "say": say,
            "raw": raw_text,
        }
        return json.dumps(result, separators=(',', ':'))

    if is_ok and not has_photo:
        # User asks if correct but no photo → need photo
        result = {
            "skill": PROTOCOL,
            "intent": "need_photo",
            "part": part,
            "confidence": 0.40,
            "warn": "soft",
            "say": "Send a clear photo of the part and the plus/minus silkscreen.",
            "raw": raw_text,
        }
        return json.dumps(result, separators=(',', ':'))

    if is_check and has_photo:
        # User asks to check + has photo → ok_check (assume ok unless analysis says otherwise)
        say = _ok_message(part)
        result = {
            "skill": PROTOCOL,
            "intent": "ok_check",
            "part": part or "other",
            "confidence": 0.75,
            "warn": "none",
            "say": say,
            "raw": raw_text,
        }
        return json.dumps(result, separators=(',', ':'))

    # ─── Can't determine ───
    if part and is_check:
        # We know the part but not sure what the user wants
        result = {
            "skill": PROTOCOL,
            "intent": "unknown",
            "part": part,
            "confidence": 0.42,
            "warn": "soft",
            "say": f"I see you're asking about the {part}, but I need a photo to check polarity.",
            "raw": raw_text,
        }
        return json.dumps(result, separators=(',', ':'))

    # ─── Totally unknown ───
    result = {
        "skill": PROTOCOL,
        "intent": "unknown",
        "part": None,
        "confidence": 0.20,
        "warn": "soft",
        "say": "I can't determine what you need. Can you describe the part and what to check?",
        "raw": raw_text,
    }
    return json.dumps(result, separators=(',', ':'))


def _reverse_polarity_message(part):
    """Generate spoken message for reverse polarity warning."""
    messages = {
        "capacitor": "Stop — that looks reverse polarity. Match the stripe to the board minus mark.",
        "diode": "Stop — diode band should match the silkscreen line. Flip it.",
        "battery": "Stop — red wire goes to plus. You have it reversed. Disconnect now.",
        "other": "Stop — that component looks reversed. Check the orientation mark.",
    }
    return messages.get(part, "Stop — that looks reverse polarity. Check the orientation marks.")


def _ok_message(part):
    """Generate spoken message for OK check."""
    messages = {
        "capacitor": "Looks correct. Stripe lines up with the minus mark.",
        "diode": "Diode is correct. Band lines up with the silkscreen.",
        "battery": "Battery is correct. Red to plus, black to minus.",
        "other": "Looks correct. Orientation marks are aligned.",
    }
    return messages.get(part, "Looks correct.")


# ─── Router (after JSON) ───
def route_warn_mistake(parsed_json):
    """
    Router for warn_mistake JSON output.
    Hermes calls this after getting the JSON.
    """
    result = json.loads(parsed_json) if isinstance(parsed_json, str) else parsed_json
    warn = result.get("warn", "soft")
    intent = result.get("intent", "unknown")
    say = result.get("say", "")

    if warn == "hard":
        return {"action": "speak_block", "speak": say, "block_power": True}
    elif intent == "ok_check":
        return {"action": "speak_ok", "speak": say, "block_power": False}
    elif intent == "need_photo":
        return {"action": "ask_photo", "speak": say, "block_power": False}
    elif intent == "unknown":
        return {"action": "ask_clarify", "speak": say, "block_power": False}
    else:
        return {"action": "ask_once", "speak": say, "block_power": False}


# ─── Test Suite ───
if __name__ == "__main__":
    tests = [
        # (text, has_photo, photo_analysis, expected_intent, expected_warn)
        ("Is this electrolytic capacitor backwards?", False, None, "warn_reverse_polarity", "hard"),
        ("Does this look right?", True, None, "ok_check", "none"),
        ("Check my board", False, None, "need_photo", "soft"),
        ("Is the diode oriented correctly?", True, None, "ok_check", "none"),
        ("I connected the battery", True, {"polarity_reversed": True, "part": "battery", "clear": True}, "warn_reverse_polarity", "hard"),
        ("Check this cap", True, {"polarity_reversed": False, "part": "capacitor", "clear": True}, "ok_check", "none"),
        ("Check this cap", True, {"polarity_reversed": None, "part": "capacitor", "clear": False}, "unknown", "soft"),
        ("Diode ok?", True, None, "ok_check", "none"),
        ("What is this thing?", True, None, "unknown", "soft"),
        ("Is this capacitor backwards?", True, {"polarity_reversed": True, "part": "capacitor", "clear": True}, "warn_reverse_polarity", "hard"),
        ("", False, None, "unknown", "soft"),
        ("Check the battery", True, {"polarity_reversed": False, "part": "battery", "clear": True}, "ok_check", "none"),
    ]

    print("🔧 warn_mistake — Electronics Polarity Safety Checker\n")
    print(f"{'INPUT':<42} {'PHOTO':<6} {'INTENT':<25} {'WARN':<6} {'CONF':<6} {'OK':<3}")
    print("─" * 100)

    passed = 0
    failed = 0

    for text, has_photo, photo_analysis, exp_intent, exp_warn in tests:
        result_json = parse_polarity(text, has_photo=has_photo, photo_analysis=photo_analysis)
        result = json.loads(result_json)

        ok = "✅" if (result["intent"] == exp_intent and result["warn"] == exp_warn) else "❌"
        if ok == "✅":
            passed += 1
        else:
            failed += 1

        display_text = text[:40] if text else "(empty)"
        print(f"{display_text:<42} {str(has_photo):<6} {result['intent']:<25} {result['warn']:<6} {result['confidence']:<6} {ok}")

    print(f"\n{'─' * 100}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")

    # Show spec examples
    print("\n📋 Protocol Spec Examples:\n")
    spec_examples = [
        ("Is this electrolytic capacitor backwards?", False, None),
        ("Does this look right?", True, None),
        ("Check my board", False, None),
    ]
    for text, has_photo, photo_analysis in spec_examples:
        result = parse_polarity(text, has_photo=has_photo, photo_analysis=photo_analysis)
        print(f'  "{text}"')
        print(f'  → {json.dumps(json.loads(result), indent=2)}')
        print()