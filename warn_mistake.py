#!/usr/bin/env python3
"""
warn_mistake v1 — Intent Parser + Router
=========================================
Deterministic command safety layer for the robot dog.
No second model call. Pure keyword/regex parse → confidence band → action.

Protocol:
  Parse: raw text → {v, intent, target, confidence, warn, raw}
  Route: confidence bands decide execute / hold / reject

  conf >= 0.80 → execute, warn=false
  0.50–0.79   → warn=true, hold/confirm
  < 0.50      → intent=unknown, warn=true, no execute

Firmware / Voice components emit this JSON only — nothing free-form.
Hermes (brain) reuses the same shape.

Usage:
    from warn_mistake import parse_command, route_command

    parsed = parse_command("turn on guard mode")
    # → {"v":1,"intent":"on","target":"guard_mode","confidence":0.92,"warn":false,"raw":"turn on guard mode"}

    decision = route_command(parsed)
    # → {"action": "execute", "reason": "confidence 0.92 >= 0.80"}
"""

import re
import json

# ─── Protocol Version ───
PROTOCOL_VERSION = 1

# ─── Confidence Bands ───
CONF_EXECUTE = 0.80   # >= this → execute
CONF_WARN = 0.50      # >= this → warn/hold; < this → unknown

# ─── Intent Keywords ───
# Ordered by specificity (longest/most-specific first)
INTENT_PATTERNS = {
    "on": [
        (r'\bturn on\b', 0.95),
        (r'\bstart\b', 0.90),
        (r'\bactivate\b', 0.92),
        (r'\benable\b', 0.88),
        (r'\bpower on\b', 0.93),
        (r'\bwake up\b', 0.85),
        (r'\bcome (here|to me)\b', 0.88),
        (r'\bdo (it|that|this)\b', 0.82),
        (r'\bgo\b', 0.75),
        (r'\bbegin\b', 0.85),
    ],
    "off": [
        (r'\bturn off\b', 0.95),
        (r'\bstop\b', 0.90),
        (r'\bdeactivate\b', 0.92),
        (r'\bdisable\b', 0.88),
        (r'\bpower off\b', 0.93),
        (r'\bshut ?down\b', 0.90),
        (r'\bgo to sleep\b', 0.88),
        (r'\bsleep\b', 0.80),
        (r'\bknock it off\b', 0.85),
        (r'\bsit down\b', 0.88),
        (r'\blie down\b', 0.85),
        (r'\bchill\b', 0.70),
    ],
    "status": [
        (r'\bwhat(?:\'s| is) (?:the |your )?status\b', 0.92),
        (r'\bstatus\b', 0.88),
        (r'\bhow are you\b', 0.85),
        (r'\bwhat (?:are )?you doing\b', 0.87),
        (r'\bwhat do you see\b', 0.90),
        (r'\breport\b', 0.85),
        (r'\bwhere are you\b', 0.82),
        (r'\bwhat can you do\b', 0.80),
        (r'\bhelp\b', 0.72),
        (r'\blights?\b', 0.55),
        (r'\?\s*$', 0.55),  # ending with ? = likely status query
    ],
    "cancel": [
        (r'\bcancel\b', 0.92),
        (r'\bnever ?mind\b', 0.90),
        (r'\bnever mind\b', 0.90),
        (r'\babort\b', 0.93),
        (r'\bwait\b', 0.75),
        (r'\bhold on\b', 0.82),
        (r'\bwait no\b', 0.88),
        (r'\bactually no\b', 0.85),
        (r'\bno wait\b', 0.87),
        (r'\bforget it\b', 0.80),
        (r'\bscratch that\b', 0.82),
    ],
}

# ─── Target Keywords ───
# Maps natural language → canonical target names
# Moses: tweak these to match your robot's demo actions
TARGET_PATTERNS = {
    # Robot dog behaviors
    "guard_mode": [r'\bguard\b', r'\bguard mode\b', r'\bprotect\b', r'\bpatrol\b'],
    "follow_me": [r'\bfollow me\b', r'\bfollow\b', r'\bcome (here|to me)\b', r'\bcome\b'],
    "dance": [r'\bdance\b', r'\bdo a dance\b', r'\bshow me your moves\b'],
    "sit": [r'\bsit\b', r'\bsit down\b'],
    "stand": [r'\bstand\b', r'\bstand up\b', r'\bget up\b'],
    "bark": [r'\bbark\b', r'\bspeak\b', r'\bsay something\b'],
    "wag_tail": [r'\bwag\b', r'\bwag (your )?tail\b', r'\btail\b'],
    "shake_hand": [r'\bshake\b', r'\bshake (my )?hand\b', r'\bpaw\b'],
    "roll_over": [r'\broll over\b', r'\broll\b'],
    "play_dead": [r'\bplay dead\b', r'\bdead\b', r'\bplay possum\b'],
    "stretch": [r'\bstretch\b'],
    "push_ups": [r'\bpush ?ups\b', r'\bpush up\b', r'\bpushups\b'],
    "tilt_head": [r'\btilt\b', r'\btilt (your )?head\b', r'\bhead tilt\b'],

    # System targets
    "camera": [r'\bcamera\b', r'\btake (a )?photo\b', r'\btake (a )?picture\b', r'\bsnap\b'],
    "vision": [r'\bsee\b', r'\blook\b', r'\bwhat do you see\b', r'\bvision\b'],
    "voice": [r'\bvoice\b', r'\bspeak\b', r'\btalk\b'],
    "motors": [r'\bmotor\b', r'\bmove\b', r'\bwalk\b', r'\brun\b'],

    # Smart home (demo extensible)
    "garage_light": [r'\bgarage light\b', r'\bgarage\b'],
    "living_room_light": [r'\bliving room\b', r'\bliving room light\b'],
    "bedroom_light": [r'\bbedroom\b', r'\bbedroom light\b'],
    "front_door": [r'\bfront door\b', r'\bdoor\b'],
    "heater": [r'\bheater\b', r'\bheat\b', r'\bheating\b'],
    "ac": [r'\bac\b', r'\bair condition\b', r'\bcooling\b'],
}


def _match_intent(text):
    """Match text against intent patterns. Returns (intent, confidence)."""
    text_lower = text.lower().strip()
    best_intent = "unknown"
    best_conf = 0.0

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern, base_conf in patterns:
            if re.search(pattern, text_lower):
                if base_conf > best_conf:
                    best_conf = base_conf
                    best_intent = intent

    return best_intent, best_conf


def _match_target(text):
    """Match text against target patterns. Returns (target, confidence_bonus) or (None, 0)."""
    text_lower = text.lower().strip()
    best_target = None
    best_score = 0

    for target, patterns in TARGET_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                # Longer pattern = more specific = higher bonus
                specificity = len(pattern) / 100.0
                score = 0.05 + specificity
                if score > best_score:
                    best_score = score
                    best_target = target

    return best_target, min(best_score, 0.08)


def parse_command(raw_text):
    """
    Parse raw text into warn_mistake v1 JSON.
    Deterministic — no model call.
    """
    text = raw_text.strip()
    if not text:
        return {
            "v": PROTOCOL_VERSION,
            "intent": "unknown",
            "target": None,
            "confidence": 0.0,
            "warn": True,
            "raw": raw_text,
        }

    # Parse intent
    intent, intent_conf = _match_intent(text)

    # Parse target
    target, target_bonus = _match_target(text)

    # Combine confidence
    # Intent is primary signal; target adds a small bonus
    confidence = min(intent_conf + target_bonus, 1.0) if intent != "unknown" else 0.0

    # If intent is unknown but target matched, treat as action command (intent=on)
    # e.g. "take a photo", "roll over", "do a dance", "follow me"
    # Single bare words (e.g. "bark") get lower confidence → hold/confirm
    if intent == "unknown" and target is not None:
        intent = "on"
        word_count = len(text.split())
        if word_count <= 1:
            # Single word command — less certain, hold for confirm
            confidence = 0.65
        else:
            confidence = min(0.82 + target_bonus, 1.0)  # multi-word = more confident

    # Apply warn flag based on confidence bands
    warn = confidence < CONF_EXECUTE

    return {
        "v": PROTOCOL_VERSION,
        "intent": intent,
        "target": target,
        "confidence": round(confidence, 2),
        "warn": warn,
        "raw": raw_text,
    }


def route_command(parsed):
    """
    Route a parsed command based on confidence bands.
    Returns decision dict.

    conf >= 0.80 → execute
    0.50–0.79   → hold/confirm
    < 0.50      → reject (unknown)
    """
    conf = parsed["confidence"]
    intent = parsed["intent"]

    if conf >= CONF_EXECUTE:
        return {
            "action": "execute",
            "intent": intent,
            "target": parsed["target"],
            "confidence": conf,
            "reason": f"confidence {conf} >= {CONF_EXECUTE}",
            "warn": False,
        }
    elif conf >= CONF_WARN:
        return {
            "action": "hold",
            "intent": intent,
            "target": parsed["target"],
            "confidence": conf,
            "reason": f"confidence {conf} in warn band [{CONF_WARN}–{CONF_EXECUTE})",
            "warn": True,
        }
    else:
        return {
            "action": "reject",
            "intent": "unknown",
            "target": parsed["target"],
            "confidence": conf,
            "reason": f"confidence {conf} < {CONF_WARN}",
            "warn": True,
        }


def parse_and_route(raw_text):
    """Convenience: parse + route in one call."""
    parsed = parse_command(raw_text)
    decision = route_command(parsed)
    return parsed, decision


# ─── Test Suite ───
if __name__ == "__main__":
    tests = [
        # (input, expected_intent, expected_action)
        ("turn on the garage light", "on", "execute"),
        ("start guard mode", "on", "execute"),
        ("activate patrol", "on", "execute"),
        ("come here", "on", "execute"),
        ("stop", "off", "execute"),
        ("turn off the heater", "off", "execute"),
        ("go to sleep", "off", "execute"),
        ("cancel", "cancel", "execute"),
        ("wait no cancel", "cancel", "execute"),
        ("never mind", "cancel", "execute"),
        ("what's your status", "status", "execute"),
        ("how are you", "status", "execute"),
        ("what are you doing", "status", "execute"),
        ("report", "status", "execute"),
        ("lights?", "status", "hold"),
        ("help", "status", "hold"),
        ("go", "on", "hold"),
        ("chill", "off", "hold"),
        ("um", "unknown", "reject"),
        ("asdfghjkl", "unknown", "reject"),
        ("take a photo", "on", "execute"),
        ("do a dance", "on", "execute"),
        ("shake my hand", "on", "execute"),
        ("roll over", "on", "execute"),
        ("bark", "on", "hold"),
        ("what do you see", "status", "execute"),
        ("follow me", "on", "execute"),
        ("sit down", "off", "execute"),
    ]

    print("🐕 warn_mistake v1 — Intent Parser Test Suite\n")
    print(f"{'INPUT':<30} {'INTENT':<10} {'TARGET':<18} {'CONF':<6} {'WARN':<5} {'ACTION':<10}")
    print("─" * 90)

    passed = 0
    failed = 0

    for raw, exp_intent, exp_action in tests:
        parsed = parse_command(raw)
        decision = route_command(parsed)

        p_str = json.dumps(parsed, separators=(',', ':'))
        d_str = json.dumps(decision, separators=(',', ':'))

        status = "✅" if (parsed["intent"] == exp_intent and decision["action"] == exp_action) else "❌"
        if status == "✅":
            passed += 1
        else:
            failed += 1

        print(f"{raw:<30} {parsed['intent']:<10} {str(parsed['target']):<18} "
              f"{parsed['confidence']:<6} {str(parsed['warn']):<5} {decision['action']:<10} {status}")

    print(f"\n{'─' * 90}")
    print(f"Results: {passed} passed, {failed} failed out of {len(tests)}")

    # Show protocol examples from spec
    print("\n📋 Protocol Spec Examples:\n")
    spec_examples = [
        "turn on the garage light",
        "lights?",
        "wait no cancel",
    ]
    for ex in spec_examples:
        parsed = parse_command(ex)
        print(f'  "{ex}" → {json.dumps(parsed, separators=(", ", ": "))}')