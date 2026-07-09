#!/usr/bin/env python3
"""
ANOFM API Scraper - Configurable field mapping
Fetches job listings from Romanian Employment Agency (mediere.anofm.ro)

Usage:
    python3 anofm_api_scraper_fixed.py --min 1           # All jobs with 1+ positions
    python3 anofm_api_scraper_fixed.py --min 1 --test    # Test mode (2 pages)
    python3 anofm_api_scraper_fixed.py --csv             # Output as CSV instead of JSON
    python3 anofm_api_scraper_fixed.py --mapping legacy  # Use old Romanian field names

FIELD MAPPING HISTORY:
    - 2025-12 (v2): English field names (employer_name, open_positions, contact_email)
    - Pre-2025 (legacy): Romanian field names (denumire_firma, nr_posturi_vacante, email)
"""

import requests
import json
import csv
import os
import sys
import time
import argparse
from datetime import datetime

# Disable SSL warnings
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# API Configuration
API_BASE_URL = "https://mediere.anofm.ro"
API_ENDPOINT = "/api/entity/vw_public_job_posting"
PAGE_SIZE = 100

# Rate Limiting
PAGE_DELAY = 5
RETRY_DELAY = 10
MAX_RETRIES = 3

# 49-column master CSV field order (kept here so streaming writer can emit the
# header before any job is fetched; must match filtered_job keys below)
CSV_FIELDS = [
    "company_name", "company_normalized", "company_address", "company_city",
    "company_postal_code", "company_website", "company_org_number",
    "contact_person_1", "contact_person_2", "email_1", "email_2", "email_3",
    "phone_1", "phone_2", "phone_3", "contact_title", "job_title", "job_id",
    "job_description", "occupation", "sector", "location", "city", "region",
    "municipality", "country", "country_name", "employment_type",
    "contract_type", "working_hours", "positions_available", "start_date",
    "application_deadline", "salary", "salary_min", "salary_max",
    "salary_currency", "source_url", "application_url", "posting_date",
    "expiry_date", "source", "official_job_board", "scrape_server",
    "scrape_method", "scrape_timestamp", "scrape_date", "raw_source_file",
    "batch_id", "fingerprint",
]

# =============================================================================
# FIELD MAPPINGS - Update here when API changes
# =============================================================================

FIELD_MAPPINGS = {
    # Current API format (2025-12)
    "v2": {
        "positions": "open_positions",
        "positions_new": "open_positions_new",
        "employer": "employer_name",
        "employer_tax": "employer_tax_code",
        "contact_name": "contact_name",
        "contact_email": "contact_email",
        "contact_phone": "contact_phone",
        "occupation": "occupation",
        "cor_name": "cor_name",
        "location": "address_locality_name",
        "street": "address_street",
        "street_number": "address_street_number",
        "contract_type": "contract_type_name",
        "work_type": "work_type_name",
        "work_regime": "work_regime_name",
        "salary_min": "minimum_salary",
        "salary_max": "maximum_salary",
        "salary_type": "salary_type",
        "education": "education_level_name",
        "experience": "professional_experience_name",
        "description": "description",
        "expiry_date": "job_expiry_date",
        "eu_citizens": "offer_available_eu_citizens",
        "domain": "job_domain_name",
        "created_at": "created_at",
        "job_id": "id",
    },
    # Legacy API format (pre-2025) - Romanian field names
    "legacy": {
        "positions": "nr_posturi_vacante",
        "positions_new": "nr_posturi_noi",
        "employer": "denumire_firma",
        "employer_tax": "cui",
        "contact_name": "nume_persoana_contact",
        "contact_email": "email",
        "contact_phone": "telefon",
        "occupation": "titlu_post",
        "cor_name": "cod_cor",
        "location": "localitate",
        "street": "strada",
        "street_number": "numar",
        "contract_type": "tip_contract",
        "work_type": "tip_norma",
        "work_regime": "regim_lucru",
        "salary_min": "salariu_minim",
        "salary_max": "salariu_maxim",
        "salary_type": "tip_salariu",
        "education": "nivel_studii",
        "experience": "experienta",
        "description": "cerinte",
        "expiry_date": "data_expirare",
        "eu_citizens": "oferta_valabila_cetateni_ue",
        "domain": "domeniu",
        "created_at": "data_creare",
        "job_id": "id",
    }
}

# Default mapping
CURRENT_MAPPING = "v2"


def fetch_page(page_num, page_size=PAGE_SIZE):
    """Fetch single page from ANOFM API using POST"""
    url = f"{API_BASE_URL}{API_ENDPOINT}"
    payload = {
        "current": page_num,
        "rowCount": page_size
    }

    for _attempt in range(MAX_RETRIES):
        try:
            response = requests.post(url, json=payload, timeout=30, verify=False, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})

            if response.status_code == 200:
                data = response.json()
                jobs = data.get('rows', [])
                total = data.get('total', 0)
                return jobs, total
            else:
                print(f"[WARN] API returned {response.status_code}, retrying...", file=sys.stderr)
                time.sleep(RETRY_DELAY)

        except requests.exceptions.RequestException as e:
            print(f"[WARN] Request failed: {e}, retrying...", file=sys.stderr)
            time.sleep(RETRY_DELAY)

    return None, None


def get_field(job, mapping, field_name, default=''):
    """Get field value using current mapping"""
    api_field = mapping.get(field_name, field_name)
    value = job.get(api_field, default)
    return value if value is not None else default


def scrape_all_jobs(min_positions=1, max_positions=None, test_mode=False, mapping_name="v2", sink=None):
    """Scrape all job listings from ANOFM API with configurable field mapping.

    If sink is given (callable taking a filtered_job dict), stream each deduped
    job to it as it is fetched (no full buffering in memory). Otherwise buffer
    all into a list and return it. Returns (jobs_or_None, deduped_count)."""
    all_jobs = [] if sink is None else None
    seen = set()  # dedup by job_id (fallback: company|title|city)
    written = 0
    page_num = 1
    total_jobs = None

    # Get field mapping
    mapping = FIELD_MAPPINGS.get(mapping_name, FIELD_MAPPINGS["v2"])
    print(f"[INFO] Using field mapping: {mapping_name}", file=sys.stderr)
    print(f"[INFO] Starting ANOFM scrape (min_positions={min_positions})", file=sys.stderr)
    if test_mode:
        print("[INFO] TEST MODE: 2 pages only", file=sys.stderr)

    while True:
        print(f"[INFO] Fetching page {page_num}...", file=sys.stderr)
        jobs, total = fetch_page(page_num)

        if jobs is None:
            print(f"[FAIL] Failed to fetch page {page_num}", file=sys.stderr)
            break

        if total_jobs is None:
            total_jobs = total
            total_pages = (total_jobs + PAGE_SIZE - 1) // PAGE_SIZE
            print(f"[INFO] Total: {total_jobs} jobs, {total_pages} pages", file=sys.stderr)

        # Filter and map fields using configurable mapping
        filtered_jobs = []
        for job in jobs:
            positions = get_field(job, mapping, 'positions', 0)
            positions = int(positions) if positions else 0

            if positions < min_positions:
                continue
            if max_positions and positions > max_positions:
                continue

            cor_name = get_field(job, mapping, 'cor_name', '')
            get_field(job, mapping, 'eu_citizens', False)

            # 50-column master format
            location_val = get_field(job, mapping, 'location', '')
            filtered_job = {
                'company_name': get_field(job, mapping, 'employer', ''),
                'company_normalized': '',
                'company_address': f"{get_field(job, mapping, 'street', '')} {get_field(job, mapping, 'street_number', '')}".strip(),
                'company_city': location_val,
                'company_postal_code': '',
                'company_website': '',
                'company_org_number': get_field(job, mapping, 'employer_tax', ''),
                'contact_person_1': get_field(job, mapping, 'contact_name', ''),
                'contact_person_2': '',
                'email_1': get_field(job, mapping, 'contact_email', ''),
                'email_2': '',
                'email_3': '',
                'phone_1': get_field(job, mapping, 'contact_phone', ''),
                'phone_2': '',
                'phone_3': '',
                'contact_title': '',
                'job_title': get_field(job, mapping, 'occupation', ''),
                'job_id': get_field(job, mapping, 'job_id', ''),
                'job_description': get_field(job, mapping, 'description', ''),
                'occupation': cor_name.split(' - ')[0] if cor_name and ' - ' in str(cor_name) else str(cor_name),
                'sector': get_field(job, mapping, 'domain', ''),
                'location': location_val,
                'city': location_val,
                'region': '',
                'municipality': '',
                'country': 'RO',
                'country_name': 'Romania',
                'employment_type': get_field(job, mapping, 'work_type', ''),
                'contract_type': get_field(job, mapping, 'contract_type', ''),
                'working_hours': get_field(job, mapping, 'work_regime', ''),
                'positions_available': positions,
                'start_date': '',
                'application_deadline': get_field(job, mapping, 'expiry_date', ''),
                'salary': '',
                'salary_min': get_field(job, mapping, 'salary_min', 0) or 0,
                'salary_max': get_field(job, mapping, 'salary_max', 0) or 0,
                'salary_currency': 'RON',
                'source_url': '',
                'application_url': '',
                'posting_date': get_field(job, mapping, 'created_at', ''),
                'expiry_date': get_field(job, mapping, 'expiry_date', ''),
                'source': 'ANOFM',
                'official_job_board': 'anofm.ro',
                'scrape_server': 'raspibig',
                'scrape_method': 'api',
                'scrape_timestamp': datetime.now().isoformat(),
                'scrape_date': datetime.now().strftime('%Y-%m-%d'),
                'raw_source_file': '',
                'batch_id': '',
                'fingerprint': '',
            }

            # Dedup: job_id preferred; fallback to company|title|city
            jid = str(filtered_job['job_id']).strip()
            key = jid or f"{filtered_job['company_name']}|{filtered_job['job_title']}|{filtered_job['city']}"
            if key in seen:
                continue
            seen.add(key)

            if sink is not None:
                sink(filtered_job)
            else:
                filtered_jobs.append(filtered_job)
            written += 1

        if sink is None:
            all_jobs.extend(filtered_jobs)
        print(f"[INFO] Page {page_num}: {len(jobs)} total, {written} deduped so far", file=sys.stderr)

        if test_mode and page_num >= 2:
            print("[INFO] TEST MODE: Stopping", file=sys.stderr)
            break

        if len(jobs) < PAGE_SIZE:
            print("[INFO] Reached last page", file=sys.stderr)
            break

        page_num += 1
        time.sleep(PAGE_DELAY)

    return (all_jobs, written)


def save_as_json(jobs, output_file, args):
    """Save jobs as JSON"""
    output_data = {
        'metadata': {
            'scrape_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_jobs': len(jobs),
            'min_positions': args.min,
            'max_positions': args.max,
            'test_mode': args.test
        },
        'jobs': jobs
    }
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)


def save_as_csv(jobs, output_file):
    """Save jobs as CSV (buffered fallback; production path streams via main)."""
    if not jobs:
        print("[WARN] No jobs to save", file=sys.stderr)
        return

    fieldnames = CSV_FIELDS
    with open(output_file, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(jobs)


def _stream_csv(output_file, args):
    """Stream-scrape directly to a .tmp CSV then atomically rename. Returns written count."""
    tmp = output_file + '.tmp'
    # Clean orphaned tmp from a previously killed run
    if os.path.exists(tmp):
        os.remove(tmp)
    with open(tmp, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction='ignore')
        writer.writeheader()
        _, written = scrape_all_jobs(
            min_positions=args.min,
            max_positions=args.max,
            test_mode=args.test,
            mapping_name=args.mapping,
            sink=writer.writerow,
        )
        f.flush()
        os.fsync(f.fileno())
    if written == 0:
        print("[WARN] No jobs scraped; removing tmp", file=sys.stderr)
        os.remove(tmp)
        return 0
    os.replace(tmp, output_file)  # atomic: final file appears only when complete
    return written


def main():
    parser = argparse.ArgumentParser(
        description='ANOFM API Scraper with configurable field mapping',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Field mappings available:
  v2     - Current API (2025-12): English field names
  legacy - Old API (pre-2025): Romanian field names

If API changes again, add new mapping to FIELD_MAPPINGS dict.
        """
    )
    parser.add_argument('--min', type=int, default=1, help='Minimum positions (default: 1)')
    parser.add_argument('--max', type=int, default=None, help='Maximum positions')
    parser.add_argument('--test', action='store_true', help='Test mode (2 pages)')
    parser.add_argument('--csv', action='store_true', help='Output as CSV')
    parser.add_argument('--output', type=str, help='Output filename (auto-generated if not specified)')
    parser.add_argument('--mapping', type=str, default='v2', choices=['v2', 'legacy'],
                        help='Field mapping version (default: v2)')
    args = parser.parse_args()

    # Generate output filename up front (needed for streaming path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    if args.output:
        output_file = args.output
    elif args.csv:
        output_file = f"anofm_jobs_{timestamp}.csv"
    else:
        output_file = f"anofm_jobs_{timestamp}.json"

    # Save output
    if args.csv:
        written = _stream_csv(output_file, args)
        count = written
    else:
        jobs, count = scrape_all_jobs(
            min_positions=args.min,
            max_positions=args.max,
            test_mode=args.test,
            mapping_name=args.mapping,
        )
        save_as_json(jobs, output_file, args)

    print(f"[OK] Saved {count} jobs to {output_file}", file=sys.stderr)
    print(output_file)  # Print filename for piping


if __name__ == "__main__":
    main()
