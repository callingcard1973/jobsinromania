#!/usr/bin/env python3
"""Add pitch to remaining templates that were missed."""
import os

PITCH = """
De asemenea, suntem interesati sa aflam daca firma dumneavoastra este producator sau distribuitor. Daca aveti produse disponibile pentru export, am dori sa discutam posibilitati de colaborare pentru piata din Franta.
Cautam si furnizori de forta de munca pentru detasare in Europa, unde colaboram direct cu santiere si beneficiari finali.
"""

BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/templates"

files = [
    "lemn/lucian_template1.txt",
    "lemn/tudor_template1.txt",
    "confectii/lucian_template1.txt",
    "confectii/tudor_template1.txt",
    "agricultura/lucian_template1.txt",
    "agricultura/tudor_template1.txt",
    "romania_constructori/template1.txt",
    "romania/lucian_template1.txt",
    "romania/lucian_volume_template1.txt",
    "romania/sectoare/tudor/general.txt",
    "romania_horeca/template1.txt",
]

for f in files:
    full = os.path.join(BASE, f)
    if not os.path.exists(full):
        continue
    content = open(full, encoding="utf-8").read()
    if "piata din Franta" in content:
        print(f"  SKIP: {f}")
        continue

    # Insert before "Pentru dezabonare" or before last signature block
    for marker in ["Pentru dezabonare", "Pentru a nu mai primi", "Lucian\n", "Tudor\n", "Virgil\n", "seicarescu.com"]:
        if marker in content:
            idx = content.index(marker)
            # Go back to find start of signature (blank line before)
            before = content[:idx].rstrip()
            after = content[idx:]
            content = before + "\n" + PITCH + "\n" + after
            open(full, "w", encoding="utf-8").write(content)
            print(f"  ADDED: {f}")
            break
    else:
        # Just append before last 5 lines
        lines = content.split("\n")
        insert_at = max(len(lines) - 5, 1)
        lines.insert(insert_at, PITCH)
        open(full, "w", encoding="utf-8").write("\n".join(lines))
        print(f"  ADDED (end): {f}")
