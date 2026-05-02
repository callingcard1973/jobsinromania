#!/opt/ACTIVE/INFRA/venv/bin/python3
"""Health Dashboard - Generates static HTML status page"""
import sys
sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")
import os, csv, json
from pathlib import Path
from datetime import datetime, timedelta

OUTPUT = Path("/opt/ACTIVE/OPENDATA/DATA/status.html")

def get_scraper_status():
    status = []
    eures_dir = Path("/mnt/hdd/SCRAPER_DATA/csv/EURES")
    for country_dir in sorted(eures_dir.iterdir()):
        if country_dir.is_dir() and country_dir.name != "LOGS":
            csvs = list(country_dir.glob("*.csv"))
            if csvs:
                latest = max(csvs, key=lambda f: f.stat().st_mtime)
                age = datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime)
                count = sum(1 for _ in open(latest)) - 1
                status.append({
                    "country": country_dir.name,
                    "records": count,
                    "age_hours": int(age.total_seconds() / 3600),
                    "file": latest.name,
                    "ok": age < timedelta(days=3)
                })
    return status

def get_enrichment_status():
    status = []
    cache_dir = Path("/opt/ACTIVE/OPENDATA/DATA/ENRICHED")
    for cache_file in cache_dir.glob("*_cache.json"):
        try:
            data = json.load(open(cache_file))
            found = sum(1 for v in data.values() if v.get("emails"))
            status.append({
                "country": cache_file.stem.replace("_domain_cache", "").upper(),
                "total": len(data),
                "found": found,
                "pct": int(found * 100 / len(data)) if data else 0
            })
        except:
            pass
    # Also check Germany enriched
    de_cache = Path("/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/eures_domain_cache.json")
    if de_cache.exists():
        try:
            data = json.load(open(de_cache))
            found = sum(1 for v in data.values() if v.get("emails"))
            status.append({"country": "DE_EURES", "total": len(data), "found": found,
                          "pct": int(found * 100 / len(data)) if data else 0})
        except:
            pass
    return status

def get_campaign_status():
    status = []
    campaigns_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    for campaign_dir in campaigns_dir.iterdir():
        if campaign_dir.is_dir():
            contacts = list(campaign_dir.glob("contacts/*.csv"))
            if contacts:
                total = sum(sum(1 for _ in open(f)) - 1 for f in contacts)
                status.append({"name": campaign_dir.name, "contacts": total})
    return sorted(status, key=lambda x: x["contacts"], reverse=True)[:15]

def generate_html():
    scrapers = get_scraper_status()
    enrichment = get_enrichment_status()
    campaigns = get_campaign_status()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    rows_scrapers = ""
    for s in scrapers:
        cls = "ok" if s["ok"] else ("warn" if s["age_hours"] < 72 else "err")
        stat = "OK" if s["ok"] else "STALE"
        rows_scrapers += f'<tr><td>{s["country"]}</td><td>{s["records"]:,}</td><td>{s["age_hours"]}h</td><td class="{cls}">{stat}</td></tr>\n'

    rows_enrich = ""
    for e in enrichment:
        rows_enrich += f'<tr><td>{e["country"]}</td><td>{e["total"]:,}</td><td>{e["found"]:,}</td><td>{e["pct"]}%</td></tr>\n'

    rows_campaigns = ""
    for c in campaigns:
        rows_campaigns += f'<tr><td>{c["name"]}</td><td>{c["contacts"]:,}</td></tr>\n'

    html = f"""<!DOCTYPE html>
<html><head><title>Raspi Status</title>
<meta http-equiv="refresh" content="300">
<style>
body {{ font-family: monospace; background: #1a1a2e; color: #eee; padding: 20px; }}
h1 {{ color: #0f0; }}
h2 {{ color: #4cc9f0; }}
table {{ border-collapse: collapse; margin: 20px 0; }}
th, td {{ border: 1px solid #444; padding: 8px; text-align: left; }}
th {{ background: #16213e; }}
.ok {{ color: #0f0; }}
.warn {{ color: #ff0; }}
.err {{ color: #f00; }}
</style></head><body>
<h1>RASPI INFRASTRUCTURE STATUS</h1>
<p>Updated: {now}</p>

<h2>SCRAPERS (EURES)</h2>
<table>
<tr><th>Country</th><th>Records</th><th>Age</th><th>Status</th></tr>
{rows_scrapers}
</table>

<h2>ENRICHMENT</h2>
<table>
<tr><th>Country</th><th>Domains</th><th>Emails Found</th><th>Rate</th></tr>
{rows_enrich}
</table>

<h2>CAMPAIGNS</h2>
<table>
<tr><th>Campaign</th><th>Contacts</th></tr>
{rows_campaigns}
</table>

</body></html>"""

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w") as f:
        f.write(html)
    print(f"Dashboard written to {OUTPUT}")

if __name__ == "__main__":
    generate_html()
