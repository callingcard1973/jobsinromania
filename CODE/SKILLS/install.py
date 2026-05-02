#!/usr/bin/env python3
"""
Token Optimizer Suite - Installation Script

Usage:
    python3 install.py              # Full install
    python3 install.py --check      # Check current status
    python3 install.py --rollback   # Restore original claude.md
"""

import sys
import shutil
import json
from pathlib import Path
from datetime import datetime

HOME = Path.home()
CLAUDE_MD = HOME / "claude.md"
CLAUDE_MD_NEW = HOME / "claude.md.new"
CLAUDE_MD_BACKUP = HOME / "claude.md.backup"
RULES_DIR = HOME / ".claude" / "rules"
OPTIMIZER_DIR = Path("/opt/ACTIVE/INFRA/SKILLS/token_optimizer")


def check_status():
    """Check current optimization status."""
    print("=== Token Optimizer Status ===\n")

    # Check claude.md size
    if CLAUDE_MD.exists():
        size = CLAUDE_MD.stat().st_size
        tokens = size // 4
        print(f"claude.md: {size:,} bytes (~{tokens:,} tokens)")
        if size < 2000:
            print("  [OK] Optimized (minimal core)")
        else:
            print("  [!] Full version loaded")
    else:
        print("claude.md: NOT FOUND")

    # Check rules modules
    print(f"\nRules modules ({RULES_DIR}):")
    if RULES_DIR.exists():
        for f in sorted(RULES_DIR.glob("*.md")):
            size = f.stat().st_size
            print(f"  {f.name}: {size:,} bytes")
    else:
        print("  NOT CONFIGURED")

    # Check cache
    cache_db = OPTIMIZER_DIR / "cache" / "summaries.db"
    if cache_db.exists():
        size = cache_db.stat().st_size
        print(f"\nCache DB: {size:,} bytes")
    else:
        print("\nCache DB: Not initialized")

    # Check hooks
    print("\nSession hook:", end=" ")
    hook = OPTIMIZER_DIR / "hooks" / "session_start.sh"
    if hook.exists() and hook.stat().st_mode & 0o111:
        print("[OK] Installed and executable")
    else:
        print("[!] Not ready")


def install():
    """Install token optimizer."""
    print("=== Installing Token Optimizer Suite ===\n")

    # 1. Backup original claude.md
    if CLAUDE_MD.exists() and not CLAUDE_MD_BACKUP.exists():
        print(f"1. Backing up {CLAUDE_MD} -> {CLAUDE_MD_BACKUP}")
        shutil.copy2(CLAUDE_MD, CLAUDE_MD_BACKUP)
    else:
        print("1. Backup already exists, skipping")

    # 2. Install new minimal claude.md
    if CLAUDE_MD_NEW.exists():
        print(f"2. Installing optimized claude.md")
        shutil.copy2(CLAUDE_MD_NEW, CLAUDE_MD)

        old_size = CLAUDE_MD_BACKUP.stat().st_size if CLAUDE_MD_BACKUP.exists() else 0
        new_size = CLAUDE_MD.stat().st_size
        savings = ((old_size - new_size) / old_size * 100) if old_size else 0
        print(f"   {old_size:,} -> {new_size:,} bytes ({savings:.0f}% reduction)")
    else:
        print("2. [!] claude.md.new not found, skipping")

    # 3. Verify rules directory
    print(f"3. Checking rules directory: {RULES_DIR}")
    if RULES_DIR.exists():
        modules = list(RULES_DIR.glob("*.md"))
        print(f"   Found {len(modules)} modules")
    else:
        print("   [!] Rules directory not found")

    # 4. Initialize cache
    print("4. Initializing cache database")
    cache_dir = OPTIMIZER_DIR / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 5. Make hook executable
    print("5. Setting up session hook")
    hook = OPTIMIZER_DIR / "hooks" / "session_start.sh"
    if hook.exists():
        hook.chmod(0o755)
        print("   Hook is executable")

    print("\n=== Installation Complete ===")
    print("\nTo activate hooks, add to your Claude Code settings:")
    print("""
{
  "hooks": {
    "session-start": "/opt/ACTIVE/INFRA/SKILLS/token_optimizer/hooks/session_start.sh"
  }
}
""")


def rollback():
    """Restore original claude.md."""
    print("=== Rolling Back ===\n")

    if CLAUDE_MD_BACKUP.exists():
        shutil.copy2(CLAUDE_MD_BACKUP, CLAUDE_MD)
        print(f"Restored {CLAUDE_MD} from backup")
        print(f"Size: {CLAUDE_MD.stat().st_size:,} bytes")
    else:
        print("[!] No backup found at", CLAUDE_MD_BACKUP)


def compare():
    """Compare before/after token usage."""
    print("=== Token Comparison ===\n")

    if CLAUDE_MD_BACKUP.exists():
        old = CLAUDE_MD_BACKUP.stat().st_size
    else:
        old = 0

    new = CLAUDE_MD.stat().st_size if CLAUDE_MD.exists() else 0

    modules_size = sum(f.stat().st_size for f in RULES_DIR.glob("*.md")) if RULES_DIR.exists() else 0

    print(f"Before (full claude.md):     {old:>8,} bytes (~{old//4:,} tokens)")
    print(f"After (minimal claude.md):   {new:>8,} bytes (~{new//4:,} tokens)")
    print(f"Modules (lazy, not loaded):  {modules_size:>8,} bytes (~{modules_size//4:,} tokens)")
    print()

    if old > 0:
        savings = (old - new) / old * 100
        print(f"Startup savings: {savings:.0f}%")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "--check":
            check_status()
        elif cmd == "--rollback":
            rollback()
        elif cmd == "--compare":
            compare()
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: install.py [--check|--rollback|--compare]")
    else:
        install()
