"""Shared fixtures for NanoClaw tests."""
import os
import sys
import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

import nanoclaw_core as core
import nanoclaw_monitors as mon


@pytest.fixture
def tmp_lock_dir(tmp_path, monkeypatch):
    d = tmp_path / "locks"
    d.mkdir()
    monkeypatch.setattr(core, "LOCK_DIR", d)
    return d


@pytest.fixture
def tmp_hb_dir(tmp_path, monkeypatch):
    d = tmp_path / "heartbeats"
    d.mkdir()
    monkeypatch.setattr(core, "HEARTBEAT_DIR", d)
    return d


@pytest.fixture
def tmp_governor_state(tmp_path, monkeypatch):
    f = tmp_path / "governor_state.json"
    monkeypatch.setattr(core, "GOVERNOR_STATE", f)
    monkeypatch.setattr(mon, "GOVERNOR_STATE", f)
    return f


@pytest.fixture
def tmp_nanoclaw_state(tmp_path, monkeypatch):
    f = tmp_path / "nanoclaw_state.json"
    monkeypatch.setattr(core, "NANOCLAW_STATE", f)
    return f


@pytest.fixture
def tmp_scraper_log_dir(tmp_path, monkeypatch):
    d = tmp_path / "scrapers"
    d.mkdir()
    monkeypatch.setattr(core, "SCRAPER_LOG_DIR", d)
    monkeypatch.setattr(mon, "SCRAPER_LOG_DIR", d)
    return d


@pytest.fixture
def tmp_ted_dir(tmp_path, monkeypatch):
    d = tmp_path / "ted"
    d.mkdir()
    monkeypatch.setattr(mon, "TED_CSV_DIR", d)
    # Create 2 fake CSVs
    for year in ["2024", "2025"]:
        f = d / f"ted_winners_{year}.csv"
        f.write_text("col1,col2\nrow1,data\nrow2,data\n")
    return d


@pytest.fixture
def locks(tmp_lock_dir):
    return core.LockManager(tmp_lock_dir)


@pytest.fixture
def hb(tmp_hb_dir):
    return core.HeartbeatMonitor(tmp_hb_dir)


@pytest.fixture
def mock_telegram():
    with patch("nanoclaw.requests.post") as m:
        resp = MagicMock()
        resp.status_code = 200
        m.return_value = resp
        yield m
