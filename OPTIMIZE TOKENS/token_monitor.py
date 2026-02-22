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
WEIGHTS_FILE = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\tool_weights.json")

# Default estimate per tool call (used if weights file not found)
TOKENS_PER_TOOL_CALL = 1200  # average across Read/Edit/Bash/Grep
CONTEXT_WINDOW = 200000      # Claude's context window
TOOL_WEIGHTS = {}            # Loaded from tool_weights.json


def load_tool_weights():
    """Load tool-specific token weights"""
    if WEIGHTS_FILE.exists():
        try:
            with open(WEIGHTS_FILE, 'r') as f:
                data = json.load(f)
                return data.get("tool_weights", {})
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def load_counter():
    if COUNTER_FILE.exists():
        try:
            with open(COUNTER_FILE, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {"calls": 0, "started": datetime.now().isoformat(), "breakdown": {}}


def save_counter(data):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(COUNTER_FILE, 'w') as f:
        json.dump(data, f)


def main():
    if "--reset" in sys.argv:
        save_counter({"calls": 0, "started": datetime.now().isoformat(), "breakdown": {}})
        print("[RESET] Tool call counter zeroed")
        return

    global TOOL_WEIGHTS
    TOOL_WEIGHTS = load_tool_weights()

    data = load_counter()
    calls = data.get("calls", 0)
    started = data.get("started", "unknown")
    breakdown = data.get("breakdown", {})

    # Calculate estimated tokens with tool-specific weights
    estimated_tokens = 0
    for tool, count in breakdown.items():
        weight = TOOL_WEIGHTS.get(tool, TOKENS_PER_TOOL_CALL)
        estimated_tokens += count * weight

    # If no breakdown, use flat estimate
    if not breakdown and calls > 0:
        estimated_tokens = calls * TOKENS_PER_TOOL_CALL

    # Add baseline context costs (MEMORY.md, plugins, etc.)
    baseline = 2300  # From tool_weights.json baseline

    total_estimated = estimated_tokens + baseline
    fill_pct = min(100, round(100 * total_estimated / CONTEXT_WINDOW, 1))

    print(f"\n[SESSION ESTIMATE]")
    print(f"  Tool calls:      {calls}")
    print(f"  Est. tokens:     ~{estimated_tokens:,} (tools) + {baseline} (baseline)")
    print(f"  Total:           ~{total_estimated:,}")
    print(f"  Context fill:    ~{fill_pct}%")
    print(f"  Started:         {started}")

    if breakdown:
        print(f"\n[TOOL BREAKDOWN]")
        for tool, count in sorted(breakdown.items(), key=lambda x: x[1], reverse=True):
            weight = TOOL_WEIGHTS.get(tool, TOKENS_PER_TOOL_CALL)
            tool_tokens = count * weight
            print(f"  {tool:20s} {count:3d} calls × {weight:5d} = {tool_tokens:6,d} tokens")

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
