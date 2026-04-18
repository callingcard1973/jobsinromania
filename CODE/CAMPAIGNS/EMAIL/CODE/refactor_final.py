#!/usr/bin/env python3
"""Full refactor: fix STYLES concatenation, extract templates, split all code <=250 lines."""
import os, re

SRC = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"

with open(SRC) as f:
    raw = f.read()

# Step 1: Replace """ + STYLES + """ with {{ styles }} in all HTML templates
# This makes templates standalone strings instead of expressions
raw = raw.replace('""" + STYLES + """', '{{ styles }}')
# Also handle nav insertion patterns
raw = raw.replace("\"\"\" + nav_html(prefix, 'template') + \"\"\"", "{{ nav|safe }}")

# Now every *_HTML is a clean triple-quoted string.
# Step 2: Add styles= to every render_template_string call
# Find all render_template_string calls and add styles=STYLES
raw = re.sub(
    r'render_template_string\((\w+_HTML)',
    r'render_template_string(\1, styles=STYLES',
    raw
)

# Step 3: Extract line ranges using the now-clean source
lines = raw.split("\n")

def get_range(start_line, end_line):
    return "\n".join(lines[start_line-1:end_line-1]) + "\n"

# Find all key markers
markers = {}
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if stripped.startswith("STYLES ="):
        markers["styles_start"] = i
    elif stripped.startswith("INDEX_HTML ="):
        markers["index_start"] = i
    elif stripped.startswith("NEW_CAMPAIGN_HTML ="):
        markers["new_start"] = i
    elif stripped.startswith("CAMPAIGN_HTML =") and "NEW" not in stripped:
        markers["campaign_start"] = i
    elif stripped.startswith("EDIT_HTML ="):
        markers["edit_start"] = i
    elif stripped.startswith("TEMPLATE_HTML ="):
        markers["template_start"] = i
    elif stripped.startswith("LOGS_HTML ="):
        markers["logs_start"] = i
    elif stripped.startswith("STATE_HTML ="):
        markers["state_start"] = i
    elif stripped.startswith("HISTORY_HTML ="):
        markers["history_start"] = i
    elif stripped.startswith("CLONE_HTML ="):
        markers["clone_start"] = i
    elif stripped.startswith("SEND_HTML ="):
        markers["send_start"] = i
    elif stripped.startswith("@app.route('/new')"):
        markers["new_route"] = i
    elif stripped.startswith("@app.route('/')") and "prefix" not in stripped and "api" not in stripped:
        markers["index_route"] = i
    elif stripped.startswith("@app.route('/<prefix>/')"):
        markers["overview_route"] = i
    elif stripped.startswith("@app.route('/<prefix>/edit')"):
        markers["edit_route"] = i
    elif stripped.startswith("@app.route('/<prefix>/template')"):
        markers["template_route"] = i
    elif stripped.startswith("@app.route('/<prefix>/logs')"):
        markers["logs_route"] = i
    elif stripped.startswith("@app.route('/<prefix>/state')"):
        markers["state_route"] = i
    elif stripped.startswith("@app.route('/<prefix>/history')"):
        markers["history_route"] = i
    elif stripped.startswith("@app.route('/<prefix>/clone')"):
        markers["clone_route"] = i
    elif stripped.startswith("@app.route('/<prefix>/send')"):
        markers["send_route"] = i
    elif "# ── API Endpoints" in line:
        markers["api_start"] = i
    elif stripped.startswith("@app.route('/api/schedules')"):
        markers["schedules_start"] = i
    elif stripped.startswith("@app.route('/api/template/preview"):
        markers["tpl_preview_start"] = i
    elif stripped.startswith("if __name__"):
        markers["main_start"] = i

for k, v in sorted(markers.items(), key=lambda x: x[1]):
    print(f"  {v:5d}: {k}")

total = len(lines)

# Step 4: Write files

def write(name, content):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    n = content.count("\n")
    ok = "OK" if n <= 250 else f"OVER ({n})"
    print(f"  {name}: {n} lines {ok}")

# helpers: line 1 to styles_start (imports, app creation, helpers, nav_html)
helpers_end = markers["styles_start"] - 1
helpers_src = "\n".join(lines[:helpers_end])
# Remove app = Flask line, will be in main
helpers_src = helpers_src.replace("app = Flask(__name__)\n", "")
write("dashboard_helpers.py", helpers_src)

# styles: STYLES string
styles_end = markers["index_start"] - 1
write("dashboard_styles.py", "\n".join(lines[markers["styles_start"]-1:styles_end]))

# HTML templates: each one from its start to the next section
html_sections = [
    ("index_start", "new_start"),
    ("new_start", "new_route"),
    ("campaign_start", "overview_route"),
    ("edit_start", "edit_route"),
    ("template_start", "template_route"),
    ("logs_start", "logs_route"),
    ("state_start", "state_route"),
    ("history_start", "history_route"),
    ("clone_start", "clone_route"),
    ("send_start", "send_route"),
]
html_content = "#!/usr/bin/env python3\n# HTML templates (DATA)\nfrom dashboard_styles import STYLES\n\n"
for start_key, end_key in html_sections:
    s = markers.get(start_key)
    e = markers.get(end_key)
    if s and e:
        html_content += "\n".join(lines[s-1:e-1]) + "\n\n"
write("dashboard_html.py", html_content)

# Page routes: collected between HTML blocks
page_sections = [
    (markers["new_route"], markers.get("campaign_start", markers["index_route"])),
    (markers["index_route"], markers["campaign_start"]),
    (markers["overview_route"], markers["edit_start"]),
    (markers["edit_route"], markers["template_start"]),
    (markers["template_route"], markers["logs_start"]),
    (markers["logs_route"], markers["state_start"]),
    (markers["state_route"], markers["history_start"]),
    (markers["history_route"], markers["clone_start"]),
    (markers["clone_route"], markers["send_start"]),
    (markers["send_route"], markers["api_start"]),
]

# Split pages into 2 files
mid = len(page_sections) // 2
for idx, (name, bp_name, sections) in enumerate([
    ("bp_pages.py", "pages_bp", page_sections[:mid]),
    ("bp_pages2.py", "pages2_bp", page_sections[mid:]),
]):
    header = f"""#!/usr/bin/env python3
import os, json, psycopg2
from pathlib import Path
from datetime import datetime, timedelta
from flask import Blueprint, request, render_template_string, redirect, jsonify
from dashboard_helpers import *
from dashboard_styles import STYLES
from dashboard_html import *

{bp_name} = Blueprint('{bp_name}', __name__)

"""
    body = ""
    for s, e in sections:
        chunk = "\n".join(lines[s-1:e-1])
        chunk = chunk.replace("@app.route", f"@{bp_name}.route")
        body += chunk + "\n\n"
    write(name, header + body)

# API routes: split into 3
api_end = markers.get("schedules_start", total)
sched_end = markers.get("tpl_preview_start", total)
main_end = markers.get("main_start", total)

for name, bp, s, e in [
    ("bp_api_core.py", "api_core_bp", markers["api_start"], api_end),
    ("bp_api_extra.py", "api_extra_bp", api_end, sched_end),
    ("bp_api_monitor.py", "api_monitor_bp", sched_end, main_end),
]:
    header = f"""#!/usr/bin/env python3
import os, json, subprocess, psycopg2, shutil
from pathlib import Path
from datetime import datetime
from flask import Blueprint, request, jsonify, redirect
from dashboard_helpers import *
from dashboard_styles import STYLES
from dashboard_html import *

{bp} = Blueprint('{bp}', __name__)

"""
    chunk = "\n".join(lines[s-1:e-1])
    chunk = chunk.replace("@app.route", f"@{bp}.route")
    write(name, header + chunk)

# Main entry
main = """#!/opt/ACTIVE/INFRA/venv/bin/python3
\"\"\"Campaign Dashboard v6 — Modular.\"\"\"
import argparse
from pathlib import Path
from flask import Flask
from dashboard_helpers import CONFIGS_DIR, load_all_configs, load_senders
from bp_pages import pages_bp
from bp_pages2 import pages2_bp
from bp_api_core import api_core_bp
from bp_api_extra import api_extra_bp
from bp_api_monitor import api_monitor_bp
from bp_csv import csv_bp

app = Flask(__name__)
app.register_blueprint(pages_bp)
app.register_blueprint(pages2_bp)
app.register_blueprint(api_core_bp)
app.register_blueprint(api_extra_bp)
app.register_blueprint(api_monitor_bp)
app.register_blueprint(csv_bp)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8090)
    parser.add_argument('--configs', default=str(CONFIGS_DIR))
    args = parser.parse_args()
    load_all_configs(Path(args.configs))
    load_senders()
    app.run(host='0.0.0.0', port=args.port, debug=False)
"""
write("dashboard_v6.py", main)

print("\nDone. Run: mv dashboard.py dashboard_old.py && mv dashboard_v6.py dashboard.py")
