#!/usr/bin/env python3
"""Remove inline CSV endpoints from dashboard.py, register bp_csv blueprint instead."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

# 1. Remove the inline CSV upload code (appended at the end)
marker = "\n# ── CSV Upload Support ────────────────────────────────────"
if marker in content:
    idx = content.index(marker)
    content = content[:idx].rstrip() + "\n"
    print(f"Removed inline CSV code from line ~{content[:idx].count(chr(10))}")

# 2. Add blueprint import and registration before app.run
old_main = "    load_senders()\n    app.run("
new_main = """    load_senders()
    from bp_csv import csv_bp
    app.register_blueprint(csv_bp)
    app.run("""
content = content.replace(old_main, new_main)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - CSV code extracted to bp_csv.py blueprint")

# Check final line count
print(f"dashboard.py now: {content.count(chr(10))} lines")
