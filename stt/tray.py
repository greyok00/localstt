#!/usr/bin/env python3
"""Standalone STT system tray.

Supervises the STT daemon (stt.daemon) as a pystray icon; a headless
stdin keeper runs when pystray is unavailable. Quitting the tray stops
the daemon and ends dictation; nothing else depends on it.

Menu:
  1. STT          - disabled header
  2. STT Controls - open/close the control popup (label reflects state)
  3. Quit         - stops the STT daemon and this tray
"""

from __future__ import annotations

import importlib
import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

if sys.platform == "linux":
    os.environ.setdefault("PYSTRAY_BACKEND", "gtk")

from stt.config import CFG  # noqa: E402

CYAN, GREEN, YELLOW, RED, DIM, RST = (
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
    "\033[2m",
    "\033[0m",
)
if not sys.stderr.isatty():
    CYAN = GREEN = YELLOW = RED = DIM = RST = ""

_STT_DAEMON = _REPO_ROOT / "stt" / "daemon.py"

_LABEL_OPEN = "Open STT Controls"
_LABEL_CLOSE = "Close STT Controls"

_ICON = None


def _log(msg: str, emoji: str = "", color: str = "") -> None:
    print(f"{color}{emoji} {DIM}stt-tray{RST} {msg}{RST}", file=sys.stderr, flush=True)


def _daemon_alive() -> bool:
    """Check the daemon state file, then fall back to a process-name scan."""
    pid_file = CFG.state_dir / "stt_daemon.json"
    if pid_file.exists():
        try:
            pid = int(json.loads(pid_file.read_text()).get("pid", 0))
            os.kill(pid, 0)
            return True
        except (ValueError, ProcessLookupError, OSError):
            pass
    try:
        r = subprocess.run(
            ["pgrep", "-f", "stt/daemon.py"], capture_output=True, text=True, timeout=2
        )
        return bool((r.stdout or "").strip())
    except Exception:
        return False


def _daemon_start() -> bool:
    """Launch the daemon as a detached process; report whether it came up."""
    if _daemon_alive():
        return True
    _log("starting STT daemon…", "🔄", CYAN)
    subprocess.Popen(
        [sys.executable, "-u", str(_STT_DAEMON)],
        cwd=str(_REPO_ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(20):
        if _daemon_alive():
            _log("STT daemon up", "✅", GREEN)
            return True
        time.sleep(0.5)
    _log("STT daemon failed to start", "❌", RED)
    return False


def _daemon_stop() -> bool:
    """Stop the daemon via its control command; pkill as a last resort."""
    if not _daemon_alive():
        return True
    _log("stopping STT daemon…", "🛑", YELLOW)
    subprocess.run([sys.executable, str(_STT_DAEMON), "stop"], capture_output=True, timeout=30)
    for _ in range(20):
        if not _daemon_alive():
            _log("STT daemon stopped", "✅", GREEN)
            return True
        time.sleep(0.5)
    # Last resort: kill by process pattern.
    subprocess.run(["pkill", "-f", "stt/daemon.py"], capture_output=True, timeout=5)
    return not _daemon_alive()


def _stt_controls_alive() -> bool:
    """Check whether the in-process controls window exists."""
    try:
        import stt.controls as sc

        return sc._is_open()
    except Exception:
        return False


def _open_stt_controls() -> None:
    import stt.controls as sc

    sc = importlib.reload(sc)
    sc.open_in_thread()


def _close_stt_controls() -> bool:
    import stt.controls as sc

    sc = importlib.reload(sc)
    return sc.close()


def _make_icon_image():
    from PIL import Image, ImageDraw  # type: ignore

    img = Image.new("RGBA", (64, 64), (15, 17, 21, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, 58, 58], radius=12, fill=(150, 220, 255, 255))
    # Mic glyph
    d.rounded_rectangle([26, 14, 38, 36], radius=6, fill=(15, 17, 21, 255))
    d.rectangle([20, 32, 44, 36], outline=(15, 17, 21, 255), width=2)
    d.line([32, 38, 32, 50], fill=(15, 17, 21, 255), width=3)
    d.line([24, 50, 40, 50], fill=(15, 17, 21, 255), width=3)
    return img


def _run_gui(quit_event: threading.Event) -> None:
    import pystray  # type: ignore
    from pystray import MenuItem as MI, Menu  # type: ignore

    def _toast(icon, msg, kind="info"):
        try:
            icon.notify(msg, "LocalSTT")
        except Exception:
            pass
        _log(msg, "ℹ️", CYAN if kind == "info" else (GREEN if kind == "ok" else RED))

    def _stt_label_text(_item) -> str:
        return _LABEL_CLOSE if _stt_controls_alive() else _LABEL_OPEN

    def on_stt_controls(icon, item):
        try:
            if _stt_controls_alive():
                _close_stt_controls()
                _toast(icon, "STT controls closed", "ok")
            else:
                _open_stt_controls()
                _toast(icon, "STT controls opened", "ok")
        except Exception as e:
            _toast(icon, f"Failed to toggle STT controls: {e}", "info")
        try:
            icon.update_menu()
        except Exception:
            pass

    def on_quit(icon, item):
        _log("Quit — stopping STT daemon", "🛑", YELLOW)
        quit_event.set()
        try:
            icon.stop()
        except Exception:
            pass
        try:
            _close_stt_controls()
        except Exception:
            pass
        try:
            _daemon_stop()
        except Exception:
            pass

    menu = Menu(
        MI("STT", None, enabled=False),
        Menu.SEPARATOR,
        MI(_stt_label_text, on_stt_controls),
        Menu.SEPARATOR,
        MI("Quit", on_quit),
    )
    icon = pystray.Icon("localstt", _make_icon_image(), "LocalSTT", menu)
    global _ICON
    _ICON = icon
    _log("STT tray running — close it via Quit to stop the STT daemon", "🟢", GREEN)

    def _refresh_tick():
        try:
            icon.update_menu()
        except Exception:
            pass
        t = threading.Timer(3.0, _refresh_tick)
        t.daemon = True
        t.start()

    _refresh_tick()

    icon.run()


def _run_headless(quit_event: threading.Event) -> None:
    print(f"{DIM}stt-tray — headless mode. keys: q=quit, s=status{RST}")
    while not quit_event.is_set():
        try:
            line = sys.stdin.readline()
        except KeyboardInterrupt:
            break
        if not line:
            time.sleep(0.5)
            continue
        key = line.strip().lower()[:1]
        if key == "q":
            break
        if key == "s":
            print(f"daemon alive: {_daemon_alive()} | controls alive: {_stt_controls_alive()}")


def run() -> int:
    """Start the daemon, then run the GUI tray (or headless keeper) until quit.

    Stops the daemon on exit, whether quit came from the menu or a signal.
    """
    quit_event = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: quit_event.set())
    signal.signal(signal.SIGTERM, lambda *_: quit_event.set())

    _daemon_start()

    try:
        _log("pystray found — starting GUI tray", "🖥️", CYAN)
        _run_gui(quit_event)
    except Exception as e:
        _log(f"GUI tray unavailable ({e}) — headless keeper", "⚠️", YELLOW)
        _run_headless(quit_event)

    if _daemon_alive():
        _daemon_stop()
    _log("stt tray exited", "✅", GREEN)
    return 0


def main() -> int:
    return run()


if __name__ == "__main__":
    sys.exit(main())
