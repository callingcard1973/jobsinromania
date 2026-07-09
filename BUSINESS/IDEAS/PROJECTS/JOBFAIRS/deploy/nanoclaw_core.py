#!/usr/bin/env python3
"""NanoClaw Core — Lock management, heartbeats, task status, constants."""
import os
import fcntl
import time
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Set
from enum import Enum

# Paths
GOVERNOR_DIR = Path("/opt/ACTIVE/INFRA/GOVERNOR")
GOVERNOR_STATE = GOVERNOR_DIR / "governor_state.json"
NANOCLAW_STATE = GOVERNOR_DIR / "nanoclaw_state.json"
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS")
LOCK_DIR = Path("/tmp/interjob_locks")
SCRAPER_LOG_DIR = LOG_DIR / "scrapers"
HEARTBEAT_DIR = Path("/tmp/interjob_heartbeats")
TED_CSV_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_TENDERS/CSV")
TED_WINNER_PATTERN = "ted_winners_*.csv"
TED_STALE_DAYS = 90
OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_FAST_MODEL = "qwen2.5:1.5b"
OLLAMA_SMART_MODEL = "qwen3-4b"

SCRAPER_SCHEDULE = {
    "uk": "00:00", "anofm": "03:00", "denmark": "02:05",
    "sweden": "03:10", "finland": "04:15", "norway": "05:00",
    "iceland": "05:30", "bulgaria": "06:00", "eures": "22:00",
}
CAMPAIGN_WINDOWS = ["08:40", "12:40", "16:40"]
MISS_TOLERANCE_MINUTES = 60
DISK_WARN_PCT = 65
DISK_CLEAR_PCT = 60


class Priority(Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class TaskStatus:
    name: str
    status: str
    started: Optional[str]
    finished: Optional[str]
    pid: Optional[int]
    lock_file: Optional[str]
    retries: int
    last_error: Optional[str]


class LockManager:
    def __init__(self, lock_dir: Path):
        self.lock_dir = lock_dir
        self.lock_dir.mkdir(parents=True, exist_ok=True)
        self.held_locks: Dict[str, int] = {}

    def acquire(self, name: str, timeout: int = 0) -> bool:
        lock_file = self.lock_dir / f"{name}.lock"
        try:
            fd = os.open(str(lock_file), os.O_RDWR | os.O_CREAT)
            if timeout == 0:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            else:
                deadline = time.time() + timeout
                while True:
                    try:
                        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.time() >= deadline:
                            os.close(fd)
                            return False
                        time.sleep(1)
            os.ftruncate(fd, 0)
            os.write(fd, f"{os.getpid()}\n".encode())
            self.held_locks[name] = fd
            return True
        except BlockingIOError:
            try:
                os.close(fd)
            except Exception:
                pass
            return False
        except Exception:
            return False

    def release(self, name: str):
        if name in self.held_locks:
            try:
                fd = self.held_locks.pop(name)
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                (self.lock_dir / f"{name}.lock").unlink(missing_ok=True)
            except Exception:
                pass

    def is_locked(self, name: str) -> bool:
        lock_file = self.lock_dir / f"{name}.lock"
        if not lock_file.exists():
            return False
        try:
            fd = os.open(str(lock_file), os.O_RDONLY)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            return False
        except BlockingIOError:
            return True
        except Exception:
            return False

    def get_lock_holder(self, name: str) -> Optional[int]:
        lock_file = self.lock_dir / f"{name}.lock"
        try:
            if lock_file.exists():
                content = lock_file.read_text().strip()
                return int(content) if content else None
        except Exception:
            pass
        return None

    def cleanup_stale(self):
        for lock_file in self.lock_dir.glob("*.lock"):
            try:
                pid = int(lock_file.read_text().strip())
                os.kill(pid, 0)
            except (ValueError, ProcessLookupError, PermissionError):
                lock_file.unlink(missing_ok=True)
            except Exception:
                pass


class HeartbeatMonitor:
    def __init__(self, heartbeat_dir: Path):
        self.dir = heartbeat_dir
        self.dir.mkdir(parents=True, exist_ok=True)

    def beat(self, name: str):
        (self.dir / f"{name}.heartbeat").write_text(datetime.now().isoformat())

    def last_beat(self, name: str) -> Optional[datetime]:
        hb_file = self.dir / f"{name}.heartbeat"
        if hb_file.exists():
            try:
                return datetime.fromisoformat(hb_file.read_text().strip())
            except Exception:
                pass
        return None

    def is_alive(self, name: str, max_age_seconds: int = 300) -> bool:
        last = self.last_beat(name)
        if last is None:
            return False
        return (datetime.now() - last).total_seconds() <= max_age_seconds
