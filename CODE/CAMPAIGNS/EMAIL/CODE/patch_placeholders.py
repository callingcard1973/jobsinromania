#!/usr/bin/env python3
"""Patch send_campaign.py to support ALL database columns as template placeholders."""

path = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py"
with open(path, "r") as f:
    content = f.read()

# Find the end of expand_template's hardcoded replacements and add generic replacement
old_end = """        subject = subject.replace(old, new)
        body = body.replace(old, new)

    return subject, body"""

new_end = """        subject = subject.replace(old, new)
        body = body.replace(old, new)

    # Generic: replace ANY {column_name} from the contact dict
    for key, val in contact.items():
        placeholder = '{' + str(key) + '}'
        if placeholder in subject or placeholder in body:
            subject = subject.replace(placeholder, str(val or ''))
            body = body.replace(placeholder, str(val or ''))

    return subject, body"""

content = content.replace(old_end, new_end)

with open(path, "w") as f:
    f.write(content)

print("PATCHED OK - All column names now work as {placeholder} in templates")
