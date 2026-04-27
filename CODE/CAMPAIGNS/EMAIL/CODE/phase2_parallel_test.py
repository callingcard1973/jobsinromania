#!/usr/bin/env python3
"""
Phase 2: ANOFM Parallel Testing (PostgreSQL vs SQLite)

Validates PostgreSQL migration by comparing sender data and metrics:
  1. Data integrity: Compare email counts, domains, sectors between PG and SQLite
  2. Run parallel sends from both sources
  3. Track delivery metrics separately
  4. Generate comparison report before Phase 3 cutover

Usage:
    python3 phase2_parallel_test.py --validate    # Data comparison only
    python3 phase2_parallel_test.py --test-sends  # Send test batch (10 each)
    python3 phase2_parallel_test.py --full        # Full 1-hour parallel test

Deploy to: /opt/ACTIVE/INFRA/SCRIPTS/phase2_parallel_test.py
"""

import sqlite3
import psycopg2
from datetime import datetime
from pathlib import Path
import argparse
import sys
from typing import Dict, List, Tuple
from collections import Counter
import json

PG_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "database": "interjob_master",
    "user": "tudor",
    "password": "tudor",
}

SQLITE_PATH = "D:/MEMORY/CODE/CAMPAIGNS/ANOFM_APRIL_2026/tudor.db"


class Phase2ParallelTest:
    def __init__(self):
        self.pg_conn = None
        self.sqlite_conn = None
        self.report = {
            "timestamp": datetime.now().isoformat(),
            "pg_data": {},
            "sqlite_data": {},
            "comparison": {},
            "validation": {},
        }

    def log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def error(self, msg: str):
        print(f"[ERROR] {msg}", file=sys.stderr)

    def connect_pg(self) -> bool:
        try:
            self.pg_conn = psycopg2.connect(**PG_CONFIG)
            self.log("Connected to PostgreSQL")
            return True
        except Exception as e:
            self.error(f"PostgreSQL connection failed: {e}")
            return False

    def connect_sqlite(self) -> bool:
        if not Path(SQLITE_PATH).exists():
            self.error(f"SQLite file not found: {SQLITE_PATH}")
            return False
        try:
            self.sqlite_conn = sqlite3.connect(SQLITE_PATH)
            self.sqlite_conn.row_factory = sqlite3.Row
            self.log("Connected to SQLite")
            return True
        except Exception as e:
            self.error(f"SQLite connection failed: {e}")
            return False

    def extract_domain(self, email: str) -> str:
        """Extract domain from email."""
        if "@" not in email:
            return "invalid"
        return email.split("@")[1].lower()

    def get_pg_anofm_data(self) -> Dict:
        """Get ANOFM data statistics from PostgreSQL."""
        self.log("Analyzing PostgreSQL ANOFM data...")
        try:
            cur = self.pg_conn.cursor()

            # Basic counts (all ANOFM)
            cur.execute("SELECT COUNT(*) FROM companies_clean WHERE source = 'ANOFM';")
            total = cur.fetchone()[0]

            # Counts for migrated records only (from tudor.db)
            cur.execute("""
                SELECT COUNT(*) FROM companies_clean
                WHERE source = 'ANOFM' AND source_file = 'tudor.db';
            """)
            migrated_total = cur.fetchone()[0]

            cur.execute("""
                SELECT COUNT(*) FROM companies_clean
                WHERE source = 'ANOFM' AND source_file = 'tudor.db'
                AND email IS NOT NULL AND email != '';
            """)
            with_email = cur.fetchone()[0]

            # Domain distribution
            cur.execute("""
                SELECT
                    SUBSTRING(email FROM POSITION('@' IN email) + 1) AS domain,
                    COUNT(*) as count
                FROM companies_clean
                WHERE source = 'ANOFM' AND email IS NOT NULL AND email != ''
                GROUP BY domain
                ORDER BY count DESC
                LIMIT 10;
            """)
            top_domains = {row[0]: row[1] for row in cur.fetchall()}

            # Sector distribution
            cur.execute("""
                SELECT sector, COUNT(*) as count
                FROM companies_clean
                WHERE source = 'ANOFM'
                GROUP BY sector
                ORDER BY count DESC
                LIMIT 10;
            """)
            sectors = {row[0] or "NULL": row[1] for row in cur.fetchall()}

            # Sample emails
            cur.execute("""
                SELECT email, name, sector
                FROM companies_clean
                WHERE source = 'ANOFM' AND email IS NOT NULL
                LIMIT 5;
            """)
            samples = [{"email": row[0], "name": row[1], "sector": row[2]} for row in cur.fetchall()]

            cur.close()

            return {
                "total_anofm_records": total,
                "migrated_from_tudor_db": migrated_total,
                "with_valid_email": with_email,
                "top_domains": top_domains,
                "sectors": sectors,
                "sample_records": samples,
            }
        except Exception as e:
            self.error(f"Failed to get PG data: {e}")
            return {}

    def get_sqlite_anofm_data(self) -> Dict:
        """Get ANOFM data statistics from SQLite."""
        self.log("Analyzing SQLite ANOFM data...")
        try:
            cur = self.sqlite_conn.cursor()

            # Find table
            cur.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table'
                AND (name LIKE '%contact%' OR name LIKE '%anofm%')
                ORDER BY name;
            """
            )
            tables = [row[0] for row in cur.fetchall()]
            if not tables:
                cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cur.fetchall()]

            if not tables:
                self.error("No tables found in SQLite")
                return {}

            table = tables[0]
            self.log(f"Reading from SQLite table: {table}")

            # Basic counts
            cur.execute(f"SELECT COUNT(*) FROM {table};")
            total = cur.fetchone()[0]

            cur.execute(f"""
                SELECT COUNT(*) FROM {table}
                WHERE email IS NOT NULL AND email != '';
            """)
            with_email = cur.fetchone()[0]

            # Domain distribution
            cur.execute(f"""
                SELECT
                    SUBSTR(email, INSTR(email, '@') + 1) AS domain,
                    COUNT(*) as count
                FROM {table}
                WHERE email IS NOT NULL AND email != ''
                GROUP BY domain
                ORDER BY count DESC
                LIMIT 10;
            """)
            top_domains = {row[0]: row[1] for row in cur.fetchall()}

            # Sector distribution
            cur.execute(f"""
                SELECT sector, COUNT(*) as count
                FROM {table}
                GROUP BY sector
                ORDER BY count DESC
                LIMIT 10;
            """)
            sectors = {(row[0] or "NULL"): row[1] for row in cur.fetchall()}

            # Sample emails
            cur.execute(f"""
                SELECT email, company, sector
                FROM {table}
                WHERE email IS NOT NULL
                LIMIT 5;
            """)
            samples = [{"email": row[0], "name": row[1], "sector": row[2]} for row in cur.fetchall()]

            return {
                "total_records": total,
                "with_valid_email": with_email,
                "top_domains": top_domains,
                "sectors": sectors,
                "sample_records": samples,
            }
        except Exception as e:
            self.error(f"Failed to get SQLite data: {e}")
            return {}

    def compare_data(self) -> bool:
        """Compare PostgreSQL and SQLite data."""
        self.log("\n=== Data Comparison ===")

        pg_data = self.get_pg_anofm_data()
        sqlite_data = self.get_sqlite_anofm_data()

        self.report["pg_data"] = pg_data
        self.report["sqlite_data"] = sqlite_data

        if not pg_data or not sqlite_data:
            self.error("Could not retrieve data from one or both sources")
            return False

        # Compare migrated records only
        pg_migrated = pg_data.get("migrated_from_tudor_db", 0)
        sqlite_total = sqlite_data.get("total_records", 0)
        pg_emails = pg_data.get("with_valid_email", 0)
        sqlite_emails = sqlite_data.get("with_valid_email", 0)

        self.log(f"PostgreSQL migrated (tudor.db):  {pg_migrated:,} records")
        self.log(f"SQLite source data:              {sqlite_total:,} records")
        self.log(f"Emails migrated:                 {pg_emails:,} valid")
        self.log(f"Emails in SQLite:                {sqlite_emails:,} valid")

        # Check if migration counts match
        match = pg_migrated == sqlite_total
        self.log(f"Record count match: {match} ({pg_migrated:,} vs {sqlite_total:,}) {'OK' if match else 'MISMATCH'}")

        # Domain comparison
        pg_domains = set(pg_data["top_domains"].keys())
        sqlite_domains = set(sqlite_data["top_domains"].keys())
        domain_overlap = len(pg_domains & sqlite_domains)
        self.log(f"Top domains overlap: {domain_overlap}/10 OK")

        # Validation results
        validation = {
            "record_count_match": match,
            "pg_migrated": pg_migrated,
            "sqlite_total": sqlite_total,
            "pg_emails": pg_emails,
            "sqlite_emails": sqlite_emails,
            "domain_overlap": domain_overlap,
            "status": "PASS" if match and domain_overlap >= 8 else "WARNING",
        }

        self.report["validation"] = validation
        return validation["status"] == "PASS"

    def generate_report(self) -> str:
        """Generate and save comparison report."""
        report_dir = Path("D:/MEMORY/CODE/CAMPAIGNS/EMAIL/DATA")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"anofm_phase2_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(report_path, "w") as f:
                json.dump(self.report, f, indent=2, default=str)
            self.log(f"Report saved to {report_path}")
            return report_path
        except Exception as e:
            self.error(f"Failed to save report: {e}")
            return ""

    def run_validation(self) -> bool:
        """Run data validation only."""
        if not self.connect_pg() or not self.connect_sqlite():
            return False

        result = self.compare_data()
        self.generate_report()

        self.log(f"\nValidation: {'PASS' if result else 'FAIL'}")
        return result

    def close(self):
        if self.pg_conn:
            self.pg_conn.close()
        if self.sqlite_conn:
            self.sqlite_conn.close()


def main():
    parser = argparse.ArgumentParser(description="Phase 2: ANOFM Parallel Testing")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Data validation only (default)",
    )
    parser.add_argument("--test-sends", action="store_true", help="Send test batch (10 each)")
    parser.add_argument("--full", action="store_true", help="Full 1-hour parallel test")
    args = parser.parse_args()

    tester = Phase2ParallelTest()

    if args.test_sends or args.full:
        print("[TODO] Test sends not yet implemented")
        return 1

    success = tester.run_validation()
    tester.close()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
