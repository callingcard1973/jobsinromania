#!/usr/bin/env python3
"""
A2 Hosting Email Management
Manage email accounts and forwarders via cPanel UAPI.
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
    """List all email accounts"""
    result = cpanel_api(config, 'Email', 'list_pops')

    if result.get('status') != 1:
        print("Error:", result.get('errors'))
        sys.exit(1)

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

def cmd_create(config, args):
    """Create email account"""
    if len(args.extra) < 2:
        print("Usage: a2_email.py create <email@domain.com> <password> [quota_mb]")
        sys.exit(1)

    email = args.extra[0]
    password = args.extra[1]
    quota = args.extra[2] if len(args.extra) > 2 else '1024'

    if '@' not in email:
        print("Error: Invalid email format (need user@domain.com)")
        sys.exit(1)

    user, domain = email.split('@', 1)

    result = cpanel_api(config, 'Email', 'add_pop', {
        'email': user,
        'domain': domain,
        'password': password,
        'quota': quota
    })

    if result.get('status') == 1:
        print(f"Created: {email}")
        print(f"Quota: {quota} MB")
    else:
        print("Error:", result.get('errors'))

def cmd_delete(config, args):
    """Delete email account"""
    if not args.extra:
        print("Usage: a2_email.py delete <email@domain.com>")
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
        print(f"Deleted: {email}")
    else:
        print("Error:", result.get('errors'))

def cmd_password(config, args):
    """Change email password"""
    if len(args.extra) < 2:
        print("Usage: a2_email.py password <email@domain.com> <new_password>")
        sys.exit(1)

    email = args.extra[0]
    password = args.extra[1]

    if '@' not in email:
        print("Error: Invalid email format")
        sys.exit(1)

    user, domain = email.split('@', 1)

    result = cpanel_api(config, 'Email', 'passwd_pop', {
        'email': user,
        'domain': domain,
        'password': password
    })

    if result.get('status') == 1:
        print(f"Password changed for: {email}")
    else:
        print("Error:", result.get('errors'))

def cmd_quota(config, args):
    """Change email quota"""
    if len(args.extra) < 2:
        print("Usage: a2_email.py quota <email@domain.com> <quota_mb>")
        sys.exit(1)

    email = args.extra[0]
    quota = args.extra[1]

    if '@' not in email:
        print("Error: Invalid email format")
        sys.exit(1)

    user, domain = email.split('@', 1)

    result = cpanel_api(config, 'Email', 'edit_pop_quota', {
        'email': user,
        'domain': domain,
        'quota': quota
    })

    if result.get('status') == 1:
        print(f"Quota updated for {email}: {quota} MB")
    else:
        print("Error:", result.get('errors'))

def cmd_forwarders_list(config, args):
    """List email forwarders"""
    result = cpanel_api(config, 'Email', 'list_forwarders')

    if result.get('status') != 1:
        print("Error:", result.get('errors'))
        sys.exit(1)

    forwarders = result.get('data', [])

    if not forwarders:
        print("No forwarders found.")
        return

    print(f"{'Source':<40} {'Destination':<40}")
    print("-" * 80)

    for fwd in forwarders:
        source = fwd.get('dest', 'N/A')
        dest = fwd.get('forward', 'N/A')
        print(f"{source:<40} {dest:<40}")

def cmd_forwarders_add(config, args):
    """Add email forwarder"""
    if len(args.extra) < 2:
        print("Usage: a2_email.py forwarders add <source@domain.com> <dest@email.com>")
        sys.exit(1)

    source = args.extra[0]
    dest = args.extra[1]

    if '@' not in source:
        print("Error: Invalid source email format")
        sys.exit(1)

    user, domain = source.split('@', 1)

    result = cpanel_api(config, 'Email', 'add_forwarder', {
        'email': user,
        'domain': domain,
        'fwdopt': 'fwd',
        'fwdemail': dest
    })

    if result.get('status') == 1:
        print(f"Forwarder created: {source} -> {dest}")
    else:
        print("Error:", result.get('errors'))

def cmd_forwarders_delete(config, args):
    """Delete email forwarder"""
    if len(args.extra) < 2:
        print("Usage: a2_email.py forwarders delete <source@domain.com> <dest@email.com>")
        sys.exit(1)

    source = args.extra[0]
    dest = args.extra[1]

    result = cpanel_api(config, 'Email', 'delete_forwarder', {
        'address': source,
        'forwarder': dest
    })

    if result.get('status') == 1:
        print(f"Deleted forwarder: {source} -> {dest}")
    else:
        print("Error:", result.get('errors'))

def cmd_autoresponders(config, args):
    """List autoresponders"""
    result = cpanel_api(config, 'Email', 'list_auto_responders')

    if result.get('status') != 1:
        print("Error:", result.get('errors'))
        sys.exit(1)

    responders = result.get('data', [])

    if not responders:
        print("No autoresponders configured.")
        return

    print("Autoresponders:")
    for resp in responders:
        email = resp.get('email', 'N/A')
        subject = resp.get('subject', 'N/A')
        print(f"  - {email}: {subject}")

def main():
    parser = argparse.ArgumentParser(description='A2 Hosting Email Management')
    parser.add_argument('action', help='Action: list, create, delete, password, quota, forwarders, autoresponders')
    parser.add_argument('extra', nargs='*', help='Additional arguments')

    args = parser.parse_args()
    config = load_config()

    # Handle forwarders subcommands
    if args.action == 'forwarders' and args.extra:
        subaction = args.extra[0]
        args.extra = args.extra[1:]

        if subaction == 'list':
            cmd_forwarders_list(config, args)
        elif subaction == 'add':
            cmd_forwarders_add(config, args)
        elif subaction == 'delete':
            cmd_forwarders_delete(config, args)
        else:
            print(f"Unknown forwarders action: {subaction}")
            print("Available: list, add, delete")
        return

    commands = {
        'list': cmd_list,
        'create': cmd_create,
        'delete': cmd_delete,
        'password': cmd_password,
        'quota': cmd_quota,
        'forwarders': cmd_forwarders_list,
        'autoresponders': cmd_autoresponders,
    }

    if args.action in commands:
        commands[args.action](config, args)
    else:
        print(f"Unknown action: {args.action}")
        print("Available: list, create, delete, password, quota, forwarders, autoresponders")
        sys.exit(1)

if __name__ == '__main__':
    main()
