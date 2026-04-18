#!/usr/bin/env python3
"""Split bp_api.py into bp_api.py (core) + bp_api_extra.py (schedules/alerts/monitoring)."""
import os

OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"
path = os.path.join(OUT, "bp_api.py")

with open(path) as f:
    lines = f.readlines()

# Find the split point: schedules start around "api_list_schedules"
split_at = None
for i, line in enumerate(lines):
    if "def api_list_schedules" in line:
        # Go back to find the @route decorator
        j = i - 1
        while j > 0 and not lines[j].strip().startswith("@"):
            j -= 1
        split_at = j
        break

if split_at is None:
    print("Could not find split point")
    exit(1)

core = lines[:split_at]
extra_body = lines[split_at:]

# Write core
with open(os.path.join(OUT, "bp_api.py"), "w") as f:
    f.writelines(core)
print(f"bp_api.py: {len(core)} lines")

# Write extra with its own blueprint
extra_header = [
    "#!/usr/bin/env python3\n",
    '"""Extra API routes: schedules, alerts, monitoring, A/B tests."""\n',
    "import os, json, subprocess, psycopg2\n",
    "from pathlib import Path\n",
    "from datetime import datetime\n",
    "from flask import Blueprint, request, jsonify, redirect\n",
    "from dashboard_helpers import *\n",
    "\n",
    "api_extra_bp = Blueprint('api_extra', __name__)\n",
    "\n",
]
extra = list(extra_header)
for line in extra_body:
    extra.append(line.replace("@api_bp.route", "@api_extra_bp.route"))

with open(os.path.join(OUT, "bp_api_extra.py"), "w") as f:
    f.writelines(extra)
print(f"bp_api_extra.py: {len(extra)} lines")

# Update dashboard_v6.py to register the extra blueprint
main_path = os.path.join(OUT, "dashboard_v6.py")
with open(main_path) as f:
    main = f.read()

main = main.replace(
    "from bp_api import api_bp",
    "from bp_api import api_bp\nfrom bp_api_extra import api_extra_bp"
)
main = main.replace(
    "app.register_blueprint(api_bp)",
    "app.register_blueprint(api_bp)\napp.register_blueprint(api_extra_bp)"
)

with open(main_path, "w") as f:
    f.write(main)
print(f"dashboard_v6.py updated")
