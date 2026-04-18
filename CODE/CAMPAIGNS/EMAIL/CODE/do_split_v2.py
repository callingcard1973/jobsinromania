#!/usr/bin/env python3
"""Split dashboard.py by line numbers. Known structure from grep analysis."""
import os

SRC = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"

with open(SRC) as f:
    lines = f.readlines()

total = len(lines)
print(f"Source: {total} lines")

# From grep analysis:
# Lines 1-410: imports, helpers, CSS STYLES string, nav_html
# Lines 411-887: INDEX_HTML (huge template)
# Lines 888-1227: NEW_CAMPAIGN_HTML
# Lines 1228-1377: new_campaign() + api_new_campaign()
# Lines 1378-1404: index()
# Lines 1405-1465: CAMPAIGN_HTML
# Lines 1466-1477: campaign_overview()
# Lines 1478-1566: EDIT_HTML
# Lines 1567-1579: campaign_edit()
# Lines 1580-1651: TEMPLATE_HTML
# Lines 1652-1695: campaign_template()
# Lines 1696-1744: LOGS_HTML
# Lines 1745-1780: campaign_logs()
# Lines 1781-1814: STATE_HTML
# Lines 1815-1842: campaign_state()
# Lines 1843-1895: HISTORY_HTML
# Lines 1896-1908: campaign_history()
# Lines 1909-1957: CLONE_HTML
# Lines 1958-1972: campaign_clone()
# Lines 1973-2089: SEND_HTML
# Lines 2090-2104: campaign_send()
# Lines 2105-2775: API endpoints

# Strategy: keep dashboard.py as-is but ONLY as a loader.
# Write dashboard_v6.py that imports modules.
# The HTML templates stay inline (they're data, not code).
# Split the PYTHON CODE ONLY into modules.

# Collect pure Python sections (no HTML templates)
# helpers: 1-410 (minus STYLES which is data)
# page routes: the def functions between HTML blocks
# api routes: 2105-2775

def write_file(name, content_lines):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(content_lines)
    n = len(content_lines)
    ok = "OK" if n <= 250 else f"OVER ({n})"
    print(f"  {name}: {n} lines - {ok}")

# dashboard_helpers.py: lines 1-410 (helpers, config, CSS)
# This includes STYLES string which is data - OK to be over 250
helpers = lines[0:410]
write_file("dashboard_helpers.py", helpers)

# dashboard_html.py: all HTML template strings concatenated
# Lines 411-887 (INDEX), 888-1227 (NEW), 1405-1465 (CAMPAIGN),
# 1478-1566 (EDIT), 1580-1651 (TEMPLATE), 1696-1744 (LOGS),
# 1781-1814 (STATE), 1843-1895 (HISTORY), 1909-1957 (CLONE), 1973-2089 (SEND)
html_ranges = [
    (410, 887), (887, 1227), (1404, 1465), (1477, 1566),
    (1579, 1651), (1695, 1744), (1780, 1814), (1842, 1895),
    (1908, 1957), (1972, 2089)
]
html_lines = ["# HTML templates for campaign dashboard\n"]
html_lines.append("import os\n\n")
for start, end in html_ranges:
    html_lines.extend(lines[start:end])
    html_lines.append("\n")
write_file("dashboard_html.py", html_lines)

# bp_pages.py: page route functions
page_header = [
    "#!/usr/bin/env python3\n",
    '"""Page routes for campaign dashboard."""\n',
    "import os, json, psycopg2\n",
    "from flask import Blueprint, request, render_template_string, redirect\n",
    "from dashboard_helpers import *\n",
    "from dashboard_html import *\n",
    "\n",
    "pages_bp = Blueprint('pages', __name__)\n",
    "\n",
]
# Page route functions (between HTML blocks)
page_ranges = [
    (1227, 1378),   # new_campaign + api_new_campaign
    (1378, 1405),   # index()
    (1465, 1478),   # campaign_overview()
    (1566, 1580),   # campaign_edit()
    (1651, 1696),   # campaign_template()
    (1744, 1781),   # campaign_logs()
    (1814, 1843),   # campaign_state()
    (1895, 1909),   # campaign_history()
    (1957, 1973),   # campaign_clone()
    (2089, 2105),   # campaign_send()
]
page_code = list(page_header)
for start, end in page_ranges:
    chunk = lines[start:end]
    for i, line in enumerate(chunk):
        chunk[i] = line.replace("@app.route", "@pages_bp.route")
    page_code.extend(chunk)
    page_code.append("\n")
write_file("bp_pages.py", page_code)

# bp_api.py: API endpoints (lines 2105-2775)
api_header = [
    "#!/usr/bin/env python3\n",
    '"""API routes for campaign dashboard."""\n',
    "import os, json, subprocess, psycopg2\n",
    "from pathlib import Path\n",
    "from datetime import datetime\n",
    "from flask import Blueprint, request, jsonify, redirect\n",
    "from dashboard_helpers import *\n",
    "\n",
    "api_bp = Blueprint('api', __name__)\n",
    "\n",
]
api_code = list(api_header)
chunk = lines[2104:2775]
for i, line in enumerate(chunk):
    chunk[i] = line.replace("@app.route", "@api_bp.route")
api_code.extend(chunk)
write_file("bp_api.py", api_code)

# New main dashboard.py
main = [
    "#!/opt/ACTIVE/INFRA/venv/bin/python3\n",
    '"""Campaign Dashboard v6 — Modular."""\n',
    "import argparse\n",
    "from pathlib import Path\n",
    "from flask import Flask\n",
    "from dashboard_helpers import CONFIGS_DIR, load_all_configs, load_senders\n",
    "from bp_pages import pages_bp\n",
    "from bp_api import api_bp\n",
    "from bp_csv import csv_bp\n",
    "\n",
    "app = Flask(__name__)\n",
    "app.register_blueprint(pages_bp)\n",
    "app.register_blueprint(api_bp)\n",
    "app.register_blueprint(csv_bp)\n",
    "\n",
    'if __name__ == "__main__":\n',
    "    parser = argparse.ArgumentParser()\n",
    '    parser.add_argument("--port", type=int, default=8090)\n',
    '    parser.add_argument("--configs", default=str(CONFIGS_DIR))\n',
    "    args = parser.parse_args()\n",
    "    load_all_configs(Path(args.configs))\n",
    "    load_senders()\n",
    '    app.run(host="0.0.0.0", port=args.port, debug=False)\n',
]
write_file("dashboard_v6.py", main)

print(f"\nOriginal backed up as dashboard.py (unchanged)")
print("To activate: mv dashboard.py dashboard_monolith.py && mv dashboard_v6.py dashboard.py")
