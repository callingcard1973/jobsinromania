#!/usr/bin/env python3
"""
Pipeline Web Dashboard - Unified HTML view of scrapers, data, campaigns, and sending.

Usage:
    python3 pipeline_web_dashboard.py              # Generate HTML and open
    python3 pipeline_web_dashboard.py --serve      # Serve on http://0.0.0.0:8080
    python3 pipeline_web_dashboard.py --serve 9000 # Custom port
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS')
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')

import os
import json
import http.server
import socketserver
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Import from pipeline_dashboard
from pipeline_dashboard import (
    collect_all_stats,
    SENDER_LIMITS,
    DATA_SOURCES,
)

OUTPUT_FILE = '/tmp/pipeline_dashboard.html'
DEFAULT_PORT = 8080


def generate_html(stats: dict) -> str:
    """Generate HTML dashboard from pipeline stats."""

    generated = datetime.now().strftime('%Y-%m-%d %H:%M')

    scraper = stats.get('scrapers', {})
    data = stats.get('data', {})
    campaign = stats.get('campaigns', {})
    sending = stats.get('sending', {})
    tracker = stats.get('tracker', {})

    # Calculate percentages
    scraper_pct = round(100 * scraper.get('healthy', 0) / max(scraper.get('total', 1), 1))
    campaign_pct = round(100 * campaign.get('total_sent', 0) / max(campaign.get('total_leads', 1), 1), 1)
    sender_pct = sending.get('percent_used', 0)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta http-equiv="refresh" content="60">
    <title>Pipeline Dashboard</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Courier New', monospace;
            background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
            color: #c9d1d9;
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}

        /* Header */
        header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 1px solid #30363d;
        }}
        h1 {{
            font-size: 1.5em;
            color: #58a6ff;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        h1::before {{ content: ""; }}
        .timestamp {{ color: #8b949e; font-size: 0.85em; }}

        /* Pipeline Flow */
        .pipeline-flow {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: #21262d;
            border-radius: 10px;
            padding: 20px 30px;
            margin-bottom: 25px;
            gap: 10px;
        }}
        .flow-stage {{
            text-align: center;
            flex: 1;
        }}
        .flow-stage .num {{
            font-size: 2em;
            font-weight: bold;
            color: #58a6ff;
        }}
        .flow-stage .label {{
            font-size: 0.8em;
            color: #8b949e;
            margin-top: 5px;
        }}
        .flow-arrow {{
            font-size: 1.5em;
            color: #30363d;
        }}

        /* Grid Layout */
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 20px;
            margin-bottom: 25px;
        }}

        /* Cards */
        .card {{
            background: #21262d;
            border-radius: 10px;
            border: 1px solid #30363d;
            overflow: hidden;
        }}
        .card-header {{
            background: #161b22;
            padding: 12px 16px;
            border-bottom: 1px solid #30363d;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .card-header h2 {{
            font-size: 0.95em;
            color: #c9d1d9;
            font-weight: 500;
        }}
        .card-header .badge {{
            background: #238636;
            color: #fff;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75em;
        }}
        .card-header .badge.warning {{ background: #9e6a03; }}
        .card-header .badge.danger {{ background: #da3633; }}
        .card-header .badge.info {{ background: #1f6feb; }}
        .card-body {{
            padding: 16px;
        }}

        /* Progress Bar */
        .progress-container {{
            margin: 15px 0;
        }}
        .progress-label {{
            display: flex;
            justify-content: space-between;
            font-size: 0.85em;
            margin-bottom: 8px;
        }}
        .progress-bar {{
            height: 8px;
            background: #30363d;
            border-radius: 4px;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        .progress-fill.green {{ background: linear-gradient(90deg, #238636, #2ea043); }}
        .progress-fill.yellow {{ background: linear-gradient(90deg, #9e6a03, #d29922); }}
        .progress-fill.red {{ background: linear-gradient(90deg, #da3633, #f85149); }}
        .progress-fill.blue {{ background: linear-gradient(90deg, #1f6feb, #58a6ff); }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 0.85em;
        }}
        th {{
            text-align: left;
            padding: 8px 10px;
            color: #8b949e;
            font-weight: 500;
            border-bottom: 1px solid #30363d;
        }}
        td {{
            padding: 8px 10px;
            border-bottom: 1px solid #21262d;
        }}
        tr:hover {{ background: #161b22; }}

        /* Status Badges */
        .status {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 0.75em;
            font-weight: 500;
        }}
        .status.healthy {{ background: #238636; color: #fff; }}
        .status.stale {{ background: #9e6a03; color: #fff; }}
        .status.dead {{ background: #da3633; color: #fff; }}
        .status.missing {{ background: #6e7681; color: #fff; }}

        /* Stats Row */
        .stats-row {{
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }}
        .stat-item {{
            flex: 1;
            min-width: 80px;
            text-align: center;
            padding: 10px;
            background: #161b22;
            border-radius: 6px;
        }}
        .stat-item .value {{
            font-size: 1.3em;
            font-weight: bold;
            color: #58a6ff;
        }}
        .stat-item .label {{
            font-size: 0.75em;
            color: #8b949e;
            margin-top: 3px;
        }}

        /* Footer */
        footer {{
            text-align: center;
            padding: 20px;
            color: #6e7681;
            font-size: 0.8em;
            border-top: 1px solid #30363d;
            margin-top: 20px;
        }}
        footer a {{ color: #58a6ff; text-decoration: none; }}

        /* Responsive */
        @media (max-width: 768px) {{
            .pipeline-flow {{ flex-wrap: wrap; }}
            .flow-arrow {{ display: none; }}
            .grid {{ grid-template-columns: 1fr; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Pipeline Dashboard</h1>
            <span class="timestamp">Updated: {generated} | Auto-refresh: 60s</span>
        </header>

        <!-- Pipeline Flow -->
        <div class="pipeline-flow">
            <div class="flow-stage">
                <div class="num">{scraper.get('total', 0)}</div>
                <div class="label">SCRAPERS</div>
                <div class="label">{scraper.get('healthy', 0)} healthy</div>
            </div>
            <div class="flow-arrow">--></div>
            <div class="flow-stage">
                <div class="num">{data.get('total_records', 0):,}</div>
                <div class="label">DATA RECORDS</div>
                <div class="label">{data.get('source_count', 0)} sources</div>
            </div>
            <div class="flow-arrow">--></div>
            <div class="flow-stage">
                <div class="num">{campaign.get('total_leads', 0):,}</div>
                <div class="label">CAMPAIGN LEADS</div>
                <div class="label">{campaign.get('total_campaigns', 0)} campaigns</div>
            </div>
            <div class="flow-arrow">--></div>
            <div class="flow-stage">
                <div class="num">{campaign.get('total_sent', 0):,}</div>
                <div class="label">SENT</div>
                <div class="label">{campaign_pct}% complete</div>
            </div>
        </div>

        <!-- Sender Capacity -->
        <div class="card" style="margin-bottom: 25px;">
            <div class="card-header">
                <h2>Sender Capacity (Today)</h2>
                <span class="badge {'info' if sender_pct < 50 else 'warning' if sender_pct < 80 else 'danger'}">{sending.get('remaining', 0):,} remaining</span>
            </div>
            <div class="card-body">
                <div class="progress-container">
                    <div class="progress-label">
                        <span>{sending.get('used_today', 0):,} used</span>
                        <span>{sending.get('capacity_total', 0):,} capacity</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill {'green' if sender_pct < 50 else 'yellow' if sender_pct < 80 else 'red'}" style="width: {min(sender_pct, 100)}%"></div>
                    </div>
                </div>
                <div class="stats-row" style="margin-top: 15px;">
                    <div class="stat-item">
                        <div class="value">{sending.get('senders_active', 0)}</div>
                        <div class="label">Active Senders</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{sending.get('senders_total', 0)}</div>
                        <div class="label">Total Senders</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{tracker.get('today', 0)}</div>
                        <div class="label">Tracked Today</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">{tracker.get('week', 0)}</div>
                        <div class="label">This Week</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="grid">
            <!-- Scrapers Card -->
            <div class="card">
                <div class="card-header">
                    <h2>Scrapers</h2>
                    <span class="badge {'danger' if scraper.get('healthy', 0) == 0 else 'warning' if scraper.get('healthy', 0) < scraper.get('total', 1)/2 else ''}">{scraper.get('healthy', 0)}/{scraper.get('total', 0)} healthy</span>
                </div>
                <div class="card-body">
                    <table>
                        <tr><th>Scraper</th><th>Status</th><th>Last Run</th><th>Rows</th></tr>
'''

    # Add scraper rows
    details = scraper.get('details', [])
    health_order = {'healthy': 0, 'stale': 1, 'dead': 2, 'no_output': 3, 'missing': 4}
    sorted_details = sorted(details, key=lambda x: health_order.get(x.get('health', 'missing'), 5))[:8]

    for s in sorted_details:
        health = s.get('health', 'unknown')
        status_class = {'healthy': 'healthy', 'stale': 'stale', 'dead': 'dead'}.get(health, 'missing')

        last_run = ''
        if s.get('last_output'):
            lo = s['last_output']
            if isinstance(lo, str):
                last_run = lo[:10]
            else:
                age = datetime.now() - lo
                last_run = f"{age.days}d" if age.days > 0 else f"{int(age.total_seconds()/3600)}h"

        rows = s.get('last_output_rows', 0)
        html += f'''                        <tr>
                            <td>{s['name']}</td>
                            <td><span class="status {status_class}">{health}</span></td>
                            <td>{last_run or '-'}</td>
                            <td>{rows:,}</td>
                        </tr>
'''

    html += '''                    </table>
                </div>
            </div>

            <!-- Data Sources Card -->
            <div class="card">
                <div class="card-header">
                    <h2>Data Sources</h2>
                    <span class="badge info">''' + f"{data.get('total_records', 0):,}" + ''' records</span>
                </div>
                <div class="card-body">
                    <table>
                        <tr><th>Source</th><th>Rows</th><th>Size</th><th>Age</th></tr>
'''

    # Add data source rows
    sources = data.get('sources', {})
    for name, info in sorted(sources.items(), key=lambda x: -x[1].get('rows', 0)):
        if info.get('rows', 0) > 0:
            html += f'''                        <tr>
                            <td>{name}</td>
                            <td>{info['rows']:,}</td>
                            <td>{info.get('size_mb', 0):.1f}MB</td>
                            <td>{info.get('age_days', 0):.0f}d</td>
                        </tr>
'''

    html += '''                    </table>
                </div>
            </div>

            <!-- Campaigns Card -->
            <div class="card">
                <div class="card-header">
                    <h2>Campaigns</h2>
                    <span class="badge">''' + f"{campaign.get('total_remaining', 0):,}" + ''' remaining</span>
                </div>
                <div class="card-body">
                    <table>
                        <tr><th>Campaign</th><th>Leads</th><th>Sent</th><th>%</th></tr>
'''

    # Add campaign rows
    campaigns = campaign.get('campaigns', [])
    for c in campaigns[:7]:
        pct = round(100 * c['sent'] / max(c['leads'], 1), 1)
        html += f'''                        <tr>
                            <td>{c['name']}</td>
                            <td>{c['leads']:,}</td>
                            <td>{c['sent']:,}</td>
                            <td>{pct}%</td>
                        </tr>
'''

    html += '''                    </table>
                </div>
            </div>
        </div>

        <!-- ANOFM Brevo Campaigns -->
        <div class="card" style="margin-bottom: 25px;">
            <div class="card-header">
                <h2>ANOFM Brevo Campaigns (Romania)</h2>
                <span class="badge info">''' + f"{stats.get('anofm', {}).get('total_remaining', 0):,}" + ''' remaining</span>
            </div>
            <div class="card-body">
                <div class="stats-row" style="margin-bottom: 15px;">
                    <div class="stat-item">
                        <div class="value">''' + str(stats.get('anofm', {}).get('total_campaigns', 0)) + '''</div>
                        <div class="label">Campaigns</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">''' + f"{stats.get('anofm', {}).get('total_sent', 0):,}" + '''</div>
                        <div class="label">Total Sent</div>
                    </div>
                    <div class="stat-item">
                        <div class="value">''' + f"{stats.get('anofm', {}).get('capacity_daily', 0):,}" + '''</div>
                        <div class="label">Daily Capacity</div>
                    </div>
                </div>
                <table>
                    <tr><th>Campaign</th><th>Sender</th><th>Sectors</th><th>Sent</th><th>Today</th><th>Remaining</th></tr>
'''

    # Add ANOFM campaign rows
    anofm_campaigns = stats.get('anofm', {}).get('campaigns', [])
    for c in anofm_campaigns:
        sectors_str = ', '.join(c.get('sectors', []))[:30]
        html += f'''                    <tr>
                        <td>{c['name']}</td>
                        <td>{c.get('sender', '-')}</td>
                        <td>{sectors_str}</td>
                        <td>{c.get('sent', 0):,}</td>
                        <td>{c.get('sent_today', 0)}</td>
                        <td>{c.get('remaining', 0):,}</td>
                    </tr>
'''

    html += f'''                </table>
            </div>
        </div>

        <footer>
            Pipeline Dashboard | raspibig |
            <a href="http://raspibig:8888">Status Dashboard</a> |
            Capacity: {sending.get('remaining', 0):,}/day
        </footer>
    </div>
</body>
</html>
'''

    return html


def serve_dashboard(port: int = DEFAULT_PORT):
    """Serve dashboard via HTTP."""

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path in ('/', '/index.html', '/dashboard'):
                try:
                    stats = collect_all_stats()
                    html = generate_html(stats)

                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.send_header('Cache-Control', 'no-cache')
                    self.end_headers()
                    self.wfile.write(html.encode('utf-8'))
                except Exception as e:
                    self.send_error(500, f"Error: {e}")
            elif self.path == '/api/stats':
                try:
                    stats = collect_all_stats()
                    self.send_response(200)
                    self.send_header('Content-Type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps(stats, default=str).encode('utf-8'))
                except Exception as e:
                    self.send_error(500, f"Error: {e}")
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {args[0]}")

    hostname = os.uname().nodename

    print(f"\n{'='*50}")
    print(f" PIPELINE WEB DASHBOARD")
    print(f"{'='*50}")
    print(f" URL: http://{hostname}:{port}")
    print(f"      http://localhost:{port}")
    print(f" API: http://{hostname}:{port}/api/stats")
    print(f"{'='*50}")
    print(f" Auto-refresh: 60 seconds")
    print(f" Press Ctrl+C to stop")
    print(f"{'='*50}\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Pipeline Web Dashboard")
    parser.add_argument('--serve', nargs='?', const=DEFAULT_PORT, type=int,
                        metavar='PORT', help=f'Serve on HTTP (default: {DEFAULT_PORT})')
    args = parser.parse_args()

    if args.serve:
        serve_dashboard(args.serve)
    else:
        # Generate and save
        print("Generating dashboard...")
        stats = collect_all_stats()
        html = generate_html(stats)

        with open(OUTPUT_FILE, 'w') as f:
            f.write(html)

        print(f"Saved to: {OUTPUT_FILE}")

        # Try to open
        try:
            subprocess.run(['xdg-open', OUTPUT_FILE], stderr=subprocess.DEVNULL)
        except:
            pass

        # Print summary
        print(f"\nPipeline: {stats['scrapers']['total']} scrapers -> "
              f"{stats['data']['total_records']:,} records -> "
              f"{stats['campaigns']['total_leads']:,} leads -> "
              f"{stats['campaigns']['total_sent']:,} sent")


if __name__ == '__main__':
    main()
