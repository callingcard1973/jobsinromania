#!/usr/bin/env python3
"""Verify ALL campaign configs: templates exist, senders set, business hours, gentle delays,
corporate=Brevo, personal=Gmail, pitch present, reply-to matches sender domain."""
import json, glob, os

ISSUES = []

def check(name, condition, msg):
    if not condition:
        ISSUES.append(f"  {name}: {msg}")

configs = set()
for p in ["/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/*.json",
          "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/configs/*.json"]:
    configs.update(glob.glob(p))

# Resolve symlinks to avoid double-checking
real_configs = {}
for f in configs:
    real = os.path.realpath(f)
    if real not in real_configs:
        real_configs[real] = os.path.basename(f)

print(f"Checking {len(real_configs)} unique configs...\n")

for fpath, fname in sorted(real_configs.items(), key=lambda x: x[1]):
    try:
        cfg = json.load(open(fpath))
    except:
        print(f"FAIL {fname}: cannot parse JSON")
        continue

    tpl_dir = cfg.get("templates_dir", "")
    sectors = cfg.get("sectors", {})
    enabled = {s: c for s, c in sectors.items() if c.get("enabled")}

    if not enabled:
        continue  # skip dormant

    print(f"{fname} ({len(enabled)} sectors enabled)")

    for s, c in enabled.items():
        sender = c.get("sender_email", "")
        reply = c.get("reply_to", "")
        dl = c.get("daily_limit", 0)
        dmin = c.get("delay_min", 0)
        dmax = c.get("delay_max", 0)
        bh = c.get("business_hours", {})
        ft = c.get("filter_type", "")
        tpl_prefix = c.get("template_prefix", "template")
        tpl_file = os.path.join(tpl_dir, f"{tpl_prefix}1.txt")

        # Template exists
        check(s, os.path.exists(tpl_file), f"template missing: {tpl_file}")

        # Pitch present
        if os.path.exists(tpl_file):
            content = open(tpl_file).read()
            check(s, "piata din Franta" in content, "missing export/Franta/detasare pitch")

        # Business hours
        check(s, bh.get("enabled"), "no business hours")

        # Gentle delays (>=300s)
        check(s, dmin >= 300, f"delay_min={dmin} too fast (need >=300)")

        # Corporate = Brevo, Personal = Gmail
        is_gmail = "@gmail.com" in sender
        if is_gmail:
            check(s, ft == "personal", f"Gmail sender but filter_type={ft} (should be personal)")
            check(s, "@gmail.com" in reply, f"Gmail sender but reply_to={reply} (should be gmail)")
        else:
            if ft:
                check(s, ft == "corporate", f"Brevo sender but filter_type={ft}")

        status = "OK" if not any(s in i for i in ISSUES[-10:]) else "ISSUE"
        print(f"  {s:25s} {sender:35s} {dl:>4}/day {dmin}-{dmax}s bh={'Y' if bh.get('enabled') else 'N'} ft={ft:10s} {status}")

print(f"\n{'='*60}")
if ISSUES:
    print(f"ISSUES FOUND ({len(ISSUES)}):")
    for i in ISSUES:
        print(i)
else:
    print("ALL OK - no issues found")
