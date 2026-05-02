#!/usr/bin/env python3
"""
Job Portal Multisite Manager

Manage the 10-site WordPress multisite network on A2 Hosting.

Usage:
    python3 jobportal_multisite.py status          # Check all sites
    python3 jobportal_multisite.py jobs [domain]   # List jobs on a site
    python3 jobportal_multisite.py add-job         # Add a job (interactive)
    python3 jobportal_multisite.py backup          # Backup database
    python3 jobportal_multisite.py info            # Show credentials/paths
"""

import sys
import subprocess
import json
import requests
from datetime import datetime

# Configuration
SITES = {
    1: {'domain': 'factoryjobs.eu', 'title': 'Factory Jobs Europe', 'color': '#E65100'},
    2: {'domain': 'buildjobs.eu', 'title': 'Build Jobs Europe', 'color': '#F9A825'},
    3: {'domain': 'warehouseworkers.eu', 'title': 'Warehouse Workers Europe', 'color': '#1565C0'},
    4: {'domain': 'horecaworkers.eu', 'title': 'HORECA Workers Europe', 'color': '#C62828'},
    5: {'domain': 'careworkers.eu', 'title': 'Care Workers Europe', 'color': '#AD1457'},
    6: {'domain': 'electricjobs.eu', 'title': 'Electric Jobs Europe', 'color': '#FBC02D'},
    7: {'domain': 'farmworkers.eu', 'title': 'Farm Workers Europe', 'color': '#2E7D32'},
    8: {'domain': 'meatworkers.eu', 'title': 'Meat Workers Europe', 'color': '#B71C1C'},
    9: {'domain': 'mechanicjobs.eu', 'title': 'Mechanic Jobs Europe', 'color': '#455A64'},
    10: {'domain': 'nepalezi.com', 'title': 'Nepalezi Workers', 'color': '#DC143C'},
}

CREDENTIALS = {
    'wp_admin': 'admin',
    'wp_password': 'JN@dmin2026!Secure',
    'db_name': 'loaiidil_jobnetwork',
    'db_user': 'loaiidil_jobnet',
    'db_password': 'JNjobnet2026secure',
    'cpanel_token': 'loaiidil:30GYXYLTECIUBV36ND4B20VRQUZ51ZA4',
    'cpanel_host': 'nl1-cl8-ats1.a2hosting.com:2083',
}

PATHS = {
    'wp_install': '/home/loaiidil/jobnetwork/',
    'backup_dir': '/home/loaiidil/jobsites_backup/',
    'local_docs': '/opt/ACTIVE/WEB/WEBSITE_REMODELING/',
}


def check_status():
    """Check HTTP status of all sites."""
    print("=== Job Portal Multisite Status ===\n")
    
    for site_id, site in SITES.items():
        domain = site['domain']
        try:
            r = requests.head(f"https://{domain}/", timeout=10)
            status = f"HTTP {r.status_code}"
        except Exception as e:
            status = f"ERROR: {e}"
        
        print(f"  {domain}: {status}")
    
    print("\n=== Admin URLs ===")
    print(f"  Network: https://factoryjobs.eu/wp-admin/network/")
    print(f"  Login: admin / JN@dmin2026!Secure")


def show_info():
    """Show all credentials and paths."""
    print("=== Credentials ===\n")
    print(f"  WP Admin: {CREDENTIALS['wp_admin']}")
    print(f"  WP Password: {CREDENTIALS['wp_password']}")
    print(f"  DB Name: {CREDENTIALS['db_name']}")
    print(f"  DB User: {CREDENTIALS['db_user']}")
    print(f"  DB Password: {CREDENTIALS['db_password']}")
    
    print("\n=== Paths ===\n")
    for name, path in PATHS.items():
        print(f"  {name}: {path}")
    
    print("\n=== Sites ===\n")
    for site_id, site in SITES.items():
        print(f"  {site_id}. {site['domain']} - {site['title']}")
    
    print("\n=== Admin URLs ===\n")
    print(f"  Network Admin: https://factoryjobs.eu/wp-admin/network/")
    for site_id, site in SITES.items():
        print(f"  {site['domain']}: https://{site['domain']}/wp-admin/")


def list_jobs(domain=None):
    """List jobs from a site (placeholder - requires WP REST API)."""
    if domain is None:
        domain = 'factoryjobs.eu'
    
    print(f"=== Jobs on {domain} ===\n")
    print(f"  View jobs: https://{domain}/jobs/")
    print(f"  Add job: https://{domain}/wp-admin/post-new.php?post_type=job_listing")
    print(f"  Manage: https://{domain}/wp-admin/edit.php?post_type=job_listing")


def backup_info():
    """Show backup information."""
    print("=== Backup Information ===\n")
    print("Original HTML backups: /home/loaiidil/jobsites_backup/")
    print("\nTo backup database via SSH:")
    print("  ssh loaiidil@nl1-cl8-ats1.a2hosting.com")
    print("  mysqldump -u loaiidil_jobnet -p loaiidil_jobnetwork > backup.sql")
    print(f"\nDB Password: {CREDENTIALS['db_password']}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    
    cmd = sys.argv[1].lower()
    
    if cmd == 'status':
        check_status()
    elif cmd == 'info':
        show_info()
    elif cmd == 'jobs':
        domain = sys.argv[2] if len(sys.argv) > 2 else None
        list_jobs(domain)
    elif cmd == 'backup':
        backup_info()
    else:
        print(f"Unknown command: {cmd}")
        print(__doc__)


if __name__ == '__main__':
    main()
