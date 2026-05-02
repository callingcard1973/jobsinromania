#!/usr/bin/env python3
"""
Job Market Intelligence Skill

Tracks:
1. Job fairs in Romania (AJOFM, independent, university)
2. Exhibitor/participant lists at job fairs
3. Layoff announcements (concedieri colective)

Sources:
- AJOFM/ANOFM websites (42 counties + Bucuresti)
- hipo.ro / Angajatori de TOP exhibitors
- targuldecariere.ro participants
- BVB (Bucharest Stock Exchange) current reports
- ITM notifications (via news aggregation)
- Business news (ZF, wall-street.ro, economica.net)

Usage:
    python3 job_market_intel.py --fairs              # List upcoming job fairs
    python3 job_market_intel.py --exhibitors EVENT   # Get exhibitors for event
    python3 job_market_intel.py --layoffs            # Recent layoff announcements
    python3 job_market_intel.py --layoffs --days 30  # Layoffs in last 30 days
    python3 job_market_intel.py --monitor            # Full market scan
    python3 job_market_intel.py --sources            # List all data sources
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import argparse
import csv
import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin, quote_plus

from skills_common import to_ascii, get_http_client

# ============================================================
# CONFIGURATION
# ============================================================

DATA_DIR = Path('/opt/ACTIVE/OPENDATA/DATA/ROMANIA/JOB FAIRS')
CACHE_DIR = DATA_DIR / 'cache'
OUTPUT_DIR = DATA_DIR / 'output'

# Job Fair Sources
JOB_FAIR_SOURCES = {
    'ajofm': {
        'name': 'AJOFM/ANOFM',
        'base_url': 'https://www.anofm.ro/',
        'type': 'government',
        'data': 'burse, job fairs by county'
    },
    'hipo': {
        'name': 'Angajatori de TOP (Hipo.ro)',
        'base_url': 'https://www.hipo.ro/locuri-de-munca/angajatoridetop/',
        'exhibitors_url': 'https://www.hipo.ro/locuri-de-munca/angajatoridetop/{city}/companii',
        'type': 'independent',
        'cities': ['bucuresti', 'timisoara', 'cluj', 'iasi', 'brasov']
    },
    'targul_cariere': {
        'name': 'Targul de Cariere',
        'base_url': 'https://www.targuldecariere.ro/',
        'type': 'independent',
        'cities': ['cluj', 'bucuresti', 'timisoara', 'iasi', 'brasov', 'sibiu', 'oradea', 'targu-mures', 'ploiesti', 'chisinau']
    },
    'devtalks': {
        'name': 'DevTalks',
        'base_url': 'https://www.devtalks.ro/',
        'type': 'tech',
        'cities': ['bucuresti', 'cluj']
    },
    'techsylvania': {
        'name': 'Techsylvania',
        'base_url': 'https://techsylvania.com/',
        'type': 'tech'
    },
    'itdays': {
        'name': 'IT Days Cluj',
        'base_url': 'https://www.itdays.ro/',
        'type': 'tech'
    },
    'polijobs': {
        'name': 'POLIJobs UPB',
        'base_url': 'https://events.upb.ro/event/polijobs/',
        'type': 'university'
    },
    'zilele_carierei': {
        'name': 'Zilele Carierei UPT',
        'base_url': 'https://zilelecarierei.upt.ro/',
        'type': 'university'
    }
}

# Layoff/Restructuring Sources
LAYOFF_SOURCES = {
    'bvb': {
        'name': 'BVB Current Reports',
        'url': 'https://bvb.ro/FinancialInstruments/SelectedData/CurrentReports',
        'type': 'official',
        'keywords': ['concediere', 'restructurare', 'disponibilizare', 'reducere personal', 'reorganizare']
    },
    'zf': {
        'name': 'Ziarul Financiar',
        'search_url': 'https://www.zf.ro/cautare/?q={query}',
        'type': 'news',
        'keywords': ['concedieri', 'disponibilizari', 'restructurare']
    },
    'economica': {
        'name': 'Economica.net',
        'search_url': 'https://www.economica.net/cauta/?q={query}',
        'type': 'news'
    },
    'wall_street': {
        'name': 'Wall-Street.ro',
        'search_url': 'https://www.wall-street.ro/cauta/{query}',
        'type': 'news'
    },
    'profit': {
        'name': 'Profit.ro',
        'search_url': 'https://www.profit.ro/search?q={query}',
        'type': 'news'
    }
}

# ITM (Inspectoratul Teritorial de Munca) - 42 judete
ITM_COUNTIES = [
    'alba', 'arad', 'arges', 'bacau', 'bihor', 'bistrita-nasaud', 'botosani',
    'braila', 'brasov', 'bucuresti', 'buzau', 'calarasi', 'caras-severin',
    'cluj', 'constanta', 'covasna', 'dambovita', 'dolj', 'galati', 'giurgiu',
    'gorj', 'harghita', 'hunedoara', 'ialomita', 'iasi', 'ilfov', 'maramures',
    'mehedinti', 'mures', 'neamt', 'olt', 'prahova', 'salaj', 'satu-mare',
    'sibiu', 'suceava', 'teleorman', 'timis', 'tulcea', 'valcea', 'vaslui', 'vrancea'
]

# ============================================================
# DATA LOADING
# ============================================================

def load_job_fairs_csv() -> List[Dict]:
    """Load job fairs from CSV."""
    csv_path = DATA_DIR / 'job_fairs_romania_2026.csv'
    if not csv_path.exists():
        print(f"Warning: {csv_path} not found")
        return []

    fairs = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            fairs.append(row)
    return fairs

def get_upcoming_fairs(days_ahead: int = 90) -> List[Dict]:
    """Get job fairs happening in the next N days."""
    fairs = load_job_fairs_csv()
    today = datetime.now().date()
    cutoff = today + timedelta(days=days_ahead)

    upcoming = []
    for fair in fairs:
        date_str = fair.get('date_2026_predicted', '')
        if not date_str or date_str == 'N/A':
            continue
        try:
            fair_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            if today <= fair_date <= cutoff:
                fair['days_until'] = (fair_date - today).days
                upcoming.append(fair)
        except ValueError:
            continue

    return sorted(upcoming, key=lambda x: x.get('days_until', 999))

# ============================================================
# EXHIBITOR EXTRACTION
# ============================================================

def get_hipo_exhibitors(city: str = 'bucuresti') -> List[Dict]:
    """
    Get exhibitor list from Angajatori de TOP.

    The exhibitor list is typically published 2-4 weeks before the event.
    URL pattern: https://www.hipo.ro/locuri-de-munca/angajatoridetop/{city}/companii
    """
    http = get_http_client()
    url = f"https://www.hipo.ro/locuri-de-munca/angajatoridetop/{city}/companii"

    try:
        resp = http.get(url, timeout=30)
        if resp.status_code != 200:
            return []

        # Parse company names from HTML
        # Pattern: <div class="company-name">Company Name</div>
        # or: <a href="/companii/company-slug">Company Name</a>
        html = resp.text
        exhibitors = []

        # Multiple patterns to try
        patterns = [
            r'class="company[_-]?name[^"]*"[^>]*>([^<]+)<',
            r'href="/companii/[^"]+">([^<]+)</a>',
            r'<h\d[^>]*class="[^"]*exhibitor[^"]*"[^>]*>([^<]+)<',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for name in matches:
                name = to_ascii(name.strip())
                if name and len(name) > 2 and name not in [e['name'] for e in exhibitors]:
                    exhibitors.append({
                        'name': name,
                        'source': 'hipo.ro',
                        'event': f'Angajatori de TOP {city.title()}',
                        'url': url
                    })

        return exhibitors
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def get_targul_cariere_exhibitors(city: str = 'cluj') -> List[Dict]:
    """
    Get exhibitor list from Targul de Cariere.

    URL pattern: https://www.targuldecariere.ro/{city}/companii
    """
    http = get_http_client()
    url = f"https://www.targuldecariere.ro/{city}"

    try:
        resp = http.get(url, timeout=30)
        if resp.status_code != 200:
            return []

        html = resp.text
        exhibitors = []

        # Patterns for company extraction
        patterns = [
            r'class="company[^"]*"[^>]*>([^<]+)<',
            r'<div[^>]*data-company="([^"]+)"',
            r'href="/companii/[^"]+">([^<]+)</a>',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for name in matches:
                name = to_ascii(name.strip())
                if name and len(name) > 2 and name not in [e['name'] for e in exhibitors]:
                    exhibitors.append({
                        'name': name,
                        'source': 'targuldecariere.ro',
                        'event': f'Targul de Cariere {city.title()}',
                        'url': url
                    })

        return exhibitors
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

def get_ajofm_participants(county: str) -> List[Dict]:
    """
    Get employer list from AJOFM press releases.

    AJOFM typically publishes:
    - List of participating employers
    - Number of positions offered
    - Job types available
    """
    http = get_http_client()
    url = f"https://www.anofm.ro/{county}/"

    try:
        resp = http.get(url, timeout=30)
        if resp.status_code != 200:
            return []

        html = resp.text
        participants = []

        # Look for employer mentions in bursa-related content
        # Common patterns in AJOFM announcements
        patterns = [
            r'(?:angajator|firma|compani[ae]|societate)[:\s]+([A-Z][A-Za-z\s&.,-]+(?:S\.?R\.?L\.?|S\.?A\.?|S\.?C\.?)?)',
            r'([A-Z][A-Za-z\s&.,-]+(?:S\.?R\.?L\.?|S\.?A\.?))\s+(?:ofera|recruteaza|angajeaza)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html)
            for name in matches:
                name = to_ascii(name.strip())
                if name and len(name) > 3:
                    participants.append({
                        'name': name,
                        'source': 'anofm.ro',
                        'county': county,
                        'url': url
                    })

        return participants
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return []

# ============================================================
# LAYOFF TRACKING
# ============================================================

def search_bvb_layoffs(days: int = 30) -> List[Dict]:
    """
    Search BVB current reports for layoff announcements.

    Listed companies must report material events including:
    - Collective dismissals
    - Restructuring plans
    - Workforce changes > 10%
    """
    http = get_http_client()
    layoffs = []

    # BVB current reports page
    url = "https://bvb.ro/FinancialInstruments/SelectedData/CurrentReports"

    keywords = ['concediere', 'restructurare', 'disponibilizare', 'reducere personal',
                'reorganizare', 'inchidere', 'layoff', 'workforce']

    try:
        resp = http.get(url, timeout=30)
        if resp.status_code == 200:
            html = resp.text.lower()
            for kw in keywords:
                if kw in html:
                    layoffs.append({
                        'source': 'BVB',
                        'keyword': kw,
                        'url': url,
                        'note': 'Manual review needed - keyword found in current reports'
                    })
    except Exception as e:
        print(f"Error searching BVB: {e}")

    return layoffs

def search_news_layoffs(days: int = 30) -> List[Dict]:
    """
    Search business news for layoff announcements.

    Sources: ZF, Economica, Wall-Street, Profit
    """
    http = get_http_client()
    layoffs = []

    search_terms = ['concedieri colective', 'disponibilizari', 'restructurare angajati']

    news_sources = [
        ('Ziarul Financiar', 'https://www.zf.ro/cautare/?q={}'),
        ('Economica', 'https://www.economica.net/cauta/?q={}'),
        ('Profit.ro', 'https://www.profit.ro/search?q={}'),
    ]

    for term in search_terms:
        for source_name, url_template in news_sources:
            url = url_template.format(quote_plus(term))
            layoffs.append({
                'source': source_name,
                'search_term': term,
                'search_url': url,
                'note': 'Search URL - manual review for recent articles'
            })

    return layoffs

def get_itm_info() -> Dict:
    """
    Get ITM (Inspectoratul Teritorial de Munca) information.

    ITM receives mandatory notifications for collective dismissals under:
    - Law 76/2002 art. 69-71 (collective dismissals)
    - HG 1256/2011 (notification procedures)

    Companies must notify ITM 30 days before collective dismissals (>30 employees).
    """
    return {
        'legal_basis': [
            'Legea 76/2002 art. 69-71 - Concedieri colective',
            'HG 1256/2011 - Procedura notificare',
            'Codul Muncii art. 68-73'
        ],
        'thresholds': {
            '20-99_employees': '10+ dismissals = collective',
            '100-299_employees': '10%+ dismissals = collective',
            '300+_employees': '30+ dismissals = collective'
        },
        'notification_period': '30 days before dismissals',
        'itm_websites': {
            county: f'https://www.itm{county}.ro/' for county in ['bucuresti', 'cluj', 'timis', 'iasi', 'brasov']
        },
        'note': 'ITM data not publicly available online - requires FOIA request'
    }

# ============================================================
# OUTPUT / REPORTING
# ============================================================

def print_upcoming_fairs(days: int = 90):
    """Print upcoming job fairs."""
    fairs = get_upcoming_fairs(days)

    print(f"\n=== UPCOMING JOB FAIRS (next {days} days) ===\n")

    if not fairs:
        print("No upcoming fairs found in the specified period.")
        return

    for fair in fairs:
        days_until = fair.get('days_until', '?')
        print(f"{fair.get('date_2026_predicted', 'TBD'):12} | {days_until:3}d | {fair.get('event_name', 'Unknown')[:40]:40}")
        print(f"             | {fair.get('city', ''):15} | {fair.get('type', ''):12} | {fair.get('website', '')[:50]}")
        print()

def print_exhibitors(event: str):
    """Print exhibitors for an event."""
    print(f"\n=== EXHIBITORS: {event.upper()} ===\n")

    exhibitors = []
    event_lower = event.lower()

    if 'angajatori' in event_lower or 'hipo' in event_lower:
        for city in ['bucuresti', 'timisoara', 'cluj']:
            if city in event_lower or event_lower in ['all', 'angajatori']:
                exhibitors.extend(get_hipo_exhibitors(city))

    if 'targul' in event_lower or 'cariere' in event_lower:
        for city in ['cluj', 'bucuresti', 'timisoara']:
            if city in event_lower or event_lower in ['all', 'cariere']:
                exhibitors.extend(get_targul_cariere_exhibitors(city))

    if not exhibitors:
        print(f"No exhibitors found for '{event}'")
        print("\nTry:")
        print("  --exhibitors angajatori-bucuresti")
        print("  --exhibitors targul-cluj")
        print("  --exhibitors all")
        return

    print(f"Found {len(exhibitors)} exhibitors:\n")
    for ex in exhibitors[:50]:  # Limit output
        print(f"  - {ex['name'][:50]:50} | {ex['source']:20} | {ex['event']}")

def print_layoffs(days: int = 30):
    """Print layoff tracking resources."""
    print(f"\n=== LAYOFF TRACKING (last {days} days) ===\n")

    print("BVB Current Reports (listed companies):")
    bvb = search_bvb_layoffs(days)
    for item in bvb[:5]:
        print(f"  - {item['source']}: {item.get('note', '')}")
        print(f"    URL: {item['url']}")

    print("\nNews Search URLs:")
    news = search_news_layoffs(days)
    seen = set()
    for item in news:
        key = (item['source'], item['search_term'])
        if key not in seen:
            seen.add(key)
            print(f"  - {item['source']}: \"{item['search_term']}\"")
            print(f"    {item['search_url']}")

    print("\nITM Legal Framework:")
    itm = get_itm_info()
    for basis in itm['legal_basis']:
        print(f"  - {basis}")
    print(f"\n  Notification period: {itm['notification_period']}")
    print(f"  Note: {itm['note']}")

def print_sources():
    """Print all data sources."""
    print("\n=== JOB FAIR SOURCES ===\n")
    for key, source in JOB_FAIR_SOURCES.items():
        print(f"{source['name']:30} | {source['type']:12} | {source['base_url']}")

    print("\n=== LAYOFF TRACKING SOURCES ===\n")
    for key, source in LAYOFF_SOURCES.items():
        print(f"{source['name']:30} | {source['type']:12}")

    print("\n=== ITM COUNTIES (42) ===\n")
    print(', '.join(ITM_COUNTIES[:21]))
    print(', '.join(ITM_COUNTIES[21:]))

def export_exhibitors_csv(event: str, output_path: Path):
    """Export exhibitors to CSV."""
    exhibitors = []
    event_lower = event.lower()

    if 'all' in event_lower or 'angajatori' in event_lower:
        for city in JOB_FAIR_SOURCES['hipo']['cities']:
            exhibitors.extend(get_hipo_exhibitors(city))

    if 'all' in event_lower or 'cariere' in event_lower:
        for city in JOB_FAIR_SOURCES['targul_cariere']['cities']:
            exhibitors.extend(get_targul_cariere_exhibitors(city))

    if not exhibitors:
        print(f"No exhibitors found for '{event}'")
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'source', 'event', 'url'])
        writer.writeheader()
        writer.writerows(exhibitors)

    print(f"Exported {len(exhibitors)} exhibitors to {output_path}")

# ============================================================
# MAIN
# ============================================================

def main():
    parser = argparse.ArgumentParser(description='Job Market Intelligence')
    parser.add_argument('--fairs', action='store_true', help='List upcoming job fairs')
    parser.add_argument('--days', type=int, default=90, help='Days to look ahead/back')
    parser.add_argument('--exhibitors', type=str, help='Get exhibitors for event (e.g., angajatori-bucuresti)')
    parser.add_argument('--layoffs', action='store_true', help='Layoff tracking resources')
    parser.add_argument('--monitor', action='store_true', help='Full market scan')
    parser.add_argument('--sources', action='store_true', help='List all data sources')
    parser.add_argument('--export', type=str, help='Export exhibitors to CSV')

    args = parser.parse_args()

    # Ensure directories exist
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.sources:
        print_sources()
    elif args.fairs:
        print_upcoming_fairs(args.days)
    elif args.exhibitors:
        if args.export:
            export_exhibitors_csv(args.exhibitors, Path(args.export))
        else:
            print_exhibitors(args.exhibitors)
    elif args.layoffs:
        print_layoffs(args.days)
    elif args.monitor:
        print_upcoming_fairs(args.days)
        print_layoffs(args.days)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
