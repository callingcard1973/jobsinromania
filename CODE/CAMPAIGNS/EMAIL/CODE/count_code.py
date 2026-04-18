#!/usr/bin/env python3
import os
OUT = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED"
for fname in ["dashboard_helpers.py", "bp_pages.py", "bp_api.py"]:
    path = os.path.join(OUT, fname)
    if not os.path.exists(path):
        continue
    with open(path) as f:
        lines = f.readlines()
    in_str = False
    code = 0
    for line in lines:
        if '"""' in line.strip():
            in_str = not in_str
            continue
        if not in_str:
            code += 1
    print(f"{fname}: {len(lines)} total, ~{code} code, ~{len(lines)-code} data/html")
