#!/usr/bin/env python3
"""
Token Monitor — Estimate session token usage from log data.

Usage:
  python token_monitor.py              # Show current session estimate
  python token_monitor.py --reset      # Reset tool call counter
"""

import json
import sys
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")
COUNTER_FILE = LOG_DIR / "tool_count.json"

# Rough estimates per tool call (input + output tokens)
TOKENS_PER_TOOL_CALL = 1200  # average across Read/Edit/Bash/Grep
CONTEXT_WINDOW = 200000      # Claude's context window


def load_counter():
    if COUNTER_FILE.exists():
        try:
            with open(COUNTER_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"calls": 0, "started": datetime.now().isoformat()}


def save_counter(data):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(COUNTER_FILE, 'w') as f:
        json.dump(data, f)


def main():
    if "--reset" in sys.argv:
        save_counter({"calls": 0, "started": datetime.now().isoformat()})
        print("[RESET] Tool call counter zeroed")
        return

    data = load_counter()
    calls = data["calls"]
    started = data.get("started", "unknown")
    estimated_tokens = calls * TOKENS_PER_TOOL_CALL
    fill_pct = min(100, round(100 * estimated_tokens / CONTEXT_WINDOW, 1))

    print(f"\n[SESSION ESTIMATE]")
    print(f"  Tool calls:      {calls}")
    print(f"  Est. tokens:     ~{estimated_tokens:,}")
    print(f"  Context fill:    ~{fill_pct}%")
    print(f"  Started:         {started}")

    if fill_pct >= 90:
        print(f"\n  [CRITICAL] Run /clear or restart NOW")
    elif fill_pct >= 75:
        print(f"\n  [WARNING] Run /compact soon")
    elif fill_pct >= 50:
        print(f"\n  [INFO] Consider /compact")
    else:
        print(f"\n  [OK] Context usage normal")


if __name__ == '__main__':
    main()
