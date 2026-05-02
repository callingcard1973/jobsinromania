#!/usr/bin/env python3
"""
Shared utilities for Claude Content Skills
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Optional


def save_json(data: Any, path: Path, indent: int = 2) -> None:
    """Save data to JSON file"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=indent, ensure_ascii=False, default=str)


def load_json(path: Path) -> Any:
    """Load data from JSON file"""
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def file_hash(path: Path) -> str:
    """Calculate MD5 hash of file content"""
    with open(path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def timestamp() -> str:
    """Get current ISO timestamp"""
    return datetime.now().isoformat()


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length with suffix"""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists, create if needed"""
    path.mkdir(parents=True, exist_ok=True)
    return path


class ProgressTracker:
    """Track progress for resumable operations"""

    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state: dict[str, Any] = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Load state from file"""
        if self.state_file.exists():
            return load_json(self.state_file)
        return {
            "started_at": None,
            "last_updated": None,
            "completed": [],
            "failed": [],
            "pending": [],
            "current": None,
            "metadata": {}
        }

    def save(self) -> None:
        """Save current state to file"""
        self.state["last_updated"] = timestamp()
        ensure_dir(self.state_file.parent)
        save_json(self.state, self.state_file)

    def start(self, items: list[str]) -> None:
        """Start tracking a new batch of items"""
        self.state["started_at"] = timestamp()
        self.state["pending"] = items
        self.state["completed"] = []
        self.state["failed"] = []
        self.state["current"] = None
        self.save()

    def mark_current(self, item: str) -> None:
        """Mark item as currently being processed"""
        self.state["current"] = item
        if item in self.state["pending"]:
            self.state["pending"].remove(item)
        self.save()

    def mark_completed(self, item: str) -> None:
        """Mark item as completed"""
        if item not in self.state["completed"]:
            self.state["completed"].append(item)
        self.state["current"] = None
        self.save()

    def mark_failed(self, item: str, error: Optional[str] = None) -> None:
        """Mark item as failed"""
        self.state["failed"].append({
            "item": item,
            "error": error,
            "timestamp": timestamp()
        })
        self.state["current"] = None
        self.save()

    def get_remaining(self) -> list[str]:
        """Get list of items still pending"""
        remaining = self.state["pending"].copy()
        if self.state["current"]:
            remaining.insert(0, self.state["current"])
        return remaining

    def is_complete(self) -> bool:
        """Check if all items are processed"""
        return len(self.state["pending"]) == 0 and self.state["current"] is None

    def get_stats(self) -> dict[str, int]:
        """Get progress statistics"""
        return {
            "completed": len(self.state["completed"]),
            "failed": len(self.state["failed"]),
            "pending": len(self.state["pending"]),
            "current": 1 if self.state["current"] else 0
        }

    def reset(self) -> None:
        """Reset all progress"""
        self.state = {
            "started_at": None,
            "last_updated": None,
            "completed": [],
            "failed": [],
            "pending": [],
            "current": None,
            "metadata": {}
        }
        self.save()
