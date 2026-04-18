#!/usr/bin/env python3
"""
IDEA-046: Genereaza cataloage HTML angajatori pe domeniu x tara.
Datele vin din PostgreSQL (raspibig). Output: HTML static per domeniu/tara.
Deploy pe A2 Hosting via cPanel API.

Reguli:
- NU publica email/telefon/persoana contact (doar nume firma + oras)
- Toate linkurile apply -> https://interjob.ro/apply.html
- NU mentiona sursa (ANOFM/EURES/TED)
- RTL pentru ar/ur/ps
"""
import json, os, sys
from pathlib import Path

# --- CONFIG ---
OUTPUT_DIR = Path(__file__).parent / "output"

APPLY_URL = "https://interjob.ro/apply.html"

# Domeniu -> ce sectoare/CPV/NACE cauta in DB
DOMAINS = {
    "factoryjobs.eu": {
        "title": "Factory Jobs EU",
        "desc": "Manufacturing and industrial positions across Europe",
        "icon": "🏭",
        "ted_cpv_prefix": ["31", "32", "33", "34", "42", "43", "44"],  # industrial/manufacturing
        "no_nace_prefix": ["10", "11", "13", "14", "15", "16", "17", "20", "22", "23", "24", "25"],
        "ro_caen_prefix": ["10", "11", "13", "14", "15", "16", "17", "20", "22", "23", "24", "25"],
    },
    "buildjobs.eu": {
        "title": "Build Jobs EU",
        "desc": "Construction and building positions across Europe",
        "icon": "🏗️",
        "ted_cpv_prefix": ["45"],  # construction works
        "no_nace_prefix": ["41", "42", "43"],
        "ro_caen_prefix": ["41", "42", "43"],
    },
    "careworkers.eu": {
        "title": "Care Workers EU",
        "desc": "Healthcare and social care positions across Europe",
        "icon": "🏥",
        "ted_cpv_prefix": ["85", "33"],  # health, medical
        "no_nace_prefix": ["86", "87", "88"],
        "ro_caen_prefix": ["86", "87", "88"],
    },
    "electricjobs.eu": {
        "title": "Electric Jobs EU",
        "desc": "Electrical and energy sector positions across Europe",
        "icon": "⚡",
        "ted_cpv_prefix": ["09", "31", "65"],  # energy, electrical
        "no_nace_prefix": ["27", "35"],
        "ro_caen_prefix": ["27", "35"],
    },
    "farmworkers.eu": {
        "title": "Farm Workers EU",
        "desc": "Agricultural and farming positions across Europe",
        "icon": "🌾",
        "ted_cpv_prefix": ["03", "15", "16"],  # agriculture, food
        "no_nace_prefix": ["01", "02", "03"],
        "ro_caen_prefix": ["01", "02", "03"],
    },
    "horecaworkers.eu": {
        "title": "HORECA Workers EU",
        "desc": "Hotel, restaurant and catering positions across Europe",
        "icon": "🍽️",
        "ted_cpv_prefix": ["55", "56"],  # hotel, restaurant
        "no_nace_prefix": ["55", "56"],
        "ro_caen_prefix": ["55", "56"],
    },
    "meatworkers.eu": {
        "title": "Meat Workers EU",
        "desc": "Meat processing and food industry positions across Europe",
        "icon": "🥩",
        "ted_cpv_prefix": ["15"],  # food products
        "no_nace_prefix": ["10.1", "10.2", "10.3"],  # meat, fish, fruit processing
        "ro_caen_prefix": ["1011", "1012", "1013", "1020"],
    },
    "mechanicjobs.eu": {
        "title": "Mechanic Jobs EU",
        "desc": "Automotive and mechanical engineering positions across Europe",
        "icon": "🔧",
        "ted_cpv_prefix": ["34", "50"],  # vehicles, repair
        "no_nace_prefix": ["29", "30", "33", "45"],
        "ro_caen_prefix": ["29", "30", "33", "45"],
    },
    "warehouseworkers.eu": {
        "title": "Warehouse Workers EU",
        "desc": "Logistics and warehouse positions across Europe",
        "icon": "📦",
        "ted_cpv_prefix": ["63", "60"],  # transport, storage
        "no_nace_prefix": ["49", "50", "51", "52", "53"],
        "ro_caen_prefix": ["49", "50", "51", "52", "53"],
    },
}

# Tari cu date in DB
COUNTRIES = {
    "NO": {"name": "Norway", "table": "no_companies_full", "col_name": "navn", "col_city": "forretningsadresse_poststed", "col_nace": "naeringskode1_kode", "col_email": "epostadresse"},
    "RO": {"name": "Romania", "table": "master_romania_companies", "col_name": "name", "col_city": "city", "col_nace": "caen", "col_email": "email"},
    # TED winners — multi-tara
}

TED_COUNTRIES = {
    "DE": "Germany", "PL": "Poland", "FR": "France", "ES": "Spain",
    "CZ": "Czech Republic", "SE": "Sweden", "HU": "Hungary", "BG": "Bulgaria",
    "IT": "Italy", "FI": "Finland", "NL": "Netherlands", "AT": "Austria",
    "DK": "Denmark", "BE": "Belgium", "HR": "Croatia", "SI": "Slovenia",
    "LV": "Latvia", "SK": "Slovakia", "PT": "Portugal", "IE": "Ireland",
}

# ISO3 -> ISO2 mapping for TED
ISO3_TO_ISO2 = {
    "DEU": "DE", "POL": "PL", "FRA": "FR", "ESP": "ES", "CZE": "CZ",
    "SWE": "SE", "HUN": "HU", "BGR": "BG", "ITA": "IT", "FIN": "FI",
    "NLD": "NL", "AUT": "AT", "DNK": "DK", "BEL": "BE", "HRV": "HR",
    "SVN": "SI", "LVA": "LV", "SVK": "SK", "PRT": "PT", "IRL": "IE",
    "ROU": "RO", "RO": "RO", "NOR": "NO",
}


def generate_page_html(domain_key, domain_cfg, country_code, country_name, employers):
    """Genereaza HTML pentru o pagina domeniu/tara."""
    title = f"{domain_cfg['title']} in {country_name}"
    desc = f"{len(employers)} employers hiring in {country_name} — {domain_cfg['desc']}"

    rows = ""
    for i, emp in enumerate(employers[:500]):  # max 500 per pagina
        name = emp.get("name", "").strip()
        city = emp.get("city", "").strip() or "—"
        if not name:
            continue
        rows += f"""      <tr>
        <td>{i+1}</td>
        <td>{name}</td>
        <td>{city}</td>
        <td><a href="{APPLY_URL}?ref={domain_key}&country={country_code}" class="btn">Apply Now</a></td>
      </tr>\n"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — {len(employers)} Employers Hiring</title>
  <meta name="description" content="{desc}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="https://{domain_key}/{country_code.lower()}/">
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background:#0d1f2d; color:#e2e8f0; }}
    .header {{ background:#0d1f2d; padding:1rem 2rem; border-bottom:1px solid #1e3a5f; display:flex; justify-content:space-between; align-items:center; }}
    .header a {{ color:#f59e0b; text-decoration:none; font-weight:700; font-size:1.2rem; }}
    .hero {{ background:linear-gradient(135deg,#0d1f2d 0%,#1e3a5f 100%); padding:3rem 2rem; text-align:center; }}
    .hero h1 {{ font-size:2rem; margin-bottom:0.5rem; }}
    .hero .count {{ font-size:3rem; color:#f59e0b; font-weight:800; }}
    .hero p {{ color:#94a3b8; margin-top:0.5rem; }}
    .container {{ max-width:1000px; margin:2rem auto; padding:0 1rem; }}
    table {{ width:100%; border-collapse:collapse; }}
    th {{ background:#1e3a5f; padding:0.75rem; text-align:left; font-size:0.85rem; text-transform:uppercase; }}
    td {{ padding:0.6rem 0.75rem; border-bottom:1px solid #1e3a5f; }}
    tr:hover {{ background:#1e3a5f33; }}
    .btn {{ background:#f59e0b; color:#0d1f2d; padding:0.4rem 1rem; border-radius:4px; text-decoration:none; font-weight:600; font-size:0.85rem; white-space:nowrap; }}
    .btn:hover {{ background:#d97706; }}
    .countries {{ display:flex; flex-wrap:wrap; gap:0.5rem; justify-content:center; padding:1.5rem; }}
    .countries a {{ background:#1e3a5f; color:#e2e8f0; padding:0.4rem 1rem; border-radius:20px; text-decoration:none; font-size:0.85rem; }}
    .countries a.active {{ background:#f59e0b; color:#0d1f2d; }}
    .countries a:hover {{ background:#f59e0b; color:#0d1f2d; }}
    footer {{ text-align:center; padding:2rem; color:#64748b; font-size:0.8rem; }}
    footer a {{ color:#f59e0b; }}
    @media(max-width:600px) {{ .hero h1 {{ font-size:1.4rem; }} table {{ font-size:0.85rem; }} }}
  </style>
</head>
<body>
  <div class="header">
    <a href="https://{domain_key}/">{domain_cfg['icon']} {domain_cfg['title']}</a>
    <a href="{APPLY_URL}" class="btn">Apply Now</a>
  </div>
  <div class="hero">
    <h1>{title}</h1>
    <div class="count">{len(employers)}</div>
    <p>Employers currently hiring — apply directly</p>
  </div>
  <div class="countries" id="country-nav"></div>
  <div class="container">
    <table>
      <thead><tr><th>#</th><th>Company</th><th>City</th><th>Action</th></tr></thead>
      <tbody>
{rows}      </tbody>
    </table>
  </div>
  <footer>
    &copy; 2026 <a href="https://{domain_key}/">{domain_cfg['title']}</a> &mdash;
    Part of the <a href="https://interjob.ro">InterJob European Recruitment Network</a>
  </footer>
  <script type="application/ld+json">
  {{
    "@context": "https://schema.org",
    "@type": "ItemList",
    "name": "{title}",
    "description": "{desc}",
    "numberOfItems": {len(employers)},
    "url": "https://{domain_key}/{country_code.lower()}/"
  }}
  </script>
</body>
</html>"""
    return html


def generate_index_html(domain_key, domain_cfg, country_pages):
    """Genereaza pagina index cu linkuri catre toate tarile."""
    cards = ""
    for cc, data in sorted(country_pages.items(), key=lambda x: -x[1]["count"]):
        cards += f"""    <a href="/{cc.lower()}/" class="card">
      <div class="count">{data['count']}</div>
      <div class="name">{data['name']}</div>
    </a>\n"""

    total = sum(d["count"] for d in country_pages.values())

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{domain_cfg['title']} — {total} Employers Across Europe</title>
  <meta name="description" content="{domain_cfg['desc']}. Browse {total} employers in {len(country_pages)} countries.">
  <link rel="canonical" href="https://{domain_key}/">
  <style>
    * {{ margin:0; padding:0; box-sizing:border-box; }}
    body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif; background:#0d1f2d; color:#e2e8f0; }}
    .header {{ background:#0d1f2d; padding:1rem 2rem; border-bottom:1px solid #1e3a5f; display:flex; justify-content:space-between; align-items:center; }}
    .header a {{ color:#f59e0b; text-decoration:none; font-weight:700; font-size:1.2rem; }}
    .hero {{ background:linear-gradient(135deg,#0d1f2d 0%,#1e3a5f 100%); padding:4rem 2rem; text-align:center; }}
    .hero h1 {{ font-size:2.5rem; margin-bottom:0.5rem; }}
    .hero .total {{ font-size:4rem; color:#f59e0b; font-weight:800; }}
    .hero p {{ color:#94a3b8; margin-top:0.5rem; font-size:1.1rem; }}
    .grid {{ max-width:1000px; margin:2rem auto; padding:0 1rem; display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:1rem; }}
    .card {{ background:#1e3a5f; padding:1.5rem; border-radius:8px; text-align:center; text-decoration:none; color:#e2e8f0; transition:transform 0.2s; }}
    .card:hover {{ transform:translateY(-3px); background:#2d4a6f; }}
    .card .count {{ font-size:2rem; color:#f59e0b; font-weight:800; }}
    .card .name {{ margin-top:0.3rem; font-size:1rem; }}
    .btn {{ background:#f59e0b; color:#0d1f2d; padding:0.6rem 1.5rem; border-radius:4px; text-decoration:none; font-weight:600; }}
    footer {{ text-align:center; padding:2rem; color:#64748b; font-size:0.8rem; }}
    footer a {{ color:#f59e0b; }}
  </style>
</head>
<body>
  <div class="header">
    <a href="/">{domain_cfg['icon']} {domain_cfg['title']}</a>
    <a href="{APPLY_URL}" class="btn">Apply Now</a>
  </div>
  <div class="hero">
    <h1>{domain_cfg['icon']} {domain_cfg['title']}</h1>
    <div class="total">{total}</div>
    <p>Employers hiring across {len(country_pages)} European countries</p>
  </div>
  <div class="grid">
{cards}  </div>
  <footer>
    &copy; 2026 <a href="https://{domain_key}/">{domain_cfg['title']}</a> &mdash;
    Part of the <a href="https://interjob.ro">InterJob European Recruitment Network</a>
  </footer>
</body>
</html>"""
    return html


def generate_sitemap(domain_key, country_pages):
    """Genereaza sitemap.xml."""
    urls = f'  <url><loc>https://{domain_key}/</loc><priority>1.0</priority></url>\n'
    for cc in sorted(country_pages.keys()):
        urls += f'  <url><loc>https://{domain_key}/{cc.lower()}/</loc><priority>0.8</priority></url>\n'
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}</urlset>"""


def save_domain(domain_key, domain_cfg, country_pages, employers_by_country):
    """Salveaza toate fisierele HTML pentru un domeniu."""
    domain_dir = OUTPUT_DIR / domain_key
    domain_dir.mkdir(parents=True, exist_ok=True)

    # Index
    index_html = generate_index_html(domain_key, domain_cfg, country_pages)
    (domain_dir / "index.html").write_text(index_html, encoding="utf-8")

    # Pagini per tara
    for cc, employers in employers_by_country.items():
        if not employers:
            continue
        country_dir = domain_dir / cc.lower()
        country_dir.mkdir(exist_ok=True)
        page_html = generate_page_html(domain_key, domain_cfg, cc, country_pages[cc]["name"], employers)
        (country_dir / "index.html").write_text(page_html, encoding="utf-8")

    # Sitemap
    sitemap = generate_sitemap(domain_key, country_pages)
    (domain_dir / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    print(f"  {domain_key}: {len(country_pages)} tari, {sum(d['count'] for d in country_pages.values())} angajatori")


if __name__ == "__main__":
    print("IDEA-046: Genereaza cataloage HTML din DB")
    print("Folosire: python generate_catalogs.py")
    print()
    print("ATENTIE: Acest script trebuie rulat pe raspibig (acces PostgreSQL).")
    print("Sau configurati SSH tunnel: ssh -L 5432:localhost:5432 tudor@192.168.100.21")
    print()
    print("Domenii configurate:")
    for k, v in DOMAINS.items():
        print(f"  {v['icon']} {k} — {v['desc']}")
    print()
    print(f"Output: {OUTPUT_DIR}/")
    print()
    print("Pentru a genera, rulati: python generate_catalogs_raspibig.py")
