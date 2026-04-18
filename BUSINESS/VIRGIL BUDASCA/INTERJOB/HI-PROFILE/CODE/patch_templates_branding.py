#!/usr/bin/env python3
"""Patch ANOFM templates: add {sender_tagline} intro + personalized signature."""
import os

TPLS = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/templates/anofm"

PATCHES = {
    "elena_template1.txt": {
        "intro_after": "Buna ziua{contact_greeting}\n\n",
        "old_sig": "Elena Vasilescu\nINTERJOB SOLUTIONS EUROPE\nelena.manpower.dristor@gmail.com\nWhatsApp: +33 7 51 17 13 56\nwww.interjob.ro\nhttps://bppltd.co.uk/",
        "new_sig": "Elena Vasilescu\n{sender_brand}\nelena.manpower.dristor@gmail.com\nWhatsApp: +33 7 51 17 13 56\n{sender_url}",
    },
    "anofm_gmail_template1.txt": {
        "intro_after": "Buna ziua{contact_greeting}\n\n",
        "old_sig": "Elena Vasilescu\nINTERJOB SOLUTIONS EUROPE\nelena.manpower.dristor@gmail.com\nWhatsApp: +33 7 51 17 13 56\nwww.interjob.ro\nhttps://bppltd.co.uk/",
        "new_sig": "Elena Vasilescu\n{sender_brand}\nelena.manpower.dristor@gmail.com\nWhatsApp: +33 7 51 17 13 56\n{sender_url}",
    },
    "lucian_template1.txt": {
        "intro_after": "Buna ziua{contact_greeting}\n\n",
        "old_sig": "Lucian\nBP&P Partners\n+40 771 028 948\n\nhttps://bppltd.co.uk/",
        "new_sig": "Lucian\n{sender_brand}\n+40 771 028 948\n{sender_url}",
    },
    "virgil_template1.txt": {
        "intro_after": "Buna ziua{contact_greeting}\n\n",
        "old_sig": "Virgil\nBP&P Partners\nWhatsApp: +44 7842 964322\n\nhttps://bppltd.co.uk/",
        "new_sig": "Virgil\n{sender_brand}\nWhatsApp: +44 7842 964322\n{sender_url}",
    },
    "warehouse_template1.txt": {
        "intro_after": "Buna ziua{contact_greeting}\n\n",
        "old_sig": "Elena Vasilescu, INTERJOB SOLUTIONS EUROPE\nWhatsApp: +33 7 51 17 13 56\nwww.interjob.ro\nhttps://bppltd.co.uk/",
        "new_sig": "Elena Vasilescu, {sender_brand}\nWhatsApp: +33 7 51 17 13 56\n{sender_url}",
    },
}

INTRO_LINE = "{sender_tagline}.\n\n"

for fname, p in PATCHES.items():
    path = os.path.join(TPLS, fname)
    with open(path, encoding="utf-8") as f:
        content = f.read()

    # Add tagline intro if not already present
    if "{sender_tagline}" not in content:
        content = content.replace(p["intro_after"], p["intro_after"] + INTRO_LINE)

    # Replace hardcoded signature
    if p["old_sig"] in content:
        content = content.replace(p["old_sig"], p["new_sig"])
        print(f"PATCHED sig: {fname}")
    else:
        print(f"SKIP sig (not found): {fname}")

    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  saved: {fname}")
