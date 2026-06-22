#!/usr/bin/env python3
"""Content Creator Agent — generates bilingual RO + EN articles with translations."""

import json
import sys
import time
from datetime import datetime

try:
    from deep_translator import GoogleTranslator
except ImportError:
    GoogleTranslator = None

RO_MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie",
             "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]

SECTOR_LABELS_RO = {
    "constructii": "Construcții", "it": "IT & Tehnologie", "vanzari": "Vânzări & Retail",
    "productie": "Producție & Industrie", "horeca": "HoReCa", "transport": "Transport & Logistică",
    "logistica": "Logistică & Depozitare", "sanatate": "Sănătate & Medicină",
    "agricultura": "Agricultură", "altul": "Alte domenii",
}
SECTOR_LABELS_EN = {
    "constructii": "Construction", "it": "IT & Technology", "vanzari": "Sales & Retail",
    "productie": "Production & Manufacturing", "horeca": "HoReCa & Hospitality",
    "transport": "Transport & Logistics", "logistica": "Warehousing & Logistics",
    "sanatate": "Healthcare & Medicine", "agricultura": "Agriculture", "altul": "Other fields",
}

def translate_batch(titles, src="auto", tgt="ro"):
    """Batch translate titles via GoogleTranslator."""
    if not titles or not GoogleTranslator:
        return titles

    try:
        tr = GoogleTranslator(source=src, target=tgt)
        joined = "\n".join(t[:120] for t in titles)
        translated = tr.translate(joined[:4900]) or joined
        parts = translated.split("\n")
        while len(parts) < len(titles):
            parts.append(titles[len(parts)])
        return [p.strip() or titles[i] for i, p in enumerate(parts[:len(titles)])]
    except Exception as e:
        print(f"[WARN] Translation failed: {e}", file=sys.stderr)
        return titles

def newsletter_block(lang="ro"):
    """Newsletter CTA block."""
    if lang == "ro":
        return '''<div style="background:#f0f7ff;border:2px solid #0073aa;border-radius:8px;padding:20px;margin:30px 0;text-align:center">
  <h3 style="margin-top:0;color:#0073aa">📩 Primești zilnic ofertele noi pe email</h3>
  <p style="margin:8px 0">Abonează-te la newsletter-ul InterJob.ro și fii primul care află cele mai bune locuri de muncă din România și Europa.</p>
  <a href="https://interjob.ro/apply.html" style="background:#0073aa;color:white;padding:10px 22px;text-decoration:none;border-radius:4px;display:inline-block;margin-top:8px">Abonează-te gratuit</a>
</div>'''
    else:
        return '''<div style="background:#f0f7ff;border:2px solid #0073aa;border-radius:8px;padding:20px;margin:30px 0;text-align:center">
  <h3 style="margin-top:0;color:#0073aa">📩 Get daily job alerts by email</h3>
  <p style="margin:8px 0">Subscribe to InterJob.ro newsletter and be the first to know about new job openings in Romania and Europe.</p>
  <a href="https://interjob.ro/apply.html" style="background:#0073aa;color:white;padding:10px 22px;text-decoration:none;border-radius:4px;display:inline-block;margin-top:8px">Subscribe for free</a>
</div>'''

def build_ro_article(data):
    """Generate RO article."""
    now = datetime.now()
    today_str = f"{now.day} {RO_MONTHS[now.month]} {now.year}"

    anofm_total = data["anofm_total"]
    eures_total = data["eures_total"]
    by_sector = data["anofm_by_sector"]
    count_sector = data["anofm_count_sector"]
    by_country = data["eures_by_country"]

    title = f"Piața muncii {today_str}: {anofm_total:,} locuri de muncă în România și Europa"
    slug = f"piata-muncii-{now.strftime('%Y-%m-%d')}"
    meta = f"Piața muncii {today_str}: {anofm_total:,} posturi active în România și {eures_total:,}+ în Europa. Construcții, IT, HoReCa, transport."[:155]
    focus_kw = f"locuri de munca {now.day} {RO_MONTHS[now.month]} {now.year}"

    top2 = [SECTOR_LABELS_RO.get(s, s.title())
            for s, _ in sorted(count_sector.items(), key=lambda x: x[1], reverse=True)[:2]]
    h2_jobs = f"Locuri de muncă {' și '.join(top2)} în România — {today_str}"
    h2_eu = f"Oferte de muncă în Europa — {today_str}"

    html = [
        f"<p>Azi, <strong>{today_str}</strong>, sunt disponibile <strong>{anofm_total:,} locuri de muncă active în România</strong> și <strong>{eures_total:,}+ oferte în Europa</strong>.</p>",
        newsletter_block("ro"),
        f"<hr><h2>{h2_jobs}</h2>",
    ]

    for sector, cnt in sorted(count_sector.items(), key=lambda x: x[1], reverse=True)[:7]:
        label = SECTOR_LABELS_RO.get(sector, sector.title())
        html.append(f"<h3>{label} — {cnt:,} posturi</h3><ul>")
        for job in by_sector.get(sector, [])[:4]:
            title_text = job.get("title", "N/A")
            city = job.get("city", "")
            html.append(f"<li>{title_text}{' — ' + city if city else ''}</li>")
        html.append("</ul>")

    html.append(f"<hr><h2>{h2_eu}</h2>")
    html.append(f"<p>Peste <strong>{eures_total:,} oferte</strong> în țările partenere.</p>")

    for country, jobs in by_country.items():
        html.append(f"<h3>{country}</h3><ul>")
        for title_text, city in jobs[:4]:
            html.append(f"<li>{title_text}{' — ' + city if city else ''}</li>")
        html.append("</ul>")

    html.append(newsletter_block("ro"))
    html.append(f'<p style="text-align:center"><a href="https://interjob.ro/apply.html" style="background:#e65c00;color:white;padding:14px 28px;text-decoration:none;border-radius:5px;font-size:1.1em;display:inline-block">Aplică acum</a></p>')
    html.append('<p style="font-size:0.8em;color:#999;text-align:center">Date actualizate zilnic. InterJob.ro</p>')

    return {
        "title": title,
        "slug": slug,
        "meta_description": meta,
        "focus_keyword": focus_kw,
        "category": "Piata Muncii",
        "content_html": "\n".join(html),
        "content_length": len("\n".join(html))
    }

def build_en_article(data):
    """Generate EN article."""
    now = datetime.now()
    today_en = now.strftime("%B %-d, %Y").replace("-", "").replace("  ", " ")

    anofm_total = data["anofm_total"]
    eures_total = data["eures_total"]
    by_sector = data["anofm_by_sector"]
    count_sector = data["anofm_count_sector"]
    by_country = data["eures_by_country"]

    title = f"Job Market {today_en}: {anofm_total:,} Jobs in Romania + Europe Openings"
    slug = f"job-market-{now.strftime('%Y-%m-%d')}"
    meta = f"Romania job market {today_en}: {anofm_total:,} open positions + {eures_total:,} in Europe. Construction, IT, HoReCa, transport."[:155]
    focus_kw = f"jobs Romania Europe {today_en}"

    top2 = [SECTOR_LABELS_EN.get(s, s.title())
            for s, _ in sorted(count_sector.items(), key=lambda x: x[1], reverse=True)[:2]]
    h2_jobs = f"{' & '.join(top2)} Jobs in Romania — {today_en}"
    h2_eu = f"European Job Openings — {today_en}"

    html = [
        f"<p>Today, <strong>{today_en}</strong>, the job market shows <strong>{anofm_total:,} active positions in Romania</strong> and <strong>{eures_total:,}+ openings across Europe</strong>.</p>",
        newsletter_block("en"),
        f"<hr><h2>{h2_jobs}</h2>",
    ]

    for sector, cnt in sorted(count_sector.items(), key=lambda x: x[1], reverse=True)[:7]:
        label = SECTOR_LABELS_EN.get(sector, sector.title())
        html.append(f"<h3>{label} — {cnt:,} positions</h3><ul>")
        for job in by_sector.get(sector, [])[:4]:
            title_text = job.get("title", "N/A")
            city = job.get("city", "")
            html.append(f"<li>{title_text}{' — ' + city + ', Romania' if city else ' — Romania'}</li>")
        html.append("</ul>")

    html.append(f"<hr><h2>{h2_eu}</h2>")
    html.append(f"<p>Over <strong>{eures_total:,} openings</strong> in partner countries.</p>")

    for country, jobs in by_country.items():
        html.append(f"<h3>{country}</h3><ul>")
        for title_text, city in jobs[:4]:
            html.append(f"<li>{title_text}{' — ' + city if city else ''}</li>")
        html.append("</ul>")

    html.append(newsletter_block("en"))
    html.append(f'<p style="text-align:center"><a href="https://interjob.ro/apply.html" style="background:#0073aa;color:white;padding:14px 28px;text-decoration:none;border-radius:5px;font-size:1.1em;display:inline-block">Apply Now</a></p>')
    html.append('<p style="font-size:0.8em;color:#999;text-align:center">Updated daily. InterJob.ro — European Workforce Solutions.</p>')

    return {
        "title": title,
        "slug": slug,
        "meta_description": meta,
        "focus_keyword": focus_kw,
        "category": "Job Market",
        "content_html": "\n".join(html),
        "content_length": len("\n".join(html))
    }

def main():
    data = json.loads(sys.stdin.read())

    output = {
        "status": "generated",
        "articles": {
            "ro": build_ro_article(data),
            "en": build_en_article(data)
        },
        "translations_made": 0,
        "warnings": [],
        "generation_timestamp": datetime.now().isoformat()
    }

    print(json.dumps(output))

if __name__ == "__main__":
    main()
