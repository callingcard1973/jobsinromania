#!/usr/bin/env python3
"""Generate project directories with CLAUDE.md for ALL countries (not just Romania)."""
import os, re, subprocess, json

base = "D:/MEMORY/BERD EBRD"

# Get all active non-financial projects per country
cmd = """psql -U tudor interjob_master -t -A -F'|||' -c "
SELECT country, psd_id, REPLACE(title,' | We invest in changing lives',''), sector, status, ebrd_finance, total_cost, contact_name, contact_email, contact_phone, contact_website, contact_address, LEFT(REPLACE(overview,E'\\n',' '),800), url
FROM ebrd_projects
WHERE status NOT IN ('Complete','Repaying')
AND country IS NOT NULL AND country != ''
AND country NOT LIKE 'Industry%%' AND country NOT LIKE 'Countries%%' AND country != 'Regional'
ORDER BY country, sector, psd_id
" """

result = subprocess.run(
    ["ssh", "tudor@192.168.100.21", cmd],
    capture_output=True, text=True, timeout=60
)

# Country name to dir name mapping
def safe_dir(country):
    if country == "Romania": return "ROMANIA"
    if country == "Moldova": return "MOLDOVA"
    return country.replace(" ", "_")

projects_by_country = {}
for line in result.stdout.strip().split("\n"):
    if not line.strip(): continue
    parts = line.split("|||")
    if len(parts) < 14: continue
    country = parts[0].strip()
    if country in ("Romania",):  # Romania already has 77 dirs
        continue
    if country not in projects_by_country:
        projects_by_country[country] = []
    projects_by_country[country].append({
        "psd_id": parts[1].strip(),
        "title": parts[2].strip(),
        "sector": parts[3].strip(),
        "status": parts[4].strip() or "In Progress",
        "finance": parts[5].strip(),
        "total_cost": parts[6].strip(),
        "contact_name": parts[7].strip(),
        "contact_email": parts[8].strip(),
        "contact_phone": parts[9].strip(),
        "contact_website": parts[10].strip(),
        "contact_address": parts[11].strip(),
        "overview": parts[12].strip(),
        "url": parts[13].strip(),
    })

total_dirs = 0
for country, projects in sorted(projects_by_country.items()):
    country_dir = os.path.join(base, safe_dir(country))
    os.makedirs(country_dir, exist_ok=True)

    for p in projects:
        psd = p["psd_id"]
        safe_title = re.sub(r'[<>:"/\\|?*]', '', p["title"])[:55].strip().rstrip('.')
        dirname = f"{psd}_{safe_title}"
        dirpath = os.path.join(country_dir, dirname)
        os.makedirs(dirpath, exist_ok=True)

        is_financial = p["sector"] in ("Financial Institutions", "Equity Funds", "Notice Type")
        priority = "INDIRECT" if is_financial else ("HIGH" if p["contact_email"] and p["contact_email"] != "Related" else "MEDIUM")

        claude = f"""# {p['title']}

## Project
- **PSD ID:** {psd}
- **Country:** {country}
- **Sector:** {p['sector']}
- **Status:** {p['status']}
- **EBRD Finance:** {p['finance'] or 'N/A'}
- **Total Cost:** {p['total_cost'] or 'N/A'}
- **URL:** {p['url']}
- **Priority:** {priority}

## Contact
- **Name:** {p['contact_name'] or 'N/A'}
- **Email:** {p['contact_email'] or 'N/A'}
- **Phone:** {p['contact_phone'] or 'N/A'}
- **Website:** {p['contact_website'] or 'N/A'}
- **Address:** {p['contact_address'] or 'N/A'}

## Overview
{p['overview'][:800] if p['overview'] else 'No overview available.'}

## Status Tracking
- [ ] Contractor identified
- [ ] First contact sent
- [ ] Response received
- [ ] Offer sent
- [ ] Contract signed
"""
        with open(os.path.join(dirpath, "CLAUDE.md"), "w", encoding="utf-8") as f:
            f.write(claude)
        total_dirs += 1

    print(f"  {country:30s}: {len(projects)} projects")

print(f"\nTotal: {total_dirs} project directories created across {len(projects_by_country)} countries")
