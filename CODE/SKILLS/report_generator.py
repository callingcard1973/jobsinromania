#!/usr/bin/env python3
"""
Report Generator - Generate weekly summary reports
Usage: python3 report_generator.py [--email] [--output report.html]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# ============================================================
# CONFIGURATION
# ============================================================

SKILLS_DIR = '/opt/ACTIVE/INFRA/SKILLS'
OUTPUT_DIR = '/tmp/reports'
Path(OUTPUT_DIR).mkdir(exist_ok=True)

PYTHON = '/opt/ACTIVE/INFRA/venv/bin/python3'

# Skills to include in report
REPORT_SKILLS = [
    ('master_contacts.py', 'Contact Inventory'),
    ('scraper_monitor.py', 'Scraper Status'),
    ('blacklist_checker.py --all-domains', 'Email Blacklist'),
]

# ============================================================
# RUN SKILLS
# ============================================================

def run_skill(script: str) -> str:
    """Run a skill and capture output"""
    try:
        cmd = f"{PYTHON} {SKILLS_DIR}/{script}"
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=300
        )
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return f"Error: Timeout running {script}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_disk_usage() -> Dict:
    """Get disk usage stats"""
    usage = {}
    for path in ['/mnt/usb', '/opt', '/']:
        try:
            stat = os.statvfs(path)
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bavail * stat.f_frsize
            used = total - free
            usage[path] = {
                'total_gb': round(total / 1024**3, 1),
                'used_gb': round(used / 1024**3, 1),
                'free_gb': round(free / 1024**3, 1),
                'percent': round(used * 100 / total, 1) if total > 0 else 0,
            }
        except Exception:
            pass
    return usage

def get_system_info() -> Dict:
    """Get system information"""
    info = {
        'hostname': os.uname().nodename,
        'uptime': '',
        'load': '',
        'memory': '',
    }

    try:
        result = subprocess.run(['uptime'], capture_output=True, text=True)
        info['uptime'] = result.stdout.strip()
    except Exception:
        pass

    try:
        with open('/proc/loadavg') as f:
            info['load'] = f.read().strip()
    except Exception:
        pass

    try:
        result = subprocess.run(['free', '-h'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if line.startswith('Mem:'):
                parts = line.split()
                if len(parts) >= 4:
                    info['memory'] = f"{parts[2]} / {parts[1]} used"
    except Exception:
        pass

    return info

def get_recent_files(path: str, days: int = 7, limit: int = 10) -> List[Dict]:
    """Get recently modified files"""
    files = []
    cutoff = datetime.now() - timedelta(days=days)

    try:
        for f in Path(path).rglob('*.csv'):
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime > cutoff:
                files.append({
                    'path': str(f),
                    'name': f.name,
                    'size_kb': round(f.stat().st_size / 1024, 1),
                    'modified': mtime.strftime('%Y-%m-%d %H:%M'),
                })
    except Exception:
        pass

    files.sort(key=lambda x: x['modified'], reverse=True)
    return files[:limit]

# ============================================================
# REPORT GENERATION
# ============================================================

def generate_text_report() -> str:
    """Generate plain text report"""
    lines = [
        "=" * 70,
        f"WEEKLY SYSTEM REPORT - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "=" * 70,
        "",
    ]

    # System info
    sys_info = get_system_info()
    lines.extend([
        "SYSTEM STATUS",
        "-" * 70,
        f"  Hostname: {sys_info['hostname']}",
        f"  Load: {sys_info['load']}",
        f"  Memory: {sys_info['memory']}",
        "",
    ])

    # Disk usage
    disk = get_disk_usage()
    lines.extend([
        "DISK USAGE",
        "-" * 70,
    ])
    for path, info in disk.items():
        bar = '#' * int(info['percent'] / 5)
        lines.append(f"  {path}: {info['used_gb']}/{info['total_gb']} GB ({info['percent']}%) [{bar}]")
    lines.append("")

    # Recent files
    recent = get_recent_files('/mnt/hdd/SCRAPER_DATA')
    if recent:
        lines.extend([
            "RECENT SCRAPER OUTPUT (7 days)",
            "-" * 70,
        ])
        for f in recent[:10]:
            lines.append(f"  {f['modified']} - {f['name']} ({f['size_kb']} KB)")
        lines.append("")

    # Run each skill
    for script, title in REPORT_SKILLS:
        lines.extend([
            "",
            "=" * 70,
            title.upper(),
            "=" * 70,
            "",
        ])
        output = run_skill(script)
        lines.append(output)

    lines.extend([
        "",
        "=" * 70,
        f"Report generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "=" * 70,
    ])

    return '\n'.join(lines)

def generate_html_report() -> str:
    """Generate HTML report"""
    # Get data
    sys_info = get_system_info()
    disk = get_disk_usage()
    recent = get_recent_files('/mnt/hdd/SCRAPER_DATA')

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Weekly Report - {datetime.now().strftime('%Y-%m-%d')}</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f8f9fa; }}
        .progress {{ background: #e9ecef; border-radius: 4px; height: 20px; }}
        .progress-bar {{ background: #28a745; height: 100%; border-radius: 4px; }}
        .warning {{ background: #ffc107; }}
        .danger {{ background: #dc3545; }}
        pre {{ background: #f8f9fa; padding: 15px; border-radius: 4px; overflow-x: auto; font-size: 12px; }}
        .metric {{ display: inline-block; background: #007bff; color: white; padding: 5px 15px; border-radius: 20px; margin: 5px; }}
        .ok {{ background: #28a745; }}
        .warn {{ background: #ffc107; color: #333; }}
        .error {{ background: #dc3545; }}
        footer {{ margin-top: 30px; text-align: center; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Weekly System Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        <p><strong>Hostname:</strong> {sys_info['hostname']}</p>

        <h2>System Status</h2>
        <div class="metric ok">Load: {sys_info['load'].split()[0] if sys_info['load'] else 'N/A'}</div>
        <div class="metric ok">Memory: {sys_info['memory']}</div>

        <h2>Disk Usage</h2>
        <table>
            <tr><th>Path</th><th>Used</th><th>Total</th><th>Usage</th></tr>
"""

    for path, info in disk.items():
        bar_class = 'danger' if info['percent'] > 90 else 'warning' if info['percent'] > 75 else ''
        html += f"""
            <tr>
                <td>{path}</td>
                <td>{info['used_gb']} GB</td>
                <td>{info['total_gb']} GB</td>
                <td>
                    <div class="progress">
                        <div class="progress-bar {bar_class}" style="width: {info['percent']}%"></div>
                    </div>
                    {info['percent']}%
                </td>
            </tr>
"""

    html += """
        </table>

        <h2>Recent Scraper Output (7 days)</h2>
        <table>
            <tr><th>Modified</th><th>File</th><th>Size</th></tr>
"""

    for f in recent[:10]:
        html += f"""
            <tr>
                <td>{f['modified']}</td>
                <td>{f['name']}</td>
                <td>{f['size_kb']} KB</td>
            </tr>
"""

    html += """
        </table>
"""

    # Run skills and add output
    for script, title in REPORT_SKILLS:
        output = run_skill(script)
        # Escape HTML in output
        output_escaped = output.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        html += f"""
        <h2>{title}</h2>
        <pre>{output_escaped}</pre>
"""

    html += f"""
        <footer>
            <p>Report generated by report_generator.py</p>
            <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </footer>
    </div>
</body>
</html>
"""

    return html

def send_email(content: str, subject: str = None, html: bool = False):
    """Send report via email using run_and_email.py pattern"""
    if not subject:
        subject = f"Weekly Report - {datetime.now().strftime('%Y-%m-%d')}"

    # Save to temp file
    ext = '.html' if html else '.txt'
    temp_file = f"/tmp/report_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}"
    with open(temp_file, 'w') as f:
        f.write(content)

    # Use run_and_email.py if available
    email_script = os.path.join(SKILLS_DIR, 'run_and_email.py')
    if os.path.exists(email_script):
        print(f"Sending via run_and_email.py...")
        # This would need modification to accept file input
        # For now, print instructions
        print(f"Report saved to: {temp_file}")
        print(f"To email: python3 {email_script} with attachment")
    else:
        print(f"Report saved to: {temp_file}")
        print("Email sending not configured")

    return temp_file

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if '-h' in args or '--help' in args:
        print(f"""
{'='*60}
REPORT GENERATOR
{'='*60}

Usage: report_generator.py [options]

Options:
  --html         Generate HTML report (default: text)
  --output FILE  Save to specific file
  --email        Send report via email
  --quick        Skip running skills, system info only

Skills included:
  - master_contacts.py (Contact inventory)
  - scraper_monitor.py (Scraper health)
  - blacklist_checker.py (Email deliverability)

Output: {OUTPUT_DIR}/
""")
        return

    html_format = '--html' in args
    send_mail = '--email' in args
    quick = '--quick' in args
    output_file = None

    for i, arg in enumerate(args):
        if arg == '--output' and i + 1 < len(args):
            output_file = args[i + 1]

    print(f"\n{'='*60}")
    print(f"REPORT GENERATOR - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}\n")

    if quick:
        # Quick system-only report
        print("Generating quick system report...")
        sys_info = get_system_info()
        disk = get_disk_usage()

        print(f"\nSystem: {sys_info['hostname']}")
        print(f"Load: {sys_info['load']}")
        print(f"Memory: {sys_info['memory']}")
        print(f"\nDisk:")
        for path, info in disk.items():
            print(f"  {path}: {info['percent']}% ({info['free_gb']} GB free)")
        return

    # Generate full report
    print("Generating report (this may take a few minutes)...")

    if html_format:
        content = generate_html_report()
        ext = '.html'
    else:
        content = generate_text_report()
        ext = '.txt'

    # Save report
    if not output_file:
        output_file = os.path.join(OUTPUT_DIR, f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}{ext}")

    with open(output_file, 'w') as f:
        f.write(content)

    print(f"\nReport saved to: {output_file}")
    print(f"Size: {os.path.getsize(output_file) / 1024:.1f} KB")

    # Email if requested
    if send_mail:
        send_email(content, html=html_format)

    # Print summary for text format
    if not html_format:
        print(f"\n{'-'*60}")
        print("SUMMARY (first 50 lines):")
        print(f"{'-'*60}")
        for line in content.split('\n')[:50]:
            print(line)
        if content.count('\n') > 50:
            print(f"\n... ({content.count(chr(10))} total lines)")

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
