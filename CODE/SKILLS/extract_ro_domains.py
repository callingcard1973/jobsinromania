#!/usr/bin/env python3
"""
Extract and validate .ro domains from Romanian data sources

Sources:
  - ONRC registry (WEB column)
  - ANOFM (company_website)
  - CCIB (website)
  - Listafirme scraper output

Usage:
  python3 extract_ro_domains.py --scan          # Scan all sources
  python3 extract_ro_domains.py --onrc          # ONRC only
  python3 extract_ro_domains.py --export        # Export all valid domains
  python3 extract_ro_domains.py --ct-search     # Search CT logs for .ro

Output:
  /opt/ACTIVE/OPENDATA/DATA/ROMANIA/DOMAINS/all_ro_domains.csv
  /opt/ACTIVE/OPENDATA/DATA/ROMANIA/DOMAINS/domains_by_source.csv
"""

import sys
import csv
import re
import argparse
from pathlib import Path
from collections import Counter
from urllib.parse import urlparse

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

# Data sources
SOURCES = {
    'onrc': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ONRC/onrc_firme_clean.csv',
    'anofm': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_master.csv',
    'ccib': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CCIB/ccib_companies.csv',
    'master_all': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER_ALL.csv',
    'listafirme': '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/LISTAFIRME/all_urls.csv',
}

OUTPUT_DIR = '/opt/ACTIVE/OPENDATA/DATA/ROMANIA/DOMAINS'

# URL patterns to skip
GARBAGE_PATTERNS = [
    r'^#$', r'^www\.#', r'^http://#', r'^https://#',
    r'^www$', r'^http$', r'^https$',
    r'^n/?a$', r'^-$', r'^\.+$',
    r'facebook\.com', r'linkedin\.com', r'instagram\.com',
    r'twitter\.com', r'youtube\.com', r'tiktok\.com',
]


def is_garbage_url(url):
    """Check if URL is garbage/invalid"""
    if not url or len(url) < 4:
        return True
    url_lower = url.lower().strip()
    for pattern in GARBAGE_PATTERNS:
        if re.match(pattern, url_lower):
            return True
    return False


def normalize_url(url):
    """Normalize URL to standard format"""
    if not url:
        return None

    url = url.strip().lower()

    # Remove garbage
    if is_garbage_url(url):
        return None

    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    # Parse and extract domain
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        domain = domain.replace('www.', '')

        # Skip if no valid TLD
        if '.' not in domain:
            return None

        return domain
    except:
        return None


def extract_domain(url):
    """Extract clean domain from URL"""
    domain = normalize_url(url)
    if not domain:
        return None

    # Remove port if present
    domain = domain.split(':')[0]

    # Skip if not a valid domain
    if len(domain) < 4 or '.' not in domain:
        return None

    return domain


def scan_onrc():
    """Scan ONRC for domains"""
    print("Scanning ONRC...")
    domains = {}

    try:
        with open(SOURCES['onrc'], 'r', encoding='utf-8', errors='ignore') as f:
            # ONRC uses ^ delimiter
            reader = csv.DictReader(f, delimiter='^')

            for row in reader:
                cui = (row.get('CUI') or '').strip()
                web = (row.get('WEB') or '').strip()
                name = (row.get('DENUMIRE') or '').strip()

                if not web or not cui:
                    continue

                domain = extract_domain(web)
                if domain:
                    domains[cui] = {
                        'cui': cui,
                        'company_name': to_ascii(name),
                        'domain': domain,
                        'original_url': web,
                        'source': 'onrc'
                    }

        print(f"  Found {len(domains):,} domains")
    except Exception as e:
        print(f"  Error: {e}")

    return domains


def scan_anofm():
    """Scan ANOFM for domains"""
    print("Scanning ANOFM...")
    domains = {}

    try:
        with open(SOURCES['anofm'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                web = (row.get('company_website') or '').strip()
                name = (row.get('company_name') or '').strip()
                org_num = (row.get('company_org_number') or '').strip()

                if not web:
                    continue

                domain = extract_domain(web)
                if domain and name:
                    # Use org_number as key if available, else normalized name
                    key = org_num if org_num else to_ascii(name).upper()
                    domains[key] = {
                        'cui': org_num,
                        'company_name': to_ascii(name),
                        'domain': domain,
                        'original_url': web,
                        'source': 'anofm'
                    }

        print(f"  Found {len(domains):,} domains")
    except Exception as e:
        print(f"  Error: {e}")

    return domains


def scan_ccib():
    """Scan CCIB for domains"""
    print("Scanning CCIB...")
    domains = {}

    try:
        with open(SOURCES['ccib'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                web = row.get('website', '').strip()
                name = row.get('name', '').strip()

                domain = extract_domain(web)
                if domain and name:
                    key = to_ascii(name).upper()
                    domains[key] = {
                        'company_name': to_ascii(name),
                        'domain': domain,
                        'original_url': web,
                        'source': 'ccib'
                    }

        print(f"  Found {len(domains):,} domains")
    except Exception as e:
        print(f"  Error: {e}")

    return domains


def scan_master_all():
    """Scan MASTER_ALL for domains"""
    print("Scanning MASTER_ALL...")
    domains = {}

    try:
        with open(SOURCES['master_all'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                web = row.get('company_website', '').strip()
                name = row.get('employer', '').strip()

                domain = extract_domain(web)
                if domain and name:
                    key = to_ascii(name).upper()
                    domains[key] = {
                        'company_name': to_ascii(name),
                        'domain': domain,
                        'original_url': web,
                        'source': 'master_all'
                    }

        print(f"  Found {len(domains):,} domains")
    except Exception as e:
        print(f"  Error: {e}")

    return domains


def scan_listafirme():
    """Scan Listafirme scraper output"""
    print("Scanning Listafirme...")
    domains = {}

    try:
        if not Path(SOURCES['listafirme']).exists():
            print("  Not yet scraped")
            return domains

        with open(SOURCES['listafirme'], 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = row.get('cui', '').strip()
                web = row.get('website', '').strip()
                name = row.get('company_name', '').strip()

                domain = extract_domain(web)
                if domain and cui:
                    domains[cui] = {
                        'cui': cui,
                        'company_name': to_ascii(name),
                        'domain': domain,
                        'original_url': web,
                        'source': 'listafirme'
                    }

        print(f"  Found {len(domains):,} domains")
    except Exception as e:
        print(f"  Error: {e}")

    return domains


def merge_domains(all_sources):
    """Merge domains from all sources, deduplicating"""
    print("\nMerging domains...")

    merged = {}
    by_domain = {}

    for source_name, source_data in all_sources.items():
        for key, data in source_data.items():
            domain = data['domain']

            # Track by domain for dedup
            if domain not in by_domain:
                by_domain[domain] = data
            else:
                # Keep entry with more info (CUI preferred)
                if 'cui' in data and 'cui' not in by_domain[domain]:
                    by_domain[domain] = data

    print(f"  Unique domains: {len(by_domain):,}")

    # Stats by TLD
    tld_counts = Counter()
    for domain in by_domain:
        tld = '.' + domain.split('.')[-1]
        tld_counts[tld] += 1

    print("\n  Top TLDs:")
    for tld, count in tld_counts.most_common(10):
        print(f"    {tld}: {count:,}")

    return by_domain


def export_domains(domains, output_path):
    """Export domains to CSV"""
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

    fieldnames = ['domain', 'company_name', 'cui', 'original_url', 'source']

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        for domain, data in sorted(domains.items()):
            data['domain'] = domain
            writer.writerow(data)

    print(f"\nExported {len(domains):,} domains to {output_path}")


def search_ct_logs(limit=1000):
    """Search Certificate Transparency logs for .ro domains"""
    print("\nSearching CT logs (crt.sh)...")

    try:
        import httpx
    except ImportError:
        print("  httpx not installed")
        return []

    domains = set()

    # Query crt.sh for .ro certificates
    url = f"https://crt.sh/?q=%.ro&output=json"

    try:
        with httpx.Client(timeout=60) as client:
            response = client.get(url)
            if response.status_code == 200:
                data = response.json()
                for cert in data[:limit]:
                    name = cert.get('common_name', '')
                    if name.endswith('.ro'):
                        # Clean domain
                        domain = name.replace('*.', '').lower()
                        if '.' in domain and len(domain) > 4:
                            domains.add(domain)

                print(f"  Found {len(domains)} unique .ro domains from CT logs")
    except Exception as e:
        print(f"  CT search error: {e}")

    return list(domains)


def show_stats():
    """Show domain extraction stats"""
    print("\n" + "="*60)
    print("ROMANIAN DOMAIN EXTRACTION STATS")
    print("="*60)

    # Check each source
    for name, path in SOURCES.items():
        exists = Path(path).exists()
        if exists:
            try:
                with open(path, 'r') as f:
                    lines = sum(1 for _ in f) - 1
                print(f"  {name:15} {lines:>10,} records")
            except:
                print(f"  {name:15} exists but unreadable")
        else:
            print(f"  {name:15} NOT FOUND")

    # Check output
    output_file = f'{OUTPUT_DIR}/all_ro_domains.csv'
    if Path(output_file).exists():
        with open(output_file, 'r') as f:
            domains = sum(1 for _ in f) - 1
        print(f"\n  Exported domains: {domains:,}")


def main():
    parser = argparse.ArgumentParser(description='Extract .ro domains from Romanian data')
    parser.add_argument('--scan', action='store_true', help='Scan all sources')
    parser.add_argument('--onrc', action='store_true', help='Scan ONRC only')
    parser.add_argument('--export', action='store_true', help='Export all domains')
    parser.add_argument('--ct-search', action='store_true', help='Search CT logs')
    parser.add_argument('--stats', action='store_true', help='Show stats')

    args = parser.parse_args()

    if args.stats:
        show_stats()
        return

    all_sources = {}

    if args.onrc:
        all_sources['onrc'] = scan_onrc()
    elif args.scan or args.export:
        all_sources['onrc'] = scan_onrc()
        all_sources['anofm'] = scan_anofm()
        all_sources['ccib'] = scan_ccib()
        all_sources['master_all'] = scan_master_all()
        all_sources['listafirme'] = scan_listafirme()

    if args.ct_search:
        ct_domains = search_ct_logs()
        print(f"CT domains sample: {ct_domains[:5]}")

    if all_sources:
        merged = merge_domains(all_sources)

        if args.export:
            output = f'{OUTPUT_DIR}/all_ro_domains.csv'
            export_domains(merged, output)


if __name__ == '__main__':
    main()
