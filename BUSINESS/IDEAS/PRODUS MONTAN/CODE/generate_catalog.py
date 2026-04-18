#!/usr/bin/env python3
"""Generate static HTML catalog from produs_montan PostgreSQL tables."""
import os
import sys
import html
import psycopg2
from collections import defaultdict

# --
DB = dict(host="192.168.100.21", port=5432, dbname="interjob_master",
          user="tudor", password="tudor")
OUT = os.path.join(os.path.dirname(__file__), "catalog")
WHATSAPP = "https://wa.me/33751171356?text=Bonjour%2C%20je%20souhaite%20commander%20des%20produits%20montagne"
EMAIL_CONTACT = "cumparlegume@agroevolution.com"
PHONE = "+33 7 51 17 13 56"

# AGRIP sectors (Annex I TFEU aligned)
SECTOR_DISPLAY = {
    "DAIRY": ("Lactate si Oua", "🧀", "dairy"),
    "HONEY": ("Miere si Apicole", "🍯", "honey"),
    "FRESH_FV": ("Fructe si Legume Proaspete", "🥬", "fresh-fv"),
    "PROCESSED_FV": ("Conserve si Sucuri", "🫙", "processed-fv"),
    "MEAT": ("Carne si Mezeluri", "🥩", "meat"),
    "FISH": ("Peste si Pastrav", "🐟", "fish"),
    "CEREALS": ("Cereale si Faina", "🌾", "cereals"),
    "BAKERY": ("Panificatie", "🍞", "bakery"),
    "HERBS": ("Plante si Ceaiuri", "🌿", "herbs"),
}
PROC_BADGE = {
    "FRESH": ("Proaspat", "#4caf50"),
    "MATURED": ("Maturat", "#ff9800"),
    "PROCESSED": ("Procesat", "#2196f3"),
    "NON_PERISHABLE": ("Neperisabil", "#9c27b0"),
}
COUNTY_NORM = {
    "Vâlcea": "VALCEA", "VÂLCEA": "VALCEA",
    "BISTRIȚA NĂSĂUD": "BISTRITA NASAUD",
    "BISTRIȚA-NĂSĂUD": "BISTRITA NASAUD",
    "MARAMUREȘ": "MARAMURES", "BRAȘOV": "BRASOV",
    "BACĂU": "BACAU", "NEAMȚ": "NEAMT",
    "CARAȘ-SEVERIN": "CARAS-SEVERIN",
}


def norm_county(c):
    if not c:
        return "NECUNOSCUT"
    return COUNTY_NORM.get(c, c.upper())


def slug(s):
    return s.lower().replace(" ", "-").replace(",", "")


def e(s):
    return html.escape(str(s)) if s else ""


def fetch_data():
    conn_str = f"host={DB['host']} port={DB['port']} dbname={DB['dbname']} user={DB['user']} password={DB['password']}"
    conn = psycopg2.connect(conn_str)
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name, p.county, p.addr_sediu, p.email, p.phone,
               p.website_url, p.year_registered, p.obs,
               array_agg(DISTINCT pr.product_name) FILTER(WHERE pr.product_name IS NOT NULL),
               array_agg(DISTINCT pr.agrip_sector) FILTER(WHERE pr.agrip_sector IS NOT NULL),
               array_agg(DISTINCT pr.processing) FILTER(WHERE pr.processing IS NOT NULL)
        FROM produs_montan_producers p
        LEFT JOIN produs_montan_products pr ON pr.producer_id = p.id
        GROUP BY p.id ORDER BY p.name
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


CSS = """
body{font-family:system-ui,sans-serif;margin:0;background:#f8f9fa;color:#333}
.top{background:#2d5016;color:#fff;padding:20px 30px}
.top h1{margin:0;font-size:1.8em}.top p{margin:5px 0 0;opacity:.85}
.nav{background:#3a6b1e;padding:10px 30px;display:flex;flex-wrap:wrap;gap:8px}
.nav a{color:#fff;text-decoration:none;padding:6px 14px;border-radius:20px;font-size:.9em;background:rgba(255,255,255,.15)}
.nav a:hover,.nav a.active{background:rgba(255,255,255,.3)}
.container{max-width:1200px;margin:20px auto;padding:0 20px}
.stats{display:flex;gap:15px;flex-wrap:wrap;margin:20px 0}
.stat{background:#fff;padding:15px 20px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.1);text-align:center}
.stat .n{font-size:1.8em;font-weight:700;color:#2d5016}.stat .l{font-size:.85em;color:#666}
.search{width:100%;padding:12px 18px;border:2px solid #ddd;border-radius:8px;font-size:1em;margin:15px 0;box-sizing:border-box}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:15px}
.card{background:#fff;border-radius:8px;padding:18px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.card h3{margin:0 0 8px;font-size:1.05em;color:#2d5016}
.card .county{color:#666;font-size:.85em;margin-bottom:8px}
.card .badge{display:inline-block;background:#e8f5e9;color:#2d5016;padding:2px 8px;border-radius:10px;font-size:.75em;margin:2px}
.btn{display:inline-block;background:#25d366;color:#fff;padding:8px 16px;border-radius:6px;text-decoration:none;font-size:.9em;margin-top:10px}
.btn:hover{background:#1da851}
.footer{text-align:center;padding:30px;color:#999;font-size:.85em}
.products-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(120px,1fr));gap:8px;margin:12px 0}
.product-item{text-align:center;padding:8px;background:#f9f9f9;border-radius:6px;transition:all 0.2s}
.product-item:hover{background:#f0f0f0;transform:scale(1.02)}
.product-img{width:80px;height:80px;object-fit:cover;border-radius:4px;margin-bottom:4px;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.product-name{font-size:.75em;color:#555;word-wrap:break-word;line-height:1.2}
.more-products{display:flex;align-items:center;justify-content:center;height:80px;color:#999;font-size:.85em;font-weight:600}
.card-footer{display:flex;justify-content:space-between;align-items:center;margin-top:12px;padding-top:12px;border-top:1px solid #eee;color:#666;font-size:.85em}
.product-count{font-weight:600;color:#2d5016}
@media(max-width:600px){.grid{grid-template-columns:1fr}.stats{flex-direction:column}.products-grid{grid-template-columns:repeat(auto-fill,minmax(100px,1fr))}}
@media(max-width:400px){.product-img{width:60px;height:60px}}
"""

JS_SEARCH = """
function filterCards(){var q=document.getElementById('q').value.toLowerCase();
document.querySelectorAll('.card').forEach(function(c){
c.style.display=c.textContent.toLowerCase().includes(q)?'':'none';})}
"""


def write_page(path, title, nav_active, body_html, counties=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    nav_items = [("index.html", "🏠 Acasa")]
    for key, (disp, icon, sl) in SECTOR_DISPLAY.items():
        nav_items.append((f"{sl}.html", f"{icon} {disp}"))
    nav_items.append(("judete.html", "📍 Judete"))
    nav_html = ""
    for href, label in nav_items:
        cls = ' class="active"' if href == nav_active else ""
        nav_html += f'<a href="{href}"{cls}>{label}</a>\n'
    county_filter = ""
    if counties:
        opts = "".join(f'<option value="{e(c)}">{e(c)}</option>' for c in sorted(counties))
        county_filter = f'''<select onchange="filterByCounty(this.value)" style="padding:8px;border-radius:6px;border:1px solid #ddd;margin:10px 0">
<option value="">Toate judetele</option>{opts}</select>
<script>function filterByCounty(v){{document.querySelectorAll('.card').forEach(function(c){{
c.style.display=(!v||c.dataset.county===v)?'':'none'}})}}</script>'''
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"""<!DOCTYPE html><html lang="ro"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} - Catalog Produs Montan</title>
<meta name="description" content="Catalog complet producatori certificati Produs Montan din Romania. {e(title)}">
<style>{CSS}</style></head><body>
<div class="top"><h1>🏔️ Catalog Produs Montan Romania</h1>
<p>Producatori certificati RNPM &bull; Agregator: Gospodarii de Altadata Cooperativa</p></div>
<div class="nav">{nav_html}</div>
<div class="container">
<input type="text" id="q" class="search" placeholder="Cauta producator, produs, judet..." oninput="filterCards()">
{county_filter}{body_html}</div>
<div class="footer">Catalog generat din Registrul National al Produselor Montane (RNPM)<br>
Agregator: Gospodarii de Altadata Cooperativa Agricola (CUI 51957925)</div>
<script>{JS_SEARCH}</script></body></html>""")


def producer_card(row):
    pid, name, county, addr, email, phone, url, year, obs, products, sectors, procs = row
    county_n = norm_county(county)
    badges = ""
    if sectors:
        for s in sorted(set(sectors)):
            info = SECTOR_DISPLAY.get(s)
            if info:
                badges += f'<span class="badge">{info[1]} {e(info[0])}</span> '
    if procs:
        for p in sorted(set(procs)):
            info = PROC_BADGE.get(p)
            if info:
                badges += f'<span class="badge" style="background:{info[1]}20;color:{info[1]}">{e(info[0])}</span> '
    
    # Build products list with images
    prod_html = ""
    unique_products = []
    if products:
        unique_products = sorted(set(products))
        prod_html = '<div class="products-grid">'
        for i, product in enumerate(unique_products[:12]):  # Show max 12 products
            # Generate image URL based on product name (placeholder style)
            img_name = slug(product)
            prod_html += f'''
            <div class="product-item">
                <img src="products/{img_name}.jpg" alt="{e(product)}" class="product-img" 
                     onerror="this.src='data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iODAiIGhlaWdodD0iODAiIHZpZXdCb3g9IjAgMCA4MCA4MCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHJlY3Qgd2lkdGg9IjgwIiBoZWlnaHQ9IjgwIiBmaWxsPSIjRjhGOUZBIi8+CjxwYXRoIGQ9Ik00MCAyMEM0OCAyMCA1NSAyNyA1NSAzNUM1NSA0MyA0OCA1MCA0MCA1MEMzMiA1MCAyNSA0MyAyNSAzNUMyNSAyNyAzMiAyMCA0MCAyMFoiIGZpbGw9IiMyRDUwMTYiLz4KPHBhdGggZD0iTTQwIDMwQzQ0IDMwIDQ3IDMzIDQ3IDM3QzQ3IDQxIDQ0IDQ0IDQwIDQ0QzM2IDQ0IDMzIDQxIDMzIDM3QzMzIDMzIDM2IDMwIDQwIDMwWiIgZmlsbD0id2hpdGUiLz4KPC9zdmc+'" />
                <div class="product-name">{e(product)}</div>
            </div>'''
            if i == 11 and len(unique_products) > 12:
                prod_html += f'<div class="product-item more-products">+{len(unique_products)-12} mai multe</div>'
        prod_html += '</div>'
    
    return f"""<div class="card" data-county="{e(county_n)}">
<h3>{e(name)}</h3>
<div class="county">📍 {e(county_n)}</div>
<div>{badges}</div>
{prod_html}
<div class="card-footer">
    <span class="product-count">{len(unique_products)} produse</span>
</div></div>"""


def main():
    print("Fetching data from PostgreSQL...")
    rows = fetch_data()
    print(f"  {len(rows)} producers loaded")

    # Build sector index
    by_sector = defaultdict(list)
    by_county = defaultdict(list)
    all_counties = set()
    for row in rows:
        sectors = row[10] or []
        county_n = norm_county(row[2])
        all_counties.add(county_n)
        by_county[county_n].append(row)
        for s in sectors:
            by_sector[s].append(row)

    os.makedirs(OUT, exist_ok=True)

    # Index page
    sec_cards = ""
    for key, (disp, icon, sl) in SECTOR_DISPLAY.items():
        n = len(set(r[0] for r in by_sector.get(key, [])))
        sec_cards += f'<div class="stat"><div class="n">{icon} {n}</div><div class="l"><a href="{sl}.html">{e(disp)}</a></div></div>\n'
    stats = f"""<div class="stats">
<div class="stat"><div class="n">{len(rows)}</div><div class="l">Producatori</div></div>
<div class="stat"><div class="n">{sum(len(r[9] or []) for r in rows)}</div><div class="l">Produse</div></div>
<div class="stat"><div class="n">{len(all_counties)}</div><div class="l">Judete</div></div>
{sec_cards}</div>"""
    cards = "\n".join(producer_card(r) for r in rows)
    write_page(f"{OUT}/index.html", "Toti Producatorii",
               "index.html", stats + f'<div class="grid">{cards}</div>',
               counties=all_counties)

    # Sector pages
    for key, (disp, icon, sl) in SECTOR_DISPLAY.items():
        sec_rows = by_sector.get(key, [])
        seen = set()
        unique = []
        for r in sec_rows:
            if r[0] not in seen:
                seen.add(r[0])
                unique.append(r)
        cards = "\n".join(producer_card(r) for r in unique)
        counties = set(norm_county(r[2]) for r in unique)
        header = f'<h2>{icon} {e(disp)} ({len(unique)} producatori)</h2>'
        write_page(f"{OUT}/{sl}.html", disp, f"{sl}.html",
                   header + f'<div class="grid">{cards}</div>', counties=counties)

    # County page
    county_html = '<h2>📍 Producatori pe Judete</h2><div class="grid">'
    for county in sorted(all_counties):
        n = len(by_county[county])
        county_html += f'<div class="card"><h3>📍 {e(county)}</h3><div class="county">{n} producatori</div></div>\n'
    county_html += "</div>"
    write_page(f"{OUT}/judete.html", "Judete", "judete.html", county_html)

    print(f"Catalog generated in {OUT}/")
    print(f"  index.html + {len(SECTOR_DISPLAY)} sector pages + judete.html")
    print(f"  Total: {len(rows)} producers, {len(all_counties)} counties")


if __name__ == "__main__":
    main()
