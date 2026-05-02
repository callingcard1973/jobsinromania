#!/usr/bin/env python3
"""Cross-reference 26K Bundesagentur agencies with OffeneRegister 5.3M companies.
Uses rapidfuzz for fuzzy name matching + officer lookup via company_number.
Output: /opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/bundesagentur_with_officers.csv"""

import csv
import sqlite3
import re
import sys
from collections import defaultdict
from rapidfuzz import fuzz, process

BA_FILE = '/opt/ACTIVE/OPENDATA/DATA/AGENCIES/agencies_germany_ba_20260213.csv'
OR_DB = '/opt/ACTIVE/OPENDATA/DATA/OFFENEREGISTER/openregister.db'
OUTPUT = '/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED/bundesagentur_with_officers.csv'
MATCH_THRESHOLD = 82  # Fuzzy match score threshold

def normalize(name):
    """Normalize company name for matching."""
    if not name:
        return ''
    n = name.lower().strip()
    n = n.replace('"', '').replace("'", '')
    # Remove legal form suffixes
    for suffix in [' gmbh & co. kg', ' gmbh & co.kg', ' gmbh&co.kg', ' gmbh & co kg',
                   ' ug (haftungsbeschränkt)', ' ug (haftungsbeschraenkt)',
                   ' (haftungsbeschränkt)', ' gmbh', ' ug', ' ag', ' kg', ' ohg',
                   ' e.k.', ' e.k', ' gbr', ' mbh', ' sia', ' s.r.o.', ' b.v.',
                   ' ltd', ' limited', ' inc']:
        n = n.replace(suffix, '')
    # Remove punctuation except spaces
    n = re.sub(r'[^\w\s]', ' ', n)
    n = re.sub(r'\s+', ' ', n).strip()
    return n

def main():
    # Load Bundesagentur agencies
    print("Loading Bundesagentur agencies...")
    ba_rows = []
    ba_names = {}  # normalized -> [indices]
    with open(BA_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        ba_fields = list(reader.fieldnames)
        for i, row in enumerate(reader):
            ba_rows.append(row)
            norm = normalize(row.get('company_name', ''))
            if norm:
                if norm not in ba_names:
                    ba_names[norm] = []
                ba_names[norm].append(i)
    print(f"  {len(ba_rows)} agencies, {len(ba_names)} unique normalized names")

    # Connect to OffeneRegister
    print("Loading OffeneRegister companies (currently registered only)...")
    conn = sqlite3.connect(OR_DB)
    conn.row_factory = sqlite3.Row

    cur = conn.cursor()
    or_companies = {}  # normalized -> {company_number, name, address, city, status, federal_state}
    or_names_list = []  # For fuzzy matching
    count = 0

    cur.execute("""
        SELECT company_number, name, registered_address, registered_office,
               current_status, federal_state
        FROM company
        WHERE current_status = 'currently registered'
    """)
    for row in cur:
        norm = normalize(row['name'])
        if norm and len(norm) > 3:
            or_companies[norm] = {
                'company_number': row['company_number'],
                'or_name': row['name'],
                'or_address': row['registered_address'] or '',
                'or_city': row['registered_office'] or '',
                'or_status': row['current_status'] or '',
                'or_federal_state': row['federal_state'] or ''
            }
        count += 1
        if count % 500000 == 0:
            print(f"  Processed {count}...")
    print(f"  {count} total, {len(or_companies)} unique normalized (currently registered)")

    # Phase 1: Exact matching
    print("\nPhase 1: Exact name matching...")
    matched = {}  # ba_norm -> or_data
    exact_count = 0
    for ba_norm in ba_names:
        if ba_norm in or_companies:
            matched[ba_norm] = or_companies[ba_norm]
            exact_count += 1
    print(f"  Exact matches: {exact_count}/{len(ba_names)} ({exact_count*100/len(ba_names):.1f}%)")

    # Phase 2: Fuzzy matching for unmatched
    unmatched_ba = [n for n in ba_names if n not in matched]
    print(f"\nPhase 2: Fuzzy matching {len(unmatched_ba)} remaining names (threshold={MATCH_THRESHOLD})...")

    or_names_list = list(or_companies.keys())
    fuzzy_count = 0
    batch_size = 500

    for i in range(0, len(unmatched_ba), batch_size):
        batch = unmatched_ba[i:i+batch_size]
        for ba_norm in batch:
            # Use rapidfuzz extractOne for best match
            result = process.extractOne(
                ba_norm, or_names_list,
                scorer=fuzz.token_sort_ratio,
                score_cutoff=MATCH_THRESHOLD
            )
            if result:
                match_name, score, _ = result
                matched[ba_norm] = or_companies[match_name]
                matched[ba_norm]['match_score'] = score
                fuzzy_count += 1

        done = min(i + batch_size, len(unmatched_ba))
        if done % 2000 == 0 or done == len(unmatched_ba):
            print(f"  Processed {done}/{len(unmatched_ba)}, fuzzy matches so far: {fuzzy_count}")

    total_matched = exact_count + fuzzy_count
    print(f"\nTotal matched: {total_matched}/{len(ba_names)} ({total_matched*100/len(ba_names):.1f}%)")
    print(f"  Exact: {exact_count}, Fuzzy: {fuzzy_count}")

    # Phase 3: Load officers for matched companies
    print("\nPhase 3: Loading officers...")
    matched_numbers = [v['company_number'] for v in matched.values() if v.get('company_number')]
    print(f"  Looking up officers for {len(matched_numbers)} companies...")

    officers_by_company = defaultdict(list)
    for i in range(0, len(matched_numbers), 500):
        batch = matched_numbers[i:i+500]
        placeholders = ','.join(['?'] * len(batch))
        cur.execute(f"""
            SELECT company_id, name, position, firstname, lastname, city
            FROM officer
            WHERE company_id IN ({placeholders})
            AND (dismissed IS NULL OR dismissed = '' OR dismissed = '0')
            ORDER BY company_id,
                CASE
                    WHEN position LIKE '%Geschäftsführer%' THEN 1
                    WHEN position LIKE '%Inhaber%' THEN 2
                    WHEN position LIKE '%Vorstand%' THEN 3
                    WHEN position LIKE '%Prokurist%' THEN 4
                    ELSE 5
                END
        """, batch)
        for row in cur:
            cid = row[0]
            if len(officers_by_company[cid]) < 3:  # Max 3 officers per company
                officers_by_company[cid].append({
                    'name': row[1] or '',
                    'position': row[2] or '',
                    'firstname': row[3] or '',
                    'lastname': row[4] or '',
                    'city': row[5] or ''
                })

    companies_with_officers = len(officers_by_company)
    total_officers = sum(len(v) for v in officers_by_company.values())
    print(f"  Companies with officers: {companies_with_officers}")
    print(f"  Total officers found: {total_officers}")

    conn.close()

    # Build company_number -> officers lookup
    cn_to_officers = officers_by_company

    # Write output
    print(f"\nWriting output...")
    extra_fields = ['or_name', 'or_address', 'or_city', 'or_status', 'or_federal_state',
                    'match_score',
                    'officer_1_name', 'officer_1_position', 'officer_1_firstname', 'officer_1_lastname',
                    'officer_2_name', 'officer_2_position',
                    'officer_3_name', 'officer_3_position']
    out_fields = ba_fields + extra_fields

    rows_with_match = 0
    rows_with_officer = 0

    with open(OUTPUT, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=out_fields, extrasaction='ignore')
        writer.writeheader()

        for row in ba_rows:
            norm = normalize(row.get('company_name', ''))
            if norm in matched:
                md = matched[norm]
                row['or_name'] = md.get('or_name', '')
                row['or_address'] = md.get('or_address', '')
                row['or_city'] = md.get('or_city', '')
                row['or_status'] = md.get('or_status', '')
                row['or_federal_state'] = md.get('or_federal_state', '')
                row['match_score'] = md.get('match_score', 100)  # 100 for exact
                rows_with_match += 1

                cn = md.get('company_number', '')
                offs = cn_to_officers.get(cn, [])
                if offs:
                    rows_with_officer += 1
                    for j, off in enumerate(offs[:3], 1):
                        row[f'officer_{j}_name'] = off['name']
                        row[f'officer_{j}_position'] = off['position']
                        if j == 1:
                            row['officer_1_firstname'] = off['firstname']
                            row['officer_1_lastname'] = off['lastname']

            writer.writerow(row)

    print(f"\nDONE!")
    print(f"  Total BA agencies: {len(ba_rows)}")
    print(f"  With OR match: {rows_with_match} ({rows_with_match*100/len(ba_rows):.1f}%)")
    print(f"  With officers: {rows_with_officer} ({rows_with_officer*100/len(ba_rows):.1f}%)")
    print(f"  Output: {OUTPUT}")

if __name__ == '__main__':
    main()
