"""Step 39: Template router - maps standard_sector + country to best template file.
Extends step30. Outputs routing table and validates template files exist.
"""
import os
import psycopg2
import csv

DB = dict(host='127.0.0.1', port=5433, dbname='interjob_master', user='tudor', password='tudor')

# sector -> country -> template path
ROUTING = {
    'construction': {
        'NO': 'D:/MEMORY/EMAIL/CAMPAIGNS/norway_virgil.txt',
        'RO': 'D:/MEMORY/HARGHITA/templates/harghita_phase1_construction.txt',
        'DEFAULT': 'D:/MEMORY/EMAIL/CAMPAIGNS/isc_constructii.txt',
    },
    'manufacturing': {
        'RO': 'D:/MEMORY/HARGHITA/templates/manufacturing.txt',
        'DEFAULT': 'D:/MEMORY/EMAIL/CAMPAIGNS/factoryjobs_en.txt',
    },
    'hospitality': {
        'RO': 'D:/MEMORY/HARGHITA/templates/hospitality.txt',
        'DEFAULT': 'D:/MEMORY/EMAIL/CAMPAIGNS/horecaworkers_en.txt',
    },
    'transport': {
        'RO': 'D:/MEMORY/DELIVERY/tudor_template1.txt',
        'DEFAULT': 'D:/MEMORY/EMAIL/CAMPAIGNS/transport_en.txt',
    },
    'healthcare': {
        'DEFAULT': 'D:/MEMORY/EMAIL/CAMPAIGNS/careworkers_en.txt',
    },
    'it': {
        'DEFAULT': 'D:/MEMORY/EMAIL/CAMPAIGNS/it_sector_en.txt',
    },
    'agriculture': {
        'DEFAULT': 'D:/MEMORY/EMAIL/CAMPAIGNS/farmworkers_en.txt',
    },
    'DEFAULT': {
        'DEFAULT': 'D:/MEMORY/EMAIL/CAMPAIGNS/generic_en.txt',
    }
}

def get_template(sector, country):
    sector = (sector or 'DEFAULT').lower()
    country = (country or '').upper()
    bucket = ROUTING.get(sector, ROUTING['DEFAULT'])
    return bucket.get(country, bucket.get('DEFAULT', ROUTING['DEFAULT']['DEFAULT']))

def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("""
        SELECT standard_sector, country, COUNT(*) AS n
        FROM companies_clean
        WHERE (email IS NOT NULL AND email != '' OR enriched_email IS NOT NULL AND enriched_email != '')
          AND (is_insolvent IS NULL OR is_insolvent = false)
          AND (is_agency IS NULL OR is_agency = false)
        GROUP BY standard_sector, country
        ORDER BY n DESC
        LIMIT 50
    """)
    rows = cur.fetchall()

    print(f"{'Sector':<20} {'Country':<8} {'Count':>8}  Template")
    print('-' * 80)
    missing = set()
    for sector, country, n in rows:
        tpl = get_template(sector, country)
        exists = os.path.exists(tpl.replace('D:/', '/d/'))
        flag = '  OK' if exists else '  MISSING'
        if not exists:
            missing.add(tpl)
        print(f"{str(sector):<20} {str(country):<8} {n:>8}  {tpl}{flag}")

    if missing:
        print(f"\nMissing templates ({len(missing)}):")
        for t in missing:
            print(f"  {t}")

    # Export routing CSV for campaign_builder_v2
    out = '/d/MEMORY/EMAIL PERSONAL/CODE/template_routing.csv'
    with open(out, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['standard_sector', 'country', 'template_path'])
        for sector, countries in ROUTING.items():
            for country, path in countries.items():
                w.writerow([sector, country, path])
    print(f"\nRouting table -> {out}")
    cur.close()
    conn.close()

main()
