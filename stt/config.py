"""Standalone config for the STT app.

Every setting is an env var; a small INI at ~/.stt/stt.conf ([stt] section)
overrides defaults, env wins over the file. Defaults match the app's
historical behavior.
"""

from __future__ import annotations

import configparser
import os
from pathlib import Path

CONF_PATH = Path(os.environ.get("STT_CONF", str(Path.home() / ".stt" / "stt.conf")))


def _load_conf() -> configparser.ConfigParser:
    cp = configparser.ConfigParser()
    if CONF_PATH.exists():
        cp.read(CONF_PATH)
    return cp


def _env(name: str, conf_key: str, default: str) -> str:
    cp = _load_conf()
    return os.environ.get(name) or cp.get("stt", conf_key, fallback=default)


def _env_bool(name: str, conf_key: str, default: bool) -> bool:
    raw = os.environ.get(name) or _load_conf().get("stt", conf_key, fallback="")
    if raw == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def _env_float(name: str, conf_key: str, default: float) -> float:
    raw = os.environ.get(name) or _load_conf().get("stt", conf_key, fallback="")
    try:
        return float(raw)
    except ValueError:
        return default


def _env_int(name: str, conf_key: str, default: int) -> int:
    raw = os.environ.get(name) or _load_conf().get("stt", conf_key, fallback="")
    try:
        return int(float(raw))
    except ValueError:
        return default


class Config:
    def __init__(self) -> None:
        self.state_dir = Path(
            _env("STT_STATE_DIR", "state_dir", str(Path.home() / ".stt" / "state"))
        )

        self.stt_model = _env("STT_MODEL", "model", "base")
        self.stt_device = _env("STT_DEVICE", "device", "cuda")
        self.stt_mic_device = _env("STT_MIC", "mic_device", "")
        self.stt_hotkey = _env("STT_HOTKEY", "hotkey", "<ctrl>+<shift>+space")
        self.stt_speak_to_capture = _env_bool("STT_SPEAK", "speak_to_capture", True)
        self.stt_vad_threshold = _env_float("STT_VAD_THRESHOLD", "vad_threshold", 0.05)
        self.stt_vad_silence_sec = _env_float("STT_VAD_SILENCE", "vad_silence_sec", 1.5)
        self.stt_vad_max_utterance_sec = _env_float(
            "STT_VAD_MAX_UTTERANCE", "vad_max_utterance_sec", 10.0
        )

        self.stt_cleanup = _env_bool("STT_CLEANUP", "cleanup", False)
        self.stt_cleanup_target = _env("STT_CLEANUP_TARGET", "cleanup_target", "big")
        self.stt_cleanup_max_sentences = _env_int(
            "STT_CLEANUP_MAX_SENTENCES", "cleanup_max_sentences", 4
        )

        # optional cleanup pass sends text to a local llama.cpp server
        self.big_model_port = _env_int("STT_BIG_MODEL_PORT", "big_model_port", 11599)


CFG = Config()
