#!/usr/bin/env python3
"""Refactor dashboard.py into modules. Each .py file <=250 code lines.
HTML template strings are DATA (not code) — stored in dashboard_html.py.

Files produced:
  dashboard.py          - entry point, app creation, blueprint registration (~25 lines)
  dashboard_helpers.py  - config loading, DB helpers, nav_html (~180 code lines)
  dashboard_styles.py   - STYLES CSS string (data)
  dashboard_html.py     - all *_HTML template strings (data)
  bp_pages.py           - page routes: index, new, overview, edit, template, logs, state, history, clone, send
  bp_api_core.py        - core API: status, toggle, update, template, reset, send, clone, senders, stats, active, bulk
  bp_api_extra.py       - extra API: schedules, preview, validate, metrics, ab-tests, alerts
  bp_csv.py             - CSV upload (already exists, 121 lines)
"""
import os

SRC = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"

with open(SRC) as f:
    lines = f.readlines()

def extract(start, end):
    """Extract lines (1-indexed to 0-indexed)."""
    return lines[start-1:end]

def write(name, content):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(content)
    print(f"  {name}: {len(content)} lines")

# ── dashboard_helpers.py: lines 1-315 (imports, helpers, nav_html, NO css/html) ──
h = []
h.append("#!/usr/bin/env python3\n")
h.append('"""Shared helpers for campaign dashboard."""\n')
h.extend(extract(30, 39))   # imports
h.append("\n")
h.append("CAMPAIGNS = {}\n")
h.append("SENDERS = {}\n")
h.extend(extract(43, 47))   # paths
h.extend(extract(48, 313))  # all helper functions through nav_html
write("dashboard_helpers.py", h)

# ── dashboard_styles.py: lines 315-410 (CSS string) ──
s = []
s.append("#!/usr/bin/env python3\n")
s.append('"""CSS styles for campaign dashboard."""\n')
s.extend(extract(315, 410))
write("dashboard_styles.py", s)

# ── dashboard_html.py: all HTML template strings ──
html = []
html.append("#!/usr/bin/env python3\n")
html.append('"""HTML templates for campaign dashboard. These are DATA strings, not code."""\n')
html.append("from dashboard_styles import STYLES\n")
html.append("from dashboard_helpers import nav_html\n\n")
# INDEX_HTML: 411-887
html.extend(extract(410, 888))
html.append("\n")
# NEW_CAMPAIGN_HTML: 889-1227
html.extend(extract(888, 1228))
html.append("\n")
# CAMPAIGN_HTML: 1405-1464
html.extend(extract(1404, 1465))
html.append("\n")
# EDIT_HTML: 1478-1565
html.extend(extract(1477, 1566))
html.append("\n")
# TEMPLATE_HTML: 1580-1651
html.extend(extract(1579, 1652))
html.append("\n")
# LOGS_HTML: 1697-1743
html.extend(extract(1696, 1744))
html.append("\n")
# STATE_HTML: 1781-1813
html.extend(extract(1780, 1814))
html.append("\n")
# HISTORY_HTML: 1843-1894
html.extend(extract(1842, 1895))
html.append("\n")
# CLONE_HTML: 1909-1956
html.extend(extract(1908, 1957))
html.append("\n")
# SEND_HTML: 1973-2088
html.extend(extract(1972, 2089))
write("dashboard_html.py", html)

# ── bp_pages.py: page route functions ──
p = []
p.append("#!/usr/bin/env python3\n")
p.append('"""Page routes for campaign dashboard."""\n')
p.append("import os, json, psycopg2\n")
p.append("from pathlib import Path\n")
p.append("from datetime import datetime, timedelta\n")
p.append("from flask import Blueprint, request, render_template_string, redirect, jsonify\n")
p.append("from dashboard_helpers import *\n")
p.append("from dashboard_html import *\n")
p.append("\npages_bp = Blueprint('pages', __name__)\n\n")

page_ranges = [
    (1228, 1378),  # new_campaign + api_new_campaign
    (1378, 1404),  # index
    (1465, 1477),  # campaign_overview
    (1566, 1579),  # campaign_edit
    (1652, 1696),  # campaign_template
    (1744, 1780),  # campaign_logs
    (1814, 1842),  # campaign_state
    (1895, 1908),  # campaign_history
    (1957, 1972),  # campaign_clone
    (2089, 2104),  # campaign_send
]
for s, e in page_ranges:
    chunk = extract(s, e)
    for i, line in enumerate(chunk):
        chunk[i] = line.replace("@app.route", "@pages_bp.route")
    p.extend(chunk)
    p.append("\n")
write("bp_pages.py", p)

# ── bp_api_core.py: core API endpoints (lines 2104-2466) ──
ac = []
ac.append("#!/usr/bin/env python3\n")
ac.append('"""Core API routes: CRUD, toggle, send, clone, stats."""\n')
ac.append("import os, json, subprocess, psycopg2, shutil\n")
ac.append("from pathlib import Path\n")
ac.append("from datetime import datetime\n")
ac.append("from flask import Blueprint, request, jsonify, redirect\n")
ac.append("from dashboard_helpers import *\n")
ac.append("\napi_core_bp = Blueprint('api_core', __name__)\n\n")
chunk = extract(2105, 2467)
for i, line in enumerate(chunk):
    chunk[i] = line.replace("@app.route", "@api_core_bp.route")
ac.extend(chunk)
write("bp_api_core.py", ac)

# ── bp_api_extra.py: extra API (schedules, alerts, etc. lines 2467-2760) ──
ae = []
ae.append("#!/usr/bin/env python3\n")
ae.append('"""Extra API routes: schedules, alerts, monitoring, A/B tests."""\n')
ae.append("import os, json, subprocess, psycopg2\n")
ae.append("from pathlib import Path\n")
ae.append("from datetime import datetime\n")
ae.append("from flask import Blueprint, request, jsonify, redirect\n")
ae.append("from dashboard_helpers import *\n")
ae.append("\napi_extra_bp = Blueprint('api_extra', __name__)\n\n")
chunk = extract(2467, 2760)
for i, line in enumerate(chunk):
    chunk[i] = line.replace("@app.route", "@api_extra_bp.route")
ae.extend(chunk)
write("bp_api_extra.py", ae)

# ── dashboard.py: main entry point ──
m = []
m.append("#!/opt/ACTIVE/INFRA/venv/bin/python3\n")
m.append('"""Campaign Dashboard v6 — Modular entry point."""\n')
m.append("import argparse\n")
m.append("from pathlib import Path\n")
m.append("from flask import Flask\n")
m.append("from dashboard_helpers import CONFIGS_DIR, load_all_configs, load_senders\n")
m.append("from bp_pages import pages_bp\n")
m.append("from bp_api_core import api_core_bp\n")
m.append("from bp_api_extra import api_extra_bp\n")
m.append("from bp_csv import csv_bp\n")
m.append("\n")
m.append("app = Flask(__name__)\n")
m.append("app.register_blueprint(pages_bp)\n")
m.append("app.register_blueprint(api_core_bp)\n")
m.append("app.register_blueprint(api_extra_bp)\n")
m.append("app.register_blueprint(csv_bp)\n")
m.append("\n")
m.append("if __name__ == '__main__':\n")
m.append("    parser = argparse.ArgumentParser()\n")
m.append("    parser.add_argument('--port', type=int, default=8090)\n")
m.append("    parser.add_argument('--configs', default=str(CONFIGS_DIR))\n")
m.append("    args = parser.parse_args()\n")
m.append("    load_all_configs(Path(args.configs))\n")
m.append("    load_senders()\n")
m.append("    app.run(host='0.0.0.0', port=args.port, debug=False)\n")
write("dashboard_new.py", m)

# Rename
os.rename(os.path.join(OUT, "dashboard.py"), os.path.join(OUT, "dashboard_monolith_backup.py"))
os.rename(os.path.join(OUT, "dashboard_new.py"), os.path.join(OUT, "dashboard.py"))
print("\nActivated: dashboard.py (modular)")
print("Backup: dashboard_monolith_backup.py")
