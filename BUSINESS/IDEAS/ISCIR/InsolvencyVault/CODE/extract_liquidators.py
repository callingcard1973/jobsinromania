#!/usr/bin/env python3
"""Extract liquidator contacts from CIFN insolvency data."""

import pandas as pd
from pathlib import Path
import sqlite3
import json

print("InsolvencyVault: Liquidator Extraction")
print("=" * 50)

# Strategy: Query PostgreSQL interjob_master for insolvency data
# Expected tables: insolvencies, companies_clean (enriched ONRC)

try:
    import psycopg2
    conn = psycopg2.connect(
        host='127.0.0.1',
        port=5433,
        database='interjob_master',
        user='tudor',
        password='tudor'
    )
    print("[OK] Connected to PostgreSQL (port 5433)")

    # Query insolvencies (if table exists)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        LIMIT 20
    """)
    tables = [row[0] for row in cursor.fetchall()]
    print(f"  Available tables: {', '.join(tables[:5])}...")

    # If insolvencies table exists, extract liquidators
    if 'insolvencies' in tables or 'insolventa' in tables:
        table = 'insolvencies' if 'insolvencies' in tables else 'insolventa'
        cursor.execute(f"""
            SELECT DISTINCT
                liquidator_name,
                liquidator_email,
                liquidator_phone,
                COUNT(*) as cases_active
            FROM {table}
            WHERE status = 'active' OR status LIKE '%activ%'
            GROUP BY liquidator_name, liquidator_email, liquidator_phone
            ORDER BY cases_active DESC
        """)
        results = cursor.fetchall()
        print(f"  Found {len(results):,} active liquidators")

        df = pd.DataFrame(results, columns=['name', 'email', 'phone', 'cases'])
        df.to_csv('DATA/liquidators_ready.csv', index=False)
        print(f"[OK] Saved: {len(df):,} liquidators")
    else:
        print("  [WARN] Insolvency table not found")

    conn.close()

except Exception as e:
    print(f"[ERROR] PostgreSQL: {e}")
    print("  Fallback: Using ONRC + manual insolvency data...")

    # Fallback: Use ONRC data and search for liquidators
    # (requires pre-processed insolvency list)

    onrc_path = Path("D:/MEMORY/DATA/DB/onrc_firme.csv")
    if onrc_path.exists():
        print(f"  Loading ONRC ({onrc_path})...")
        df = pd.read_csv(onrc_path, encoding='utf-8-sig')

        # Filter: liquidators (CAEN 7490 = other specialist activities)
        # Or search by keyword in name
        keywords = ['lichidator', 'executor', 'insolventa', 'faliment', 'curator']
        mask = df['denumire'].str.lower().str.contains('|'.join(keywords), na=False)
        liquidators = df[mask][['denumire', 'email', 'telefon', 'cui']].copy()

        print(f"  Found {len(liquidators):,} potential liquidators")
        liquidators.columns = ['name', 'email', 'phone', 'cui']
        liquidators.to_csv('DATA/liquidators_ready.csv', index=False)
        print(f"[OK] Saved: {len(liquidators):,} liquidators")
    else:
        print(f"[WARN] ONRC data not found at {onrc_path}")
        print("  Create stub file for manual review")

        stub = pd.DataFrame({
            'name': ['Test Liquidator Ltd', 'Sample Executor SRL'],
            'email': ['info@liquidator.ro', 'executor@example.ro'],
            'phone': ['+40213334455', '0213334455'],
            'cui': ['12345678', '87654321']
        })
        stub.to_csv('DATA/liquidators_ready.csv', index=False)
        print(f"[OK] Created stub: {len(stub)} records")

print("\n" + "=" * 50)
print("Next: Import into SaaS + send validation list to Tudor")
