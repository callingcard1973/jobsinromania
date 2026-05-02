#!/usr/bin/env python3
"""
Competitive Ads Extractor - Analyze competitor ads from ad libraries
Usage: python3 competitive_ads.py <competitor> [--platform meta|google]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS, fetch_url

import os
import re
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote, urlencode

# ============================================================
# CONFIGURATION
# ============================================================

CACHE_DIR = Path('/tmp/ads_cache')
CACHE_DIR.mkdir(exist_ok=True)

USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'

# Known job board competitors
COMPETITORS = {
    'eures': {
        'name': 'EURES',
        'domains': ['eures.europa.eu', 'ec.europa.eu/eures'],
        'facebook_page': 'EURESjobs',
        'keywords': ['eures', 'european jobs', 'eu employment'],
    },
    'indeed': {
        'name': 'Indeed',
        'domains': ['indeed.com', 'indeed.ro', 'indeed.no'],
        'facebook_page': 'indeed',
        'keywords': ['indeed', 'job search', 'find jobs'],
    },
    'linkedin': {
        'name': 'LinkedIn Jobs',
        'domains': ['linkedin.com/jobs'],
        'facebook_page': 'LinkedIn',
        'keywords': ['linkedin jobs', 'career', 'professional'],
    },
    'glassdoor': {
        'name': 'Glassdoor',
        'domains': ['glassdoor.com'],
        'facebook_page': 'Glassdoor',
        'keywords': ['glassdoor', 'company reviews', 'salaries'],
    },
    'monster': {
        'name': 'Monster',
        'domains': ['monster.com', 'monster.de'],
        'facebook_page': 'monster',
        'keywords': ['monster jobs', 'career advice'],
    },
    'stepstone': {
        'name': 'StepStone',
        'domains': ['stepstone.de', 'stepstone.com'],
        'facebook_page': 'StepStone',
        'keywords': ['stepstone', 'jobs germany'],
    },
    'jobindex': {
        'name': 'Jobindex',
        'domains': ['jobindex.dk'],
        'facebook_page': 'jobindex',
        'keywords': ['jobindex', 'jobs denmark', 'danish jobs'],
    },
    'finn': {
        'name': 'FINN.no',
        'domains': ['finn.no/job'],
        'facebook_page': 'finn.no',
        'keywords': ['finn jobs', 'norway jobs'],
    },
    'nav': {
        'name': 'NAV.no',
        'domains': ['arbeidsplassen.nav.no'],
        'facebook_page': 'NAV',
        'keywords': ['nav', 'arbeidsplassen', 'norway employment'],
    },
}

# ============================================================
# AD LIBRARY SCRAPERS
# ============================================================

def get_meta_ad_library_url(query: str, country: str = 'ALL') -> str:
    """Generate Meta Ad Library search URL"""
    params = {
        'ad_type': 'all',
        'q': query,
        'country': country,
        'media_type': 'all',
    }
    return f"https://www.facebook.com/ads/library/?{urlencode(params)}"

def get_google_ads_transparency_url(advertiser: str) -> str:
    """Generate Google Ads Transparency Center URL"""
    return f"https://adstransparency.google.com/?query={quote(advertiser)}"

def fetch_url(url: str) -> str:
    """Fetch URL with caching"""
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{url_hash}.html"

    # Check cache (1 hour)
    if cache_file.exists():
        age = datetime.now().timestamp() - cache_file.stat().st_mtime
        if age < 3600:
            return cache_file.read_text(encoding='utf-8', errors='ignore')

    headers = {'User-Agent': USER_AGENT}

    try:
        if HTTP_CLIENT == 'httpx':
            with httpx.Client(follow_redirects=True, timeout=30) as client:
                response = client.get(url, headers=headers)
                html = response.text
        else:
            response = requests.get(url, headers=headers, timeout=30)
            html = response.text

        cache_file.write_text(html, encoding='utf-8')
        return html
    except Exception as e:
        return f"Error: {e}"

def analyze_ad_content(html: str, competitor: str) -> Dict:
    """Analyze ad content from HTML"""
    result = {
        'competitor': competitor,
        'analyzed_at': datetime.now().isoformat(),
        'ads_found': 0,
        'themes': [],
        'ctas': [],
        'offers': [],
        'keywords': [],
    }

    # Common ad patterns
    cta_patterns = [
        r'apply now', r'sign up', r'register', r'join', r'get started',
        r'find jobs', r'search jobs', r'browse', r'discover', r'explore',
        r'free', r'no cost', r'start today',
    ]

    offer_patterns = [
        r'\d+\s*jobs?', r'\d+[kK]\+?\s*jobs?', r'millions?\s*of\s*jobs?',
        r'free\s*access', r'premium', r'exclusive', r'top\s*companies',
    ]

    html_lower = html.lower()

    # Extract CTAs
    for pattern in cta_patterns:
        if re.search(pattern, html_lower):
            result['ctas'].append(pattern.replace(r'\s*', ' ').replace(r'\s+', ' '))

    # Extract offers
    for pattern in offer_patterns:
        matches = re.findall(pattern, html_lower)
        result['offers'].extend(matches[:3])

    # Count potential ads
    ad_indicators = ['sponsored', 'ad_id', 'advertisement', 'promoted']
    for indicator in ad_indicators:
        result['ads_found'] += html_lower.count(indicator)

    return result

# ============================================================
# COMPETITOR ANALYSIS
# ============================================================

def analyze_competitor(name: str) -> Dict:
    """Full analysis of a competitor"""
    name_lower = name.lower()

    if name_lower in COMPETITORS:
        config = COMPETITORS[name_lower]
    else:
        config = {
            'name': name,
            'domains': [name],
            'facebook_page': name,
            'keywords': [name],
        }

    result = {
        'competitor': config['name'],
        'analyzed_at': datetime.now().isoformat(),
        'meta_ad_library': get_meta_ad_library_url(config['name']),
        'google_transparency': get_google_ads_transparency_url(config['name']),
        'domains': config.get('domains', []),
        'facebook_page': config.get('facebook_page'),
        'keywords': config.get('keywords', []),
        'analysis': {
            'meta': None,
            'google': None,
        },
        'recommendations': [],
    }

    # Generate recommendations based on competitor
    if 'indeed' in name_lower:
        result['recommendations'] = [
            "Focus on niche markets (specific countries/industries) where Indeed is weaker",
            "Emphasize personal service vs. automated matching",
            "Target specific industries: healthcare, construction, hospitality",
        ]
    elif 'linkedin' in name_lower:
        result['recommendations'] = [
            "Target blue-collar workers who don't use LinkedIn",
            "Emphasize no-registration job applications",
            "Focus on Eastern European markets",
        ]
    elif 'eures' in name_lower:
        result['recommendations'] = [
            "Provide faster, more responsive service than government portal",
            "Offer additional services: CV help, interview prep",
            "Better mobile experience",
        ]
    else:
        result['recommendations'] = [
            f"Research {config['name']}'s unique selling points",
            "Identify gaps in their service offering",
            "Target underserved markets or demographics",
        ]

    return result

def compare_competitors(names: List[str]) -> Dict:
    """Compare multiple competitors"""
    results = {
        'compared_at': datetime.now().isoformat(),
        'competitors': [],
        'summary': {},
    }

    for name in names:
        analysis = analyze_competitor(name)
        results['competitors'].append(analysis)

    # Summary
    results['summary'] = {
        'total_analyzed': len(names),
        'with_meta_ads': len([c for c in results['competitors'] if c['meta_ad_library']]),
        'with_google_ads': len([c for c in results['competitors'] if c['google_transparency']]),
    }

    return results

def list_known_competitors() -> None:
    """List all known competitors"""
    print(f"\n{'='*60}")
    print("KNOWN COMPETITORS")
    print(f"{'='*60}\n")

    for key, config in COMPETITORS.items():
        print(f"  {key:<15} - {config['name']}")
        print(f"                  Domains: {', '.join(config['domains'][:2])}")

    print(f"\n{'='*60}\n")

# ============================================================
# OUTPUT
# ============================================================

def print_analysis(result: Dict):
    """Print competitor analysis"""
    print(f"\n{'='*60}")
    print(f"COMPETITOR ANALYSIS: {result['competitor']}")
    print(f"{'='*60}\n")

    print(f"Domains: {', '.join(result.get('domains', []))}")
    print(f"Facebook: {result.get('facebook_page', 'N/A')}")

    print(f"\nAD LIBRARY LINKS:")
    print(f"  Meta: {result['meta_ad_library']}")
    print(f"  Google: {result['google_transparency']}")

    if result.get('keywords'):
        print(f"\nKEYWORDS TO MONITOR:")
        for kw in result['keywords']:
            print(f"  - {kw}")

    if result.get('recommendations'):
        print(f"\nRECOMMENDATIONS:")
        for rec in result['recommendations']:
            print(f"  * {rec}")

    print(f"\n{'='*60}\n")

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if not args or '-h' in args or '--help' in args:
        print(f"""
{'='*60}
COMPETITIVE ADS EXTRACTOR
{'='*60}

Usage: competitive_ads.py <competitor> [options]
       competitive_ads.py --list
       competitive_ads.py --compare comp1 comp2 comp3

Options:
  --list            List known competitors
  --compare         Compare multiple competitors
  --json            Output as JSON
  --output FILE     Save to file

Known competitors: {', '.join(COMPETITORS.keys())}

Examples:
  competitive_ads.py indeed
  competitive_ads.py eures --json
  competitive_ads.py --compare indeed linkedin eures
  competitive_ads.py --list
""")
        return

    as_json = '--json' in args
    output_file = None

    for i, arg in enumerate(args):
        if arg == '--output' and i + 1 < len(args):
            output_file = args[i + 1]

    if '--list' in args:
        list_known_competitors()
        return

    if '--compare' in args:
        # Get all competitor names after --compare
        idx = args.index('--compare')
        competitors = [a for a in args[idx+1:] if not a.startswith('-')]

        if not competitors:
            print("Error: No competitors specified for comparison")
            return

        result = compare_competitors(competitors)

        if as_json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{'='*60}")
            print(f"COMPETITOR COMPARISON")
            print(f"{'='*60}\n")

            for comp in result['competitors']:
                print(f"\n{comp['competitor']}:")
                print(f"  Meta Ads: {comp['meta_ad_library'][:50]}...")
                print(f"  Recommendations: {len(comp['recommendations'])}")

        return

    # Single competitor analysis
    competitor = args[0]
    result = analyze_competitor(competitor)

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print_analysis(result)

    if output_file:
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"Saved to: {output_file}")

if __name__ == '__main__':
    main()
