#!/usr/bin/env python3
"""Add export/Franta/detasare pitch to ALL templates that don't have it."""
import os, glob

PITCH = """
De asemenea, suntem interesati sa aflam daca firma dumneavoastra este producator sau distribuitor. Daca aveti produse disponibile pentru export, am dori sa discutam posibilitati de colaborare pentru piata din Franta.
Cautam si furnizori de forta de munca pentru detasare in Europa, unde colaboram direct cu santiere si beneficiari finali."""

TEMPLATES_BASE = "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/ROMANIA/templates"

for tpl in glob.glob(f"{TEMPLATES_BASE}/**/*.txt", recursive=True):
    content = open(tpl, encoding="utf-8").read()

    # Skip if already has the pitch
    if "piata din Franta" in content or "detasare in Europa" in content:
        print(f"  SKIP (already has pitch): {tpl.replace(TEMPLATES_BASE+'/', '')}")
        continue

    # Find insertion point: before signature (Cu stima / Multumesc / Best / ---)
    for marker in ["Cu stima", "Multumesc", "Best regards", "---\n"]:
        if marker in content:
            # Insert pitch before the marker
            parts = content.split(marker, 1)
            new_content = parts[0].rstrip() + "\n" + PITCH + "\n\n" + marker + parts[1]
            open(tpl, "w", encoding="utf-8").write(new_content)
            print(f"  ADDED: {tpl.replace(TEMPLATES_BASE+'/', '')}")
            break
    else:
        print(f"  SKIP (no marker found): {tpl.replace(TEMPLATES_BASE+'/', '')}")
