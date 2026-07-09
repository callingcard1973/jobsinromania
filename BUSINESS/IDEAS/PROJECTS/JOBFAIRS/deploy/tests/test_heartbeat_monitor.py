"""Tests for HeartbeatMonitor — 8 cases."""
import time
from datetime import datetime, timedelta
from nanoclaw_core import HeartbeatMonitor


def test_beat_creates_file(tmp_hb_dir):
    hb = HeartbeatMonitor(tmp_hb_dir)
    hb.beat("test")
    assert (tmp_hb_dir / "test.heartbeat").exists()


def test_beat_updates_timestamp(tmp_hb_dir):
    hb = HeartbeatMonitor(tmp_hb_dir)
    hb.beat("ts")
    t1 = hb.last_beat("ts")
    time.sleep(0.05)
    hb.beat("ts")
    t2 = hb.last_beat("ts")
    assert t2 > t1


def test_last_beat_none_when_missing(tmp_hb_dir):
    hb = HeartbeatMonitor(tmp_hb_dir)
    assert hb.last_beat("unknown") is None


def test_last_beat_parses_correctly(tmp_hb_dir):
    hb = HeartbeatMonitor(tmp_hb_dir)
    hb.beat("parse")
    result = hb.last_beat("parse")
    assert isinstance(result, datetime)
    assert (datetime.now() - result).total_seconds() < 2


def test_is_alive_true_fresh(tmp_hb_dir):
    hb = HeartbeatMonitor(tmp_hb_dir)
    hb.beat("fresh")
    assert hb.is_alive("fresh", max_age_seconds=300) is True


def test_is_alive_false_stale(tmp_hb_dir):
    hb = HeartbeatMonitor(tmp_hb_dir)
    old_time = (datetime.now() - timedelta(seconds=400)).isoformat()
    (tmp_hb_dir / "stale.heartbeat").write_text(old_time)
    assert hb.is_alive("stale", max_age_seconds=300) is False


def test_is_alive_false_missing(tmp_hb_dir):
    hb = HeartbeatMonitor(tmp_hb_dir)
    assert hb.is_alive("ghost") is False


def test_is_alive_corrupt_file(tmp_hb_dir):
    hb = HeartbeatMonitor(tmp_hb_dir)
    (tmp_hb_dir / "corrupt.heartbeat").write_text("not a date")
    assert hb.last_beat("corrupt") is None
    assert hb.is_alive("corrupt") is False
