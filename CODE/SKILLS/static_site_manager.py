#!/usr/bin/env python3
"""
Static Site Manager — Edit and deploy HTML sites

Manages static HTML/CSS/JS sites for A2 Hosting.

Usage:
    python3 static_site_manager.py list SITE          # List all HTML files
    python3 static_site_manager.py show SITE PAGE     # Show page content
    python3 static_site_manager.py deploy SITE        # Deploy to A2 Hosting
    python3 static_site_manager.py status SITE        # Check deployed status

Sites: agroevolution, internaltransfers, factoryjobs, weddnesday

Example:
    python3 static_site_manager.py list agroevolution
    python3 static_site_manager.py deploy agroevolution

# [AI: Claude Code]
Author: INTERJOB SOLUTIONS EUROPE SRL
"""

import os
import sys
import ssl
import json
import argparse
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime

# Site configurations
SITES = {
    'agroevolution': {
        'local': '/opt/ACTIVE/WEB/WEBSITES/AGROEVOLUTION.COM/static',
        'remote': '/home/loaiidil/agroevolution.com',
        'domain': 'agroevolution.com',
        'description': 'Agricultural land marketplace'
    },
    'internaltransfers': {
        'local': '/opt/ACTIVE/INFRA/SKILLS/output',
        'remote': '/home/loaiidil/internaltransfers.eu',
        'domain': 'internaltransfers.eu',
        'description': 'Multilingual job portal'
    },
    'factoryjobs': {
        'local': '/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu',
        'remote': '/home/loaiidil/jobnetwork',
        'domain': 'factoryjobs.eu',
        'description': 'Factory jobs portal'
    },
    'weddnesday': {
        'local': '/opt/ACTIVE/WEB/WEBSITES/weddnesday.org',
        'remote': '/home/loaiidil/weddnesday.org',
        'domain': 'weddnesday.org',
        'description': 'Wedding services'
    }
}

# A2 Hosting cPanel API
CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_PORT = 2083
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = "30GYXYLTECIUBV36ND4B20VRQUZ51ZA4"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE


def list_files(site_name: str) -> list:
    """List all HTML/CSS/JS files in site."""
    if site_name not in SITES:
        print(f"[ERROR] Unknown site: {site_name}")
        print(f"Available: {', '.join(SITES.keys())}")
        return []

    local_path = SITES[site_name]['local']
    if not os.path.exists(local_path):
        print(f"[ERROR] Path not found: {local_path}")
        return []

    files = []
    for root, dirs, filenames in os.walk(local_path):
        # Skip hidden directories
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for f in filenames:
            if f.endswith(('.html', '.css', '.js', '.json')):
                rel_path = os.path.relpath(os.path.join(root, f), local_path)
                full_path = os.path.join(root, f)
                size = os.path.getsize(full_path)
                mtime = datetime.fromtimestamp(os.path.getmtime(full_path))
                files.append({
                    'path': rel_path,
                    'size': size,
                    'modified': mtime.strftime('%Y-%m-%d %H:%M')
                })

    return sorted(files, key=lambda x: x['path'])


def show_page(site_name: str, page_name: str) -> str:
    """Show content of a page."""
    if site_name not in SITES:
        print(f"[ERROR] Unknown site: {site_name}")
        return ""

    local_path = os.path.join(SITES[site_name]['local'], page_name)
    if not os.path.exists(local_path):
        print(f"[ERROR] File not found: {local_path}")
        return ""

    with open(local_path, 'r', encoding='utf-8') as f:
        return f.read()


def deploy_site(site_name: str, dry_run: bool = False) -> bool:
    """Deploy site to A2 Hosting via rsync over SSH."""
    if site_name not in SITES:
        print(f"[ERROR] Unknown site: {site_name}")
        return False

    site = SITES[site_name]
    local_path = site['local']
    remote_path = site['remote']

    if not os.path.exists(local_path):
        print(f"[ERROR] Local path not found: {local_path}")
        return False

    # Build rsync command
    ssh_cmd = f"ssh -p 7822 -o StrictHostKeyChecking=no"
    rsync_cmd = [
        'rsync', '-avz', '--delete',
        '-e', ssh_cmd,
        f'{local_path}/',
        f'{CPANEL_USER}@{CPANEL_HOST}:{remote_path}/'
    ]

    if dry_run:
        rsync_cmd.insert(2, '--dry-run')
        print(f"[DRY RUN] Would execute: {' '.join(rsync_cmd)}")

    print(f"[DEPLOY] {site_name} -> {site['domain']}")
    print(f"  Local:  {local_path}")
    print(f"  Remote: {remote_path}")

    try:
        result = subprocess.run(rsync_cmd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            print(f"[OK] Deployed successfully")
            if result.stdout:
                # Count files
                lines = [l for l in result.stdout.split('\n') if l and not l.startswith('sending')]
                print(f"  Files synced: {len(lines)}")
            return True
        else:
            print(f"[ERROR] rsync failed: {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        print(f"[ERROR] Deploy timed out")
        return False
    except Exception as e:
        print(f"[ERROR] Deploy failed: {e}")
        return False


def check_status(site_name: str) -> dict:
    """Check deployed site status via HTTP."""
    if site_name not in SITES:
        print(f"[ERROR] Unknown site: {site_name}")
        return {}

    site = SITES[site_name]
    domain = site['domain']

    status = {
        'site': site_name,
        'domain': domain,
        'pages': {}
    }

    # Check main pages
    pages_to_check = ['/', '/index.html', '/about.html', '/contact.html']

    for page in pages_to_check:
        url = f"https://{domain}{page}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                status['pages'][page] = {
                    'status': resp.status,
                    'size': len(resp.read())
                }
        except urllib.error.HTTPError as e:
            status['pages'][page] = {'status': e.code, 'error': str(e)}
        except Exception as e:
            status['pages'][page] = {'status': 0, 'error': str(e)[:50]}

    return status


def main():
    parser = argparse.ArgumentParser(description='Static Site Manager')
    parser.add_argument('command', choices=['list', 'show', 'deploy', 'status', 'sites'],
                        help='Command to run')
    parser.add_argument('site', nargs='?', help='Site name')
    parser.add_argument('page', nargs='?', help='Page name (for show command)')
    parser.add_argument('--dry-run', action='store_true', help='Dry run deploy')

    args = parser.parse_args()

    if args.command == 'sites':
        print("\n=== AVAILABLE SITES ===\n")
        for name, config in SITES.items():
            print(f"{name:20} {config['domain']:30} {config['description']}")
        return

    if not args.site:
        print("[ERROR] Site name required")
        parser.print_help()
        return

    if args.command == 'list':
        files = list_files(args.site)
        if files:
            print(f"\n=== {args.site.upper()} FILES ===\n")
            print(f"{'Path':<40} {'Size':>8} {'Modified':>16}")
            print("-" * 66)
            for f in files:
                size_str = f"{f['size']:,}" if f['size'] < 10000 else f"{f['size']//1024}K"
                print(f"{f['path']:<40} {size_str:>8} {f['modified']:>16}")
            print(f"\nTotal: {len(files)} files")

    elif args.command == 'show':
        if not args.page:
            print("[ERROR] Page name required")
            return
        content = show_page(args.site, args.page)
        if content:
            print(content)

    elif args.command == 'deploy':
        deploy_site(args.site, dry_run=args.dry_run)

    elif args.command == 'status':
        status = check_status(args.site)
        if status:
            print(f"\n=== {status['site'].upper()} STATUS ===\n")
            print(f"Domain: {status['domain']}")
            print(f"\nPages:")
            for page, info in status['pages'].items():
                code = info.get('status', 0)
                if code == 200:
                    print(f"  {page:<20} OK ({info.get('size', 0):,} bytes)")
                else:
                    print(f"  {page:<20} {code} {info.get('error', '')}")


if __name__ == '__main__':
    main()
