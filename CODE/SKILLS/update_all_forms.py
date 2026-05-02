#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
update_all_forms.py - Bulk update Formspree forms across all A2 Hosting websites

Updates form action emails to centralized inbox (manpowerdristor@gmail.com)
for automatic processing by cv_processor.py.

Usage:
    # Dry run - show what would change
    python3 /opt/ACTIVE/INFRA/SKILLS/update_all_forms.py --dry-run

    # Update all forms
    python3 /opt/ACTIVE/INFRA/SKILLS/update_all_forms.py

    # Update specific domain
    python3 /opt/ACTIVE/INFRA/SKILLS/update_all_forms.py --domain factoryjobs.eu

    # Deploy after update
    python3 /opt/ACTIVE/INFRA/SKILLS/update_all_forms.py --deploy
"""

import os
import re
import sys
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

# Configuration
BACKUPS_DIR = Path('/opt/ACTIVE/WEB/WEBSITES/.backups')
TARGET_EMAIL = 'manpowerdristor@gmail.com'
A2_USER = 'loaiidil'
A2_HOST = 'nl1-cl8-ats1.a2hosting.com'
A2_PORT = '7822'
SSH_KEY = os.path.expanduser('~/.ssh/ofn_a2hosting')

# Job portal domains to update
JOB_DOMAINS = [
    'buildjobs.eu',
    'careworkers.eu',
    'electricjobs.eu',
    'factoryjobs.eu',
    'farmworkers.eu',
    'horecaworkers.eu',
    'meatworkers.eu',
    'mechanicjobs.eu',
    'cifn.info',
    'mivromania.info',
    'mivromania.online',
    'nepalezi.com',
]

# Files to update
FORM_FILES = ['apply.html', 'noneu-apply.html']


def find_latest_backup(domain: str) -> Path:
    """Find the most recent backup for a domain."""
    domain_dir = BACKUPS_DIR / domain
    if not domain_dir.exists():
        return None

    backups = sorted(domain_dir.iterdir(), reverse=True)
    for backup in backups:
        if backup.is_dir() and backup.name.startswith('20'):
            return backup
    return None


def update_formspree_email(content: str, domain: str) -> tuple[str, int]:
    """
    Update Formspree form action email and add source tracking.

    Returns: (updated_content, changes_count)
    """
    changes = 0

    # Pattern to match Formspree action URLs
    # Matches: action="https://formspree.io/f/EMAIL" or action='https://formspree.io/f/EMAIL'
    pattern = r'(action=["\'])https://formspree\.io/f/[^"\']+(["\'])'

    def replace_action(match):
        nonlocal changes
        quote = match.group(1)[-1]  # Get the quote character
        changes += 1
        return f'{match.group(1)}https://formspree.io/f/{TARGET_EMAIL}{quote}'

    updated = re.sub(pattern, replace_action, content)

    # Add hidden _source field if not present
    if '_source' not in updated and '<form' in updated.lower():
        # Find the form tag and add hidden field after it
        form_pattern = r'(<form[^>]*>)'
        def add_source(match):
            return f'{match.group(1)}\n                <input type="hidden" name="_source" value="{domain}">'

        # Only add if we made email changes
        if changes > 0:
            updated = re.sub(form_pattern, add_source, updated, count=1, flags=re.IGNORECASE)

    return updated, changes


def process_domain(domain: str, dry_run: bool = False) -> dict:
    """Process all form files for a domain."""
    result = {
        'domain': domain,
        'backup_path': None,
        'files_found': [],
        'files_updated': [],
        'errors': []
    }

    backup_path = find_latest_backup(domain)
    if not backup_path:
        result['errors'].append(f'No backup found for {domain}')
        return result

    result['backup_path'] = str(backup_path)

    for form_file in FORM_FILES:
        file_path = backup_path / form_file
        if not file_path.exists():
            continue

        result['files_found'].append(form_file)

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            updated, changes = update_formspree_email(content, domain)

            if changes > 0:
                result['files_updated'].append({
                    'file': form_file,
                    'changes': changes
                })

                if not dry_run:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(updated)
                    print(f'  Updated: {file_path}')
                else:
                    print(f'  Would update: {file_path} ({changes} changes)')
            else:
                print(f'  No changes needed: {file_path}')

        except Exception as e:
            result['errors'].append(f'{form_file}: {str(e)}')

    return result


def deploy_domain(domain: str) -> bool:
    """Deploy updated files to A2 Hosting."""
    backup_path = find_latest_backup(domain)
    if not backup_path:
        print(f'  No backup found for {domain}')
        return False

    for form_file in FORM_FILES:
        file_path = backup_path / form_file
        if not file_path.exists():
            continue

        remote_path = f'{A2_USER}@{A2_HOST}:~/{domain}/'
        cmd = [
            'rsync', '-avz',
            '-e', f'ssh -i {SSH_KEY} -p {A2_PORT}',
            str(file_path),
            remote_path
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                print(f'  Deployed: {form_file} -> {domain}')
            else:
                print(f'  Failed: {form_file} - {result.stderr}')
                return False
        except subprocess.TimeoutExpired:
            print(f'  Timeout deploying {form_file}')
            return False
        except Exception as e:
            print(f'  Error: {str(e)}')
            return False

    return True


def main():
    parser = argparse.ArgumentParser(description='Bulk update Formspree forms')
    parser.add_argument('--dry-run', action='store_true', help='Show changes without applying')
    parser.add_argument('--domain', help='Update specific domain only')
    parser.add_argument('--deploy', action='store_true', help='Deploy to A2 Hosting after update')
    parser.add_argument('--deploy-only', action='store_true', help='Deploy without updating')
    parser.add_argument('--list', action='store_true', help='List domains and their backup status')

    args = parser.parse_args()

    domains = [args.domain] if args.domain else JOB_DOMAINS

    if args.list:
        print('=' * 60)
        print('DOMAIN BACKUP STATUS')
        print('=' * 60)
        for domain in JOB_DOMAINS:
            backup = find_latest_backup(domain)
            if backup:
                forms = [f for f in FORM_FILES if (backup / f).exists()]
                print(f'{domain}: {backup.name} ({len(forms)} forms)')
            else:
                print(f'{domain}: NO BACKUP')
        return

    print('=' * 60)
    print(f'FORM UPDATER - Target: {TARGET_EMAIL}')
    print(f'Mode: {"DRY RUN" if args.dry_run else "LIVE"}')
    print('=' * 60)

    results = []

    if not args.deploy_only:
        for domain in domains:
            print(f'\n[{domain}]')
            result = process_domain(domain, dry_run=args.dry_run)
            results.append(result)

    if args.deploy or args.deploy_only:
        print('\n' + '=' * 60)
        print('DEPLOYING TO A2 HOSTING')
        print('=' * 60)

        for domain in domains:
            print(f'\n[{domain}]')
            deploy_domain(domain)

    # Summary
    print('\n' + '=' * 60)
    print('SUMMARY')
    print('=' * 60)

    total_updated = 0
    for r in results:
        if r['files_updated']:
            total_updated += len(r['files_updated'])
            print(f"{r['domain']}: {len(r['files_updated'])} files updated")
        if r['errors']:
            for err in r['errors']:
                print(f"{r['domain']}: ERROR - {err}")

    print(f'\nTotal files {"would be " if args.dry_run else ""}updated: {total_updated}')

    if args.dry_run:
        print('\nRun without --dry-run to apply changes.')
        print('Run with --deploy to also deploy to A2 Hosting.')


if __name__ == '__main__':
    main()
