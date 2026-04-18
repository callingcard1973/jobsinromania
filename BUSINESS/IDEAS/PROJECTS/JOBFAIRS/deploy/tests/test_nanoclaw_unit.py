"""Tests for NanoClaw class — 15 cases."""
import os
import json
from datetime import datetime, date
from unittest.mock import MagicMock, patch
from pathlib import Path

import nanoclaw_core as core


def _make_nano(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "LOCK_DIR", tmp_path / "locks")
    monkeypatch.setattr(core, "HEARTBEAT_DIR", tmp_path / "hb")
    monkeypatch.setattr(core, "LOG_DIR", tmp_path / "logs")
    monkeypatch.setattr(core, "GOVERNOR_DIR", tmp_path / "gov")
    monkeypatch.setattr(core, "SCRAPER_LOG_DIR", tmp_path / "scrlogs")
    monkeypatch.setattr(core, "NANOCLAW_STATE", tmp_path / "state.json")
    (tmp_path / "locks").mkdir()
    (tmp_path / "hb").mkdir()
    (tmp_path / "logs").mkdir()
    (tmp_path / "gov").mkdir()
    (tmp_path / "scrlogs").mkdir()
    from nanoclaw import NanoClaw
    return NanoClaw()


def test_init_creates_dirs(tmp_path, monkeypatch):
    nano = _make_nano(tmp_path, monkeypatch)
    assert nano.running is True
    assert (tmp_path / "locks").exists()


def test_send_telegram_false_no_token(tmp_path, monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    nano = _make_nano(tmp_path, monkeypatch)
    assert nano.send_telegram("test") is False


def test_send_telegram_posts_payload(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    nano = _make_nano(tmp_path, monkeypatch)
    with patch("nanoclaw.requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        result = nano.send_telegram("hello", "error")
        assert result is True
        call_json = mock_post.call_args[1]["json"]
        assert call_json["chat_id"] == "123"
        assert "hello" in call_json["text"]


def test_send_telegram_false_on_exception(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    nano = _make_nano(tmp_path, monkeypatch)
    with patch("nanoclaw.requests.post", side_effect=ConnectionError):
        assert nano.send_telegram("fail") is False


def test_send_telegram_false_on_http_error(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    nano = _make_nano(tmp_path, monkeypatch)
    with patch("nanoclaw.requests.post") as m:
        m.return_value = MagicMock(status_code=401)
        assert nano.send_telegram("bad token") is False


def test_diagnose_error_returns_response(tmp_path, monkeypatch):
    nano = _make_nano(tmp_path, monkeypatch)
    with patch("nanoclaw.requests.post") as m:
        m.return_value = MagicMock(status_code=200)
        m.return_value.json.return_value = {"response": "Connection timeout to API"}
        result = nano.diagnose_error("Traceback\nConnectionError: timeout")
        assert "Connection" in result


def test_diagnose_error_fallback_on_timeout(tmp_path, monkeypatch):
    nano = _make_nano(tmp_path, monkeypatch)
    with patch("nanoclaw.requests.post", side_effect=TimeoutError):
        result = nano.diagnose_error("some error")
        assert result == "Check logs manually."


def test_diagnose_error_no_chr10_literal(tmp_path, monkeypatch):
    nano = _make_nano(tmp_path, monkeypatch)
    with patch("nanoclaw.requests.post") as m:
        m.return_value = MagicMock(status_code=200)
        m.return_value.json.return_value = {"response": "ok"}
        nano.diagnose_error("line1\nline2\nline3")
        prompt = m.call_args[1]["json"]["prompt"]
        assert "chr(10)" not in prompt


def test_morning_digest_not_at_wrong_hour(tmp_path, monkeypatch):
    nano = _make_nano(tmp_path, monkeypatch)
    with patch("nanoclaw.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15, 10, 0)
        with patch("nanoclaw.requests.post") as m:
            nano.morning_digest()
            m.assert_not_called()


def test_morning_digest_sends_at_7(tmp_path, monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "123")
    nano = _make_nano(tmp_path, monkeypatch)
    with patch("nanoclaw.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15, 7, 0)
        with patch("nanoclaw.monitor_ted_data") as ted:
            ted.return_value = {"total_winners": 100, "files": {"2025": {}}, "issues": [], "healthy": True}
            with patch("nanoclaw.get_running_scrapers", return_value=[]):
                with patch("nanoclaw.requests.post") as m:
                    m.return_value = MagicMock(status_code=200)
                    m.return_value.json.return_value = {"response": "All OK"}
                    nano.morning_digest()
                    assert m.called


def test_morning_digest_once_per_day(tmp_path, monkeypatch):
    nano = _make_nano(tmp_path, monkeypatch)
    nano._digest_sent_today = date(2026, 4, 15)
    with patch("nanoclaw.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15, 7, 0)
        with patch("nanoclaw.requests.post") as m:
            nano.morning_digest()
            m.assert_not_called()


def test_write_state_valid_json(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    nano = _make_nano(tmp_path, monkeypatch)
    import nanoclaw
    monkeypatch.setattr(nanoclaw, "NANOCLAW_STATE", state_file)
    with patch("nanoclaw.monitor_ted_data") as ted:
        ted.return_value = {"total_winners": 0, "files": {}, "issues": [], "healthy": True}
        with patch("nanoclaw.get_running_scrapers", return_value=[]):
            with patch("nanoclaw.is_campaign_window", return_value=False):
                with patch("nanoclaw.is_system_healthy", return_value=True):
                    nano.write_state()
    state = json.loads(state_file.read_text())
    assert "timestamp" in state
    assert "running_scrapers" in state


def test_write_state_atomic(tmp_path, monkeypatch):
    state_file = tmp_path / "state.json"
    nano = _make_nano(tmp_path, monkeypatch)
    import nanoclaw
    monkeypatch.setattr(nanoclaw, "NANOCLAW_STATE", state_file)
    with patch("nanoclaw.monitor_ted_data") as ted:
        ted.return_value = {"total_winners": 0, "files": {}, "issues": [], "healthy": True}
        with patch("nanoclaw.get_running_scrapers", return_value=[]):
            with patch("nanoclaw.is_campaign_window", return_value=False):
                with patch("nanoclaw.is_system_healthy", return_value=True):
                    nano.write_state()
    assert not (tmp_path / "state.tmp").exists()
    assert state_file.exists()


def test_handle_signal_stops(tmp_path, monkeypatch):
    nano = _make_nano(tmp_path, monkeypatch)
    nano._handle_signal(15, None)
    assert nano.running is False
