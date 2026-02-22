#!/usr/bin/env python3
"""
Pre-session check — Run before starting Claude Code work.

Checks:
  1. CLAUDE.md compliance (≤50 lines, ≤1500 tokens)
  2. Plugin state summary
  3. Resets token monitor counter

Usage:
  python auto_init.py                # Full check + reset counter
  python auto_init.py --check-only   # Check without changes
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")
CLAUDE_MD = Path("D:\\MEMORY\\CLAUDE.md")
COUNTER_FILE = LOG_DIR / "tool_count.json"
SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
CONTEXT_PROFILES = Path.home() / ".claude" / "context-profiles.json"
MEMORY_DIR = Path.home() / ".claude" / "projects" / "D--MEMORY" / "memory"


def check_claude_md():
    if not CLAUDE_MD.exists():
        print("[SKIP] CLAUDE.md not found")
        return
    content = CLAUDE_MD.read_text(encoding='utf-8', errors='ignore')
    lines = len(content.splitlines())
    tokens = len(content) // 4
    status = "[OK]" if lines <= 50 and tokens <= 1500 else "[BLOAT]"
    print(f"  {status} CLAUDE.md: {lines} lines, ~{tokens} tokens")


def check_plugins():
    if not SETTINGS_PATH.exists():
        print("  [SKIP] No settings.json")
        return
    try:
        settings = json.loads(SETTINGS_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        print("  [ERROR] Can't read settings.json")
        return
    disabled = set(settings.get("disabled_mcp_servers", []))
    print(f"  Playwright: {'OFF' if 'mcp__plugin_playwright_playwright' in disabled else 'ON'}")
    print(f"  Simplifier: {'OFF' if 'superpowers:code-simplifier' in disabled else 'ON'}")


def load_context_profile():
    """Load context profile from env or config file"""
    if not CONTEXT_PROFILES.exists():
        return None
    try:
        profiles = json.loads(CONTEXT_PROFILES.read_text())
        profile_name = os.getenv("CLAUDE_CONTEXT_PROFILE", "default")
        profile = profiles.get(profile_name, profiles.get("default"))
        if profile:
            context_files = profile.get("context_files", [])
            print(f"  [PROFILE] {profile_name}: {len(context_files)} context file(s)")
            for cf in context_files:
                file_path = MEMORY_DIR / cf.replace("memory/", "")
                if file_path.exists():
                    size = len(file_path.read_text())
                    print(f"    ✓ {cf} ({size} bytes)")
    except (json.JSONDecodeError, OSError):
        pass


def reset_counter():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    data = {"calls": 0, "started": datetime.now().isoformat()}
    COUNTER_FILE.write_text(json.dumps(data))
    print("  [RESET] Tool call counter")


def log_init():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"init_{datetime.now().strftime('%Y%m%d')}.jsonl"
    entry = {"timestamp": datetime.now().isoformat(), "event": "init"}
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def main():
    check_only = "--check-only" in sys.argv
    print("\n[PRE-SESSION CHECK]")
    check_claude_md()
    check_plugins()
    load_context_profile()
    if not check_only:
        reset_counter()
        log_init()
    print()


if __name__ == '__main__':
    main()
