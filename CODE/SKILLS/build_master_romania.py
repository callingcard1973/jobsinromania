#!/usr/bin/env python3
"""
Build Master Romania Database
Consolidates ALL Romania company/contact data into one enriched database.

Sources:
1. CAEN Index (4.8M) - base companies
2. interjob_master companies RO (1M) - merge
3. interjob_master contacts (555K) - add contacts
4. ANOFM campaign (26K) - add contacts
5. Agencies RO (5K) - add agencies
6. opendata.companies (5.5M RO) - additional Romanian companies
7. opendata.contacts (RO only) - contact data with email/phone
8. SEAP contractors (2.1M) - public procurement winners
9. Faliment (222K) - insolvency status flags
10. Professional registries (auditors, evaluators, executors ~6K)
11. Cooperatives & Producers (produs montan 1.5K, ONGs 150K)
12. romania DB: ecologic_producers, food_companies_master, rnpm_enriched_producers, specialists
13. ANAF API - enrich revenue/phone

Run: python3 /opt/ACTIVE/INFRA/SKILLS/build_master_romania.py
"""

import os
import sys
import json
import sqlite3
import psycopg2
import requests
import time
import logging
import unicodedata
import re
from datetime import datetime
from typing import Optional, Dict, List

# Setup logging
LOG_DIR = "/opt/ACTIVE/INFRA/SKILLS/logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = f"{LOG_DIR}/master_romania_{datetime.now().strftime('%Y%m%d_%H%M')}.log"

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
SEAP_DIR = '/opt/ACTIVE/OPENDATA/DATA/ACHIZITII_PUBLICE'
DSVSA_CSV = '/mnt/hdd/USB_BACKUP/SCRAPER_DATA/csv/DSVSA/DSVSA_MASTER.csv'
ANAF_API_URL = 'https://webservicesp.anaf.ro/api/PlatitorTvaRest/v9/tva'
ANAF_BATCH_SIZE = 500
ANAF_DELAY = 1

# TEST MODE - set to True to import small sample from each source
TEST_MODE = False  # Set to False for full import
TEST_LIMIT = 10000  # Records per source in test mode

# opendata database config
OPENDATA_CONFIG = {
    'host': 'localhost',
    'dbname': 'opendata',
    'user': 'tudor',
    'password': 'scraper123'
}

# romania database config
ROMANIA_CONFIG = {
    'host': 'localhost',
    'dbname': 'romania',
    'user': 'tudor',
    'password': 'scraper123'
}


def to_ascii(text):
    """Convert text to ASCII."""
    if not text:
        return text
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii')


def normalize_phone(phone):
    """Normalize phone to +40XXXXXXXXX format."""
    if not phone:
        return None
    phone = re.sub(r'[^0-9+]', '', str(phone))
    if phone.startswith('00'):
        phone = '+' + phone[2:]
    elif phone.startswith('0') and len(phone) == 10:
        phone = '+4' + phone
    elif phone.startswith('4') and len(phone) == 11:
        phone = '+' + phone
    return phone if phone.startswith('+40') and len(phone) >= 12 else None


def normalize_cui(cui):
    """Normalize CUI to digits only."""
    if not cui:
        return None
    cui = re.sub(r'[^0-9]', '', str(cui))
    return cui if cui and len(cui) >= 2 else None


def get_pg_conn(dbname=None):
    config = DB_CONFIG.copy()
    if dbname:
        config['dbname'] = dbname
    return psycopg2.connect(**config)


def create_tables():
    """Create master tables."""
    logger.info("Creating master tables...")

    conn = get_pg_conn()
    cur = conn.cursor()

    # Master Companies
    cur.execute("""
        DROP TABLE IF EXISTS master_romania_companies_new CASCADE;

        CREATE TABLE master_romania_companies_new (
            id SERIAL PRIMARY KEY,

            -- Identification
            cui VARCHAR(20) UNIQUE,
            j_number VARCHAR(50),
            name TEXT,
            name_normalized TEXT,

            -- Contact
            email VARCHAR(255),
            email_secondary VARCHAR(255),
            phone VARCHAR(50),
            phone_secondary VARCHAR(50),
            website VARCHAR(500),

            -- Location
            county TEXT,
            city TEXT,
            address TEXT,
            postal_code VARCHAR(20),

            -- Business
            caen TEXT,
            caen_description TEXT,
            caen_secondary TEXT,
            legal_form TEXT,
            employees_count INT,
            revenue BIGINT,
            revenue_year INT,
            founded_date DATE,
            vat_registered BOOLEAN,
            status VARCHAR(100),

            -- Enrichment
            contact_name VARCHAR(255),
            contact_position VARCHAR(100),

            -- Flags
            is_insolvent BOOLEAN DEFAULT FALSE,
            insolvency_status VARCHAR(100),
            has_public_contracts BOOLEAN DEFAULT FALSE,
            public_contracts_count INT DEFAULT 0,
            public_contracts_value BIGINT DEFAULT 0,

            -- Scoring
            lead_score INT DEFAULT 0,
            data_quality INT DEFAULT 0,

            -- Meta
            sources TEXT,
            last_enriched TIMESTAMP,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    # Master Contacts (linked to companies)
    cur.execute("""
        DROP TABLE IF EXISTS master_romania_contacts_new CASCADE;

        CREATE TABLE master_romania_contacts_new (
            id SERIAL PRIMARY KEY,
            cui VARCHAR(20),
            company_name TEXT,

            -- Contact info
            name TEXT,
            email TEXT,
            phone VARCHAR(100),
            position TEXT,

            -- Source
            source VARCHAR(100),
            verified BOOLEAN DEFAULT FALSE,

            -- Meta
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Tables created")


def import_caen_index():
    """Import base data from CAEN Index."""
    logger.info(f"Importing CAEN Index {'(TEST MODE)' if TEST_MODE else '(4.8M records)'}...")

    sqlite_conn = sqlite3.connect(CAEN_DB)
    sqlite_cur = sqlite_conn.cursor()

    pg_conn = get_pg_conn()
    pg_cur = pg_conn.cursor()

    sqlite_cur.execute("SELECT COUNT(*) FROM companies WHERE country='RO'")
    total = sqlite_cur.fetchone()[0]
    logger.info(f"Total RO records: {total:,}")

    batch_size = 10000
    imported = 0

    limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""
    sqlite_cur.execute(f"""
        SELECT cui, company_name, company_name_normalized, email, phone,
               city, county, caen, caen_description
        FROM companies
        WHERE country = 'RO'
        {limit_clause}
    """)

    batch = []
    for row in sqlite_cur:
        cui, name, name_norm, email, phone, city, county, caen, caen_desc = row

        batch.append((
            normalize_cui(cui),
            to_ascii(name),
            to_ascii(name_norm),
            email,
            normalize_phone(phone),
            to_ascii(city),
            to_ascii(county),
            caen,
            to_ascii(caen_desc),
            'caen_index'
        ))

        if len(batch) >= batch_size:
            pg_cur.executemany("""
                INSERT INTO master_romania_companies_new
                (cui, name, name_normalized, email, phone, city, county, caen, caen_description, sources)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cui) DO UPDATE SET
                    email = COALESCE(NULLIF(master_romania_companies_new.email, ''), EXCLUDED.email),
                    phone = COALESCE(NULLIF(master_romania_companies_new.phone, ''), EXCLUDED.phone),
                    city = COALESCE(NULLIF(master_romania_companies_new.city, ''), EXCLUDED.city),
                    county = COALESCE(NULLIF(master_romania_companies_new.county, ''), EXCLUDED.county),
                    caen = COALESCE(NULLIF(master_romania_companies_new.caen, ''), EXCLUDED.caen),
                    sources = master_romania_companies_new.sources || ',' || EXCLUDED.sources
            """, batch)
            pg_conn.commit()
            imported += len(batch)
            if imported % 100000 == 0:
                logger.info(f"Imported {imported:,} / {total:,}")
            batch = []

    if batch:
        pg_cur.executemany("""
            INSERT INTO master_romania_companies_new
            (cui, name, name_normalized, email, phone, city, county, caen, caen_description, sources)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (cui) DO UPDATE SET
                email = COALESCE(NULLIF(master_romania_companies_new.email, ''), EXCLUDED.email),
                phone = COALESCE(NULLIF(master_romania_companies_new.phone, ''), EXCLUDED.phone),
                city = COALESCE(NULLIF(master_romania_companies_new.city, ''), EXCLUDED.city),
                county = COALESCE(NULLIF(master_romania_companies_new.county, ''), EXCLUDED.county),
                caen = COALESCE(NULLIF(master_romania_companies_new.caen, ''), EXCLUDED.caen),
                sources = master_romania_companies_new.sources || ',' || EXCLUDED.sources
        """, batch)
        pg_conn.commit()
        imported += len(batch)

    logger.info(f"CAEN Index complete: {imported:,}")

    sqlite_cur.close()
    sqlite_conn.close()
    pg_cur.close()
    pg_conn.close()


def merge_interjob_companies():
    """Merge interjob_master companies."""
    logger.info(f"Merging interjob_master companies {'(TEST MODE)' if TEST_MODE else '(1M)'}...")

    conn = get_pg_conn()
    cur = conn.cursor()

    limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""

    # Update existing (UPDATE doesn't support LIMIT directly in PostgreSQL)
    if TEST_MODE:
        cur.execute(f"""
            UPDATE master_romania_companies_new mc
            SET
                email = COALESCE(NULLIF(mc.email, ''), c.email),
                phone = COALESCE(NULLIF(mc.phone, ''), c.phone),
                website = COALESCE(mc.website, c.website),
                employees_count = COALESCE(mc.employees_count, c.employees_count),
                revenue = COALESCE(mc.revenue, c.revenue::bigint),
                sources = mc.sources || ',interjob'
            FROM (SELECT * FROM companies WHERE country = 'RO' LIMIT {TEST_LIMIT}) c
            WHERE mc.cui IS NOT NULL
              AND mc.cui = c.cui
        """)
    else:
        cur.execute("""
            UPDATE master_romania_companies_new mc
            SET
                email = COALESCE(NULLIF(mc.email, ''), c.email),
                phone = COALESCE(NULLIF(mc.phone, ''), c.phone),
                website = COALESCE(mc.website, c.website),
                employees_count = COALESCE(mc.employees_count, c.employees_count),
                revenue = COALESCE(mc.revenue, c.revenue::bigint),
                sources = mc.sources || ',interjob'
            FROM companies c
            WHERE mc.cui IS NOT NULL
              AND mc.cui = c.cui
              AND c.country = 'RO'
        """)
    updated = cur.rowcount
    logger.info(f"Updated {updated:,} from interjob_master")

    # Insert new (with ON CONFLICT to merge) - use subquery with DISTINCT ON to dedupe source
    cur.execute(f"""
        INSERT INTO master_romania_companies_new
        (cui, name, email, phone, website, city, employees_count, revenue, caen, caen_description, sources)
        SELECT cui, name, email, phone, website, city, employees_count, revenue, sector, sector_name, 'interjob'
        FROM (
            SELECT DISTINCT ON (c.cui)
                c.cui, c.name, c.email, c.phone, c.website, c.city,
                c.employees_count, c.revenue::bigint as revenue, c.sector, c.sector_name
            FROM companies c
            WHERE c.country = 'RO'
              AND c.cui IS NOT NULL
              AND c.cui != ''
            ORDER BY c.cui, c.email NULLS LAST
        ) deduped
        {limit_clause}
        ON CONFLICT (cui) DO UPDATE SET
            email = COALESCE(NULLIF(master_romania_companies_new.email, ''), EXCLUDED.email),
            phone = COALESCE(NULLIF(master_romania_companies_new.phone, ''), EXCLUDED.phone),
            website = COALESCE(master_romania_companies_new.website, EXCLUDED.website),
            employees_count = COALESCE(master_romania_companies_new.employees_count, EXCLUDED.employees_count),
            revenue = COALESCE(master_romania_companies_new.revenue, EXCLUDED.revenue),
            caen = COALESCE(NULLIF(master_romania_companies_new.caen, ''), EXCLUDED.caen),
            sources = master_romania_companies_new.sources || ',interjob'
    """)
    inserted = cur.rowcount
    logger.info(f"Inserted {inserted:,} new from interjob_master")

    conn.commit()
    cur.close()
    conn.close()


def import_contacts():
    """Import contacts from all sources."""
    logger.info(f"Importing contacts {'(TEST MODE)' if TEST_MODE else ''}...")

    conn = get_pg_conn()
    cur = conn.cursor()

    limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""

    # From interjob_master contacts - get ALL, no filtering
    cur.execute(f"""
        INSERT INTO master_romania_contacts_new (cui, company_name, name, email, phone, position, source)
        SELECT
            c.cui, comp.name, ct.name, ct.email, ct.phone, ct.position, 'interjob_contacts'
        FROM contacts ct
        LEFT JOIN companies comp ON ct.company_id = comp.id
        LEFT JOIN (SELECT DISTINCT cui, name FROM companies WHERE country='RO') c ON comp.name = c.name
        {limit_clause}
    """)
    contacts_interjob = cur.rowcount
    logger.info(f"Contacts from interjob: {contacts_interjob:,}")

    conn.commit()

    # From ANOFM campaign
    try:
        anofm_conn = get_pg_conn('anofm_campaign')
        anofm_cur = anofm_conn.cursor()

        limit_anofm = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""
        anofm_cur.execute(f"""
            SELECT cui, company_name, email, phone FROM contacts {limit_anofm}
        """)

        anofm_data = anofm_cur.fetchall()

        for cui, company, email, phone in anofm_data:
            cur.execute("""
                INSERT INTO master_romania_contacts_new (cui, company_name, email, phone, source)
                VALUES (%s, %s, %s, %s, 'anofm')
            """, (normalize_cui(cui), to_ascii(company), email, normalize_phone(phone)))

        conn.commit()
        logger.info(f"Contacts from ANOFM: {len(anofm_data):,}")

        anofm_cur.close()
        anofm_conn.close()
    except Exception as e:
        logger.warning(f"ANOFM import failed: {e}")

    # From agencies - get ALL
    cur.execute(f"""
        INSERT INTO master_romania_contacts_new (company_name, email, phone, source)
        SELECT name, email, phone, 'agencies'
        FROM agencies
        WHERE country = 'RO'
        {limit_clause}
    """)
    agencies = cur.rowcount
    logger.info(f"Contacts from agencies: {agencies:,}")

    conn.commit()
    cur.close()
    conn.close()


def import_opendata_companies():
    """Import Romanian companies from opendata database (5.5M RO only)."""
    logger.info(f"Importing opendata.companies {'(TEST MODE)' if TEST_MODE else '(Romania only)'}...")

    try:
        od_conn = psycopg2.connect(**OPENDATA_CONFIG)
        od_cur = od_conn.cursor()

        pg_conn = get_pg_conn()
        pg_cur = pg_conn.cursor()

        limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""
        # Get ONLY Romania companies from opendata - include ALL data
        od_cur.execute(f"""
            SELECT source_id, name, country, city, address, postal_code, region, caen_code, caen_description
            FROM companies
            WHERE country = 'RO'
            {limit_clause}
        """)

        batch = []
        imported = 0
        for row in od_cur:
            source_id, name, country, city, address, postal_code, region, caen, caen_desc = row
            # Import ALL - no filtering
            batch.append((
                to_ascii(name) if name else None,
                to_ascii(name.upper()) if name else None,
                to_ascii(city),
                to_ascii(address),
                postal_code,
                to_ascii(region),  # county
                caen,
                to_ascii(caen_desc),
                'opendata'
            ))

            if len(batch) >= 10000:
                pg_cur.executemany("""
                    INSERT INTO master_romania_companies_new
                    (name, name_normalized, city, address, postal_code, county, caen, caen_description, sources)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cui) DO UPDATE SET
                        city = COALESCE(NULLIF(master_romania_companies_new.city, ''), EXCLUDED.city),
                        address = COALESCE(NULLIF(master_romania_companies_new.address, ''), EXCLUDED.address),
                        postal_code = COALESCE(master_romania_companies_new.postal_code, EXCLUDED.postal_code),
                        county = COALESCE(NULLIF(master_romania_companies_new.county, ''), EXCLUDED.county),
                        caen = COALESCE(NULLIF(master_romania_companies_new.caen, ''), EXCLUDED.caen),
                        sources = master_romania_companies_new.sources || ',' || EXCLUDED.sources
                """, batch)
                pg_conn.commit()
                imported += len(batch)
                if imported % 100000 == 0:
                    logger.info(f"opendata imported: {imported:,}")
                batch = []

        if batch:
            pg_cur.executemany("""
                INSERT INTO master_romania_companies_new
                (name, name_normalized, city, address, postal_code, county, caen, caen_description, sources)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (cui) DO UPDATE SET
                    city = COALESCE(NULLIF(master_romania_companies_new.city, ''), EXCLUDED.city),
                    address = COALESCE(NULLIF(master_romania_companies_new.address, ''), EXCLUDED.address),
                    postal_code = COALESCE(master_romania_companies_new.postal_code, EXCLUDED.postal_code),
                    county = COALESCE(NULLIF(master_romania_companies_new.county, ''), EXCLUDED.county),
                    caen = COALESCE(NULLIF(master_romania_companies_new.caen, ''), EXCLUDED.caen),
                    sources = master_romania_companies_new.sources || ',' || EXCLUDED.sources
            """, batch)
            pg_conn.commit()
            imported += len(batch)

        logger.info(f"opendata.companies complete: {imported:,}")

        od_cur.close()
        od_conn.close()
        pg_cur.close()
        pg_conn.close()

    except Exception as e:
        logger.warning(f"opendata.companies import failed: {e}")


def import_opendata_contacts():
    """Import contacts from opendata database (Romania only)."""
    logger.info(f"Importing opendata.contacts {'(TEST MODE)' if TEST_MODE else '(Romania only)'}...")

    try:
        od_conn = psycopg2.connect(**OPENDATA_CONFIG)
        od_cur = od_conn.cursor()

        pg_conn = get_pg_conn()
        pg_cur = pg_conn.cursor()

        limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""
        # Get ALL contacts from Romania companies - no filtering
        od_cur.execute(f"""
            SELECT c.name, ct.contact_type, ct.contact_value
            FROM contacts ct
            JOIN companies c ON ct.company_id = c.id
            WHERE c.country = 'RO'
            {limit_clause}
        """)

        batch = []
        imported = 0
        for row in od_cur:
            company_name, contact_type, value = row
            # Import ALL - no filtering
            if contact_type == 'email':
                batch.append((
                    to_ascii(company_name),
                    value,
                    None,  # phone
                    'opendata_contacts'
                ))
            elif contact_type == 'phone':
                batch.append((
                    to_ascii(company_name),
                    None,  # email
                    normalize_phone(value) if value else None,
                    'opendata_contacts'
                ))
            else:
                # Any other contact type - store as-is
                batch.append((
                    to_ascii(company_name),
                    value if contact_type == 'email' else None,
                    normalize_phone(value) if contact_type == 'phone' else None,
                    'opendata_contacts'
                ))

            if len(batch) >= 10000:
                pg_cur.executemany("""
                    INSERT INTO master_romania_contacts_new
                    (company_name, email, phone, source)
                    VALUES (%s, %s, %s, %s)
                """, batch)
                pg_conn.commit()
                imported += len(batch)
                if imported % 100000 == 0:
                    logger.info(f"opendata contacts imported: {imported:,}")
                batch = []

        if batch:
            pg_cur.executemany("""
                INSERT INTO master_romania_contacts_new
                (company_name, email, phone, source)
                VALUES (%s, %s, %s, %s)
            """, batch)
            pg_conn.commit()
            imported += len(batch)

        logger.info(f"opendata.contacts complete: {imported:,}")

        od_cur.close()
        od_conn.close()
        pg_cur.close()
        pg_conn.close()

    except Exception as e:
        logger.warning(f"opendata.contacts import failed: {e}")


def import_seap_contractors():
    """Import SEAP public procurement contractors (2.1M)."""
    logger.info(f"Importing SEAP contractors {'(TEST MODE)' if TEST_MODE else ''}...")

    import csv

    pg_conn = get_pg_conn()
    pg_cur = pg_conn.cursor()

    seap_file = f"{SEAP_DIR}/achizitii_publice_2025_combined.csv"

    try:
        with open(seap_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            contractors = {}  # cui -> {count, total_value}
            row_count = 0

            for row in reader:
                if TEST_MODE and row_count >= TEST_LIMIT:
                    break
                row_count += 1
                cui = normalize_cui(row.get('CUI_OFERTANT_CASTIGATOR', ''))
                if not cui:
                    continue

                try:
                    value = float(row.get('VALOARE_CONTRACT_(RON)', 0) or 0)
                except:
                    value = 0

                if cui not in contractors:
                    contractors[cui] = {'count': 0, 'value': 0, 'name': row.get('OFERTANT_CASTIGATOR', '')}

                contractors[cui]['count'] += 1
                contractors[cui]['value'] += value

            logger.info(f"Unique SEAP contractors: {len(contractors):,}")

            # Update master table with SEAP data - batch with retry
            updated = 0
            batch = []
            for cui, data in contractors.items():
                batch.append((data['count'], int(data['value']), cui))

                if len(batch) >= 1000:
                    try:
                        pg_cur.executemany("""
                            UPDATE master_romania_companies_new
                            SET
                                has_public_contracts = TRUE,
                                public_contracts_count = %s,
                                public_contracts_value = %s,
                                sources = sources || ',seap'
                            WHERE cui = %s
                        """, batch)
                        updated += pg_cur.rowcount
                        pg_conn.commit()
                    except Exception as e:
                        logger.warning(f"SEAP batch error, retrying one by one: {e}")
                        pg_conn.rollback()
                        for b in batch:
                            try:
                                pg_cur.execute("""
                                    UPDATE master_romania_companies_new
                                    SET has_public_contracts = TRUE,
                                        public_contracts_count = %s,
                                        public_contracts_value = %s,
                                        sources = sources || ',seap'
                                    WHERE cui = %s
                                """, b)
                                if pg_cur.rowcount > 0:
                                    updated += 1
                                pg_conn.commit()
                            except:
                                pg_conn.rollback()
                    batch = []
                    if updated % 10000 == 0 and updated > 0:
                        logger.info(f"SEAP updated: {updated:,}")

            # Final batch
            if batch:
                try:
                    pg_cur.executemany("""
                        UPDATE master_romania_companies_new
                        SET has_public_contracts = TRUE,
                            public_contracts_count = %s,
                            public_contracts_value = %s,
                            sources = sources || ',seap'
                        WHERE cui = %s
                    """, batch)
                    updated += pg_cur.rowcount
                    pg_conn.commit()
                except:
                    pg_conn.rollback()

            logger.info(f"SEAP contractors complete: {updated:,} companies updated")

    except Exception as e:
        logger.warning(f"SEAP import failed: {e}")

    pg_cur.close()
    pg_conn.close()


def flag_faliment():
    """Flag insolvent companies from opendata.faliment (222K)."""
    logger.info(f"Flagging insolvent companies {'(TEST MODE)' if TEST_MODE else ''}...")

    try:
        od_conn = psycopg2.connect(**OPENDATA_CONFIG)
        od_cur = od_conn.cursor()

        pg_conn = get_pg_conn()
        pg_cur = pg_conn.cursor()

        limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""
        # Get all faliment CUIs
        od_cur.execute(f"""
            SELECT cui, status_name FROM faliment
            WHERE cui IS NOT NULL AND cui != ''
            {limit_clause}
        """)

        faliment_data = od_cur.fetchall()
        logger.info(f"Faliment records: {len(faliment_data):,}")

        updated = 0
        for cui, status in faliment_data:
            cui_clean = normalize_cui(cui)
            if not cui_clean:
                continue

            pg_cur.execute("""
                UPDATE master_romania_companies_new
                SET
                    is_insolvent = TRUE,
                    insolvency_status = %s,
                    sources = sources || ',faliment'
                WHERE cui = %s
            """, (status, cui_clean))

            if pg_cur.rowcount > 0:
                updated += 1

            if updated % 10000 == 0 and updated > 0:
                pg_conn.commit()

        pg_conn.commit()
        logger.info(f"Faliment flags complete: {updated:,} companies flagged")

        od_cur.close()
        od_conn.close()
        pg_cur.close()
        pg_conn.close()

    except Exception as e:
        logger.warning(f"Faliment flagging failed: {e}")


def import_professional_registries():
    """Import professional registries (auditors, evaluators, executors)."""
    logger.info(f"Importing professional registries {'(TEST MODE)' if TEST_MODE else ''}...")

    conn = get_pg_conn()
    cur = conn.cursor()

    limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""

    # Auditori financiari - ALL records, no filtering
    try:
        cur.execute(f"""
            INSERT INTO master_romania_contacts_new
            (name, email, position, source)
            SELECT "Nume, prenume", "E-mail", 'Auditor Financiar', 'auditori_financiari'
            FROM auditori_financiari
            {limit_clause}
        """)
        conn.commit()
        auditori = cur.rowcount
        logger.info(f"Auditori financiari: {auditori:,}")
    except Exception as e:
        logger.warning(f"Auditori import failed: {e}")
        conn.rollback()
        auditori = 0

    # Anevar evaluatori - ALL records, no filtering
    try:
        cur.execute(f"""
            INSERT INTO master_romania_contacts_new
            (name, email, phone, position, source)
            SELECT name, email, phone, 'Evaluator ANEVAR', 'anevar_evaluatori'
            FROM anevar_evaluatori
            {limit_clause}
        """)
        conn.commit()
        anevar = cur.rowcount
        logger.info(f"ANEVAR evaluatori: {anevar:,}")
    except Exception as e:
        logger.warning(f"ANEVAR import failed: {e}")
        conn.rollback()
        anevar = 0

    # Executori - ALL records, no filtering
    try:
        cur.execute(f"""
            INSERT INTO master_romania_contacts_new
            (name, email, phone, position, source)
            SELECT CONCAT(nume, ' ', prenume), email, telefon, 'Executor Judecatoresc', 'executori'
            FROM executori
            {limit_clause}
        """)
        conn.commit()
        executori = cur.rowcount
        logger.info(f"Executori: {executori:,}")
    except Exception as e:
        logger.warning(f"Executori import failed: {e}")
        conn.rollback()
        executori = 0

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Professional registries complete: {auditori + anevar + executori:,} contacts")


def import_cooperatives_producers():
    """Import cooperatives and producers (produs montan, ONGs, ecological)."""
    logger.info(f"Importing cooperatives and producers {'(TEST MODE)' if TEST_MODE else ''}...")

    conn = get_pg_conn()
    cur = conn.cursor()

    limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""

    # Produs Montan producers (1.5K) - ALL records, no filtering
    try:
        cur.execute(f"""
            INSERT INTO master_romania_contacts_new
            (company_name, email, phone, source)
            SELECT name, email, phone, 'produs_montan'
            FROM produs_montan_producers
            {limit_clause}
        """)
        produs_montan = cur.rowcount
        logger.info(f"Produs Montan producers: {produs_montan:,}")
    except Exception as e:
        logger.warning(f"Produs Montan import failed: {e}")
        produs_montan = 0

    # ONG Registry (150K) - ALL records, no filtering
    try:
        cur.execute(f"""
            INSERT INTO master_romania_companies_new
            (name, name_normalized, county, city, address, legal_form, sources)
            SELECT
                denumire,
                UPPER(denumire),
                judet,
                localitate,
                adresa,
                categorie,
                'ong_registry'
            FROM ong_registry_mj
            {limit_clause}
            ON CONFLICT (cui) DO UPDATE SET
                county = COALESCE(NULLIF(master_romania_companies_new.county, ''), EXCLUDED.county),
                city = COALESCE(NULLIF(master_romania_companies_new.city, ''), EXCLUDED.city),
                address = COALESCE(NULLIF(master_romania_companies_new.address, ''), EXCLUDED.address),
                legal_form = COALESCE(master_romania_companies_new.legal_form, EXCLUDED.legal_form),
                sources = master_romania_companies_new.sources || ',ong_registry'
        """)
        ongs = cur.rowcount
        logger.info(f"ONG registry: {ongs:,}")
    except Exception as e:
        logger.warning(f"ONG import failed: {e}")
        ongs = 0

    # Look for cooperatives by name pattern in existing data
    try:
        cur.execute("""
            UPDATE master_romania_companies_new
            SET legal_form = 'COOPERATIVA'
            WHERE legal_form IS NULL
              AND (name ILIKE '%COOPERATIV%' OR name ILIKE '%COOP %' OR name ILIKE '% CAP %')
        """)
        coops_flagged = cur.rowcount
        logger.info(f"Cooperatives flagged: {coops_flagged:,}")
    except Exception as e:
        logger.warning(f"Cooperative flagging failed: {e}")

    conn.commit()
    cur.close()
    conn.close()

    logger.info(f"Cooperatives/producers complete: {produs_montan + ongs:,}")


def import_romania_db():
    """Import ALL data from romania database (ecologic, food, rnpm, specialists)."""
    logger.info(f"Importing romania database tables {'(TEST MODE)' if TEST_MODE else ''}...")

    try:
        ro_conn = psycopg2.connect(**ROMANIA_CONFIG)
        ro_cur = ro_conn.cursor()

        pg_conn = get_pg_conn()
        pg_cur = pg_conn.cursor()

        total_imported = 0
        limit_clause = f"LIMIT {TEST_LIMIT}" if TEST_MODE else ""

        # 1. ecologic_producers - ALL records
        try:
            ro_cur.execute(f"""
                SELECT company_name, cui, email, phone, website FROM ecologic_producers {limit_clause}
            """)
            for row in ro_cur:
                name, cui, email, phone, website = row
                pg_cur.execute("""
                    INSERT INTO master_romania_contacts_new
                    (company_name, cui, email, phone, source)
                    VALUES (%s, %s, %s, %s, 'ecologic_producers')
                """, (to_ascii(name), normalize_cui(cui), email, normalize_phone(phone)))
            ecologic = ro_cur.rowcount
            pg_conn.commit()
            logger.info(f"ecologic_producers: {ecologic:,}")
            total_imported += ecologic
        except Exception as e:
            logger.warning(f"ecologic_producers failed: {e}")
            pg_conn.rollback()

        # 2. food_companies_master - ALL records
        try:
            ro_cur.execute(f"""
                SELECT name, cui, county, city, address, phone, email, website, sector, sector_name
                FROM food_companies_master {limit_clause}
            """)
            batch = []
            for row in ro_cur:
                name, cui, county, city, address, phone, email, website, caen, caen_desc = row
                batch.append((
                    normalize_cui(cui),
                    to_ascii(name),
                    to_ascii(name.upper()) if name else None,
                    email,
                    normalize_phone(phone),
                    website,
                    to_ascii(county),
                    to_ascii(city),
                    to_ascii(address),
                    caen,
                    to_ascii(caen_desc),
                    'food_companies'
                ))
                if len(batch) >= 5000:
                    pg_cur.executemany("""
                        INSERT INTO master_romania_companies_new
                        (cui, name, name_normalized, email, phone, website, county, city, address, caen, caen_description, sources)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (cui) DO UPDATE SET
                            email = COALESCE(NULLIF(master_romania_companies_new.email, ''), EXCLUDED.email),
                            phone = COALESCE(NULLIF(master_romania_companies_new.phone, ''), EXCLUDED.phone),
                            website = COALESCE(master_romania_companies_new.website, EXCLUDED.website),
                            address = COALESCE(NULLIF(master_romania_companies_new.address, ''), EXCLUDED.address),
                            sources = master_romania_companies_new.sources || ',food_companies'
                    """, batch)
                    pg_conn.commit()
                    batch = []
            if batch:
                pg_cur.executemany("""
                    INSERT INTO master_romania_companies_new
                    (cui, name, name_normalized, email, phone, website, county, city, address, caen, caen_description, sources)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cui) DO UPDATE SET
                        email = COALESCE(NULLIF(master_romania_companies_new.email, ''), EXCLUDED.email),
                        phone = COALESCE(NULLIF(master_romania_companies_new.phone, ''), EXCLUDED.phone),
                        website = COALESCE(master_romania_companies_new.website, EXCLUDED.website),
                        address = COALESCE(NULLIF(master_romania_companies_new.address, ''), EXCLUDED.address),
                        sources = master_romania_companies_new.sources || ',food_companies'
                """, batch)
                pg_conn.commit()
            food = len(batch)
            logger.info(f"food_companies_master: imported")
            total_imported += food
        except Exception as e:
            logger.warning(f"food_companies_master failed: {e}")
            pg_conn.rollback()

        # 3. rnpm_enriched_producers - ALL records
        try:
            ro_cur.execute(f"""
                SELECT producer_name, county, address, phone, email FROM rnpm_enriched_producers {limit_clause}
            """)
            for row in ro_cur:
                name, county, address, phone, email = row
                pg_cur.execute("""
                    INSERT INTO master_romania_contacts_new
                    (company_name, email, phone, source)
                    VALUES (%s, %s, %s, 'rnpm_producers')
                """, (to_ascii(name), email, normalize_phone(phone)))
            rnpm = ro_cur.rowcount
            pg_conn.commit()
            logger.info(f"rnpm_enriched_producers: {rnpm:,}")
            total_imported += rnpm
        except Exception as e:
            logger.warning(f"rnpm_enriched_producers failed: {e}")

        # 4. specialists - ALL records (if exists)
        try:
            ro_cur.execute(f"""
                SELECT name, email, phone, specialization FROM specialists {limit_clause}
            """)
            for row in ro_cur:
                name, email, phone, specialty = row
                pg_cur.execute("""
                    INSERT INTO master_romania_contacts_new
                    (name, email, phone, position, source)
                    VALUES (%s, %s, %s, %s, 'specialists')
                """, (to_ascii(name), email, normalize_phone(phone), to_ascii(specialty)))
            specialists = ro_cur.rowcount
            pg_conn.commit()
            logger.info(f"specialists: {specialists:,}")
            total_imported += specialists
        except Exception as e:
            logger.warning(f"specialists failed: {e}")

        ro_cur.close()
        ro_conn.close()
        pg_cur.close()
        pg_conn.close()

        logger.info(f"romania database complete: {total_imported:,} records")

    except Exception as e:
        logger.warning(f"romania database import failed: {e}")


def import_dsvsa():
    """Import DSVSA food safety registered companies (309K)."""
    logger.info(f"Importing DSVSA {'(TEST MODE)' if TEST_MODE else '(309K records)'}...")

    import csv

    pg_conn = get_pg_conn()
    pg_cur = pg_conn.cursor()

    try:
        with open(DSVSA_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            batch = []
            imported = 0
            row_count = 0

            for row in reader:
                if TEST_MODE and row_count >= TEST_LIMIT:
                    break
                row_count += 1

                name = row.get('company_name', '')
                name_norm = row.get('company_normalized', '')
                city = row.get('city', '')
                county = row.get('county', '')
                address = row.get('address', '')
                category = row.get('category', '')
                activity = row.get('activity_type', '')

                batch.append((
                    to_ascii(name),
                    to_ascii(name_norm) or to_ascii(name.upper()) if name else None,
                    to_ascii(city),
                    to_ascii(county),
                    to_ascii(address),
                    f"{category} - {activity}" if category and activity else category or activity,
                    'dsvsa'
                ))

                if len(batch) >= 5000:
                    pg_cur.executemany("""
                        INSERT INTO master_romania_companies_new
                        (name, name_normalized, city, county, address, caen_description, sources)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (cui) DO UPDATE SET
                            city = COALESCE(NULLIF(master_romania_companies_new.city, ''), EXCLUDED.city),
                            county = COALESCE(NULLIF(master_romania_companies_new.county, ''), EXCLUDED.county),
                            address = COALESCE(NULLIF(master_romania_companies_new.address, ''), EXCLUDED.address),
                            sources = master_romania_companies_new.sources || ',dsvsa'
                    """, batch)
                    pg_conn.commit()
                    imported += len(batch)
                    if imported % 50000 == 0:
                        logger.info(f"DSVSA imported: {imported:,}")
                    batch = []

            if batch:
                pg_cur.executemany("""
                    INSERT INTO master_romania_companies_new
                    (name, name_normalized, city, county, address, caen_description, sources)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (cui) DO UPDATE SET
                        city = COALESCE(NULLIF(master_romania_companies_new.city, ''), EXCLUDED.city),
                        county = COALESCE(NULLIF(master_romania_companies_new.county, ''), EXCLUDED.county),
                        address = COALESCE(NULLIF(master_romania_companies_new.address, ''), EXCLUDED.address),
                        sources = master_romania_companies_new.sources || ',dsvsa'
                """, batch)
                pg_conn.commit()
                imported += len(batch)

            logger.info(f"DSVSA complete: {imported:,}")

    except Exception as e:
        logger.warning(f"DSVSA import failed: {e}")

    pg_cur.close()
    pg_conn.close()


def enrich_with_anaf():
    """Enrich top companies with ANAF API."""
    if TEST_MODE:
        logger.info("ANAF enrichment SKIPPED (TEST MODE)")
        return

    logger.info("Enriching with ANAF API (top 50K by data quality)...")

    conn = get_pg_conn()
    cur = conn.cursor()

    # Get CUIs needing enrichment
    cur.execute("""
        SELECT id, cui FROM master_romania_companies_new
        WHERE cui IS NOT NULL
          AND cui ~ '^[0-9]+$'
          AND (phone IS NULL OR vat_registered IS NULL)
        ORDER BY
            CASE WHEN email IS NOT NULL THEN 1 ELSE 2 END,
            id
        LIMIT 50000
    """)

    records = cur.fetchall()
    total = len(records)
    logger.info(f"Records to enrich: {total:,}")

    if total == 0:
        logger.warning("No records found for ANAF enrichment - checking why...")
        cur.execute("SELECT COUNT(*) FROM master_romania_companies_new WHERE cui IS NOT NULL")
        has_cui = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM master_romania_companies_new WHERE cui ~ '^[0-9]+$'")
        numeric_cui = cur.fetchone()[0]
        logger.info(f"  Records with CUI: {has_cui:,}, numeric CUI: {numeric_cui:,}")

    enriched = 0
    api_errors = 0
    for i in range(0, total, ANAF_BATCH_SIZE):
        batch = records[i:i+ANAF_BATCH_SIZE]
        cuis = [r[1] for r in batch]
        id_map = {r[1]: r[0] for r in batch}

        payload = [{"cui": int(cui), "data": datetime.now().strftime("%Y-%m-%d")}
                   for cui in cuis if cui and cui.isdigit()]

        if not payload:
            continue

        try:
            resp = requests.post(ANAF_API_URL, json=payload, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                found_count = len(data.get('found', []))
                for item in data.get('found', []):
                    dg = item.get('date_generale', {})
                    cui = str(dg.get('cui', ''))
                    if cui in id_map:
                        cur.execute("""
                            UPDATE master_romania_companies_new
                            SET
                                phone = COALESCE(NULLIF(%s, ''), phone),
                                address = COALESCE(NULLIF(%s, ''), address),
                                status = COALESCE(NULLIF(%s, ''), status),
                                vat_registered = %s,
                                caen = COALESCE(NULLIF(%s, ''), caen),
                                last_enriched = NOW(),
                                sources = sources || ',anaf'
                            WHERE id = %s
                        """, (
                            normalize_phone(dg.get('telefon', '')),
                            to_ascii(dg.get('adresa', '')),
                            dg.get('stare_inregistrare', ''),
                            dg.get('scpTVA', False),
                            dg.get('cod_CAEN', ''),
                            id_map[cui]
                        ))
                        enriched += 1

            else:
                api_errors += 1
                if api_errors <= 3:
                    logger.warning(f"ANAF API error: status {resp.status_code}")
        except Exception as e:
            api_errors += 1
            if api_errors <= 3:
                logger.warning(f"ANAF batch error: {e}")

        conn.commit()

        if (i + ANAF_BATCH_SIZE) % 5000 == 0:
            logger.info(f"ANAF progress: {i+len(batch):,} / {total:,}, enriched: {enriched:,}, errors: {api_errors}")

        time.sleep(ANAF_DELAY)

    cur.close()
    conn.close()
    logger.info(f"ANAF enrichment complete: {enriched:,}")


def calculate_scores():
    """Calculate lead and data quality scores."""
    logger.info("Calculating scores...")

    conn = get_pg_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE master_romania_companies_new
        SET
            data_quality = (
                CASE WHEN cui IS NOT NULL THEN 15 ELSE 0 END +
                CASE WHEN email IS NOT NULL AND email != '' THEN 25 ELSE 0 END +
                CASE WHEN phone IS NOT NULL AND phone != '' THEN 25 ELSE 0 END +
                CASE WHEN revenue > 0 THEN 20 ELSE 0 END +
                CASE WHEN caen IS NOT NULL THEN 10 ELSE 0 END +
                CASE WHEN address IS NOT NULL THEN 5 ELSE 0 END
            ),
            lead_score = (
                CASE
                    WHEN revenue > 50000000 THEN 100
                    WHEN revenue > 10000000 THEN 80
                    WHEN revenue > 1000000 THEN 60
                    WHEN revenue > 100000 THEN 40
                    ELSE 20
                END +
                CASE WHEN employees_count > 50 THEN 20 WHEN employees_count > 10 THEN 10 ELSE 0 END
            )
    """)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Scores calculated")


def create_indexes():
    """Create indexes for fast queries."""
    logger.info("Creating indexes...")

    conn = get_pg_conn()
    cur = conn.cursor()

    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_mr_cui ON master_romania_companies_new(cui)",
        "CREATE INDEX IF NOT EXISTS idx_mr_email ON master_romania_companies_new(email)",
        "CREATE INDEX IF NOT EXISTS idx_mr_county ON master_romania_companies_new(county)",
        "CREATE INDEX IF NOT EXISTS idx_mr_caen ON master_romania_companies_new(caen)",
        "CREATE INDEX IF NOT EXISTS idx_mr_revenue ON master_romania_companies_new(revenue DESC NULLS LAST)",
        "CREATE INDEX IF NOT EXISTS idx_mr_lead ON master_romania_companies_new(lead_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_mr_quality ON master_romania_companies_new(data_quality DESC)",
        "CREATE INDEX IF NOT EXISTS idx_mrc_email ON master_romania_contacts_new(email)",
        "CREATE INDEX IF NOT EXISTS idx_mrc_cui ON master_romania_contacts_new(cui)",
    ]

    for idx in indexes:
        cur.execute(idx)

    conn.commit()
    cur.close()
    conn.close()
    logger.info("Indexes created")


def finalize():
    """Swap tables and generate stats."""
    logger.info("Finalizing...")

    conn = get_pg_conn()
    cur = conn.cursor()

    # Swap companies
    cur.execute("""
        DROP TABLE IF EXISTS master_romania_companies_old CASCADE;
        ALTER TABLE IF EXISTS master_romania_companies RENAME TO master_romania_companies_old;
        ALTER TABLE master_romania_companies_new RENAME TO master_romania_companies;
    """)

    # Swap contacts
    cur.execute("""
        DROP TABLE IF EXISTS master_romania_contacts_old CASCADE;
        ALTER TABLE IF EXISTS master_romania_contacts RENAME TO master_romania_contacts_old;
        ALTER TABLE master_romania_contacts_new RENAME TO master_romania_contacts;
    """)

    # Stats
    cur.execute("SELECT COUNT(*) FROM master_romania_companies")
    total_companies = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_romania_companies WHERE email IS NOT NULL AND email != ''")
    with_email = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_romania_companies WHERE phone IS NOT NULL AND phone != ''")
    with_phone = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_romania_companies WHERE revenue > 0")
    with_revenue = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_romania_companies WHERE revenue > 1000000")
    revenue_1m = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_romania_companies WHERE is_insolvent = TRUE")
    insolvent = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM master_romania_companies WHERE has_public_contracts = TRUE")
    with_contracts = cur.fetchone()[0]

    cur.execute("SELECT SUM(public_contracts_value) FROM master_romania_companies")
    total_contract_value = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM master_romania_contacts")
    total_contacts = cur.fetchone()[0]

    conn.commit()
    cur.close()
    conn.close()

    stats = {
        'total_companies': int(total_companies),
        'with_email': int(with_email),
        'with_phone': int(with_phone),
        'with_revenue': int(with_revenue),
        'revenue_over_1m': int(revenue_1m),
        'insolvent_flagged': int(insolvent),
        'with_public_contracts': int(with_contracts),
        'total_contract_value_ron': int(total_contract_value),
        'total_contacts': int(total_contacts)
    }

    logger.info("=" * 60)
    logger.info("MASTER ROMANIA BUILD COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Companies: {total_companies:,}")
    if total_companies > 0:
        logger.info(f"  with email: {with_email:,} ({100*float(with_email)/float(total_companies):.1f}%)")
        logger.info(f"  with phone: {with_phone:,} ({100*float(with_phone)/float(total_companies):.1f}%)")
    logger.info(f"  with revenue: {with_revenue:,}")
    logger.info(f"  revenue > 1M RON: {revenue_1m:,}")
    logger.info(f"  insolvent (flagged): {insolvent:,}")
    logger.info(f"  with public contracts: {with_contracts:,}")
    logger.info(f"  total contract value: {float(total_contract_value)/1e9:.2f}B RON")
    logger.info(f"Contacts: {total_contacts:,}")

    return stats


def main():
    logger.info("=" * 60)
    logger.info(f"STARTING MASTER ROMANIA BUILD {'(TEST MODE)' if TEST_MODE else '(FULL)'}")
    logger.info(f"Time: {datetime.now()}")
    if TEST_MODE:
        logger.info(f"TEST_LIMIT: {TEST_LIMIT} records per source")
    logger.info("=" * 60)

    start = datetime.now()
    errors = []

    create_tables()

    # Run each import and collect errors
    imports = [
        ("CAEN Index", import_caen_index),
        ("Interjob Companies", merge_interjob_companies),
        ("Opendata Companies", import_opendata_companies),
        ("Contacts", import_contacts),
        ("Opendata Contacts", import_opendata_contacts),
        ("Professional Registries", import_professional_registries),
        ("Cooperatives/Producers", import_cooperatives_producers),
        ("Romania DB", import_romania_db),
        ("DSVSA", import_dsvsa),
        ("SEAP Contractors", import_seap_contractors),
        ("Faliment Flags", flag_faliment),
        ("ANAF Enrichment", enrich_with_anaf),
    ]

    for name, func in imports:
        try:
            func()
        except Exception as e:
            logger.error(f"ERROR in {name}: {e}")
            errors.append((name, str(e)))

    # Final steps
    try:
        calculate_scores()
        create_indexes()
        stats = finalize()
    except Exception as e:
        logger.error(f"ERROR in finalize: {e}")
        errors.append(("Finalize", str(e)))
        stats = {}

    duration = datetime.now() - start
    logger.info(f"Total duration: {duration}")

    # Report all errors
    if errors:
        logger.error("=" * 60)
        logger.error(f"ERRORS FOUND: {len(errors)}")
        for name, err in errors:
            logger.error(f"  - {name}: {err}")
        logger.error("=" * 60)

    # Save stats
    stats['built_at'] = datetime.now().isoformat()
    stats['duration_seconds'] = duration.total_seconds()
    stats['errors'] = errors

    with open('/opt/ACTIVE/INFRA/SKILLS/master_romania_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)


if __name__ == '__main__':
    main()
