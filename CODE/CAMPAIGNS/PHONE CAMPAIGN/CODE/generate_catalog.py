#!/usr/bin/env python3
"""
ANOFM Jobs Catalog Generator
Dark-theme, anonymous, print-ready HTML catalog.
Employer names hidden. Job titles translated RO→EN.
"""
import sys, io, csv, os, urllib.parse
from collections import defaultdict
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ═══════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════
TITLE = "Active Job Vacancies — Romania"
SUBTITLE = "Labor Market Catalog · April 2026"
CONTACT_NAME = "Yohan"
CONTACT_PHONE = "40723068733"
INPUT_PATH = r"D:\MEMORY\PHONE CAMPAIGN\DATA\anofm_phones_20260416_v3.csv"
OUTPUT_PATH = r"D:\MEMORY\PHONE CAMPAIGN\CATALOGS\YOHAN\jobs_catalog_april_yohan.html"
ACCENT_COLOR = "#f59e0b"
EUR_DIVISOR = 5

# ═══════════════════════════════════════════
# JOB TITLE TRANSLATIONS (RO → EN)
# ═══════════════════════════════════════════
TRANSLATIONS = {
    "LUCRATOR COMERCIAL": "Sales & Retail Worker",
    "MUNCITOR NECALIFICAT LA DEMOLAREA CLADIRILOR, CAPTUSELI ZIDARIE, PLACI MOZAIC, FAIANTA, GRESIE, PARCHET": "General Construction Labourer (tiling, flooring, demolition)",
    "AJUTOR BUCATAR": "Kitchen Assistant / Cook Helper",
    "MANIPULANT MARFURI": "Goods Handler / Warehouse Operative",
    "FEMEIE DE SERVICIU": "Cleaning Operative",
    "Conducător auto transport rutier de mărfuri": "Freight Truck Driver",
    "MUNCITOR NECALIFICAT LA ASAMBLAREA, MONTAREA PIESELOR": "Assembly Line Worker",
    "SOFER DE AUTOTURISME SI CAMIONETE": "Car & Van Driver",
    "MUNCITOR NECALIFICAT LA SPARGEREA SI TAIEREA MATERIALELOR DE CONSTRUCTII": "Construction Material Cutter / Labourer",
    "LUCRATOR BUCATARIE": "Kitchen Worker",
    "VÂNZATOR": "Sales Assistant",
    "AGENT DE SECURITATE": "Security Guard",
    "SUDOR": "Welder",
    "BUCATAR": "Cook / Chef",
    "AGENT DE VÂNZARI": "Sales Agent",
    "CURIER": "Courier / Delivery Driver",
    "MECANIC AUTO": "Auto Mechanic",
    "OSPATAR": "Waiter / Waitress",
    "AMBALATOR MANUAL": "Manual Packer",
    "LACATUS MECANIC": "Mechanical Fitter",
    "MUNCITOR NECALIFICAT ÎN INDUSTRIA CONFECTIILOR": "Garment Industry Worker",
    "UCENIC": "Apprentice",
    "MASINIST LA MASINI PENTRU TERASAMENTE": "Earthmoving Machine Operator",
    "LUCRATOR GESTIONAR": "Stock Controller",
    "OPERATOR INTRODUCERE, VALIDARE SI PRELUCRARE DATE": "Data Entry Operator",
    "OPERATOR LA MASINI-UNELTE CU COMANDA NUMERICA": "CNC Machine Operator",
    "AJUTOR OSPATAR": "Waiter Assistant / Busboy",
    "ÎNGRIJITOR CLADIRI": "Building Caretaker",
    "MUNCITOR NECALIFICAT LA ÎNTRETINEREA DE DRUMURI, SOSELE, PODURI, BARAJE": "Road & Bridge Maintenance Worker",
    "CAMERISTA HOTEL": "Hotel Chambermaid / Housekeeper",
    "ELECTRICIAN ÎN CONSTRUCTII": "Construction Electrician",
    "MUNCITOR NECALIFICAT ÎN AGRICULTURA": "Agricultural Labourer",
    "ASISTENT MEDICAL GENERALIST": "General Nurse",
    "ASISTENT MANAGER": "Executive Assistant",
    "AGENT CURATENIE CLADIRI SI MIJLOACE DE TRANSPORT": "Cleaning Agent (buildings & transport)",
    "DULGHER": "Carpenter / Formwork Carpenter",
    "ZIDAR ROSAR-TENCUITOR": "Bricklayer & Plasterer",
    "FIERAR BETONIST": "Reinforced Concrete Worker (Ironworker)",
    "ÎNGRIJITOR ANIMALE": "Animal Care Worker",
    "CONTABIL": "Accountant",
    "TÂMPLAR UNIVERSAL": "General Joiner / Woodworker",
    "MUNCITOR NECALIFICAT LA AMBALAREA PRODUSELOR SOLIDE SI SEMISOLIDE": "Packaging Worker",
    "BRUTAR": "Baker",
    "BARMAN": "Bartender",
    "ELECTRICIAN DE ÎNTRETINERE SI REPARATII": "Maintenance Electrician",
    "ZUGRAV": "Painter & Decorator",
    "INSTALATOR INSTALATII TEHNICO-SANITARE SI DE GAZE": "Plumber & Gas Fitter",
    "GESTIONAR DEPOZIT": "Warehouse Manager / Stock Keeper",
    "STIVUITORIST": "Forklift Operator",
    "MENAJERA": "Housekeeper / Domestic Cleaner",
    "CONFECTIONER-ASAMBLOR ARTICOLE DIN TEXTILE": "Textile Assembly Worker",
    "CASIER": "Cashier",
    "MECANIC UTILAJ": "Equipment Mechanic",
    "PATISER": "Pastry Chef",
    "SPALATOR VEHICULE": "Car Wash Operative",
    "INGINER CONSTRUCTII CIVILE, INDUSTRIALE SI AGRICOLE": "Civil & Industrial Construction Engineer",
    "INGINER MECANIC": "Mechanical Engineer",
    "Conducator auto transport rutier de persoane": "Passenger Transport Driver / Bus Driver",
    "MUNCITOR NECALIFICAT ÎN SILVICULTURA": "Forestry Labourer",
    "LACATUS CONSTRUCTII METALICE SI NAVALE": "Steel & Naval Construction Fitter",
    "SUDOR CU ARC ELECTRIC ACOPERIT SUB STRAT DE FLUX": "Submerged Arc Welder",
    "TUBULATOR NAVAL": "Naval Pipefitter",
    "LACATUS-MONTATOR AGREGATE ENERGETICE SI DE TRANSPORT": "Power & Transport Aggregate Fitter",
    "LACATUS MECANIC DE ÎNTRETINERE SI REPARATII UNIVERSALE": "Universal Maintenance Fitter",
}

def translate_job(title: str) -> str:
    t = title.split("(")[0].strip()
    return TRANSLATIONS.get(t, t.title())

# ═══════════════════════════════════════════
# SECTOR MAPPING & ICONS
# ═══════════════════════════════════════════
SECTOR_MAP = {
    "Construcții / Instalații": "Construction & Installation",
    "Producție / Logistică": "Production & Logistics",
    "RESTAURANTE": "Restaurants & Food Service",
    "COMERT": "Retail & Commerce",
    "Turism / Alimentație": "Tourism & Hospitality",
    "Servicii transport / curierat": "Transport & Courier",
    "Medicină / Sănătate /Psihoterapie": "Healthcare",
    "Agricultură / Zootehnie": "Agriculture & Livestock",
    "Vânzări": "Sales",
    "SERVICE AUTO": "Automotive Services",
    "Armată / Pază/ Protecție": "Security & Protection",
    "PRODUCTIE MOBILA": "Furniture Production",
    "IT / Telecomunicații": "IT & Telecom",
    "Retail": "Retail",
    "Altele": "Other",
}

SECTOR_ICONS = {
    "Construction & Installation": "🔨",
    "Production & Logistics": "🏭",
    "Restaurants & Food Service": "🍽️",
    "Retail & Commerce": "🛒",
    "Tourism & Hospitality": "🏨",
    "Transport & Courier": "🚛",
    "Healthcare": "🏥",
    "Agriculture & Livestock": "🌾",
    "Sales": "📊",
    "Automotive Services": "🔧",
    "Security & Protection": "🛡️",
    "Furniture Production": "🪑",
    "IT & Telecom": "💻",
    "Retail": "🛍️",
    "Other": "📋",
}

def sector_en(raw: str) -> str:
    return SECTOR_MAP.get(raw.strip(), raw.strip())


# ═══════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════
def load_data():
    sectors = defaultdict(list)
    with open(INPUT_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sec = sector_en(row.get("sector", "Other"))
            jobs_raw = row.get("jobs", "")
            jobs_translated = []
            for j in jobs_raw.split(" | "):
                title = j.split("(")[0].strip()
                count_str = ""
                if "(" in j:
                    count_str = j.split("(")[1].rstrip(")")
                en = translate_job(title)
                jobs_translated.append((en, count_str))

            sectors[sec].append({
                "city": row.get("city", "").title(),
                "jobs": jobs_translated,
                "positions": row.get("positions_total", ""),
            })
    return sectors


# ═══════════════════════════════════════════
# HTML GENERATION
# ═══════════════════════════════════════════
def make_card(entry, sector):
    city = entry["city"]
    jobs = entry["jobs"]
    positions = entry["positions"] or "?"
    icon = SECTOR_ICONS.get(sector, "📋")

    job_lines = ""
    for title, cnt in jobs[:4]:
        cnt_badge = f'<span class="cnt">{cnt} pos</span>' if cnt else ""
        job_lines += f'<div class="job-line">{title} {cnt_badge}</div>'

    wa_msg = f"Hi {CONTACT_NAME}, I found your job listings and I have qualified candidates available. Can we discuss?"
    wa_url = f"https://wa.me/{CONTACT_PHONE}?text={urllib.parse.quote(wa_msg)}"

    return f'''<div class="emp-card">
  <div class="card-top">
    <span class="card-icon">{icon}</span>
    <span class="card-loc">📍 {city}</span>
    <span class="card-pos">{positions} positions</span>
  </div>
  <div class="card-jobs">{job_lines}</div>
  <a href="{wa_url}" class="card-apply">💬 Apply Now</a>
</div>'''


def generate_html(sectors):
    total_companies = sum(len(v) for v in sectors.values())
    total_positions = 0
    for entries in sectors.values():
        for e in entries:
            try:
                total_positions += int(e["positions"])
            except (ValueError, TypeError):
                pass

    sorted_sectors = sorted(sectors.items(), key=lambda x: -len(x[1]))

    toc_rows = ""
    for sec, entries in sorted_sectors:
        icon = SECTOR_ICONS.get(sec, "📋")
        toc_rows += f'<tr><td>{icon} {sec}</td><td>{len(entries)}</td></tr>'

    sector_blocks = ""
    for sec, entries in sorted_sectors:
        icon = SECTOR_ICONS.get(sec, "📋")
        cards = "".join(make_card(e, sec) for e in entries)
        sector_blocks += f'''<div class="sector-block page-break">
  <div class="sector-header">
    <span class="sector-icon">{icon}</span>
    <h2>{sec}</h2>
    <span class="sector-count">{len(entries)} employers</span>
  </div>
  <div class="cards-grid">{cards}</div>
</div>'''

    wa_main = f"https://wa.me/{CONTACT_PHONE}?text={urllib.parse.quote('Hi, I have qualified workers available. Let us connect.')}"

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Space+Mono&display=swap" rel="stylesheet">
<style>
:root {{
  --bg:#08080d; --surface:#0f0f17; --surface-raised:#1a1a28;
  --border:#1e1e30; --text:#e8e8ec; --text-muted:#7e7e96;
  --accent:{ACCENT_COLOR}; --green:#22c55e;
  --font:'DM Sans',sans-serif; --mono:'Space Mono',monospace;
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);font-size:14px;line-height:1.5}}
a{{color:var(--accent);text-decoration:none}}

/* COVER */
.cover{{min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;
  padding:60px 40px;text-align:center;border-bottom:1px solid var(--border)}}
.cover h1{{font-size:2.4rem;font-weight:700;margin-bottom:12px;color:var(--accent)}}
.cover .sub{{font-size:1rem;color:var(--text-muted);margin-bottom:40px}}
.stats-row{{display:flex;gap:40px;margin:30px 0}}
.stat-box{{background:var(--surface);border:1px solid var(--border);border-radius:12px;
  padding:20px 32px;text-align:center}}
.stat-box .num{{font-size:2rem;font-weight:700;color:var(--accent)}}
.stat-box .label{{color:var(--text-muted);font-size:0.8rem;margin-top:4px}}
.apply-btn{{display:inline-block;background:var(--accent);color:#000;font-weight:700;
  padding:14px 32px;border-radius:8px;font-size:1rem;margin-top:20px}}

/* TOC */
.toc{{padding:40px;max-width:700px;margin:0 auto}}
.toc h2{{color:var(--accent);margin-bottom:20px;font-size:1.2rem}}
.toc table{{width:100%;border-collapse:collapse}}
.toc td{{padding:10px 12px;border-bottom:1px solid var(--border);color:var(--text-muted)}}
.toc td:last-child{{text-align:right;color:var(--accent);font-family:var(--mono)}}

/* SECTOR BLOCKS */
.sector-block{{padding:40px}}
.sector-header{{display:flex;align-items:center;gap:12px;margin-bottom:24px;
  border-left:4px solid var(--accent);padding-left:16px}}
.sector-header h2{{font-size:1.3rem;flex:1}}
.sector-count{{background:var(--surface-raised);color:var(--accent);
  padding:4px 12px;border-radius:20px;font-size:0.8rem;font-family:var(--mono)}}
.sector-icon{{font-size:1.5rem}}

/* CARDS */
.cards-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}}
.emp-card{{background:var(--surface);border:1px solid var(--border);border-radius:10px;
  padding:16px;display:flex;flex-direction:column;gap:10px}}
.card-top{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.card-icon{{font-size:1.2rem}}
.card-loc{{color:var(--text-muted);font-size:0.8rem;flex:1}}
.card-pos{{background:var(--surface-raised);color:var(--green);padding:2px 8px;
  border-radius:20px;font-size:0.75rem;font-family:var(--mono)}}
.card-jobs{{flex:1}}
.job-line{{font-size:0.82rem;color:var(--text);padding:3px 0;border-bottom:1px solid var(--border)}}
.job-line:last-child{{border-bottom:none}}
.cnt{{background:var(--surface-raised);color:var(--accent);padding:1px 6px;
  border-radius:10px;font-size:0.7rem;margin-left:6px;font-family:var(--mono)}}
.card-apply{{display:block;text-align:center;background:var(--accent);color:#000;
  font-weight:700;padding:8px;border-radius:6px;font-size:0.82rem;margin-top:4px}}

/* FOOTER */
.footer{{padding:40px;text-align:center;border-top:1px solid var(--border);color:var(--text-muted)}}

/* PAGE BREAKS */
.page-break{{page-break-before:always}}
@media print{{
  *{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
  body{{background:var(--bg)}}
  .card-apply{{display:none}}
}}
</style>
</head>
<body>

<div class="cover">
  <h1>{TITLE}</h1>
  <p class="sub">{SUBTITLE}</p>
  <div class="stats-row">
    <div class="stat-box"><div class="num">{total_companies:,}</div><div class="label">Active Employers</div></div>
    <div class="stat-box"><div class="num">{total_positions:,}</div><div class="label">Open Positions</div></div>
    <div class="stat-box"><div class="num">{len(sectors)}</div><div class="label">Sectors</div></div>
  </div>
  <a href="{wa_main}" class="apply-btn">💬 Place Candidates via WhatsApp</a>
  <p style="margin-top:16px;color:var(--text-muted);font-size:0.8rem">Source: public labor market data · {date.today().strftime('%d %B %Y')}</p>
</div>

<div class="toc page-break">
  <h2>Sectors</h2>
  <table>{toc_rows}</table>
</div>

{sector_blocks}

<div class="footer">
  <p>Contact: <a href="{wa_main}">WhatsApp {CONTACT_PHONE}</a></p>
  <p style="margin-top:8px;font-size:0.75rem">Data compiled from public labor market sources. All employer details anonymised.</p>
</div>

</body>
</html>'''


def main():
    sectors = load_data()
    html = generate_html(sectors)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    total = sum(len(v) for v in sectors.values())
    print(f"Generated: {OUTPUT_PATH}")
    print(f"Companies: {total} | Sectors: {len(sectors)}")


if __name__ == "__main__":
    main()
