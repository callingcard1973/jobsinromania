"""Tests for nanoclaw_monitors — 20 cases."""
import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch
import nanoclaw_core as core
import nanoclaw_monitors as mon


def test_check_governor_returns_dict(tmp_governor_state):
    tmp_governor_state.write_text(json.dumps({"health": {"all_healthy": True}}))
    assert mon.check_governor()["health"]["all_healthy"] is True


def test_check_governor_fallback_missing(tmp_governor_state):
    result = mon.check_governor()
    assert result["health"]["all_healthy"] is True


def test_check_governor_fallback_corrupt(tmp_governor_state):
    tmp_governor_state.write_text("{bad json")
    result = mon.check_governor()
    assert result["health"]["all_healthy"] is True


def test_is_system_healthy_true_default(tmp_governor_state):
    assert mon.is_system_healthy() is True


def test_is_system_healthy_false(tmp_governor_state):
    tmp_governor_state.write_text(json.dumps({"health": {"all_healthy": False}}))
    assert mon.is_system_healthy() is False


def test_is_campaign_window_false_default(tmp_governor_state):
    assert mon.is_campaign_window() is False


def test_is_campaign_window_true(tmp_governor_state):
    tmp_governor_state.write_text(json.dumps({"health": {"in_campaign_window": True}}))
    assert mon.is_campaign_window() is True


def test_get_running_scrapers_empty(locks):
    assert mon.get_running_scrapers(locks) == []


def test_get_running_scrapers_detects(locks):
    locks.acquire("scraper_uk")
    result = mon.get_running_scrapers(locks)
    assert "uk" in result
    locks.release("scraper_uk")


def test_monitor_tasks_detects_new(locks, tmp_scraper_log_dir):
    locks.acquire("scraper_uk")
    tasks = {}
    mon.monitor_running_tasks(locks, tasks, MagicMock(), lambda x: x, lambda m, l: None)
    assert "uk" in tasks
    assert tasks["uk"].status == "running"
    locks.release("scraper_uk")


def test_monitor_tasks_completes(locks, tmp_scraper_log_dir):
    locks.acquire("scraper_uk")
    tasks = {}
    mon.monitor_running_tasks(locks, tasks, MagicMock(), lambda x: x, lambda m, l: None)
    locks.release("scraper_uk")
    mon.monitor_running_tasks(locks, tasks, MagicMock(), lambda x: x, lambda m, l: None)
    assert tasks["uk"].status == "completed"


def test_monitor_tasks_fails_on_error(locks, tmp_scraper_log_dir):
    locks.acquire("scraper_uk")
    tasks = {}
    logger = MagicMock()
    diagnose = MagicMock(return_value="Connection timeout")
    alert = MagicMock()
    mon.monitor_running_tasks(locks, tasks, logger, diagnose, alert)
    locks.release("scraper_uk")
    today = datetime.now().strftime("%Y%m%d")
    log = tmp_scraper_log_dir / f"uk_{today}.log"
    log.write_text("Starting scraper\nTraceback (most recent call last):\nConnectionError: timeout")
    mon.monitor_running_tasks(locks, tasks, logger, diagnose, alert)
    assert tasks["uk"].status == "failed"
    diagnose.assert_called_once()
    alert.assert_called_once()


def test_monitor_tasks_clean_log(locks, tmp_scraper_log_dir):
    locks.acquire("scraper_uk")
    tasks = {}
    mon.monitor_running_tasks(locks, tasks, MagicMock(), lambda x: x, lambda m, l: None)
    locks.release("scraper_uk")
    today = datetime.now().strftime("%Y%m%d")
    (tmp_scraper_log_dir / f"uk_{today}.log").write_text("Scraper completed successfully")
    mon.monitor_running_tasks(locks, tasks, MagicMock(), lambda x: x, lambda m, l: None)
    assert tasks["uk"].status == "completed"


def test_missed_no_alert_before_window(locks, tmp_governor_state):
    alert = MagicMock()
    alerted = set()
    with patch("nanoclaw_monitors.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15, 0, 30)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        mon.check_missed_scrapers(locks, {}, MagicMock(), alert, alerted)
    alert.assert_not_called()


def test_missed_alerts_after_window(locks, tmp_governor_state):
    alert = MagicMock()
    alerted = set()
    with patch("nanoclaw_monitors.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15, 1, 30)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        mon.check_missed_scrapers(locks, {}, MagicMock(), alert, alerted)
    assert alert.called
    assert "uk" in alerted


def test_missed_no_double_alert(locks, tmp_governor_state):
    alert = MagicMock()
    alerted = {"uk"}
    with patch("nanoclaw_monitors.datetime") as mock_dt:
        mock_dt.now.return_value = datetime(2026, 4, 15, 1, 30)
        mock_dt.side_effect = lambda *a, **kw: datetime(*a, **kw)
        mon.check_missed_scrapers(locks, {}, MagicMock(), alert, alerted)
    alert.assert_not_called()


def test_ted_healthy(tmp_ted_dir):
    result = mon.monitor_ted_data()
    assert result["healthy"] is True
    assert result["total_winners"] == 4  # 2 files x 2 rows each


def test_ted_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(mon, "TED_CSV_DIR", tmp_path / "nonexistent")
    result = mon.monitor_ted_data()
    assert result["healthy"] is False


def test_ted_empty_csv(tmp_ted_dir):
    (tmp_ted_dir / "ted_winners_2026.csv").write_text("header\n")
    result = mon.monitor_ted_data()
    assert any("empty" in i for i in result["issues"])


def test_disk_alert(monkeypatch):
    mock_usage = MagicMock()
    mock_usage.used = 66
    mock_usage.total = 100
    monkeypatch.setattr("nanoclaw_monitors.shutil.disk_usage", lambda p: mock_usage)
    pct, alerted, msg = mon.check_disk(False)
    assert msg is not None
    assert "66%" in msg
    _, alerted2, msg2 = mon.check_disk(True)
    assert msg2 is None
