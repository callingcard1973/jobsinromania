#!/usr/bin/env python3
"""Fix Jinja2 syntax error in template editor - curly braces in placeholder display."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/dashboard.py"
with open(path, "r") as f:
    content = f.read()

# The broken line tries to render {column_name} but Jinja2 chokes on nested braces
old_line = '''    <code class="ph" style="cursor:pointer;color:#38bdf8;margin:2px;padding:2px 6px;background:#0f172a;border:1px solid #334155;border-radius:4px;display:inline-block;" onclick="insertPh('{{'+'{{ col }}'+'}}')">{{'{'}}{{ col }}{{'}'}}</code>'''

new_line = '''    <code class="ph" style="cursor:pointer;color:#38bdf8;margin:2px;padding:2px 6px;background:#0f172a;border:1px solid #334155;border-radius:4px;display:inline-block;" onclick="insertPh('&#123;{{ col }}&#125;')">&#123;{{ col }}&#125;</code>'''

content = content.replace(old_line, new_line)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - Jinja2 syntax fixed")
