#!/usr/bin/env python3
"""
A2 Hosting Domain Audit - Check all 26 domains for SEO, content, and analytics
Identifies which domains are LIVE, PARKED, or INACTIVE
"""

import os
import sys
import json
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from urllib.parse import urljoin

def load_config():
    """Load configuration from ~/.a2hosting.env"""
    config = {}
    config_file = Path.home() / ".a2hosting.env"

    if not config_file.exists():
        print(f"Error: Configuration file not found: {config_file}")
        sys.exit(1)

    with open(config_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                config[key.strip()] = value.strip().strip('"\'')

    return config

def check_domain_live(domain):
    """Check if domain is live and returns HTTP status"""
    try:
        for protocol in ['https', 'http']:
            try:
                url = f"{protocol}://{domain}"
                response = requests.get(url, timeout=5, allow_redirects=True)
                return {
                    'live': True,
                    'status_code': response.status_code,
                    'protocol': protocol,
                    'title': response.text[response.text.find('<title>'):response.text.find('</title>')]
                    if '<title>' in response.text else 'N/A',
                    'size_bytes': len(response.content)
                }
            except requests.exceptions.Timeout:
                continue
    except Exception as e:
        pass
    
    return {'live': False, 'status_code': 0, 'protocol': 'N/A', 'title': 'N/A', 'size_bytes': 0}

def check_seo_files(domain):
    """Check for SEO files (robots.txt, sitemap.xml)"""
    seo_status = {
        'robots_exists': False,
        'sitemap_exists': False,
        'ssl_valid': False
    }
    
    # Check robots.txt
    try:
        response = requests.get(f"https://{domain}/robots.txt", timeout=5)
        seo_status['robots_exists'] = response.status_code == 200
    except:
        pass
    
    # Check sitemap.xml
    try:
        response = requests.get(f"https://{domain}/sitemap.xml", timeout=5)
        seo_status['sitemap_exists'] = response.status_code == 200
    except:
        pass
    
    # Check SSL
    try:
        response = requests.head(f"https://{domain}", timeout=5, verify=True)
        seo_status['ssl_valid'] = response.status_code < 400
    except:
        seo_status['ssl_valid'] = False
    
    return seo_status

def check_dns_health(domain):
    """Check DNS configuration"""
    try:
        result = subprocess.run(['nslookup', domain], capture_output=True, text=True, timeout=5)
        return 'can be resolved' in result.stdout or result.returncode == 0
    except:
        return False

def analyze_content(domain):
    """Analyze page content for job portal indicators"""
    try:
        response = requests.get(f"https://{domain}", timeout=5)
        text = response.text.lower()
        
        job_indicators = {
            'job' in text or 'job' in response.url,
            'employment' in text,
            'positions' in text,
            'hire' in text,
            'worker' in text,
            'vacancy' in text,
            'career' in text,
            'apply' in text
        }
        
        return sum(job_indicators) >= 2  # At least 2 job indicators
    except:
        return False

def classify_domain(domain, health):
    """Classify domain status"""
    if not health['live']['live']:
        return 'INACTIVE'
    elif health['content_is_job_portal']:
        return 'ACTIVE_JOB_PORTAL'
    elif health['live']['size_bytes'] < 1000:
        return 'PARKED'
    else:
        return 'ACTIVE_OTHER'

def audit_domain(domain):
    """Complete audit for one domain"""
    print(f"\n🔍 Auditing: {domain}")
    
    # Check if domain is live
    live = check_domain_live(domain)
    print(f"  Status: {live['status_code']} {'✓' if live['live'] else '✗'}")
    
    # SEO files
    seo = check_seo_files(domain)
    print(f"  robots.txt: {'✓' if seo['robots_exists'] else '✗'}")
    print(f"  sitemap.xml: {'✓' if seo['sitemap_exists'] else '✗'}")
    print(f"  SSL: {'✓' if seo['ssl_valid'] else '✗'}")
    
    # DNS
    dns_ok = check_dns_health(domain)
    print(f"  DNS: {'✓' if dns_ok else '✗'}")
    
    # Content analysis
    is_job = analyze_content(domain) if live['live'] else False
    print(f"  Job Portal: {'✓' if is_job else '✗'}")
    
    # Classify
    health = {
        'live': live,
        'seo': seo,
        'dns': dns_ok,
        'content_is_job_portal': is_job
    }
    status = classify_domain(domain, health)
    print(f"  ➜ Status: {status}")
    
    return {
        'domain': domain,
        'status': status,
        'health': health,
        'timestamp': datetime.now().isoformat()
    }

def main():
    # 26 domains to audit
    domains = [
        'mivromania.com', 'mivromania.info', 'mivromania.online',
        'cumparlegume.com', 'nepalezi.com', 'interjob.ro', 'ajwang.org', 'weddnesday.org',
        'aluminumrecyclehub.com', 'expatsinromania.org', 'seicarescu.com',
        'factoryjobs.eu', 'buildjobs.eu', 'careworkers.eu', 'horecaworkers.eu',
        'meatworkers.eu', 'electricjobs.eu', 'mechanicjobs.eu', 'farmworkers.eu',
        'horecaworkers2026.com', 'horecaworkers2026.eu', 'horecaworkers2026.online',
        'internaltransfers.eu', 'bppltd.co.uk', 'warehouseworkers.eu', 'haritina.com'
    ]
    
    results = []
    
    print("=" * 70)
    print("A2 HOSTING DOMAIN AUDIT - Portfolio Health Check")
    print("=" * 70)
    
    for domain in domains:
        try:
            result = audit_domain(domain)
            results.append(result)
        except Exception as e:
            print(f"  Error: {e}")
            results.append({
                'domain': domain,
                'status': 'ERROR',
                'error': str(e)
            })
    
    # Summary Report
    print("\n" + "=" * 70)
    print("SUMMARY REPORT")
    print("=" * 70)
    
    active_job = sum(1 for r in results if r['status'] == 'ACTIVE_JOB_PORTAL')
    active_other = sum(1 for r in results if r['status'] == 'ACTIVE_OTHER')
    parked = sum(1 for r in results if r['status'] == 'PARKED')
    inactive = sum(1 for r in results if r['status'] == 'INACTIVE')
    
    print(f"\n📊 Status Breakdown:")
    print(f"  Active Job Portals: {active_job}")
    print(f"  Active Other: {active_other}")
    print(f"  Parked: {parked}")
    print(f"  Inactive: {inactive}")
    print(f"  Total: {len(results)}")
    
    # List inactive domains (candidates for renewal decision)
    inactive_domains = [r['domain'] for r in results if r['status'] == 'INACTIVE']
    if inactive_domains:
        print(f"\n⚠️  Inactive Domains (consider renewal):")
        for domain in inactive_domains:
            print(f"    - {domain}")
    
    # Save detailed report
    report_file = Path.home() / f"domain_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n✓ Detailed report saved to: {report_file}")

if __name__ == '__main__':
    main()
