#!/usr/bin/env python3
"""
A2 Hosting Analytics Tracker - Monitor domain traffic and activity
Parses access logs to track visitors, page views, and engagement per domain
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

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

def parse_access_log(log_content):
    """Parse Apache/Nginx access logs"""
    # Apache Combined Log Format: IP timestamp method path http_version status bytes referer user_agent
    pattern = r'(\d+\.\d+\.\d+\.\d+)\s+\S+\s+\S+\s+\[(.*?)\]\s+"([A-Z]+)\s+(.*?)\s+HTTP/[\d\.]+"'
    
    stats = {
        'total_requests': 0,
        'unique_ips': set(),
        'page_views': defaultdict(int),
        'status_codes': defaultdict(int),
        'referers': defaultdict(int),
        'traffic_over_time': defaultdict(int),
    }
    
    for line in log_content.split('\n'):
        match = re.search(pattern, line)
        if match:
            ip, timestamp, method, path = match.groups()
            
            # Parse timestamp
            try:
                dt = datetime.strptime(timestamp, '%d/%b/%Y:%H:%M:%S %z')
                day_key = dt.strftime('%Y-%m-%d')
                stats['traffic_over_time'][day_key] += 1
            except:
                pass
            
            stats['total_requests'] += 1
            stats['unique_ips'].add(ip)
            
            # Track page views (only GET requests to HTML/index)
            if method == 'GET' and (path.endswith('.html') or path == '/' or path.endswith('/')):
                stats['page_views'][path] += 1
    
    return {
        'total_requests': stats['total_requests'],
        'unique_visitors': len(stats['unique_ips']),
        'page_views': dict(stats['page_views']),
        'most_visited_pages': sorted(stats['page_views'].items(), key=lambda x: x[1], reverse=True)[:5],
        'daily_traffic': dict(stats['traffic_over_time']),
    }

def check_domain_logs(domain, days=7):
    """Check access logs for domain (requires SSH access to A2)"""
    # This would require SSH to A2 server
    # For now, return a template
    return {
        'domain': domain,
        'note': 'Requires SSH access to parse live logs',
        'template': {
            'total_requests': 'N/A',
            'unique_visitors': 'N/A',
            'top_pages': 'N/A'
        }
    }

def generate_analytics_report(domains, config):
    """Generate analytics report for domains"""
    
    print("=" * 70)
    print("DOMAIN ANALYTICS REPORT")
    print("=" * 70)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'domains_analyzed': len(domains),
        'summary': {},
        'details': {}
    }
    
    for domain in domains:
        print(f"\n📊 {domain}")
        print("-" * 50)
        
        # For now, show what would be tracked
        analytics = check_domain_logs(domain)
        report['details'][domain] = analytics
        
        print(f"  Status: Requires log access")
        print(f"  To enable: SSH to A2 server and parse access logs")
        print(f"  Path: /home/username/logs/{domain}/access.log")
    
    return report

def main():
    parser_config = load_config()
    
    # Default domains
    default_domains = [
        'factoryjobs.eu', 'buildjobs.eu', 'careworkers.eu', 'horecaworkers.eu',
        'meatworkers.eu', 'electricjobs.eu', 'mechanicjobs.eu', 'farmworkers.eu',
        'warehouseworkers.eu', 'mivromania.com'
    ]
    
    if len(sys.argv) > 1:
        domains = sys.argv[1:]
    else:
        domains = default_domains
    
    print("\n" + "=" * 70)
    print("A2 HOSTING ANALYTICS - Domain Traffic Monitoring")
    print("=" * 70)
    
    for domain in domains:
        print(f"\n🔍 Analyzing: {domain}")
        analytics = check_domain_logs(domain)
        
        print(f"  Set up log analysis:")
        print(f"    1. SSH to A2 server")
        print(f"    2. Check logs at: /home/username/logs/{domain}/access.log")
        print(f"    3. Monitor daily: tail -f /home/username/logs/{domain}/access.log")
    
    print("\n" + "=" * 70)
    print("\n💡 To track analytics, you need:")
    print("  1. Raw access logs from A2 (via SSH)")
    print("  2. Google Analytics integration (add tracking ID to HTML)")
    print("  3. Or: Use the catalog-generator to add GA tracking to catalogs")
    print("\n" + "=" * 70)

class DomainAnalytics:
    """Class to track domain analytics over time"""
    
    def __init__(self, domain):
        self.domain = domain
        self.visitors = defaultdict(int)  # date -> count
        self.pageviews = defaultdict(int)
        self.referrers = defaultdict(int)
        self.created = datetime.now()
    
    def add_visit(self, date, pages=1, referrer=None):
        """Record a visit"""
        date_key = date.strftime('%Y-%m-%d')
        self.visitors[date_key] += 1
        self.pageviews[date_key] += pages
        if referrer:
            self.referrers[referrer] += 1
    
    def get_summary(self):
        """Get analytics summary"""
        total_visitors = sum(self.visitors.values())
        total_pageviews = sum(self.pageviews.values())
        days_active = len(self.visitors)
        
        return {
            'domain': self.domain,
            'total_visitors': total_visitors,
            'total_pageviews': total_pageviews,
            'days_with_traffic': days_active,
            'avg_visitors_per_day': total_visitors / days_active if days_active > 0 else 0,
            'bounce_rate': 'N/A',  # Requires more detail
            'top_referrers': dict(sorted(self.referrers.items(), key=lambda x: x[1], reverse=True)[:5])
        }

if __name__ == '__main__':
    main()
