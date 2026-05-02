#!/usr/bin/env python3
"""
Build Master Companies Database
Consolidates all company data sources into one enriched database.

Sources:
1. CAEN Index (4.8M) - base
2. interjob_master companies - merge
3. ANAF API - enrich revenue/phone

Run: python3 /opt/ACTIVE/INFRA/SKILLS/build_master_companies.py
Schedule: Tonight (cron)
"""

import os
import sys
import csv
import json
import sqlite3
import psycopg2
import requests
import time
import logging
from datetime import datetime
from typing import Optional, Dict, List

# Setup logging
LOG_FILE = f"/opt/ACTIVE/INFRA/SKILLS/logs/master_companies_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Config
DB_CONFIG = {
    'host': 'localhost',
    'dbname': 'interjob_master',
    'user': 'tudor',
    'password': 'scraper123'
}

CAEN_DB = '/opt/ACTIVE/OPENDATA/DATA/CAEN_INDEX/caen_search.db'
ANAF_API_URL = 'https://webservicesp.anaf.ro/PlatitorTvaRest/api/v8/ws/tva'
ANAF_BATCH_SIZE = 500
ANAF_DELAY = 1  # seconds between batches


def get_pg_conn():
    return psycopg2.connect(**DB_CONFIG)


def create_master_table():
    """Create master_companies table if not exists."""
    logger.info("Creating master_companies table...")

    conn = get_pg_conn()
    cur = conn.cursor()

    cur.execute("""
        DROP TABLE IF EXISTS master_companies_new;

        CREATE TABLE master_companies_new (
            id SERIAL PRIMARY KEY,

            -- Identification
            cui VARCHAR(20),
            name VARCHAR(500),
            name_normalized VARCHAR(500),

            -- Contact
            email VARCHAR(255),
            email_verified BOOLEAN DEFAULT FALSE,
            phone VARCHAR(100),
            phone_verified BOOLEAN DEFAULT FALSE,
            website VARCHAR(500),

            -- Location
            country CHAR(2) DEFAULT 'RO',
            county VARCHAR(100),
            city VARCHAR(255),
            address TEXT,

            -- Business
            caen VARCHAR(10),
            caen_description VARCHAR(500),
            employees_count INT,
            revenue BIGINT,
            revenue_year INT,
            founded_date DATE,
            vat_registered BOOLEAN,
            status VARCHAR(50),

            -- Scoring
            lead_score INT DEFAULT 0,
            data_quality_score INT DEFAULT 0,

            -- Meta
            sources TEXT,
            last_enriched TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );

        CREATE INDEX idx_mc_cui ON master_companies_new(cui);
        CREATE INDEX idx_mc_county ON master_companies_new(county);
        CREATE INDEX idx_mc_caen ON master_companies_new(caen);
        CREATE INDEX idx_mc_revenue ON master_companies_new(revenue DESC NULLS LAST);
        CREATE INDEX idx_mc_email ON master_companies_new(email);
    """)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Table created successfully")


def import_caen_index():
    """Import base data from CAEN Index SQLite."""
    logger.info("Importing from CAEN Index...")

    sqlite_conn = sqlite3.connect(CAEN_DB)
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = get_pg_conn()
    pg_cur = pg_conn.cursor()

    # Count total
    sqlite_cur.execute("SELECT COUNT(*) FROM companies")
    total = sqlite_cur.fetchone()[0]
    logger.info(f"Total records in CAEN Index: {total:,}")

    # Import in batches
    batch_size = 10000
    imported = 0

    sqlite_cur.execute("""
        SELECT cui, company_name, company_name_normalized, email, phone,
               city, county, country, caen, caen_description
        FROM companies
    """)

    batch = []
    for row in sqlite_cur:
        cui, name, name_norm, email, phone, city, county, country, caen, caen_desc = row

        batch.append((
            cui, name, name_norm, email, phone, city, county,
            country or 'RO', caen, caen_desc, 'caen_index'
        ))

        if len(batch) >= batch_size:
            pg_cur.executemany("""
                INSERT INTO master_companies_new
                (cui, name, name_normalized, email, phone, city, county, country, caen, caen_description, sources)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, batch)
            pg_conn.commit()
            imported += len(batch)
            logger.info(f"Imported {imported:,} / {total:,} ({100*imported/total:.1f}%)")
            batch = []

    # Final batch
    if batch:
        pg_cur.executemany("""
            INSERT INTO master_companies_new
            (cui, name, name_normalized, email, phone, city, county, country, caen, caen_description, sources)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, batch)
        pg_conn.commit()
        imported += len(batch)

    logger.info(f"CAEN Index import complete: {imported:,} records")

    sqlite_cur.close()
    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()


def merge_interjob_master():
    """Merge data from interjob_master companies table."""
    logger.info("Merging interjob_master data...")

    conn = get_pg_conn()
    cur = conn.cursor()

    # Update existing records with additional data from companies table
    cur.execute("""
        UPDATE master_companies_new mc
        SET
            email = COALESCE(NULLIF(mc.email, ''), c.email),
            phone = COALESCE(NULLIF(mc.phone, ''), c.phone),
            website = COALESCE(mc.website, c.website),
            employees_count = COALESCE(mc.employees_count, c.employees_count),
            revenue = COALESCE(mc.revenue, c.revenue::bigint),
            sources = mc.sources || ',interjob_master'
        FROM companies c
        WHERE mc.cui IS NOT NULL
          AND mc.cui = c.cui
          AND c.country = 'RO'
    """)

    updated = cur.rowcount
    logger.info(f"Updated {updated:,} records from interjob_master")

    # Insert new records not in CAEN Index
    cur.execute("""
        INSERT INTO master_companies_new
        (cui, name, email, phone, website, city, county, country,
         employees_count, revenue, caen, caen_description, sources)
        SELECT
            c.cui, c.name, c.email, c.phone, c.website, c.city,
            NULL, c.country, c.employees_count, c.revenue::bigint,
            c.sector, c.sector_name, 'interjob_master'
        FROM companies c
        WHERE c.country = 'RO'
          AND c.cui IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM master_companies_new mc WHERE mc.cui = c.cui
          )
    """)

    inserted = cur.rowcount
    logger.info(f"Inserted {inserted:,} new records from interjob_master")

    conn.commit()
    cur.close()
    conn.close()


def enrich_anaf_batch(cuis: List[str]) -> Dict:
    """Call ANAF API for a batch of CUIs."""
    payload = [{"cui": int(cui), "data": datetime.now().strftime("%Y-%m-%d")} for cui in cuis if cui and cui.isdigit()]

    if not payload:
        return {}

    try:
        resp = requests.post(ANAF_API_URL, json=payload, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            results = {}
            for item in data.get('found', []):
                cui = str(item.get('date_generale', {}).get('cui', ''))
                if cui:
                    results[cui] = {
                        'phone': item.get('date_generale', {}).get('telefon', ''),
                        'address': item.get('date_generale', {}).get('adresa', ''),
                        'status': item.get('date_generale', {}).get('stare_inregistrare', ''),
                        'vat': item.get('date_generale', {}).get('scpTVA', False),
                        'caen': item.get('date_generale', {}).get('cod_CAEN', '')
                    }
            return results
    except Exception as e:
        logger.warning(f"ANAF API error: {e}")

    return {}


def enrich_with_anaf():
    """Enrich records with ANAF API data."""
    logger.info("Enriching with ANAF API...")

    conn = get_pg_conn()
    cur = conn.cursor()

    # Get CUIs that need enrichment (no phone or need verification)
    cur.execute("""
        SELECT id, cui FROM master_companies_new
        WHERE cui IS NOT NULL
          AND cui ~ '^[0-9]+$'
          AND (phone IS NULL OR phone = '' OR phone_verified = FALSE)
        ORDER BY revenue DESC NULLS LAST
        LIMIT 50000
    """)

    records = cur.fetchall()
    total = len(records)
    logger.info(f"Records to enrich: {total:,}")

    enriched = 0
    for i in range(0, total, ANAF_BATCH_SIZE):
        batch = records[i:i+ANAF_BATCH_SIZE]
        cuis = [r[1] for r in batch]
        id_map = {r[1]: r[0] for r in batch}

        results = enrich_anaf_batch(cuis)

        for cui, data in results.items():
            if cui in id_map:
                cur.execute("""
                    UPDATE master_companies_new
                    SET
                        phone = COALESCE(NULLIF(%s, ''), phone),
                        phone_verified = TRUE,
                        address = COALESCE(NULLIF(%s, ''), address),
                        status = COALESCE(NULLIF(%s, ''), status),
                        vat_registered = %s,
                        caen = COALESCE(NULLIF(%s, ''), caen),
                        last_enriched = NOW(),
                        sources = sources || ',anaf'
                    WHERE id = %s
                """, (
                    data.get('phone', ''),
                    data.get('address', ''),
                    data.get('status', ''),
                    data.get('vat', False),
                    data.get('caen', ''),
                    id_map[cui]
                ))
                enriched += 1

        conn.commit()

        if (i + ANAF_BATCH_SIZE) % 5000 == 0:
            logger.info(f"ANAF enriched: {enriched:,} / {i+len(batch):,}")

        time.sleep(ANAF_DELAY)

    cur.close()
    conn.close()
    logger.info(f"ANAF enrichment complete: {enriched:,} records updated")


def calculate_scores():
    """Calculate lead scores and data quality scores."""
    logger.info("Calculating scores...")

    conn = get_pg_conn()
    cur = conn.cursor()

    # Data quality score (0-100)
    cur.execute("""
        UPDATE master_companies_new
        SET data_quality_score = (
            CASE WHEN cui IS NOT NULL AND cui != '' THEN 20 ELSE 0 END +
            CASE WHEN email IS NOT NULL AND email != '' THEN 25 ELSE 0 END +
            CASE WHEN phone IS NOT NULL AND phone != '' THEN 25 ELSE 0 END +
            CASE WHEN revenue IS NOT NULL AND revenue > 0 THEN 15 ELSE 0 END +
            CASE WHEN caen IS NOT NULL AND caen != '' THEN 10 ELSE 0 END +
            CASE WHEN phone_verified THEN 5 ELSE 0 END
        )
    """)

    # Lead score based on business potential
    cur.execute("""
        UPDATE master_companies_new
        SET lead_score = (
            CASE
                WHEN revenue > 10000000 THEN 50  -- >10M RON
                WHEN revenue > 1000000 THEN 40   -- >1M RON
                WHEN revenue > 100000 THEN 30    -- >100K RON
                ELSE 10
            END +
            CASE
                WHEN employees_count > 50 THEN 30
                WHEN employees_count > 10 THEN 20
                WHEN employees_count > 0 THEN 10
                ELSE 0
            END +
            CASE WHEN email IS NOT NULL AND email != '' THEN 20 ELSE 0 END
        )
    """)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Scores calculated")


def deduplicate():
    """Remove duplicates, keeping best quality record."""
    logger.info("Deduplicating...")

    conn = get_pg_conn()
    cur = conn.cursor()

    # Remove duplicates by CUI, keeping highest data_quality_score
    cur.execute("""
        DELETE FROM master_companies_new a
        USING master_companies_new b
        WHERE a.cui = b.cui
          AND a.cui IS NOT NULL
          AND a.id > b.id
          AND a.data_quality_score <= b.data_quality_score
    """)

    deleted = cur.rowcount
    logger.info(f"Removed {deleted:,} duplicate records")

    conn.commit()
    cur.close()
    conn.close()


def finalize():
    """Swap tables and create final indexes."""
    logger.info("Finalizing...")

    conn = get_pg_conn()
    cur = conn.cursor()

    # Swap tables
    cur.execute("""
        DROP TABLE IF EXISTS master_companies_old;
        ALTER TABLE IF EXISTS master_companies RENAME TO master_companies_old;
        ALTER TABLE master_companies_new RENAME TO master_companies;
    """)

    # Final stats
    cur.execute("SELECT COUNT(*) FROM master_companies")
    total = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_companies WHERE email IS NOT NULL AND email != ''")
    with_email = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_companies WHERE phone IS NOT NULL AND phone != ''")
    with_phone = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_companies WHERE revenue > 0")
    with_revenue = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    logger.info("=" * 50)
    logger.info("MASTER COMPANIES BUILD COMPLETE")
    logger.info("=" * 50)
    logger.info(f"Total records: {total:,}")
    logger.info(f"With email: {with_email:,} ({100*with_email/total:.1f}%)")
    logger.info(f"With phone: {with_phone:,} ({100*with_phone/total:.1f}%)")
    logger.info(f"With revenue: {with_revenue:,} ({100*with_revenue/total:.1f}%)")

    return {
        'total': total,
        'with_email': with_email,
        'with_phone': with_phone,
        'with_revenue': with_revenue
    }


def main():
    logger.info("=" * 50)
    logger.info("STARTING MASTER COMPANIES BUILD")
    logger.info("=" * 50)

    start = datetime.now()

    try:
        create_master_table()
        import_caen_index()
        merge_interjob_master()
        enrich_with_anaf()
        calculate_scores()
        deduplicate()
        stats = finalize()

        duration = datetime.now() - start
        logger.info(f"Total duration: {duration}")

        # Save stats
        with open('/opt/ACTIVE/INFRA/SKILLS/master_companies_stats.json', 'w') as f:
            json.dump({
                'built_at': datetime.now().isoformat(),
                'duration_seconds': duration.total_seconds(),
                **stats
            }, f, indent=2)

    except Exception as e:
        logger.error(f"Build failed: {e}", exc_info=True)
        raise


if __name__ == '__main__':
    main()
