#!/usr/bin/env python3
"""Generate EBRD handoff files for each country with active projects."""
import subprocess, json, os

base = "D:/MEMORY/BERD EBRD"

# Get country data
cmd = """psql -U tudor interjob_master -t -A -F'|||' -c "
SELECT country,
       COUNT(CASE WHEN status NOT IN ('Complete','Repaying') THEN 1 END) active,
       COUNT(CASE WHEN status NOT IN ('Complete','Repaying') AND contact_email != '' AND contact_email IS NOT NULL THEN 1 END) with_email,
       COUNT(CASE WHEN status NOT IN ('Complete','Repaying') AND sector NOT IN ('Financial Institutions','Equity Funds','Notice Type') THEN 1 END) actionable
FROM ebrd_projects
WHERE country != '' AND country IS NOT NULL
AND country NOT LIKE 'Industry%%' AND country NOT LIKE 'Countries%%'
GROUP BY country
HAVING COUNT(CASE WHEN status NOT IN ('Complete','Repaying') THEN 1 END) > 0
ORDER BY COUNT(CASE WHEN status NOT IN ('Complete','Repaying') THEN 1 END) DESC
" """

result = subprocess.run(
    ["ssh", "tudor@192.168.100.21", cmd],
    capture_output=True, text=True, timeout=30
)

countries = []
for line in result.stdout.strip().split("\n"):
    if not line.strip(): continue
    parts = line.split("|||")
    if len(parts) < 4: continue
    countries.append({
        "name": parts[0].strip(),
        "active": int(parts[1]),
        "with_email": int(parts[2]),
        "actionable": int(parts[3])
    })

print(f"Found {len(countries)} countries")

# Get projects per country
for c in countries:
    name = c["name"]
    if name in ("Romania", "Moldova"):
        continue  # already done

    safe = name.replace(" ", "_").replace("&", "and")
    dirpath = os.path.join(base, safe)
    os.makedirs(dirpath, exist_ok=True)

    # Get project list
    cmd2 = f"""psql -U tudor interjob_master -t -A -F'|||' -c "
SELECT psd_id, REPLACE(title,' | We invest in changing lives',''), sector, status, ebrd_finance, contact_name, contact_email
FROM ebrd_projects
WHERE country = '{name}'
AND status NOT IN ('Complete','Repaying')
ORDER BY sector, psd_id
" """

    result2 = subprocess.run(
        ["ssh", "tudor@192.168.100.21", cmd2],
        capture_output=True, text=True, timeout=30
    )

    projects = []
    for line in result2.stdout.strip().split("\n"):
        if not line.strip(): continue
        parts = line.split("|||")
        if len(parts) < 7: continue
        projects.append({
            "psd": parts[0].strip(),
            "title": parts[1].strip(),
            "sector": parts[2].strip(),
            "status": parts[3].strip() or "In Progress",
            "finance": parts[4].strip(),
            "contact_name": parts[5].strip(),
            "contact_email": parts[6].strip(),
        })

    # Group by sector
    sectors = {}
    for p in projects:
        s = p["sector"] or "Other"
        if s not in sectors:
            sectors[s] = []
        sectors[s].append(p)

    # Build handoff
    lines = []
    lines.append(f"# EBRD {name} — {c['active']} proiecte active")
    lines.append(f"")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Active | {c['active']} |")
    lines.append(f"| Cu email contact | {c['with_email']} |")
    lines.append(f"| Actionabile (non-financiar) | {c['actionable']} |")
    lines.append(f"")

    for sector, projs in sorted(sectors.items()):
        is_financial = sector in ("Financial Institutions", "Equity Funds", "Notice Type")
        lines.append(f"## {sector} ({len(projs)} proiecte){' — INDIRECT' if is_financial else ''}")
        lines.append(f"")
        lines.append(f"| PSD | Titlu | Status | Finance | Contact |")
        lines.append(f"|-----|-------|--------|---------|---------|")
        for p in projs:
            email = p["contact_email"] if p["contact_email"] and p["contact_email"] != "Related" else ""
            contact = p["contact_name"] if p["contact_name"] and p["contact_name"] != "Related" else ""
            lines.append(f"| {p['psd']} | {p['title'][:60]} | {p['status']} | {p['finance'] or 'N/A'} | {contact} {email} |")
        lines.append(f"")

    # Add action section
    high_priority = [p for p in projects if p["contact_email"] and p["contact_email"] != "Related" and p["sector"] not in ("Financial Institutions", "Equity Funds", "Notice Type")]

    if high_priority:
        lines.append(f"## CONTACTE DIRECTE ({len(high_priority)})")
        lines.append(f"")
        for p in high_priority:
            lines.append(f"- **{p['title'][:50]}** — {p['contact_name']} — {p['contact_email']}")
        lines.append(f"")

    lines.append(f"## CE TREBUIE FACUT")
    lines.append(f"1. Identifica proiectele de constructie/energie/infrastructura")
    lines.append(f"2. Gaseste contractorii (EPC/constructori) prin EBRD procurement portal sau licitatii locale")
    lines.append(f"3. Contacteaza cu oferta de forta de munca specifica proiectului")
    lines.append(f"4. Mentioneaza EBRD in outreach — adauga credibilitate")
    lines.append(f"")

    filepath = os.path.join(dirpath, "HANDOFF.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"  {name}: {c['active']} active, {len(high_priority)} HIGH")

print(f"\nDone: {len(countries)} countries")
