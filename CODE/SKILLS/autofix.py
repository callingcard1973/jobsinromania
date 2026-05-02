#!/usr/bin/env python3
"""
Autofix - Self-healing system maintenance

Automatically detects and fixes common issues:
- Broken Node-RED flows (missing scripts, bad DB connections)
- Stale processes
- Disk space issues
- Failed services

Usage:
    python3 autofix.py              # Check all, report only
    python3 autofix.py --fix        # Auto-fix what can be fixed
    python3 autofix.py --alert      # Send Telegram summary
    python3 autofix.py --cron       # Silent unless issues (for scheduled runs)
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime

NODERED_URL = "http://localhost:1880/flows"

# Known deprecated/broken scripts
DEPRECATED_SCRIPTS = [
    'anofm_construct_pipeline.py',
    'db_campaign_sender.py',
    'daily_report.py',
]

# Critical services to check
SERVICES = [
    ('postgresql', 'pg_isready'),
    ('node-red', 'curl -s http://localhost:1880'),
    ('dashboard', 'curl -s http://localhost:8085'),
]


class AutoFix:
    def __init__(self):
        self.issues = []
        self.fixed = []
        self.warnings = []

    def check_nodered_flows(self, fix=False):
        """Check Node-RED scheduled flows for broken scripts."""
        try:
            resp = requests.get(NODERED_URL, timeout=5)
            data = resp.json()
        except Exception as e:
            self.issues.append(f"Node-RED unreachable: {e}")
            return

        exec_nodes = {n.get('id'): n for n in data if n.get('type') == 'exec'}
        broken_injects = []

        for node in data:
            if node.get('type') == 'inject' and node.get('crontab'):
                for wire_group in node.get('wires', []):
                    for wire_id in wire_group:
                        if wire_id in exec_nodes:
                            exec_node = exec_nodes[wire_id]
                            cmd = exec_node.get('command', '')

                            # Check script exists
                            for part in cmd.split():
                                if part.endswith('.py') and part.startswith('/'):
                                    if not os.path.exists(part):
                                        broken_injects.append({
                                            'id': node.get('id'),
                                            'name': node.get('name'),
                                            'reason': f"Script not found: {part}"
                                        })
                                    # Check deprecated
                                    for dep in DEPRECATED_SCRIPTS:
                                        if dep in part:
                                            broken_injects.append({
                                                'id': node.get('id'),
                                                'name': node.get('name'),
                                                'reason': f"Deprecated: {dep}"
                                            })

        if broken_injects:
            for b in broken_injects:
                self.issues.append(f"Broken flow: {b['name']} - {b['reason']}")

            if fix:
                for b in broken_injects:
                    for node in data:
                        if node.get('id') == b['id'] and node.get('crontab'):
                            node['crontab'] = ''
                            node['name'] = f"DISABLED: {node.get('name', '')}"
                            self.fixed.append(f"Disabled: {b['name']}")

                # Deploy fixes
                resp = requests.post(NODERED_URL, json=data,
                    headers={'Content-Type': 'application/json',
                             'Node-RED-Deployment-Type': 'full'})
                if resp.status_code == 204:
                    self.fixed.append("Node-RED flows deployed")

    def check_services(self, fix=False):
        """Check critical services are running."""
        for name, check_cmd in SERVICES:
            try:
                result = subprocess.run(check_cmd, shell=True,
                    capture_output=True, timeout=10)
                if result.returncode != 0:
                    self.issues.append(f"Service down: {name}")
                    if fix and name == 'dashboard':
                        # Restart dashboard
                        subprocess.run('pkill -f "pipeline_web_dashboard"', shell=True)
                        subprocess.Popen(
                            '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/pipeline_web_dashboard.py --serve 8085',
                            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                        )
                        self.fixed.append("Restarted dashboard")
            except subprocess.TimeoutExpired:
                self.warnings.append(f"Service slow: {name}")
            except Exception as e:
                self.warnings.append(f"Cannot check {name}: {e}")

    def check_disk_space(self, fix=False):
        """Check disk space on critical partitions."""
        result = subprocess.run("df -h / /opt /mnt/usb 2>/dev/null",
            shell=True, capture_output=True, text=True)

        for line in result.stdout.strip().split('\n')[1:]:
            parts = line.split()
            if len(parts) >= 5:
                usage = int(parts[4].replace('%', ''))
                mount = parts[5]
                if usage > 90:
                    self.issues.append(f"Disk critical: {mount} at {usage}%")
                elif usage > 80:
                    self.warnings.append(f"Disk warning: {mount} at {usage}%")

    def check_stale_processes(self, fix=False):
        """Check for stale/zombie processes."""
        result = subprocess.run("ps aux | grep -E 'Z|defunct' | grep -v grep",
            shell=True, capture_output=True, text=True)

        if result.stdout.strip():
            count = len(result.stdout.strip().split('\n'))
            self.warnings.append(f"Zombie processes: {count}")

    def check_brevo_campaigns(self, fix=False):
        """Verify brevo campaign scripts are runnable."""
        brevo_scripts = list(Path('/opt/ACTIVE/INFRA/SKILLS').glob('brevo_*.py'))

        for script in brevo_scripts:
            if 'sync' in script.name or 'monitor' in script.name:
                continue
            # Quick syntax check
            result = subprocess.run(
                f'/opt/ACTIVE/INFRA/venv/bin/python3 -m py_compile {script}',
                shell=True, capture_output=True, timeout=5
            )
            if result.returncode != 0:
                self.issues.append(f"Syntax error: {script.name}")

    def run_all(self, fix=False):
        """Run all checks."""
        self.check_nodered_flows(fix)
        self.check_services(fix)
        self.check_disk_space(fix)
        self.check_stale_processes(fix)
        self.check_brevo_campaigns(fix)

    def report(self):
        """Generate report."""
        lines = []
        lines.append("=== AUTOFIX REPORT ===")
        lines.append(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        if self.fixed:
            lines.append(f"FIXED ({len(self.fixed)}):")
            for f in self.fixed:
                lines.append(f"  + {f}")
            lines.append("")

        if self.issues:
            lines.append(f"ISSUES ({len(self.issues)}):")
            for i in self.issues:
                lines.append(f"  ! {i}")
            lines.append("")

        if self.warnings:
            lines.append(f"WARNINGS ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"  ? {w}")
            lines.append("")

        if not self.issues and not self.warnings and not self.fixed:
            lines.append("All systems OK")

        return '\n'.join(lines)

    def telegram_summary(self):
        """Short summary for Telegram."""
        if not self.issues and not self.fixed:
            return None  # Nothing to report

        emoji = "🔧" if self.fixed else "⚠️"
        msg = f"{emoji} Autofix Report\n"

        if self.fixed:
            msg += f"\nFixed: {len(self.fixed)}\n"
            for f in self.fixed[:3]:
                msg += f"  + {f}\n"

        if self.issues:
            msg += f"\nIssues: {len(self.issues)}\n"
            for i in self.issues[:3]:
                msg += f"  ! {i}\n"

        return msg


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--fix', action='store_true', help='Auto-fix issues')
    parser.add_argument('--alert', action='store_true', help='Send Telegram alert')
    parser.add_argument('--cron', action='store_true', help='Silent unless issues')
    parser.add_argument('--json', action='store_true', help='JSON output')
    args = parser.parse_args()

    af = AutoFix()
    af.run_all(fix=args.fix)

    if args.json:
        print(json.dumps({
            'issues': af.issues,
            'warnings': af.warnings,
            'fixed': af.fixed
        }, indent=2))
        return

    if args.cron:
        # Only output if there are issues
        if af.issues or af.fixed:
            print(af.report())
            if args.alert:
                msg = af.telegram_summary()
                if msg:
                    try:
                        from alerting import send_telegram
                        send_telegram(msg)
                    except:
                        pass
    else:
        print(af.report())
        if args.alert:
            msg = af.telegram_summary()
            if msg:
                try:
                    from alerting import send_telegram
                    send_telegram(msg)
                except Exception as e:
                    print(f"Alert failed: {e}")


if __name__ == '__main__':
    main()
