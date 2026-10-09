#!/usr/bin/env python3
"""
SRA Robot Dog — Behavior Training System
========================================
Teach your robot dog through rewards and corrections.

The robot remembers which behaviors get praised ("good boy")
and which get corrected ("no"). Over time, it prefers behaviors
with higher reward scores.

Usage:
    from training import BehaviorTrainer

    trainer = BehaviorTrainer()

    # Robot does a trick
    trainer.record_behavior("dance")

    # You say "good boy!"
    trainer.reward("dance", "good boy")

    # You say "no, stop"
    trainer.correct("dance", "no")

    # Robot decides what trick to do next (prefers rewarded ones)
    best_trick = trainer.get_best_behavior()
"""

import json
import os
from datetime import datetime
from collections import defaultdict

BEHAVIOR_LOG_PATH = os.path.expanduser("~/ai-robot/behavior_log.json")


class BehaviorTrainer:
    """Reward-based learning for the robot dog."""

    REWARD_WORDS = ["good boy", "good girl", "good dog", "yes", "nice",
                    "great", "well done", "love it", "amazing", "perfect"]
    CORRECTION_WORDS = ["no", "stop", "bad", "bad dog", "nope", "don't",
                        "wrong", "cut it out", "stop that"]

    def __init__(self):
        self.log = self._load_log()
        self.scores = self._calculate_scores()

    def _load_log(self):
        """Load behavior log from disk."""
        if os.path.exists(BEHAVIOR_LOG_PATH):
            try:
                with open(BEHAVIOR_LOG_PATH) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return []
        return []

    def _save_log(self):
        """Save behavior log to disk."""
        os.makedirs(os.path.dirname(BEHAVIOR_LOG_PATH), exist_ok=True)
        with open(BEHAVIOR_LOG_PATH, 'w') as f:
            json.dump(self.log, f, indent=2)

    def record_behavior(self, action, context=None):
        """Record that the robot performed an action."""
        entry = {
            "action": action,
            "context": context,
            "reward": None,
            "timestamp": datetime.now().isoformat()
        }
        self.log.append(entry)
        self._save_log()

    def reward(self, action, reward_text="good boy"):
        """Mark the last occurrence of an action as rewarded."""
        for entry in reversed(self.log):
            if entry["action"] == action and entry["reward"] is None:
                entry["reward"] = reward_text
                break
        self._save_log()
        self.scores = self._calculate_scores()

    def correct(self, action, correction_text="no"):
        """Mark the last occurrence of an action as corrected."""
        for entry in reversed(self.log):
            if entry["action"] == action and entry["reward"] is None:
                entry["reward"] = correction_text
                break
        self._save_log()
        self.scores = self._calculate_scores()

    def detect_reward_from_speech(self, text):
        """Check if user's speech is a reward or correction.
        Returns: 'reward', 'correction', or None
        """
        text_lower = text.lower().strip()

        for word in self.REWARD_WORDS:
            if word in text_lower:
                return "reward"

        for word in self.CORRECTION_WORDS:
            if word in text_lower:
                return "correction"

        return None

    def _calculate_scores(self):
        """Calculate reward score for each action."""
        scores = defaultdict(int)
        for entry in self.log:
            action = entry["action"]
            reward = entry["reward"]

            if reward is None:
                continue

            # Check if it's a reward or correction
            reward_lower = reward.lower()
            is_reward = any(w in reward_lower for w in self.REWARD_WORDS)
            is_correction = any(w in reward_lower for w in self.CORRECTION_WORDS)

            if is_reward:
                scores[action] += 1
            elif is_correction:
                scores[action] -= 1

        return dict(scores)

    def get_best_behavior(self):
        """Return the action with the highest reward score."""
        if not self.scores:
            return None
        return max(self.scores, key=self.scores.get)

    def get_worst_behavior(self):
        """Return the action with the lowest score (most corrected)."""
        if not self.scores:
            return None
        return min(self.scores, key=self.scores.get)

    def should_do_action(self, action_name):
        """Check if an action should be performed (score >= 0)."""
        return self.scores.get(action_name, 0) >= 0

    def get_stats(self):
        """Return training statistics."""
        total = len(self.log)
        rewarded = sum(1 for e in self.log if e["reward"] and
                       any(w in e["reward"].lower() for w in self.REWARD_WORDS))
        corrected = sum(1 for e in self.log if e["reward"] and
                        any(w in e["reward"].lower() for w in self.CORRECTION_WORDS))

        return {
            "total_actions": total,
            "rewarded": rewarded,
            "corrected": corrected,
            "success_rate": f"{(rewarded / total * 100):.0f}%" if total > 0 else "N/A",
            "best_behavior": self.get_best_behavior(),
            "worst_behavior": self.get_worst_behavior(),
            "scores": self.scores,
        }

    def reset(self):
        """Clear all training data."""
        self.log = []
        self.scores = {}
        self._save_log()

    def __str__(self):
        stats = self.get_stats()
        return (f"BehaviorTrainer: {stats['total_actions']} actions, "
                f"{stats['rewarded']} rewarded, {stats['corrected']} corrected, "
                f"best: {stats['best_behavior']}")


if __name__ == "__main__":
    # Test the training system
    print("🐕 SRA Robot Dog — Behavior Training System\n")

    trainer = BehaviorTrainer()

    # Simulate training session
    print("=== Simulating Training Session ===\n")

    # Robot does tricks
    trainer.record_behavior("dance")
    trainer.record_behavior("dance")
    trainer.reward("dance", "good boy")
    trainer.reward("dance", "good boy")

    trainer.record_behavior("bark")
    trainer.correct("bark", "no")

    trainer.record_behavior("roll_over")
    trainer.reward("roll_over", "nice")

    trainer.record_behavior("jump")
    trainer.correct("jump", "stop that")

    # Show results
    stats = trainer.get_stats()
    print(f"Total actions:  {stats['total_actions']}")
    print(f"Rewarded:       {stats['rewarded']}")
    print(f"Corrected:      {stats['corrected']}")
    print(f"Success rate:   {stats['success_rate']}")
    print(f"Best behavior:  {stats['best_behavior']}")
    print(f"Worst behavior: {stats['worst_behavior']}")
    print(f"\nScores: {json.dumps(stats['scores'], indent=2)}")

    # Test speech detection
    print("\n=== Speech Detection ===\n")
    test_phrases = [
        "Good boy!",
        "No, stop that",
        "Nice trick",
        "Bad dog",
        "What time is it?",
        "I love it when you dance",
        "Cut it out",
    ]
    for phrase in test_phrases:
        result = trainer.detect_reward_from_speech(phrase)
        print(f"  '{phrase}' → {result or 'neutral'}")

    print(f"\n{trainer}")