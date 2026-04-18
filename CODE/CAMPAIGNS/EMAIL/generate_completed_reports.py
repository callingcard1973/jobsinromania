#!/usr/bin/env python3
"""Generate COMPLETED project reports per country."""
import os, subprocess, re

base = "D:/MEMORY/BERD EBRD"

def safe_dir(country):
    if country == "Romania": return "ROMANIA"
    if country == "Moldova": return "MOLDOVA"
    return country.replace(" ", "_")

cmd = """psql -U tudor interjob_master -t -A -F'|||' -c "
SELECT country, psd_id, REPLACE(title,' | We invest in changing lives',''), sector, status, ebrd_finance, contact_name, contact_email
FROM ebrd_projects
WHERE status IN ('Complete','Repaying')
AND country IN ('Romania','Poland','Serbia','Greece','Georgia','Bosnia and Herzegovina','Moldova','Montenegro','Croatia','Armenia','Kosovo','Bulgaria','Albania','North Macedonia','Lithuania','Slovak Republic','Hungary','Slovenia','Estonia','Latvia','Czechia','Ukraine')
ORDER BY country, status DESC, sector, psd_id
" """

result = subprocess.run(
    ["ssh", "tudor@192.168.100.21", cmd],
    capture_output=True, text=True, timeout=60
)

by_country = {}
for line in result.stdout.strip().split("\n"):
    if not line.strip(): continue
    parts = line.split("|||")
    if len(parts) < 8: continue
    country = parts[0].strip()
    if country not in by_country:
        by_country[country] = {"Complete": [], "Repaying": []}
    status = parts[4].strip()
    by_country[country][status].append({
        "psd": parts[1].strip(),
        "title": parts[2].strip(),
        "sector": parts[3].strip(),
        "finance": parts[5].strip(),
        "contact": parts[6].strip(),
        "email": parts[7].strip(),
    })

for country, data in sorted(by_country.items()):
    country_dir = os.path.join(base, safe_dir(country))
    os.makedirs(country_dir, exist_ok=True)

    total_c = len(data["Complete"])
    total_r = len(data["Repaying"])

    lines = [
        f"# {country} — Completed & Repaying EBRD Projects",
        f"Total: {total_c} Complete + {total_r} Repaying = {total_c + total_r}",
        "",
    ]

    if data["Repaying"]:
        lines.append(f"## Repaying ({total_r}) — still active, loan being repaid")
        lines.append("")
        lines.append("| PSD | Title | Sector | Finance | Contact |")
        lines.append("|-----|-------|--------|---------|---------|")
        for p in data["Repaying"]:
            email = p["email"] if p["email"] and p["email"] != "Related" else ""
            lines.append(f"| {p['psd']} | {p['title'][:55]} | {p['sector']} | {p['finance'] or '-'} | {email} |")
        lines.append("")

    if data["Complete"]:
        lines.append(f"## Complete ({total_c})")
        lines.append("")
        lines.append("| PSD | Title | Sector | Finance |")
        lines.append("|-----|-------|--------|---------|")
        for p in data["Complete"]:
            lines.append(f"| {p['psd']} | {p['title'][:55]} | {p['sector']} | {p['finance'] or '-'} |")
        lines.append("")

    outfile = os.path.join(country_dir, "COMPLETED_PROJECTS.md")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  {country:30s}: {total_c}C + {total_r}R = {total_c+total_r}")

print(f"\nDone: {len(by_country)} countries")
