#!/usr/bin/env python3
"""
Build SQLite index for CAEN code searching across all CSVs.

Usage:
    python3 build_caen_index.py                    # Build full index
    python3 build_caen_index.py --incremental      # Update changed files only
    python3 build_caen_index.py --stats            # Show index statistics
    python3 build_caen_index.py --clean            # Rebuild from scratch
"""
import os
import sys
import csv
import json
import sqlite3
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

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

# CSV files to index - priority order (highest priority = 1)
CSV_SOURCES = [
    # Priority 1: Master files with email (best quality)
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER/romania_with_email.csv",
        "country": "RO", "priority": 1,
        "caen_col": "caen", "company_col": "company_name",
        "email_col": "email_1", "phone_col": "phone_1",
        "city_col": "city", "county_col": "county", "cui_col": "cui",
    },
    # Priority 2: EU Funds contacts (verified businesses)
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/EUFUNDS/eufunds_contacts.csv",
        "country": "RO", "priority": 2,
        "caen_col": "caen", "company_col": "company_name",
        "email_col": "email_1", "phone_col": "phone",
        "city_col": "city", "county_col": "county", "cui_col": "cui",
    },
    # Priority 3: ANOFM Employers (active recruiters)
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/EMPLOYERS_RO/employers_ro_enriched.csv",
        "country": "RO", "priority": 3,
        "caen_col": "anaf_caen", "company_col": "company",
        "email_col": "best_email", "phone_col": "best_phone",
        "city_col": "city", "county_col": "county", "cui_col": "cui",
    },
    # Priority 4: Bucharest/Ilfov established companies
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_fully_enriched.csv",
        "country": "RO", "priority": 4,
        "caen_col": "anaf_caen", "company_col": "denumire",
        "email_col": "enrich_email", "phone_col": "anaf_phone",
        "city_col": "localitate", "county_col": "judet", "cui_col": "cui",
    },
    # Priority 5: Construction companies
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/CONSTRUCTII/constructii_all.csv",
        "country": "RO", "priority": 5,
        "caen_col": "caen", "company_col": "nume_firma",
        "email_col": None, "phone_col": "telefon",
        "city_col": "localitate", "county_col": "judet", "cui_col": "cui",
    },
    # Priority 6: Unified Romania (large, may have dupes)
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/MASTER/romania_unified.csv",
        "country": "RO", "priority": 6,
        "caen_col": "caen", "company_col": "company_name",
        "email_col": "email_1", "phone_col": "phone_1",
        "city_col": "city", "county_col": "county", "cui_col": "cui",
    },
    # Priority 7: ANAF all phones (2.4M, phone only)
    {
        "path": "/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/anaf_all/all_phones.csv",
        "country": "RO", "priority": 7,
        "caen_col": "caen", "company_col": "name",
        "email_col": None, "phone_col": "phone",
        "city_col": None, "county_col": None, "cui_col": "cui",
    },
    # Priority 8: EU Funds financing contracts
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/FONDURIEUROPENE/ro/fonduri-ue/financing_contracts_clean.csv",
        "country": "RO", "priority": 8,
        "caen_col": "CAEN_CODE", "company_col": "BENEFICIAR",
        "email_col": "EMAIL", "phone_col": "PHONE",
        "city_col": "LOCALITATEA", "county_col": "JUDETUL", "cui_col": "BENEFICIARY_CODE",
    },
    # Priority 9: Firme 2016 enriched
    {
        "path": "/opt/ACTIVE/OPENDATA/FIRME_ROMANIA/DATA/firme_2016_FINAL.csv",
        "country": "RO", "priority": 9,
        "caen_col": "anaf_caen", "company_col": "company_name",
        "email_col": "email", "phone_col": "anaf_phone",
        "city_col": "city", "county_col": "county", "cui_col": "cui",
    },
    # Priority 10: Bucharest/Ilfov with phones
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/buc_ilfov_with_phones.csv",
        "country": "RO", "priority": 10,
        "caen_col": "anaf_caen", "company_col": "denumire",
        "email_col": None, "phone_col": "anaf_phone",
        "city_col": "localitate", "county_col": "judet", "cui_col": "cui",
    },
    # Priority 11: Oldest companies enriched
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BUCHAREST_ILFOV_ESTABLISHED/oldest_companies_enriched.csv",
        "country": "RO", "priority": 11,
        "caen_col": "anaf_caen", "company_col": "denumire",
        "email_col": "enrich_email", "phone_col": "anaf_phone",
        "city_col": "localitate", "county_col": "judet", "cui_col": "cui",
    },
    # Priority 12: HORECA all
    {
        "path": "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/BILANT/horeca_all.csv",
        "country": "RO", "priority": 12,
        "caen_col": "caen", "company_col": "company_name",
        "email_col": None, "phone_col": "phone",
        "city_col": "city", "county_col": "county", "cui_col": "cui",
    },
]


def get_file_hash(filepath):
    """Get MD5 hash of first 100KB + file size for change detection."""
    path = Path(filepath)
    if not path.exists():
        return None
    size = path.stat().st_size
    with open(path, 'rb') as f:
        data = f.read(102400)  # First 100KB
    return hashlib.md5(data + str(size).encode()).hexdigest()


def init_database():
    """Initialize SQLite database with proper schema."""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Main companies table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cui TEXT,
            company_name TEXT NOT NULL,
            company_name_normalized TEXT,
            caen TEXT,
            caen_description TEXT,
            email TEXT,
            phone TEXT,
            city TEXT,
            county TEXT,
            country TEXT DEFAULT 'RO',
            source_file TEXT,
            priority INTEGER DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # File index for incremental updates
    cur.execute("""
        CREATE TABLE IF NOT EXISTS file_index (
            path TEXT PRIMARY KEY,
            file_hash TEXT,
            rows_indexed INTEGER,
            last_indexed TIMESTAMP,
            caen_column TEXT,
            status TEXT DEFAULT 'indexed'
        )
    """)

    # CAEN codes reference
    cur.execute("""
        CREATE TABLE IF NOT EXISTS caen_codes (
            code TEXT PRIMARY KEY,
            description TEXT,
            category TEXT
        )
    """)

    # Create indexes for fast searching
    cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_caen ON companies(caen)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_name ON companies(company_name_normalized)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_email ON companies(email)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_country ON companies(country)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_companies_county ON companies(county)")

    conn.commit()
    return conn


def load_caen_descriptions(conn):
    """Load CAEN descriptions into database."""
    if not CAEN_DESCRIPTIONS_PATH.exists():
        print(f"Warning: CAEN descriptions not found at {CAEN_DESCRIPTIONS_PATH}")
        return

    with open(CAEN_DESCRIPTIONS_PATH) as f:
        descriptions = json.load(f)

    cur = conn.cursor()
    cur.execute("DELETE FROM caen_codes")

    for code, desc in descriptions.items():
        # Determine category from first 2 digits
        prefix = code[:2]
        categories = {
            "01": "Agriculture", "02": "Forestry", "03": "Fishing",
            "05": "Mining", "06": "Mining", "07": "Mining", "08": "Mining", "09": "Mining",
            "10": "Food", "11": "Beverages", "12": "Tobacco",
            "13": "Textiles", "14": "Apparel", "15": "Leather",
            "16": "Wood", "17": "Paper", "18": "Printing",
            "19": "Petroleum", "20": "Chemicals", "21": "Pharma",
            "22": "Rubber/Plastic", "23": "Mineral products", "24": "Metals",
            "25": "Fabricated metals", "26": "Electronics", "27": "Electrical",
            "28": "Machinery", "29": "Motor vehicles", "30": "Transport equipment",
            "31": "Furniture", "32": "Other manufacturing", "33": "Repair",
            "35": "Utilities", "36": "Water", "37": "Sewerage", "38": "Waste", "39": "Remediation",
            "41": "Construction", "42": "Civil engineering", "43": "Specialized construction",
            "45": "Automotive trade", "46": "Wholesale", "47": "Retail",
            "49": "Land transport", "50": "Water transport", "51": "Air transport",
            "52": "Warehousing", "53": "Postal",
            "55": "Accommodation", "56": "Food service",
            "58": "Publishing", "59": "Film/TV", "60": "Broadcasting", "61": "Telecom",
            "62": "IT", "63": "Information services",
            "64": "Finance", "65": "Insurance", "66": "Financial auxiliaries",
            "68": "Real estate", "69": "Legal/Accounting", "70": "Management",
            "71": "Architecture/Engineering", "72": "R&D", "73": "Advertising",
            "74": "Professional services", "75": "Veterinary",
            "77": "Rental", "78": "Employment", "79": "Travel",
            "80": "Security", "81": "Facilities", "82": "Business support",
            "84": "Public administration", "85": "Education",
            "86": "Health", "87": "Residential care", "88": "Social work",
            "90": "Arts", "91": "Libraries/Museums", "92": "Gambling", "93": "Sports/Recreation",
            "94": "Membership orgs", "95": "Repair services", "96": "Personal services",
            "97": "Households", "98": "Households", "99": "Extraterritorial",
        }
        category = categories.get(prefix, "Other")

        cur.execute(
            "INSERT OR REPLACE INTO caen_codes (code, description, category) VALUES (?, ?, ?)",
            (code, desc, category)
        )

    conn.commit()
    print(f"Loaded {len(descriptions)} CAEN code descriptions")


def normalize_company_name(name):
    """Normalize company name for fuzzy matching."""
    if not name:
        return ""
    name = to_ascii(name).upper()
    # Remove common suffixes
    for suffix in [" SRL", " SA", " SCS", " SCA", " PFA", " II", " IF", " ONG", " IFN",
                   " S.R.L.", " S.A.", " S.C.S.", " LIMITED", " LTD", " GMBH", " AG"]:
        if name.endswith(suffix):
            name = name[:-len(suffix)]
    # Remove "SC " prefix
    if name.startswith("SC "):
        name = name[3:]
    return name.strip()


def index_csv(conn, source, incremental=False):
    """Index a single CSV file."""
    path = Path(source["path"])
    if not path.exists():
        print(f"  Skipping {path} (not found)")
        return 0

    cur = conn.cursor()

    # Check if file changed (for incremental)
    file_hash = get_file_hash(path)
    if incremental:
        cur.execute("SELECT file_hash FROM file_index WHERE path = ?", (str(path),))
        row = cur.fetchone()
        if row and row[0] == file_hash:
            print(f"  Skipping {path.name} (unchanged)")
            return 0

    print(f"  Indexing {path.name}...")

    # Delete existing entries for this file
    cur.execute("DELETE FROM companies WHERE source_file = ?", (str(path),))

    # Parse CSV
    rows_indexed = 0
    batch = []
    batch_size = 10000

    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f)

            for row in reader:
                # Get CAEN code
                caen = row.get(source.get("caen_col", "caen"), "").strip()
                if not caen:
                    continue

                # Extract fields
                company = row.get(source.get("company_col", "company_name"), "").strip()
                if not company:
                    continue

                email = row.get(source.get("email_col", "email"), "").strip() if source.get("email_col") else ""
                phone = row.get(source.get("phone_col", "phone"), "").strip() if source.get("phone_col") else ""
                city = row.get(source.get("city_col", "city"), "").strip() if source.get("city_col") else ""
                county = row.get(source.get("county_col", "county"), "").strip() if source.get("county_col") else ""
                cui = row.get(source.get("cui_col", "cui"), "").strip() if source.get("cui_col") else ""

                # Get CAEN description
                caen_desc = row.get("caen_description", "") or ""

                batch.append((
                    cui,
                    company,
                    normalize_company_name(company),
                    caen,
                    caen_desc,
                    email,
                    phone,
                    city,
                    county,
                    source.get("country", "RO"),
                    str(path),
                    source.get("priority", 10),
                ))

                if len(batch) >= batch_size:
                    cur.executemany("""
                        INSERT INTO companies
                        (cui, company_name, company_name_normalized, caen, caen_description,
                         email, phone, city, county, country, source_file, priority)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, batch)
                    rows_indexed += len(batch)
                    batch = []
                    print(f"    {rows_indexed:,} rows...")

        # Insert remaining
        if batch:
            cur.executemany("""
                INSERT INTO companies
                (cui, company_name, company_name_normalized, caen, caen_description,
                 email, phone, city, county, country, source_file, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, batch)
            rows_indexed += len(batch)

        # Update file index
        cur.execute("""
            INSERT OR REPLACE INTO file_index (path, file_hash, rows_indexed, last_indexed, caen_column, status)
            VALUES (?, ?, ?, ?, ?, 'indexed')
        """, (str(path), file_hash, rows_indexed, datetime.now().isoformat(), source.get("caen_col")))

        conn.commit()
        print(f"    Indexed {rows_indexed:,} rows from {path.name}")

    except Exception as e:
        print(f"    Error indexing {path.name}: {e}")
        return 0

    return rows_indexed


def show_stats(conn):
    """Show index statistics."""
    cur = conn.cursor()

    print("\n=== CAEN INDEX STATISTICS ===\n")

    # Total companies
    cur.execute("SELECT COUNT(*) FROM companies")
    total = cur.fetchone()[0]
    print(f"Total indexed companies: {total:,}")

    # By country
    print("\nBy Country:")
    cur.execute("SELECT country, COUNT(*) FROM companies GROUP BY country ORDER BY COUNT(*) DESC")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,}")

    # Top CAEN codes
    print("\nTop 15 CAEN Codes:")
    cur.execute("""
        SELECT c.caen, COALESCE(d.description, 'Unknown'), COUNT(*)
        FROM companies c
        LEFT JOIN caen_codes d ON c.caen = d.code
        GROUP BY c.caen
        ORDER BY COUNT(*) DESC
        LIMIT 15
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1][:40]}... ({row[2]:,})")

    # With email/phone
    cur.execute("SELECT COUNT(*) FROM companies WHERE email != '' AND email IS NOT NULL")
    with_email = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM companies WHERE phone != '' AND phone IS NOT NULL")
    with_phone = cur.fetchone()[0]
    print(f"\nWith email: {with_email:,} ({with_email/total*100:.1f}%)")
    print(f"With phone: {with_phone:,} ({with_phone/total*100:.1f}%)")

    # Indexed files
    print("\nIndexed Files:")
    cur.execute("SELECT path, rows_indexed, last_indexed FROM file_index ORDER BY rows_indexed DESC")
    for row in cur.fetchall():
        path = Path(row[0]).name
        print(f"  {path}: {row[1]:,} rows ({row[2][:10]})")

    # CAEN categories
    print("\nCAEN Categories (top 10):")
    cur.execute("""
        SELECT d.category, COUNT(*)
        FROM companies c
        JOIN caen_codes d ON c.caen = d.code
        GROUP BY d.category
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]:,}")


def main():
    parser = argparse.ArgumentParser(description="Build CAEN search index")
    parser.add_argument("--incremental", action="store_true", help="Only update changed files")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")
    parser.add_argument("--clean", action="store_true", help="Rebuild from scratch")
    args = parser.parse_args()

    if args.clean and DB_PATH.exists():
        print(f"Removing existing database: {DB_PATH}")
        DB_PATH.unlink()

    conn = init_database()

    if args.stats:
        show_stats(conn)
        conn.close()
        return

    print("Building CAEN search index...")
    print(f"Database: {DB_PATH}")

    # Load CAEN descriptions
    load_caen_descriptions(conn)

    # Index all CSV sources
    total_indexed = 0
    for source in CSV_SOURCES:
        total_indexed += index_csv(conn, source, incremental=args.incremental)

    print(f"\nTotal rows indexed: {total_indexed:,}")

    # Show stats
    show_stats(conn)

    conn.close()
    print(f"\nIndex saved to: {DB_PATH}")


if __name__ == "__main__":
    main()
