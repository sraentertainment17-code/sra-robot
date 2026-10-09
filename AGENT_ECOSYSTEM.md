# 🤖 SRA Robot Dog — Agent Ecosystem

## Architecture: 4 Agents + 1 Monitor

```
┌─────────────────────────────────────────────────────────┐
│                    YOUR PHONE (Telegram)                 │
│                                                         │
│  @your_hermes_bot    @your_robot_bot      @your_debug_bot │
│  (Mac mini brain)   (Robot brain)        (Robot health)  │
└──────┬──────────────────┬──────────────────┬────────────┘
       │                  │                  │
       │     Wi-Fi        │                  │
       ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  MAC MINI    │  │  PI 5 ROBOT  │  │  PI 5 DEBUG  │
│              │  │              │  │              │
│ Agent 1:     │  │ Agent 2:     │  │ Agent 3:     │
│ Build Helper │  │ Robot Brain  │  │ Debug Monitor│
│ (Hermes)     │  │ (Hermes)     │  │ (Daemon)     │
│              │  │              │  │              │
│ Agent 4:     │  │ - Whisper    │  │ - Log watcher│
│ Assembly     │  │ - GLM-5.2    │  │ - Crash detect│
│ Checker      │  │ - Edge TTS   │  │ - Health check│
│ (warn_mistake│  │ - 12 servos  │  │ - Auto-restart│
│  skill)      │  │ - Camera     │  │ - Alert bot   │
│              │  │ - Training   │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

## The 4 Agents

### Agent 1: Build Helper (Mac mini — Hermes default profile)
- **Where:** Your Mac mini (already running)
- **What:** Helps you write code, research parts, debug software
- **Telegram:** @your_hermes_bot (existing)
- **Role:** "Help me write the motor control code" / "Research PiDog API"

### Agent 2: Robot Brain (Pi 5 — Hermes robot profile)
- **Where:** Raspberry Pi 5 on the robot
- **What:** The actual robot intelligence — hears, thinks, speaks, moves
- **Telegram:** @your_robot_bot (new — create via @BotFather)
- **Role:** Voice conversation + movement + camera + training

### Agent 3: Debug Monitor (Pi 5 — background daemon)
- **Where:** Raspberry Pi 5 (runs alongside Agent 2)
- **What:** Watches for crashes, logs errors, auto-restarts, alerts you
- **Telegram:** @your_debug_bot (new — create via @BotFather)
- **Role:** "Robot brain crashed at 3AM — restarted, here's the error log"

### Agent 4: Assembly Checker (Mac mini or Pi 5 — warn_mistake skill)
- **Where:** Either machine (loads warn_mistake skill)
- **What:** Checks electronics polarity during assembly
- **Telegram:** Uses whichever bot you're talking to
- **Role:** "Is this capacitor backwards?" → JSON safety check → hard warn

## Communication Flow

```
You (Telegram) → @your_robot_bot → Agent 2 (Robot Brain)
  → Whisper hears you
  → warn_mistake parses command
  → GLM-5.2 thinks
  → Robot moves/speaks
  → Agent 3 (Debug) watches silently
  → If crash → @your_debug_bot alerts you
  → You can ask @your_hermes_bot to help fix it
```