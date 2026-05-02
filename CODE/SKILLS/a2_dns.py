#!/usr/bin/env python3
"""
A2 Hosting DNS Zone Management
Manage DNS records via cPanel UAPI.
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

    url = f"https://{host}:{port}/execute/{module}/{function}"
    if params:
        url += "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    req.add_header('Authorization', f'cpanel {user}:{token}')

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    try:
        with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Connection Error: {e.reason}")
        sys.exit(1)

def cmd_list(config, args):
    """List DNS records for domain"""
    if not args.domain:
        print("Error: Domain required")
        sys.exit(1)

    result = cpanel_api(config, 'DNS', 'parse_zone', {'zone': args.domain})

    if result.get('status') != 1:
        print("Error:", result.get('errors'))
        sys.exit(1)

    records = result.get('data', [])

    print(f"DNS Records for {args.domain}:")
    print(f"{'Type':<8} {'Name':<30} {'TTL':<8} {'Value':<40}")
    print("-" * 90)

    for record in records:
        rtype = record.get('type', 'N/A')
        name = record.get('name', 'N/A')
        ttl = record.get('ttl', 'N/A')

        # Get value based on record type
        if rtype == 'A' or rtype == 'AAAA':
            value = record.get('address', 'N/A')
        elif rtype == 'CNAME':
            value = record.get('cname', 'N/A')
        elif rtype == 'MX':
            value = f"{record.get('preference', '')} {record.get('exchange', '')}"
        elif rtype == 'TXT':
            value = record.get('txtdata', 'N/A')[:40]
        elif rtype == 'NS':
            value = record.get('nsdname', 'N/A')
        else:
            value = str(record.get('record', 'N/A'))[:40]

        print(f"{rtype:<8} {name:<30} {ttl:<8} {value:<40}")

def cmd_add(config, args):
    """Add DNS record"""
    if not args.domain:
        print("Error: Domain required")
        sys.exit(1)

    if len(args.extra) < 3:
        print("Usage: a2_dns.py add <domain> <type> <name> <value> [ttl]")
        print("Example: a2_dns.py add example.com A subdomain 1.2.3.4")
        sys.exit(1)

    rtype = args.extra[0].upper()
    name = args.extra[1]
    value = args.extra[2]
    ttl = args.extra[3] if len(args.extra) > 3 else '14400'

    # Build params based on record type
    params = {
        'zone': args.domain,
        'type': rtype,
        'name': name,
        'ttl': ttl
    }

    if rtype == 'A':
        params['address'] = value
    elif rtype == 'AAAA':
        params['address'] = value
    elif rtype == 'CNAME':
        params['cname'] = value
    elif rtype == 'MX':
        params['exchange'] = value
        params['preference'] = args.extra[3] if len(args.extra) > 3 else '10'
    elif rtype == 'TXT':
        params['txtdata'] = value
    else:
        print(f"Unsupported record type: {rtype}")
        sys.exit(1)

    result = cpanel_api(config, 'DNS', 'mass_edit_zone', params)

    if result.get('status') == 1:
        print(f"Added {rtype} record: {name} -> {value}")
    else:
        print("Error:", result.get('errors'))

def cmd_delete(config, args):
    """Delete DNS record"""
    if not args.domain:
        print("Error: Domain required")
        sys.exit(1)

    if not args.extra:
        print("Usage: a2_dns.py delete <domain> <line_number>")
        print("Use 'a2_dns.py list <domain>' to find line numbers")
        sys.exit(1)

    line = args.extra[0]

    result = cpanel_api(config, 'DNS', 'mass_edit_zone', {
        'zone': args.domain,
        'remove': line
    })

    if result.get('status') == 1:
        print(f"Deleted record at line {line}")
    else:
        print("Error:", result.get('errors'))

def cmd_check(config, args):
    """Check DNS propagation"""
    if not args.domain:
        print("Error: Domain required")
        sys.exit(1)

    import subprocess

    print(f"Checking DNS for {args.domain}...")
    print()

    # Check A record
    print("A Record:")
    subprocess.run(['dig', '+short', 'A', args.domain], check=False)

    # Check MX
    print("\nMX Records:")
    subprocess.run(['dig', '+short', 'MX', args.domain], check=False)

    # Check NS
    print("\nNS Records:")
    subprocess.run(['dig', '+short', 'NS', args.domain], check=False)

    # Check TXT
    print("\nTXT Records:")
    subprocess.run(['dig', '+short', 'TXT', args.domain], check=False)

def main():
    parser = argparse.ArgumentParser(description='A2 Hosting DNS Management')
    parser.add_argument('action', help='Action: list, add, delete, check')
    parser.add_argument('domain', nargs='?', help='Domain name')
    parser.add_argument('extra', nargs='*', help='Record type, name, value')

    args = parser.parse_args()
    config = load_config()

    commands = {
        'list': cmd_list,
        'add': cmd_add,
        'delete': cmd_delete,
        'check': cmd_check,
    }

    if args.action in commands:
        commands[args.action](config, args)
    else:
        print(f"Unknown action: {args.action}")
        print("Available: list, add, delete, check")
        sys.exit(1)

if __name__ == '__main__':
    main()
