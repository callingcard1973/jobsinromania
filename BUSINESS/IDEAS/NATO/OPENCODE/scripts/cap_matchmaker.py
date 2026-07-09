#!/usr/bin/env python3
"""
CAP Federation Contract-Cooperative Matchmaker

Matches SEAP contracts to cooperative capacity.
Identifies recommended cooperatives for each contract based on:
1. Product requirements (CPV codes)
2. Volume needed
3. Geographic location
4. Capacity availability
"""

import sys
import psycopg2
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

try:
    from alerting import send_telegram
except ImportError:
    send_telegram = None

# Configuration
DB_NAME = "interjob_master"
DB_USER = "tudor"
DB_HOST = "localhost"
LOG_DIR = Path("/opt/ACTIVE/IDEAS/NATO/OPENCODE/logs")

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / f"cap_matchmaker_{datetime.now():%Y%m%d}.log"),
        logging.StreamHandler(),
    ],
)
log = logging.getLogger(__name__)

# CPV code mappings for agricultural products
CPV_TO_PRODUCTS = {
    "03": ["cereals", "grains", "wheat", "barley", "maize", "rice"],
    "15": ["food", "meal", "meat", "dairy", "fish", "honey"],
    "0409": ["honey"],
    "02": ["meat", "beef", "pork", "chicken"],
    "22": ["beverages", "wine", "spirits"],
    "032": ["fruits", "vegetables"],
    "0322": ["fruits"],
    "08": ["animal feed"],
}

# CPV codes for military procurement
MILITARY_CPV_PREFIXES = ["03", "15", "0409", "02", "22"]


class CAPMatchmaker:
    """Match SEAP contracts to cooperative capacity."""

    def __init__(self):
        self.db_conn = None

    def connect_db(self):
        """Connect to database."""
        try:
            self.db_conn = psycopg2.connect(
                host=DB_HOST, user=DB_USER, database=DB_NAME
            )
            log.info("Connected to database")
            return True
        except Exception as e:
            log.error(f"Database connection failed: {e}")
            return False

    def fetch_open_contracts(self, limit: int = 20) -> List[Dict]:
        """
        Fetch open SEAP contracts for agricultural/food products.

        Args:
            limit: Max contracts to fetch

        Returns:
            List of contract dictionaries
        """
        if not self.connect_db():
            return []

        contracts = []

        try:
            cursor = self.db_conn.cursor()

            # Query contracts relevant to CAP (food/agri)
            query = """
                SELECT id, contract_name, contract_id, buyer_name, buyer_type, buyer_county,
                       value_eur, value_ron, cpv_code, cpv_description, delivery_date_start, 
                       delivery_date_end, delivery_location, status, created_at
                FROM cap_contracts
                WHERE status IN ('OPPORTUNITY', 'BIDDING')
                  AND (cpv_code LIKE ANY(ARRAY[%s,%s,%s,%s,%s]) 
                       OR cpv_code LIKE '%03%'
                       OR cpv_code LIKE '%15%')
                ORDER BY value_eur DESC
                LIMIT %s
            """

            military_codes = ["0409%", "02113000%", "15811100%"]
            cursor.execute(query, military_codes + [limit])

            columns = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                contract = dict(zip(columns, row))
                contracts.append(self._enrich_contract(contract))

            cursor.close()

            log.info(f"Fetched {len(contracts)} open contracts")

        except Exception as e:
            log.error(f"Error fetching contracts: {e}")

        return contracts

    def _enrich_contract(self, contract: Dict) -> Dict:
        """
        Enrich contract with additional metadata.
        """
        # Estimate volume needed based on value (rough estimate)
        value_eur = contract.get("value_eur", 0)

        if (
            "cereals" in contract.get("cpv_description", "").lower()
            or contract["cpv_code"][:2] == "03"
        ):
            # Cereals: ~400 EUR/ton -> volume = value / 400
            contract["estimated_volume_tons"] = value_eur / 400
        elif "honey" in contract.get("cpv_description", "").lower():
            # Honey: ~2000 EUR/ton -> volume = value / 2000
            contract["estimated_volume_tons"] = value_eur / 2000
        else:
            # General food: ~600 EUR/ton
            contract["estimated_volume_tons"] = value_eur / 600

        # Parse CPV products
        contract["required_products"] = self._parse_cpv_products(
            contract["cpv_code"], contract.get("cpv_description", "")
        )

        return contract

    def _parse_cpv_products(self, cpv_code: str, description: str) -> List[str]:
        """
        Parse CPV code to extract required products.

        Args:
            cpv_code: CPV code (e.g., '04090000-0')
            description: CPV description

        Returns:
            List of product keywords
        """
        products = []

        # Check by CPV prefix
        for prefix, keywords in CPV_TO_PRODUCTS.items():
            if cpv_code.startswith(prefix):
                products.extend(keywords)
                break

        # Check description
        desc_lower = description.lower()

        if "cereals" in desc_lower or "grâu" in desc_lower or "grains" in desc_lower:
            products.extend(["cereals", "grains"])
        if "honey" in desc_lower or "miere" in desc_lower:
            products.append("honey")
        if "meat" in desc_lower or "carne" in desc_lower:
            products.extend(["meat"])
        if "beef" in desc_lower or "vitel" in desc_lower:
            products.append("beef")
        if "poultry" in desc_lower or "pasăre" in desc_lower:
            products.append("poultry")
        if "dairy" in desc_lower or "lactate" in desc_lower:
            products.extend(["dairy", "milk", "cheese"])
        if "fruits" in desc_lower or "fructe" in desc_lower:
            products.extend(["fruits"])
        if "vegetables" in desc_lower or "legume" in desc_lower:
            products.extend(["vegetables"])

        # Remove duplicates
        return list(set(products))

    def find_matching_cooperatives(
        self, contract: Dict, min_match_score: float = 0.6, max_coops: int = 10
    ) -> List[Dict]:
        """
        Find cooperatives that can fulfill a contract.

        Args:
            contract: Contract dictionary
            min_match_score: Minimum confidence score (0.0-1.0)
            max_coops: Max number of cooperatives to return

        Returns:
            List of matching cooperatives with match scores
        """
        if not self.connect_db():
            return []

        matches = []
        required_products = contract.get("required_products", [])
        volume_needed = contract.get("estimated_volume_tons", 0)
        buyer_county = contract.get("buyer_county", "")

        try:
            cursor = self.db_conn.cursor()

            # Query potential matching cooperatives
            query = """
                SELECT id, name, county, capacity_annual_tons, capacity_monthly_tons,
                       products, email, phone, website, certification_status, status
                FROM cap_cooperatives
                WHERE status = 'MEMBER'
                  AND capacity_annual_tons >= %s
                ORDER BY county ASC, capacity_annual_tons DESC
                LIMIT 50
            """

            # Minimum capacity: 10% of annual capacity used for this contract
            min_capacity = volume_needed * 0.1
            cursor.execute(query, (min_capacity,))

            columns = [desc[0] for desc in cursor.description]

            for row in cursor.fetchall():
                coop = dict(zip(columns, row))

                # Calculate match score
                match_score, match_reasons = self._calculate_match_score(
                    contract, coop, required_products, volume_needed, buyer_county
                )

                if match_score >= min_match_score:
                    coop["match_score"] = match_score
                    coop["match_reasons"] = match_reasons
                    matches.append(coop)

            cursor.close()

            # Sort by match score and limit
            matches.sort(key=lambda x: x["match_score"], reverse=True)
            matches = matches[:max_coops]

            log.info(
                f"Found {len(matches)} matching cooperatives for contract: {contract.get('contract_name', 'Unknown')}"
            )

        except Exception as e:
            log.error(f"Error finding matches: {e}")

        return matches

    def _calculate_match_score(
        self,
        contract: Dict,
        cooperative: Dict,
        required_products: List[str],
        volume_needed: float,
        buyer_county: str,
    ) -> Tuple[float, List[str]]:
        """
        Calculate match score between contract and cooperative.

        Scores:
        - Product match: 0.0-0.5 (based on products overlap)
        - County match: 0.0-0.2 (same county preference)
        - Capacity match: 0.0-0.3 (capacity availability)

        Returns:
            Tuple of (score, list of match reasons)
        """
        score = 0.0
        reasons = []

        coop_products = cooperative.get("products", [])
        if isinstance(coop_products, str):
            # Handle string products (should be array)
            coop_products = []

        # 1. Product match (0.0-0.5)
        if required_products and coop_products:
            # Check for any product overlap
            overlap = any(
                any(req in str(prod).lower() for req in required_products)
                for prod in coop_products
            )
            if overlap:
                product_score = 0.5
                score += product_score
                reasons.append(f"Product match")
        else:
            # Default: assume match if no specific requirements
            product_score = 0.25
            score += product_score
            reasons.append("General food/agri production")

        # 2. County match (0.0-0.2)
        coop_county = cooperative.get("county", "")
        if buyer_county and coop_county and buyer_county.lower() == coop_county.lower():
            score += 0.2
            reasons.append(f"Same county: {buyer_county}")
        else:
            score += 0.1
            reasons.append("Different county (acceptable)")

        # 3. Capacity match (0.0-0.3)
        coop_capacity = cooperative.get("capacity_annual_tons", 0)
        capacity_ratio = min(coop_capacity / (volume_needed * 0.3 + 1), 1.0)
        # More points for higher capacity (relative to need)
        score += 0.3 * capacity_ratio
        reasons.append(f"Capacity sufficient: {coop_capacity:,.0f} tons/year")

        return min(score, 1.0), reasons

    def save_match(
        self,
        contract_id: int,
        cooperative_id: int,
        match_score: float,
        match_reasons: List[str],
    ):
        """
        Save contract-to-cooperative match to database.
        """
        if not self.connect_db():
            return False

        try:
            cursor = self.db_conn.cursor()

            query = """
                INSERT INTO cap_contract_matches 
                (contract_id, cooperative_id, match_score, match_reasons, status)
                VALUES (%s, %s, %s, %s, 'PENDING')
                ON CONFLICT (contract_id, cooperative_id) DO UPDATE SET
                    match_score = EXCLUDED.match_score,
                    match_reasons = EXCLUDED.match_reasons
            """

            cursor.execute(
                query, (contract_id, cooperative_id, match_score, match_reasons)
            )
            self.db_conn.commit()
            cursor.close()

            log.info(f"Saved match: contract {contract_id} - co-op {cooperative_id}")
            return True

        except Exception as e:
            log.error(f"Error saving match: {e}")
            if self.db_conn:
                self.db_conn.rollback()
            return False

    def run_matching(self, limit: int = 10, save_matches: bool = False):
        """
        Run contract-to-cooperative matching.

        Args:
            limit: Number of contracts to match
            save_matches: Whether to save matches to database
        """
        log.info(f"{'=' * 60}")
        log.info("CAP CONTRACT-TO-COOP MATCHER")
        log.info(f"{'=' * 60}")
        log.info(f"Contracts to match: {limit}")
        log.info(f"Save matches: {save_matches}")
        log.info(f"{'=' * 60}\n")

        # Fetch contracts
        contracts = self.fetch_open_contracts(limit)

        if not contracts:
            log.warning("No contracts found to match!")
            return

        # Match each contract
        total_matches = 0
        high_value_matches = 0

        for contract in contracts:
            log.info(f"\nContract: {contract['contract_name']}")
            log.info(f"  Value: {contract['value_eur']:,.0f} EUR")
            log.info(f"  CPV: {contract['cpv_code']} - {contract['cpv_description']}")
            log.info(f"  Est. Volume: {contract['estimated_volume_tons']:,.1f} tons")
            log.info(f"  Buyer: {contract['buyer_name']}\n")

            # Find matching cooperatives
            matches = self.find_matching_cooperatives(contract)

            if matches:
                total_matches += len(matches)

                # Check for high-value contracts
                if contract["value_eur"] >= 100000:
                    high_value_matches += 1

                    # Alert on high-value match
                    if send_telegram:
                        message = f"""💼 HIGH-VALUE CONTRACT MATCH!

{contract["contract_name"]}
Value: {contract["value_eur"]:,.0f} EUR
CPV: {contract["cpv_code"]}
{len(matches)} matching cooperatives available:
"""
                        for coop in matches[:5]:
                            message += f"  • {coop['name']} ({coop['county']}) - Score: {coop['match_score']:.2f}\n"

                        send_telegram(message)
                        log.info(f"✅ Telegram alert sent for high-value contract")

                # Display matches
                for i, match in enumerate(matches[:3], 1):
                    log.info(f"  Match {i}: {match['name']} ({match['county']})")
                    log.info(f"    Score: {match['match_score']:.2f}")
                    log.info(
                        f"    Capacity: {match.get('capacity_annual_tons', 0):,.0f} tons/year"
                    )
                    log.info(f"    Reasons: {', '.join(match['match_reasons'])}")

                # Save matches to database if requested
                if save_matches:
                    for match in matches:
                        self.save_match(
                            contract["id"],
                            match["id"],
                            match["match_score"],
                            match["match_reasons"],
                        )
            else:
                log.info("  No matching cooperatives found")

        # Summary
        log.info(f"\n{'=' * 60}")
        log.info("MATCHING SUMMARY")
        log.info(f"{'=' * 60}")
        log.info(f"Contracts processed: {len(contracts)}")
        log.info(f"Total matches: {total_matches}")
        log.info(f"High-value alerts sent: {high_value_matches}")
        log.info(f"{'=' * 60}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="CAP Contract-Cooperative Matchmaker")
    parser.add_argument(
        "--limit", type=int, default=10, help="Number of contracts to match"
    )
    parser.add_argument("--save", action="store_true", help="Save matches to database")

    args = parser.parse_args()

    matchmaker = CAPMatchmaker()

    try:
        matchmaker.run_matching(limit=args.limit, save_matches=args.save)
    except Exception as e:
        log.error(f"Matching error: {e}")
        raise


if __name__ == "__main__":
    main()
