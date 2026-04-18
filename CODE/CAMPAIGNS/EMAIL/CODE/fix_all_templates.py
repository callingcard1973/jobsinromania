#!/usr/bin/env python3
"""Fix all templates: Tudor phone, WhatsApp, add personalization."""
import glob, re, os

BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/templates"
fixes = 0

for tpl in glob.glob(f"{BASE}/**/*.txt", recursive=True):
    content = open(tpl, encoding="utf-8").read()
    original = content

    # Fix Tudor wrong phones -> +33 7 51 17 13 56
    content = content.replace("+40 770 123 456", "+33 7 51 17 13 56")
    content = content.replace("+40 722 789 938", "+33 7 51 17 13 56")
    content = content.replace("+40 729 069 269", "+33 7 51 17 13 56")

    # Add personalization if missing
    if "{contact_greeting}" not in content:
        # Replace "Buna ziua," with "Buna ziua{contact_greeting}"
        content = content.replace("Buna ziua,\n", "Buna ziua{contact_greeting}\n")
        content = content.replace("Buna ziua,\r\n", "Buna ziua{contact_greeting}\r\n")

    if "{city_text}" not in content and "ANOFM" not in content:
        # Add {position_text}{city_text} after first reference to company/anunt
        for marker in ["anuntul dumneavoastra", "firma dumneavoastra", "compania dumneavoastra"]:
            if marker in content.lower():
                idx = content.lower().index(marker) + len(marker)
                # Check if there's already a period or newline
                if idx < len(content) and content[idx] in ".\n":
                    content = content[:idx] + "{position_text}{city_text}" + content[idx:]
                break

    if content != original:
        open(tpl, "w", encoding="utf-8").write(content)
        name = tpl.replace(BASE + "/", "")
        fixes += 1
        changes = []
        if "+40 770" in original or "+40 722" in original or "+40 729" in original:
            changes.append("phone")
        if "{contact_greeting}" not in original and "{contact_greeting}" in content:
            changes.append("greeting")
        if "{city_text}" not in original and "{city_text}" in content:
            changes.append("city")
        print(f"  FIXED {name}: {', '.join(changes)}")

print(f"\nTotal: {fixes} templates fixed")
