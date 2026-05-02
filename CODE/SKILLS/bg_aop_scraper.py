#!/usr/bin/env python3
"""
Bulgarian AOP Scraper Skill

Scrapes Bulgarian Public Procurement notices from www.aop.bg
Uses async httpx for 3-5x faster scraping.

Usage:
    python3 bg_aop_scraper.py --status
    python3 bg_aop_scraper.py --test
    python3 bg_aop_scraper.py --full --concurrency 10
"""
import subprocess
import sys
import argparse

SCRAPER_PATH = "/opt/ACTIVE/EU_FUNDING/CODE/SCRAPERS/BULGARIA/aop_scraper_async.py"

def main():
    parser = argparse.ArgumentParser(description='Bulgarian AOP Procurement Scraper')
    parser.add_argument('--status', action='store_true', help='Show status')
    parser.add_argument('--test', action='store_true', help='Test with 5 pages')
    parser.add_argument('--full', action='store_true', help='Full scrape (~43K notices)')
    parser.add_argument('--concurrency', type=int, default=10, help='Concurrent requests')
    parser.add_argument('--db', action='store_true', help='Save to PostgreSQL')
    parser.add_argument('--resume', action='store_true', help='Resume from last page')
    args = parser.parse_args()
    
    cmd = [sys.executable, SCRAPER_PATH]
    
    if args.status:
        cmd.append('--status')
    elif args.test:
        cmd.extend(['--test', '--limit', '5', '--concurrency', str(args.concurrency)])
    elif args.full:
        cmd.extend(['--all', '--concurrency', str(args.concurrency)])
        if args.db:
            cmd.append('--db')
        if args.resume:
            cmd.append('--resume')
    else:
        parser.print_help()
        return
    
    subprocess.run(cmd)

if __name__ == '__main__':
    main()
