#!/usr/bin/env python3
"""Generate HTML catalog of employer requests from orders.csv."""
import sys, io, csv, urllib.parse
from pathlib import Path
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# CONFIG
TITLE = "Employer Requests - Worker Placement"
SUBTITLE = "Active Demands & Partners"
CONTACT_NAME = "Tudor"
CONTACT_PHONE = "40722789938"
INPUT_PATH = Path(__file__).parent / "orders.csv"
OUTPUT_PATH = Path(__file__).parent / "orders_catalog.html"

TIPO_ICONS = {"Constructii":"🔨","Transport":"🚛","HoReCa":"🍽","Curatenie":"🧹",
    "Agricultura":"🌾","Tamplari":"🪵","Fleet":"🛴","Sudori":"⚡","Manpower":"👷",
    "Tehnician":"🔧","Operatori":"🚜","Incarcator":"📦","Facility":"🏢"}

def icon_for(pos):
    for k,v in TIPO_ICONS.items():
        if k.lower() in (pos or "").lower(): return v
    return "🏭"

def load_orders():
    rows = []
    with open(INPUT_PATH, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f): rows.append(r)
    return rows

def wa_link(company, positions):
    msg = f"Buna ziua {CONTACT_NAME}, sunt interesat de cererea pentru {positions} ({company})."
    return f"https://wa.me/{CONTACT_PHONE}?text={urllib.parse.quote(msg)}"

def make_card(r):
    clf = r.get("Clasificare","")
    co = r.get("Denumire companie","") or "—"
    contact = r.get("Nume persoană de contact","")
    tel = r.get("Telefon","")
    email = r.get("Email","")
    loc = r.get("Localitate","")
    nr = r.get("Număr persoane","")
    pos = r.get("Tip poziții","") or r.get("Observații","")[:50]
    obs = r.get("Observații","")
    ic = icon_for(pos)
    badge_color = {"COMANDA":"#22c55e","INTERESAT":"#f59e0b","PARTENER":"#3b82f6"}.get(clf,"#6b7280")
    wa = wa_link(co, pos)
    nr_html = f'<div class="nr">{nr} persoane</div>' if nr else ""
    tel_html = f'<div class="det">📞 {tel}</div>' if tel else ""
    email_html = f'<div class="det">✉ {email}</div>' if email else ""
    loc_html = f'<div class="det">📍 {loc}</div>' if loc else ""
    return f'''<div class="card">
<div class="card-head"><span class="ic">{ic}</span><h3>{co}</h3>
<span class="badge" style="background:{badge_color}">{clf}</span></div>
{f'<div class="det">👤 {contact}</div>' if contact else ''}
{loc_html}{tel_html}{email_html}
<div class="pos">🔧 {pos}</div>{nr_html}
<div class="obs">{obs}</div>
<a href="{wa}" class="apply" target="_blank">📱 Contact via WhatsApp</a>
</div>'''

def generate():
    orders = load_orders()
    grouped = defaultdict(list)
    for r in orders: grouped[r.get("Clasificare","OTHER")].append(r)
    stats = {k:len(v) for k,v in grouped.items()}
    total = len(orders)
    cards_html = ""
    for clf in ["COMANDA","INTERESAT","PARTENER"]:
        if clf not in grouped: continue
        cards_html += f'<div class="section"><h2>{clf} ({len(grouped[clf])})</h2><div class="grid">'
        for r in grouped[clf]: cards_html += make_card(r)
        cards_html += '</div></div>'
    html = f'''<!DOCTYPE html><html><head><meta charset="utf-8">
<title>{TITLE}</title>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#08080d;--sf:#0f0f17;--sr:#1a1a28;--bd:#1e1e30;--tx:#e8e8ec;--tm:#7e7e96;--ac:#f59e0b;--gn:#22c55e}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{background:var(--bg);color:var(--tx);font-family:'DM Sans',sans-serif;padding:2rem}}
h1{{font-size:2rem;margin-bottom:.5rem}}h2{{color:var(--ac);margin:2rem 0 1rem;font-size:1.4rem}}
.sub{{color:var(--tm);margin-bottom:2rem}}
.stats{{display:flex;gap:1.5rem;margin-bottom:2rem;flex-wrap:wrap}}
.stat{{background:var(--sf);border:1px solid var(--bd);border-radius:12px;padding:1rem 1.5rem;min-width:120px}}
.stat-n{{font-size:1.8rem;font-weight:700}}.stat-l{{color:var(--tm);font-size:.85rem}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:1.2rem}}
.card{{background:var(--sf);border:1px solid var(--bd);border-radius:12px;padding:1.2rem;transition:border-color .2s}}
.card:hover{{border-color:var(--ac)}}
.card-head{{display:flex;align-items:center;gap:.6rem;margin-bottom:.8rem}}
.card-head h3{{flex:1;font-size:1rem}}.ic{{font-size:1.4rem}}
.badge{{padding:2px 8px;border-radius:6px;font-size:.7rem;font-weight:700;color:#fff}}
.det,.pos,.obs,.nr{{font-size:.85rem;color:var(--tm);margin:4px 0}}
.pos{{color:var(--tx)}}.nr{{color:var(--gn);font-weight:700;font-size:1rem}}
.obs{{font-size:.8rem;color:var(--tm);font-style:italic;margin-top:6px}}
.apply{{display:inline-block;margin-top:.8rem;padding:8px 16px;background:var(--gn);color:#fff;
text-decoration:none;border-radius:8px;font-weight:600;font-size:.85rem}}
.apply:hover{{opacity:.85}}
.section{{margin-bottom:2rem}}
@media print{{body{{-webkit-print-color-adjust:exact;print-color-adjust:exact}}}}
</style></head><body>
<h1>{TITLE}</h1><div class="sub">{SUBTITLE} — {total} cereri active</div>
<div class="stats">
<div class="stat"><div class="stat-n" style="color:var(--gn)">{stats.get("COMANDA",0)}</div><div class="stat-l">COMENZI</div></div>
<div class="stat"><div class="stat-n" style="color:var(--ac)">{stats.get("INTERESAT",0)}</div><div class="stat-l">INTERESATI</div></div>
<div class="stat"><div class="stat-n" style="color:#3b82f6">{stats.get("PARTENER",0)}</div><div class="stat-l">PARTENERI</div></div>
</div>
{cards_html}
<div style="margin-top:3rem;padding:1.5rem;background:var(--sr);border-radius:12px;text-align:center">
<div style="font-size:1.2rem;margin-bottom:.5rem">📱 Contact: <strong>{CONTACT_NAME}</strong></div>
<a href="https://wa.me/{CONTACT_PHONE}" style="color:var(--gn);font-size:1.1rem">WhatsApp: +{CONTACT_PHONE}</a>
</div></body></html>'''
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    print(f"Catalog generated: {OUTPUT_PATH} ({total} orders)")

if __name__ == "__main__":
    generate()
