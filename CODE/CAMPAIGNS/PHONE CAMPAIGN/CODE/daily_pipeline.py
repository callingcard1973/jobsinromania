#!/usr/bin/env python3
"""
Daily ANOFM Phone Campaign Pipeline — runs on raspibig at 14:00
1. Extract phones from today's ANOFM CSV → /opt/ACTIVE/PHONE_CAMPAIGN/anofm_phones_YYYYMMDD.csv
2. Generate sector HTMLs
3. Convert HTMLs → PDFs via Playwright
4. Deploy PDFs to expatsinromania.org/jobs/SECTORS/YYYYMMDD/ via cPanel API
5. Keep last 7 days of catalogs
"""
import os, sys, csv, glob, json, asyncio, shutil, requests
from datetime import date, timedelta
from collections import defaultdict
from urllib.parse import quote

TODAY    = date.today().strftime("%Y%m%d")
BASE_DIR = "/opt/ACTIVE/PHONE_CAMPAIGN"
HTML_DIR = f"{BASE_DIR}/SECTORS/{TODAY}"
PDF_DIR  = f"{BASE_DIR}/SECTORS/{TODAY}/PDF"
PHONE_CSV = f"{BASE_DIR}/anofm_phones_{TODAY}.csv"

# cPanel
CPANEL_HOST  = "nl1-cl8-ats1.a2hosting.com"
CPANEL_USER  = "loaiidil"
CPANEL_TOKEN = open("/opt/ACTIVE/PHONE_CAMPAIGN/cpanel_token.txt").read().strip()
CPANEL_BASE  = f"https://{CPANEL_HOST}:2083"
EXPATS_DIR   = f"/home/{CPANEL_USER}/expatsinromania.org/jobs/SECTORS/{TODAY}"

APPLY_URL = "https://interjob.ro/apply.html"
TELEGRAM  = "https://t.me/jobsinro"
WA_GROUP  = "https://chat.whatsapp.com/DvnchNG3vYBLnLuqY3DW9K"
FB_GROUP  = "https://www.facebook.com/groups/expatsinromania"

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
    "SUDOR": "Welder", "BUCATAR": "Cook / Chef", "AJUTOR BUCATAR": "Kitchen Assistant",
    "MANIPULANT MARFURI": "Goods Handler", "FEMEIE DE SERVICIU": "Cleaning Operative",
    "Conducător auto transport rutier de mărfuri": "Freight Truck Driver",
    "MUNCITOR NECALIFICAT LA ASAMBLAREA, MONTAREA PIESELOR": "Assembly Line Worker",
    "SOFER DE AUTOTURISME SI CAMIONETE": "Car & Van Driver",
    "LUCRATOR BUCATARIE": "Kitchen Worker", "VÂNZATOR": "Sales Assistant",
    "AGENT DE SECURITATE": "Security Guard", "AGENT DE VÂNZARI": "Sales Agent",
    "CURIER": "Courier / Delivery Driver", "MECANIC AUTO": "Auto Mechanic",
    "OSPATAR": "Waiter / Waitress", "AMBALATOR MANUAL": "Manual Packer",
    "LACATUS MECANIC": "Mechanical Fitter", "UCENIC": "Apprentice",
    "CASIER": "Cashier", "BRUTAR": "Baker", "BARMAN": "Bartender",
    "STIVUITORIST": "Forklift Operator", "MENAJERA": "Housekeeper",
    "CONTABIL": "Accountant", "DULGHER": "Carpenter",
    "ZIDAR ROSAR-TENCUITOR": "Bricklayer & Plasterer",
    "FIERAR BETONIST": "Reinforced Concrete Worker",
    "ELECTRICIAN ÎN CONSTRUCTII": "Construction Electrician",
    "ELECTRICIAN DE ÎNTRETINERE SI REPARATII": "Maintenance Electrician",
    "ZUGRAV": "Painter & Decorator",
    "INSTALATOR INSTALATII TEHNICO-SANITARE SI DE GAZE": "Plumber & Gas Fitter",
    "GESTIONAR DEPOZIT": "Warehouse Keeper",
    "LACATUS CONSTRUCTII METALICE SI NAVALE": "Steel & Naval Fitter",
    "SUDOR CU ARC ELECTRIC ACOPERIT SUB STRAT DE FLUX": "Submerged Arc Welder",
    "INGINER MECANIC": "Mechanical Engineer",
    "INGINER CONSTRUCTII CIVILE, INDUSTRIALE SI AGRICOLE": "Civil Construction Engineer",
    "Conducator auto transport rutier de persoane": "Passenger Bus Driver",
    "MUNCITOR NECALIFICAT ÎN AGRICULTURA": "Agricultural Labourer",
    "MUNCITOR NECALIFICAT LA DEMOLAREA CLADIRILOR, CAPTUSELI ZIDARIE, PLACI MOZAIC, FAIANTA, GRESIE, PARCHET": "General Construction Labourer",
    "MUNCITOR NECALIFICAT LA SPARGEREA SI TAIEREA MATERIALELOR DE CONSTRUCTII": "Construction Labourer",
    "MUNCITOR NECALIFICAT LA ÎNTRETINEREA DE DRUMURI, SOSELE, PODURI, BARAJE": "Road Maintenance Worker",
    "MUNCITOR NECALIFICAT LA AMBALAREA PRODUSELOR SOLIDE SI SEMISOLIDE": "Packaging Worker",
    "MUNCITOR NECALIFICAT ÎN INDUSTRIA CONFECTIILOR": "Garment Industry Worker",
    "MUNCITOR NECALIFICAT ÎN SILVICULTURA": "Forestry Labourer",
    "LUCRATOR COMERCIAL": "Sales & Retail Worker",
    "PATISER": "Pastry Chef", "MECANIC UTILAJ": "Equipment Mechanic",
    "ASISTENT MEDICAL GENERALIST": "General Nurse",
    "CAMERISTA HOTEL": "Hotel Chambermaid",
    "MASINIST LA MASINI PENTRU TERASAMENTE": "Earthmoving Machine Operator",
    "OPERATOR LA MASINI-UNELTE CU COMANDA NUMERICA": "CNC Machine Operator",
}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
:root{--bg:#07070e;--s0:#0c0c18;--s1:#131320;--s2:#1c1c2e;--border:#22223a;
  --text:#eaeaf0;--muted:#6b6b8a;--accent:#f59e0b;--green:#22c55e;
  --font:'DM Sans',sans-serif;--mono:'Space Mono',monospace}
body{background:var(--bg);color:var(--text);font-family:var(--font);font-size:13px;line-height:1.5}
.cover{min-height:70vh;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:50px 30px;text-align:center;
  background:radial-gradient(ellipse 80% 60% at 50% 30%,rgba(245,158,11,.07) 0%,transparent 70%)}
.badge{display:inline-block;background:rgba(245,158,11,.12);border:1px solid rgba(245,158,11,.3);
  color:var(--accent);padding:4px 14px;border-radius:20px;font-size:11px;
  letter-spacing:.1em;text-transform:uppercase;font-family:var(--mono);margin-bottom:18px}
h1{font-size:clamp(1.6rem,4vw,2.6rem);font-weight:700;
  background:linear-gradient(135deg,#fff 30%,#f59e0b);
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:8px}
.sub{color:var(--muted);font-size:.85rem;margin-bottom:28px}
.stats{display:flex;gap:14px;flex-wrap:wrap;justify-content:center;margin-bottom:28px}
.stat{background:var(--s1);border:1px solid var(--border);border-radius:10px;padding:16px 22px;text-align:center}
.stat .n{font-size:1.6rem;font-weight:700;color:var(--accent);font-family:var(--mono)}
.stat .l{font-size:.7rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-top:3px}
.cta{display:inline-block;background:linear-gradient(135deg,#f59e0b,#d97706);
  color:#000;font-weight:700;padding:12px 28px;border-radius:10px;font-size:.88rem}
.comm{display:flex;gap:10px;margin-top:16px;flex-wrap:wrap;justify-content:center}
.comm a{background:var(--s1);border:1px solid var(--border);border-radius:7px;
  padding:7px 14px;font-size:.75rem;color:var(--muted)}
.section{padding:30px}
.sec-head{display:flex;align-items:center;gap:10px;margin-bottom:20px;
  padding-bottom:12px;border-bottom:1px solid var(--border)}
.sec-ico{font-size:1.4rem}
.sec-head h2{font-size:1.1rem;font-weight:700;flex:1}
.sec-cnt{background:var(--s2);color:var(--accent);padding:3px 10px;border-radius:20px;font-size:.72rem;font-family:var(--mono)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:11px}
.card{background:var(--s0);border:1px solid var(--border);border-radius:9px;padding:13px;display:flex;flex-direction:column;gap:9px}
.ct{display:flex;align-items:flex-start;gap:7px}
.ci{font-size:1.1rem;line-height:1}
.cm{flex:1}
.cy{font-size:.74rem;color:var(--muted)}
.pos{display:inline-block;background:rgba(34,197,94,.1);color:var(--green);padding:2px 6px;border-radius:9px;font-size:.68rem;font-family:var(--mono);margin-top:2px}
.jobs{flex:1;display:flex;flex-direction:column;gap:2px}
.jr{font-size:.76rem;padding:2px 0;border-bottom:1px solid var(--border);display:flex;align-items:baseline;gap:4px}
.jr:last-child{border-bottom:none}
.dot{color:var(--accent);font-size:.58rem;flex-shrink:0}
.cnt{margin-left:auto;background:var(--s2);color:var(--muted);padding:1px 5px;border-radius:6px;font-size:.65rem;font-family:var(--mono)}
.apply{display:block;text-align:center;background:linear-gradient(135deg,#f59e0b,#d97706);
  color:#000;font-weight:700;font-size:.76rem;padding:8px;border-radius:7px}
.footer{padding:30px;text-align:center;border-top:1px solid var(--border);color:var(--muted);font-size:.76rem}
@media print{*{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
"""

FONTS = '<link rel="preconnect" href="https://fonts.googleapis.com"><link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">'


def translate(raw):
    t = raw.split("(")[0].strip()
    return TRANSLATIONS.get(t, t.title())


def re_slug(s):
    import re
    return re.sub(r'[^a-z0-9]+', '_', s.lower()).strip('_')[:30]


def load_sectors():
    sectors = defaultdict(list)
    meta = {}
    if not os.path.exists(PHONE_CSV):
        # fallback to latest
        files = sorted(glob.glob(f"{BASE_DIR}/anofm_phones_*.csv"))
        csv_file = files[-1] if files else None
    else:
        csv_file = PHONE_CSV

    if not csv_file:
        print("ERROR: No phone CSV found", file=sys.stderr)
        sys.exit(1)

    print(f"Input: {csv_file}")
    with open(csv_file, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            raw = row.get("sector", "").strip()
            if raw in SECTOR_MAP:
                name, slug, icon = SECTOR_MAP[raw]
            else:
                name, slug, icon = raw.title(), re_slug(raw), "📋"
            meta[raw] = (name, slug, icon)
            jobs = []
            for j in row.get("jobs", "").split(" | "):
                t = j.split("(")[0].strip()
                cnt = j.split("(")[1].rstrip(")") if "(" in j else ""
                jobs.append((translate(t), cnt))
            sectors[raw].append({
                "city": row.get("city", "").title(),
                "jobs": jobs,
                "positions": row.get("positions_total", ""),
            })
    return sectors, meta


def make_card(e, icon):
    jlines = ""
    for t, cnt in e["jobs"][:4]:
        b = f'<span class="cnt">{cnt}</span>' if cnt else ""
        jlines += f'<div class="jr"><span class="dot">▸</span>{t}{b}</div>'
    pos = e["positions"] or "?"
    return f'<div class="card"><div class="ct"><span class="ci">{icon}</span><div class="cm"><div class="cy">📍 {e["city"]}</div><span class="pos">{pos} pos</span></div></div><div class="jobs">{jlines}</div><a href="{APPLY_URL}" class="apply">Apply Now →</a></div>'


def make_html(name, icon, entries):
    total_pos = sum(int(e["positions"]) for e in entries if str(e["positions"]).isdigit())
    cards = "".join(make_card(e, icon) for e in entries)
    fmt_date = date.today().strftime("%d %B %Y")
    return f'''<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>{name} Jobs — Romania</title>{FONTS}<style>{CSS}</style></head><body>
<div class="cover">
  <div class="badge">Romania · {TODAY}</div>
  <h1>{icon} {name}</h1>
  <p class="sub">Labor Market Catalog · {date.today().strftime("%B %Y")}</p>
  <div class="stats">
    <div class="stat"><div class="n">{len(entries):,}</div><div class="l">Employers</div></div>
    <div class="stat"><div class="n">{total_pos:,}</div><div class="l">Positions</div></div>
  </div>
  <a href="{APPLY_URL}" class="cta">Apply Now →</a>
  <div class="comm">
    <a href="{TELEGRAM}">✈️ t.me/jobsinro</a>
    <a href="{WA_GROUP}">💬 English Jobs</a>
    <a href="{FB_GROUP}">🌍 Expats in Romania</a>
  </div>
</div>
<div class="section">
  <div class="sec-head"><span class="sec-ico">{icon}</span><h2>{name}</h2><span class="sec-cnt">{len(entries)} employers</span></div>
  <div class="grid">{cards}</div>
</div>
<div class="footer"><p><a href="{APPLY_URL}">interjob.ro/apply.html</a> · <a href="{TELEGRAM}">t.me/jobsinro</a></p><p style="margin-top:6px">Public labor market data · {fmt_date}</p></div>
</body></html>'''


async def convert_to_pdf():
    from playwright.async_api import async_playwright
    html_files = sorted(glob.glob(f"{HTML_DIR}/*.html"))
    print(f"Converting {len(html_files)} HTMLs to PDF...")
    os.makedirs(PDF_DIR, exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for hf in html_files:
            name = os.path.basename(hf).replace(".html", ".pdf")
            out = f"{PDF_DIR}/{name}"
            page = await browser.new_page()
            await page.goto(f"file://{hf}", wait_until="networkidle")
            await page.pdf(path=out, print_background=True, format="A4",
                           margin={"top":"10mm","bottom":"10mm","left":"10mm","right":"10mm"})
            await page.close()
            print(f"  ✓ {name} ({os.path.getsize(out)//1024}KB)")
        await browser.close()


def deploy_pdfs():
    auth = (CPANEL_USER, CPANEL_TOKEN)
    # Create dated directory on expats site
    requests.get(f"{CPANEL_BASE}/execute/Fileman/mkdir",
                 params={"path": f"/home/{CPANEL_USER}/expatsinromania.org/jobs/SECTORS",
                         "name": TODAY},
                 auth=auth, verify=False, timeout=30)

    pdfs = sorted(glob.glob(f"{PDF_DIR}/*.pdf"))
    ok = 0
    for pdf in pdfs:
        with open(pdf, "rb") as f:
            r = requests.post(
                f"{CPANEL_BASE}/execute/Fileman/upload_files",
                params={"dir": EXPATS_DIR},
                files={"file-1": (os.path.basename(pdf), f, "application/pdf")},
                auth=auth, verify=False, timeout=120
            )
        if r.status_code == 200:
            ok += 1
            print(f"  ✓ deployed {os.path.basename(pdf)}")
        else:
            print(f"  ✗ FAILED {os.path.basename(pdf)}: {r.status_code}")
    print(f"Deployed {ok}/{len(pdfs)} PDFs to expatsinromania.org/jobs/SECTORS/{TODAY}/")


def cleanup_old(keep=7):
    """Remove dated dirs older than keep days."""
    cutoff = (date.today() - timedelta(days=keep)).strftime("%Y%m%d")
    for d in glob.glob(f"{BASE_DIR}/SECTORS/2*"):
        dirname = os.path.basename(d)
        if dirname.isdigit() and dirname < cutoff:
            shutil.rmtree(d)
            print(f"Cleaned: {d}")


def main():
    print(f"=== Daily Catalog Pipeline {TODAY} ===")

    # Step 1: Generate HTMLs
    os.makedirs(HTML_DIR, exist_ok=True)
    sectors, meta = load_sectors()
    manifest = []
    for raw, entries in sorted(sectors.items(), key=lambda x: -len(x[1])):
        name, slug, icon = meta[raw]
        html = make_html(name, icon, entries)
        out = f"{HTML_DIR}/{slug}.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        total_pos = sum(int(e["positions"]) for e in entries if str(e["positions"]).isdigit())
        manifest.append({"name": name, "slug": slug, "icon": icon,
                          "count": len(entries), "positions": total_pos})
        print(f"  HTML: {slug}.html ({len(entries)} employers)")
    with open(f"{HTML_DIR}/manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False)
    print(f"Step 1 done: {len(manifest)} sector HTMLs")

    # Step 2: Convert to PDF
    asyncio.run(convert_to_pdf())
    print("Step 2 done: PDFs generated")

    # Step 3: Deploy
    deploy_pdfs()
    print("Step 3 done: deployed")

    # Step 4: Cleanup old
    cleanup_old(keep=7)
    print("Step 4 done: old catalogs cleaned")
    print(f"=== Pipeline complete ===")


if __name__ == "__main__":
    main()
