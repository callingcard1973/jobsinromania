"""Fix response_tracker to only alert on INTERESTED employers."""
f = "/opt/ACTIVE/INFRA/SKILLS/response_tracker.py"
lines = open(f).readlines()
result = []
skip_alert = False
for i, line in enumerate(lines):
    if 'icons = {"INTERESTED"' in line:
        skip_alert = True
        result.append("            # Only alert on INTERESTED employers\n")
        result.append("            if category == 'INTERESTED':\n")
        result.append('                alert(f"\\U0001f7e2 <b>NEW EMPLOYER LEAD</b> - {campaign}\\n"\n')
        result.append('                      f"From: {sender}\\nSubject: {subject[:80]}\\n"\n')
        result.append('                      f"Preview: {body[:150]}")\n')
        continue
    if skip_alert:
        if "save_response_db" in line:
            skip_alert = False
            result.append(line)
        continue
    result.append(line)
open(f, "w").writelines(result)
print(f"Fixed: {len(result)} lines")
