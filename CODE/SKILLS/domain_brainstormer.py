#!/usr/bin/env python3
"""
Domain Brainstormer - Generate and check domain name availability
Usage: python3 domain_brainstormer.py <keywords> [--tlds .com,.eu] [--check]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import socket
import itertools
import subprocess
from datetime import datetime
from typing import Dict, List, Set

# ============================================================
# CONFIGURATION
# ============================================================

COMMON_TLDS = ['.com', '.eu', '.io', '.co', '.net', '.org', '.info', '.ro', '.no', '.se', '.dk', '.pl']
JOB_TLDS = ['.jobs', '.work', '.career', '.careers']

PREFIXES = ['get', 'my', 'the', 'go', 'try', 'use', 'find', 'hire', 'join', 'ez', 'pro', 'top']
SUFFIXES = ['hq', 'hub', 'app', 'now', 'pro', 'plus', 'go', 'io', 'ly', 'ify', 'er', 'ster']
JOB_WORDS = ['jobs', 'work', 'career', 'employ', 'hire', 'recruit', 'staff', 'talent', 'workforce']
COUNTRY_WORDS = {'eu': 'europe', 'no': 'norway', 'se': 'sweden', 'dk': 'denmark', 'pl': 'poland', 'ro': 'romania'}

# ============================================================
# NAME GENERATION
# ============================================================

def generate_variations(keywords: List[str]) -> Set[str]:
    """Generate domain name variations from keywords"""
    names = set()

    for kw in keywords:
        kw = kw.lower().strip()

        # Base keyword
        names.add(kw)

        # With prefixes
        for prefix in PREFIXES:
            names.add(f"{prefix}{kw}")
            names.add(f"{prefix}-{kw}")

        # With suffixes
        for suffix in SUFFIXES:
            names.add(f"{kw}{suffix}")
            names.add(f"{kw}-{suffix}")

        # With job words
        for jw in JOB_WORDS:
            names.add(f"{kw}{jw}")
            names.add(f"{jw}{kw}")
            names.add(f"{kw}-{jw}")
            names.add(f"{jw}-{kw}")

        # Country combinations
        for code, name in COUNTRY_WORDS.items():
            names.add(f"{kw}{code}")
            names.add(f"{code}{kw}")
            names.add(f"{kw}{name}")

    # Keyword combinations
    if len(keywords) >= 2:
        for combo in itertools.permutations(keywords[:3], 2):
            names.add(''.join(combo))
            names.add('-'.join(combo))

    # Filter invalid names
    valid = set()
    for name in names:
        name = name.replace('--', '-').strip('-')
        if len(name) >= 3 and len(name) <= 63:
            if name.replace('-', '').isalnum():
                valid.add(name)

    return valid

def score_domain(name: str, keywords: List[str]) -> int:
    """Score domain name quality (0-100)"""
    score = 50

    # Length (shorter is better)
    if len(name) <= 8:
        score += 20
    elif len(name) <= 12:
        score += 10
    elif len(name) > 20:
        score -= 20

    # Contains keyword
    for kw in keywords:
        if kw in name:
            score += 15
            break

    # No hyphens
    if '-' not in name:
        score += 10

    # Pronounceable (has vowels)
    vowels = sum(1 for c in name if c in 'aeiou')
    if vowels >= len(name) * 0.2:
        score += 5

    # Common suffixes
    for suffix in ['ly', 'io', 'hub', 'app']:
        if name.endswith(suffix):
            score += 5
            break

    return min(100, max(0, score))

# ============================================================
# AVAILABILITY CHECKING
# ============================================================

def check_dns(domain: str) -> bool:
    """Check if domain has DNS records (quick check)"""
    try:
        socket.gethostbyname(domain)
        return False  # Has records, likely taken
    except socket.gaierror:
        return True  # No records, might be available
    except Exception:
        return None  # Error

def check_whois(domain: str) -> Dict:
    """Check domain via whois"""
    result = {'domain': domain, 'available': None, 'error': None}

    try:
        proc = subprocess.run(
            ['whois', domain],
            capture_output=True, text=True, timeout=10
        )
        output = proc.stdout.lower()

        # Check for availability indicators
        available_patterns = ['no match', 'not found', 'no entries', 'available', 'no data found']
        taken_patterns = ['domain name:', 'registrant:', 'creation date:', 'registered on']

        for pattern in available_patterns:
            if pattern in output:
                result['available'] = True
                return result

        for pattern in taken_patterns:
            if pattern in output:
                result['available'] = False
                return result

        # Unknown
        result['available'] = None
    except subprocess.TimeoutExpired:
        result['error'] = 'timeout'
    except Exception as e:
        result['error'] = str(e)

    return result

def batch_check(names: List[str], tlds: List[str], quick: bool = True) -> List[Dict]:
    """Check multiple domains"""
    results = []

    for name in names:
        for tld in tlds:
            domain = f"{name}{tld}"
            result = {'name': name, 'tld': tld, 'domain': domain, 'available': None}

            if quick:
                # DNS check only
                result['available'] = check_dns(domain)
            else:
                # Full whois check
                whois = check_whois(domain)
                result['available'] = whois.get('available')
                result['error'] = whois.get('error')

            results.append(result)

    return results

# ============================================================
# OUTPUT
# ============================================================

def print_suggestions(names: Set[str], keywords: List[str], tlds: List[str], check: bool = False):
    """Print domain suggestions"""
    print(f"\n{'='*60}")
    print("DOMAIN BRAINSTORMER")
    print(f"{'='*60}\n")

    print(f"Keywords: {', '.join(keywords)}")
    print(f"TLDs: {', '.join(tlds)}")
    print(f"Generated: {len(names)} variations")

    # Score and sort
    scored = [(name, score_domain(name, keywords)) for name in names]
    scored.sort(key=lambda x: -x[1])

    print(f"\n{'='*60}")
    print("TOP SUGGESTIONS (by score)")
    print(f"{'='*60}\n")

    top_names = [name for name, _ in scored[:20]]

    if check:
        print("Checking availability...")
        results = batch_check(top_names, tlds[:3], quick=True)

        print(f"\n{'NAME':<25} {'DOMAIN':<35} {'STATUS':<10}")
        print("-" * 70)

        for r in results:
            if r['available'] is True:
                status = "LIKELY FREE"
            elif r['available'] is False:
                status = "TAKEN"
            else:
                status = "UNKNOWN"
            print(f"{r['name']:<25} {r['domain']:<35} {status:<10}")
    else:
        print(f"{'NAME':<25} {'SCORE':<8} EXAMPLES")
        print("-" * 70)

        for name, score in scored[:20]:
            examples = ', '.join(f"{name}{tld}" for tld in tlds[:3])
            print(f"{name:<25} {score:<8} {examples}")

    # Category suggestions
    print(f"\n{'='*60}")
    print("BY PATTERN")
    print(f"{'='*60}\n")

    patterns = {
        'Short (<=8)': [n for n in names if len(n) <= 8],
        'No hyphens': [n for n in names if '-' not in n],
        'With prefix': [n for n in names if any(n.startswith(p) for p in PREFIXES)],
        'With suffix': [n for n in names if any(n.endswith(s) for s in SUFFIXES)],
    }

    for pattern, matches in patterns.items():
        if matches:
            sample = ', '.join(sorted(matches, key=len)[:5])
            print(f"{pattern} ({len(matches)}): {sample}")

    print(f"\n{'='*60}\n")

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if not args or '-h' in args or '--help' in args:
        print(f"""
{'='*60}
DOMAIN BRAINSTORMER
{'='*60}

Usage: domain_brainstormer.py <keywords> [options]

Options:
  --tlds .com,.eu    TLDs to suggest (default: .com,.eu,.io,.co)
  --check            Check availability (DNS-based)
  --full-check       Check via whois (slower)

Examples:
  domain_brainstormer.py jobs europe
  domain_brainstormer.py "nordic work" --tlds .no,.se,.dk
  domain_brainstormer.py recruit staff --check
  domain_brainstormer.py interjob hiring --tlds .com,.eu,.ro

Prefixes: {', '.join(PREFIXES)}
Suffixes: {', '.join(SUFFIXES)}
""")
        return

    # Parse arguments
    keywords = []
    tlds = ['.com', '.eu', '.io', '.co']
    check = '--check' in args or '--full-check' in args

    for i, arg in enumerate(args):
        if arg == '--tlds' and i + 1 < len(args):
            tlds = [t.strip() if t.startswith('.') else f'.{t.strip()}' for t in args[i + 1].split(',')]
        elif not arg.startswith('-'):
            keywords.extend(arg.split())

    if not keywords:
        print("Error: No keywords provided")
        return

    # Generate names
    names = generate_variations(keywords)

    # Print suggestions
    print_suggestions(names, keywords, tlds, check)

if __name__ == '__main__':
    main()
