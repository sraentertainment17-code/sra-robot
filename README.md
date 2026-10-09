# 🤖 SRA Robot — AI Companion Robot

**A personal AI robot you can build for ~$65. No 3D printer. No soldering. No OpenAI subscription.**

SRA Robot is a voice AI companion: it hears you (Whisper), thinks (GLM via Ollama Cloud — free), and talks back (Edge TTS). The ESP32-S3 is the thin body; your own machine running [Hermes Agent](https://github.com/NousResearch/hermes-agent) is the big brain.

Built by [Sut Ring Aung](https://github.com/sraentertainment17-code) · v2.0

## ✨ What It Does

- 🎤 **Hears you** — INMP441 I2S mic + Whisper speech-to-text (local)
- 🧠 **Thinks** — GLM-5.2 via Ollama Cloud (free tier, no OpenAI needed)
- 🗣️ **Talks** — MAX98357 amp + speaker, Edge TTS voice (Andrew voice)
- 👀 **Sees** *(coming)* — Pi Camera face detection via OpenCV
- 🐕 **Moves** *(coming)* — SunFounder PiDog body, 12 servos
- 💛 **Has a soul** — 4 swappable personalities: Guard Dog / Playful Puppy / Smart Assistant / Sassy Companion
- 🎓 **Learns** — reward-based behavior training ("good boy" system)
- 📱 **Reachable** — Telegram bots for robot control + health alerts

## 🧰 Hardware (~$65)

| Part | Qty | ~Price |
|------|-----|--------|
| Hosyond ESP32-S3 N16R8 dev board | 1 (of 3-pack) | $19 |
| AITRIP INMP441 I2S MEMS microphone | 1 (of 5-pack) | $12 |
| MAX98357 I2S amplifier | 1 (of 2-pack) | $7 |
| 4Ω 3W speaker | 1 (of 4-pack) | $10 |
| ELEGOO jumper wires 120pc | 1 pack | $7 |
| ELEGOO breadboards (830+400pt) | 1 pack | $9 |

**Why ESP32-S3 N16R8?** The 8MB PSRAM is required for audio buffering + wake-word. The S3's two I2S buses run mic and speaker simultaneously. Community-proven reference combo for voice assistants.

## 📐 Wiring

Full illustrated guide: `esp32/BUILD_GUIDE.html` (open in any browser)

**Mic (INMP441) → I2S0:**
| Mic pin | ESP32-S3 |
|---------|----------|
| VDD | 3V3 (⚠️ 3.3V only — 5V kills it) |
| GND | GND |
| L/R | GND (left-channel mode) |
| SCK | GPIO4 |
| WS | GPIO5 |
| SD | GPIO6 |

**Amp (MAX98357) → I2S1:**
| Amp pin | ESP32-S3 |
|---------|----------|
| VIN | 5V |
| GND | GND |
| BCLK | GPIO15 |
| LRC | GPIO16 |
| DIN | GPIO7 |
| SD | (unconnected — default gain) |

## 🚀 Quick Start

```bash
git clone https://github.com/sraentertainment17-code/sra-robot.git
cd sra-robot
./install.sh
python3 robot_brain.py
```

Set your LLM endpoint in `config.json` (reads the key from your Hermes config or `OLLAMA_API_KEY` env var — never hard-coded).

## 📁 Repo Structure

```
├── robot_brain.py      ← main loop: hear → think → speak
├── brain.py            ← LLM calls (GLM via Ollama Cloud)
├── personality.py      ← 4 swappable personalities
├── training.py         ← reward-based learning
├── behavior_log.json   ← what the robot learned
├── motors.py           ← movement (L298N, PiDog later)
├── vision.py           ← camera + face detection
├── debug_bot.py        ← Telegram health bot
├── debug_monitor.py    ← watchdog + auto-restart
├── systemd_services.py ← run as a service
├── warn_mistake.py     ← assembly mistake checker
├── esp32/              ← ESP32-S3 voice-body sketches
│   ├── BUILD_GUIDE.html
│   └── step1_hello/
├── install.sh
└── BUILD_PLAN.md       ← full build guide (PiDog phase included)
```

## 🗺️ Roadmap

- [x] Brain: hear → think → speak pipeline
- [x] Personality system
- [x] Behavior training (rewards)
- [x] Health monitoring + Telegram bots
- [ ] ESP32-S3 voice body (parts arrived, assembly in progress)
- [ ] Vision: face detection + follow-me
- [ ] PiDog body: walk, tricks, patrol
- [ ] Publish + share

## 📜 License

MIT — free for everyone. Built with ❤️ + Hermes Agent.

*Brain first. Body later. Build the future.* 🤖