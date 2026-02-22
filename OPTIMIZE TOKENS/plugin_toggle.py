#!/usr/bin/env python3
"""
Plugin Toggle - Enable/disable Claude Code plugins to reduce token consumption.

Plugins and estimated token costs:
  - playwright: ~15-20 tool definitions (~400-600 tokens per session)
  - code-simplifier: ~5 tool definitions (~200 tokens per session)

Usage:
  python plugin_toggle.py browser on|off      # Toggle playwright plugin
  python plugin_toggle.py simplifier on|off   # Toggle code-simplifier
  python plugin_toggle.py status               # Show current plugin state
  python plugin_toggle.py defaults             # Restore to recommended defaults
"""

import json
import os
from pathlib import Path

# Settings file location
SETTINGS_PATH = Path(os.path.expanduser("~/.claude/settings.json"))
PLUGINS_DEFAULT = {
    "mcp__plugin_playwright_playwright": True,  # Enable by default
    "superpowers:code-simplifier": False,       # Disable by default
}

PLUGIN_INFO = {
    "browser": {
        "key": "mcp__plugin_playwright_playwright",
        "tokens": "~400-600",
        "use": "Browser automation, web scraping, UI testing"
    },
    "simplifier": {
        "key": "superpowers:code-simplifier",
        "tokens": "~200",
        "use": "Code refactoring and cleanup"
    }
}

def load_settings():
    """Load current Claude Code settings."""
    if not SETTINGS_PATH.exists():
        print(f"[INFO] Settings file not found at {SETTINGS_PATH}")
        print(f"[INFO] Creating new settings file...")
        SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        return {
            "enabled_mcp_servers": [],
            "disabled_mcp_servers": []
        }

    try:
        with open(SETTINGS_PATH, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"[ERROR] Failed to parse {SETTINGS_PATH}")
        return {}

def save_settings(settings):
    """Save Claude Code settings."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_PATH, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"[SAVED] Settings updated at {SETTINGS_PATH}")

def toggle_plugin(plugin_name, state):
    """Enable or disable a plugin."""
    if plugin_name not in PLUGIN_INFO:
        print(f"[ERROR] Unknown plugin: {plugin_name}")
        print(f"        Available: {', '.join(PLUGIN_INFO.keys())}")
        return

    settings = load_settings()
    plugin_key = PLUGIN_INFO[plugin_name]["key"]
    state_bool = state.lower() == 'on'

    if "disabled_mcp_servers" not in settings:
        settings["disabled_mcp_servers"] = []
    if "enabled_mcp_servers" not in settings:
        settings["enabled_mcp_servers"] = []

    # Update disable/enable lists
    if state_bool:
        # Enable: remove from disabled list
        if plugin_key in settings["disabled_mcp_servers"]:
            settings["disabled_mcp_servers"].remove(plugin_key)
        if plugin_key not in settings["enabled_mcp_servers"]:
            settings["enabled_mcp_servers"].append(plugin_key)
        status = "ENABLED"
    else:
        # Disable: add to disabled list
        if plugin_key not in settings["disabled_mcp_servers"]:
            settings["disabled_mcp_servers"].append(plugin_key)
        if plugin_key in settings["enabled_mcp_servers"]:
            settings["enabled_mcp_servers"].remove(plugin_key)
        status = "DISABLED"

    save_settings(settings)
    tokens = PLUGIN_INFO[plugin_name]["tokens"]
    print(f"\n[{status}] {plugin_name}")
    print(f"        Token cost: {tokens} per session")
    print(f"        Use case: {PLUGIN_INFO[plugin_name]['use']}")

def show_status():
    """Show current plugin state."""
    settings = load_settings()
    disabled = set(settings.get("disabled_mcp_servers", []))

    print("\n=== PLUGIN STATUS ===\n")
    total_savings = 0
    for name, info in PLUGIN_INFO.items():
        key = info["key"]
        is_disabled = key in disabled
        status = "[OFF]" if is_disabled else "[ON]"
        tokens = int(info["tokens"].split("-")[0].strip("~"))
        if is_disabled:
            total_savings += tokens
        print(f"{status} {name:<15} {info['tokens']:>10} tokens")

    print(f"\n[SAVINGS] Disabling all unused plugins saves ~{total_savings}-{total_savings+400} tokens/session")

def set_defaults():
    """Restore recommended defaults: browser ON, simplifier OFF."""
    settings = load_settings()
    settings["disabled_mcp_servers"] = ["superpowers:code-simplifier"]
    settings["enabled_mcp_servers"] = ["mcp__plugin_playwright_playwright"]
    save_settings(settings)
    print("\n[DEFAULTS] Restored recommended configuration:")
    print("  - Playwright (browser):  ON   (needed for web tasks)")
    print("  - Code-simplifier:       OFF  (disable until needed)")
    print("  - Estimated savings:     ~200 tokens/session")

def main():
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        show_status()
        return

    cmd = sys.argv[1].lower()

    if cmd == "status":
        show_status()
    elif cmd == "defaults":
        set_defaults()
    elif cmd in PLUGIN_INFO and len(sys.argv) >= 3:
        state = sys.argv[2].lower()
        if state not in ['on', 'off']:
            print(f"[ERROR] State must be 'on' or 'off', got '{state}'")
            return
        toggle_plugin(cmd, state)
    else:
        print(__doc__)

if __name__ == '__main__':
    main()
