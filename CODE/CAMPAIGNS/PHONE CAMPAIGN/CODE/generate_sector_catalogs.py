#!/usr/bin/env python3
"""
Generate one HTML catalog per sector from ANOFM phone data.
Output: CATALOGS/TUDOR/SECTORS/construction.html, production.html, etc.
Then convert each to PDF via WSL Firefox.
"""
import sys, io, csv, os, urllib.parse
from collections import defaultdict
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TODAY       = date.today().strftime("%Y%m%d")
INPUT_PATH  = rf"D:\MEMORY\PHONE CAMPAIGN\DATA\anofm_phones_{TODAY}_v3.csv"
# Fallback: use latest available CSV if today's not yet extracted
if not os.path.exists(INPUT_PATH):
    import glob as _glob
    _files = sorted(_glob.glob(r"D:\MEMORY\PHONE CAMPAIGN\DATA\anofm_phones_*_v3.csv"))
    INPUT_PATH = _files[-1] if _files else INPUT_PATH
SECTOR_DIR  = rf"D:\MEMORY\PHONE CAMPAIGN\CATALOGS\TUDOR\SECTORS\{TODAY}"
APPLY_URL   = "https://interjob.ro/apply.html"
TELEGRAM    = "https://t.me/jobsinro"
WA_GROUP    = "https://chat.whatsapp.com/DvnchNG3vYBLnLuqY3DW9K"
FB_GROUP    = "https://www.facebook.com/groups/expatsinromania"
ACCENT      = "#f59e0b"
GREEN       = "#22c55e"

SECTOR_MAP = {
    "Construcții / Instalații": ("Construction & Installation", "construction", "🔨"),
    "Producție / Logistică":    ("Production & Logistics",     "production",   "🏭"),
    "RESTAURANTE":              ("Restaurants & Food Service", "restaurants",  "🍽️"),
    "COMERT":                   ("Retail & Commerce",          "retail",       "🛒"),
    "Turism / Alimentație":     ("Tourism & Hospitality",      "tourism",      "🏨"),
    "Servicii transport / curierat": ("Transport & Courier",  "transport",    "🚛"),
    "Medicină / Sănătate /Psihoterapie": ("Healthcare",       "healthcare",   "🏥"),
    "Agricultură / Zootehnie":  ("Agriculture & Livestock",   "agriculture",  "🌾"),
    "Vânzări":                  ("Sales",                      "sales",        "📊"),
    "SERVICE AUTO":             ("Automotive Services",        "automotive",   "🔧"),
    "Armată / Pază/ Protecție": ("Security & Protection",     "security",     "🛡️"),
    "PRODUCTIE MOBILA":         ("Furniture Production",       "furniture",    "🪑"),
    "IT / Telecomunicații":     ("IT & Telecom",               "it_telecom",   "💻"),
    "Retail":                   ("Retail",                     "retail2",      "🛍️"),
    "Altele":                   ("Other Sectors",              "other",        "📋"),
}

TRANSLATIONS = {
    "LUCRATOR COMERCIAL": "Sales & Retail Worker",
    "AJUTOR BUCATAR": "Kitchen Assistant",
    "MANIPULANT MARFURI": "Goods Handler",
    "FEMEIE DE SERVICIU": "Cleaning Operative",
    "Conducător auto transport rutier de mărfuri": "Freight Truck Driver",
    "MUNCITOR NECALIFICAT LA ASAMBLAREA, MONTAREA PIESELOR": "Assembly Line Worker",
    "SOFER DE AUTOTURISME SI CAMIONETE": "Car & Van Driver",
    "MUNCITOR NECALIFICAT LA SPARGEREA SI TAIEREA MATERIALELOR DE CONSTRUCTII": "Construction Labourer",
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
    "AJUTOR OSPATAR": "Waiter Assistant",
    "ÎNGRIJITOR CLADIRI": "Building Caretaker",
    "MUNCITOR NECALIFICAT LA ÎNTRETINEREA DE DRUMURI, SOSELE, PODURI, BARAJE": "Road Maintenance Worker",
    "CAMERISTA HOTEL": "Hotel Chambermaid",
    "ELECTRICIAN ÎN CONSTRUCTII": "Construction Electrician",
    "MUNCITOR NECALIFICAT ÎN AGRICULTURA": "Agricultural Labourer",
    "ASISTENT MEDICAL GENERALIST": "General Nurse",
    "ASISTENT MANAGER": "Executive Assistant",
    "AGENT CURATENIE CLADIRI SI MIJLOACE DE TRANSPORT": "Cleaning Agent",
    "DULGHER": "Carpenter",
    "ZIDAR ROSAR-TENCUITOR": "Bricklayer & Plasterer",
    "FIERAR BETONIST": "Reinforced Concrete Worker",
    "ÎNGRIJITOR ANIMALE": "Animal Care Worker",
    "CONTABIL": "Accountant",
    "TÂMPLAR UNIVERSAL": "Joiner / Woodworker",
    "MUNCITOR NECALIFICAT LA AMBALAREA PRODUSELOR SOLIDE SI SEMISOLIDE": "Packaging Worker",
    "BRUTAR": "Baker",
    "BARMAN": "Bartender",
    "ELECTRICIAN DE ÎNTRETINERE SI REPARATII": "Maintenance Electrician",
    "ZUGRAV": "Painter & Decorator",
    "INSTALATOR INSTALATII TEHNICO-SANITARE SI DE GAZE": "Plumber & Gas Fitter",
    "GESTIONAR DEPOZIT": "Warehouse Keeper",
    "STIVUITORIST": "Forklift Operator",
    "MENAJERA": "Housekeeper",
    "CONFECTIONER-ASAMBLOR ARTICOLE DIN TEXTILE": "Textile Assembly Worker",
    "CASIER": "Cashier",
    "MECANIC UTILAJ": "Equipment Mechanic",
    "PATISER": "Pastry Chef",
    "SPALATOR VEHICULE": "Car Wash Operative",
    "INGINER CONSTRUCTII CIVILE, INDUSTRIALE SI AGRICOLE": "Civil Construction Engineer",
    "INGINER MECANIC": "Mechanical Engineer",
    "Conducator auto transport rutier de persoane": "Passenger Bus Driver",
    "MUNCITOR NECALIFICAT ÎN SILVICULTURA": "Forestry Labourer",
    "LACATUS CONSTRUCTII METALICE SI NAVALE": "Steel & Naval Fitter",
    "SUDOR CU ARC ELECTRIC ACOPERIT SUB STRAT DE FLUX": "Submerged Arc Welder",
    "TUBULATOR NAVAL": "Naval Pipefitter",
    "LACATUS-MONTATOR AGREGATE ENERGETICE SI DE TRANSPORT": "Power & Transport Fitter",
    "LACATUS MECANIC DE ÎNTRETINERE SI REPARATII UNIVERSALE": "Universal Maintenance Fitter",
    "MUNCITOR NECALIFICAT LA DEMOLAREA CLADIRILOR, CAPTUSELI ZIDARIE, PLACI MOZAIC, FAIANTA, GRESIE, PARCHET": "General Construction Labourer",
}

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#07070e;--s0:#0c0c18;--s1:#131320;--s2:#1c1c2e;
  --border:#22223a;--text:#eaeaf0;--muted:#6b6b8a;
  --accent:{ACCENT};--green:{GREEN};
  --font:'DM Sans',sans-serif;--mono:'Space Mono',monospace;
}}
html{{background:var(--bg)}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);font-size:13px;line-height:1.5}}
a{{color:var(--accent);text-decoration:none}}
.cover{{min-height:80vh;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:60px 40px;text-align:center;position:relative}}
.cover::before{{content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 80% 60% at 50% 40%,rgba(245,158,11,.07) 0%,transparent 70%);
  pointer-events:none}}
.eyebrow{{display:inline-block;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.3);
  color:var(--accent);padding:5px 16px;border-radius:20px;font-size:11px;
  letter-spacing:.12em;text-transform:uppercase;font-family:var(--mono);margin-bottom:20px}}
.cover h1{{font-size:clamp(1.8rem,5vw,3rem);font-weight:700;
  background:linear-gradient(135deg,#fff 30%,var(--accent));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}}
.cover .sub{{color:var(--muted);font-size:.9rem;margin-bottom:36px}}
.stats{{display:flex;gap:16px;flex-wrap:wrap;justify-content:center;margin-bottom:36px}}
.stat{{background:var(--s1);border:1px solid var(--border);border-radius:10px;
  padding:18px 26px;text-align:center}}
.stat .n{{font-size:1.8rem;font-weight:700;color:var(--accent);font-family:var(--mono)}}
.stat .l{{font-size:.72rem;color:var(--muted);margin-top:3px;text-transform:uppercase;letter-spacing:.08em}}
.cover-cta{{display:inline-block;background:linear-gradient(135deg,var(--accent),#d97706);
  color:#000;font-weight:700;padding:13px 32px;border-radius:10px;font-size:.9rem}}
.comm{{display:flex;gap:12px;margin-top:20px;flex-wrap:wrap;justify-content:center}}
.comm a{{background:var(--s1);border:1px solid var(--border);border-radius:8px;
  padding:8px 16px;font-size:.78rem;color:var(--muted)}}
.comm a:hover{{border-color:var(--accent);color:var(--accent)}}
.section{{padding:40px}}
.sec-head{{display:flex;align-items:center;gap:12px;margin-bottom:24px;
  padding-bottom:14px;border-bottom:1px solid var(--border)}}
.sec-ico{{font-size:1.6rem}}
.sec-head h2{{font-size:1.2rem;font-weight:700;flex:1}}
.sec-count{{background:var(--s2);color:var(--accent);padding:4px 12px;
  border-radius:20px;font-size:.74rem;font-family:var(--mono)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:12px}}
.card{{background:var(--s0);border:1px solid var(--border);border-radius:10px;
  padding:14px;display:flex;flex-direction:column;gap:10px}}
.card-top{{display:flex;align-items:flex-start;gap:8px}}
.card-ico{{font-size:1.2rem;line-height:1}}
.card-meta{{flex:1}}
.card-city{{font-size:.76rem;color:var(--muted)}}
.pos{{display:inline-block;background:rgba(34,197,94,.1);color:var(--green);
  padding:2px 7px;border-radius:10px;font-size:.7rem;font-family:var(--mono);margin-top:3px}}
.jobs{{flex:1;display:flex;flex-direction:column;gap:2px}}
.jr{{font-size:.78rem;padding:3px 0;border-bottom:1px solid var(--border);
  display:flex;align-items:baseline;gap:5px}}
.jr:last-child{{border-bottom:none}}
.dot{{color:var(--accent);font-size:.6rem;flex-shrink:0}}
.cnt{{margin-left:auto;background:var(--s2);color:var(--muted);
  padding:1px 5px;border-radius:7px;font-size:.67rem;font-family:var(--mono)}}
.apply{{display:block;text-align:center;background:linear-gradient(135deg,var(--accent),#d97706);
  color:#000;font-weight:700;font-size:.78rem;padding:8px;border-radius:7px}}
.footer{{padding:40px;text-align:center;border-top:1px solid var(--border);
  color:var(--muted);font-size:.78rem}}
@media print{{
  *{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
  .apply{{background:var(--accent)!important}}
}}
"""

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">'


def translate_job(raw):
    t = raw.split("(")[0].strip()
    return TRANSLATIONS.get(t, t.title())


def make_card(entry, icon):
    job_lines = ""
    for title, cnt in entry["jobs"][:4]:
        badge = f'<span class="cnt">{cnt}</span>' if cnt else ""
        job_lines += f'<div class="jr"><span class="dot">▸</span>{title}{badge}</div>'
    pos = entry["positions"] or "?"
    return f'''<div class="card">
  <div class="card-top">
    <span class="card-ico">{icon}</span>
    <div class="card-meta">
      <div class="card-city">📍 {entry["city"]}</div>
      <span class="pos">{pos} positions</span>
    </div>
  </div>
  <div class="jobs">{job_lines}</div>
  <a href="{APPLY_URL}" class="apply">Apply Now →</a>
</div>'''


def make_html(sector_name, icon, entries, slug):
    total_pos = sum(int(e["positions"]) for e in entries if str(e["positions"]).isdigit())
    cards = "".join(make_card(e, icon) for e in entries)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{sector_name} Jobs — Romania</title>
{FONTS}
<style>{CSS}</style>
</head>
<body>
<div class="cover">
  <div class="eyebrow">Romania · April 2026</div>
  <h1>{icon} {sector_name}</h1>
  <p class="sub">Labor Market Catalog · April 2026</p>
  <div class="stats">
    <div class="stat"><div class="n">{len(entries):,}</div><div class="l">Employers</div></div>
    <div class="stat"><div class="n">{total_pos:,}</div><div class="l">Open Positions</div></div>
  </div>
  <a href="{APPLY_URL}" class="cover-cta">Apply Now →</a>
  <div class="comm">
    <a href="{TELEGRAM}">✈️ t.me/jobsinro</a>
    <a href="{WA_GROUP}">💬 English Jobs in Romania</a>
    <a href="{FB_GROUP}">🌍 Expats in Romania</a>
  </div>
</div>
<div class="section">
  <div class="sec-head">
    <span class="sec-ico">{icon}</span>
    <h2>{sector_name}</h2>
    <span class="sec-count">{len(entries)} employers</span>
  </div>
  <div class="grid">{cards}</div>
</div>
<div class="footer">
  <p><a href="{APPLY_URL}">interjob.ro/apply.html</a> · <a href="{TELEGRAM}">t.me/jobsinro</a> · <a href="{WA_GROUP}">WhatsApp Group</a> · <a href="{FB_GROUP}">Expats in Romania</a></p>
  <p style="margin-top:8px">Public labor market data · {date.today().strftime("%B %Y")}</p>
</div>
</body>
</html>'''


def load_by_sector():
    sectors = defaultdict(list)
    raw_map = {}  # raw sector → (name, slug, icon)
    with open(INPUT_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw_sec = row.get("sector", "").strip()
            if raw_sec in SECTOR_MAP:
                name, slug, icon = SECTOR_MAP[raw_sec]
            else:
                import re as _re
                slug = _re.sub(r'[^a-z0-9]+', '_', raw_sec.lower()).strip('_')[:30]
                name, icon = raw_sec.title(), "📋"
            raw_map[raw_sec] = (name, slug, icon)

            jobs = []
            for j in row.get("jobs", "").split(" | "):
                t = j.split("(")[0].strip()
                cnt = j.split("(")[1].rstrip(")") if "(" in j else ""
                jobs.append((translate_job(t), cnt))

            sectors[raw_sec].append({
                "city": row.get("city", "").title(),
                "jobs": jobs,
                "positions": row.get("positions_total", ""),
            })
    return sectors, raw_map


def main():
    os.makedirs(SECTOR_DIR, exist_ok=True)
    sectors, raw_map = load_by_sector()
    sorted_sectors = sorted(sectors.items(), key=lambda x: -len(x[1]))

    manifest = []  # for landing page

    for raw_sec, entries in sorted_sectors:
        name, slug, icon = raw_map[raw_sec]
        html = make_html(name, icon, entries, slug)
        out_path = os.path.join(SECTOR_DIR, f"{slug}.html")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        size_kb = os.path.getsize(out_path) // 1024
        total_pos = sum(int(e["positions"]) for e in entries if str(e["positions"]).isdigit())
        print(f"  {icon} {name:35s} {len(entries):5d} employers  {size_kb:5d}KB  → {slug}.html")
        manifest.append({
            "name": name, "slug": slug, "icon": icon,
            "count": len(entries), "positions": total_pos,
            "size_kb": size_kb,
        })

    # Save manifest for landing page generator
    import json
    manifest_path = os.path.join(SECTOR_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"\n✓ {len(manifest)} sector HTMLs in {SECTOR_DIR}")
    print(f"  Manifest: {manifest_path}")
    print(f"\nNext: run convert_sectors_to_pdf.sh to generate PDFs")


if __name__ == "__main__":
    main()
