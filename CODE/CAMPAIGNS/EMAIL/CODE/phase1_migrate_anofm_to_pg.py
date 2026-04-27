#!/usr/bin/env python3
"""
Phase 1: ANOFM SQLite → PostgreSQL Migration

Migrates ANOFM contacts from SQLite tudor.db to PostgreSQL companies_clean table.

Steps:
  1. Connect to PostgreSQL
  2. Get max(id) from companies_clean
  3. Read SQLite tudor.db
  4. Insert records with auto-generated ids
  5. Validate inserted rows
  6. Create indices if needed

Usage:
    python3 phase1_migrate_anofm_to_pg.py              # Full migration
    python3 phase1_migrate_anofm_to_pg.py --dry-run    # Test without commit
    python3 phase1_migrate_anofm_to_pg.py --validate   # Validation only

Deploy to: /opt/ACTIVE/INFRA/SCRIPTS/phase1_migrate_anofm_to_pg.py
"""

import sqlite3
import psycopg2
import psycopg2.extras
from datetime import datetime
from pathlib import Path
import argparse
import sys
from typing import Dict, List, Optional, Tuple

# Configuration
PG_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "database": "interjob_master",
    "user": "tudor",
    "password": "tudor",
}

SQLITE_PATH = "D:/MEMORY/CODE/CAMPAIGNS/ANOFM_APRIL_2026/tudor.db"
BATCH_SIZE = 5000


class Phase1Migration:
    def __init__(self, dry_run: bool = False):
        self.pg_conn = None
        self.dry_run = dry_run
        self.errors = []
        self.stats = {
            "read": 0,
            "valid": 0,
            "inserted": 0,
            "failed": 0,
            "duplicates": 0,
            "max_id_before": 0,
            "max_id_after": 0,
        }

    def log(self, msg: str):
        """Log message with timestamp."""
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {msg}")

    def error(self, msg: str):
        """Log error."""
        print(f"[ERROR] {msg}", file=sys.stderr)
        self.errors.append(msg)

    def connect_pg(self) -> bool:
        """Connect to PostgreSQL."""
        try:
            self.pg_conn = psycopg2.connect(**PG_CONFIG)
            self.log("Connected to PostgreSQL")
            return True
        except psycopg2.Error as e:
            self.error(f"PostgreSQL connection failed: {e}")
            return False

    def get_max_id(self) -> int:
        """Get current max(id) from companies_clean."""
        try:
            cur = self.pg_conn.cursor()
            cur.execute("SELECT COALESCE(MAX(id), 0) FROM companies_clean;")
            max_id = cur.fetchone()[0]
            cur.close()
            self.stats["max_id_before"] = max_id
            self.log(f"Current max(id) in companies_clean: {max_id}")
            return max_id
        except psycopg2.Error as e:
            self.error(f"Failed to get max(id): {e}")
            return 0

    def read_sqlite_contacts(self, sqlite_path: str) -> List[Dict]:
        """Read ANOFM contacts from SQLite."""
        if not Path(sqlite_path).exists():
            self.error(f"SQLite file not found: {sqlite_path}")
            return []

        self.log(f"Reading SQLite from {sqlite_path}...")
        rows = []

        try:
            sqlite_conn = sqlite3.connect(sqlite_path)
            sqlite_conn.row_factory = sqlite3.Row
            sqlite_cur = sqlite_conn.cursor()

            # Detect table name
            sqlite_cur.execute(
                """
                SELECT name FROM sqlite_master
                WHERE type='table'
                AND name LIKE '%contact%' OR name LIKE '%anofm%'
                ORDER BY name;
            """
            )
            tables = [row[0] for row in sqlite_cur.fetchall()]

            if not tables:
                sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in sqlite_cur.fetchall()]

            if not tables:
                self.error("No tables found in SQLite")
                return []

            table = tables[0]
            self.log(f"Reading from table: {table}")

            sqlite_cur.execute(f"SELECT * FROM {table};")
            columns = [desc[0] for desc in sqlite_cur.description]

            for row in sqlite_cur.fetchall():
                rows.append(dict(zip(columns, row)))

            self.log(f"Read {len(rows)} rows from SQLite")
            sqlite_conn.close()
            self.stats["read"] = len(rows)
            return rows

        except Exception as e:
            self.error(f"SQLite read failed: {e}")
            return []

    def validate_row(self, row: Dict) -> Tuple[bool, Optional[Dict]]:
        """Validate and normalize a row."""
        # Find email column
        email = None
        for key in row:
            if key.lower().replace("_", "").replace("-", "") == "email":
                email = row[key]
                break

        if not email or not isinstance(email, str):
            return False, None

        email = email.strip().lower()
        if "@" not in email or len(email) < 5:
            return False, None

        # Extract fields
        name = None
        for key in row:
            if key.lower() in ("name", "company", "companyname"):
                name = row[key]
                break

        sector = None
        for key in row:
            if key.lower() in ("sector", "category"):
                sector = row[key]
                break

        phone = None
        for key in row:
            if key.lower() in ("phone", "telephone"):
                phone = row[key]
                break

        city = None
        for key in row:
            if key.lower() in ("city", "location", "localitate"):
                city = row[key]
                break

        normalized = {
            "email": email,
            "name": str(name)[:500] if name else None,
            "sector": str(sector)[:100] if sector else "ANOFM",
            "city": str(city)[:200] if city else None,
            "phone": str(phone)[:50] if phone else None,
            "source": "ANOFM",
            "source_file": "tudor.db",
        }

        return True, normalized

    def insert_batch(self, batch: List[Dict], next_id: int) -> Tuple[int, int]:
        """Insert a batch of records. Returns (inserted, failed)."""
        if not batch or not self.pg_conn:
            return 0, 0

        inserted = 0
        failed = 0

        try:
            cur = self.pg_conn.cursor()
            current_id = next_id

            for row in batch:
                try:
                    sql = """
                        INSERT INTO companies_clean
                        (id, email, name, sector, city, phone, source, source_file, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (id) DO NOTHING;
                    """

                    cur.execute(
                        sql,
                        (
                            current_id,
                            row["email"],
                            row["name"],
                            row["sector"],
                            row["city"],
                            row["phone"],
                            row["source"],
                            row["source_file"],
                        ),
                    )

                    if cur.rowcount > 0:
                        inserted += 1
                    else:
                        self.stats["duplicates"] += 1

                    current_id += 1

                except psycopg2.IntegrityError as e:
                    if "duplicate" in str(e).lower():
                        self.stats["duplicates"] += 1
                        cur.execute("ROLLBACK;")
                        current_id += 1
                    else:
                        failed += 1
                        cur.execute("ROLLBACK;")
                        self.error(f"Insert error: {e}")
                except Exception as e:
                    failed += 1
                    cur.execute("ROLLBACK;")
                    self.error(f"Unexpected error: {e}")

            if not self.dry_run:
                cur.execute("COMMIT;")

            cur.close()
            return inserted, failed

        except Exception as e:
            self.error(f"Batch insert failed: {e}")
            return 0, len(batch)

    def migrate(self) -> bool:
        """Execute Phase 1 migration."""
        if not self.connect_pg():
            return False

        # Get current max id
        max_id = self.get_max_id()
        next_id = max_id + 1

        # Read SQLite
        sqlite_rows = self.read_sqlite_contacts(SQLITE_PATH)
        if not sqlite_rows:
            return False

        # Validate and normalize
        self.log(f"Validating {len(sqlite_rows)} rows...")
        batch = []
        valid_count = 0

        for row in sqlite_rows:
            is_valid, normalized = self.validate_row(row)
            if is_valid:
                batch.append(normalized)
                valid_count += 1

                if len(batch) >= BATCH_SIZE:
                    inserted, failed = self.insert_batch(batch, next_id)
                    self.stats["inserted"] += inserted
                    self.stats["failed"] += failed
                    next_id += len(batch)
                    batch = []

        # Insert remaining batch
        if batch:
            inserted, failed = self.insert_batch(batch, next_id)
            self.stats["inserted"] += inserted
            self.stats["failed"] += failed

        self.stats["valid"] = valid_count

        # Final commit
        if not self.dry_run and self.pg_conn:
            try:
                self.pg_conn.commit()
                self.log("Committed all inserts to PostgreSQL")
            except Exception as e:
                self.error(f"Commit failed: {e}")
                self.pg_conn.rollback()
                return False

        # Get new max id
        new_max = self.get_max_id()
        self.stats["max_id_after"] = new_max

        self.log_stats()
        return self.stats["failed"] == 0

    def log_stats(self):
        """Log migration statistics."""
        self.log("\n=== Migration Statistics ===")
        self.log(f"Read from SQLite:    {self.stats['read']:,}")
        self.log(f"Valid records:       {self.stats['valid']:,}")
        self.log(f"Inserted to PG:      {self.stats['inserted']:,}")
        self.log(f"Duplicate skipped:   {self.stats['duplicates']:,}")
        self.log(f"Failed inserts:      {self.stats['failed']:,}")
        self.log(f"ID range:            {self.stats['max_id_before']:,} -> {self.stats['max_id_after']:,}")
        self.log(f"Mode:                {'DRY-RUN' if self.dry_run else 'COMMITTED'}")

    def close(self):
        """Close connections."""
        if self.pg_conn:
            self.pg_conn.close()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Phase 1: ANOFM SQLite → PostgreSQL Migration")
    parser.add_argument("--dry-run", action="store_true", help="Test without committing")
    parser.add_argument("--validate", action="store_true", help="Validation only")
    args = parser.parse_args()

    migrator = Phase1Migration(dry_run=args.dry_run or args.validate)
    success = migrator.migrate()
    migrator.close()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
