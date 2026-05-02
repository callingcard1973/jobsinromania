"""
Generate Anonymous Employer Catalog — English, Romania only
No branding, no contact data (no emails, no phones, no websites)
Contact: Yohan +40 723 068 733 (WhatsApp)
Apply Now button → WhatsApp link
"""
import json
import sys
import io
from collections import Counter, defaultdict
from datetime import datetime
import html as html_mod

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# ═══════════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════════
print("Loading employers...")
with open(r'D:\MEMORY\A2_SITE_DEPLOYER\FACTORYJOBS\DATA\factory_employers_unified.json', encoding='utf-8') as f:
    data = json.load(f)

employers = data['employers']
print(f"  {len(employers)} employers loaded")

# ═══════════════════════════════════════════════════════════════════
# SECTOR ICONS
# ═══════════════════════════════════════════════════════════════════
SECTOR_ICONS = {
    'Warehouse & logistics': '📦',
    'Transport & delivery': '🚛',
    'Factory & production': '🏭',
    'Freight transport by road': '🚚',
    'Building construction': '🏗️',
    'Construction': '🔨',
    'Construction development': '🏘️',
    'Bread & bakery': '🍞',
    'Food processing': '🥩',
    'Auto repair & mechanics': '🔧',
    'Electrical installation': '⚡',
    'Metal structures & frameworks': '⚙️',
    'Plumbing & HVAC': '🔩',
    'Wood & furniture': '🪵',
    'Textile & garments': '🧵',
    'Agriculture & farming': '🌾',
    'Cleaning & maintenance': '🧹',
    'Packaging': '📦',
    'Plastics & rubber': '🧪',
    'Recycling & waste': '♻️',
    'Glass & ceramics': '🏺',
    'Paper & printing': '📄',
    'Mining & quarrying': '⛏️',
    'Steel & metalwork': '🔩',
    'Concrete & cement': '🧱',
    'Painting & decorating': '🎨',
    'Welding': '🔥',
    'Scaffolding': '🪜',
}

def sector_icon(sector):
    for key, icon in SECTOR_ICONS.items():
        if key.lower() in sector.lower():
            return icon
    return '🏭'

# ═══════════════════════════════════════════════════════════════════
# COUNTY NAME MAPPING (Romanian counties)
# ═══════════════════════════════════════════════════════════════════
COUNTY_DISPLAY = {
    'Bucuresti': 'Bucharest',
    'Ilfov': 'Ilfov (Bucharest area)',
    'Cluj': 'Cluj',
    'Timis': 'Timișoara',
    'Constanta': 'Constanța',
    'Bihor': 'Bihor (Oradea)',
    'Brasov': 'Brașov',
    'Sibiu': 'Sibiu',
    'Arges': 'Argeș',
    'Dolj': 'Dolj (Craiova)',
    'Galati': 'Galați',
    'Mures': 'Mureș',
    'Prahova': 'Prahova (Ploiești)',
    'Suceava': 'Suceava',
    'Bacau': 'Bacău',
    'Hunedoara': 'Hunedoara',
    'Neamt': 'Neamț',
    'Maramures': 'Maramureș',
    'Alba': 'Alba Iulia',
    'Arad': 'Arad',
    'Valcea': 'Vâlcea',
    'Gorj': 'Gorj',
    'Olt': 'Olt',
    'Dambovita': 'Dâmbovița',
    'Buzau': 'Buzău',
    'Teleorman': 'Teleorman',
    'Botosani': 'Botoșani',
    'Satu Mare': 'Satu Mare',
    'Vaslui': 'Vaslui',
    'Vrancea': 'Vrancea',
    'Ialomita': 'Ialomița',
    'Calarasi': 'Călărași',
    'Giurgiu': 'Giurgiu',
    'Mehedinti': 'Mehedinți',
    'Tulcea': 'Tulcea',
    'Braila': 'Brăila',
    'Salaj': 'Sălaj',
    'Bistrita-Nasaud': 'Bistrița-Năsăud',
    'Covasna': 'Covasna',
    'Harghita': 'Harghita',
    'Caras-Severin': 'Caraș-Severin',
    'Iasi': 'Iași',
}

def fmt_county(county):
    if not county:
        return 'Romania'
    return COUNTY_DISPLAY.get(county, county)

def fmt_salary(salary_str):
    if not salary_str:
        return None
    s = salary_str.strip()
    if not s:
        return None
    # Parse "4050.00-None RON none" or "4582.00-7000.00 RON gross"
    parts = s.split()
    if len(parts) >= 1:
        range_part = parts[0]
        currency = parts[1] if len(parts) > 1 else 'RON'
        gross_net = parts[2] if len(parts) > 2 else ''
        nums = range_part.split('-')
        try:
            low = int(float(nums[0]))
        except:
            return None
        high = None
        if len(nums) > 1 and nums[1] != 'None':
            try:
                high = int(float(nums[1]))
            except:
                pass

        if high and high > low:
            result = f'{low:,}–{high:,} RON'
        else:
            result = f'{low:,} RON'

        if 'gross' in gross_net.lower():
            result += ' gross'
        elif 'net' in gross_net.lower():
            result += ' net'

        # Add EUR estimate
        eur_low = int(low / 5)  # rough RON to EUR
        if high:
            eur_high = int(high / 5)
            result += f' (≈€{eur_low:,}–€{eur_high:,})'
        else:
            result += f' (≈€{eur_low:,})'

        return result
    return None

def clean_desc(desc):
    if not desc:
        return ''
    d = desc.strip()
    # Truncate very long descriptions
    if len(d) > 400:
        d = d[:397] + '...'
    return html_mod.escape(d)

def clean_jobs(job_titles):
    if not job_titles:
        return 'General Worker'
    return html_mod.escape(job_titles)

# ═══════════════════════════════════════════════════════════════════
# ORGANIZE BY SECTOR
# ═══════════════════════════════════════════════════════════════════
by_sector = defaultdict(list)
for e in employers:
    sector = e.get('sector', 'Other')
    if not sector:
        sector = 'Other'
    by_sector[sector].append(e)

# Sort sectors by count
sector_order = sorted(by_sector.keys(), key=lambda s: -len(by_sector[s]))

# Stats
total = len(employers)
total_positions = sum(int(e.get('positions', 0) or 0) for e in employers)
with_salary = sum(1 for e in employers if e.get('salary'))
counties = Counter(e.get('county', '') for e in employers)
now = datetime.now().strftime('%B %Y')

print(f"  Sectors: {len(sector_order)}")
print(f"  Total positions: {total_positions:,}")
print(f"  With salary: {with_salary}")
print(f"  Counties: {len(counties)}")

# ═══════════════════════════════════════════════════════════════════
# GENERATE HTML
# ═══════════════════════════════════════════════════════════════════

def make_employer_card(e, idx):
    company = html_mod.escape(e.get('company', ''))
    county = fmt_county(e.get('county', ''))
    sector = html_mod.escape(e.get('sector', ''))
    icon = sector_icon(sector)
    jobs = clean_jobs(e.get('job_titles', ''))
    positions = e.get('positions', '')
    salary = fmt_salary(e.get('salary', ''))
    desc = clean_desc(e.get('job_description', ''))
    address = html_mod.escape(e.get('address', '') or '')

    pos_html = f'<span class="card-positions">{positions} positions</span>' if positions and int(positions or 0) > 0 else ''
    salary_html = f'<div class="card-salary">💰 {salary}</div>' if salary else ''
    addr_html = f'<div class="card-addr">📍 {address}, {county}</div>' if address and address != '. .' else f'<div class="card-addr">📍 {county}</div>'

    # WhatsApp deep link with pre-filled message
    wa_msg = f"Hi Yohan, I'm interested in the {jobs.replace('<','').replace('>','')} position at {company} ({county}). I'd like to apply."
    import urllib.parse as _up
    wa_url = f"https://wa.me/40723068733?text={_up.quote(wa_msg)}"

    return f'''<div class="emp-card">
<div class="card-header">
<div class="card-icon">{icon}</div>
<div class="card-title">
<h4>{company}</h4>
<div class="card-sector">{sector}</div>
</div>
{pos_html}
</div>
<div class="card-jobs">🔧 {jobs}</div>
{salary_html}
{addr_html}
<div class="card-desc">{desc}</div>
<a href="{wa_url}" target="_blank" class="card-apply"><svg viewBox="0 0 24 24"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492a.5.5 0 00.611.611l4.458-1.495A11.952 11.952 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-2.387 0-4.594-.822-6.34-2.199l-.446-.369-3.89 1.304 1.304-3.89-.369-.446A9.935 9.935 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z"/></svg>Apply Now</a>
</div>'''

# Build sector sections
sector_sections = ''
for sector in sector_order:
    emps = by_sector[sector]
    icon = sector_icon(sector)
    # Sort by positions descending
    emps.sort(key=lambda e: -(int(e.get('positions', 0) or 0)))
    cards = '\n'.join(make_employer_card(e, i) for i, e in enumerate(emps))
    total_pos = sum(int(e.get('positions', 0) or 0) for e in emps)
    pos_str = f' — {total_pos:,} positions' if total_pos > 0 else ''
    sector_sections += f'''
<div class="page-break"></div>
<div class="sector-block">
<div class="sector-header">
<span class="sector-icon-big">{icon}</span>
<div>
<h3>{html_mod.escape(sector)}</h3>
<span class="sector-count">{len(emps)} employers{pos_str}</span>
</div>
</div>
<div class="emp-grid">
{cards}
</div>
</div>
'''

# Top counties for stats
top_counties = counties.most_common(10)

# TOC entries
toc_items = ''
for i, sector in enumerate(sector_order):
    toc_items += f'<div class="toc-item"><span>{sector_icon(sector)} {html_mod.escape(sector)}</span><span>{len(by_sector[sector])} employers</span></div>\n'

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Factory &amp; Manufacturing Jobs in Romania — Employer Catalog {now}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
:root{{
  --bg:#08080d;--surface:#0f0f17;--surface-raised:#1a1a28;--border:#1e1e30;
  --text:#e8e8ec;--text-muted:#7e7e96;--text-dim:#4a4a62;
  --accent:#f59e0b;--accent-hot:#fbbf24;--accent-glow:rgba(245,158,11,0.12);
  --green:#22c55e;--blue:#3b82f6;
  --radius:8px;--radius-lg:12px;
  --font:'DM Sans',-apple-system,sans-serif;--mono:'Space Mono',monospace;
}}
html{{scroll-behavior:smooth}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.6;min-height:100vh}}
body::before{{content:'';position:fixed;inset:0;background:url("data:image/svg+xml,%3Csvg viewBox='0 0 512 512' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.03'/%3E%3C/svg%3E");pointer-events:none;z-index:9999}}
body::after{{content:'';position:fixed;inset:0;background-image:linear-gradient(rgba(59,130,246,0.02) 1px,transparent 1px),linear-gradient(90deg,rgba(59,130,246,0.02) 1px,transparent 1px);background-size:60px 60px;pointer-events:none;z-index:0}}
body>*{{position:relative;z-index:1}}

@media print{{
  body{{background:#08080d !important;-webkit-print-color-adjust:exact;print-color-adjust:exact}}
  body::before,body::after{{display:none}}
  .page-break{{page-break-before:always}}
}}
@page{{size:A4;margin:12mm}}

/* COVER */
.cover{{min-height:100vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;padding:4rem 2rem;position:relative;overflow:hidden}}
.cover::before{{content:'';position:absolute;width:800px;height:800px;top:-200px;left:50%;margin-left:-400px;background:radial-gradient(circle,rgba(245,158,11,0.08) 0%,transparent 70%);pointer-events:none}}
.cover::after{{content:'';position:absolute;top:0;left:0;right:0;height:4px;background:repeating-linear-gradient(90deg,var(--accent) 0px,var(--accent) 20px,transparent 20px,transparent 30px)}}
.cover-logo{{font-family:var(--mono);font-size:1.8rem;font-weight:700;color:var(--accent);margin-bottom:0.5rem;letter-spacing:-1px}}
.cover-logo span{{color:var(--text-dim);font-weight:400}}
.cover h1{{font-size:clamp(2.2rem,5vw,3.2rem);font-weight:800;letter-spacing:-2px;line-height:1.15;margin:1rem 0}}
.cover h1 em{{font-style:normal;color:var(--accent);position:relative}}
.cover h1 em::after{{content:'';position:absolute;bottom:2px;left:0;right:0;height:3px;background:var(--accent);opacity:0.3;border-radius:2px}}
.cover-sub{{color:var(--text-muted);font-size:1rem;max-width:600px;margin:0.5rem auto 2rem;line-height:1.7}}
.cover-stats{{display:flex;gap:3rem;flex-wrap:wrap;justify-content:center;margin:2rem 0}}
.cover-stat{{text-align:center}}
.cover-stat-num{{font-family:var(--mono);font-size:2.2rem;font-weight:700;color:var(--accent);line-height:1.2}}
.cover-stat-label{{font-size:0.7rem;color:var(--text-dim);text-transform:uppercase;letter-spacing:2px;font-weight:600}}
.cover-date{{font-family:var(--mono);font-size:0.8rem;color:var(--text-dim);margin-top:2rem;padding:8px 20px;border:1px solid var(--border);border-radius:4px;letter-spacing:1px}}
.cover-contact{{margin-top:1.5rem;padding:12px 24px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);font-size:0.9rem}}
.cover-contact strong{{color:var(--accent)}}

/* SECTIONS */
.section{{padding:2rem 2rem;max-width:1200px;margin:0 auto}}
.section-divider{{display:flex;align-items:center;gap:1rem;margin-bottom:1.5rem}}
.section-divider::before{{content:'';flex:0 0 40px;height:2px;background:var(--accent)}}
.section-divider::after{{content:'';flex:1;height:1px;background:linear-gradient(90deg,var(--border) 0%,transparent 100%)}}
.section-divider h2{{font-family:var(--mono);font-size:0.8rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:3px;white-space:nowrap}}

/* TOC */
.toc{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:1.5rem 2rem;max-width:700px;margin:0 auto 2rem}}
.toc h3{{font-family:var(--mono);font-size:0.78rem;color:var(--accent);text-transform:uppercase;letter-spacing:2px;margin-bottom:1rem}}
.toc-item{{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:0.82rem}}
.toc-item:last-child{{border-bottom:none}}
.toc-item span:first-child{{color:var(--text)}}
.toc-item span:last-child{{color:var(--text-dim);font-family:var(--mono);font-size:0.72rem}}

/* SECTOR BLOCKS */
.sector-block{{max-width:1200px;margin:0 auto 2rem;padding:0 2rem}}
.sector-header{{display:flex;align-items:center;gap:1rem;margin-bottom:1.2rem;padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);border-left:3px solid var(--accent)}}
.sector-icon-big{{font-size:1.8rem}}
.sector-header h3{{font-size:1rem;font-weight:700;letter-spacing:-0.3px}}
.sector-count{{font-size:0.75rem;color:var(--text-muted)}}

/* EMPLOYER CARDS */
.emp-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:10px}}
.emp-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:1rem 1.2rem;transition:border-color 0.2s;position:relative;overflow:hidden}}
.emp-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,transparent,var(--accent),transparent);opacity:0;transition:opacity 0.2s}}
.emp-card:hover{{border-color:rgba(245,158,11,0.3)}}
.emp-card:hover::before{{opacity:1}}
.card-header{{display:flex;align-items:flex-start;gap:10px;margin-bottom:8px}}
.card-icon{{font-size:1.4rem;flex-shrink:0;margin-top:2px}}
.card-title{{flex:1;min-width:0}}
.card-title h4{{font-size:0.85rem;font-weight:700;letter-spacing:-0.3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.card-sector{{font-size:0.68rem;color:var(--text-dim)}}
.card-positions{{font-family:var(--mono);font-size:0.72rem;color:var(--green);font-weight:700;white-space:nowrap;padding:2px 8px;background:rgba(34,197,94,0.08);border-radius:3px;flex-shrink:0}}
.card-jobs{{font-size:0.78rem;color:var(--accent);font-weight:600;margin-bottom:6px;line-height:1.4}}
.card-salary{{font-size:0.78rem;color:var(--green);margin-bottom:4px;font-weight:500}}
.card-addr{{font-size:0.72rem;color:var(--text-muted);margin-bottom:6px}}
.card-desc{{font-size:0.72rem;color:var(--text-dim);line-height:1.55;border-top:1px solid var(--border);padding-top:6px;margin-top:4px}}
.card-apply{{display:inline-flex;align-items:center;gap:6px;margin-top:8px;padding:6px 16px;background:#25D366;color:#fff;text-decoration:none;border-radius:5px;font-size:0.75rem;font-weight:700;transition:transform 0.2s,box-shadow 0.2s}}
.card-apply:hover{{transform:translateY(-1px);box-shadow:0 4px 12px rgba(37,211,102,0.3)}}
.card-apply svg{{width:14px;height:14px;fill:currentColor}}

/* OVERVIEW TABLE */
.overview-table{{width:100%;border-collapse:collapse;font-size:0.82rem;margin:1rem 0}}
.overview-table th{{text-align:left;padding:8px 12px;background:var(--surface-raised);color:var(--text-dim);font-family:var(--mono);font-size:0.65rem;text-transform:uppercase;letter-spacing:1px;border-bottom:2px solid var(--accent)}}
.overview-table td{{padding:8px 12px;border-bottom:1px solid var(--border)}}
.overview-table .val{{font-family:var(--mono);color:var(--accent);font-weight:700}}

/* FOOTER */
.footer{{max-width:1200px;margin:3rem auto;padding:2rem;border-top:1px solid var(--border);text-align:center;position:relative}}
.footer::before{{content:'';position:absolute;top:-1px;left:2rem;width:60px;height:2px;background:var(--accent)}}
.footer p{{font-size:0.78rem;color:var(--text-dim);margin-bottom:0.4rem}}

/* COUNTIES */
.county-grid{{display:flex;flex-wrap:wrap;gap:8px;margin:1rem 0}}
.county-tag{{padding:6px 14px;background:var(--surface);border:1px solid var(--border);border-radius:20px;font-size:0.78rem;color:var(--text-muted)}}
.county-tag .county-num{{font-family:var(--mono);color:var(--accent);font-weight:700;margin-left:6px}}

@media(max-width:768px){{
  .emp-grid{{grid-template-columns:1fr}}
  .cover h1{{font-size:2rem}}
  .cover-stats{{gap:1.5rem}}
}}
</style>
</head>
<body>

<!-- COVER -->
<section class="cover">
<h1>Factory &amp; Manufacturing<br><em>Jobs</em> in Romania</h1>
<p class="cover-sub">Complete catalog of {total:,} verified employers across Romania offering factory, production, warehouse, construction, and industrial positions. All information sourced from public data. Jobs include descriptions, locations, and salary information where available.</p>
<div class="cover-stats">
<div class="cover-stat"><div class="cover-stat-num">{total:,}</div><div class="cover-stat-label">Employers</div></div>
<div class="cover-stat"><div class="cover-stat-num">{total_positions:,}</div><div class="cover-stat-label">Open Positions</div></div>
<div class="cover-stat"><div class="cover-stat-num">{len(sector_order)}</div><div class="cover-stat-label">Industry Sectors</div></div>
<div class="cover-stat"><div class="cover-stat-num">{len(counties)}</div><div class="cover-stat-label">Counties</div></div>
</div>
<div class="cover-date">CATALOG EDITION — {now.upper()}</div>
<a href="https://wa.me/40723068733?text=Hi%20Yohan%2C%20I%27m%20interested%20in%20factory%20jobs%20in%20Romania." target="_blank" style="display:inline-flex;align-items:center;gap:10px;margin-top:1.5rem;padding:16px 36px;background:#25D366;color:#fff;text-decoration:none;border-radius:8px;font-size:1.1rem;font-weight:700;transition:transform 0.2s,box-shadow 0.2s"><svg width="22" height="22" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492a.5.5 0 00.611.611l4.458-1.495A11.952 11.952 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-2.387 0-4.594-.822-6.34-2.199l-.446-.369-3.89 1.304 1.304-3.89-.369-.446A9.935 9.935 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z"/></svg>Apply Now — WhatsApp</a>
<div class="cover-contact" style="margin-top:1rem">Contact: <strong>Yohan</strong> — <strong>+40 723 068 733</strong></div>
</section>

<!-- TOC -->
<section class="section page-break">
<div class="section-divider"><h2>Table of Contents</h2></div>
<div class="toc">
<h3>Sectors ({len(sector_order)})</h3>
{toc_items}
</div>
</section>

<!-- OVERVIEW -->
<section class="section page-break">
<div class="section-divider"><h2>Overview — Romania Factory Jobs Market</h2></div>
<p style="color:var(--text-muted);font-size:0.88rem;max-width:800px;margin-bottom:1.5rem;line-height:1.7">This catalog contains {total:,} Romanian employers actively hiring for factory, manufacturing, warehouse, construction, and industrial positions. All information compiled from public data. All positions are in Romania with legal employment contracts.</p>

<table class="overview-table">
<thead><tr><th>Metric</th><th>Value</th></tr></thead>
<tbody>
<tr><td>Total Employers</td><td class="val">{total:,}</td></tr>
<tr><td>Total Open Positions</td><td class="val">{total_positions:,}</td></tr>
<tr><td>Industry Sectors</td><td class="val">{len(sector_order)}</td></tr>
<tr><td>Counties Covered</td><td class="val">{len(counties)}</td></tr>
<tr><td>Employers with Salary Data</td><td class="val">{with_salary:,}</td></tr>
<tr><td>Data Sources</td><td>Public data</td></tr>
</tbody>
</table>

<h3 style="font-family:var(--mono);font-size:0.75rem;color:var(--accent);text-transform:uppercase;letter-spacing:2px;margin:1.5rem 0 0.8rem">Top Hiring Regions</h3>
<div class="county-grid">
'''

for county, cnt in top_counties:
    display = fmt_county(county) if county else 'Not specified'
    html += f'<span class="county-tag">{html_mod.escape(display)}<span class="county-num">{cnt}</span></span>\n'

html += f'''</div>
</section>

<!-- EMPLOYER LISTINGS BY SECTOR -->
{sector_sections}

<!-- FOOTER -->
<footer class="footer page-break">
<p style="font-size:1rem;color:var(--text);margin-bottom:1rem"><strong>Factory &amp; Manufacturing Jobs in Romania</strong></p>
<a href="https://wa.me/40723068733?text=Hi%20Yohan%2C%20I%27d%20like%20to%20apply%20for%20a%20factory%20job." target="_blank" style="display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:#25D366;color:#fff;text-decoration:none;border-radius:6px;font-size:0.95rem;font-weight:700;margin-bottom:1rem"><svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347z"/><path d="M12 0C5.373 0 0 5.373 0 12c0 2.625.846 5.059 2.284 7.034L.789 23.492a.5.5 0 00.611.611l4.458-1.495A11.952 11.952 0 0012 24c6.627 0 12-5.373 12-12S18.627 0 12 0zm0 22c-2.387 0-4.594-.822-6.34-2.199l-.446-.369-3.89 1.304 1.304-3.89-.369-.446A9.935 9.935 0 012 12C2 6.486 6.486 2 12 2s10 4.486 10 10-4.486 10-10 10z"/></svg>Apply Now — WhatsApp Yohan</a>
<p style="font-size:0.95rem;color:var(--accent);margin-bottom:0.8rem">Contact: <strong>Yohan</strong> — +40 723 068 733</p>
<p>{total:,} employers | {total_positions:,} positions | {len(sector_order)} sectors | {len(counties)} counties</p>
<p>All data sourced from public records | Generated {datetime.now().strftime('%d %B %Y')}</p>
</footer>

</body>
</html>'''

output_path = r'D:\MEMORY\A2_SITE_DEPLOYER\FACTORYJOBS\OUTPUT\employer_catalog.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)

size_kb = len(html.encode('utf-8')) / 1024
print(f"\nCatalog written to: {output_path}")
print(f"Size: {size_kb:.0f} KB")
print(f"Employers: {total:,}")
print(f"Positions: {total_positions:,}")
print(f"Sectors: {len(sector_order)}")
