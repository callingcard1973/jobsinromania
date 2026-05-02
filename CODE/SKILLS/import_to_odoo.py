#!/usr/bin/env python3
"""
Import CSV contacts to Odoo CRM as leads.

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/import_to_odoo.py --csv /opt/TINICHIGII/tinichigerii_sector3_vitan.csv --type lead
    python3 /opt/ACTIVE/INFRA/SKILLS/import_to_odoo.py --csv contacts.csv --type contact --tag "Tinichigerie"
    python3 /opt/ACTIVE/INFRA/SKILLS/import_to_odoo.py --list-tags

Author: Claude Code
"""

import os
import sys
import csv
import argparse
from typing import List, Dict, Optional

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, clean_text

# Load env
from dotenv import load_dotenv
load_dotenv("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")

# Odoo connection
ODOO_URL = os.getenv("ODOO_URL", "http://raspibig:8069")
ODOO_DB = os.getenv("ODOO_DB", "master_odoo")
ODOO_USER = os.getenv("ODOO_USER", "admin")
ODOO_PASSWORD = os.getenv("ODOO_PASSWORD")

try:
    import xmlrpc.client
except ImportError:
    print("xmlrpc.client required (built-in Python)")
    sys.exit(1)


class OdooImporter:
    """Import data to Odoo CRM."""

    def __init__(self):
        self.url = ODOO_URL
        self.db = ODOO_DB
        self.username = ODOO_USER
        self.password = ODOO_PASSWORD
        self.uid = None
        self.models = None

    def connect(self) -> bool:
        """Connect to Odoo."""
        try:
            common = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/common')
            self.uid = common.authenticate(self.db, self.username, self.password, {})

            if not self.uid:
                print(f"EROARE: Autentificare esuata la {self.url}")
                return False

            self.models = xmlrpc.client.ServerProxy(f'{self.url}/xmlrpc/2/object')
            print(f"Conectat la Odoo: {self.url} (user_id={self.uid})")
            return True

        except Exception as e:
            print(f"EROARE conectare Odoo: {e}")
            return False

    def search_tag(self, tag_name: str, model: str = 'crm.tag') -> Optional[int]:
        """Search for existing tag."""
        try:
            ids = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search',
                [[['name', '=', tag_name]]]
            )
            return ids[0] if ids else None
        except:
            return None

    def create_tag(self, tag_name: str, model: str = 'crm.tag') -> Optional[int]:
        """Create tag if not exists."""
        existing = self.search_tag(tag_name, model)
        if existing:
            return existing

        try:
            tag_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'create',
                [{'name': tag_name}]
            )
            print(f"Tag creat: {tag_name} (id={tag_id})")
            return tag_id
        except Exception as e:
            print(f"Eroare creare tag: {e}")
            return None

    def list_tags(self, model: str = 'crm.tag'):
        """List existing tags."""
        try:
            tags = self.models.execute_kw(
                self.db, self.uid, self.password,
                model, 'search_read',
                [[]],
                {'fields': ['name']}
            )
            print(f"\n=== Tag-uri existente ({model}) ===\n")
            for t in tags:
                print(f"  [{t['id']}] {t['name']}")
            print(f"\nTotal: {len(tags)} tag-uri")
        except Exception as e:
            print(f"Eroare listare tags: {e}")

    def import_lead(self, data: Dict, tag_ids: List[int] = None) -> Optional[int]:
        """Import single lead to CRM."""
        try:
            lead_data = {
                'name': data.get('name') or data.get('nume') or 'Lead necunoscut',
                'type': 'lead',
            }

            # Phone
            phone = data.get('phone') or data.get('telefon') or data.get('Telefon')
            if phone:
                lead_data['phone'] = phone

            # Email
            email = data.get('email') or data.get('Email')
            if email:
                lead_data['email_from'] = email

            # Website
            website = data.get('website') or data.get('Website')
            if website:
                lead_data['website'] = website

            # Address
            address = data.get('address') or data.get('adresa') or data.get('Adresa')
            if address:
                lead_data['street'] = address

            # Description/Notes
            notes_parts = []
            servicii = data.get('servicii') or data.get('Servicii')
            if servicii:
                notes_parts.append(f"Servicii: {servicii}")
            preturi = data.get('Preturi_Info') or data.get('preturi')
            if preturi:
                notes_parts.append(f"Preturi: {preturi}")
            sursa = data.get('sursa') or data.get('Sursa')
            if sursa:
                notes_parts.append(f"Sursa: {sursa}")
            zona = data.get('zona') or data.get('Zona')
            if zona:
                notes_parts.append(f"Zona: {zona}")
            nota = data.get('nota') or data.get('Rating')
            if nota:
                notes_parts.append(f"Nota: {nota}")

            if notes_parts:
                lead_data['description'] = '\n'.join(notes_parts)

            # Tags
            if tag_ids:
                lead_data['tag_ids'] = [(6, 0, tag_ids)]

            lead_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'crm.lead', 'create',
                [lead_data]
            )
            return lead_id

        except Exception as e:
            print(f"Eroare creare lead: {e}")
            return None

    def import_contact(self, data: Dict, tag_ids: List[int] = None) -> Optional[int]:
        """Import single contact to res.partner."""
        try:
            contact_data = {
                'name': data.get('name') or data.get('nume') or data.get('Nume') or 'Contact necunoscut',
                'is_company': True,
            }

            # Phone
            phone = data.get('phone') or data.get('telefon') or data.get('Telefon')
            if phone:
                contact_data['phone'] = phone

            # Email
            email = data.get('email') or data.get('Email')
            if email:
                contact_data['email'] = email

            # Website
            website = data.get('website') or data.get('Website')
            if website:
                contact_data['website'] = website

            # Address
            address = data.get('address') or data.get('adresa') or data.get('Adresa')
            if address:
                contact_data['street'] = address

            # Tags (category_id for res.partner)
            if tag_ids:
                contact_data['category_id'] = [(6, 0, tag_ids)]

            contact_id = self.models.execute_kw(
                self.db, self.uid, self.password,
                'res.partner', 'create',
                [contact_data]
            )
            return contact_id

        except Exception as e:
            print(f"Eroare creare contact: {e}")
            return None

    def import_csv(self, csv_path: str, import_type: str = 'lead',
                   tag_name: str = None, skip_existing: bool = True) -> Dict:
        """Import CSV to Odoo."""
        stats = {'total': 0, 'imported': 0, 'skipped': 0, 'errors': 0}

        if not os.path.exists(csv_path):
            print(f"EROARE: Fisier inexistent: {csv_path}")
            return stats

        # Create tag if specified
        tag_ids = []
        if tag_name:
            if import_type == 'lead':
                tag_id = self.create_tag(tag_name, 'crm.tag')
            else:
                tag_id = self.create_tag(tag_name, 'res.partner.category')
            if tag_id:
                tag_ids = [tag_id]

        # Read CSV
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        stats['total'] = len(rows)
        print(f"\nImport {csv_path}: {stats['total']} randuri")
        print(f"Tip: {import_type}, Tag: {tag_name or '-'}")
        print("-" * 50)

        for i, row in enumerate(rows):
            # Normalize row keys
            data = {}
            for k, v in row.items():
                data[k.lower().strip()] = to_ascii(str(v).strip()) if v else ''

            # Also keep original keys
            data.update(row)

            # Check for existing (by email or phone)
            if skip_existing:
                email = data.get('email') or data.get('Email')
                phone = data.get('telefon') or data.get('Telefon') or data.get('phone')

                # Search existing
                search_domain = []
                if email:
                    if import_type == 'lead':
                        search_domain = [['email_from', '=', email]]
                    else:
                        search_domain = [['email', '=', email]]

                if search_domain:
                    try:
                        model = 'crm.lead' if import_type == 'lead' else 'res.partner'
                        existing = self.models.execute_kw(
                            self.db, self.uid, self.password,
                            model, 'search',
                            [search_domain]
                        )
                        if existing:
                            stats['skipped'] += 1
                            continue
                    except:
                        pass

            # Import
            if import_type == 'lead':
                result = self.import_lead(data, tag_ids)
            else:
                result = self.import_contact(data, tag_ids)

            if result:
                stats['imported'] += 1
                name = data.get('nume') or data.get('Nume') or data.get('name') or '-'
                print(f"  [{i+1}] {name[:30]:<30} -> ID {result}")
            else:
                stats['errors'] += 1

        print("-" * 50)
        print(f"SUMAR: {stats['imported']} importate, {stats['skipped']} skip, {stats['errors']} erori")

        return stats


def main():
    parser = argparse.ArgumentParser(description='Import CSV in Odoo CRM')
    parser.add_argument('--csv', help='Path CSV de importat')
    parser.add_argument('--type', choices=['lead', 'contact'], default='lead',
                        help='Tip import: lead sau contact')
    parser.add_argument('--tag', help='Tag de aplicat')
    parser.add_argument('--no-skip', action='store_true', help='Nu sari peste existente')
    parser.add_argument('--list-tags', action='store_true', help='Listeaza tag-urile existente')

    args = parser.parse_args()

    if not ODOO_PASSWORD:
        print("EROARE: ODOO_PASSWORD nu e setat in /opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
        sys.exit(1)

    importer = OdooImporter()

    if not importer.connect():
        sys.exit(1)

    if args.list_tags:
        importer.list_tags('crm.tag')
        importer.list_tags('res.partner.category')
        return

    if not args.csv:
        print("EROARE: Specifica --csv sau --list-tags")
        parser.print_help()
        sys.exit(1)

    stats = importer.import_csv(
        args.csv,
        import_type=args.type,
        tag_name=args.tag,
        skip_existing=not args.no_skip
    )

    print(f"\n=== Import finalizat ===")
    print(f"Total: {stats['total']}")
    print(f"Importate: {stats['imported']}")
    print(f"Sarite: {stats['skipped']}")
    print(f"Erori: {stats['errors']}")


if __name__ == "__main__":
    main()
