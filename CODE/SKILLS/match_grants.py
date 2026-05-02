#!/usr/bin/env python3
"""
Grant Matcher - Match Romanian companies to eligible EU grants.

Matches companies from interjob_master database to open EU funding calls
from cifn_eu database based on sector (CAEN code), company size, and keywords.

Usage:
    python3 match_grants.py                          # Match all companies
    python3 match_grants.py --cui 12345678           # Match specific company
    python3 match_grants.py --input companies.csv   # Match from CSV
    python3 match_grants.py --programme HORIZON     # Filter by programme
    python3 match_grants.py --min-score 70          # Minimum relevance
"""

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
    sys.exit(1)

# CAEN code to EU programme mapping
# First 2 digits of CAEN code -> list of relevant EU programmes
CAEN_TO_PROGRAMMES = {
    # Agriculture, Forestry, Fishing (01-03)
    "01": ["HORIZON", "LIFE"],
    "02": ["HORIZON", "LIFE"],
    "03": ["HORIZON", "LIFE"],

    # Mining (05-09)
    "05": ["INNOVFUND", "LIFE"],
    "06": ["INNOVFUND"],
    "07": ["INNOVFUND", "LIFE"],
    "08": ["INNOVFUND", "LIFE"],
    "09": ["INNOVFUND"],

    # Manufacturing (10-33)
    "10": ["HORIZON", "EIC", "LIFE"],  # Food
    "11": ["HORIZON", "EIC"],  # Beverages
    "13": ["HORIZON", "EIC"],  # Textiles
    "14": ["HORIZON", "EIC"],  # Apparel
    "15": ["HORIZON", "EIC"],  # Leather
    "16": ["HORIZON", "LIFE"],  # Wood
    "17": ["HORIZON", "LIFE"],  # Paper
    "18": ["HORIZON", "CREA"],  # Printing
    "19": ["INNOVFUND"],  # Petroleum
    "20": ["HORIZON", "INNOVFUND"],  # Chemicals
    "21": ["HORIZON", "EIC"],  # Pharma
    "22": ["HORIZON", "INNOVFUND"],  # Plastics
    "23": ["HORIZON", "INNOVFUND"],  # Non-metallic minerals
    "24": ["HORIZON", "INNOVFUND"],  # Metals
    "25": ["HORIZON", "EIC"],  # Fabricated metal
    "26": ["HORIZON", "DIGITAL", "EIC"],  # Electronics
    "27": ["HORIZON", "INNOVFUND"],  # Electrical equipment
    "28": ["HORIZON", "EIC"],  # Machinery
    "29": ["HORIZON", "EIC", "CEF"],  # Motor vehicles
    "30": ["HORIZON", "EIC", "CEF"],  # Transport equipment
    "31": ["HORIZON", "CREA"],  # Furniture
    "32": ["HORIZON", "EIC"],  # Other manufacturing
    "33": ["HORIZON", "EIC"],  # Repair/installation

    # Energy (35)
    "35": ["INNOVFUND", "HORIZON", "CEF"],

    # Water, Waste (36-39)
    "36": ["LIFE", "HORIZON"],
    "37": ["LIFE", "HORIZON"],
    "38": ["LIFE", "HORIZON", "INNOVFUND"],
    "39": ["LIFE", "HORIZON"],

    # Construction (41-43)
    "41": ["HORIZON", "LIFE", "INNOVFUND"],
    "42": ["CEF", "HORIZON"],
    "43": ["HORIZON", "LIFE"],

    # Trade (45-47)
    "45": ["DIGITAL", "EIC"],
    "46": ["DIGITAL", "EIC"],
    "47": ["DIGITAL", "EIC"],

    # Transport (49-53)
    "49": ["CEF", "HORIZON"],
    "50": ["CEF", "HORIZON"],
    "51": ["CEF", "HORIZON"],
    "52": ["CEF", "HORIZON", "DIGITAL"],
    "53": ["DIGITAL", "HORIZON"],

    # Hospitality (55-56)
    "55": ["CREA", "ERASMUS", "DIGITAL"],
    "56": ["CREA", "DIGITAL"],

    # IT/Digital (58-63)
    "58": ["DIGITAL", "HORIZON", "EIC", "CREA"],
    "59": ["DIGITAL", "CREA", "EIC"],
    "60": ["DIGITAL", "CREA"],
    "61": ["DIGITAL", "HORIZON", "EIC"],
    "62": ["DIGITAL", "HORIZON", "EIC"],
    "63": ["DIGITAL", "HORIZON", "EIC"],

    # Finance (64-66)
    "64": ["DIGITAL", "EIC"],
    "65": ["DIGITAL", "EIC"],
    "66": ["DIGITAL", "EIC"],

    # Real Estate (68)
    "68": ["LIFE", "INNOVFUND"],

    # Professional Services (69-75)
    "69": ["DIGITAL"],
    "70": ["DIGITAL", "HORIZON"],
    "71": ["HORIZON", "LIFE"],
    "72": ["HORIZON", "EIC", "DIGITAL"],  # R&D
    "73": ["DIGITAL", "CREA"],  # Advertising
    "74": ["CREA", "DIGITAL"],  # Design
    "75": ["HORIZON", "DIGITAL"],  # Veterinary

    # Education (85)
    "85": ["ERASMUS", "HORIZON", "DIGITAL"],

    # Healthcare (86-88)
    "86": ["HORIZON", "EIC", "DIGITAL"],
    "87": ["HORIZON", "EIC"],
    "88": ["HORIZON", "EIC"],

    # Culture/Arts (90-93)
    "90": ["CREA", "HORIZON"],
    "91": ["CREA", "HORIZON"],
    "92": ["CREA"],
    "93": ["CREA", "ERASMUS"],
}

# Programme keywords for text matching
PROGRAMME_KEYWORDS = {
    "HORIZON": [
        "research", "innovation", "r&d", "science", "technology",
        "development", "prototype", "pilot", "demonstration", "cluster",
        "consortium", "collaborative", "breakthrough", "emerging",
    ],
    "DIGITAL": [
        "digital", "software", "ai", "artificial intelligence", "machine learning",
        "cloud", "data", "cybersecurity", "blockchain", "iot", "5g",
        "digitalization", "automation", "platform", "saas", "app",
    ],
    "EIC": [
        "startup", "sme", "scale-up", "accelerator", "disruptive",
        "market", "commercialization", "growth", "equity", "venture",
        "entrepreneur", "founder", "deep tech",
    ],
    "INNOVFUND": [
        "clean", "green", "renewable", "carbon", "emission", "climate",
        "hydrogen", "solar", "wind", "battery", "storage", "efficiency",
        "sustainable", "circular", "decarbonization",
    ],
    "LIFE": [
        "environment", "nature", "biodiversity", "ecosystem", "conservation",
        "waste", "recycling", "water", "pollution", "climate adaptation",
        "green", "sustainable", "organic",
    ],
    "CEF": [
        "infrastructure", "transport", "energy", "network", "corridor",
        "cross-border", "connectivity", "mobility", "freight", "rail",
    ],
    "ERASMUS": [
        "education", "training", "learning", "youth", "exchange",
        "mobility", "skills", "vocational", "academic", "university",
    ],
    "CREA": [
        "creative", "culture", "media", "content", "audiovisual",
        "film", "music", "arts", "heritage", "design", "fashion",
    ],
}

# Sector keywords for description matching
SECTOR_KEYWORDS = {
    "agriculture": ["farming", "agri", "crop", "livestock", "food production", "rural"],
    "manufacturing": ["production", "industry", "factory", "manufacturing", "assembly"],
    "it": ["software", "digital", "ai", "cloud", "data", "cyber", "tech"],
    "energy": ["energy", "renewable", "solar", "wind", "hydrogen", "battery"],
    "healthcare": ["health", "medical", "pharma", "biotech", "clinical", "patient"],
    "construction": ["construction", "building", "infrastructure", "renovation"],
    "transport": ["transport", "logistics", "mobility", "freight", "shipping"],
    "education": ["education", "training", "learning", "skills", "academic"],
}


def to_ascii(text: str) -> str:
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", str(text))
    return normalized.encode("ascii", "ignore").decode("ascii")


def load_db_config() -> Dict:
    """Load database connections from postgres skill config."""
    config_paths = [
        Path.home() / ".claude/skills/postgres/connections.json",
        Path.home() / ".config/claude/postgres-connections.json",
    ]

    for path in config_paths:
        if path.exists():
            with open(path) as f:
                return json.load(f)

    raise FileNotFoundError("No database config found. Check postgres skill setup.")


def get_db_connection(db_name: str):
    """Get database connection by name."""
    config = load_db_config()

    for db in config.get("databases", []):
        if db["name"].lower() == db_name.lower():
            return psycopg2.connect(
                host=db["host"],
                port=db.get("port", 5432),
                database=db["database"],
                user=db["user"],
                password=db.get("password", ""),
                sslmode=db.get("sslmode", "prefer"),
            )

    raise ValueError(f"Database '{db_name}' not found in config")


def get_company_size(employees: Optional[int]) -> str:
    """Categorize company by employee count."""
    if not employees:
        return "unknown"
    if employees < 10:
        return "micro"
    if employees < 50:
        return "small"
    if employees < 250:
        return "medium"
    return "large"


def is_sme(employees: Optional[int]) -> bool:
    """Check if company qualifies as SME (< 250 employees)."""
    if not employees:
        return True  # Assume SME if unknown
    return employees < 250


def get_caen_prefix(sector: Optional[str]) -> Optional[str]:
    """Extract first 2 digits of CAEN code."""
    if not sector:
        return None
    # Clean and extract digits
    clean = re.sub(r"[^\d]", "", str(sector))
    if len(clean) >= 2:
        return clean[:2]
    return None


def get_programmes_for_sector(sector: Optional[str]) -> List[str]:
    """Get relevant EU programmes for a CAEN sector code."""
    prefix = get_caen_prefix(sector)
    if prefix and prefix in CAEN_TO_PROGRAMMES:
        return CAEN_TO_PROGRAMMES[prefix]
    return []


def calculate_keyword_score(description: str, programmes: List[str]) -> int:
    """Score based on keyword matches in call description."""
    if not description:
        return 0

    desc_lower = description.lower()
    max_score = 0

    for prog in programmes:
        if prog in PROGRAMME_KEYWORDS:
            keywords = PROGRAMME_KEYWORDS[prog]
            matches = sum(1 for kw in keywords if kw in desc_lower)
            # Score: up to 30 points based on keyword matches
            score = min(30, matches * 5)
            max_score = max(max_score, score)

    return max_score


def calculate_sector_keyword_score(description: str, sector_name: Optional[str]) -> int:
    """Score based on sector-specific keywords in description."""
    if not description or not sector_name:
        return 0

    desc_lower = description.lower()
    sector_lower = sector_name.lower()

    for sector_key, keywords in SECTOR_KEYWORDS.items():
        if sector_key in sector_lower:
            matches = sum(1 for kw in keywords if kw in desc_lower)
            return min(15, matches * 3)

    return 0


def calculate_relevance_score(
    company: Dict,
    call: Dict,
) -> Tuple[int, str]:
    """
    Calculate relevance score (0-100) between company and funding call.

    Returns: (score, reason)
    """
    score = 0
    reasons = []

    # 1. Direct sector match (40 points)
    company_sector = company.get("sector")
    call_programme = call.get("programme", "")

    relevant_programmes = get_programmes_for_sector(company_sector)
    if call_programme in relevant_programmes:
        # Primary match
        score += 40
        reasons.append(f"Sector {company_sector} matches {call_programme}")
    elif relevant_programmes:
        # Partial match - sector has programmes but not this one
        score += 10
        reasons.append(f"Sector {company_sector} partially relevant")

    # 2. Keyword matching (30 points)
    description = call.get("description", "") or call.get("title", "")
    keyword_score = calculate_keyword_score(description, [call_programme])
    score += keyword_score
    if keyword_score > 15:
        reasons.append(f"Strong keyword match ({keyword_score}pts)")
    elif keyword_score > 0:
        reasons.append(f"Keyword match ({keyword_score}pts)")

    # Sector keyword bonus
    sector_bonus = calculate_sector_keyword_score(description, company.get("sector_name"))
    score += sector_bonus
    if sector_bonus > 0:
        reasons.append(f"Sector keywords ({sector_bonus}pts)")

    # 3. Size eligibility (20 points)
    employees = company.get("employees_count")
    call_title = (call.get("title", "") or "").lower()
    call_desc = (call.get("description", "") or "").lower()

    if is_sme(employees):
        # SME gets bonus for SME-targeted calls
        if "sme" in call_title or "sme" in call_desc:
            score += 20
            reasons.append("SME eligible")
        elif call_programme in ["EIC", "DIGITAL"]:
            score += 15
            reasons.append("SME-friendly programme")
        else:
            score += 10
            reasons.append("SME can apply")
    else:
        # Large company - only consortium projects
        if "consortium" in call_desc or "collaborative" in call_desc:
            score += 10
            reasons.append("Consortium eligible")
        else:
            # Penalty for large companies in SME-only calls
            if "sme" in call_title or "only sme" in call_desc:
                score -= 20
                reasons.append("Large company not eligible")

    # 4. Geographic/Romania bonus (10 points)
    # Romania is eligible for all EU programmes
    if company.get("country", "").upper() in ["RO", "ROMANIA"]:
        score += 5
        # Extra if call mentions Eastern Europe or convergence regions
        if any(x in call_desc for x in ["eastern europe", "convergence", "cohesion"]):
            score += 5
            reasons.append("Regional focus bonus")

    # Cap score at 100
    score = max(0, min(100, score))

    reason = "; ".join(reasons) if reasons else "General eligibility"
    return score, reason


def fetch_open_calls(
    conn,
    programme: Optional[str] = None,
) -> List[Dict]:
    """Fetch open funding calls from cifn_eu database."""
    query = """
        SELECT
            call_id,
            programme,
            title,
            description,
            budget_eur,
            deadline,
            status,
            url
        FROM calls
        WHERE status = 'open'
    """
    params = []

    if programme:
        query += " AND UPPER(programme) = UPPER(%s)"
        params.append(programme)

    query += " ORDER BY deadline ASC"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def fetch_companies(
    conn,
    cui: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 1000,
) -> List[Dict]:
    """Fetch companies from interjob_master database."""
    query = """
        SELECT
            name,
            cui,
            sector,
            sector_name,
            employees_count,
            city,
            country,
            email
        FROM companies
        WHERE email IS NOT NULL
    """
    params = []

    if cui:
        query += " AND cui = %s"
        params.append(cui)

    if sector:
        query += " AND sector LIKE %s"
        params.append(f"{sector}%")

    query += f" LIMIT {limit}"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def load_companies_from_csv(
    filepath: str,
    cui_col: str = "cui",
) -> List[Dict]:
    """Load companies from CSV file."""
    companies = []

    with open(filepath, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            company = {
                "name": row.get("name") or row.get("company_name") or row.get("nume_firma", ""),
                "cui": row.get(cui_col) or row.get("tax_id", ""),
                "sector": row.get("sector") or row.get("caen", ""),
                "sector_name": row.get("sector_name") or row.get("caen_name", ""),
                "employees_count": None,
                "city": row.get("city") or row.get("oras", ""),
                "country": row.get("country", "RO"),
                "email": row.get("email", ""),
            }
            # Parse employee count
            emp = row.get("employees_count") or row.get("employees") or row.get("angajati")
            if emp:
                try:
                    company["employees_count"] = int(re.sub(r"[^\d]", "", str(emp)))
                except ValueError:
                    pass

            companies.append(company)

    return companies


def match_grants(
    companies: List[Dict],
    calls: List[Dict],
    min_score: int = 20,
    size_filter: Optional[str] = None,
) -> List[Dict]:
    """Match companies to funding calls."""
    matches = []

    for company in companies:
        # Size filter
        if size_filter:
            company_size = get_company_size(company.get("employees_count"))
            if size_filter == "sme" and company_size == "large":
                continue
            if size_filter == "large" and company_size != "large":
                continue

        for call in calls:
            score, reason = calculate_relevance_score(company, call)

            if score >= min_score:
                matches.append({
                    "company_name": to_ascii(company.get("name", "")),
                    "company_cui": company.get("cui", ""),
                    "company_sector": company.get("sector", ""),
                    "company_sector_name": to_ascii(company.get("sector_name", "")),
                    "company_size": get_company_size(company.get("employees_count")),
                    "company_email": company.get("email", ""),
                    "grant_id": call.get("call_id", ""),
                    "grant_programme": call.get("programme", ""),
                    "grant_title": to_ascii(call.get("title", ""))[:100],
                    "grant_budget_eur": call.get("budget_eur"),
                    "grant_deadline": call.get("deadline"),
                    "grant_url": call.get("url", ""),
                    "relevance_score": score,
                    "match_reason": reason,
                })

    # Sort by score descending
    matches.sort(key=lambda x: x["relevance_score"], reverse=True)
    return matches


def save_matches(matches: List[Dict], output_path: str):
    """Save matches to CSV file."""
    if not matches:
        print("No matches to save")
        return

    # Ensure output directory exists
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "company_name", "company_cui", "company_sector", "company_sector_name",
        "company_size", "company_email", "grant_id", "grant_programme",
        "grant_title", "grant_budget_eur", "grant_deadline", "grant_url",
        "relevance_score", "match_reason",
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(matches)

    print(f"Saved {len(matches)} matches to {output_path}")


def print_summary(matches: List[Dict]):
    """Print summary of matches."""
    if not matches:
        print("\nNo matches found")
        return

    print(f"\n=== MATCH SUMMARY ===")
    print(f"Total matches: {len(matches)}")

    # By relevance
    high = sum(1 for m in matches if m["relevance_score"] >= 80)
    medium = sum(1 for m in matches if 50 <= m["relevance_score"] < 80)
    low = sum(1 for m in matches if m["relevance_score"] < 50)
    print(f"\nRelevance: HIGH={high}, MEDIUM={medium}, LOW={low}")

    # By programme
    programmes = {}
    for m in matches:
        prog = m["grant_programme"]
        programmes[prog] = programmes.get(prog, 0) + 1
    print(f"\nBy Programme:")
    for prog, count in sorted(programmes.items(), key=lambda x: -x[1]):
        print(f"  {prog}: {count}")

    # Top 5 matches
    print(f"\nTop 5 Matches:")
    for m in matches[:5]:
        print(f"  [{m['relevance_score']}] {m['company_name'][:30]} -> {m['grant_programme']}: {m['grant_title'][:40]}")


def main():
    parser = argparse.ArgumentParser(
        description="Match companies to eligible EU grants"
    )
    parser.add_argument("--input", "-i", help="Input CSV file with companies")
    parser.add_argument("--output", "-o", help="Output CSV file for matches")
    parser.add_argument("--cui", help="Match specific company by CUI")
    parser.add_argument("--sector", help="Filter by CAEN sector prefix")
    parser.add_argument("--programme", "-p", help="Filter by EU programme")
    parser.add_argument("--min-score", type=int, default=20, help="Minimum relevance score (0-100)")
    parser.add_argument("--size", choices=["sme", "large", "any"], default="any", help="Company size filter")
    parser.add_argument("--limit", type=int, default=1000, help="Max companies to process")
    parser.add_argument("--cui-col", default="cui", help="CUI column name in CSV")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed output")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be matched without saving")

    args = parser.parse_args()

    # Default output path
    if not args.output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        args.output = f"/opt/DATA/GRANT_MATCHES/matches_{timestamp}.csv"

    print("=== Grant Matcher ===")
    print(f"Min score: {args.min_score}")
    print(f"Size filter: {args.size}")
    if args.programme:
        print(f"Programme filter: {args.programme}")

    try:
        # Load companies
        if args.input:
            print(f"\nLoading companies from {args.input}...")
            companies = load_companies_from_csv(args.input, args.cui_col)
        else:
            print("\nLoading companies from database...")
            company_conn = get_db_connection("interjob_master")
            companies = fetch_companies(
                company_conn,
                cui=args.cui,
                sector=args.sector,
                limit=args.limit,
            )
            company_conn.close()

        print(f"Loaded {len(companies)} companies")

        # Load funding calls
        print("\nLoading open funding calls...")
        calls_conn = get_db_connection("cifn_eu")
        calls = fetch_open_calls(calls_conn, programme=args.programme)
        calls_conn.close()

        print(f"Loaded {len(calls)} open calls")

        if not calls:
            print("WARNING: No open funding calls found. Run eu-funding-calls skill to fetch latest.")
            return

        # Match
        print("\nMatching...")
        size_filter = args.size if args.size != "any" else None
        matches = match_grants(
            companies,
            calls,
            min_score=args.min_score,
            size_filter=size_filter,
        )

        # Summary
        print_summary(matches)

        # Verbose output
        if args.verbose and matches:
            print("\n=== DETAILED MATCHES ===")
            for m in matches[:20]:
                print(f"\n[{m['relevance_score']}] {m['company_name']}")
                print(f"  CUI: {m['company_cui']}, Sector: {m['company_sector']} ({m['company_sector_name']})")
                print(f"  Grant: {m['grant_programme']} - {m['grant_title']}")
                print(f"  Budget: EUR {m['grant_budget_eur']:,.0f}" if m['grant_budget_eur'] else "  Budget: TBD")
                print(f"  Deadline: {m['grant_deadline']}")
                print(f"  Reason: {m['match_reason']}")

        # Save
        if not args.dry_run and matches:
            save_matches(matches, args.output)
        elif args.dry_run:
            print(f"\nDry run - would save {len(matches)} matches to {args.output}")

    except FileNotFoundError as e:
        print(f"ERROR: {e}")
        sys.exit(1)
    except psycopg2.Error as e:
        print(f"Database error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
