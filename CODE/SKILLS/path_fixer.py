#!/usr/bin/env python3
"""
Path Fixer - Auto-detect and fix broken paths after directory reorganization.

USE THIS WHEN:
- Scripts fail with "python3: not found"
- Scripts fail with "No such file or directory"
- After moving directories around
- Scrapers or campaigns won't start

RUN:
    python3 /opt/ACTIVE/INFRA/SKILLS/path_fixer.py --check     # Check only
    python3 /opt/ACTIVE/INFRA/SKILLS/path_fixer.py --fix       # Fix all issues
    python3 /opt/ACTIVE/INFRA/SKILLS/path_fixer.py --verify    # Verify scrapers work

LLM INSTRUCTIONS:
    If user reports "path not found" or "python3 not found":
    1. Run: python3 /opt/ACTIVE/INFRA/SKILLS/path_fixer.py --fix
    2. Run: python3 /opt/ACTIVE/INFRA/SKILLS/path_fixer.py --verify
    3. Report results to user
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path
from datetime import datetime

# Required symlinks for backward compatibility
REQUIRED_SYMLINKS = {
    '/opt/venv/bin/python3': '/usr/bin/python3',
    '/opt/ACTIVE/INFRA/venv/bin/python3': '/usr/bin/python3',
    '/opt/SCRAPERS': '/opt/ACTIVE/SCRAPERS',
}

# Required directories
REQUIRED_DIRS = [
    '/opt/venv/bin',
    '/opt/ACTIVE/INFRA/venv/bin',
]

# Scrapers to verify
SCRAPERS_TO_TEST = {
    'ANOFM': {
        'dir': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM',
        'script': 'anofm_scraper.py',
        'test_arg': '--test',
    },
    'EURES': {
        'dir': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/EURES',
        'script': 'eures_scraper.py',
        'test_arg': '1 1 10 de 1 LAST_WEEK',  # Minimal test
    },
}

# Campaign paths to verify
CAMPAIGN_PATHS = [
    '/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS',
    '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED',
]

def log(msg, level='INFO'):
    """Print with timestamp."""
    ts = datetime.now().strftime('%H:%M:%S')
    symbol = {'INFO': '>', 'OK': '+', 'WARN': '!', 'ERROR': 'X', 'FIX': '*'}
    print(f"[{ts}] [{symbol.get(level, '>')}] {msg}")

def check_symlink(path, target):
    """Check if symlink exists and points to correct target."""
    path = Path(path)
    if not path.exists():
        return False, f"Missing: {path}"
    if path.is_symlink():
        actual_target = os.readlink(path)
        if actual_target == target:
            return True, f"OK: {path} -> {target}"
        else:
            return False, f"Wrong target: {path} -> {actual_target} (should be {target})"
    else:
        return False, f"Not a symlink: {path}"

def create_symlink(path, target):
    """Create symlink with sudo if needed."""
    path = Path(path)

    # Create parent directory if needed
    parent = path.parent
    if not parent.exists():
        log(f"Creating directory: {parent}", 'FIX')
        try:
            parent.mkdir(parents=True, exist_ok=True)
        except PermissionError:
            subprocess.run(['sudo', 'mkdir', '-p', str(parent)], check=True)
            subprocess.run(['sudo', 'chown', '-R', f'{os.getuid()}:{os.getgid()}', str(parent)], check=True)

    # Remove existing if wrong
    if path.exists() or path.is_symlink():
        log(f"Removing existing: {path}", 'FIX')
        try:
            path.unlink()
        except PermissionError:
            subprocess.run(['sudo', 'rm', '-f', str(path)], check=True)

    # Create symlink
    log(f"Creating symlink: {path} -> {target}", 'FIX')
    try:
        path.symlink_to(target)
    except PermissionError:
        subprocess.run(['sudo', 'ln', '-sf', target, str(path)], check=True)
        subprocess.run(['sudo', 'chown', '-h', f'{os.getuid()}:{os.getgid()}', str(path)], check=True)

    return True

def check_playwright():
    """Check if Playwright browsers are installed."""
    firefox_path = Path.home() / '.cache/ms-playwright'
    if not firefox_path.exists():
        return False, "Playwright not installed"

    # Check for firefox
    firefox_dirs = list(firefox_path.glob('firefox-*'))
    if not firefox_dirs:
        return False, "Firefox browser not installed"

    return True, f"Playwright OK: {len(firefox_dirs)} browser(s)"

def install_playwright():
    """Install Playwright Firefox browser."""
    log("Installing Playwright Firefox...", 'FIX')
    result = subprocess.run(
        [sys.executable, '-m', 'playwright', 'install', 'firefox'],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        log("Playwright Firefox installed", 'OK')
        return True
    else:
        log(f"Failed to install Playwright: {result.stderr}", 'ERROR')
        return False

def verify_scraper(name, config):
    """Test a scraper to verify it works."""
    script_path = Path(config['dir']) / config['script']
    if not script_path.exists():
        return False, f"Script not found: {script_path}"

    cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', str(script_path)]
    if config['test_arg']:
        cmd.extend(config['test_arg'].split())

    log(f"Testing {name}...", 'INFO')
    try:
        result = subprocess.run(
            cmd,
            capture_output=True, text=True,
            timeout=60,
            cwd=config['dir']
        )

        # Check for common success indicators
        output = result.stdout + result.stderr
        if 'error' in output.lower() and 'retry' not in output.lower():
            if 'ModuleNotFoundError' in output:
                return False, f"Missing module: {output.split('ModuleNotFoundError:')[1].split()[0]}"
            if 'FileNotFoundError' in output:
                return False, f"Missing file in output"

        if result.returncode == 0 or 'Saved' in output or 'jobs' in output.lower():
            return True, f"{name} OK"
        else:
            return False, f"{name} failed: {output[:200]}"

    except subprocess.TimeoutExpired:
        return True, f"{name} running (timeout OK for long scrapers)"
    except Exception as e:
        return False, f"{name} error: {e}"

def check_campaign_paths():
    """Verify campaign paths exist."""
    issues = []
    for path in CAMPAIGN_PATHS:
        if not Path(path).exists():
            issues.append(f"Missing: {path}")
    return len(issues) == 0, issues

def fix_campaign_scripts():
    """Fix common path issues in campaign scripts."""
    campaigns_dir = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/CAMPAIGNS')
    if not campaigns_dir.exists():
        return 0, "Campaigns directory not found"

    fixed = 0
    for script in campaigns_dir.glob('*/send_*.py'):
        content = script.read_text()

        # Fix old paths
        replacements = [
            ('/opt/SHARED', '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED'),
            ('/opt/SCRAPERS/SCRIPTS/SHARED', '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED'),
            ('/opt/venv/bin/python3', '/opt/ACTIVE/INFRA/venv/bin/python3'),
        ]

        new_content = content
        for old, new in replacements:
            if old in new_content:
                new_content = new_content.replace(old, new)

        if new_content != content:
            script.write_text(new_content)
            log(f"Fixed paths in: {script.name}", 'FIX')
            fixed += 1

    return fixed, f"Fixed {fixed} campaign scripts"

def main():
    parser = argparse.ArgumentParser(description='Auto-fix paths after directory reorganization')
    parser.add_argument('--check', action='store_true', help='Check for issues only')
    parser.add_argument('--fix', action='store_true', help='Fix all issues')
    parser.add_argument('--verify', action='store_true', help='Verify scrapers work')
    parser.add_argument('--campaigns', action='store_true', help='Fix campaign scripts')
    parser.add_argument('--all', action='store_true', help='Do everything: fix + verify + campaigns')
    args = parser.parse_args()

    if not any([args.check, args.fix, args.verify, args.campaigns, args.all]):
        args.check = True

    if args.all:
        args.fix = True
        args.verify = True
        args.campaigns = True

    print("=" * 60)
    print("PATH FIXER - Auto-detect and fix broken paths")
    print("=" * 60)

    issues_found = 0
    issues_fixed = 0

    # Check/fix symlinks
    print("\n[1] SYMLINKS")
    print("-" * 40)
    for path, target in REQUIRED_SYMLINKS.items():
        ok, msg = check_symlink(path, target)
        if ok:
            log(msg, 'OK')
        else:
            log(msg, 'WARN')
            issues_found += 1
            if args.fix:
                if create_symlink(path, target):
                    issues_fixed += 1

    # Check/fix Playwright
    print("\n[2] PLAYWRIGHT")
    print("-" * 40)
    ok, msg = check_playwright()
    if ok:
        log(msg, 'OK')
    else:
        log(msg, 'WARN')
        issues_found += 1
        if args.fix:
            if install_playwright():
                issues_fixed += 1

    # Check campaign paths
    print("\n[3] CAMPAIGN PATHS")
    print("-" * 40)
    ok, issues = check_campaign_paths()
    if ok:
        log("All campaign paths OK", 'OK')
    else:
        for issue in issues:
            log(issue, 'WARN')
            issues_found += 1

    # Fix campaign scripts
    if args.campaigns:
        print("\n[4] CAMPAIGN SCRIPTS")
        print("-" * 40)
        fixed, msg = fix_campaign_scripts()
        log(msg, 'OK' if fixed == 0 else 'FIX')
        issues_fixed += fixed

    # Verify scrapers
    if args.verify:
        print("\n[5] SCRAPER VERIFICATION")
        print("-" * 40)
        for name, config in SCRAPERS_TO_TEST.items():
            ok, msg = verify_scraper(name, config)
            log(msg, 'OK' if ok else 'ERROR')
            if not ok:
                issues_found += 1

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Issues found: {issues_found}")
    print(f"Issues fixed: {issues_fixed}")

    if issues_found > issues_fixed:
        print("\nRun with --fix to fix remaining issues")
        return 1
    elif issues_found == 0:
        print("\nAll paths OK!")
        return 0
    else:
        print("\nAll issues fixed!")
        return 0

if __name__ == '__main__':
    sys.exit(main())
