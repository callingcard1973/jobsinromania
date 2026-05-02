#!/usr/bin/env python3
"""
A2 Hosting cPanel UAPI Client
Provides command-line access to cPanel API functions.
"""

import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
import ssl
from pathlib import Path

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

def cpanel_api(config, module, function, params=None):
    """Make a cPanel UAPI call"""
    host = config.get('A2_HOST')
    user = config.get('A2_SSH_USER')
    token = config.get('A2_CPANEL_TOKEN')
    port = config.get('A2_CPANEL_PORT', '2083')

    if not all([host, user, token]):
        print("Error: A2_HOST, A2_SSH_USER, and A2_CPANEL_TOKEN required")
        sys.exit(1)

    # Build URL
    url = f"https://{host}:{port}/execute/{module}/{function}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    # Create request with auth header
    req = urllib.request.Request(url)
    req.add_header('Authorization', f'cpanel {user}:{token}')

    # Disable SSL verification for self-signed certs (common in cPanel)
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            data = json.loads(response.read().decode())
            return data
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        sys.exit(1)

def cmd_domains_list(config, args):
    """List all domains"""
    result = cpanel_api(config, 'DomainInfo', 'list_domains')
    if result.get('status') == 1:
        data = result.get('data', {})
        print("Main Domain:", data.get('main_domain', 'N/A'))
        print("\nAddon Domains:")
        for domain in data.get('addon_domains', []):
            print(f"  - {domain}")
        print("\nSubdomains:")
        for sub in data.get('sub_domains', []):
            print(f"  - {sub}")
        print("\nParked Domains:")
        for parked in data.get('parked_domains', []):
            print(f"  - {parked}")
    else:
        print("Error:", result.get('errors', ['Unknown error']))

def cmd_stats_disk(config, args):
    """Show disk usage"""
    result = cpanel_api(config, 'Quota', 'get_quota_info')
    if result.get('status') == 1:
        data = result.get('data', {})
        used = float(data.get('bytes_used', 0)) / (1024**3)
        limit = data.get('byte_limit')
        if limit:
            limit = float(limit) / (1024**3)
            print(f"Disk Usage: {used:.2f} GB / {limit:.2f} GB")
            print(f"Percentage: {(used/limit)*100:.1f}%")
        else:
            print(f"Disk Usage: {used:.2f} GB (unlimited)")
    else:
        print("Error:", result.get('errors'))

def cmd_email_list(config, args):
    """List email accounts"""
    result = cpanel_api(config, 'Email', 'list_pops')
    if result.get('status') == 1:
        accounts = result.get('data', [])
        if not accounts:
            print("No email accounts found.")
            return
        print(f"{'Email':<40} {'Disk Used':<15} {'Quota':<15}")
        print("-" * 70)
        for acc in accounts:
            email = acc.get('email', 'N/A')
            used = acc.get('humandiskused', 'N/A')
            quota = acc.get('humandiskquota', 'unlimited')
            print(f"{email:<40} {used:<15} {quota:<15}")
    else:
        print("Error:", result.get('errors'))

def cmd_email_create(config, args):
    """Create email account"""
    if len(args.extra) < 2:
        print("Usage: a2_cpanel.py email create <email@domain.com> <password>")
        sys.exit(1)

    email = args.extra[0]
    password = args.extra[1]
    quota = args.extra[2] if len(args.extra) > 2 else '1024'  # 1GB default

    if '@' not in email:
        print("Error: Invalid email format")
        sys.exit(1)

    user, domain = email.split('@', 1)

    result = cpanel_api(config, 'Email', 'add_pop', {
        'email': user,
        'domain': domain,
        'password': password,
        'quota': quota
    })

    if result.get('status') == 1:
        print(f"Created email account: {email}")
    else:
        print("Error:", result.get('errors'))

def cmd_email_delete(config, args):
    """Delete email account"""
    if not args.extra:
        print("Usage: a2_cpanel.py email delete <email@domain.com>")
        sys.exit(1)

    email = args.extra[0]
    if '@' not in email:
        print("Error: Invalid email format")
        sys.exit(1)

    user, domain = email.split('@', 1)

    result = cpanel_api(config, 'Email', 'delete_pop', {
        'email': user,
        'domain': domain
    })

    if result.get('status') == 1:
        print(f"Deleted email account: {email}")
    else:
        print("Error:", result.get('errors'))

def cmd_mysql_list(config, args):
    """List MySQL databases"""
    result = cpanel_api(config, 'Mysql', 'list_databases')
    if result.get('status') == 1:
        dbs = result.get('data', [])
        if not dbs:
            print("No databases found.")
            return
        print("Databases:")
        for db in dbs:
            name = db.get('database', 'N/A')
            size = db.get('disk_usage', 0)
            print(f"  - {name} ({size} bytes)")
    else:
        print("Error:", result.get('errors'))

def cmd_mysql_users(config, args):
    """List MySQL users"""
    result = cpanel_api(config, 'Mysql', 'list_users')
    if result.get('status') == 1:
        users = result.get('data', [])
        print("MySQL Users:")
        for user in users:
            print(f"  - {user.get('user', 'N/A')}")
    else:
        print("Error:", result.get('errors'))

def cmd_backup_list(config, args):
    """List available backups"""
    result = cpanel_api(config, 'Backup', 'list_backups')
    if result.get('status') == 1:
        backups = result.get('data', [])
        if not backups:
            print("No backups found.")
            return
        print("Available Backups:")
        for backup in backups:
            print(f"  - {backup}")
    else:
        print("Error:", result.get('errors'))

def cmd_ssl_list(config, args):
    """List SSL certificates"""
    result = cpanel_api(config, 'SSL', 'list_certs')
    if result.get('status') == 1:
        certs = result.get('data', [])
        if not certs:
            print("No SSL certificates found.")
            return
        for cert in certs:
            print(f"Domain: {cert.get('domain', 'N/A')}")
            print(f"  Issuer: {cert.get('issuer', {}).get('organizationName', 'N/A')}")
            print(f"  Expires: {cert.get('not_after', 'N/A')}")
            print()
    else:
        print("Error:", result.get('errors'))

def main():
    parser = argparse.ArgumentParser(description='A2 Hosting cPanel API Client')
    parser.add_argument('category', help='Command category (domains, stats, email, mysql, backup, ssl)')
    parser.add_argument('action', help='Action to perform')
    parser.add_argument('extra', nargs='*', help='Additional arguments')

    args = parser.parse_args()
    config = load_config()

    commands = {
        ('domains', 'list'): cmd_domains_list,
        ('stats', 'disk'): cmd_stats_disk,
        ('email', 'list'): cmd_email_list,
        ('email', 'create'): cmd_email_create,
        ('email', 'delete'): cmd_email_delete,
        ('mysql', 'list'): cmd_mysql_list,
        ('mysql', 'users'): cmd_mysql_users,
        ('backup', 'list'): cmd_backup_list,
        ('ssl', 'list'): cmd_ssl_list,
    }

    key = (args.category, args.action)
    if key in commands:
        commands[key](config, args)
    else:
        print(f"Unknown command: {args.category} {args.action}")
        print("\nAvailable commands:")
        for cat, act in sorted(commands.keys()):
            print(f"  {cat} {act}")
        sys.exit(1)

if __name__ == '__main__':
    main()
