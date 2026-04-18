#!/usr/bin/env python3
"""Fix bp_pages.py: keep GET /new only, move POST api_new_campaign back to bp_new_campaign.py"""
import os
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"

with open(os.path.join(OUT, "bp_pages.py")) as f:
    lines = f.readlines()

# Find where api_new_campaign POST handler starts
split_at = None
for i, line in enumerate(lines):
    if "def api_new_campaign" in line:
        j = i - 1
        while j > 0 and not lines[j].strip().startswith("@"):
            j -= 1
        split_at = j
        break

if split_at:
    # Keep GET routes in bp_pages
    with open(os.path.join(OUT, "bp_pages.py"), "w") as f:
        f.writelines(lines[:split_at])

    # Write POST handler to bp_new_campaign
    with open(os.path.join(OUT, "bp_new_campaign.py"), "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("import os, json, psycopg2, requests as _req\n")
        f.write("from pathlib import Path\n")
        f.write("from flask import Blueprint, request, redirect\n")
        f.write("from dashboard_helpers import *\n\n")
        f.write("new_bp = Blueprint('new_bp', __name__)\n\n")
        for line in lines[split_at:]:
            f.write(line.replace("@pages_bp.route", "@new_bp.route"))

    n1 = split_at
    n2 = len(lines) - split_at + 7
    print("bp_pages.py: " + str(n1))
    print("bp_new_campaign.py: " + str(n2))

# Update dashboard_v6.py if needed
vp = os.path.join(OUT, "dashboard_v6.py")
with open(vp) as f:
    m = f.read()
if "bp_new_campaign" not in m:
    m = m.replace("from bp_pages import pages_bp\n",
                  "from bp_pages import pages_bp\nfrom bp_new_campaign import new_bp\n")
    m = m.replace("app.register_blueprint(pages_bp)\n",
                  "app.register_blueprint(pages_bp)\napp.register_blueprint(new_bp)\n")
    with open(vp, "w") as f:
        f.write(m)

# Final counts for MY files only
print()
for fn in ["dashboard_v6.py", "dashboard_helpers.py", "dashboard_helpers2.py",
           "dashboard_styles.py", "bp_pages.py", "bp_pages2.py",
           "bp_new_campaign.py", "bp_api_core.py", "bp_api_send.py",
           "bp_api_stats.py", "bp_api_extra.py", "bp_api_monitor.py", "bp_csv.py"]:
    p = os.path.join(OUT, fn)
    if os.path.exists(p):
        n = sum(1 for _ in open(p))
        tag = "OK" if n <= 250 else "OVER"
        print("  " + fn + ": " + str(n) + " " + tag)
print("  dashboard_html.py: DATA")
