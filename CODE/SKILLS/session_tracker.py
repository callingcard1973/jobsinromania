#!/usr/bin/env python3
"""
Session Tracker - Maintains state across Claude interactions
Prevents re-explaining same things, tracks context shown
"""
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

SESSION_FILE = Path('/tmp/claude_session.json')

def load_session():
    """Load existing session or create new one."""
    if SESSION_FILE.exists():
        try:
            with open(SESSION_FILE, 'r') as f:
                session = json.load(f)
            # Check if session is stale (> 1 hour)
            started = datetime.fromisoformat(session.get('started', '2000-01-01'))
            if datetime.now() - started > timedelta(hours=1):
                return new_session()
            return session
        except:
            pass
    return new_session()

def new_session():
    """Create a new session."""
    return {
        'started': datetime.now().isoformat(),
        'last_activity': datetime.now().isoformat(),
        'explained': [],        # Rules/concepts already explained
        'paths_shown': [],      # Paths already shown to user
        'files_read': [],       # Files already read
        'decisions_made': [],   # Decisions already made
        'context_loaded': [],   # Context files loaded
        'commands_run': []      # Commands already executed
    }

def save_session(session):
    """Save session to file."""
    session['last_activity'] = datetime.now().isoformat()
    with open(SESSION_FILE, 'w') as f:
        json.dump(session, f, indent=2)

def mark_explained(topic):
    """Mark a topic as already explained."""
    session = load_session()
    if topic not in session['explained']:
        session['explained'].append(topic)
        save_session(session)
    return session

def is_explained(topic):
    """Check if topic was already explained."""
    session = load_session()
    return topic in session['explained']

def mark_path_shown(path):
    """Mark a path as already shown."""
    session = load_session()
    if path not in session['paths_shown']:
        session['paths_shown'].append(path)
        save_session(session)

def mark_file_read(filepath):
    """Mark a file as already read."""
    session = load_session()
    if filepath not in session['files_read']:
        session['files_read'].append(filepath)
        save_session(session)

def mark_decision(decision_key, value):
    """Record a decision."""
    session = load_session()
    session['decisions_made'].append({
        'key': decision_key,
        'value': value,
        'timestamp': datetime.now().isoformat()
    })
    save_session(session)

def get_decision(decision_key):
    """Get a previously made decision."""
    session = load_session()
    for d in reversed(session['decisions_made']):
        if d['key'] == decision_key:
            return d['value']
    return None

def mark_context_loaded(context_name):
    """Mark context as loaded."""
    session = load_session()
    if context_name not in session['context_loaded']:
        session['context_loaded'].append(context_name)
        save_session(session)

def get_session_summary():
    """Get summary of current session."""
    session = load_session()
    return {
        'duration_minutes': round((datetime.now() - datetime.fromisoformat(session['started'])).total_seconds() / 60, 1),
        'topics_explained': len(session['explained']),
        'files_read': len(session['files_read']),
        'decisions_made': len(session['decisions_made']),
        'context_loaded': session['context_loaded']
    }

def reset_session():
    """Reset session to fresh state."""
    session = new_session()
    save_session(session)
    return session

def main():
    if len(sys.argv) < 2:
        print("Usage: session_tracker.py <command> [args]")
        print("\nCommands:")
        print("  status              - Show session summary")
        print("  explained <topic>   - Mark topic as explained")
        print("  check <topic>       - Check if topic was explained")
        print("  read <file>         - Mark file as read")
        print("  decide <key> <val>  - Record a decision")
        print("  getdecision <key>   - Get previous decision")
        print("  reset               - Reset session")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'status':
        print(json.dumps(get_session_summary(), indent=2))
    elif cmd == 'explained':
        mark_explained(sys.argv[2])
        print(f"Marked '{sys.argv[2]}' as explained")
    elif cmd == 'check':
        result = is_explained(sys.argv[2])
        print(f"'{sys.argv[2]}': {'already explained' if result else 'not explained yet'}")
        sys.exit(0 if result else 1)
    elif cmd == 'read':
        mark_file_read(sys.argv[2])
        print(f"Marked '{sys.argv[2]}' as read")
    elif cmd == 'decide':
        mark_decision(sys.argv[2], sys.argv[3])
        print(f"Recorded decision: {sys.argv[2]} = {sys.argv[3]}")
    elif cmd == 'getdecision':
        val = get_decision(sys.argv[2])
        print(val if val else "No decision found")
        sys.exit(0 if val else 1)
    elif cmd == 'reset':
        reset_session()
        print("Session reset")
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == '__main__':
    main()
