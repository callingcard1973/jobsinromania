#!/usr/bin/env python3
"""
Session Manager - Track Claude Code session usage and enforce token hygiene.

Logs task start/end times, estimates token usage, and recommends actions.

Usage:
  python session_manager.py start "task description"  # Log task start
  python session_manager.py end                        # Log task end
  python session_manager.py status                     # Show current session
  python session_manager.py log [--tail 20]            # View session log
  python session_manager.py export                     # Export to JSON
"""

import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")
CURRENT_SESSION = LOG_DIR / "current_session.json"

def ensure_log_dir():
    """Ensure log directory exists."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def load_current_session():
    """Load current session metadata."""
    if CURRENT_SESSION.exists():
        try:
            with open(CURRENT_SESSION, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            pass
    return None

def save_current_session(session):
    """Save current session metadata."""
    ensure_log_dir()
    with open(CURRENT_SESSION, 'w') as f:
        json.dump(session, f, indent=2)

def append_to_log(task_name, event_type, event_data):
    """Append entry to session log."""
    ensure_log_dir()
    log_file = LOG_DIR / f"session_{datetime.now().strftime('%Y%m%d')}.jsonl"

    entry = {
        "timestamp": datetime.now().isoformat(),
        "task": task_name,
        "event": event_type,
        "data": event_data
    }

    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')

def recommend_model(description):
    """Recommend haiku vs sonnet based on task type."""
    lower_desc = description.lower()

    # Research/reading tasks → haiku
    research_keywords = ['read', 'search', 'understand', 'analyze', 'explore',
                         'find', 'lookup', 'check', 'verify', 'research']
    if any(kw in lower_desc for kw in research_keywords):
        return "haiku (cost-optimized for research)"

    # Implementation/complex tasks → sonnet
    implementation_keywords = ['implement', 'build', 'create', 'fix', 'refactor',
                               'develop', 'design', 'architecture', 'test']
    if any(kw in lower_desc for kw in implementation_keywords):
        return "sonnet (recommended for implementation)"

    return "haiku (default - upgrade if needed)"

def cmd_start(task_desc):
    """Start a new session."""
    session = {
        "task": task_desc,
        "start_time": datetime.now().isoformat(),
        "model": recommend_model(task_desc),
        "notes": []
    }

    save_current_session(session)
    append_to_log(task_desc, "start", {"model": session["model"]})

    print(f"\n[SESSION STARTED]")
    print(f"  Task: {task_desc}")
    print(f"  Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"  Recommended model: {session['model']}")
    print(f"\n[TIPS]")
    print(f"  - Use /clear between unrelated tasks")
    print(f"  - Run /compact at 50% context fill")
    print(f"  - Disable plugins via: python plugin_toggle.py status")

def cmd_end():
    """End current session."""
    session = load_current_session()
    if not session:
        print("[ERROR] No active session. Run: session_manager.py start \"task\"")
        return

    task = session.get("task", "unknown")
    start = datetime.fromisoformat(session.get("start_time", datetime.now().isoformat()))
    duration = datetime.now() - start

    append_to_log(task, "end", {
        "duration_seconds": duration.total_seconds(),
        "duration_minutes": round(duration.total_seconds() / 60, 1)
    })

    # Estimate tokens
    # Very rough: 8 min session ~= 20K tokens with plugins on, ~10K with plugins off
    estimated_tokens = max(8000, int(8 + duration.total_seconds() / 60 * 2000))

    print(f"\n[SESSION ENDED]")
    print(f"  Task: {task}")
    print(f"  Duration: {int(duration.total_seconds() // 60)}m {int(duration.total_seconds() % 60)}s")
    print(f"  Estimated tokens: ~{estimated_tokens}")
    print(f"\n[NEXT STEPS]")
    print(f"  - Run /clear to reset context")
    print(f"  - Review session log: python session_manager.py log")

    # Cleanup
    CURRENT_SESSION.unlink(missing_ok=True)

def cmd_status():
    """Show current session status."""
    session = load_current_session()
    if not session:
        print("[INFO] No active session")
        return

    task = session.get("task")
    start = datetime.fromisoformat(session.get("start_time"))
    duration = datetime.now() - start
    model = session.get("model", "unknown")

    print(f"\n[ACTIVE SESSION]")
    print(f"  Task: {task}")
    print(f"  Model: {model}")
    print(f"  Duration: {int(duration.total_seconds() // 60)}m {int(duration.total_seconds() % 60)}s")

    if duration > timedelta(minutes=30):
        print(f"\n[WARNING] Session exceeds 30 minutes - consider /clear + restart")

def cmd_log(tail=None):
    """Show session log."""
    ensure_log_dir()
    log_file = LOG_DIR / f"session_{datetime.now().strftime('%Y%m%d')}.jsonl"

    if not log_file.exists():
        print(f"[INFO] No logs found for today")
        return

    with open(log_file, 'r') as f:
        lines = f.readlines()

    if tail:
        lines = lines[-tail:]

    print(f"\n[SESSION LOG] {log_file.name}\n")
    for line in lines:
        try:
            entry = json.loads(line)
            ts = entry.get("timestamp", "?").split('T')[1][:8]
            task = entry.get("task", "?")[:30]
            event = entry.get("event")
            print(f"{ts}  {event:<6}  {task}")
        except:
            print(line.strip())

def cmd_export():
    """Export session logs to JSON."""
    ensure_log_dir()
    log_file = LOG_DIR / f"session_{datetime.now().strftime('%Y%m%d')}.jsonl"

    if not log_file.exists():
        print("[INFO] No logs to export")
        return

    entries = []
    with open(log_file, 'r') as f:
        for line in f:
            try:
                entries.append(json.loads(line))
            except:
                pass

    output = LOG_DIR / f"session_{datetime.now().strftime('%Y%m%d')}_export.json"
    with open(output, 'w') as f:
        json.dump(entries, f, indent=2)

    print(f"[EXPORTED] {len(entries)} entries to {output}")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "start":
        if len(sys.argv) < 3:
            print("[ERROR] Usage: session_manager.py start \"task description\"")
            return
        task_desc = " ".join(sys.argv[2:])
        cmd_start(task_desc)

    elif cmd == "end":
        cmd_end()

    elif cmd == "status":
        cmd_status()

    elif cmd == "log":
        tail = None
        if len(sys.argv) >= 3 and sys.argv[2] == "--tail":
            tail = int(sys.argv[3]) if len(sys.argv) >= 4 else 20
        cmd_log(tail)

    elif cmd == "export":
        cmd_export()

    else:
        print(__doc__)

if __name__ == '__main__':
    main()
