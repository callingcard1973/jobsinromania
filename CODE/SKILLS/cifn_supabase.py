#!/usr/bin/env python3
"""
CIFN.EU Supabase Management Skill

Manage the cifn-eu Supabase project: sync data, query leads, update records.

Usage:
    python3 cifn_supabase.py status        # Show stats
    python3 cifn_supabase.py sync          # Sync from PostgreSQL
    python3 cifn_supabase.py search TERM   # Search leads
    python3 cifn_supabase.py category CAT  # Filter by category
"""

import os
import sys
import json
import argparse
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Supabase config
SUPABASE_URL = "https://srgfzelqcehzidkzkjyx.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNyZ2Z6ZWxxY2Voemlka3pranl4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzQ2NTU1MjAsImV4cCI6MjA5MDIzMTUyMH0.ybQVkWw_UFDgqLqCGsOnTvt5weq0ps3N1sZmRSAb2gE"
SUPABASE_SERVICE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InNyZ2Z6ZWxxY2Voemlka3pranl4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NDY1NTUyMCwiZXhwIjoyMDkwMjMxNTIwfQ.rAbu0WdET9GdnUL7o3b4wsdiQtRwx9-rLCy6Fy9fQww"

# Category mapping
CATEGORY_MAP = {
    'Lucrari': 'constructii',
    'Furnizare': 'echipamente',
    'Servicii': 'servicii'
}


def get_headers(service=False):
    """Get request headers"""
    key = SUPABASE_SERVICE_KEY if service else SUPABASE_ANON_KEY
    return {
        'apikey': key,
        'Authorization': f'Bearer {key}',
        'Content-Type': 'application/json',
        'Prefer': 'count=exact'
    }


def parse_date(date_str):
    """Convert DD.MM.YYYY to YYYY-MM-DD"""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(date_str, '%d.%m.%Y')
        return dt.strftime('%Y-%m-%d')
    except:
        return None


def cmd_status(args):
    """Show Supabase stats"""
    print("=" * 50)
    print("CIFN.EU Supabase Status")
    print("=" * 50)
    print(f"URL: {SUPABASE_URL}")
    print()

    # Total count
    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/leads?select=count',
        headers=get_headers()
    )
    if response.status_code in [200, 206]:
        range_header = response.headers.get('content-range', '0-0/0')
        total = int(range_header.split('/')[1])
        print(f"Total leads: {total:,}")
    else:
        print(f"Error: {response.status_code}")
        return 1

    # Count by category
    print("\nBy category:")
    for cat in ['constructii', 'echipamente', 'servicii', 'altele']:
        response = requests.get(
            f'{SUPABASE_URL}/rest/v1/leads?select=count&categorie=eq.{cat}',
            headers=get_headers()
        )
        if response.status_code in [200, 206]:
            range_header = response.headers.get('content-range', '0-0/0')
            count = int(range_header.split('/')[1])
            print(f"  {cat}: {count:,}")

    # With/without company
    print("\nData quality:")
    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/leads?select=count&beneficiar=neq.-',
        headers=get_headers()
    )
    if response.status_code in [200, 206]:
        range_header = response.headers.get('content-range', '0-0/0')
        with_company = int(range_header.split('/')[1])
        print(f"  Cu companie: {with_company:,}")
        print(f"  Fara companie: {total - with_company:,}")

    return 0


def cmd_sync(args):
    """Sync data from local PostgreSQL to Supabase"""
    print("Syncing data to Supabase...")

    # Connect to local PostgreSQL
    conn = psycopg2.connect(
        host='localhost',
        port=5432,
        dbname='european_funds',
        user='tudor'
    )
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Fetch leads
    cur.execute("""
        SELECT id, beneficiar, titlu_achizitie as titlu, buget, judet,
               tip_contract, status_procedura as tip_procedura, data_publicare
        FROM beneficiari_privati
    """)
    rows = cur.fetchall()
    print(f"Found {len(rows)} leads in PostgreSQL")

    # Clear existing data
    print("Clearing existing Supabase data...")
    headers = get_headers(service=True)
    headers['Prefer'] = 'return=minimal'
    requests.delete(f'{SUPABASE_URL}/rest/v1/leads?id=gt.0', headers=headers)

    # Insert in batches
    batch_size = 500
    success = 0

    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        batch_num = i // batch_size + 1

        data = []
        for lead in batch:
            tip = lead.get('tip_contract', '') or ''
            categorie = CATEGORY_MAP.get(tip, 'altele')

            data.append({
                'beneficiar': lead.get('beneficiar') or '-',
                'titlu': lead.get('titlu') or '-',
                'buget': lead.get('buget') or '-',
                'judet': lead.get('judet') or '-',
                'categorie': categorie,
                'tip_procedura': lead.get('tip_procedura') or '-',
                'data_publicare': parse_date(lead.get('data_publicare'))
            })

        response = requests.post(
            f'{SUPABASE_URL}/rest/v1/leads',
            headers=headers,
            json=data
        )

        if response.status_code in [200, 201]:
            success += len(batch)
            print(f"Batch {batch_num}: {len(batch)} inserted")
        else:
            print(f"Batch {batch_num} error: {response.status_code}")

    cur.close()
    conn.close()

    print(f"\nSync complete: {success}/{len(rows)} leads")
    return 0


def cmd_search(args):
    """Search leads by term"""
    term = args.term
    limit = args.limit or 10

    print(f"Searching for: {term}")

    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/leads?select=*&or=(beneficiar.ilike.*{term}*,titlu.ilike.*{term}*,judet.ilike.*{term}*)&limit={limit}',
        headers=get_headers()
    )

    if response.status_code in [200, 206]:
        range_header = response.headers.get('content-range', '0-0/0')
        total = int(range_header.split('/')[1])
        leads = response.json()

        print(f"Found {total} results (showing {len(leads)})\n")

        for lead in leads:
            print(f"ID: {lead['id']}")
            print(f"  Companie: {lead['beneficiar']}")
            print(f"  Titlu: {lead['titlu'][:60]}...")
            print(f"  Buget: {lead['buget']}")
            print(f"  Judet: {lead['judet']}")
            print()
    else:
        print(f"Error: {response.status_code}")
        return 1

    return 0


def cmd_category(args):
    """Filter by category"""
    cat = args.category
    limit = args.limit or 10

    print(f"Category: {cat}")

    response = requests.get(
        f'{SUPABASE_URL}/rest/v1/leads?select=*&categorie=eq.{cat}&limit={limit}',
        headers=get_headers()
    )

    if response.status_code in [200, 206]:
        range_header = response.headers.get('content-range', '0-0/0')
        total = int(range_header.split('/')[1])
        leads = response.json()

        print(f"Total: {total} leads (showing {len(leads)})\n")

        for lead in leads:
            print(f"- {lead['beneficiar']} | {lead['judet']} | {lead['buget']}")
    else:
        print(f"Error: {response.status_code}")
        return 1

    return 0


def main():
    parser = argparse.ArgumentParser(description='CIFN.EU Supabase Management')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # status
    subparsers.add_parser('status', help='Show Supabase stats')

    # sync
    subparsers.add_parser('sync', help='Sync data from PostgreSQL')

    # search
    search_parser = subparsers.add_parser('search', help='Search leads')
    search_parser.add_argument('term', help='Search term')
    search_parser.add_argument('--limit', type=int, default=10, help='Max results')

    # category
    cat_parser = subparsers.add_parser('category', help='Filter by category')
    cat_parser.add_argument('category', choices=['constructii', 'echipamente', 'servicii', 'altele'])
    cat_parser.add_argument('--limit', type=int, default=10, help='Max results')

    args = parser.parse_args()

    if args.command == 'status':
        return cmd_status(args)
    elif args.command == 'sync':
        return cmd_sync(args)
    elif args.command == 'search':
        return cmd_search(args)
    elif args.command == 'category':
        return cmd_category(args)
    else:
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
