#!/usr/bin/env python3
"""
Lead Research Assistant - Qualify and enrich contact data
Usage: python3 lead_researcher.py [analyze|segment|score|export] <csv_file> [options]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import csv
import re
import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Optional

# ============================================================
# INDUSTRY CLASSIFICATION
# ============================================================

INDUSTRIES = {
    'healthcare': {
        'domains': ['hospital', 'health', 'medical', 'clinic', 'helse', 'hf.no', 'nhs', 'care'],
        'keywords': ['nurse', 'doctor', 'medical', 'patient', 'healthcare'],
        'score_boost': 1.2,
    },
    'government': {
        'domains': ['.gov', 'kommune', 'region', 'municipal', 'council', 'ministry', 'dept'],
        'keywords': ['public', 'government', 'civil', 'official'],
        'score_boost': 1.3,
    },
    'education': {
        'domains': ['.edu', 'university', 'univ', 'college', 'school', 'academy', '.ac.'],
        'keywords': ['professor', 'teacher', 'student', 'academic'],
        'score_boost': 1.1,
    },
    'staffing': {
        'domains': ['recruit', 'staff', 'manpower', 'adecco', 'randstad', 'hays', 'temp'],
        'keywords': ['recruiter', 'hr', 'talent', 'hiring'],
        'score_boost': 1.5,  # High value for recruitment business
    },
    'hospitality': {
        'domains': ['hotel', 'resort', 'hostel', 'restaurant', 'cafe', 'booking'],
        'keywords': ['chef', 'manager', 'hospitality', 'tourism'],
        'score_boost': 1.2,
    },
    'retail': {
        'domains': ['store', 'shop', 'retail', 'mall', 'market'],
        'keywords': ['sales', 'store', 'retail', 'merchandis'],
        'score_boost': 1.0,
    },
    'construction': {
        'domains': ['build', 'construct', 'architect', 'engineer', 'contractor'],
        'keywords': ['project', 'site', 'construction', 'builder'],
        'score_boost': 1.2,
    },
    'technology': {
        'domains': ['tech', 'software', 'digital', 'data', 'cloud', 'cyber', '.io'],
        'keywords': ['developer', 'engineer', 'it', 'tech', 'digital'],
        'score_boost': 1.1,
    },
    'logistics': {
        'domains': ['transport', 'logistics', 'shipping', 'freight', 'cargo', 'delivery'],
        'keywords': ['driver', 'warehouse', 'logistics', 'transport'],
        'score_boost': 1.2,
    },
    'manufacturing': {
        'domains': ['factory', 'manufactur', 'production', 'industrial'],
        'keywords': ['operator', 'production', 'assembly', 'factory'],
        'score_boost': 1.1,
    },
}

PERSONAL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com', 'yahoo.ro',
    'mail.ru', 'icloud.com', 'wp.pl', 'o2.pl', 'interia.pl', 'abv.bg',
    'yandex.ru', 'protonmail.com', 'live.com', 'msn.com', 'aol.com'
}

COUNTRIES = {
    '.no': 'Norway', '.se': 'Sweden', '.dk': 'Denmark', '.fi': 'Finland',
    '.is': 'Iceland', '.pl': 'Poland', '.ro': 'Romania', '.bg': 'Bulgaria',
    '.mt': 'Malta', '.md': 'Moldova', '.uk': 'UK', '.ie': 'Ireland',
    '.de': 'Germany', '.fr': 'France', '.nl': 'Netherlands', '.be': 'Belgium',
    '.com': 'International', '.eu': 'EU', '.org': 'Organization',
}

# ============================================================
# LEAD ANALYSIS
# ============================================================

def analyze_lead(email: str, company: str = '', name: str = '', phone: str = '') -> Dict:
    """Analyze a single lead and return enriched data"""
    if not email or '@' not in email:
        return {'valid': False, 'reason': 'Invalid email'}

    email = email.lower().strip()
    domain = email.split('@')[1]

    lead = {
        'email': email,
        'domain': domain,
        'valid': True,
        'is_personal': domain in PERSONAL_DOMAINS,
        'company': company,
        'name': name,
        'phone': phone,
        'industry': None,
        'country': None,
        'score': 0,
        'quality': 'low',
    }

    # Detect country from domain
    for tld, country in COUNTRIES.items():
        if domain.endswith(tld):
            lead['country'] = country
            break

    # Detect industry
    domain_lower = domain.lower()
    company_lower = (company or '').lower()

    for industry, config in INDUSTRIES.items():
        if any(kw in domain_lower for kw in config['domains']):
            lead['industry'] = industry
            break
        if any(kw in company_lower for kw in config['keywords']):
            lead['industry'] = industry
            break

    # Calculate score
    lead['score'] = calculate_score(lead)
    lead['quality'] = 'high' if lead['score'] >= 70 else 'medium' if lead['score'] >= 40 else 'low'

    return lead

def calculate_score(lead: Dict) -> int:
    """Calculate lead quality score (0-100)"""
    score = 0

    # Corporate email bonus
    if not lead['is_personal']:
        score += 30

    # Has company name
    if lead.get('company'):
        score += 15

    # Has contact name
    if lead.get('name'):
        score += 10

    # Has phone
    if lead.get('phone'):
        score += 10

    # Known country
    if lead.get('country') and lead['country'] != 'International':
        score += 10

    # Industry identified
    if lead.get('industry'):
        score += 15
        # Apply industry boost
        boost = INDUSTRIES.get(lead['industry'], {}).get('score_boost', 1.0)
        score = int(score * boost)

    # Valid email format
    if re.match(r'^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$', lead['email']):
        score += 10

    return min(score, 100)

# ============================================================
# BATCH ANALYSIS
# ============================================================

def analyze_csv(csv_path: str) -> Dict:
    """Analyze all leads in a CSV file"""
    results = {
        'file': csv_path,
        'total': 0,
        'valid': 0,
        'corporate': 0,
        'personal': 0,
        'by_industry': Counter(),
        'by_country': Counter(),
        'by_quality': Counter(),
        'avg_score': 0,
        'top_domains': Counter(),
        'leads': [],
    }

    with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        return results

    # Find relevant columns
    cols = rows[0].keys()
    email_col = next((c for c in cols if 'email' in c.lower()), None)
    company_col = next((c for c in cols if 'company' in c.lower()), None)
    name_col = next((c for c in cols if 'name' in c.lower() and 'company' not in c.lower()), None)
    phone_col = next((c for c in cols if 'phone' in c.lower() or 'tel' in c.lower()), None)

    if not email_col:
        return {'error': 'No email column found'}

    scores = []

    for row in rows:
        email = row.get(email_col, '').strip()
        if not email or '@' not in email:
            continue

        results['total'] += 1

        lead = analyze_lead(
            email=email,
            company=row.get(company_col, '') if company_col else '',
            name=row.get(name_col, '') if name_col else '',
            phone=row.get(phone_col, '') if phone_col else '',
        )

        if lead['valid']:
            results['valid'] += 1
            scores.append(lead['score'])

            if lead['is_personal']:
                results['personal'] += 1
            else:
                results['corporate'] += 1
                results['top_domains'][lead['domain']] += 1

            if lead['industry']:
                results['by_industry'][lead['industry']] += 1

            if lead['country']:
                results['by_country'][lead['country']] += 1

            results['by_quality'][lead['quality']] += 1
            results['leads'].append(lead)

    results['avg_score'] = sum(scores) / len(scores) if scores else 0
    results['top_domains'] = dict(results['top_domains'].most_common(20))

    return results

def segment_leads(csv_path: str) -> Dict:
    """Segment leads by industry"""
    analysis = analyze_csv(csv_path)

    if 'error' in analysis:
        return analysis

    segments = defaultdict(list)

    for lead in analysis['leads']:
        industry = lead['industry'] or 'unknown'
        segments[industry].append(lead)

    return {
        'file': csv_path,
        'total_leads': len(analysis['leads']),
        'segments': {k: len(v) for k, v in segments.items()},
        'by_segment': {k: v for k, v in segments.items()},
    }

def export_qualified(csv_path: str, output_path: str, min_score: int = 50,
                     industry: str = None, corporate_only: bool = True) -> Dict:
    """Export qualified leads to new CSV"""
    analysis = analyze_csv(csv_path)

    if 'error' in analysis:
        return analysis

    qualified = []
    for lead in analysis['leads']:
        if lead['score'] < min_score:
            continue
        if corporate_only and lead['is_personal']:
            continue
        if industry and lead['industry'] != industry:
            continue
        qualified.append(lead)

    # Write output
    if qualified:
        fieldnames = ['email', 'domain', 'company', 'name', 'phone',
                      'industry', 'country', 'score', 'quality']
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for lead in qualified:
                writer.writerow({k: lead.get(k, '') for k in fieldnames})

    return {
        'input': csv_path,
        'output': output_path,
        'total_input': len(analysis['leads']),
        'qualified': len(qualified),
        'filters': {
            'min_score': min_score,
            'industry': industry,
            'corporate_only': corporate_only,
        }
    }

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print(f"""
{'='*60}
LEAD RESEARCH ASSISTANT
{'='*60}

Usage: lead_researcher.py <command> <csv_file> [options]

Commands:
  analyze   - Full analysis with scoring and insights
  segment   - Segment leads by industry
  score     - Show score distribution
  export    - Export qualified leads

Export Options:
  --min-score N      Minimum score (default: 50)
  --industry NAME    Filter by industry
  --corporate-only   Exclude personal emails (default)
  --all-emails       Include personal emails
  --output FILE      Output file path

Industries: {', '.join(INDUSTRIES.keys())}

Examples:
  lead_researcher.py analyze contacts.csv
  lead_researcher.py segment contacts.csv
  lead_researcher.py export contacts.csv --min-score 60 --industry staffing
""")
        return

    command = args[0]
    csv_path = args[1]

    if not os.path.exists(csv_path):
        print(f"Error: File not found: {csv_path}")
        return

    print(f"\n{'='*60}")
    print(f"LEAD RESEARCH ASSISTANT - {command.upper()}")
    print(f"File: {Path(csv_path).name}")
    print(f"{'='*60}\n")

    if command == 'analyze':
        results = analyze_csv(csv_path)

        print(f"SUMMARY:")
        print(f"  Total emails: {results['total']}")
        print(f"  Valid: {results['valid']}")
        print(f"  Corporate: {results['corporate']} ({results['corporate']*100//max(results['valid'],1)}%)")
        print(f"  Personal: {results['personal']} ({results['personal']*100//max(results['valid'],1)}%)")
        print(f"  Avg Score: {results['avg_score']:.1f}/100")

        print(f"\nQUALITY DISTRIBUTION:")
        for q in ['high', 'medium', 'low']:
            count = results['by_quality'].get(q, 0)
            pct = count * 100 // max(results['valid'], 1)
            bar = '#' * (pct // 5)
            print(f"  {q:8}: {count:5} ({pct:2}%) {bar}")

        print(f"\nBY INDUSTRY:")
        for ind, count in results['by_industry'].most_common(10):
            print(f"  {ind}: {count}")

        print(f"\nBY COUNTRY:")
        for country, count in results['by_country'].most_common(10):
            print(f"  {country}: {count}")

        print(f"\nTOP CORPORATE DOMAINS:")
        for domain, count in list(results['top_domains'].items())[:10]:
            print(f"  {domain}: {count}")

    elif command == 'segment':
        results = segment_leads(csv_path)

        print(f"SEGMENTS:")
        for industry, count in sorted(results['segments'].items(), key=lambda x: -x[1]):
            pct = count * 100 // max(results['total_leads'], 1)
            print(f"  {industry}: {count} ({pct}%)")

    elif command == 'score':
        results = analyze_csv(csv_path)

        print(f"SCORE DISTRIBUTION:")
        ranges = [(90, 100), (70, 89), (50, 69), (30, 49), (0, 29)]
        for low, high in ranges:
            count = sum(1 for l in results['leads'] if low <= l['score'] <= high)
            pct = count * 100 // max(len(results['leads']), 1)
            bar = '#' * (pct // 2)
            print(f"  {low:2}-{high:3}: {count:5} ({pct:2}%) {bar}")

    elif command == 'export':
        # Parse options
        min_score = 50
        industry = None
        corporate_only = True
        output = csv_path.replace('.csv', '_qualified.csv')

        for i, arg in enumerate(args):
            if arg == '--min-score' and i + 1 < len(args):
                min_score = int(args[i + 1])
            elif arg == '--industry' and i + 1 < len(args):
                industry = args[i + 1]
            elif arg == '--all-emails':
                corporate_only = False
            elif arg == '--output' and i + 1 < len(args):
                output = args[i + 1]

        results = export_qualified(csv_path, output, min_score, industry, corporate_only)

        print(f"EXPORT RESULTS:")
        print(f"  Input: {results['total_input']} leads")
        print(f"  Qualified: {results['qualified']} leads")
        print(f"  Output: {results['output']}")
        print(f"\n  Filters:")
        for k, v in results['filters'].items():
            print(f"    {k}: {v}")

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
