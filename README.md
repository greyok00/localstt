<div align="center">

# localstt

**Local voice dictation: press to record, release to transcribe.**

Hold a hotkey — or simply speak in VAD mode — and your words are typed into whatever window has focus. Recording and transcription both run on your own GPU through [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

[![Version](https://img.shields.io/badge/version-0.1.1-2f6f5e)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-22C55E)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-2563EB)](pyproject.toml)
[![Platform](https://img.shields.io/badge/platform-Linux%20X11-1a1a2e)](#requirements)
[![CI](https://github.com/greyok00/localstt/actions/workflows/ci.yml/badge.svg)](https://github.com/greyok00/localstt/actions)

[Overview](#overview) · [Quick start](#quick-start) · [Usage](#usage) · [Configuration](#configuration) · [Privacy](#privacy) · [License](#license)

</div>

---

## Overview

localstt is a small local dictation daemon for Linux. It records the
microphone, runs faster-whisper on the machine, and types the transcript into
the focused window through `xdotool`. Audio never leaves the machine.

It has two capture modes, which can be combined:

- **Hotkey** — hold `<ctrl>+<shift>+space` and release to transcribe.
- **VAD** — the daemon transcribes automatically when you stop talking.

There is also a mouse-only control popup and an optional tray icon. No cloud,
no account, no API key, no telemetry.

## Pieces

| Piece | Source | What it does |
|---|---|---|
| Daemon | `stt/daemon.py` | Records the mic, runs faster-whisper, types text via `xdotool` |
| Controls popup | `stt/controls.py` | Mouse-only Start/Stop and Enter window; no hotkey needed |
| Tray | `stt/tray.py` | Optional pystray icon that supervises the daemon; headless fallback without pystray |

## Requirements

- Linux with X11. Typing into the focused window uses `xdotool`.
- Python 3.10 or newer.
- An NVIDIA GPU is recommended. A CPU works but is slower.
- Whisper model weights are downloaded from their upstream host on first use.

## Quick start

```bash
sudo apt install xdotool          # typing backend
pip install localstt             # or: pip install -e .
pip install "localstt[tray]"     # optional: tray icon
stt-daemon start
stt-controls                      # open the control popup
```

The popup starts the daemon when it needs one. A systemd user unit
(`stt.service`) is included if the tray should start with your session.

### Quick check

```bash
stt-daemon status
python3 -m stt.daemon --test
```

## Usage

| Command | Effect |
|---|---|
| `stt-daemon start` | Start the daemon in the background |
| `python3 -m stt.daemon set-mode hotkey` | Set mode: `hotkey`, `vad`, `both` or `off` |
| `python3 -m stt.daemon --test` | Record two seconds and transcribe, without typing |
| `python3 -m stt.daemon status` | Print daemon state |

The popup is mouse-only: **TOGGLE STT** switches voice-activity capture, and
**ENTER** types a committed transcript into the focused window.

## Configuration

Defaults work out of the box. Override any setting with an environment variable
or a small INI file at `~/.stt/stt.conf` in the `[stt]` section; the environment
wins.

| Setting | Environment | Default |
|---|---|---|
| Whisper model | `STT_MODEL` | `base` |
| Device | `STT_DEVICE` | `cuda` |
| Hotkey | `STT_HOTKEY` | `<ctrl>+<shift>+space` |
| VAD threshold | `STT_VAD_THRESHOLD` | `0.05` |
| Silence limit | `STT_VAD_SILENCE` | `1.5` |
| Maximum utterance | `STT_VAD_MAX_UTTERANCE` | `10.0` |
| Cleanup pass | `STT_CLEANUP` | off |
| Cleanup server port | `STT_BIG_MODEL_PORT` | `11599` |
| State directory | `STT_STATE_DIR` | `~/.stt/state` |

The optional cleanup pass polishes a transcript through a llama.cpp server you
run yourself, still on `127.0.0.1`, and remains off by default.

## Privacy

Recording, transcription and typing are local by construction. The only
network use is the optional cleanup pass, which talks to `127.0.0.1` and
nothing else. Whisper model weights are downloaded from their upstream host on
first use.

## Development

```bash
python3 -m pytest
ruff check .
```

Built with AI assistance and verified by tests and CI. Third-party
components are covered by the notices in [LICENSE](LICENSE).

## License

Apache-2.0. See [LICENSE](LICENSE).
