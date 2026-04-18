"""
scrape_partide.py - Enrich primarii_campanie.csv with 2024 local election party data
Source: api.rezultatevot.ro (Code for Romania)
Ballot 114 = Primari (mayors), Ballot 116 = Consilii locale (local councils)
"""
# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import csv
import json
import time
import unicodedata
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

BASE_URL = "https://api.rezultatevot.ro/api"
HEADERS = {
    'Accept': 'application/json',
    'Origin': 'https://istoric.rezultatevot.ro',
    'Referer': 'https://istoric.rezultatevot.ro/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
INPUT_CSV = "D:/MEMORY/BUSINESS/BOGDAN GAVRA/primarii_campanie.csv"
OUTPUT_CSV = "D:/MEMORY/BUSINESS/BOGDAN GAVRA/primarii_campanie_enriched.csv"
CACHE_FILE = "D:/MEMORY/BUSINESS/BOGDAN GAVRA/partide_cache.json"

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def normalize(s):
    if not s:
        return ""
    s = s.strip().lower()
    # Strip common prefixes that differ between CSV and API
    for prefix in ('municipiul ', 'municipiu ', 'oras ', 'oraș ', 'comuna ', 'satul '):
        if s.startswith(prefix):
            s = s[len(prefix):]
            break
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = re.sub(r'[\s\-]+', ' ', s)
    return s.strip()


def api_get(url, retries=3):
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=15)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        if attempt < retries - 1:
            time.sleep(1 + attempt)
    return None


def get_winner_party(candidates):
    if not candidates:
        return None
    winner = max(candidates, key=lambda c: c.get('votes', 0))
    return winner.get('partyName') or winner.get('shortName') or ''


def get_majority_party(candidates):
    if not candidates:
        return None
    # Sort by seats first, then votes
    winner = max(candidates, key=lambda c: (c.get('seats', 0) or 0, c.get('votes', 0) or 0))
    return winner.get('partyName') or winner.get('shortName') or ''


def fetch_locality_data(county_id, locality_id):
    mayor_data = api_get(
        f"{BASE_URL}/ballot?BallotId=114&Division=locality&CountyId={county_id}&LocalityId={locality_id}"
    )
    council_data = api_get(
        f"{BASE_URL}/ballot?BallotId=116&Division=locality&CountyId={county_id}&LocalityId={locality_id}"
    )

    mayor_party = ''
    council_party = ''

    if mayor_data:
        cands = mayor_data.get('results', {}).get('candidates', [])
        mayor_party = get_winner_party(cands) or ''

    if council_data:
        cands = council_data.get('results', {}).get('candidates', [])
        council_party = get_majority_party(cands) or ''

    return {'partid_primar': mayor_party, 'partid_consiliu': council_party}


def main():
    # Load cache
    cache = {}
    cache_path = Path(CACHE_FILE)
    if cache_path.exists():
        with open(cache_path, encoding='utf-8') as f:
            cache = json.load(f)
        print(f"Cache loaded: {len(cache)} localities")

    # Step 1: Build locality index
    print("Fetching counties...")
    counties = api_get(f"{BASE_URL}/counties")
    if not counties:
        print("ERROR: Could not fetch counties")
        return
    print(f"Found {len(counties)} counties")

    print("Building locality index...")
    locality_index = {}  # norm_county -> {norm_name -> (county_id, loc_id)}

    for county in counties:
        cid = county['id']
        cname = county['name']
        cnorm = normalize(cname)
        locs = api_get(f"{BASE_URL}/localities?CountyId={cid}")
        if not locs:
            continue
        locality_index[cnorm] = {
            normalize(loc['name']): (cid, loc['id'])
            for loc in locs
        }
        time.sleep(0.05)

    total_indexed = sum(len(v) for v in locality_index.values())
    print(f"Indexed {total_indexed} localities in {len(locality_index)} counties")

    # Step 2: Load target CSV
    with open(INPUT_CSV, encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} target rows")

    # Step 3: Match rows and identify what needs fetching
    to_fetch = []  # (row_idx, county_id, locality_id, cache_key)
    row_matches = {}  # row_idx -> cache_key or None

    for i, row in enumerate(rows):
        name_norm = normalize(row['name'])
        county_norm = normalize(row['county'])

        # Find county
        county_locs = locality_index.get(county_norm)
        if not county_locs:
            # Partial match
            for cn in locality_index:
                if county_norm and (cn in county_norm or county_norm in cn):
                    county_locs = locality_index[cn]
                    break

        if not county_locs:
            row_matches[i] = None
            continue

        # Find locality
        match = county_locs.get(name_norm)
        if not match:
            for ln, ldata in county_locs.items():
                if ln and name_norm and (ln == name_norm or
                        ln.startswith(name_norm + ' ') or
                        name_norm.startswith(ln + ' ')):
                    match = ldata
                    break

        if not match:
            row_matches[i] = None
            continue

        cid, lid = match
        cache_key = f"{cid}_{lid}"
        row_matches[i] = cache_key

        if cache_key not in cache:
            to_fetch.append((i, cid, lid, cache_key))

    unmatched = sum(1 for v in row_matches.values() if v is None)
    already_cached = sum(1 for v in row_matches.values() if v and v in cache)
    print(f"Matched: {len(rows)-unmatched}, Unmatched: {unmatched}")
    print(f"From cache: {already_cached}, Need fetch: {len(to_fetch)}")

    # Step 4: Fetch missing data
    if to_fetch:
        print(f"Fetching {len(to_fetch)} localities (8 threads)...")
        completed = 0

        def fetch_one(args):
            _, cid, lid, cache_key = args
            result = fetch_locality_data(cid, lid)
            return cache_key, result

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = {pool.submit(fetch_one, args): args for args in to_fetch}
            for future in as_completed(futures):
                try:
                    cache_key, result = future.result()
                    cache[cache_key] = result
                    completed += 1
                    if completed % 200 == 0:
                        pct = completed / len(to_fetch) * 100
                        print(f"  {completed}/{len(to_fetch)} ({pct:.0f}%)")
                        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
                            json.dump(cache, f, ensure_ascii=False)
                except Exception as e:
                    print(f"  Error: {e}")

        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False)
        print(f"Cache saved: {len(cache)} localities")

    # Step 5: Enrich rows
    enriched = 0
    for i, row in enumerate(rows):
        cache_key = row_matches.get(i)
        if cache_key and cache_key in cache:
            data = cache[cache_key]
            row['partid_primar'] = data.get('partid_primar', '')
            row['partid_consiliu'] = data.get('partid_consiliu', '')
            if row['partid_primar'] or row['partid_consiliu']:
                enriched += 1
        else:
            row['partid_primar'] = ''
            row['partid_consiliu'] = ''

    # Step 6: Write output
    fieldnames = ['name', 'email', 'county', 'phone', 'partid_primar', 'partid_consiliu']
    with open(OUTPUT_CSV, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    coverage = enriched / len(rows) * 100
    print(f"\nDone!")
    print(f"Total rows: {len(rows)}")
    print(f"Enriched with party data: {enriched} ({coverage:.1f}%)")
    print(f"Unmatched: {unmatched}")
    print(f"Output: {OUTPUT_CSV}")


if __name__ == '__main__':
    main()
