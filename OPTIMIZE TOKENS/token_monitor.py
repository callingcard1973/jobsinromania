#!/usr/bin/env python3
"""
Token Monitor Hook - Real-time context usage monitoring for Claude Code.

This script monitors context consumption and warns at usage thresholds:
  - 50%: Warning - start planning to /clear or /compact
  - 75%: Strong warning - consider /compact now
  - 90%: Critical - immediately /clear or restart

Installation:
  Add to ~/.claude/settings.json in "hooks" section:

  "hooks": {
    "PostToolUse": {
      "command": "python D:\\\\MEMORY\\\\OPTIMIZE TOKENS\\\\token_monitor.py"
    }
  }

The hook receives context via stdin with tool execution metadata.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")

def log_event(level, message, metadata=None):
    """Log monitoring event."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    log_file = LOG_DIR / f"monitor_{datetime.now().strftime('%Y%m%d')}.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "metadata": metadata or {}
    }

    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')

    # Print to stderr for user visibility
    if level in ["warning", "critical"]:
        print(f"[{level.upper()}] {message}", file=sys.stderr)

def estimate_context_usage():
    """
    Estimate current context usage from environment.

    In a real implementation, this would read from Claude Code's
    context management APIs or environment variables.

    For now, we return a placeholder that can be updated when
    Claude Code provides context metrics.
    """
    # Try to read from environment if Claude Code exposes it
    usage_pct = os.environ.get('CLAUDE_CONTEXT_USAGE_PCT')
    if usage_pct:
        try:
            return float(usage_pct)
        except ValueError:
            pass

    # Fallback: use token count estimation from stdin if available
    try:
        hook_input = sys.stdin.read()
        if hook_input:
            data = json.loads(hook_input)
            # If input contains token/context metrics, extract them
            if 'context_usage_percent' in data:
                return float(data['context_usage_percent'])
    except:
        pass

    return None

def check_thresholds(usage_pct):
    """Check context usage against thresholds and warn."""
    if usage_pct is None:
        return

    level = None
    message = None

    if usage_pct >= 90:
        level = "critical"
        message = f"Context at {usage_pct}% - IMMEDIATELY run /clear or restart session"
    elif usage_pct >= 75:
        level = "warning"
        message = f"Context at {usage_pct}% - Consider running /compact now"
    elif usage_pct >= 50:
        level = "info"
        message = f"Context at {usage_pct}% - Plan to /clear or /compact soon"

    if level:
        log_event(level, message, {"usage_percent": usage_pct})

def main():
    """Monitor and warn about context usage."""
    usage_pct = estimate_context_usage()

    if usage_pct:
        check_thresholds(usage_pct)
    else:
        # Log that we ran but couldn't determine usage
        # (not an error - Claude Code may not expose metrics yet)
        log_event("debug", "Hook executed, context metrics unavailable")

if __name__ == '__main__':
    main()
