#!/usr/bin/env python3
"""
Auto-Init for Token Optimization - Runs automatically on Claude Code startup.

This script:
1. Initializes session tracking
2. Restores default plugin settings
3. Checks CLAUDE.md compliance
4. Loads token monitor hook

Installation:
  Add to ~/.claude/settings.json in "hooks" section:
  "SessionStart": {
    "command": "python D:\\MEMORY\\OPTIMIZE TOKENS\\auto_init.py"
  }

Or run manually before each session:
  python auto_init.py

Usage:
  python auto_init.py                    # Full init
  python auto_init.py --check-only       # Check without changes
  python auto_init.py --reset-plugins    # Reset to defaults
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime

SETTINGS_PATH = Path(os.path.expanduser("~/.claude/settings.json"))
LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")
CLAUDE_MD = Path("D:\\MEMORY\\CLAUDE.md")

def ensure_settings_file():
    """Ensure ~/.claude/settings.json exists with proper structure."""
    if not SETTINGS_PATH.exists():
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        settings = {
            "enabled_mcp_servers": ["mcp__plugin_playwright_playwright"],
            "disabled_mcp_servers": ["superpowers:code-simplifier"],
            "hooks": {}
        }
        with open(SETTINGS_PATH, 'w') as f:
            json.dump(settings, f, indent=2)
        print("[CREATED] ~/.claude/settings.json with token optimization defaults")
        return settings

    try:
        with open(SETTINGS_PATH, 'r') as f:
            settings = json.load(f)
    except json.JSONDecodeError:
        print("[ERROR] ~/.claude/settings.json is malformed")
        return None

    # Ensure required keys exist
    if "enabled_mcp_servers" not in settings:
        settings["enabled_mcp_servers"] = []
    if "disabled_mcp_servers" not in settings:
        settings["disabled_mcp_servers"] = []
    if "hooks" not in settings:
        settings["hooks"] = {}

    return settings

def install_hooks(settings):
    """Install token monitor hook in settings."""
    hook_path = "D:\\\\MEMORY\\\\OPTIMIZE TOKENS\\\\token_monitor.py"

    if "PostToolUse" not in settings.get("hooks", {}):
        if "hooks" not in settings:
            settings["hooks"] = {}
        settings["hooks"]["PostToolUse"] = {
            "command": f"python {hook_path}"
        }
        print(f"[INSTALLED] PostToolUse hook for token monitoring")
        return True

    return False

def reset_plugins(settings):
    """Reset plugins to recommended defaults."""
    changed = False

    # Ensure Playwright is enabled
    if "mcp__plugin_playwright_playwright" not in settings.get("enabled_mcp_servers", []):
        if "mcp__plugin_playwright_playwright" in settings.get("disabled_mcp_servers", []):
            settings["disabled_mcp_servers"].remove("mcp__plugin_playwright_playwright")
        settings["enabled_mcp_servers"].append("mcp__plugin_playwright_playwright")
        print("[RESET] Playwright enabled (default)")
        changed = True

    # Ensure simplifier is disabled
    if "superpowers:code-simplifier" not in settings.get("disabled_mcp_servers", []):
        if "superpowers:code-simplifier" in settings.get("enabled_mcp_servers", []):
            settings["enabled_mcp_servers"].remove("superpowers:code-simplifier")
        settings["disabled_mcp_servers"].append("superpowers:code-simplifier")
        print("[RESET] Code-simplifier disabled (default)")
        changed = True

    return changed

def save_settings(settings):
    """Save settings file."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)

def check_claude_md():
    """Check if root CLAUDE.md is compliant."""
    if not CLAUDE_MD.exists():
        return False

    with open(CLAUDE_MD, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    lines = len(content.split('\n'))
    tokens = len(content) // 4

    if lines <= 50 and tokens <= 1500:
        print(f"[OK] CLAUDE.md compliant: {lines} lines, {tokens} tokens")
        return True
    else:
        print(f"[WARNING] CLAUDE.md: {lines} lines, {tokens} tokens (target: <=50 lines, <=1500 tokens)")
        return False

def create_log_dir():
    """Ensure log directory exists."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

def log_init():
    """Log auto-init event."""
    create_log_dir()
    log_file = LOG_DIR / f"init_{datetime.now().strftime('%Y%m%d')}.jsonl"
    entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "auto_init",
        "status": "success"
    }
    with open(log_file, 'a') as f:
        f.write(json.dumps(entry) + '\n')

def main():
    """Run auto-initialization."""
    check_only = "--check-only" in sys.argv
    reset_plugins_flag = "--reset-plugins" in sys.argv

    print("\n[INITIALIZING] Token Optimization System")
    print("=" * 60)

    # Step 1: Ensure settings file
    settings = ensure_settings_file()
    if not settings:
        print("[ERROR] Could not load or create settings file")
        return 1

    # Step 2: Reset plugins if requested or on init
    plugins_changed = reset_plugins(settings) if not check_only or reset_plugins_flag else False

    # Step 3: Install hooks
    hooks_changed = install_hooks(settings) if not check_only else False

    # Step 4: Save if anything changed
    if (plugins_changed or hooks_changed) and not check_only:
        save_settings(settings)
        print("[SAVED] ~/.claude/settings.json")

    # Step 5: Check CLAUDE.md
    print()
    check_claude_md()

    # Step 6: Log event
    if not check_only:
        log_init()
        print("[LOGGED] Initialization event")

    print("=" * 60)
    print("[READY] Token optimization system initialized")
    print()
    print("Next steps:")
    print("  python D:\\MEMORY\\OPTIMIZE TOKENS\\session_manager.py start \"task\"")
    print()

    return 0

if __name__ == '__main__':
    sys.exit(main())
