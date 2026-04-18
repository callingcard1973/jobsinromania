#!/usr/bin/env python3
"""
CAP Federation Quick Setup Script

Initializes the CAP federation infrastructure:
1. Creates database tables (if not exists)
2. Inserts sample cooperative data
3. Loads sample SEAP contracts
4. Verifies all components are ready

Run this once to initialize the system.
"""

import sys
import psycopg2
import logging
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

# Configuration
DB_NAME = "interjob_master"
DB_USER = "tudor"
DB_HOST = "localhost"
SQL_FILE = Path("/opt/ACTIVE/IDEAS/NATO/OPENCODE/data/cap_schema.sql")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)


def check_password():
    """Check if database password is set in environment."""
    import os

    # Check for password in common env files
    env_files = [
        "/opt/ACTIVE/.env",
        "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env",
        "/opt/ACTIVE/INFRA/SKILLS/.env",
    ]

    for env_file in env_files:
        if env_file.exists():
            try:
                with open(env_file) as f:
                    content = f.read()
                    if "DB_PASSWORD" in content or "POSTGRES_PASSWORD" in content:
                        log.info(f"✓ Database password found in: {env_file}")
            except:
                pass

    log.info(
        "Tip: If PostgreSQL requires password, set PGPASSWORD environment variable"
    )


def create_sample_coops(cursor, num_samples: int = 20):
    """Insert sample cooperative data for testing."""
    log.info(f"Creating {num_samples} sample cooperatives...")

    counties = [
        "Constanța",
        "Brașov",
        "Arad",
        "Timiș",
        "Dolj",
        "Iași",
        "Cluj",
        "Mureș",
        "Sibiu",
        "Bacău",
        "Bihor",
        "Alba",
        "Galați",
        "Vâlcea",
        "Prahova",
    ]

    products_combinations = [
        ["wheat", "barley"],
        ["rice", "vegetables"],
        ["potatoes", "vegetables"],
        ["wheat", "maize", "grains"],
        ["honey"],
        ["meat", "dairy"],
        ["fruits", "vegetables"],
        ["cereals", "grains"],
    ]

    certifications = ["NONE", "HACCP", "ISO_9001", "ISO_22000"]

    sample_coops = []
    for i in range(num_samples):
        county = counties[i % len(counties)]
        products = products_combinations[i % len(products_combinations)]
        capacity = 500 + (i * 100) + (hash(i) % 500)  # 500-2000 tons

        sample_coops.append(
            {
                "name": f"Cooperativa Agricola {county} #{i + 1}",
                "county": county,
                "capacity_annual_tons": capacity,
                "products": products,
                "email": f"contact@coope-{county.lower()}-{i + 1}.ro",
                "phone": f"+40 7{str(i).zfill(2)} {str(i + 100).zfill(3)} {str(i + 1000).zfill(4)}",
                "certification_status": certifications[i % len(certifications)],
                "status": "PROSPECT",
            }
        )

    # Insert into database
    inserted = 0
    for coop in sample_coops:
        try:
            # Products should be PostgreSQL array
            products_array = f"ARRAY{str(coop['products'])}"

            query = """
                INSERT INTO cap_cooperatives (name, county, capacity_annual_tons, products, email, phone, certification_status, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (name) DO NOTHING
            """

            cursor.execute(
                query,
                (
                    coop["name"],
                    coop["county"],
                    coop["capacity_annual_tons"],
                    coop["products"],
                    coop["email"],
                    coop["run_phone"],
                    coop["certification_status"],
                    coop["status"],
                ),
            )

            inserted += 1

        except Exception as e:
            log.warning(f"Failed to insert coop {coop['name']}: {e}")

    log.info(f"✓ Inserted {inserted}/{num_samples} sample cooperatives")


def create_sample_contracts(cursor, num_samples: int = 10):
    """Insert sample contract data for testing."""
    log.info(f"Creating {num_samples} sample contracts...")

    contracts = [
        {
            "contract_name": "SEAP Food Supply - Honey",
            "contract_id": f"seap_{datetime.now().strftime('%Y%m%d')}_001_{i}",
            "buyer_name": "Direcția Generală de Asistență Socială",
            "buyer_type": "SEAP",
            "buyer_county": "București",
            "value_eur": 75000.0 + (i * 25000),
            "cpv_code": "04090000-0",
            "cpv_description": "Miere naturală",
            "status": "OPPORTUNITY",
        }
        if i == 0
        else {
            "contract_name": f"SEAP Contract {i} - Agricultural Products",
            "contract_id": f"seap_{datetime.now().strftime('%Y%m%d')}_{i + 1:03d}_",
            "buyer_name": [
                "Ministerul Apărării",
                "Consiliul Județean",
                "Spital Militar",
            ][i % 3],
            "buyer_type": "MILITARY" if i % 3 == 0 else "SEAP",
            "buyer_county": counties[i % len(counties)],
            "value_eur": 50000.0 + (i * 10000),
            "cpv_code": "15112000-6" if i % 2 == 0 else "03112000-1",
            "cpv_description": "Carne de pascăre" if i % 2 == 0 else "Fructe și legume",
            "status": "OPPORTUNITY",
        }
        for i in range(1, num_samples + 1)
    ]

    # Insert into database
    inserted = 0
    for contract in contracts:
        try:
            query = """
                INSERT INTO cap_contracts (contract_name, contract_id, buyer_name, buyer_type, buyer_county, value_eur, cpv_code, cpv_description, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (contract_id) DO NOTHING
            """

            cursor.execute(
                query,
                (
                    contract["contract_name"],
                    contract["contract_id"],
                    contract["buyer_name"],
                    contract["contract_type"],
                    contract["buyer_county"],
                    contract["value_eur"],
                    contract["cpv_code"],
                    contract["cpv_description"],
                    contract["status"],
                ),
            )

            inserted += 1

        except Exception as e:
            # Handle column name mismatch
            log.warning(f"Failed to insert contract {contract['contract_name']}: {e}")

    log.info(f"✓ Inserted {inserted}/{num_samples} sample contracts")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="CAP Federation Quick Setup")
    parser.add_argument(
        "--init-db", action="store_true", help="Initialize database tables"
    )
    parser.add_argument("--sample-data", action="store_true", help="Create sample data")
    parser.add_argument(
        "--coops", type=int, default=20, help="Number of sample cooperatives"
    )
    parser.add_argument(
        "--contracts", type=int, default=10, help="Number of sample contracts"
    )
    parser.add_argument("--all", action="store_true", help="Run all setup steps")

    args = parser.parse_args()

    if not any([args.init_db, args.sample_data, args.all]):
        parser.print_help()
        return

    log.info(f"{'=' * 60}")
    log.info("CAP FEDERATION QUICK SETUP")
    log.info(f"{'=' * 60}\n")

    # Check password
    check_password()

    # Connect to database
    try:
        log.info("Connecting to database...")
        conn = psycopg2.connect(host=DB_HOST, user=DB_USER, database=DB_NAME)
        log.info("✓ Database connection successful")

        cursor = conn.cursor()

        # Initialize database tables
        if args.init_db or args.all:
            if SQL_FILE.exists():
                log.info("Executing SQL schema...")
                with open(SQL_FILE) as f:
                    cursor.execute(f.read())
                conn.commit()
                log.info("✓ Database tables created/verified")
            else:
                log.warning(f"SQL schema file not found: {SQL_FILE}")

        # Create sample data
        if args.sample_data or args.all:
            create_sample_coops(cursor, args.coops)
            create_sample_contracts(cursor, args.contracts)
            conn.commit()

        cursor.close()
        conn.close()

        # Summary
        log.info(f"\n{'=' * 60}")
        log.info("SETUP COMPLETE")
        log.info(f"{'=' * 60}")
        log.info(f"Database: {DB_NAME}")
        log.info(f"Cooperatives: {args.coops}")
        log.info(f"Contracts: {args.contracts}")
        log.info("\nNext steps:")
        log.info(
            "1. Enrich cooperatives: python3 python3 /opt/ACTIVE/INFRA/SKILLS/cap_cooperative_enricher.py"
        )
        log.info(
            "2. Run campaign: bash /opt/ACTIVE/EMAIL/CAMPAIGNS/CAP_FEDERATION/run_cap_federation.sh"
        )
        log.info(
            "3. Monitor: python3 /opt/ACTIVE/IDEAS/NATO/OPENCODE/scripts/cap_monitor.py --all"
        )
        log.info(f"{'=' * 60}\n")

    except Exception as e:
        log.error(f"Setup failed: {e}")
        return


if __name__ == "__main__":
    main()
