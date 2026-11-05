"""Smoke tests for the tray module's paths and helpers."""

from pathlib import Path

import stt.tray as tray


def test_daemon_path_points_into_repo():
    repo = Path(tray._REPO_ROOT)
    assert tray._STT_DAEMON == repo / "stt" / "daemon.py"


def test_daemon_file_exists():
    assert tray._STT_DAEMON.exists()


def test_no_injector_references():
    src = Path(tray.__file__).read_text()
    assert "session_injector" not in src
    assert "lib/" not in src


def test_controls_not_open_by_default():
    assert tray._stt_controls_alive() is False


def test_module_docstring_documents_menu():
    assert "STT Controls" in (tray.__doc__ or "")
