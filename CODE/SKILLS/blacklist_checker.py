#!/usr/bin/env python3
"""
Blacklist Checker - Check if domains/IPs are on email blacklists
Usage: python3 blacklist_checker.py [domain|ip] [--all-domains]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import socket
import subprocess
import json
from datetime import datetime
from typing import Dict, List, Optional

# ============================================================
# CONFIGURATION
# ============================================================

# Major DNS-based blacklists
DNSBL_SERVERS = [
    # Spamhaus (most important)
    ('zen.spamhaus.org', 'Spamhaus ZEN'),
    ('sbl.spamhaus.org', 'Spamhaus SBL'),
    ('xbl.spamhaus.org', 'Spamhaus XBL'),
    ('pbl.spamhaus.org', 'Spamhaus PBL'),

    # Spamcop
    ('bl.spamcop.net', 'SpamCop'),

    # Barracuda
    ('b.barracudacentral.org', 'Barracuda'),

    # SORBS
    ('dnsbl.sorbs.net', 'SORBS'),

    # Other common ones
    ('cbl.abuseat.org', 'CBL Abuseat'),
    ('dnsbl-1.uceprotect.net', 'UCEPROTECT L1'),
    ('dnsbl-2.uceprotect.net', 'UCEPROTECT L2'),
    ('psbl.surriel.com', 'PSBL'),
    ('spam.dnsbl.anonmails.de', 'Anonmails'),
]

# Domain reputation lists
DOMAIN_BL = [
    ('dbl.spamhaus.org', 'Spamhaus DBL'),
    ('multi.surbl.org', 'SURBL'),
    ('black.uribl.com', 'URIBL Black'),
]

# Brevo domains to check
BREVO_DOMAINS = [
    'buildjobs.eu',
    'factoryjobs.eu',
    'careworkers.eu',
    'mivromania.info',
    'mivromania.online',
    'cifn.info',
    'interjob.ro',
    'nepalezi.com',
]

# ============================================================
# DNS LOOKUPS
# ============================================================

def reverse_ip(ip: str) -> str:
    """Reverse IP for DNSBL lookup"""
    parts = ip.split('.')
    return '.'.join(reversed(parts))

def check_ip_blacklist(ip: str, dnsbl: str) -> bool:
    """Check if IP is listed in a DNSBL"""
    try:
        query = f"{reverse_ip(ip)}.{dnsbl}"
        socket.gethostbyname(query)
        return True  # Listed
    except socket.gaierror:
        return False  # Not listed
    except Exception:
        return False

def check_domain_blacklist(domain: str, dnsbl: str) -> bool:
    """Check if domain is listed in a domain blacklist"""
    try:
        query = f"{domain}.{dnsbl}"
        socket.gethostbyname(query)
        return True  # Listed
    except socket.gaierror:
        return False  # Not listed
    except Exception:
        return False

def get_mx_records(domain: str) -> List[str]:
    """Get MX records for a domain"""
    mx_records = []
    try:
        result = subprocess.run(
            ['dig', '+short', 'MX', domain],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if line:
                parts = line.split()
                if len(parts) >= 2:
                    mx_records.append(parts[1].rstrip('.'))
    except Exception:
        pass
    return mx_records

def get_ip_for_domain(domain: str) -> Optional[str]:
    """Get IP address for a domain"""
    try:
        return socket.gethostbyname(domain)
    except Exception:
        return None

def get_spf_record(domain: str) -> Optional[str]:
    """Get SPF record for a domain"""
    try:
        result = subprocess.run(
            ['dig', '+short', 'TXT', domain],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'v=spf1' in line.lower():
                return line.strip('"')
    except Exception:
        pass
    return None

def get_dkim_record(domain: str, selector: str = 'brevo1._domainkey') -> Optional[str]:
    """Get DKIM record for a domain"""
    try:
        result = subprocess.run(
            ['dig', '+short', 'CNAME', f'{selector}.{domain}'],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip() or None
    except Exception:
        return None

def get_dmarc_record(domain: str) -> Optional[str]:
    """Get DMARC record for a domain"""
    try:
        result = subprocess.run(
            ['dig', '+short', 'TXT', f'_dmarc.{domain}'],
            capture_output=True, text=True, timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            if 'v=dmarc1' in line.lower():
                return line.strip('"')
    except Exception:
        pass
    return None

# ============================================================
# CHECKING
# ============================================================

def check_ip(ip: str) -> Dict:
    """Full blacklist check for an IP"""
    result = {
        'ip': ip,
        'checked_at': datetime.now().isoformat(),
        'blacklists': [],
        'clean': True,
        'total_checked': len(DNSBL_SERVERS),
    }

    for dnsbl, name in DNSBL_SERVERS:
        listed = check_ip_blacklist(ip, dnsbl)
        if listed:
            result['blacklists'].append({'list': name, 'dnsbl': dnsbl})
            result['clean'] = False

    result['listed_count'] = len(result['blacklists'])
    return result

def check_domain(domain: str) -> Dict:
    """Full check for a domain"""
    result = {
        'domain': domain,
        'checked_at': datetime.now().isoformat(),
        'ip': None,
        'mx_records': [],
        'spf': None,
        'dkim': None,
        'dmarc': None,
        'ip_blacklists': [],
        'domain_blacklists': [],
        'clean': True,
        'issues': [],
    }

    # Get IP
    result['ip'] = get_ip_for_domain(domain)

    # Get MX records
    result['mx_records'] = get_mx_records(domain)

    # Get authentication records
    result['spf'] = get_spf_record(domain)
    result['dkim'] = get_dkim_record(domain)
    result['dmarc'] = get_dmarc_record(domain)

    # Check authentication
    if not result['spf']:
        result['issues'].append('Missing SPF record')
    if not result['dkim']:
        result['issues'].append('Missing DKIM (brevo1._domainkey)')
    if not result['dmarc']:
        result['issues'].append('Missing DMARC record')

    # Check domain blacklists
    for dnsbl, name in DOMAIN_BL:
        if check_domain_blacklist(domain, dnsbl):
            result['domain_blacklists'].append({'list': name, 'dnsbl': dnsbl})
            result['clean'] = False

    # Check IP blacklists
    if result['ip']:
        for dnsbl, name in DNSBL_SERVERS[:5]:  # Check top 5 for IP
            if check_ip_blacklist(result['ip'], dnsbl):
                result['ip_blacklists'].append({'list': name, 'dnsbl': dnsbl})
                result['clean'] = False

    return result

def check_all_domains() -> List[Dict]:
    """Check all Brevo domains"""
    results = []
    for domain in BREVO_DOMAINS:
        print(f"  Checking {domain}...")
        results.append(check_domain(domain))
    return results

# ============================================================
# OUTPUT
# ============================================================

def print_ip_result(result: Dict):
    """Print IP check result"""
    status = "CLEAN" if result['clean'] else "LISTED"
    print(f"\n  IP: {result['ip']} - {status}")
    print(f"  Checked {result['total_checked']} blacklists")

    if result['blacklists']:
        print(f"\n  BLACKLISTED ON:")
        for bl in result['blacklists']:
            print(f"    - {bl['list']} ({bl['dnsbl']})")

def print_domain_result(result: Dict):
    """Print domain check result"""
    status = "CLEAN" if result['clean'] else "ISSUES"
    print(f"\n  {result['domain']}: {status}")
    print(f"    IP: {result['ip'] or 'N/A'}")
    print(f"    MX: {', '.join(result['mx_records'][:2]) or 'None'}")

    # Authentication status
    spf_ok = 'OK' if result['spf'] else 'MISSING'
    dkim_ok = 'OK' if result['dkim'] else 'MISSING'
    dmarc_ok = 'OK' if result['dmarc'] else 'MISSING'
    print(f"    Auth: SPF={spf_ok}, DKIM={dkim_ok}, DMARC={dmarc_ok}")

    if result['domain_blacklists']:
        print(f"    DOMAIN BLACKLISTED:")
        for bl in result['domain_blacklists']:
            print(f"      - {bl['list']}")

    if result['ip_blacklists']:
        print(f"    IP BLACKLISTED:")
        for bl in result['ip_blacklists']:
            print(f"      - {bl['list']}")

    if result['issues']:
        print(f"    ISSUES:")
        for issue in result['issues']:
            print(f"      - {issue}")

def print_summary(results: List[Dict]):
    """Print summary of all domain checks"""
    print(f"\n{'='*60}")
    print(f"BLACKLIST CHECKER SUMMARY")
    print(f"{'='*60}")

    clean = sum(1 for r in results if r['clean'] and not r['issues'])
    issues = sum(1 for r in results if r['issues'])
    blacklisted = sum(1 for r in results if r['domain_blacklists'] or r['ip_blacklists'])

    print(f"\n  Total domains: {len(results)}")
    print(f"  Clean:         {clean}")
    print(f"  Auth issues:   {issues}")
    print(f"  Blacklisted:   {blacklisted}")

    # Table
    print(f"\n  {'DOMAIN':<25} {'IP':<15} {'SPF':>4} {'DKIM':>5} {'DMARC':>6} {'BL':>3}")
    print(f"  {'-'*60}")

    for r in results:
        spf = 'OK' if r['spf'] else '-'
        dkim = 'OK' if r['dkim'] else '-'
        dmarc = 'OK' if r['dmarc'] else '-'
        bl = len(r['domain_blacklists']) + len(r['ip_blacklists'])
        bl_str = str(bl) if bl > 0 else 'OK'

        print(f"  {r['domain']:<25} {r['ip'] or 'N/A':<15} {spf:>4} {dkim:>5} {dmarc:>6} {bl_str:>3}")

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if '-h' in args or '--help' in args:
        print(f"""
{'='*60}
BLACKLIST CHECKER
{'='*60}

Usage: blacklist_checker.py [target] [options]

Targets:
  <domain>       Check a specific domain
  <ip>           Check a specific IP address
  --all-domains  Check all Brevo domains

Options:
  --json         Output as JSON

Brevo domains: {', '.join(BREVO_DOMAINS)}

Checks:
  - DNS blacklists (Spamhaus, SpamCop, Barracuda, etc.)
  - Domain blacklists (Spamhaus DBL, SURBL, URIBL)
  - SPF, DKIM, DMARC records

Examples:
  blacklist_checker.py interjob.ro
  blacklist_checker.py 192.168.1.1
  blacklist_checker.py --all-domains
""")
        return

    as_json = '--json' in args
    all_domains = '--all-domains' in args

    print(f"\n{'='*60}")
    print(f"BLACKLIST CHECKER - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*60}")

    if all_domains:
        print(f"\nChecking {len(BREVO_DOMAINS)} Brevo domains...")
        results = check_all_domains()

        if as_json:
            print(json.dumps(results, indent=2))
        else:
            for result in results:
                print_domain_result(result)
            print_summary(results)

    elif args and not args[0].startswith('-'):
        target = args[0]

        # Detect if IP or domain
        try:
            socket.inet_aton(target)
            is_ip = True
        except Exception:
            is_ip = False

        if is_ip:
            print(f"\nChecking IP: {target}")
            result = check_ip(target)
            if as_json:
                print(json.dumps(result, indent=2))
            else:
                print_ip_result(result)
        else:
            print(f"\nChecking domain: {target}")
            result = check_domain(target)
            if as_json:
                print(json.dumps(result, indent=2))
            else:
                print_domain_result(result)

    else:
        # Default: check all Brevo domains
        print(f"\nNo target specified. Checking all Brevo domains...")
        results = check_all_domains()

        if as_json:
            print(json.dumps(results, indent=2))
        else:
            for result in results:
                print_domain_result(result)
            print_summary(results)

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
