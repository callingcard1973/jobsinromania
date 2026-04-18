#!/usr/bin/env python3
"""Split dashboard.py (2907 lines) into modules under 250 lines each.

Strategy:
- Extract HTML templates to .html files in templates/ dir
- Split routes into Flask Blueprints:
  - dashboard.py (main): app init, helpers, config loading (~200 lines)
  - bp_pages.py: page routes (index, overview, edit, template, logs, etc.)
  - bp_api.py: API endpoints (toggle, update, schedules, alerts, etc.)
  - bp_csv.py: CSV upload/import + new campaign
"""
import re, os

SRC = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"
TPL = os.path.join(OUT, "templates")
os.makedirs(TPL, exist_ok=True)

with open(SRC) as f:
    content = f.read()

# ── Extract HTML templates to files ──
html_vars = {}
for match in re.finditer(r'^(\w+_HTML)\s*=\s*"""(.*?)"""', content, re.DOTALL | re.MULTILINE):
    var_name = match.group(1)
    html_content = match.group(2)
    fname = var_name.lower().replace("_html", "") + ".html"
    with open(os.path.join(TPL, fname), "w") as f:
        f.write(html_content)
    html_vars[var_name] = fname
    print(f"  Extracted {var_name} -> templates/{fname} ({len(html_content)} chars)")

# ── Build new dashboard.py (main app, helpers only) ──
# Read lines up to first HTML template, plus helpers and app init
lines = content.split("\n")

# Collect sections
imports_end = 0
helpers_start = 0
helpers_end = 0
first_html = 0

for i, line in enumerate(lines):
    if line.startswith("INDEX_HTML"):
        first_html = i
        break

# Write main dashboard.py
main_lines = []
# Imports and config
main_lines.append('#!/opt/ACTIVE/INFRA/venv/bin/python3')
main_lines.append('"""Campaign Dashboard v6 — Modular with Blueprints."""')
main_lines.append('import os, sys, json, glob, shutil, argparse, psycopg2')
main_lines.append('from pathlib import Path')
main_lines.append('from datetime import datetime, timedelta')
main_lines.append('from flask import Flask')
main_lines.append('')
main_lines.append('app = Flask(__name__, template_folder="templates")')
main_lines.append('')

# Copy all code from line 0 to first_html (helpers, config, etc.)
# but skip the original imports and app creation
in_func = False
for i in range(0, first_html):
    line = lines[i]
    # Skip original shebang, docstring, imports, app creation
    if i < 42:
        continue
    main_lines.append(line)

# Add blueprint registration and main block
main_lines.append('')
main_lines.append('# ── Register Blueprints ──')
main_lines.append('from bp_pages import pages_bp')
main_lines.append('from bp_api import api_bp')
main_lines.append('from bp_csv import csv_bp')
main_lines.append('app.register_blueprint(pages_bp)')
main_lines.append('app.register_blueprint(api_bp)')
main_lines.append('app.register_blueprint(csv_bp)')
main_lines.append('')

# Find and copy the main block
for i, line in enumerate(lines):
    if 'if __name__' in line or 'app.run' in line or 'argparse' in line:
        if i > 2700:  # near the end
            main_lines.append(line)

main_lines.append('')
main_lines.append('if __name__ == "__main__":')
main_lines.append('    parser = argparse.ArgumentParser()')
main_lines.append('    parser.add_argument("--port", type=int, default=8090)')
main_lines.append('    parser.add_argument("--configs", default=str(CONFIGS_DIR))')
main_lines.append('    args = parser.parse_args()')
main_lines.append('    CONFIGS_DIR = Path(args.configs)')
main_lines.append('    load_all_configs(CONFIGS_DIR)')
main_lines.append('    load_senders()')
main_lines.append('    app.run(host="0.0.0.0", port=args.port, debug=False)')

# Check line count
print(f"\nMain dashboard.py: {len(main_lines)} lines")
if len(main_lines) > 250:
    print(f"  WARNING: {len(main_lines)} lines > 250 limit")

# Don't write yet - this is a dry run to show the plan
print(f"\nHTML templates extracted: {len(html_vars)}")
print(f"Templates dir: {TPL}")
for var, fname in html_vars.items():
    fpath = os.path.join(TPL, fname)
    print(f"  {fname}: {os.path.getsize(fpath)} bytes")

print("\nPlan complete. The full split requires extracting route functions into bp_pages.py, bp_api.py, bp_csv.py")
print("Each blueprint imports shared helpers from dashboard_helpers.py")
print("This is a large refactor - confirming approach before writing files.")
