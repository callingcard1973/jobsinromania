#!/usr/bin/env python3
"""
A2 Hosting Portfolio Report - Generate comprehensive health report for all 26 domains
Creates CSV/JSON export of domain status, renewals, costs, and recommendations
"""

import os
import json
import csv
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Your 26 domains with expiration dates
DOMAINS_PORTFOLIO = [
    {'name': 'mivromania.com', 'expires': '2026-06-19', 'registered': '2025-06-19', 'type': 'brand', 'cost': 10.88},
    {'name': 'mivromania.info', 'expires': '2026-06-19', 'registered': '2025-06-19', 'type': 'brand', 'cost': 22.69},
    {'name': 'mivromania.online', 'expires': '2026-06-20', 'registered': '2025-06-19', 'type': 'brand', 'cost': 26.97},
    {'name': 'cumparlegume.com', 'expires': '2026-07-29', 'registered': '2023-07-29', 'type': 'niche', 'cost': 10.88},
    {'name': 'nepalezi.com', 'expires': '2026-07-31', 'registered': '2025-07-31', 'type': 'niche', 'cost': 10.88},
    {'name': 'interjob.ro', 'expires': '2026-08-10', 'registered': '2025-08-10', 'type': 'job', 'cost': 10.46},
    {'name': 'ajwang.org', 'expires': '2026-10-10', 'registered': '2025-10-10', 'type': 'niche', 'cost': 10.53},
    {'name': 'weddnesday.org', 'expires': '2026-10-28', 'registered': '2025-10-28', 'type': 'niche', 'cost': 10.53},
    {'name': 'aluminumrecyclehub.com', 'expires': '2026-11-16', 'registered': '2023-11-16', 'type': 'niche', 'cost': 10.88},
    {'name': 'expatsinromania.org', 'expires': '2026-11-17', 'registered': '2023-11-17', 'type': 'niche', 'cost': 10.53},
    {'name': 'seicarescu.com', 'expires': '2026-11-21', 'registered': '2021-11-21', 'type': 'niche', 'cost': 10.88},
    {'name': 'factoryjobs.eu', 'expires': '2026-12-23', 'registered': '2025-12-23', 'type': 'job', 'cost': 6.41},
    {'name': 'buildjobs.eu', 'expires': '2026-12-23', 'registered': '2025-12-23', 'type': 'job', 'cost': 6.41},
    {'name': 'careworkers.eu', 'expires': '2026-12-23', 'registered': '2025-12-23', 'type': 'job', 'cost': 6.41},
    {'name': 'horecaworkers.eu', 'expires': '2027-01-13', 'registered': '2026-01-12', 'type': 'job', 'cost': 6.41},
    {'name': 'meatworkers.eu', 'expires': '2027-01-13', 'registered': '2026-01-12', 'type': 'job', 'cost': 6.41},
    {'name': 'electricjobs.eu', 'expires': '2027-01-13', 'registered': '2026-01-12', 'type': 'job', 'cost': 6.41},
    {'name': 'mechanicjobs.eu', 'expires': '2027-01-13', 'registered': '2026-01-12', 'type': 'job', 'cost': 6.41},
    {'name': 'farmworkers.eu', 'expires': '2027-01-13', 'registered': '2026-01-12', 'type': 'job', 'cost': 6.41},
    {'name': 'horecaworkers2026.com', 'expires': '2027-01-24', 'registered': '2026-01-24', 'type': 'job', 'cost': 10.88},
    {'name': 'horecaworkers2026.eu', 'expires': '2027-01-24', 'registered': '2026-01-23', 'type': 'job', 'cost': 6.41},
    {'name': 'horecaworkers2026.online', 'expires': '2027-01-24', 'registered': '2026-01-24', 'type': 'job', 'cost': 26.97},
    {'name': 'internaltransfers.eu', 'expires': '2027-02-05', 'registered': '2026-02-05', 'type': 'job', 'cost': 6.41},
    {'name': 'bppltd.co.uk', 'expires': '2027-02-19', 'registered': '2026-02-19', 'type': 'niche', 'cost': 6.27},
    {'name': 'warehouseworkers.eu', 'expires': '2027-12-29', 'registered': '2025-12-28', 'type': 'job', 'cost': 6.41},
    {'name': 'haritina.com', 'expires': '2030-06-20', 'registered': '2025-06-20', 'type': 'investment', 'cost': 10.88},
]

def days_until_expiration(expiry_date_str):
    """Calculate days until domain expiration"""
    expires = datetime.strptime(expiry_date_str, '%Y-%m-%d')
    days = (expires - datetime.now()).days
    return days

def categorize_urgency(days_left):
    """Categorize renewal urgency"""
    if days_left < 30:
        return 'URGENT'
    elif days_left < 90:
        return 'SOON'
    elif days_left < 180:
        return 'NORMAL'
    else:
        return 'OK'

def generate_portfolio_report():
    """Generate comprehensive portfolio report"""
    
    now = datetime.now()
    
    # Calculate statistics
    total_domains = len(DOMAINS_PORTFOLIO)
    total_annual_cost = sum(d['cost'] for d in DOMAINS_PORTFOLIO)
    job_portals = sum(1 for d in DOMAINS_PORTFOLIO if d['type'] == 'job')
    brand_domains = sum(1 for d in DOMAINS_PORTFOLIO if d['type'] == 'brand')
    
    # Group by expiration windows
    urgent = []
    soon = []
    normal = []
    ok = []
    
    for domain in DOMAINS_PORTFOLIO:
        days_left = days_until_expiration(domain['expires'])
        urgency = categorize_urgency(days_left)
        domain['days_until_expiry'] = days_left
        domain['urgency'] = urgency
        
        if urgency == 'URGENT':
            urgent.append(domain)
        elif urgency == 'SOON':
            soon.append(domain)
        elif urgency == 'NORMAL':
            normal.append(domain)
        else:
            ok.append(domain)
    
    # Print Report
    print("=" * 80)
    print("A2 HOSTING DOMAIN PORTFOLIO REPORT")
    print(f"Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    print("\n📊 PORTFOLIO SUMMARY")
    print("-" * 80)
    print(f"Total Domains: {total_domains}")
    print(f"Job Portals: {job_portals}")
    print(f"Brand Domains: {brand_domains}")
    print(f"Niche/Other: {total_domains - job_portals - brand_domains}")
    print(f"Annual Renewal Cost: ${total_annual_cost:.2f}")
    print(f"Average Cost per Domain: ${total_annual_cost / total_domains:.2f}")
    
    print("\n🔴 URGENT RENEWALS (< 30 days)")
    print("-" * 80)
    if urgent:
        for d in sorted(urgent, key=lambda x: x['days_until_expiry']):
            print(f"  {d['name']:<30} Expires in {d['days_until_expiry']} days ({d['expires']}) - ${d['cost']}")
    else:
        print("  None")
    
    print("\n🟡 SOON (30-90 days)")
    print("-" * 80)
    if soon:
        for d in sorted(soon, key=lambda x: x['days_until_expiry']):
            print(f"  {d['name']:<30} Expires in {d['days_until_expiry']} days ({d['expires']}) - ${d['cost']}")
    else:
        print("  None")
    
    print("\n🟢 NORMAL (90-180 days)")
    print("-" * 80)
    if normal:
        for d in sorted(normal, key=lambda x: x['days_until_expiry']):
            print(f"  {d['name']:<30} Expires in {d['days_until_expiry']} days ({d['expires']}) - ${d['cost']}")
    else:
        print("  None")
    
    print("\n✅ OK (180+ days)")
    print("-" * 80)
    if ok:
        for d in sorted(ok, key=lambda x: x['days_until_expiry'], reverse=True):
            print(f"  {d['name']:<30} Expires in {d['days_until_expiry']} days ({d['expires']}) - ${d['cost']}")
    else:
        print("  None")
    
    print("\n📋 RECOMMENDATIONS")
    print("-" * 80)
    print(f"1. Renew {len(urgent)} urgent domains immediately")
    print(f"2. Set renewal reminders for {len(soon)} domains expiring soon")
    print(f"3. Review inactive domains (audit with: a2_domain_audit.py)")
    print(f"4. Deploy catalogs to job portals (use: catalog-generator)")
    print(f"5. Monitor SEO health (use: a2_seo_monitor.py)")
    
    # Save to CSV
    csv_file = Path.home() / f"domain_portfolio_{now.strftime('%Y%m%d_%H%M%S')}.csv"
    with open(csv_file, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['name', 'expires', 'registered', 'type', 'cost', 'days_until_expiry', 'urgency'])
        writer.writeheader()
        for domain in sorted(DOMAINS_PORTFOLIO, key=lambda x: x['days_until_expiry']):
            writer.writerow(domain)
    
    print(f"\n✓ Portfolio saved to: {csv_file}")
    
    # Save to JSON
    json_file = Path.home() / f"domain_portfolio_{now.strftime('%Y%m%d_%H%M%S')}.json"
    with open(json_file, 'w') as f:
        json.dump({
            'timestamp': now.isoformat(),
            'summary': {
                'total_domains': total_domains,
                'total_annual_cost': total_annual_cost,
                'job_portals': job_portals,
                'brand_domains': brand_domains,
                'urgent_renewals': len(urgent),
            },
            'domains': sorted(DOMAINS_PORTFOLIO, key=lambda x: x['days_until_expiry'])
        }, f, indent=2)
    
    print(f"✓ JSON export saved to: {json_file}")
    
    return {
        'total_domains': total_domains,
        'total_cost': total_annual_cost,
        'urgent': len(urgent),
        'soon': len(soon),
        'files': [str(csv_file), str(json_file)]
    }

def main():
    print("\n")
    result = generate_portfolio_report()
    
    print("\n" + "=" * 80)
    print("NEXT ACTIONS:")
    print("=" * 80)
    print(f"1. Set calendar reminders for {result['urgent']} urgent renewals")
    print("2. Run: python a2_domain_audit.py")
    print("3. Run: python a2_seo_monitor.py factoryjobs.eu buildjobs.eu ...")
    print("4. Generate catalogs: catalog-generator")
    print("5. Deploy to A2: bulk_upload.sh")
    print("=" * 80)

if __name__ == '__main__':
    main()
