"""Integration tests — require Ollama running on localhost:11434."""
import pytest
import requests
from unittest.mock import patch, MagicMock


@pytest.mark.slow
def test_ollama_responds():
    r = requests.post("http://127.0.0.1:11434/api/generate",
        json={"model": "qwen2.5:1.5b", "prompt": "Reply OK", "stream": False},
        timeout=30)
    assert r.status_code == 200
    assert len(r.json()["response"]) > 0


@pytest.mark.slow
def test_diagnose_error_real(tmp_path, monkeypatch):
    import nanoclaw_core as core
    monkeypatch.setattr(core, "LOCK_DIR", tmp_path / "l")
    monkeypatch.setattr(core, "HEARTBEAT_DIR", tmp_path / "h")
    monkeypatch.setattr(core, "LOG_DIR", tmp_path / "lo")
    monkeypatch.setattr(core, "GOVERNOR_DIR", tmp_path / "g")
    monkeypatch.setattr(core, "SCRAPER_LOG_DIR", tmp_path / "s")
    monkeypatch.setattr(core, "NANOCLAW_STATE", tmp_path / "st.json")
    for d in ["l", "h", "lo", "g", "s"]:
        (tmp_path / d).mkdir()
    from nanoclaw import NanoClaw
    nano = NanoClaw()
    error_log = """2026-04-15 03:00:01 Starting uk scraper
2026-04-15 03:00:05 Fetching page 1
Traceback (most recent call last):
  File "uk_scraper.py", line 45, in fetch
    resp = requests.get(url, timeout=10)
requests.exceptions.ConnectionError: Connection refused
"""
    result = nano.diagnose_error(error_log)
    assert isinstance(result, str)
    assert len(result) > 10
    assert len(result) <= 300
    assert "chr(10)" not in result


@pytest.mark.slow
def test_morning_digest_real_ollama(tmp_path, monkeypatch):
    import nanoclaw_core as core
    monkeypatch.setattr(core, "LOCK_DIR", tmp_path / "l")
    monkeypatch.setattr(core, "HEARTBEAT_DIR", tmp_path / "h")
    monkeypatch.setattr(core, "LOG_DIR", tmp_path / "lo")
    monkeypatch.setattr(core, "GOVERNOR_DIR", tmp_path / "g")
    monkeypatch.setattr(core, "SCRAPER_LOG_DIR", tmp_path / "s")
    monkeypatch.setattr(core, "NANOCLAW_STATE", tmp_path / "st.json")
    for d in ["l", "h", "lo", "g", "s"]:
        (tmp_path / d).mkdir()
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    from nanoclaw import NanoClaw
    from datetime import datetime
    nano = NanoClaw()
    with patch("nanoclaw.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15, 7, 0)
        with patch("nanoclaw.monitor_ted_data") as ted:
            ted.return_value = {"total_winners": 2198358, "files": {"2024": {}, "2025": {}}, "issues": [], "healthy": True}
            with patch("nanoclaw.get_running_scrapers", return_value=[]):
                with patch("nanoclaw.requests.post") as mock_post:
                    # First call = Ollama (let it go through real)
                    # Second call = Telegram (mock it)
                    real_post = requests.post
                    def side_effect(*args, **kwargs):
                        if "11434" in str(args):
                            return real_post(*args, **kwargs)
                        resp = MagicMock(status_code=200)
                        return resp
                    mock_post.side_effect = side_effect
                    nano.morning_digest()
                    assert mock_post.called
