#!/usr/bin/env python3
"""
Infrastructure Health Skill - Unified health management for raspi/raspibig

Usage:
    infra_health.py status      # Quick status of both machines
    infra_health.py report      # Full status report
    infra_health.py disk        # Disk guardian status
    infra_health.py clean       # Run cleanup (dry-run)
    infra_health.py clean!      # Run cleanup (actual)
    infra_health.py scrapers    # Scraper status
    infra_health.py alerts      # Test Telegram alerts
"""

import subprocess
import sys
import os

SCRIPTS_DIR = "/opt/ACTIVE/INFRA/SKILLS"


def run(cmd):
    """Run command and print output"""
    result = subprocess.run(cmd, shell=True)
    return result.returncode


def main():
    if len(sys.argv) < 2:
        cmd = 'status'
    else:
        cmd = sys.argv[1].lower()

    if cmd == 'status':
        print("\n=== INFRASTRUCTURE STATUS ===\n")
        run(f"python3 {SCRIPTS_DIR}/disk_guardian.py --status")
        print()

    elif cmd == 'report':
        run(f"python3 {SCRIPTS_DIR}/status_report.py")

    elif cmd == 'disk':
        run(f"python3 {SCRIPTS_DIR}/disk_guardian.py --status")

    elif cmd == 'clean':
        run(f"python3 {SCRIPTS_DIR}/system_cleaner.py --dry-run")

    elif cmd == 'clean!':
        run(f"python3 {SCRIPTS_DIR}/system_cleaner.py")

    elif cmd == 'scrapers':
        run(f"python3 {SCRIPTS_DIR}/scraper_organizer.py")

    elif cmd == 'alerts' or cmd == 'test':
        run(f"python3 {SCRIPTS_DIR}/disk_guardian.py --test-alert")

    elif cmd == 'dashboard':
        print("Dashboard: http://192.168.100.21:8090")
        print("JSON API:  http://192.168.100.21:8090/status")

    elif cmd in ('-h', '--help', 'help'):
        print(__doc__)

    else:
        print(f"Unknown command: {cmd}")
        print("Use: status, report, disk, clean, clean!, scrapers, alerts, dashboard")
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
