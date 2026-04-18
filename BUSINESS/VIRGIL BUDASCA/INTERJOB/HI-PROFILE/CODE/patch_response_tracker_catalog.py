#!/usr/bin/env python3
"""Patch response_tracker.py to call catalog_autoresponder on manpower_dristor inbox."""
path = "/opt/ACTIVE/INFRA/SKILLS/response_tracker.py"

with open(path, encoding="utf-8") as f:
    content = f.read()

if "catalog_autoresponder" in content:
    print("Already patched")
    exit()

# Add import after existing imports
old_import = "from solonet_pipeline import create_draft as solonet_draft"
new_import = (
    "from solonet_pipeline import create_draft as solonet_draft\n"
    "from catalog_autoresponder import handle_catalog_request"
)
content = content.replace(old_import, new_import)

# Add catalog check right after sender/subject/body/category extraction,
# before the AUTO_REPLY/BOUNCE check
old_block = "            if category in (\"AUTO_REPLY\", \"BOUNCE\"):"
new_block = (
    "            # Auto-send catalog if email was sent to catalog@domain\n"
    "            if handle_catalog_request(msg, sender, log):\n"
    "                continue\n\n"
    "            if category in (\"AUTO_REPLY\", \"BOUNCE\"):"
)
content = content.replace(old_block, new_block)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Patched response_tracker.py OK")
