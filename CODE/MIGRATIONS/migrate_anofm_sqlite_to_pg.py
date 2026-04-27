#!/usr/bin/env python3
"""
ANOFM SQLite to PostgreSQL Migration Script

Reads all contacts from /opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db
Writes to interjob_master.anofm_contacts on 127.0.0.1:5433

Idempotent: Uses ON CONFLICT DO NOTHING (email UNIQUE constraint)
Rollback: Delete from PG, SQLite remains untouched

Usage:
    python3 migrate_anofm_sqlite_to_pg.py
"""
import sqlite3
import psycopg2
import psycopg2.extras
import sys
from datetime import datetime
from pathlib import Path

# Configuration
SQLITE_DB = "/opt/EMAIL/CAMPAIGNS/ANOFM_TUDOR/tudor.db"
PG_CONN_STR = "postgresql://tudor:tudor@127.0.0.1:5433/interjob_master"
MIGRATION_ID = "ANOFM_20260427"


def migrate():
    """Execute SQLite → PostgreSQL migration."""
    print(f"[{datetime.now().isoformat()}] Starting ANOFM migration...")
    print(f"  Source: {SQLITE_DB}")
    print(f"  Target: {PG_CONN_STR}")

    # Connect SQLite
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cur = sqlite_conn.cursor()
        print(f"✓ SQLite connection OK")
    except Exception as e:
        print(f"✗ SQLite connection failed: {e}")
        return False

    # Connect PostgreSQL
    try:
        pg_conn = psycopg2.connect(PG_CONN_STR)
        pg_cur = pg_conn.cursor()
        print(f"✓ PostgreSQL connection OK")
    except Exception as e:
        print(f"✗ PostgreSQL connection failed: {e}")
        sqlite_conn.close()
        return False

    # Read all contacts from SQLite
    try:
        sqlite_cur.execute("SELECT * FROM contacts")
        rows = sqlite_cur.fetchall()
        print(f"✓ Read {len(rows)} records from SQLite")
    except Exception as e:
        print(f"✗ SQLite read failed: {e}")
        sqlite_conn.close()
        pg_conn.close()
        return False

    # Insert into PostgreSQL with ON CONFLICT handling
    migrated = 0
    skipped = 0
    errors = 0

    for i, row in enumerate(rows):
        try:
            pg_cur.execute("""
                INSERT INTO anofm_contacts (
                    email, company, city, county, source, status,
                    sent_at, sent_via, added_at, first_name, last_name,
                    contact_name, position, phone, sector
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (email) DO NOTHING
            """, (
                row['email'],
                row['company'],
                row['city'],
                row['county'] if 'county' in row.keys() else None,
                row['source'] if 'source' in row.keys() else 'anofm',
                row['status'] if 'status' in row.keys() else 'pending',
                row['sent_at'] if 'sent_at' in row.keys() else None,
                row['sent_via'] if 'sent_via' in row.keys() else None,
                row['added_at'] if 'added_at' in row.keys() else datetime.now().isoformat(),
                row['first_name'] if 'first_name' in row.keys() else None,
                row['last_name'] if 'last_name' in row.keys() else None,
                row['contact_name'] if 'contact_name' in row.keys() else None,
                row['position'] if 'position' in row.keys() else None,
                row['phone'] if 'phone' in row.keys() else None,
                row['sector'] if 'sector' in row.keys() else None,
            ))

            # Check if insert was successful (rowcount > 0) or skipped (duplicate)
            if pg_cur.rowcount > 0:
                migrated += 1
            else:
                skipped += 1

            # Progress indicator every 100 rows
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i + 1}/{len(rows)}")

        except Exception as e:
            print(f"  ✗ ERROR row {i + 1} ({row.get('email', 'UNKNOWN')}): {e}")
            errors += 1

    # Commit transaction
    try:
        pg_conn.commit()
        print(f"✓ PostgreSQL commit OK")
    except Exception as e:
        print(f"✗ PostgreSQL commit failed: {e}")
        pg_conn.rollback()
        sqlite_conn.close()
        pg_conn.close()
        return False

    # Verify migration
    try:
        pg_cur.execute("SELECT COUNT(*) FROM anofm_contacts")
        pg_total = pg_cur.fetchone()[0]

        pg_cur.execute("SELECT COUNT(*) FROM anofm_contacts WHERE status='pending'")
        pg_pending = pg_cur.fetchone()[0]

        pg_cur.execute("SELECT status, COUNT(*) FROM anofm_contacts GROUP BY status ORDER BY status")
        status_counts = {row[0]: row[1] for row in pg_cur.fetchall()}

        print(f"\n✓ Migration complete:")
        print(f"  Inserted:  {migrated}")
        print(f"  Skipped:   {skipped} (duplicates)")
        print(f"  Errors:    {errors}")
        print(f"  PG Total:  {pg_total}")
        print(f"  PG Pending: {pg_pending}")
        print(f"\n  Status breakdown:")
        for status, count in sorted(status_counts.items()):
            print(f"    {status or 'NULL'}: {count}")

    except Exception as e:
        print(f"✗ Verification failed: {e}")
        sqlite_conn.close()
        pg_conn.close()
        return False

    # Cleanup
    pg_cur.close()
    pg_conn.close()
    sqlite_cur.close()
    sqlite_conn.close()

    print(f"\n[{datetime.now().isoformat()}] Migration successful!")
    return True


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
