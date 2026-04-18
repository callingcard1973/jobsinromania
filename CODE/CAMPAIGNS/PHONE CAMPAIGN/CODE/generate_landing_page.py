#!/usr/bin/env python3
"""
Generate landing page: interjob.ro/jobs/
Lists all sector PDFs for download + community hub.
"""
import sys, io, json, os
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

MANIFEST    = r"D:\MEMORY\PHONE CAMPAIGN\CATALOGS\TUDOR\SECTORS\manifest.json"
OUTPUT_PATH = r"D:\MEMORY\PHONE CAMPAIGN\CATALOGS\TUDOR\index.html"
APPLY_URL   = "https://interjob.ro/apply.html"
TELEGRAM    = "https://t.me/jobsinro"
WA_GROUP    = "https://chat.whatsapp.com/DvnchNG3vYBLnLuqY3DW9K"
FB_GROUP    = "https://www.facebook.com/groups/expatsinromania"
PDF_BASE    = "https://expatsinromania.org/jobs/SECTORS/"  # PDFs hosted on expats site
ACCENT      = "#f59e0b"
GREEN       = "#22c55e"
BLUE        = "#3b82f6"
PURPLE      = "#a855f7"

with open(MANIFEST, encoding="utf-8") as f:
    sectors = json.load(f)

# Sort by employer count
sectors.sort(key=lambda x: -x["count"])

total_employers = sum(s["count"] for s in sectors)
total_positions = sum(s["positions"] for s in sectors)

sector_cards = ""
for s in sectors:
    sector_cards += f'''<a href="{PDF_BASE}{s["slug"]}.pdf" class="sector-card" download>
  <div class="sc-top">
    <span class="sc-icon">{s["icon"]}</span>
    <span class="sc-count">{s["count"]} employers</span>
  </div>
  <div class="sc-name">{s["name"]}</div>
  <div class="sc-pos">{s["positions"]:,} open positions</div>
  <div class="sc-dl">⬇ Download PDF</div>
</a>'''

HTML = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Jobs in Romania — Download Sector Catalogs</title>
<meta name="description" content="Browse and download job catalogs by sector for Romania. {total_employers:,} employers, {total_positions:,} open positions. Apply now at interjob.ro">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;500;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#07070e;--s0:#0c0c18;--s1:#131320;--s2:#1c1c2e;
  --border:#22223a;--text:#eaeaf0;--muted:#6b6b8a;
  --accent:{ACCENT};--green:{GREEN};--blue:{BLUE};--purple:{PURPLE};
  --font:'DM Sans',sans-serif;--mono:'Space Mono',monospace;
}}
html,body{{background:var(--bg);color:var(--text);font-family:var(--font);
  font-size:15px;line-height:1.6;min-height:100vh}}
a{{color:var(--accent);text-decoration:none}}

/* HERO */
.hero{{
  padding:100px 40px 80px;text-align:center;
  background:radial-gradient(ellipse 90% 70% at 50% 0%,rgba(245,158,11,.08) 0%,transparent 65%);
  border-bottom:1px solid var(--border);
}}
.hero-badge{{
  display:inline-block;background:rgba(245,158,11,.12);
  border:1px solid rgba(245,158,11,.25);color:var(--accent);
  padding:6px 18px;border-radius:20px;font-size:12px;
  letter-spacing:.12em;text-transform:uppercase;
  font-family:var(--mono);margin-bottom:24px;
}}
.hero h1{{
  font-size:clamp(2rem,5vw,3.6rem);font-weight:700;
  letter-spacing:-.03em;line-height:1.1;margin-bottom:16px;
  background:linear-gradient(135deg,#fff 30%,{ACCENT});
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
}}
.hero p{{color:var(--muted);font-size:1rem;max-width:560px;margin:0 auto 40px}}
.hero-stats{{
  display:flex;gap:20px;flex-wrap:wrap;justify-content:center;margin-bottom:40px;
}}
.hs{{
  background:var(--s1);border:1px solid var(--border);
  border-radius:12px;padding:20px 32px;text-align:center;min-width:140px;
}}
.hs .n{{font-size:2rem;font-weight:700;color:var(--accent);font-family:var(--mono)}}
.hs .l{{font-size:.72rem;color:var(--muted);text-transform:uppercase;letter-spacing:.08em;margin-top:4px}}
.hero-cta{{
  display:inline-block;
  background:linear-gradient(135deg,{ACCENT},#d97706);
  color:#000;font-weight:700;padding:15px 40px;
  border-radius:12px;font-size:1rem;letter-spacing:.02em;
  box-shadow:0 0 40px rgba(245,158,11,.2);
}}

/* COMMUNITY */
.community{{padding:80px 40px;border-bottom:1px solid var(--border)}}
.community h2{{text-align:center;font-size:1.5rem;font-weight:700;margin-bottom:8px}}
.community .sub{{text-align:center;color:var(--muted);margin-bottom:48px;font-size:.9rem}}
.comm-grid{{
  display:grid;
  grid-template-columns:repeat(auto-fit,minmax(270px,1fr));
  gap:20px;max-width:960px;margin:0 auto;
}}
.cc{{
  background:var(--s1);border:1px solid var(--border);
  border-radius:14px;padding:28px;position:relative;overflow:hidden;
}}
.cc::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:14px 14px 0 0}}
.cc.tg::before{{background:linear-gradient(90deg,#2AABEE,#229ED9)}}
.cc.wa::before{{background:linear-gradient(90deg,#25D366,#128C7E)}}
.cc.fb::before{{background:linear-gradient(90deg,#1877F2,#4267B2)}}
.cc-ico{{font-size:2rem;margin-bottom:14px}}
.cc h3{{font-size:1rem;font-weight:700;margin-bottom:8px}}
.cc p{{color:var(--muted);font-size:.82rem;line-height:1.6;margin-bottom:18px}}
.cc-btn{{
  display:inline-block;padding:9px 18px;border-radius:8px;
  font-size:.8rem;font-weight:700;font-family:var(--mono);
}}
.cc.tg .cc-btn{{background:rgba(42,171,238,.15);color:#2AABEE;border:1px solid rgba(42,171,238,.3)}}
.cc.wa .cc-btn{{background:rgba(37,211,102,.15);color:#25D366;border:1px solid rgba(37,211,102,.3)}}
.cc.fb .cc-btn{{background:rgba(24,119,242,.15);color:#1877F2;border:1px solid rgba(24,119,242,.3)}}

/* SECTORS */
.sectors{{padding:80px 40px}}
.sectors-head{{text-align:center;margin-bottom:48px}}
.sectors-head h2{{font-size:1.5rem;font-weight:700;margin-bottom:8px}}
.sectors-head p{{color:var(--muted);font-size:.9rem}}
.sectors-grid{{
  display:grid;
  grid-template-columns:repeat(auto-fill,minmax(220px,1fr));
  gap:14px;max-width:1200px;margin:0 auto;
}}
.sector-card{{
  background:var(--s1);border:1px solid var(--border);
  border-radius:12px;padding:20px;
  display:flex;flex-direction:column;gap:6px;
  transition:border-color .2s,transform .15s;
  cursor:pointer;
}}
.sector-card:hover{{border-color:var(--accent);transform:translateY(-2px)}}
.sc-top{{display:flex;align-items:center;justify-content:space-between}}
.sc-icon{{font-size:1.5rem}}
.sc-count{{font-family:var(--mono);font-size:.72rem;color:var(--muted);
  background:var(--s2);padding:3px 8px;border-radius:10px}}
.sc-name{{font-size:.95rem;font-weight:700;color:var(--text);line-height:1.3}}
.sc-pos{{font-size:.76rem;color:var(--muted)}}
.sc-dl{{
  margin-top:8px;
  display:inline-block;
  background:rgba(245,158,11,.1);color:var(--accent);
  border:1px solid rgba(245,158,11,.2);
  padding:6px 12px;border-radius:7px;
  font-size:.75rem;font-family:var(--mono);
  text-align:center;
}}
.sector-card:hover .sc-dl{{background:rgba(245,158,11,.2)}}

/* FOOTER */
.footer{{
  padding:60px 40px;text-align:center;
  border-top:1px solid var(--border);color:var(--muted);font-size:.82rem;
}}
.footer-links{{display:flex;gap:24px;justify-content:center;flex-wrap:wrap;margin-bottom:16px}}
.footer-links a{{color:var(--muted)}}
.footer-links a:hover{{color:var(--accent)}}
</style>
</head>
<body>

<!-- HERO -->
<div class="hero">
  <div class="hero-badge">Romania · {date.today().strftime("%Y")}</div>
  <h1>Jobs in Romania</h1>
  <p>Browse and download job catalogs by sector. Updated monthly from official labor market data.</p>
  <div class="hero-stats">
    <div class="hs"><div class="n">{total_employers:,}</div><div class="l">Active Employers</div></div>
    <div class="hs"><div class="n">{total_positions:,}</div><div class="l">Open Positions</div></div>
    <div class="hs"><div class="n">{len(sectors)}</div><div class="l">Sectors</div></div>
  </div>
  <a href="{APPLY_URL}" class="hero-cta">Apply Now →</a>
</div>

<!-- COMMUNITY HUB -->
<div class="community">
  <h2>Join the Community</h2>
  <p class="sub">Connect with thousands of workers, expats and professionals across Romania</p>
  <div class="comm-grid">
    <div class="cc tg">
      <div class="cc-ico">✈️</div>
      <h3>Jobs in Romania — Telegram</h3>
      <p>Daily job alerts from across Romania. New vacancies posted every day across all sectors and cities.</p>
      <a href="{TELEGRAM}" class="cc-btn">t.me/jobsinro →</a>
    </div>
    <div class="cc wa">
      <div class="cc-ico">💬</div>
      <h3>English Jobs in Romania</h3>
      <p>WhatsApp group for English-speaking job seekers. Share leads, ask questions, find opportunities.</p>
      <a href="{WA_GROUP}" class="cc-btn">Join WhatsApp Group →</a>
    </div>
    <div class="cc fb">
      <div class="cc-ico">🌍</div>
      <h3>Expats in Romania</h3>
      <p>Community for English-speaking expats, repats &amp; locals — Americans, Brits, French, Germans, Dutch, Aussies, Kiwis and more. Socializing · Business · Networking · Events.</p>
      <a href="{FB_GROUP}" class="cc-btn">Facebook Group →</a>
    </div>
  </div>
</div>

<!-- SECTOR DOWNLOAD GRID -->
<div class="sectors">
  <div class="sectors-head">
    <h2>Download by Sector</h2>
    <p>Click any sector to download its PDF catalog</p>
  </div>
  <div class="sectors-grid">
    {sector_cards}
  </div>
</div>

<!-- FOOTER -->
<div class="footer">
  <div class="footer-links">
    <a href="{APPLY_URL}">Apply Now</a>
    <a href="{TELEGRAM}">t.me/jobsinro</a>
    <a href="{WA_GROUP}">English Jobs (WhatsApp)</a>
    <a href="{FB_GROUP}">Expats in Romania</a>
  </div>
  <p>Public labor market data · {date.today().strftime("%B %Y")} · <a href="{APPLY_URL}">interjob.ro/apply.html</a></p>
</div>

</body>
</html>'''

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write(HTML)

size_kb = os.path.getsize(OUTPUT_PATH) // 1024
print(f"Generated: {OUTPUT_PATH} ({size_kb}KB)")
print(f"Sectors: {len(sectors)} | Employers: {total_employers:,} | Positions: {total_positions:,}")
print(f"\nDeploy to: interjob.ro/jobs/index.html")
print(f"Also deploy: SECTORS/*.pdf → interjob.ro/jobs/SECTORS/")
