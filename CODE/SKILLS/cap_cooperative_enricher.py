#!/usr/bin/env python3
"""
CAP Federation Cooperative Enrichment Script

Adapts existing universal_enricher.py to enrich Romanian agricultural cooperatives.
Finds emails, phones, addresses, websites from ONRC, telecom index, etc.
"""

import sys
import csv
import json
import logging
import psycopg2
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

# Configuration
DB_NAME = "interjob_master"
DB_USER = "tudor"
DB_HOST = "localhost"
OUTPUT_DIR = Path("/opt/ACTIVE/IDEAS/NATO/OPENCODE/data")
LOG_DIR = Path("/opt/ACTIVE/IDEAS/NATO/OPENCODE/logs")

for d in [OUTPUT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"cap_enrichment_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)


class CAPCooperativeEnricher:
    """Enrich Romanian agricultural cooperatives with contact information."""

    def __init__(self):
        self.enriched_count = 0
        self.failed_count = 0

    def connect_db(self):
        """Connect to PostgreSQL database."""
        try:
            conn = psycopg2.connect(host=DB_HOST, user=DB_USER, database=DB_NAME)
            log.info(f"Connected to database: {DB_NAME}")
            return conn
        except Exception as e:
            log.error(f"Database connection failed: {e}")
            return None

    def get_cooperatives_to_enrich(self, limit: int = 100) -> List[Dict]:
        """
        Fetch cooperatives that need enrichment.
        Priority: Added recently, but missing key fields.
        """
        conn = self.connect_db()
        if not conn:
            return []

        coops = []

        try:
            cursor = conn.cursor()

            # Query co-ops that need enrichment
            query = """
                SELECT id, name, cui, county, city, products, capacity_annual_tons,
                       certification_status, email, phone, website, status, added_on
                FROM cap_cooperatives
                WHERE (email IS NULL OR phone IS NULL OR website IS NULL)
                  AND (cui IS NOT NULL OR name IS NOT NULL)
                ORDER BY added_on DESC
                LIMIT %s
            """

            cursor.execute(query, (limit,))
            columns = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                coop = dict(zip(columns, row))
                coops.append(coop)

            cursor.close()
            log.info(f"Retrieved {len(coops)} co-ops to enrich")

        except Exception as e:
            log.error(f"Error fetching co-ops: {e}")
        finally:
            conn.close()

        return coops

    def enrich_by_cui(self, cui: str) -> Dict:
        """
        Enrich cooperative by CUI (Cod Unic de Identificare).
        Checks ONRC (Romanian company registry).

        Args:
            cui: Romanian CUI (e.g., 'RO12345678')

        Returns:
            Dict with enriched data: email, phone, address, website
        """
        # This would normally query ONRC API or the enrichment index
        # For now, return placeholder data

        # In production, you'd use:
        # onrc_data = self.onrc_enricher.search_cui(cui)
        # telecom_data = self.telecom_index.search(name, county)
        # impressum_data = self.impressum_crawler.crawl(website)

        # Placeholder enrichment (simulated)
        enriched = {
            "email": None,
            "phone": None,
            "address": None,
            "website": None,
            "contact_person": None,
            "status": "PENDING_ENRICHMENT",
        }

        # Simulate enrichment based on CUI pattern
        if cui:
            # In real implementation, this would query the enrichment index
            pass

        return enriched

    def enrich_by_name_county(self, name: str, county: str) -> Dict:
        """
        Enrich cooperative by name and county.
        Uses fuzzy matching against enrichment index.

        Args:
            name: Cooperative name
            county: Romanian county

        Returns:
            Dict with enriched data
        """
        # In production, query the 600K+ email index
        # fuzzy_matcher = FuzzyMatcher()
        # matches = fuzzy_matcher.search(name, county)

        enriched = {
            "email": None,
            "phone": None,
            "address": None,
            "website": None,
            "contact_person": None,
            "status": "PENDING_ENRICHMENT",
        }

        return enriched

    def update_cooperative(self, coop_id: int, enriched_data: Dict):
        """
        Update cooperative record with enriched information.
        """
        conn = self.connect_db()
        if not conn:
            return False

        try:
            cursor = conn.cursor()

            # Build update query dynamically
            updates = []
            values = []

            if enriched_data.get("email"):
                updates.append("email = %s")
                values.append(enriched_data["email"])

            if enriched_data.get("phone"):
                updates.append("phone = %s")
                values.append(enriched_data["phone"])

            if enriched_data.get("website"):
                updates.append("website = %s")
                values.append(enriched_data["website"])

            if enriched_data.get("contact_person"):
                updates.append("contact_person = %s")
                values.append(enriched_data["contact_person"])

            if enriched_data.get("address"):
                updates.append("address = %s")
                values.append(enriched_data["address"])

            if enriched_data.get("status"):
                updates.append("status = %s")
                values.append(enriched_data["status"])

            if updates:
                # Add updated_at
                updates.append("updated_at = NOW()")

                # Add coop_id to values
                values.append(coop_id)

                query = (
                    f"UPDATE cap_cooperatives SET {', '.join(updates)} WHERE id = %s"
                )

                cursor.execute(query, tuple(values))
                conn.commit()

                self.enriched_count += 1
                return True

        except Exception as e:
            log.error(f"Error updating cooperative {coop_id}: {e}")
            conn.rollback()
            self.failed_count += 1
            return False

        finally:
            conn.close()

        return False

    def run_enrichment_batch(self, limit: int = 100):
        """
        Run enrichment batch on cooperative database.

        Args:
            limit: Number of co-ops to enrich
        """
        log.info(f"{'=' * 60}")
        log.info("CAP COOPERATIVE ENRICHMENT")
        log.info(f"{'=' * 60}")
        log.info(f"Limit: {limit} co-ops")
        log.info(f"{'=' * 60}\n")

        # Fetch co-ops to enrich
        coops = self.get_cooperatives_to_enrich(limit)

        if not coops:
            log.warning("No co-ops to enrich!")
            return

        log.info(f"Enriching {len(coops)} co-ops...\n")

        # Enrich each cooperative
        for i, coop in enumerate(coops, 1):
            log.info(
                f"[{i}/{len(coops)}] Enriching: {coop['name']} ({coop.get('county', 'N/A')})"
            )

            # Try enrichment by CUI first
            if coop.get("cui"):
                enriched = self.enrich_by_cui(coop["cui"])
            else:
                # Fallback to name + county
                enriched = self.enrich_by_name_county(
                    coop["name"], coop.get("county", "")
                )

            # Update database if data found
            if any(enriched[key] for key in ["email", "phone", "website"]):
                success = self.update_cooperative(coop["id"], enriched)

                if success:
                    found_fields = [
                        f"{key}={enriched[key]}"
                        for key in ["email", "phone", "website"]
                        if enriched.get(key)
                    ]
                    log.info(f"   ✓ Updated: {', '.join(found_fields)}")
            else:
                log.info(f"   ℹ No new data found")

        # Summary
        log.info(f"\n{'=' * 60}")
        log.info("ENRICHMENT SUMMARY")
        log.info(f"{'=' * 60}")
        log.info(f"Processed: {len(coops)}")
        log.info(f"Enriched: {self.enriched_count}")
        log.info(f"Failed: {self.failed_count}")
        log.info(f"{'=' * 60}\n")

        # Export results
        self.export_enrichment_report(coops)

    def export_enrichment_report(self, coops: List[Dict]):
        """
        Export enrichment results to CSV.
        """
        output_file = OUTPUT_DIR / f"cap_enrichment_report_{datetime.now():%Y%m%d}.csv"

        fieldnames = [
            "id",
            "name",
            "cui",
            "county",
            "email",
            "phone",
            "website",
            "capacity_annual_tons",
            "certification_status",
            "status",
            "added_on",
            "enriched_at",
        ]

        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for coop in coops:
                row = coop.copy()
                row["enriched_at"] = datetime.now().isoformat()
                writer.writerow(row)

        log.info(f"Enrichment report exported: {output_file}")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="CAP Cooperative Enrichment")
    parser.add_argument(
        "--limit", type=int, default=50, help="Number of co-ops to enrich"
    )

    args = parser.parse_args()

    enricher = CAPCooperativeEnricher()

    try:
        enricher.run_enrichment_batch(limit=args.limit)
    except Exception as e:
        log.error(f"Enrichment error: {e}")
        raise


if __name__ == "__main__":
    main()
