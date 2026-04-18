#!/usr/bin/env python3
"""Generate general (all-sector) catalogs for each ANOFM sender domain."""
import sys, random
sys.path.insert(0, '/opt/ACTIVE/WORKFORCE')

from generate_all_catalogs import (
    load_real_cvs, build_workers, generate_html, generate_pdf_html, OUT_DIR
)
from pathlib import Path

ALL_SECTORS = ["Constructii","Productie","Alimentar","Logistica",
               "Healthcare","Hospitality","Agricultura","General"]

GENERAL_SITES = [
    {"domain": "factoryjobs.eu",      "name": "FactoryJobs.eu",      "email": "office@factoryjobs.eu",      "catalog_email": "catalog@factoryjobs.eu"},
    {"domain": "electricjobs.eu",     "name": "ElectricJobs.eu",     "email": "office@electricjobs.eu",     "catalog_email": "catalog@electricjobs.eu"},
    {"domain": "careworkers.eu",      "name": "CareWorkers.eu",      "email": "office@careworkers.eu",      "catalog_email": "catalog@careworkers.eu"},
    {"domain": "expatsinromania.org", "name": "ExpatsInRomania.org", "email": "office@expatsinromania.org", "catalog_email": "catalog@expatsinromania.org"},
    {"domain": "horecaworkers2026.eu","name": "HorecaWorkers2026.eu","email": "office@horecaworkers2026.eu","catalog_email": "catalog@horecaworkers2026.eu"},
    {"domain": "nepalezi.com",        "name": "Nepalezi.com",        "email": "office@nepalezi.com",        "catalog_email": "catalog@nepalezi.com"},
    {"domain": "bppltd.co.uk",        "name": "WarehouseWorkers.eu", "email": "office@bppltd.co.uk",        "catalog_email": "catalog@bppltd.co.uk"},
]

Path(OUT_DIR).mkdir(exist_ok=True)
print("Loading CVs...")
real_cvs = load_real_cvs()

for site in GENERAL_SITES:
    domain = site['domain']
    site['sectors'] = ALL_SECTORS
    workers = build_workers(ALL_SECTORS, real_cvs)
    total = sum(len(v) for v in workers.values())

    html_web  = generate_html(site, workers)
    html_path = f"{OUT_DIR}/{domain}_catalog_general.html"
    pdf_path  = f"{OUT_DIR}/{domain}_catalog_general.pdf"
    pdf_html_path = f"{OUT_DIR}/{domain}_catalog_general_for_pdf.html"

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html_web)

    with open(pdf_html_path, 'w', encoding='utf-8') as f:
        f.write(generate_pdf_html(site, workers))

    print(f"HTML: {html_path} ({total} workers)")

    try:
        from weasyprint import HTML as WH
        WH(filename=pdf_html_path).write_pdf(pdf_path)
        import os; os.remove(pdf_html_path)
        print(f"PDF:  {pdf_path}")
    except Exception as e:
        print(f"PDF FAIL {domain}: {e}")

print("Done.")
