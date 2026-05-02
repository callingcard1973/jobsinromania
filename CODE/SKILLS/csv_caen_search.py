#!/usr/bin/env python3
"""
Universal CSV search by CAEN code and company name.

Usage:
    # Search by CAEN code
    python3 csv_caen_search.py --caen 8220
    python3 csv_caen_search.py --caen 5510,5520,5530    # Multiple codes
    python3 csv_caen_search.py --caen "55*"             # Wildcard (HORECA)
    python3 csv_caen_search.py --caen "41*,42*,43*"     # Construction

    # Search by company name
    python3 csv_caen_search.py --name "TELEPERFORMANCE"
    python3 csv_caen_search.py --name "call center"    # Fuzzy match

    # Combined search
    python3 csv_caen_search.py --caen 8220 --name "CALL"

    # Filter by location
    python3 csv_caen_search.py --caen 5510 --county "Bucuresti"
    python3 csv_caen_search.py --caen 5610 --city "Cluj-Napoca"

    # Output formats
    python3 csv_caen_search.py --caen 8220 --output results.csv
    python3 csv_caen_search.py --caen 8220 --json
    python3 csv_caen_search.py --caen 8220 --limit 50

    # With contact info only
    python3 csv_caen_search.py --caen 8220 --email-only
    python3 csv_caen_search.py --caen 8220 --phone-only

    # Show CAEN code info
    python3 csv_caen_search.py --lookup 8220
    python3 csv_caen_search.py --categories

Common CAEN Codes:
    8220 = Call centres
    55*  = Hotels, accommodation
    56*  = Restaurants, food service
    41*,42*,43* = Construction
    01*  = Agriculture
    10*,11* = Food & beverages manufacturing
    46*  = Wholesale trade
    47*  = Retail trade
    49*  = Transport
    62*  = IT services
    78*  = Employment agencies
"""
import os
import sys
import json
import csv
import sqlite3
import argparse
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii
except ImportError:
    def to_ascii(text):
        if not text:
            return text
        import unicodedata
        normalized = unicodedata.normalize('NFKD', str(text))
        return normalized.encode('ascii', 'ignore').decode('ascii')

# Paths
INDEX_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_INDEX")
DB_PATH = INDEX_DIR / "caen_search.db"
CAEN_DESCRIPTIONS_PATH = Path("/opt/ACTIVE/INFRA/SKILLS/caen_descriptions.json")


def get_db_connection():
    """Get database connection, build index if needed."""
    if not DB_PATH.exists():
        print(f"Index not found at {DB_PATH}")
        print("Building index... (this may take a few minutes)")
        import subprocess
        result = subprocess.run(
            [sys.executable, "/opt/ACTIVE/INFRA/SKILLS/build_caen_index.py"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error building index: {result.stderr}")
            sys.exit(1)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def parse_caen_pattern(pattern):
    """Parse CAEN pattern into SQL conditions.

    Supports:
    - Single code: "8220"
    - Multiple codes: "5510,5520,5530"
    - Wildcard: "55*" (all 55xx codes)
    - Mixed: "8220,55*,56*"
    """
    conditions = []
    params = []

    parts = [p.strip() for p in pattern.split(',')]

    for part in parts:
        if '*' in part:
            # Wildcard - convert to LIKE
            prefix = part.replace('*', '')
            conditions.append("caen LIKE ?")
            params.append(f"{prefix}%")
        else:
            # Exact match
            conditions.append("caen = ?")
            params.append(part)

    return " OR ".join(conditions), params


def normalize_name(name):
    """Normalize company name for matching."""
    if not name:
        return ""
    name = to_ascii(name).upper()
    for suffix in [" SRL", " SA", " SCS", " SCA", " PFA", " II", " IF", " LIMITED", " LTD"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    if name.startswith("SC "):
        name = name[3:]
    return name.strip()


def search(caen=None, name=None, county=None, city=None, country=None,
           email_only=False, phone_only=False, limit=100, offset=0):
    """Search companies by CAEN code and/or name."""
    conn = get_db_connection()
    cur = conn.cursor()

    conditions = []
    params = []

    # CAEN filter
    if caen:
        caen_cond, caen_params = parse_caen_pattern(caen)
        conditions.append(f"({caen_cond})")
        params.extend(caen_params)

    # Name filter (fuzzy)
    if name:
        name_normalized = normalize_name(name)
        conditions.append("company_name_normalized LIKE ?")
        params.append(f"%{name_normalized}%")

    # Location filters
    if county:
        conditions.append("county LIKE ?")
        params.append(f"%{to_ascii(county)}%")

    if city:
        conditions.append("city LIKE ?")
        params.append(f"%{to_ascii(city)}%")

    if country:
        conditions.append("country = ?")
        params.append(country.upper())

    # Contact filters
    if email_only:
        conditions.append("email != '' AND email IS NOT NULL")

    if phone_only:
        conditions.append("phone != '' AND phone IS NOT NULL")

    # Build query
    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT DISTINCT
            cui, company_name, caen, email, phone, city, county, country,
            (SELECT description FROM caen_codes WHERE code = companies.caen) as caen_description
        FROM companies
        WHERE {where_clause}
        ORDER BY priority ASC, company_name ASC
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    cur.execute(query, params)
    results = [dict(row) for row in cur.fetchall()]

    # Get total count
    count_query = f"""
        SELECT COUNT(DISTINCT cui || company_name)
        FROM companies
        WHERE {where_clause}
    """
    cur.execute(count_query, params[:-2])  # Exclude LIMIT/OFFSET params
    total = cur.fetchone()[0]

    conn.close()

    return results, total


def lookup_caen(code):
    """Look up CAEN code description."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT code, description, category
        FROM caen_codes
        WHERE code = ? OR code LIKE ?
    """, (code, f"{code}%"))

    results = [dict(row) for row in cur.fetchall()]

    # Also get count of companies with this code
    for r in results:
        cur.execute("SELECT COUNT(*) FROM companies WHERE caen = ?", (r['code'],))
        r['company_count'] = cur.fetchone()[0]

    conn.close()
    return results


def get_categories():
    """Get all CAEN categories with counts."""
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT d.category, COUNT(DISTINCT c.cui || c.company_name) as count
        FROM companies c
        JOIN caen_codes d ON c.caen = d.code
        GROUP BY d.category
        ORDER BY count DESC
    """)

    results = [{"category": row[0], "count": row[1]} for row in cur.fetchall()]
    conn.close()
    return results


def export_csv(results, output_path):
    """Export results to CSV."""
    if not results:
        print("No results to export")
        return

    fieldnames = ["company_name", "caen", "caen_description", "email", "phone",
                  "city", "county", "country", "cui"]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({k: row.get(k, '') for k in fieldnames})

    print(f"Exported {len(results)} results to {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Search CSV files by CAEN code and company name",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    # Search options
    parser.add_argument("--caen", "-c", help="CAEN code(s) to search (e.g., 8220, 55*, 5510,5520)")
    parser.add_argument("--name", "-n", help="Company name to search (fuzzy match)")
    parser.add_argument("--county", help="Filter by county")
    parser.add_argument("--city", help="Filter by city")
    parser.add_argument("--country", help="Filter by country code (default: all)")

    # Contact filters
    parser.add_argument("--email-only", action="store_true", help="Only show results with email")
    parser.add_argument("--phone-only", action="store_true", help="Only show results with phone")

    # Output options
    parser.add_argument("--output", "-o", help="Export results to CSV file")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--limit", "-l", type=int, default=100, help="Maximum results (default: 100)")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")

    # Lookup options
    parser.add_argument("--lookup", help="Look up CAEN code description")
    parser.add_argument("--categories", action="store_true", help="Show all CAEN categories")

    args = parser.parse_args()

    # Handle lookup
    if args.lookup:
        results = lookup_caen(args.lookup)
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            if not results:
                print(f"No CAEN code found matching: {args.lookup}")
            else:
                print(f"\nCAEN Code Lookup: {args.lookup}\n")
                for r in results:
                    print(f"  {r['code']}: {r['description']}")
                    print(f"         Category: {r['category']}")
                    print(f"         Companies: {r['company_count']:,}")
                    print()
        return

    # Handle categories
    if args.categories:
        results = get_categories()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            print("\nCAEN Categories:\n")
            for r in results:
                print(f"  {r['category']}: {r['count']:,} companies")
        return

    # Require at least one search criterion
    if not args.caen and not args.name:
        parser.print_help()
        print("\nError: Specify at least --caen or --name")
        sys.exit(1)

    # Perform search
    results, total = search(
        caen=args.caen,
        name=args.name,
        county=args.county,
        city=args.city,
        country=args.country,
        email_only=args.email_only,
        phone_only=args.phone_only,
        limit=args.limit,
        offset=args.offset
    )

    # Output
    if args.output:
        export_csv(results, args.output)
    elif args.json:
        print(json.dumps({
            "total": total,
            "limit": args.limit,
            "offset": args.offset,
            "results": results
        }, indent=2))
    else:
        # Table output
        print(f"\nFound {total:,} results (showing {len(results)}):\n")

        if results:
            # Header
            print(f"{'Company':<40} {'CAEN':<6} {'City':<15} {'Email':<30} {'Phone':<15}")
            print("-" * 110)

            for r in results:
                company = (r['company_name'] or '')[:38]
                caen = (r['caen'] or '')[:6]
                city = (r['city'] or '')[:13]
                email = (r['email'] or '')[:28]
                phone = (r['phone'] or '')[:13]
                print(f"{company:<40} {caen:<6} {city:<15} {email:<30} {phone:<15}")

            print("-" * 110)
            print(f"\nTotal: {total:,} companies")

            if total > len(results):
                print(f"Use --limit to see more results, or --output to export all")
        else:
            print("No results found")


if __name__ == "__main__":
    main()
