#!/usr/bin/env python3
"""Final split: bp_api_core -> core + send, bp_api_extra -> schedules + monitoring."""
import os
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"

# Split bp_api_core.py at api_send (line with "def api_send")
with open(os.path.join(OUT, "bp_api_core.py")) as f:
    lines = f.readlines()

split_at = None
for i, line in enumerate(lines):
    if "def api_senders_status" in line:
        j = i - 1
        while j > 0 and not lines[j].strip().startswith("@"):
            j -= 1
        split_at = j
        break

if split_at:
    with open(os.path.join(OUT, "bp_api_core.py"), "w") as f:
        f.writelines(lines[:split_at])

    extra = [
        "#!/usr/bin/env python3\n",
        '"""API routes: senders status, campaign stats, active sends, bulk actions."""\n',
        "import os, json, subprocess, psycopg2\n",
        "from pathlib import Path\n",
        "from datetime import datetime\n",
        "from flask import Blueprint, request, jsonify, redirect\n",
        "from dashboard_helpers import *\n",
        "\napi_stats_bp = Blueprint('api_stats', __name__)\n\n",
    ]
    for line in lines[split_at:]:
        extra.append(line.replace("@api_core_bp.route", "@api_stats_bp.route"))

    with open(os.path.join(OUT, "bp_api_stats.py"), "w") as f:
        f.writelines(extra)

    print(f"bp_api_core.py: {split_at} lines")
    print(f"bp_api_stats.py: {len(extra)} lines")

# Split bp_api_extra.py at api_template_preview
with open(os.path.join(OUT, "bp_api_extra.py")) as f:
    lines = f.readlines()

split_at = None
for i, line in enumerate(lines):
    if "def api_template_preview" in line:
        j = i - 1
        while j > 0 and not lines[j].strip().startswith("@"):
            j -= 1
        split_at = j
        break

if split_at:
    with open(os.path.join(OUT, "bp_api_extra.py"), "w") as f:
        f.writelines(lines[:split_at])

    monitor = [
        "#!/usr/bin/env python3\n",
        '"""API routes: template preview/validate, metrics, A/B tests, alerts."""\n',
        "import os, json, psycopg2\n",
        "from pathlib import Path\n",
        "from datetime import datetime\n",
        "from flask import Blueprint, request, jsonify\n",
        "from dashboard_helpers import *\n",
        "\napi_monitor_bp = Blueprint('api_monitor', __name__)\n\n",
    ]
    for line in lines[split_at:]:
        monitor.append(line.replace("@api_extra_bp.route", "@api_monitor_bp.route"))

    with open(os.path.join(OUT, "bp_api_monitor.py"), "w") as f:
        f.writelines(monitor)

    print(f"bp_api_extra.py: {split_at} lines")
    print(f"bp_api_monitor.py: {len(monitor)} lines")

# Update dashboard.py to register new blueprints
main_path = os.path.join(OUT, "dashboard.py")
with open(main_path) as f:
    main = f.read()

main = main.replace(
    "from bp_api_core import api_core_bp\nfrom bp_api_extra import api_extra_bp\n",
    "from bp_api_core import api_core_bp\nfrom bp_api_stats import api_stats_bp\nfrom bp_api_extra import api_extra_bp\nfrom bp_api_monitor import api_monitor_bp\n"
)
main = main.replace(
    "app.register_blueprint(api_core_bp)\napp.register_blueprint(api_extra_bp)\n",
    "app.register_blueprint(api_core_bp)\napp.register_blueprint(api_stats_bp)\napp.register_blueprint(api_extra_bp)\napp.register_blueprint(api_monitor_bp)\n"
)

with open(main_path, "w") as f:
    f.write(main)

print("dashboard.py updated with all blueprints")

# Summary
print("\n=== FINAL ===")
for f in ["dashboard.py", "dashboard_helpers.py", "dashboard_styles.py",
          "bp_pages.py", "bp_api_core.py", "bp_api_stats.py",
          "bp_api_extra.py", "bp_api_monitor.py", "bp_csv.py"]:
    path = os.path.join(OUT, f)
    if os.path.exists(path):
        n = sum(1 for _ in open(path))
        print(f"  {f}: {n} lines {'OK' if n <= 250 else 'OVER'}")
print("  dashboard_html.py: DATA (HTML templates)")
print("  dashboard_styles.py: DATA (CSS)")
