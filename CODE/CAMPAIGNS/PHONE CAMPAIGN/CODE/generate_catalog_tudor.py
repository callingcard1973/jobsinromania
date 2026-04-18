#!/usr/bin/env python3
"""
Tudor Jobs Catalog — Romania
Dark-theme, anonymous, print-ready. Apply → interjob.ro/apply.html
Community: Telegram + WhatsApp group + Facebook Expats group
"""
import sys, io, csv, os, urllib.parse
from collections import defaultdict
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ═══════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════
TITLE       = "Jobs in Romania"
SUBTITLE    = "Labor Market Catalog · April 2026"
APPLY_URL   = "https://interjob.ro/apply.html"
TELEGRAM    = "https://t.me/jobsinro"
WA_GROUP    = "https://chat.whatsapp.com/DvnchNG3vYBLnLuqY3DW9K"
FB_GROUP    = "https://www.facebook.com/groups/expatsinromania"
INPUT_PATH  = r"D:\MEMORY\PHONE CAMPAIGN\DATA\anofm_phones_20260416_v3.csv"
OUTPUT_PATH = r"D:\MEMORY\PHONE CAMPAIGN\CATALOGS\TUDOR\jobs_catalog_april_tudor.html"
ACCENT      = "#f59e0b"
BLUE        = "#3b82f6"
GREEN       = "#22c55e"
PURPLE      = "#a855f7"

# ═══════════════════════════════════════════
# JOB TITLE TRANSLATIONS
# ═══════════════════════════════════════════
TRANSLATIONS = {
    "LUCRATOR COMERCIAL": "Sales & Retail Worker",
    "MUNCITOR NECALIFICAT LA DEMOLAREA CLADIRILOR, CAPTUSELI ZIDARIE, PLACI MOZAIC, FAIANTA, GRESIE, PARCHET": "General Construction Labourer",
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
}

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
    "Altele": "Other Sectors",
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
    "Other Sectors": "📋",
}

def translate_job(raw):
    t = raw.split("(")[0].strip()
    return TRANSLATIONS.get(t, t.title())

def sector_en(raw):
    return SECTOR_MAP.get(raw.strip(), raw.strip())

def load_data():
    sectors = defaultdict(list)
    with open(INPUT_PATH, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            sec = sector_en(row.get("sector", "Other Sectors"))
            jobs_raw = row.get("jobs", "")
            jobs = []
            for j in jobs_raw.split(" | "):
                title = j.split("(")[0].strip()
                cnt = j.split("(")[1].rstrip(")") if "(" in j else ""
                jobs.append((translate_job(title), cnt))
            sectors[sec].append({
                "city": row.get("city", "").title(),
                "jobs": jobs,
                "positions": row.get("positions_total", ""),
            })
    return sectors

def make_card(entry, sector):
    icon = SECTOR_ICONS.get(sector, "📋")
    job_lines = ""
    for title, cnt in entry["jobs"][:4]:
        badge = f'<span class="cnt">{cnt}</span>' if cnt else ""
        job_lines += f'<div class="job-row"><span class="job-dot">▸</span>{title}{badge}</div>'
    pos = entry["positions"] or "?"
    return f'''<div class="card">
  <div class="card-head">
    <span class="card-ico">{icon}</span>
    <div class="card-meta">
      <span class="card-city">📍 {entry["city"]}</span>
      <span class="pos-badge">{pos} pos</span>
    </div>
  </div>
  <div class="card-jobs">{job_lines}</div>
  <a href="{APPLY_URL}" class="apply-btn">Apply Now →</a>
</div>'''

def generate_html(sectors):
    total_co = sum(len(v) for v in sectors.values())
    total_pos = sum(
        int(e["positions"]) for v in sectors.values()
        for e in v if str(e["positions"]).isdigit()
    )
    sorted_sectors = sorted(sectors.items(), key=lambda x: -len(x[1]))

    # TOC rows
    toc = ""
    for sec, entries in sorted_sectors:
        ico = SECTOR_ICONS.get(sec, "📋")
        toc += f'<div class="toc-row"><span>{ico} {sec}</span><span class="toc-num">{len(entries)}</span></div>'

    # Sector blocks
    blocks = ""
    for sec, entries in sorted_sectors:
        ico = SECTOR_ICONS.get(sec, "📋")
        cards = "".join(make_card(e, sec) for e in entries)
        blocks += f'''<section class="sector-section page-break">
  <div class="sector-head">
    <span class="sec-ico">{ico}</span>
    <h2>{sec}</h2>
    <span class="sec-count">{len(entries)} employers</span>
  </div>
  <div class="grid">{cards}</div>
</section>'''

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,500;0,9..40,700;1,9..40,300&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
/* ── RESET & TOKENS ─────────────────────────── */
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#07070e;--s0:#0c0c18;--s1:#131320;--s2:#1c1c2e;
  --border:#22223a;--text:#eaeaf0;--muted:#6b6b8a;--dim:#3a3a58;
  --accent:{ACCENT};--blue:{BLUE};--green:{GREEN};--purple:{PURPLE};
  --r:10px;--font:'DM Sans',sans-serif;--mono:'Space Mono',monospace;
}}
html{{background:var(--bg)}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);
  font-size:13.5px;line-height:1.55;
  background-image:
    linear-gradient(var(--border) 1px,transparent 1px),
    linear-gradient(90deg,var(--border) 1px,transparent 1px);
  background-size:40px 40px;
  background-position:center center;
}}
a{{color:var(--accent);text-decoration:none}}

/* ── COVER ──────────────────────────────────── */
.cover{{
  min-height:100vh;display:flex;flex-direction:column;
  align-items:center;justify-content:center;
  padding:80px 40px;text-align:center;
  position:relative;overflow:hidden;
}}
.cover::before{{
  content:'';position:absolute;inset:0;
  background:radial-gradient(ellipse 80% 60% at 50% 40%,
    rgba(245,158,11,.08) 0%,transparent 70%);
  pointer-events:none;
}}
.cover-eyebrow{{
  display:inline-block;
  background:rgba(245,158,11,.12);
  border:1px solid rgba(245,158,11,.3);
  color:var(--accent);
  padding:5px 18px;border-radius:20px;
  font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  font-family:var(--mono);margin-bottom:24px;
}}
.cover h1{{
  font-size:clamp(2.2rem,6vw,3.6rem);font-weight:700;
  line-height:1.1;letter-spacing:-.02em;
  background:linear-gradient(135deg,#fff 30%,var(--accent));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  margin-bottom:14px;
}}
.cover .sub{{color:var(--muted);font-size:.95rem;margin-bottom:48px}}
.stats{{display:flex;gap:20px;flex-wrap:wrap;justify-content:center;margin-bottom:48px}}
.stat{{
  background:var(--s1);border:1px solid var(--border);
  border-radius:var(--r);padding:22px 30px;min-width:140px;
}}
.stat .n{{font-size:2rem;font-weight:700;color:var(--accent);font-family:var(--mono)}}
.stat .l{{font-size:.75rem;color:var(--muted);margin-top:4px;text-transform:uppercase;letter-spacing:.08em}}
.cover-cta{{
  display:inline-block;
  background:linear-gradient(135deg,var(--accent),#d97706);
  color:#000;font-weight:700;padding:15px 36px;
  border-radius:var(--r);font-size:.95rem;letter-spacing:.02em;
  box-shadow:0 0 32px rgba(245,158,11,.25);
}}
.cover-note{{margin-top:20px;color:var(--dim);font-size:.78rem;font-family:var(--mono)}}

/* ── COMMUNITY PAGE ─────────────────────────── */
.community{{
  min-height:100vh;display:flex;flex-direction:column;
  justify-content:center;padding:80px 40px;
  border-top:1px solid var(--border);
}}
.community h2{{
  font-size:1.6rem;font-weight:700;color:var(--text);
  margin-bottom:8px;text-align:center;
}}
.community .comm-sub{{
  color:var(--muted);text-align:center;margin-bottom:50px;font-size:.9rem;
}}
.comm-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:24px}}
.comm-card{{
  background:var(--s1);border:1px solid var(--border);
  border-radius:14px;padding:32px 28px;
  position:relative;overflow:hidden;
  transition:border-color .2s;
}}
.comm-card::before{{
  content:'';position:absolute;top:0;left:0;right:0;height:3px;
  border-radius:14px 14px 0 0;
}}
.comm-card.tg::before{{background:linear-gradient(90deg,#2AABEE,#229ED9)}}
.comm-card.wa::before{{background:linear-gradient(90deg,#25D366,#128C7E)}}
.comm-card.fb::before{{background:linear-gradient(90deg,#1877F2,#4267B2)}}
.comm-icon{{font-size:2.2rem;margin-bottom:16px}}
.comm-card h3{{font-size:1.05rem;font-weight:700;margin-bottom:10px}}
.comm-card p{{color:var(--muted);font-size:.83rem;line-height:1.6;margin-bottom:20px}}
.comm-link{{
  display:inline-block;padding:9px 20px;border-radius:8px;
  font-size:.82rem;font-weight:700;font-family:var(--mono);
}}
.comm-card.tg .comm-link{{background:rgba(42,171,238,.15);color:#2AABEE;border:1px solid rgba(42,171,238,.3)}}
.comm-card.wa .comm-link{{background:rgba(37,211,102,.15);color:#25D366;border:1px solid rgba(37,211,102,.3)}}
.comm-card.fb .comm-link{{background:rgba(24,119,242,.15);color:#1877F2;border:1px solid rgba(24,119,242,.3)}}

/* ── TOC ────────────────────────────────────── */
.toc-section{{padding:60px 40px;max-width:800px;margin:0 auto}}
.toc-section h2{{font-size:1.1rem;color:var(--muted);text-transform:uppercase;
  letter-spacing:.1em;font-family:var(--mono);margin-bottom:24px}}
.toc-row{{
  display:flex;justify-content:space-between;align-items:center;
  padding:11px 16px;border-bottom:1px solid var(--border);
  font-size:.88rem;
}}
.toc-row:hover{{background:var(--s1)}}
.toc-num{{font-family:var(--mono);color:var(--accent);font-size:.82rem}}

/* ── SECTOR SECTIONS ────────────────────────── */
.sector-section{{padding:50px 40px}}
.sector-head{{
  display:flex;align-items:center;gap:14px;
  margin-bottom:28px;
  padding-bottom:16px;border-bottom:1px solid var(--border);
}}
.sec-ico{{font-size:1.6rem}}
.sector-head h2{{font-size:1.25rem;font-weight:700;flex:1}}
.sec-count{{
  background:var(--s2);color:var(--accent);
  padding:5px 14px;border-radius:20px;
  font-size:.75rem;font-family:var(--mono);
}}

/* ── CARDS ──────────────────────────────────── */
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}}
.card{{
  background:var(--s0);border:1px solid var(--border);
  border-radius:var(--r);padding:16px;
  display:flex;flex-direction:column;gap:12px;
}}
.card:hover{{border-color:var(--dim)}}
.card-head{{display:flex;align-items:flex-start;gap:10px}}
.card-ico{{font-size:1.3rem;line-height:1}}
.card-meta{{flex:1;display:flex;flex-direction:column;gap:4px}}
.card-city{{font-size:.78rem;color:var(--muted)}}
.pos-badge{{
  display:inline-block;width:fit-content;
  background:rgba(34,197,94,.1);color:var(--green);
  padding:2px 8px;border-radius:10px;
  font-size:.72rem;font-family:var(--mono);
}}
.card-jobs{{flex:1;display:flex;flex-direction:column;gap:3px}}
.job-row{{font-size:.8rem;color:var(--text);padding:3px 0;
  border-bottom:1px solid var(--border);display:flex;align-items:baseline;gap:6px}}
.job-row:last-child{{border-bottom:none}}
.job-dot{{color:var(--accent);font-size:.65rem;flex-shrink:0}}
.cnt{{
  margin-left:auto;flex-shrink:0;
  background:var(--s2);color:var(--muted);
  padding:1px 6px;border-radius:8px;
  font-size:.68rem;font-family:var(--mono);
}}
.apply-btn{{
  display:block;text-align:center;
  background:linear-gradient(135deg,var(--accent),#d97706);
  color:#000;font-weight:700;font-size:.8rem;
  padding:9px 16px;border-radius:8px;
  letter-spacing:.03em;
}}

/* ── FOOTER ─────────────────────────────────── */
.footer{{
  padding:50px 40px;text-align:center;
  border-top:1px solid var(--border);
  color:var(--muted);font-size:.8rem;
}}
.footer a{{color:var(--accent)}}

/* ── PRINT ──────────────────────────────────── */
.page-break{{page-break-before:always}}
@media print{{
  *{{print-color-adjust:exact;-webkit-print-color-adjust:exact}}
  body{{background:var(--bg);background-image:none}}
  .apply-btn{{background:var(--accent)!important}}
}}
</style>
</head>
<body>

<!-- COVER -->
<div class="cover">
  <div class="cover-eyebrow">Romania · {date.today().strftime('%Y')}</div>
  <h1>{TITLE}</h1>
  <p class="sub">{SUBTITLE}</p>
  <div class="stats">
    <div class="stat"><div class="n">{total_co:,}</div><div class="l">Active Employers</div></div>
    <div class="stat"><div class="n">{total_pos:,}</div><div class="l">Open Positions</div></div>
    <div class="stat"><div class="n">{len(sectors)}</div><div class="l">Sectors</div></div>
  </div>
  <a href="{APPLY_URL}" class="cover-cta">Apply Now →</a>
  <p class="cover-note">Source: public labor market data · {date.today().strftime('%d %B %Y')}</p>
</div>

<!-- COMMUNITY HUB -->
<div class="community page-break">
  <h2>Join the Community</h2>
  <p class="comm-sub">Connect with thousands of workers, expats and professionals in Romania</p>
  <div class="comm-grid">

    <div class="comm-card tg">
      <div class="comm-icon">✈️</div>
      <h3>Jobs in Romania — Telegram</h3>
      <p>Daily job alerts from across Romania. New vacancies posted every day across all sectors and cities.</p>
      <a href="{TELEGRAM}" class="comm-link">t.me/jobsinro →</a>
    </div>

    <div class="comm-card wa">
      <div class="comm-icon">💬</div>
      <h3>English Jobs in Romania</h3>
      <p>WhatsApp group for English-speaking job seekers in Romania. Share leads, ask questions, find opportunities.</p>
      <a href="{WA_GROUP}" class="comm-link">Join WhatsApp Group →</a>
    </div>

    <div class="comm-card fb">
      <div class="comm-icon">🌍</div>
      <h3>Expats in Romania</h3>
      <p>The community for English-speaking expats, repats &amp; locals — Americans, Brits, French, Germans, Dutch, Aussies, Kiwis and more. Socializing · Business · Networking · Events. A great way to meet people, collaborate and build a social life in Romania.</p>
      <a href="{FB_GROUP}" class="comm-link">Facebook Group →</a>
    </div>

  </div>
</div>

<!-- TOC -->
<div class="toc-section page-break">
  <h2>Sectors</h2>
  {toc}
</div>

<!-- SECTOR BLOCKS -->
{blocks}

<!-- FOOTER -->
<div class="footer">
  <p><a href="{APPLY_URL}">interjob.ro/apply.html</a> &nbsp;·&nbsp;
     <a href="{TELEGRAM}">t.me/jobsinro</a> &nbsp;·&nbsp;
     <a href="{WA_GROUP}">English Jobs in Romania (WhatsApp)</a> &nbsp;·&nbsp;
     <a href="{FB_GROUP}">Expats in Romania (Facebook)</a>
  </p>
  <p style="margin-top:10px">All employer details anonymised · Public labor market data · {date.today().strftime('%B %Y')}</p>
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
