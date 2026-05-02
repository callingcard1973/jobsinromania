#!/usr/bin/env python3
"""
Consolidate CAEN SQLite data into PostgreSQL opendata database.

Phase 0 of B2B Contact Enrichment Product:
1. Add caen_code, caen_description columns to companies table
2. Import CAEN codes from SQLite (4.8M Romanian companies) by CUI match
3. Import new contacts from SQLite into contacts table (with deduplication)

Usage:
    python3 consolidate_to_postgres.py --dry-run      # Preview changes
    python3 consolidate_to_postgres.py                # Run consolidation
    python3 consolidate_to_postgres.py --stats        # Show current stats
    python3 consolidate_to_postgres.py --verify       # Verify after run

Database:
    PostgreSQL: opendata (17.7M companies, 8.2M contacts)
    SQLite: /opt/ACTIVE/OPENDATA/DATA/CAEN_INDEX/caen_search.db (4.8M RO companies)
"""

import os
import sys
import sqlite3
import argparse
import logging
from datetime import datetime
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_batch

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from alerting import send_telegram
except ImportError:
    def send_telegram(msg):
        print(f"[TELEGRAM] {msg}")

# Configuration
SQLITE_DB = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_INDEX/caen_search.db")
BATCH_SIZE = 5000
LOG_FILE = "/opt/ACTIVE/INFRA/LOGS/consolidate_postgres.log"

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_FILE, mode='a')
    ]
)
logger = logging.getLogger(__name__)


def get_postgres_conn():
    """Get PostgreSQL connection to opendata database."""
    return psycopg2.connect(
        dbname='opendata',
        user='tudor',
        host='',  # Use Unix socket for peer auth
        port=5432
    )


def get_sqlite_conn():
    """Get SQLite connection."""
    conn = sqlite3.connect(SQLITE_DB)
    conn.row_factory = sqlite3.Row
    return conn


def add_caen_columns(pg_conn, dry_run=False):
    """Add caen_code and caen_description columns to companies table."""
    logger.info("Checking for CAEN columns...")

    cur = pg_conn.cursor()

    # Check if columns exist
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'companies' AND column_name IN ('caen_code', 'caen_description')
    """)
    existing = [row[0] for row in cur.fetchall()]

    if 'caen_code' in existing and 'caen_description' in existing:
        logger.info("CAEN columns already exist")
        return True

    if dry_run:
        logger.info("[DRY RUN] Would add caen_code, caen_description columns")
        return True

    # Add columns
    try:
        if 'caen_code' not in existing:
            logger.info("Adding caen_code column...")
            cur.execute("ALTER TABLE companies ADD COLUMN caen_code VARCHAR(10)")

        if 'caen_description' not in existing:
            logger.info("Adding caen_description column...")
            cur.execute("ALTER TABLE companies ADD COLUMN caen_description VARCHAR(255)")

        pg_conn.commit()
        logger.info("CAEN columns added successfully")
        return True
    except Exception as e:
        logger.error(f"Error adding columns: {e}")
        pg_conn.rollback()
        return False


def create_caen_index(pg_conn, dry_run=False):
    """Create index on caen_code for fast searching."""
    if dry_run:
        logger.info("[DRY RUN] Would create index idx_companies_caen")
        return True

    cur = pg_conn.cursor()

    # Check if index exists
    cur.execute("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'companies' AND indexname = 'idx_companies_caen'
    """)
    if cur.fetchone():
        logger.info("CAEN index already exists")
        return True

    logger.info("Creating CAEN index (this may take a few minutes)...")
    try:
        cur.execute("CREATE INDEX idx_companies_caen ON companies(caen_code)")
        pg_conn.commit()
        logger.info("CAEN index created successfully")
        return True
    except Exception as e:
        logger.error(f"Error creating index: {e}")
        pg_conn.rollback()
        return False


def import_caen_codes(pg_conn, sqlite_conn, dry_run=False):
    """Import CAEN codes from SQLite by matching CUI to company_number."""
    logger.info("Importing CAEN codes from SQLite...")

    # Get total count from SQLite
    sqlite_cur = sqlite_conn.cursor()
    sqlite_cur.execute("SELECT COUNT(DISTINCT cui) FROM companies WHERE cui IS NOT NULL AND length(cui) > 0 AND caen IS NOT NULL")
    total_sqlite = sqlite_cur.fetchone()[0]
    logger.info(f"SQLite: {total_sqlite:,} companies with CUI and CAEN code")

    # Get Romanian companies in PostgreSQL
    pg_cur = pg_conn.cursor()
    pg_cur.execute("""
        SELECT COUNT(*) FROM companies
        WHERE country = 'RO' AND company_number IS NOT NULL AND company_number != ''
    """)
    total_pg = pg_cur.fetchone()[0]
    logger.info(f"PostgreSQL: {total_pg:,} Romanian companies with company_number")

    if dry_run:
        # Sample match check
        sqlite_cur.execute("""
            SELECT cui, company_name, caen
            FROM companies
            WHERE cui IS NOT NULL AND length(cui) > 0 AND caen IS NOT NULL
            LIMIT 10
        """)
        samples = sqlite_cur.fetchall()

        matched = 0
        for row in samples:
            pg_cur.execute("""
                SELECT id, name FROM companies
                WHERE country = 'RO' AND company_number = %s
            """, (str(row['cui']),))
            if pg_cur.fetchone():
                matched += 1

        logger.info(f"[DRY RUN] Sample match rate: {matched}/10 ({matched*10}%)")
        logger.info(f"[DRY RUN] Would update up to {total_sqlite:,} companies with CAEN codes")
        return 0

    # Build CUI -> CAEN mapping from SQLite (take first/best CAEN for each CUI)
    logger.info("Building CUI to CAEN mapping...")
    sqlite_cur.execute("""
        SELECT cui, caen, caen_description
        FROM companies
        WHERE cui IS NOT NULL AND length(cui) > 0 AND caen IS NOT NULL
        GROUP BY cui
        ORDER BY priority ASC
    """)

    cui_to_caen = {}
    for row in sqlite_cur:
        cui = str(row['cui'])
        if cui not in cui_to_caen:
            cui_to_caen[cui] = (row['caen'], row['caen_description'] or '')

    logger.info(f"Built mapping for {len(cui_to_caen):,} unique CUIs")

    # Update PostgreSQL in batches
    updated = 0
    batch = []

    for cui, (caen, description) in cui_to_caen.items():
        batch.append((caen, description[:255] if description else '', cui))

        if len(batch) >= BATCH_SIZE:
            execute_batch(pg_cur, """
                UPDATE companies
                SET caen_code = %s, caen_description = %s
                WHERE country = 'RO' AND company_number = %s AND caen_code IS NULL
            """, batch)
            updated += pg_cur.rowcount
            pg_conn.commit()
            logger.info(f"Updated {updated:,} companies...")
            batch = []

    # Final batch
    if batch:
        execute_batch(pg_cur, """
            UPDATE companies
            SET caen_code = %s, caen_description = %s
            WHERE country = 'RO' AND company_number = %s AND caen_code IS NULL
        """, batch)
        updated += pg_cur.rowcount
        pg_conn.commit()

    logger.info(f"Total CAEN codes imported: {updated:,}")
    return updated


def import_contacts(pg_conn, sqlite_conn, dry_run=False):
    """Import contacts from SQLite that don't exist in PostgreSQL."""
    logger.info("Importing contacts from SQLite...")

    sqlite_cur = sqlite_conn.cursor()
    pg_cur = pg_conn.cursor()

    # Count contacts in SQLite
    sqlite_cur.execute("""
        SELECT
            SUM(CASE WHEN email IS NOT NULL AND length(email) > 0 THEN 1 ELSE 0 END) as emails,
            SUM(CASE WHEN phone IS NOT NULL AND length(phone) > 0 THEN 1 ELSE 0 END) as phones
        FROM companies
        WHERE cui IS NOT NULL AND length(cui) > 0
    """)
    row = sqlite_cur.fetchone()
    sqlite_emails = row['emails'] or 0
    sqlite_phones = row['phones'] or 0
    logger.info(f"SQLite contacts: {sqlite_emails:,} emails, {sqlite_phones:,} phones")

    if dry_run:
        logger.info(f"[DRY RUN] Would import up to {sqlite_emails + sqlite_phones:,} contacts")
        return 0

    # Get existing contacts for Romanian companies
    logger.info("Loading existing contacts...")
    pg_cur.execute("""
        SELECT c.id, co.contact_type, co.contact_value
        FROM companies c
        JOIN contacts co ON co.company_id = c.id
        WHERE c.country = 'RO'
    """)
    existing_contacts = set()
    for row in pg_cur:
        existing_contacts.add((row[0], row[1], row[2].lower()))
    logger.info(f"Existing contacts loaded: {len(existing_contacts):,}")

    # Build company_number -> id mapping for Romanian companies
    logger.info("Building company_number to id mapping...")
    pg_cur.execute("""
        SELECT company_number, id FROM companies
        WHERE country = 'RO' AND company_number IS NOT NULL AND company_number != ''
    """)
    cui_to_id = {row[0]: row[1] for row in pg_cur}
    logger.info(f"Mapped {len(cui_to_id):,} CUIs to company IDs")

    # Import emails
    logger.info("Importing emails...")
    sqlite_cur.execute("""
        SELECT cui, email FROM companies
        WHERE cui IS NOT NULL AND length(cui) > 0
        AND email IS NOT NULL AND length(email) > 0
    """)

    new_emails = []
    for row in sqlite_cur:
        cui = str(row['cui'])
        email = row['email'].strip().lower()

        if cui in cui_to_id:
            company_id = cui_to_id[cui]
            if (company_id, 'email', email) not in existing_contacts:
                new_emails.append((company_id, 'email', email, 'caen_import'))
                existing_contacts.add((company_id, 'email', email))

    logger.info(f"Found {len(new_emails):,} new emails to import")

    if new_emails:
        for i in range(0, len(new_emails), BATCH_SIZE):
            batch = new_emails[i:i+BATCH_SIZE]
            execute_batch(pg_cur, """
                INSERT INTO contacts (company_id, contact_type, contact_value, source)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, batch)
            pg_conn.commit()
            logger.info(f"Imported {min(i+BATCH_SIZE, len(new_emails)):,} emails...")

    # Import phones
    logger.info("Importing phones...")
    sqlite_cur.execute("""
        SELECT cui, phone FROM companies
        WHERE cui IS NOT NULL AND length(cui) > 0
        AND phone IS NOT NULL AND length(phone) > 0
    """)

    new_phones = []
    for row in sqlite_cur:
        cui = str(row['cui'])
        phone = row['phone'].strip()

        if cui in cui_to_id:
            company_id = cui_to_id[cui]
            if (company_id, 'phone', phone.lower()) not in existing_contacts:
                new_phones.append((company_id, 'phone', phone, 'caen_import'))
                existing_contacts.add((company_id, 'phone', phone.lower()))

    logger.info(f"Found {len(new_phones):,} new phones to import")

    if new_phones:
        for i in range(0, len(new_phones), BATCH_SIZE):
            batch = new_phones[i:i+BATCH_SIZE]
            execute_batch(pg_cur, """
                INSERT INTO contacts (company_id, contact_type, contact_value, source)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, batch)
            pg_conn.commit()
            logger.info(f"Imported {min(i+BATCH_SIZE, len(new_phones)):,} phones...")

    total = len(new_emails) + len(new_phones)
    logger.info(f"Total contacts imported: {total:,}")
    return total


def show_stats(pg_conn):
    """Show current database statistics."""
    cur = pg_conn.cursor()

    print("\n=== PostgreSQL opendata Statistics ===\n")

    # Total companies
    cur.execute("SELECT COUNT(*) FROM companies")
    total = cur.fetchone()[0]
    print(f"Total companies: {total:,}")

    # Romanian companies
    cur.execute("SELECT COUNT(*) FROM companies WHERE country = 'RO'")
    romanian = cur.fetchone()[0]
    print(f"Romanian companies: {romanian:,}")

    # Companies with CAEN
    cur.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'companies' AND column_name = 'caen_code'
    """)
    if cur.fetchone():
        cur.execute("SELECT COUNT(*) FROM companies WHERE caen_code IS NOT NULL")
        with_caen = cur.fetchone()[0]
        print(f"Companies with CAEN code: {with_caen:,}")
    else:
        print("CAEN columns not yet added")

    # Contacts
    cur.execute("SELECT contact_type, COUNT(*) FROM contacts GROUP BY contact_type")
    print("\nContacts:")
    for row in cur:
        print(f"  {row[0]}: {row[1]:,}")

    # Top countries
    print("\nTop countries:")
    cur.execute("""
        SELECT country, COUNT(*) as cnt
        FROM companies
        WHERE country IS NOT NULL
        GROUP BY country
        ORDER BY cnt DESC
        LIMIT 10
    """)
    for row in cur:
        print(f"  {row[0]}: {row[1]:,}")


def verify_consolidation(pg_conn):
    """Verify consolidation was successful."""
    print("\n=== Verification ===\n")

    cur = pg_conn.cursor()

    # Check CAEN codes imported
    cur.execute("""
        SELECT COUNT(*) FROM companies
        WHERE country = 'RO' AND caen_code IS NOT NULL
    """)
    with_caen = cur.fetchone()[0]
    print(f"Romanian companies with CAEN: {with_caen:,}")

    # Check contacts
    cur.execute("""
        SELECT contact_type, COUNT(*)
        FROM contacts
        WHERE source = 'caen_import'
        GROUP BY contact_type
    """)
    imported = dict(cur.fetchall())
    print(f"Contacts imported from CAEN: {sum(imported.values()):,}")
    for ctype, count in imported.items():
        print(f"  {ctype}: {count:,}")

    # Sample verification
    print("\nSample CAEN codes:")
    cur.execute("""
        SELECT company_number, name, caen_code, caen_description
        FROM companies
        WHERE country = 'RO' AND caen_code IS NOT NULL
        LIMIT 5
    """)
    for row in cur:
        print(f"  {row[0]}: {row[1][:40]} - {row[2]} ({row[3][:30] if row[3] else 'N/A'})")

    # Check for indexing
    cur.execute("""
        SELECT indexname FROM pg_indexes
        WHERE tablename = 'companies' AND indexname = 'idx_companies_caen'
    """)
    if cur.fetchone():
        print("\nCAEN index: EXISTS")
    else:
        print("\nCAEN index: MISSING (run without --dry-run to create)")


def main():
    parser = argparse.ArgumentParser(
        description="Consolidate CAEN data into PostgreSQL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without modifying database")
    parser.add_argument("--stats", action="store_true", help="Show current database statistics")
    parser.add_argument("--verify", action="store_true", help="Verify consolidation results")
    parser.add_argument("--caen-only", action="store_true", help="Only import CAEN codes, skip contacts")
    parser.add_argument("--contacts-only", action="store_true", help="Only import contacts, skip CAEN codes")

    args = parser.parse_args()

    # Ensure log directory exists
    Path(LOG_FILE).parent.mkdir(parents=True, exist_ok=True)

    # Connect to databases
    pg_conn = get_postgres_conn()
    sqlite_conn = get_sqlite_conn()

    try:
        if args.stats:
            show_stats(pg_conn)
            return

        if args.verify:
            verify_consolidation(pg_conn)
            return

        start_time = datetime.now()
        logger.info("=" * 50)
        logger.info("Starting CAEN data consolidation")
        logger.info(f"Dry run: {args.dry_run}")
        logger.info("=" * 50)

        caen_updated = 0
        contacts_imported = 0

        if not args.contacts_only:
            # Step 1: Add CAEN columns
            if not add_caen_columns(pg_conn, args.dry_run):
                logger.error("Failed to add CAEN columns, aborting")
                return

            # Step 2: Import CAEN codes
            caen_updated = import_caen_codes(pg_conn, sqlite_conn, args.dry_run)

            # Step 3: Create CAEN index
            if not args.dry_run:
                create_caen_index(pg_conn, args.dry_run)

        if not args.caen_only:
            # Step 4: Import contacts
            contacts_imported = import_contacts(pg_conn, sqlite_conn, args.dry_run)

        elapsed = datetime.now() - start_time
        logger.info("=" * 50)
        logger.info("Consolidation complete!")
        logger.info(f"CAEN codes updated: {caen_updated:,}")
        logger.info(f"Contacts imported: {contacts_imported:,}")
        logger.info(f"Elapsed time: {elapsed}")
        logger.info("=" * 50)

        if not args.dry_run:
            send_telegram(f"CAEN consolidation complete: {caen_updated:,} CAEN codes, {contacts_imported:,} contacts in {elapsed}")

    finally:
        pg_conn.close()
        sqlite_conn.close()


if __name__ == "__main__":
    main()
