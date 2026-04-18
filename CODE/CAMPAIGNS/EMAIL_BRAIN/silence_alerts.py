"""Silence non-employer alerts. Only INTERESTED .ro employers + failures + digest."""

# 1. response_tracker — only alert on INTERESTED, not everything
f = "/opt/ACTIVE/INFRA/SKILLS/response_tracker.py"
content = open(f).read()
old = '''            new_count += 1
            icons = {"INTERESTED": "\\U0001f7e2", "REPLY": "\\U0001f4e9", "NOT_INTERESTED": "\\U0001f534", "UNKNOWN": "\\u2753"}
            icon = icons.get(category, "\\u2753")
            alert(f"{icon} <b>{category}</b> — {campaign}\\n"
                  f"From: {sender}\\nSubject: {subject[:80]}\\n"
                  f"Preview: {body[:150]}")'''
new = '''            new_count += 1
            # Only alert on INTERESTED employers (not workers, not rejections)
            if category == "INTERESTED":
                alert(f"\\U0001f7e2 <b>INTERESTED EMPLOYER</b> — {campaign}\\n"
                      f"From: {sender}\\nSubject: {subject[:80]}\\n"
                      f"Preview: {body[:150]}")'''
if old in content:
    content = content.replace(old, new)
    open(f, "w").write(content)
    print("response_tracker: silenced non-employer alerts")
else:
    print("response_tracker: pattern not found, check manually")

# 2. worker_router — silence
f2 = "/opt/ACTIVE/INFRA/SKILLS/worker_router.py"
content2 = open(f2).read()
content2 = content2.replace(
    "    alert_telegram(sender_email, inbox_name, subject)",
    "    # alert_telegram(sender_email, inbox_name, subject)  # silenced")
open(f2, "w").write(content2)
print("worker_router: silenced")

# 3. gmail_label_actions — keep only IMPORTANT alert
f3 = "/opt/ACTIVE/INFRA/SKILLS/gmail_label_actions.py"
content3 = open(f3).read()
content3 = content3.replace(
    '        alert(f"\\U0001f477 <b>APPLICANT</b> (Gmail label)\\nFrom: {sender}\\nSubj: {subject[:60]}")',
    '        pass  # silenced applicant alert')
content3 = content3.replace(
    '        alert(f"\\U0001f4c5 <b>FOLLOW-UP</b> in {days}d\\n{sender}\\n{subject[:60]}")',
    '        pass  # silenced followup alert')
open(f3, "w").write(content3)
print("gmail_label_actions: silenced applicant + followup alerts")

# 4. trash_to_dnc — silence
f4 = "/opt/ACTIVE/INFRA/SKILLS/trash_to_dnc.py"
content4 = open(f4).read()
content4 = content4.replace(
    '        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",\n            json={"chat_id": CHAT, "parse_mode": "HTML",\n                  "text": f"\\U0001f5d1 <b>TRASH->DNC</b>',
    '        pass  # silenced trash DNC alert\n        if False: requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",\n            json={"chat_id": CHAT, "parse_mode": "HTML",\n                  "text": f"\\U0001f5d1 <b>TRASH->DNC</b>')
open(f4, "w").write(content4)
print("trash_to_dnc: silenced")

# 5. bounce_cleaner — silence
f5 = "/opt/ACTIVE/INFRA/SKILLS/bounce_cleaner.py"
content5 = open(f5).read()
content5 = content5.replace(
    '        alert(f"\\U0001f9f9 <b>BOUNCE CLEANER</b>\\n{msg}")',
    '        pass  # silenced bounce alert')
open(f5, "w").write(content5)
print("bounce_cleaner: silenced")

print("\nDone. Only these will alert you:")
print("  - INTERESTED employer (response_tracker)")
print("  - Solonet draft created (solonet_pipeline)")
print("  - Morning digest 07:00 (morning_digest)")
print("  - Service failures (bot_watchdog)")
print("  - IMPORTANT Gmail label (gmail_label_actions)")
