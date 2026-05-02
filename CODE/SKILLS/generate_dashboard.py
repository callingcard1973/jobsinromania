#!/usr/bin/env python3
"""
Status Dashboard Generator
Generates HTML dashboard for scraper and email campaign health.

Usage:
    python3 generate_dashboard.py           # Generate and open locally
    python3 generate_dashboard.py --serve   # Serve on http://0.0.0.0:8888
    python3 generate_dashboard.py --serve 9000  # Serve on custom port
"""
import sys
import os
import subprocess
import argparse
import http.server
import socketserver
import threading
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# Add skills directory to path
SKILLS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SKILLS_DIR))

from health_monitor import HealthMonitor
from email_health import get_stats as get_email_stats

OUTPUT_FILE = '/tmp/status_dashboard.html'

# Directories that are email campaigns, not scrapers
CAMPAIGN_DIRS = {'CAREWORKERS_EU', 'FACTORYJOBS_EU'}

# Email campaign paths to check (raspibig)
EMAIL_CAMPAIGN_PATHS = [
    Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECA2026'),
    Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM'),
    Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/NORWAY'),
]

# Long-term campaigns on raspi (fetched via SSH)
RASPI_CAMPAIGNS = [
    {'name': 'Poland', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND', 'script': 'run-poland-venv.sh'},
    {'name': 'Factory EU', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU', 'script': 'run-factory-venv.sh'},
    {'name': 'EU Funds', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'script': 'run-eufunds-venv.sh'},
]


def time_ago(dt):
    """Convert datetime to human readable 'X ago' format."""
    if not dt:
        return 'Never'
    delta = datetime.now() - dt
    if delta.days > 0:
        return f'{delta.days}d ago'
    hours = delta.seconds // 3600
    if hours > 0:
        return f'{hours}h ago'
    mins = delta.seconds // 60
    return f'{mins}m ago'


def get_raspi_campaign_status():
    """Get status of long-term campaigns running on raspi via SSH."""
    campaigns = []

    for camp in RASPI_CAMPAIGNS:
        status = {
            'name': f"[raspi] {camp['name']}",
            'status': 'unknown',
            'last_run': None,
            'sent_today': 0,
            'total_sent': 0,
            'remaining': 0,
        }

        try:
            # Get state.json via SSH
            import subprocess
            result = subprocess.run(
                ['ssh', 'raspi', f'cat {camp["path"]}/state.json 2>/dev/null || cat {camp["path"]}/.eufunds_sender_state.json 2>/dev/null'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and result.stdout.strip():
                state = json.loads(result.stdout)
                status['total_sent'] = state.get('total_sent', len(state.get('sent', [])))
                status['sent_today'] = state.get('sent_today', state.get('daily_sent', 0))

                # Get file mtime
                mtime_result = subprocess.run(
                    ['ssh', 'raspi', f'stat -c %Y {camp["path"]}/state.json 2>/dev/null || stat -c %Y {camp["path"]}/.eufunds_sender_state.json 2>/dev/null'],
                    capture_output=True, text=True, timeout=5
                )
                if mtime_result.returncode == 0 and mtime_result.stdout.strip():
                    status['last_run'] = datetime.fromtimestamp(int(mtime_result.stdout.strip()))
                    days_ago = (datetime.now() - status['last_run']).days
                    if days_ago == 0:
                        status['status'] = 'active'
                    elif days_ago <= 2:
                        status['status'] = 'idle'
                    else:
                        status['status'] = 'stale'
        except Exception as e:
            status['status'] = 'error'

        campaigns.append(status)

    return campaigns


def get_campaign_status():
    """Get status of email campaigns."""
    campaigns = []

    for camp_path in EMAIL_CAMPAIGN_PATHS:
        if not camp_path.exists():
            continue

        name = camp_path.name
        status = {
            'name': name,
            'status': 'unknown',
            'last_run': None,
            'sent_today': 0,
            'total_sent': 0,
            'errors': []
        }

        # Check state.json
        state_files = list(camp_path.glob('*state*.json')) + list(camp_path.glob('state.json'))
        for state_file in state_files:
            try:
                with open(state_file) as f:
                    state = json.load(f)
                    status['total_sent'] = state.get('total_sent', state.get('sent_count', 0))
                    status['sent_today'] = state.get('sent_today', 0)
                    status['last_run'] = datetime.fromtimestamp(state_file.stat().st_mtime)
                    break
            except:
                pass

        # Check logs
        log_files = list(camp_path.glob('logs/*.log')) + list(camp_path.glob('*.log'))
        if log_files:
            latest_log = max(log_files, key=lambda p: p.stat().st_mtime)
            log_mtime = datetime.fromtimestamp(latest_log.stat().st_mtime)
            if not status['last_run'] or log_mtime > status['last_run']:
                status['last_run'] = log_mtime

            # Check for recent errors
            try:
                content = latest_log.read_text(errors='replace')[-2000:]
                if 'error' in content.lower() or 'failed' in content.lower():
                    status['status'] = 'error'
                elif 'sent' in content.lower() or 'success' in content.lower():
                    status['status'] = 'active'
            except:
                pass

        # Determine status
        if status['last_run']:
            days_ago = (datetime.now() - status['last_run']).days
            if status['status'] == 'unknown':
                if days_ago == 0:
                    status['status'] = 'active'
                elif days_ago <= 2:
                    status['status'] = 'idle'
                else:
                    status['status'] = 'stale'

        campaigns.append(status)

    return campaigns


def generate_html(scraper_data, email_data, campaign_data):
    """Generate HTML dashboard."""

    # Filter out campaign directories from scrapers
    scraper_data = {k: v for k, v in scraper_data.items() if k not in CAMPAIGN_DIRS}

    # Calculate summary stats
    total_scrapers = len(scraper_data)
    healthy = sum(1 for h in scraper_data.values() if h.health_status == "healthy")
    degraded = sum(1 for h in scraper_data.values() if h.health_status == "degraded")
    unhealthy = sum(1 for h in scraper_data.values() if h.health_status == "unhealthy")
    unknown = sum(1 for h in scraper_data.values() if h.health_status == "unknown")

    # Campaign stats
    total_campaigns = len(campaign_data)
    active_campaigns = sum(1 for c in campaign_data if c['status'] == 'active')

    emails_total = email_data.get('total', 0)
    emails_ok = email_data.get('ok', 0)
    bounce_rate = email_data.get('bounce_rate', 0)

    html = f'''<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Status Dashboard - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            padding: 20px;
            line-height: 1.5;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: #fff; margin-bottom: 20px; font-size: 1.8em; }}
        h2 {{ color: #aaa; margin: 30px 0 15px; font-size: 1.3em; border-bottom: 1px solid #333; padding-bottom: 10px; }}

        /* Summary Cards */
        .summary {{ display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 30px; }}
        .card {{
            padding: 20px 25px;
            border-radius: 10px;
            min-width: 140px;
            text-align: center;
        }}
        .card .num {{ font-size: 2.5em; font-weight: bold; }}
        .card .label {{ font-size: 0.85em; opacity: 0.9; margin-top: 5px; }}
        .green {{ background: linear-gradient(135deg, #28a745, #20c997); }}
        .yellow {{ background: linear-gradient(135deg, #ffc107, #fd7e14); color: #222; }}
        .red {{ background: linear-gradient(135deg, #dc3545, #e83e8c); }}
        .blue {{ background: linear-gradient(135deg, #007bff, #6610f2); }}
        .gray {{ background: linear-gradient(135deg, #6c757d, #495057); }}

        /* Scrapers Table */
        table {{ width: 100%; border-collapse: collapse; background: #16213e; border-radius: 10px; overflow: hidden; }}
        th {{ background: #0f3460; padding: 12px 15px; text-align: left; font-weight: 500; }}
        td {{ padding: 12px 15px; border-bottom: 1px solid #1a1a2e; }}
        tr:hover {{ background: #1a2744; }}

        .status-badge {{
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.8em;
            font-weight: 500;
        }}
        .status-healthy {{ background: #28a745; }}
        .status-degraded {{ background: #ffc107; color: #222; }}
        .status-unhealthy {{ background: #dc3545; }}
        .status-unknown {{ background: #6c757d; }}

        .rate-good {{ color: #28a745; }}
        .rate-ok {{ color: #ffc107; }}
        .rate-bad {{ color: #dc3545; }}

        /* Email Section */
        .email-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }}
        .email-card {{ background: #16213e; padding: 20px; border-radius: 10px; }}
        .email-card h3 {{ color: #aaa; font-size: 0.9em; margin-bottom: 10px; }}
        .domain-list {{ list-style: none; }}
        .domain-list li {{
            display: flex;
            justify-content: space-between;
            padding: 8px 0;
            border-bottom: 1px solid #1a1a2e;
        }}
        .domain-name {{ color: #ccc; }}
        .domain-rate {{ font-weight: bold; }}

        .trend-bar {{
            display: flex;
            align-items: flex-end;
            gap: 4px;
            height: 60px;
            margin-top: 15px;
        }}
        .trend-day {{
            flex: 1;
            background: #007bff;
            border-radius: 3px 3px 0 0;
            min-height: 5px;
        }}
        .trend-labels {{ display: flex; gap: 4px; font-size: 0.7em; color: #666; }}
        .trend-labels span {{ flex: 1; text-align: center; }}

        .error-list {{ font-size: 0.8em; color: #ff6b6b; margin-top: 5px; }}
        .error-list li {{ margin: 3px 0; }}

        footer {{ text-align: center; color: #666; margin-top: 40px; padding: 20px; font-size: 0.85em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>System Status Dashboard</h1>

        <!-- Summary Cards -->
        <div class="summary">
            <div class="card green">
                <div class="num">{healthy}</div>
                <div class="label">Healthy Scrapers</div>
            </div>
            <div class="card yellow">
                <div class="num">{degraded}</div>
                <div class="label">Degraded</div>
            </div>
            <div class="card red">
                <div class="num">{unhealthy}</div>
                <div class="label">Unhealthy</div>
            </div>
            <div class="card gray">
                <div class="num">{unknown}</div>
                <div class="label">Unknown</div>
            </div>
            <div class="card blue">
                <div class="num">{total_campaigns}</div>
                <div class="label">Campaigns</div>
            </div>
            <div class="card {'green' if bounce_rate < 5 else 'yellow' if bounce_rate < 15 else 'red'}">
                <div class="num">{emails_total:,}</div>
                <div class="label">Emails (7d) - {bounce_rate}% bounce</div>
            </div>
        </div>

        <!-- Scrapers Table -->
        <h2>Scrapers ({total_scrapers})</h2>
        <table>
            <tr>
                <th>Country</th>
                <th>Status</th>
                <th>Last Run</th>
                <th>Success Rate</th>
                <th>Runs</th>
                <th>Last Output</th>
            </tr>
'''

    # Sort scrapers: unhealthy first, then by name
    status_order = {'unhealthy': 0, 'degraded': 1, 'unknown': 2, 'healthy': 3}
    sorted_scrapers = sorted(
        scraper_data.items(),
        key=lambda x: (status_order.get(x[1].health_status, 4), x[0])
    )

    for country, health in sorted_scrapers:
        status_class = f'status-{health.health_status}'
        rate_class = 'rate-good' if health.success_rate >= 90 else 'rate-ok' if health.success_rate >= 70 else 'rate-bad'
        last_run = time_ago(health.last_run)
        rows = f'{health.last_output_rows:,}' if health.last_output_rows else '-'

        html += f'''            <tr>
                <td><strong>{country}</strong></td>
                <td><span class="status-badge {status_class}">{health.health_status.upper()}</span></td>
                <td>{last_run}</td>
                <td class="{rate_class}">{health.success_rate:.0f}%</td>
                <td>{health.successful_runs}/{health.total_runs}</td>
                <td>{rows} rows</td>
            </tr>
'''

    html += '''        </table>

        <!-- Email Campaigns Table -->
        <h2>Email Campaigns ({total_campaigns})</h2>
        <table>
            <tr>
                <th>Campaign</th>
                <th>Status</th>
                <th>Last Run</th>
                <th>Sent Today</th>
                <th>Total Sent</th>
            </tr>
'''.format(total_campaigns=total_campaigns)

    for camp in campaign_data:
        status_class = {
            'active': 'status-healthy',
            'idle': 'status-degraded',
            'stale': 'status-unhealthy',
            'error': 'status-unhealthy',
            'unknown': 'status-unknown'
        }.get(camp['status'], 'status-unknown')

        last_run = time_ago(camp['last_run'])

        html += f'''            <tr>
                <td><strong>{camp['name']}</strong></td>
                <td><span class="status-badge {status_class}">{camp['status'].upper()}</span></td>
                <td>{last_run}</td>
                <td>{camp['sent_today']:,}</td>
                <td>{camp['total_sent']:,}</td>
            </tr>
'''

    html += '''        </table>

        <!-- Email Stats Section -->
        <h2>Email Delivery Stats (7 days)</h2>
        <div class="email-grid">
'''

    # Top domains card
    html += '''            <div class="email-card">
                <h3>Top Domains (7 days)</h3>
                <ul class="domain-list">
'''
    for d in email_data.get('top_domains', [])[:8]:
        rate_class = 'rate-good' if d['rate'] >= 90 else 'rate-ok' if d['rate'] >= 70 else 'rate-bad'
        html += f'''                    <li>
                        <span class="domain-name">{d['domain']}</span>
                        <span class="domain-rate {rate_class}">{d['ok']}/{d['total']} ({d['rate']}%)</span>
                    </li>
'''
    html += '''                </ul>
            </div>
'''

    # Daily trend card
    daily_sends = email_data.get('daily_sends', [])
    if daily_sends:
        max_count = max(d['count'] for d in daily_sends) or 1
        html += '''            <div class="email-card">
                <h3>Daily Send Volume</h3>
                <div class="trend-bar">
'''
        for d in reversed(daily_sends):
            height = int((d['count'] / max_count) * 100)
            html += f'''                    <div class="trend-day" style="height: {height}%" title="{d['date']}: {d['count']}"></div>
'''
        html += '''                </div>
                <div class="trend-labels">
'''
        for d in reversed(daily_sends):
            day = d['date'].split('-')[2] if '-' in d['date'] else d['date']
            html += f'''                    <span>{day}</span>
'''
        html += '''                </div>
            </div>
'''

    # Status breakdown card
    status_breakdown = email_data.get('status_breakdown', {})
    if status_breakdown:
        html += '''            <div class="email-card">
                <h3>Status Breakdown</h3>
                <ul class="domain-list">
'''
        for status, count in sorted(status_breakdown.items(), key=lambda x: -x[1]):
            rate_class = 'rate-good' if status == 'OK' else 'rate-ok' if status in ('sent', 'delivered') else 'rate-bad'
            html += f'''                    <li>
                        <span>{status}</span>
                        <span class="{rate_class}">{count:,}</span>
                    </li>
'''
        html += '''                </ul>
            </div>
'''

    # Email error if any
    if email_data.get('error'):
        html += f'''            <div class="email-card">
                <h3>Email Data Error</h3>
                <p style="color: #ff6b6b;">{email_data['error']}</p>
            </div>
'''

    html += f'''        </div>

        <footer>
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |
            Scrapers: {total_scrapers} |
            Emails: {emails_total:,} (7d)
        </footer>
    </div>
</body>
</html>
'''

    return html


def collect_and_generate():
    """Collect data and generate HTML dashboard."""
    print("Collecting data...")

    # Get scraper health
    print("  - Analyzing scrapers...")
    monitor = HealthMonitor(days=7)
    scraper_data = monitor.analyze_all()

    # Get email campaign status (raspibig)
    print("  - Checking email campaigns...")
    campaign_data = get_campaign_status()

    # Get raspi long-term campaigns via SSH
    print("  - Checking raspi long-term campaigns...")
    try:
        raspi_campaigns = get_raspi_campaign_status()
        campaign_data.extend(raspi_campaigns)
    except Exception as e:
        print(f"    Warning: Could not fetch raspi campaigns: {e}")

    # Get email stats
    print("  - Fetching email stats...")
    email_data = get_email_stats(days=7)

    # Generate HTML
    print("  - Generating dashboard...")
    html = generate_html(scraper_data, email_data, campaign_data)

    # Save
    with open(OUTPUT_FILE, 'w') as f:
        f.write(html)

    print(f"Dashboard saved to: {OUTPUT_FILE}")

    # Return summary for display
    healthy = sum(1 for h in scraper_data.values() if h.health_status == "healthy")
    unhealthy = sum(1 for h in scraper_data.values() if h.health_status == "unhealthy")
    return {
        'healthy': healthy,
        'unhealthy': unhealthy,
        'emails': email_data.get('total', 0),
        'bounce_rate': email_data.get('bounce_rate', 0)
    }


def serve_dashboard(port=8888, auto_refresh=60):
    """Serve dashboard via HTTP - regenerates on each page load."""

    class DashboardHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/' or self.path == '/status_dashboard.html':
                # Regenerate dashboard on each request
                try:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Generating fresh dashboard...")
                    collect_and_generate()

                    with open(OUTPUT_FILE, 'rb') as f:
                        content = f.read()

                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Content-Length', len(content))
                    self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                    self.end_headers()
                    self.wfile.write(content)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Dashboard served")
                except Exception as e:
                    self.send_error(500, f"Error generating dashboard: {e}")
            else:
                self.send_error(404, "Not found")

        def log_message(self, format, *args):
            pass  # Suppress default logging

    # Generate initial dashboard
    print("Generating initial dashboard...")
    summary = collect_and_generate()

    # Get hostname
    hostname = os.uname().nodename

    print(f"\n{'='*50}")
    print(f"Status Dashboard Server")
    print(f"{'='*50}")
    print(f"URL: http://{hostname}:{port}")
    print(f"     http://localhost:{port}")
    print(f"{'='*50}")
    print(f"Scrapers: {summary['healthy']} healthy, {summary['unhealthy']} unhealthy")
    print(f"Emails: {summary['emails']:,} ({summary['bounce_rate']}% bounce)")
    print(f"{'='*50}")
    print("Dashboard regenerates on each page load")
    print("Press Ctrl+C to stop\n")

    # Start server
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), DashboardHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


def main():
    parser = argparse.ArgumentParser(description='Status Dashboard Generator')
    parser.add_argument('--serve', nargs='?', const=8888, type=int, metavar='PORT',
                        help='Serve dashboard via HTTP (default port: 8888)')
    parser.add_argument('--refresh', type=int, default=60,
                        help='Auto-refresh interval in seconds (default: 60)')
    args = parser.parse_args()

    if args.serve:
        serve_dashboard(port=args.serve, auto_refresh=args.refresh)
    else:
        summary = collect_and_generate()

        # Open in browser
        try:
            if sys.platform == 'darwin':
                subprocess.run(['open', OUTPUT_FILE])
            else:
                subprocess.run(['xdg-open', OUTPUT_FILE], stderr=subprocess.DEVNULL)
            print("Opened in browser.")
        except Exception:
            print("Could not open browser automatically.")

        print(f"\nSummary: {summary['healthy']} healthy, {summary['unhealthy']} unhealthy scrapers | {summary['emails']:,} emails ({summary['bounce_rate']}% bounce)")


if __name__ == '__main__':
    main()
