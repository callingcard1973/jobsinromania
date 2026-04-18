#!/usr/bin/env python3
"""Split the 3 remaining over-250 files."""
import os
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"

def split_at(fname, search_str, new_file, new_bp=None, old_bp=None):
    with open(os.path.join(OUT, fname)) as f:
        lines = f.readlines()
    j = None
    for i, line in enumerate(lines):
        if search_str in line and "import" not in line:
            j = i
            # Check if there's a decorator above
            if i > 0 and lines[i-1].strip().startswith("@"):
                j = i - 1
            break
    if j is None:
        print("  NOT FOUND: " + search_str)
        return
    # Write truncated original
    with open(os.path.join(OUT, fname), "w") as f:
        f.writelines(lines[:j])
    # Write new file
    with open(os.path.join(OUT, new_file), "w") as f:
        f.write("#!/usr/bin/env python3\n")
        f.write("import os, json, psycopg2, shutil, subprocess\n")
        f.write("from pathlib import Path\n")
        f.write("from datetime import datetime, timedelta\n")
        if new_bp:
            f.write("from flask import Blueprint, request, jsonify, redirect, render_template_string\n")
            f.write("from dashboard_helpers import *\n")
            try:
                __import__("dashboard_helpers2")
                f.write("from dashboard_helpers2 import *\n")
            except Exception:
                pass
            f.write("from dashboard_styles import STYLES\n")
            f.write("from dashboard_html import *\n")
            f.write("\n" + new_bp + " = Blueprint('" + new_bp + "', __name__)\n\n")
        else:
            f.write("from dashboard_helpers import *\n\n")
        for line in lines[j:]:
            if old_bp and new_bp:
                f.write(line.replace("@" + old_bp + ".route", "@" + new_bp + ".route"))
            else:
                f.write(line)
    a = j
    b = len(lines) - j + 10
    print("  " + fname + ": " + str(a) + " | " + new_file + ": " + str(b))

# 1. dashboard_helpers.py: split at campaign_stats
split_at("dashboard_helpers.py", "def campaign_stats", "dashboard_helpers2.py")

# 2. bp_pages.py: split at api_new_campaign
split_at("bp_pages.py", "def api_new_campaign", "bp_new_campaign.py", "new_bp", "pages_bp")

# 3. bp_api_core.py: split at api_send
split_at("bp_api_core.py", "def api_send", "bp_api_send.py", "api_send_bp", "api_core_bp")

# Update dashboard_v6.py
main_path = os.path.join(OUT, "dashboard_v6.py")
with open(main_path) as f:
    m = f.read()
if "bp_new_campaign" not in m:
    m = m.replace("from bp_pages import pages_bp\n",
                  "from bp_pages import pages_bp\nfrom bp_new_campaign import new_bp\n")
    m = m.replace("app.register_blueprint(pages_bp)\n",
                  "app.register_blueprint(pages_bp)\napp.register_blueprint(new_bp)\n")
if "bp_api_send" not in m:
    m = m.replace("from bp_api_core import api_core_bp\n",
                  "from bp_api_core import api_core_bp\nfrom bp_api_send import api_send_bp\n")
    m = m.replace("app.register_blueprint(api_core_bp)\n",
                  "app.register_blueprint(api_core_bp)\napp.register_blueprint(api_send_bp)\n")
with open(main_path, "w") as f:
    f.write(m)

# Summary
print()
for fn in sorted(os.listdir(OUT)):
    if fn.endswith(".py") and ("dashboard" in fn or "bp_" in fn):
        if "monolith" in fn or "old" in fn or "backup" in fn:
            continue
        p = os.path.join(OUT, fn)
        n = sum(1 for _ in open(p))
        if "html" in fn:
            tag = "DATA"
        elif n <= 250:
            tag = "OK"
        else:
            tag = "OVER"
        print("  " + fn + ": " + str(n) + " " + tag)
