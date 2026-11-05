"""Tests for the standalone config loader (env vars + INI file)."""

import importlib

import pytest


@pytest.fixture()
def fresh_cfg(monkeypatch, tmp_path):
    """Reload stt.config with a clean environment and a private conf/state dir."""
    for name in [n for n in __import__("os").environ if n.startswith("STT_")]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("STT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("STT_CONF", str(tmp_path / "stt.conf"))
    import stt.config

    return importlib.reload(stt.config)


def test_defaults(fresh_cfg):
    cfg = fresh_cfg.CFG
    assert cfg.stt_model == "base"
    assert cfg.stt_device == "cuda"
    assert cfg.stt_hotkey == "<ctrl>+<shift>+space"
    assert cfg.stt_vad_threshold == 0.05
    assert cfg.stt_cleanup is False
    assert cfg.big_model_port == 11599


def test_env_wins(fresh_cfg, monkeypatch):
    monkeypatch.setenv("STT_MODEL", "small")
    monkeypatch.setenv("STT_CLEANUP", "1")
    cfg = fresh_cfg.Config()
    assert cfg.stt_model == "small"
    assert cfg.stt_cleanup is True


def test_ini_file_wins_over_defaults(monkeypatch, fresh_cfg):
    conf = fresh_cfg.CONF_PATH
    conf.parent.mkdir(parents=True, exist_ok=True)
    conf.write_text("[stt]\nmodel = medium\nvad_threshold = 0.3\n")
    cfg = fresh_cfg.Config()
    assert cfg.stt_model == "medium"
    assert cfg.stt_vad_threshold == 0.3


def test_bad_values_fall_back(fresh_cfg, monkeypatch):
    monkeypatch.setenv("STT_VAD_THRESHOLD", "not-a-number")
    monkeypatch.setenv("STT_BIG_MODEL_PORT", "1.9")
    cfg = fresh_cfg.Config()
    assert cfg.stt_vad_threshold == 0.05
    assert cfg.big_model_port == 1  # int(float("1.9"))
