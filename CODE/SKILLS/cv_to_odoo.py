#!/usr/bin/env python3
"""
Import CVs from CV_INBOX to Odoo CRM as leads.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/cv_to_odoo.py --stats          # Show stats only
    python3 /opt/ACTIVE/INFRA/SKILLS/cv_to_odoo.py --dry-run        # Preview import
    python3 /opt/ACTIVE/INFRA/SKILLS/cv_to_odoo.py --all            # Import all CVs
    python3 /opt/ACTIVE/INFRA/SKILLS/cv_to_odoo.py --new-only       # Import only new (not in Odoo)
    python3 /opt/ACTIVE/INFRA/SKILLS/cv_to_odoo.py --list-sources   # List UTM sources

Author: Claude Code
"""

import os
import sys
import csv
import base64
import argparse
import mimetypes
from pathlib import Path
from typing import List, Dict, Optional, Tuple

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

import xmlrpc.client

# Odoo connection
ODOO_URL = os.getenv("ODOO_URL", "http://raspibig:8069")
ODOO_DB = os.getenv("ODOO_DB", "master_odoo")
ODOO_USER = os.getenv("ODOO_USER", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

# Paths
CV_MASTER = "/opt/ACTIVE/OPENDATA/DATA/CV_INBOX/master_applicants.csv"

# Campaign to UTM source mapping (will be auto-populated on first run)
# Format: campaign_name -> source_id in Odoo
DEFAULT_SOURCE_MAP = {
    "INTERJOB": "interjob.ro",
    "HORECA": "mivromania.info",
    "WAREHOUSE": "warehouseworkers.eu",
    "MIV_ONLINE": "mivromania.online",
    "NEPALEZI": "nepalezi.com",
    "EXPATS": "expatsinromania.org",
    "GMAIL1": "Gmail",
    "GMAIL2": "Gmail",
    "YAHOO": "Yahoo",
    "CIFN": "cifn.info",
}

# Tag for CV applicants
CV_APPLICANT_TAG = "CV Applicant"


class CvToOdooImporter:
    """Import CVs to Odoo CRM as leads."""

    def __init__(self, dry_run: bool = False):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.username = ODOO_USER
        self.password = ODOO_PASSWORD
        self.uid = None
        self.models = None
        self.dry_run = dry_run
        self.cv_tag_id = None
        self.source_map = {}  # campaign -> source_id

    def connect(self) -> bool:
        """Connect to Odoo."""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})

            if not self.uid:
                print(f"ERROR: Authentication failed at {self.url}")
                return False

            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"Connected to Odoo: {self.url} (user_id={self.uid})")
            return True

        except Exception as e:
            print(f"ERROR connecting to Odoo: {e}")
            return False

    def _execute(self, model: str, method: str, *args, **kwargs):
        """Execute Odoo model method."""
        return self.models.execute_kw(
            self.db, self.uid, self.password,
            model, method, *args, **kwargs
        )

    def get_or_create_tag(self) -> Optional[int]:
        """Get or create 'CV Applicant' tag."""
        try:
            # Search existing
            ids = self._execute('crm.tag', 'search', [[['name', '=', CV_APPLICANT_TAG]]])
            if ids:
                self.cv_tag_id = ids[0]
                return self.cv_tag_id

            if self.dry_run:
                print(f"[DRY-RUN] Would create tag: {CV_APPLICANT_TAG}")
                return None

            # Create new tag
            self.cv_tag_id = self._execute('crm.tag', 'create', [{'name': CV_APPLICANT_TAG}])
            print(f"Created tag: {CV_APPLICANT_TAG} (id={self.cv_tag_id})")
            return self.cv_tag_id

        except Exception as e:
            print(f"Error with tag: {e}")
            return None

    def get_or_create_source(self, source_name: str) -> Optional[int]:
        """Get or create UTM source."""
        if not source_name:
            return None

        # Check cache
        if source_name in self.source_map:
            return self.source_map[source_name]

        try:
            # Search existing
            ids = self._execute('utm.source', 'search', [[['name', '=', source_name]]])
            if ids:
                self.source_map[source_name] = ids[0]
                return ids[0]

            if self.dry_run:
                print(f"[DRY-RUN] Would create source: {source_name}")
                return None

            # Create new source
            source_id = self._execute('utm.source', 'create', [{'name': source_name}])
            self.source_map[source_name] = source_id
            print(f"Created source: {source_name} (id={source_id})")
            return source_id

        except Exception as e:
            print(f"Error with source {source_name}: {e}")
            return None

    def list_sources(self):
        """List existing UTM sources."""
        try:
            sources = self._execute('utm.source', 'search_read', [[]], {'fields': ['name']})
            print(f"\n=== UTM Sources ({len(sources)}) ===\n")
            for s in sorted(sources, key=lambda x: x['name']):
                print(f"  [{s['id']:3d}] {s['name']}")
        except Exception as e:
            print(f"Error listing sources: {e}")

    def check_lead_exists(self, email: str) -> bool:
        """Check if lead with email already exists."""
        if not email:
            return False
        try:
            ids = self._execute('crm.lead', 'search', [[['email_from', '=', email]]])
            return len(ids) > 0
        except:
            return False

    def attach_files(self, lead_id: int, folder: str, cv_files: str) -> int:
        """Attach CV files to lead."""
        if not folder or not cv_files:
            return 0

        attached = 0
        files = [f.strip() for f in cv_files.split(',') if f.strip()]

        for filename in files:
            filepath = os.path.join(folder, filename)
            if not os.path.exists(filepath):
                print(f"    File not found: {filepath}")
                continue

            try:
                # Read and encode file
                with open(filepath, 'rb') as f:
                    file_data = base64.b64encode(f.read()).decode('utf-8')

                # Detect mimetype
                mimetype, _ = mimetypes.guess_type(filename)
                if not mimetype:
                    mimetype = 'application/octet-stream'

                if self.dry_run:
                    print(f"    [DRY-RUN] Would attach: {filename}")
                    attached += 1
                    continue

                # Create attachment
                attachment_id = self._execute('ir.attachment', 'create', [{
                    'name': filename,
                    'type': 'binary',
                    'datas': file_data,
                    'res_model': 'crm.lead',
                    'res_id': lead_id,
                    'mimetype': mimetype,
                }])
                attached += 1
                print(f"    Attached: {filename} (id={attachment_id})")

            except Exception as e:
                print(f"    Error attaching {filename}: {e}")

        return attached

    def import_cv(self, row: Dict) -> Tuple[bool, Optional[int]]:
        """Import single CV as CRM lead."""
        email = row.get('email', '').strip()
        name = row.get('name', '').strip() or 'Unknown Applicant'
        phone = row.get('phone', '').strip()
        campaign = row.get('campaign', '').strip()
        date = row.get('date', '').strip()
        cv_files = row.get('cv_files', '').strip()
        folder = row.get('folder', '').strip()
        saved_at = row.get('saved_at', '').strip()

        # Clean name
        name = to_ascii(name) if name else 'Unknown Applicant'

        # Build description
        description_parts = [
            f"Campaign: {campaign}",
            f"Received: {date}",
            f"CV Files: {cv_files}",
            f"Folder: {folder}",
            f"Imported: {saved_at}",
        ]
        description = '\n'.join(description_parts)

        # Get source
        source_name = DEFAULT_SOURCE_MAP.get(campaign, campaign)
        source_id = self.get_or_create_source(source_name)

        # Build lead data
        lead_data = {
            'name': name,
            'type': 'lead',
            'email_from': email,
            'description': description,
        }

        if phone:
            lead_data['phone'] = phone

        if self.cv_tag_id:
            lead_data['tag_ids'] = [(6, 0, [self.cv_tag_id])]

        if source_id:
            lead_data['source_id'] = source_id

        if self.dry_run:
            print(f"  [DRY-RUN] Would create lead: {name} <{email}>")
            # Still attach files in dry-run preview
            self.attach_files(None, folder, cv_files)
            return True, None

        try:
            lead_id = self._execute('crm.lead', 'create', [lead_data])
            print(f"  Created lead: {name} <{email}> (id={lead_id})")

            # Attach CV files
            self.attach_files(lead_id, folder, cv_files)

            return True, lead_id

        except Exception as e:
            print(f"  ERROR creating lead for {email}: {e}")
            return False, None

    def import_all(self, new_only: bool = False) -> Dict:
        """Import all CVs from master CSV."""
        stats = {'total': 0, 'imported': 0, 'skipped': 0, 'errors': 0, 'attachments': 0}

        if not os.path.exists(CV_MASTER):
            print(f"ERROR: File not found: {CV_MASTER}")
            return stats

        # Get or create tag
        self.get_or_create_tag()

        # Read CSV
        with open(CV_MASTER, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        stats['total'] = len(rows)
        print(f"\nImporting {stats['total']} CVs from {CV_MASTER}")
        print(f"Mode: {'new-only' if new_only else 'all'}")
        if self.dry_run:
            print("*** DRY-RUN MODE - No changes will be made ***")
        print("-" * 60)

        for i, row in enumerate(rows, 1):
            email = row.get('email', '').strip()

            # Skip if new_only and already exists
            if new_only and email:
                if self.check_lead_exists(email):
                    print(f"  [{i}] SKIP (exists): {email}")
                    stats['skipped'] += 1
                    continue

            # Import
            print(f"[{i}/{stats['total']}] Processing: {row.get('name', 'Unknown')}")
            success, lead_id = self.import_cv(row)

            if success:
                stats['imported'] += 1
            else:
                stats['errors'] += 1

        print("-" * 60)
        print(f"\nSUMMARY:")
        print(f"  Total:    {stats['total']}")
        print(f"  Imported: {stats['imported']}")
        print(f"  Skipped:  {stats['skipped']}")
        print(f"  Errors:   {stats['errors']}")

        return stats

    def show_stats(self):
        """Show stats about CV data and Odoo leads."""
        print("\n=== CV INBOX STATS ===\n")

        # Local stats
        if os.path.exists(CV_MASTER):
            with open(CV_MASTER, 'r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            # Campaign distribution
            campaigns = {}
            for row in rows:
                camp = row.get('campaign', 'Unknown')
                campaigns[camp] = campaigns.get(camp, 0) + 1

            print(f"Master CSV: {CV_MASTER}")
            print(f"Total records: {len(rows)}")
            print("\nBy Campaign:")
            for camp, count in sorted(campaigns.items(), key=lambda x: -x[1]):
                print(f"  {camp}: {count}")
        else:
            print(f"Master CSV not found: {CV_MASTER}")

        # Odoo stats
        print("\n=== ODOO STATS ===\n")
        try:
            # Find CV Applicant tag
            tag_ids = self._execute('crm.tag', 'search', [[['name', '=', CV_APPLICANT_TAG]]])
            if tag_ids:
                tag_id = tag_ids[0]
                # Count leads with this tag
                lead_count = self._execute('crm.lead', 'search_count', [[['tag_ids', 'in', [tag_id]]]])
                print(f"Leads with '{CV_APPLICANT_TAG}' tag: {lead_count}")
            else:
                print(f"Tag '{CV_APPLICANT_TAG}' not found in Odoo")

            # Total leads
            total_leads = self._execute('crm.lead', 'search_count', [[]])
            print(f"Total leads in Odoo: {total_leads}")

        except Exception as e:
            print(f"Error getting Odoo stats: {e}")


def main():
    parser = argparse.ArgumentParser(description='Import CVs to Odoo CRM')
    parser.add_argument('--stats', action='store_true', help='Show stats only')
    parser.add_argument('--dry-run', action='store_true', help='Preview without changes')
    parser.add_argument('--all', action='store_true', help='Import all CVs')
    parser.add_argument('--new-only', action='store_true', help='Import only new (not in Odoo)')
    parser.add_argument('--list-sources', action='store_true', help='List UTM sources')

    args = parser.parse_args()

    if not ODOO_PASSWORD:
        print("ERROR: ODOO_PASSWORD not set in /opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
        sys.exit(1)

    importer = CvToOdooImporter(dry_run=args.dry_run)

    if not importer.connect():
        sys.exit(1)

    if args.stats:
        importer.show_stats()
        return

    if args.list_sources:
        importer.list_sources()
        return

    if args.all or args.new_only or args.dry_run:
        stats = importer.import_all(new_only=args.new_only)
        if stats['errors'] > 0 and not args.dry_run:
            sys.exit(1)
        return

    # Default: show help
    print("\nNo action specified. Use --stats, --dry-run, --all, or --new-only")
    parser.print_help()


if __name__ == "__main__":
    main()
