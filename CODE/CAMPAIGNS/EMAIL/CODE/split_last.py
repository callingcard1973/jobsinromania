#!/usr/bin/env python3
"""Final splits for files over 250 lines."""
import os
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"

def split_file(fname, search_func, new_name, new_bp_name, old_bp_name):
    path = os.path.join(OUT, fname)
    with open(path) as f:
        lines = f.readlines()
    split_at = None
    for i, line in enumerate(lines):
        if search_func in line:
            j = i - 1
            while j > 0 and not lines[j].strip().startswith("@"):
                j -= 1
            split_at = j
            break
    if not split_at:
        print(f"  {fname}: could not find '{search_func}'")
        return
    with open(path, "w") as f:
        f.writelines(lines[:split_at])
    header = [
        "#!/usr/bin/env python3\n",
        f'"""Split from {fname}."""\n',
        "import os, json, psycopg2, shutil, subprocess\n",
        "from pathlib import Path\n",
        "from datetime import datetime, timedelta\n",
        "from flask import Blueprint, request, jsonify, redirect, render_template_string\n",
        "from dashboard_helpers import *\n",
        "from dashboard_html import *\n",
        f"\n{new_bp_name} = Blueprint('{new_bp_name}', __name__)\n\n",
    ]
    extra = list(header)
    for line in lines[split_at:]:
        extra.append(line.replace(f"@{old_bp_name}.route", f"@{new_bp_name}.route"))
    with open(os.path.join(OUT, new_name), "w") as f:
        f.writelines(extra)
    print(f"  {fname}: {split_at} lines")
    print(f"  {new_name}: {len(extra)} lines")

# 1. dashboard_helpers.py (286): split at get_daily_stats
split_file("dashboard_helpers.py", "def get_daily_stats", "dashboard_stats_helpers.py", "dummy", "dummy")
# stats helpers don't have routes, just fix the import
p = os.path.join(OUT, "dashboard_stats_helpers.py")
with open(p) as f:
    c = f.read()
# Remove blueprint stuff, it's just helper functions
c = c.replace("from flask import Blueprint, request, jsonify, redirect, render_template_string\n", "")
c = c.replace("from dashboard_html import *\n", "")
c = c.replace("\ndummy = Blueprint('dummy', __name__)\n\n", "\n")
c = c.replace("@dummy.route", "@BROKEN")  # should not happen
with open(p, "w") as f:
    f.write(c)

# 2. bp_pages.py (383): split at campaign_template (bigger functions)
split_file("bp_pages.py", "def campaign_logs", "bp_pages2.py", "pages2_bp", "pages_bp")

# 3. bp_api_core.py (274): split at api_send
split_file("bp_api_core.py", "def api_send", "bp_api_send.py", "api_send_bp", "api_core_bp")

# Update dashboard.py
main_path = os.path.join(OUT, "dashboard.py")
with open(main_path) as f:
    main = f.read()

# Add new imports
main = main.replace(
    "from bp_pages import pages_bp\n",
    "from bp_pages import pages_bp\nfrom bp_pages2 import pages2_bp\n"
)
main = main.replace(
    "from bp_api_core import api_core_bp\n",
    "from bp_api_core import api_core_bp\nfrom bp_api_send import api_send_bp\n"
)
main = main.replace(
    "app.register_blueprint(pages_bp)\n",
    "app.register_blueprint(pages_bp)\napp.register_blueprint(pages2_bp)\n"
)
main = main.replace(
    "app.register_blueprint(api_core_bp)\n",
    "app.register_blueprint(api_core_bp)\napp.register_blueprint(api_send_bp)\n"
)

with open(main_path, "w") as f:
    f.write(main)

# Summary
print("\n=== FINAL COUNTS ===")
for f in sorted(os.listdir(OUT)):
    if f.endswith(".py") and ("dashboard" in f or "bp_" in f):
        path = os.path.join(OUT, f)
        n = sum(1 for _ in open(path))
        status = "OK" if n <= 250 else "OVER"
        print(f"  {f}: {n} lines {status}")
