#!/usr/bin/env python3
"""Split dashboard.py into files under 250 lines each.
Writes: dashboard_helpers.py, bp_pages.py, bp_api.py, bp_csv.py (already done), dashboard.py (main)
HTML templates go to templates/ folder as .html files.
"""
import re, os

SRC = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"
TPL = os.path.join(OUT, "templates")
os.makedirs(TPL, exist_ok=True)

with open(SRC) as f:
    raw = f.read()

# Step 1: Extract all HTML template strings to files
pattern = r'^([A-Z_]+_HTML)\s*=\s*"""(.*?)^"""'
templates = {}
for m in re.finditer(pattern, raw, re.DOTALL | re.MULTILINE):
    var = m.group(1)
    html = m.group(2)
    fname = var.lower().replace("_html", "") + ".html"
    with open(os.path.join(TPL, fname), "w", encoding="utf-8") as f:
        f.write(html)
    templates[var] = fname
    print(f"  {var} -> templates/{fname} ({len(html.splitlines())} lines)")

# Step 2: Remove HTML strings from source, replace with file reads
cleaned = raw
for var, fname in templates.items():
    pattern_specific = re.compile(
        r'^' + re.escape(var) + r'\s*=\s*""".*?^"""',
        re.DOTALL | re.MULTILINE
    )
    replacement = f'{var} = open(os.path.join(os.path.dirname(__file__), "templates", "{fname}")).read()'
    cleaned = pattern_specific.sub(replacement, cleaned)

# Step 3: Find route functions and split into categories
lines = cleaned.split("\n")

# Identify line ranges for each section
helpers_end = 0
pages_routes = []  # (start, end, name)
api_routes = []

i = 0
while i < len(lines):
    line = lines[i]
    # Find @app.route lines
    if line.startswith("@app.route"):
        route_start = i
        # Find the def line
        j = i + 1
        while j < len(lines) and not lines[j].startswith("def "):
            j += 1
        if j < len(lines):
            func_name = lines[j].split("(")[0].replace("def ", "").strip()
            # Find end of function
            k = j + 1
            while k < len(lines):
                if lines[k] and not lines[k][0].isspace() and not lines[k].startswith("#"):
                    break
                k += 1
            route_info = (route_start, k, func_name)
            if "/api/" in line or func_name.startswith("api_"):
                api_routes.append(route_info)
            else:
                pages_routes.append(route_info)
            i = k
            continue
    # Track where helpers end (first route or HTML var)
    if line.startswith("@app.route") and helpers_end == 0:
        helpers_end = i
    i += 1

print(f"\nHelpers: lines 0-{helpers_end} ({helpers_end} lines)")
print(f"Page routes: {len(pages_routes)}")
print(f"API routes: {len(api_routes)}")

# Step 4: Write dashboard_helpers.py (shared code)
helper_lines = lines[:helpers_end]
# Remove app creation - will be in main
helper_clean = []
for line in helper_lines:
    if line.strip().startswith("app = Flask"):
        continue
    helper_clean.append(line)

with open(os.path.join(OUT, "dashboard_helpers.py"), "w", encoding="utf-8") as f:
    f.write("\n".join(helper_clean))
print(f"dashboard_helpers.py: {len(helper_clean)} lines")

# Step 5: Write bp_pages.py
page_lines = []
page_lines.append("#!/usr/bin/env python3")
page_lines.append('"""Page routes for campaign dashboard."""')
page_lines.append("import os, json, psycopg2")
page_lines.append("from pathlib import Path")
page_lines.append("from datetime import datetime, timedelta")
page_lines.append("from flask import Blueprint, request, render_template_string, redirect, jsonify")
page_lines.append("from dashboard_helpers import *")
page_lines.append("")
page_lines.append("pages_bp = Blueprint('pages', __name__)")
page_lines.append("")

for start, end, name in pages_routes:
    chunk = lines[start:end]
    # Replace @app.route with @pages_bp.route
    for ci, cl in enumerate(chunk):
        chunk[ci] = cl.replace("@app.route", "@pages_bp.route")
    page_lines.extend(chunk)
    page_lines.append("")

with open(os.path.join(OUT, "bp_pages.py"), "w", encoding="utf-8") as f:
    f.write("\n".join(page_lines))
print(f"bp_pages.py: {len(page_lines)} lines")

# Step 6: Write bp_api.py
api_lines = []
api_lines.append("#!/usr/bin/env python3")
api_lines.append('"""API routes for campaign dashboard."""')
api_lines.append("import os, json, psycopg2, subprocess")
api_lines.append("from pathlib import Path")
api_lines.append("from datetime import datetime")
api_lines.append("from flask import Blueprint, request, jsonify, redirect")
api_lines.append("from dashboard_helpers import *")
api_lines.append("")
api_lines.append("api_bp = Blueprint('api', __name__)")
api_lines.append("")

for start, end, name in api_routes:
    chunk = lines[start:end]
    for ci, cl in enumerate(chunk):
        chunk[ci] = cl.replace("@app.route", "@api_bp.route")
    api_lines.extend(chunk)
    api_lines.append("")

with open(os.path.join(OUT, "bp_api.py"), "w", encoding="utf-8") as f:
    f.write("\n".join(api_lines))
print(f"bp_api.py: {len(api_lines)} lines")

# Step 7: Write new dashboard.py (just app init + blueprint registration)
main = []
main.append("#!/opt/ACTIVE/INFRA/venv/bin/python3")
main.append('"""Campaign Dashboard v6 — Modular."""')
main.append("import argparse")
main.append("from pathlib import Path")
main.append("from flask import Flask")
main.append("from dashboard_helpers import CONFIGS_DIR, load_all_configs, load_senders")
main.append("from bp_pages import pages_bp")
main.append("from bp_api import api_bp")
main.append("from bp_csv import csv_bp")
main.append("")
main.append("app = Flask(__name__)")
main.append("app.register_blueprint(pages_bp)")
main.append("app.register_blueprint(api_bp)")
main.append("app.register_blueprint(csv_bp)")
main.append("")
main.append('if __name__ == "__main__":')
main.append("    parser = argparse.ArgumentParser()")
main.append('    parser.add_argument("--port", type=int, default=8090)')
main.append('    parser.add_argument("--configs", default=str(CONFIGS_DIR))')
main.append("    args = parser.parse_args()")
main.append("    load_all_configs(Path(args.configs))")
main.append("    load_senders()")
main.append('    app.run(host="0.0.0.0", port=args.port, debug=False)')

with open(os.path.join(OUT, "dashboard_new.py"), "w", encoding="utf-8") as f:
    f.write("\n".join(main))
print(f"dashboard_new.py: {len(main)} lines")

print("\n=== SUMMARY ===")
for fname in ["dashboard_helpers.py", "bp_pages.py", "bp_api.py", "bp_csv.py", "dashboard_new.py"]:
    fpath = os.path.join(OUT, fname)
    if os.path.exists(fpath):
        with open(fpath) as f:
            n = len(f.readlines())
        status = "OK" if n <= 250 else f"OVER ({n})"
        print(f"  {fname}: {n} lines - {status}")
print(f"  templates/: {len(templates)} HTML files")
