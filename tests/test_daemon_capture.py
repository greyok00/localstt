"""Hermetic tests for the daemon's capture paths (no mic, no audio stack).

sounddevice is replaced with a fake module that hands vad_capture canned
blocks, so the VAD/hotkey interplay can be exercised on any machine.
"""

import os
import sys
import threading
import types

import numpy as np
import pytest

import stt.daemon as daemon
from stt.daemon import HotkeyListener

BLOCK = 1600  # 0.1 s at 16 kHz, matching vad_capture's default block


@pytest.fixture(autouse=True)
def quiet_cfg(monkeypatch):
    """Pin the VAD knobs so a host ~/.stt/stt.conf can't skew the thresholds."""
    monkeypatch.setattr("stt.config.CFG.stt_vad_threshold", 0.05)
    monkeypatch.setattr("stt.config.CFG.stt_vad_silence_sec", 1.5)
    monkeypatch.setattr("stt.config.CFG.stt_vad_max_utterance_sec", 10.0)
    monkeypatch.setattr("stt.config.CFG.stt_mic_device", "")


def _speech_block(amp=0.3):
    return amp * np.sin(np.linspace(0, 400, BLOCK, endpoint=False)).astype("float32").reshape(-1, 1)


def _silence_block():
    return np.zeros((BLOCK, 1), dtype="float32")


def _fake_sd(blocks, stop_event):
    """Fake sounddevice whose InputStream replays ``blocks`` then signals stop."""

    class _FakeStream:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self, n):
            if blocks:
                return blocks.pop(0), n
            stop_event.set()
            return _silence_block(), n

    return types.SimpleNamespace(InputStream=lambda **kw: _FakeStream())


def _run_vad(monkeypatch, blocks, clips):
    stop_event = threading.Event()
    monkeypatch.setitem(sys.modules, "sounddevice", _fake_sd(blocks, stop_event))
    done = threading.Event()

    def runner():
        daemon.vad_capture(clips.append, stop_event=stop_event)
        done.set()

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    assert done.wait(timeout=10), "vad_capture did not exit"
    t.join(timeout=1)


def test_vad_delivers_clip_when_hotkey_idle(monkeypatch):
    blocks = [_speech_block(), _speech_block()] + [_silence_block() for _ in range(15)]
    clips = []
    _run_vad(monkeypatch, blocks, clips)
    assert len(clips) == 1
    assert clips[0].size >= int(16000 * 0.3)


def test_vad_skips_blocks_while_hotkey_recording(monkeypatch):
    # Speech during a hotkey hold must not also become a VAD clip ("both"
    # mode would otherwise transcribe and type every utterance twice).
    monkeypatch.setattr(daemon, "_hotkey_recording", threading.Event())
    daemon._hotkey_recording.set()
    blocks = [_speech_block(), _speech_block()] + [_silence_block() for _ in range(15)]
    clips = []
    try:
        _run_vad(monkeypatch, blocks, clips)
        assert clips == []
    finally:
        daemon._hotkey_recording.clear()


def test_abort_hotkey_recording_resets_state(monkeypatch):
    closed = []

    class _FakeStream:
        def stop(self):
            closed.append("stop")

        def close(self):
            closed.append("close")

    monkeypatch.setattr(daemon, "_recorder", {"stream": _FakeStream(), "frames": [_silence_block()]})
    monkeypatch.setattr(daemon, "_hotkey_recording", threading.Event())
    daemon._hotkey_recording.set()
    listener = HotkeyListener({"<ctrl>"}, on_start=lambda: None, on_stop=lambda: None)
    listener.active = True
    listener.pressed = {"<ctrl>"}
    monkeypatch.setattr(daemon, "_hotkey_listener", listener)

    daemon._abort_hotkey_recording()

    assert closed == ["stop", "close"]
    assert daemon._recorder["stream"] is None
    assert daemon._recorder["frames"] == []
    assert not daemon._hotkey_recording.is_set()
    assert listener.active is False
    assert listener.pressed == set()


def test_headless_quit_on_q(monkeypatch):
    import stt.tray as tray

    r, w = os.pipe()
    monkeypatch.setattr(sys, "stdin", os.fdopen(r, "r"))
    os.write(w, b"q\n")
    done = threading.Event()

    def runner():
        tray._run_headless(done)
        done.set()

    t = threading.Thread(target=runner, daemon=True)
    t.start()
    assert done.wait(timeout=10), "headless keeper did not exit on 'q'"
    t.join(timeout=1)
    os.close(w)
    sys.stdin.close()
