"""Tests for LockManager — 15 cases."""
import os
from pathlib import Path
from nanoclaw_core import LockManager


def test_acquire_new_lock(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    assert lm.acquire("test1") is True
    assert (tmp_lock_dir / "test1.lock").exists()
    lm.release("test1")


def test_acquire_writes_pid(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    lm.acquire("test2")
    content = (tmp_lock_dir / "test2.lock").read_text().strip()
    assert content == str(os.getpid())
    lm.release("test2")


def test_acquire_already_locked(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    assert lm.acquire("dup") is True
    lm2 = LockManager(tmp_lock_dir)
    assert lm2.acquire("dup") is False
    lm.release("dup")


def test_release_removes_file(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    lm.acquire("rel")
    lm.release("rel")
    assert not (tmp_lock_dir / "rel.lock").exists()


def test_release_unknown_name_silent(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    lm.release("nonexistent")  # should not raise


def test_is_locked_false_when_no_file(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    assert lm.is_locked("nope") is False


def test_is_locked_true_when_held(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    lm.acquire("held")
    lm2 = LockManager(tmp_lock_dir)
    assert lm2.is_locked("held") is True
    lm.release("held")


def test_is_locked_false_after_release(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    lm.acquire("temp")
    lm.release("temp")
    assert lm.is_locked("temp") is False


def test_get_lock_holder_returns_pid(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    lm.acquire("pid_test")
    assert lm.get_lock_holder("pid_test") == os.getpid()
    lm.release("pid_test")


def test_get_lock_holder_none_on_missing(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    assert lm.get_lock_holder("missing") is None


def test_cleanup_stale_removes_dead_pid(tmp_lock_dir):
    lf = tmp_lock_dir / "dead.lock"
    lf.write_text("99999999")  # PID that doesn't exist
    lm = LockManager(tmp_lock_dir)
    lm.cleanup_stale()
    assert not lf.exists()


def test_cleanup_stale_keeps_live_pid(tmp_lock_dir):
    lf = tmp_lock_dir / "alive.lock"
    lf.write_text(str(os.getpid()))
    lm = LockManager(tmp_lock_dir)
    lm.cleanup_stale()
    assert lf.exists()


def test_cleanup_stale_handles_invalid_content(tmp_lock_dir):
    lf = tmp_lock_dir / "bad.lock"
    lf.write_text("notanumber")
    lm = LockManager(tmp_lock_dir)
    lm.cleanup_stale()
    assert not lf.exists()


def test_multiple_locks_independent(tmp_lock_dir):
    lm = LockManager(tmp_lock_dir)
    assert lm.acquire("a") is True
    assert lm.acquire("b") is True
    lm.release("a")
    assert lm.is_locked("b") is True
    lm.release("b")


def test_lock_dir_created_if_missing(tmp_path):
    new_dir = tmp_path / "new_locks"
    lm = LockManager(new_dir)
    assert new_dir.exists()
