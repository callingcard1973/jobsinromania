#!/usr/bin/env python3
"""
Mautic CSV Export Skill

Exports contacts from PostgreSQL to Mautic-ready CSV with validation.

Usage:
    python3 mautic_csv_export.py --table bg_campaign --filter "campaign_status='pending'" --output bulgaria.csv
    python3 mautic_csv_export.py --config /path/to/config.json
    python3 mautic_csv_export.py --query "SELECT * FROM companies WHERE country='BG'"

Mautic default fields:
    email, firstname, lastname, company, position, phone, mobile, address1, address2,
    city, state, zipcode, country, website, facebook, twitter, linkedin, tags
"""

import argparse
import csv
import json
import os
import re
import sys
from datetime import datetime

# Default database connection (use socket for local)
DEFAULT_DB = {
    "host": "/var/run/postgresql",
    "port": 5432,
    "dbname": "interjob_master",
    "user": "tudor",
    "password": ""
}

# Mautic field mappings (source -> mautic)
DEFAULT_MAPPINGS = {
    "email": "email",
    "name": "company",
    "company_name": "company",
    "firma": "company",
    "company": "company",
    "phone": "phone",
    "telefon": "phone",
    "mobile": "mobile",
    "city": "city",
    "oras": "city",
    "город": "city",
    "country": "country",
    "tara": "country",
    "website": "website",
    "site": "website",
    "url": "website",
    "address": "address1",
    "adresa": "address1",
    "sector": "tags",
    "category": "tags",
    "industry": "tags",
    "source": "tags",
    "first_name": "firstname",
    "last_name": "lastname",
    "position": "position",
    "job_title": "position",
    "eik": "company_id",
    "cui": "company_id",
    "org_number": "company_id",
}

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def validate_email(email):
    """Check if email is valid."""
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def fix_email(email):
    """Try to fix a single email."""
    if not email:
        return None
    email = email.strip().replace(' ', '')
    if validate_email(email):
        return email
    return None


def split_emails(email_field):
    """Split multiple emails and return list of valid ones."""
    if not email_field:
        return []

    valid = []
    # Split by common separators
    for sep in [';', ',', ' ', '\n', '|']:
        if sep in email_field:
            parts = email_field.split(sep)
            for part in parts:
                fixed = fix_email(part)
                if fixed:
                    valid.append(fixed)
            return valid if valid else []

    # Single email
    fixed = fix_email(email_field)
    return [fixed] if fixed else []


def to_ascii(text):
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return ""
    import unicodedata
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii').strip()


def clean_value(value):
    """Clean a value for CSV export."""
    if value is None:
        return ""
    value = str(value).strip()
    # Remove problematic characters
    value = value.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    return value


def get_db_connection(db_config):
    """Get PostgreSQL connection."""
    try:
        import psycopg2
        return psycopg2.connect(
            host=db_config.get("host", "localhost"),
            port=db_config.get("port", 5432),
            dbname=db_config.get("dbname", "interjob_master"),
            user=db_config.get("user", "tudor"),
            password=db_config.get("password", "tudor")
        )
    except ImportError:
        print("ERROR: psycopg2 not installed. Run: pip install psycopg2-binary")
        sys.exit(1)


def export_to_mautic_csv(
    query=None,
    table=None,
    filter_clause=None,
    output_file=None,
    db_config=None,
    field_mappings=None,
    tags=None,
    country=None,
    ascii_only=True,
    validate=True,
    limit=None
):
    """
    Export data to Mautic-ready CSV.

    Args:
        query: Full SQL query (overrides table/filter)
        table: Table name to export from
        filter_clause: WHERE clause (without WHERE keyword)
        output_file: Output CSV path
        db_config: Database connection config
        field_mappings: Dict mapping source fields to Mautic fields
        tags: Default tags to add
        country: Default country
        ascii_only: Convert to ASCII
        validate: Validate emails
        limit: Max rows to export

    Returns:
        dict with stats
    """
    db_config = db_config or DEFAULT_DB
    field_mappings = field_mappings or DEFAULT_MAPPINGS

    # Build query
    if not query:
        if not table:
            raise ValueError("Must provide either query or table")
        query = f"SELECT * FROM {table}"
        if filter_clause:
            query += f" WHERE {filter_clause}"
        if limit:
            query += f" LIMIT {limit}"

    # Connect and fetch
    conn = get_db_connection(db_config)
    cur = conn.cursor()
    cur.execute(query)

    columns = [desc[0] for desc in cur.description]
    rows = cur.fetchall()

    cur.close()
    conn.close()

    # Map columns to Mautic fields
    mautic_fields = ["email", "company", "firstname", "lastname", "phone", "mobile",
                     "city", "country", "website", "address1", "position", "tags", "company_id"]

    col_to_mautic = {}
    for i, col in enumerate(columns):
        col_lower = col.lower()
        if col_lower in field_mappings:
            col_to_mautic[i] = field_mappings[col_lower]
        elif col_lower in mautic_fields:
            col_to_mautic[i] = col_lower

    # Process rows
    output_rows = []
    stats = {
        "total": len(rows),
        "valid": 0,
        "invalid_email": 0,
        "with_company": 0,
        "with_phone": 0,
    }

    invalid_emails = []

    for row in rows:
        record = {f: "" for f in mautic_fields}

        # Map values
        for i, value in enumerate(row):
            if i in col_to_mautic:
                mautic_field = col_to_mautic[i]
                clean_val = clean_value(value)
                if ascii_only:
                    clean_val = to_ascii(clean_val)

                # Handle tags (append, don't replace)
                if mautic_field == "tags" and record["tags"]:
                    record["tags"] += f",{clean_val}"
                else:
                    record[mautic_field] = clean_val

        # Add defaults
        if tags:
            if record["tags"]:
                record["tags"] = f"{tags},{record['tags']}"
            else:
                record["tags"] = tags
        if country and not record["country"]:
            record["country"] = country

        # Split and validate emails - create row for each valid email
        raw_email = record.get("email", "")
        if validate:
            valid_emails = split_emails(raw_email)
            if not valid_emails:
                stats["invalid_email"] += 1
                invalid_emails.append(raw_email[:50])
                continue

            # Create a row for EACH valid email
            for i, email in enumerate(valid_emails):
                row_copy = record.copy()
                row_copy["email"] = email

                if i == 0:
                    # Count stats only for first email
                    stats["valid"] += 1
                    if row_copy.get("company"):
                        stats["with_company"] += 1
                    if row_copy.get("phone") or row_copy.get("mobile"):
                        stats["with_phone"] += 1
                else:
                    stats["expanded"] = stats.get("expanded", 0) + 1

                output_rows.append(row_copy)
            continue  # Skip the normal append below

        stats["valid"] += 1
        if record.get("company"):
            stats["with_company"] += 1
        if record.get("phone") or record.get("mobile"):
            stats["with_phone"] += 1

        output_rows.append(record)

    # Determine output file
    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"/opt/ACTIVE/MAUTIC/docroot/media/files/export_{timestamp}.csv"

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Write CSV
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=mautic_fields, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(output_rows)

    stats["output_file"] = output_file
    stats["invalid_samples"] = invalid_emails[:5]

    return stats


def main():
    parser = argparse.ArgumentParser(description="Export contacts to Mautic CSV")
    parser.add_argument("--table", "-t", help="Source table name")
    parser.add_argument("--filter", "-f", help="WHERE clause filter")
    parser.add_argument("--query", "-q", help="Full SQL query")
    parser.add_argument("--output", "-o", help="Output CSV file path")
    parser.add_argument("--config", "-c", help="JSON config file")
    parser.add_argument("--tags", help="Default tags to add")
    parser.add_argument("--country", help="Default country")
    parser.add_argument("--limit", "-l", type=int, help="Max rows to export")
    parser.add_argument("--no-validate", action="store_true", help="Skip email validation")
    parser.add_argument("--no-ascii", action="store_true", help="Keep non-ASCII characters")
    parser.add_argument("--db-host", default="/var/run/postgresql")
    parser.add_argument("--db-name", default="interjob_master")
    parser.add_argument("--db-user", default="tudor")
    parser.add_argument("--db-pass", default="tudor")

    args = parser.parse_args()

    # Load config file if provided
    config = {}
    if args.config:
        with open(args.config) as f:
            config = json.load(f)

    # Build db_config
    db_config = {
        "host": args.db_host or config.get("db", {}).get("host", "localhost"),
        "dbname": args.db_name or config.get("db", {}).get("dbname", "interjob_master"),
        "user": args.db_user or config.get("db", {}).get("user", "tudor"),
        "password": args.db_pass or config.get("db", {}).get("password", "tudor"),
    }

    # Run export
    try:
        stats = export_to_mautic_csv(
            query=args.query or config.get("query"),
            table=args.table or config.get("table"),
            filter_clause=args.filter or config.get("filter"),
            output_file=args.output or config.get("output"),
            db_config=db_config,
            field_mappings=config.get("mappings"),
            tags=args.tags or config.get("tags"),
            country=args.country or config.get("country"),
            ascii_only=not args.no_ascii,
            validate=not args.no_validate,
            limit=args.limit or config.get("limit"),
        )

        # Print results
        print("=== MAUTIC CSV EXPORT ===")
        print(f"Source rows: {stats['total']}")
        print(f"Valid contacts: {stats['valid']}")
        expanded = stats.get('expanded', 0)
        if expanded:
            print(f"Expanded (multi-email): +{expanded}")
        total_exported = stats['valid'] + expanded
        print(f"Total exported: {total_exported}")
        print(f"Invalid emails: {stats['invalid_email']}")
        print(f"With company: {stats['with_company']} ({100*stats['with_company']//max(stats['valid'],1)}%)")
        print(f"With phone: {stats['with_phone']} ({100*stats['with_phone']//max(stats['valid'],1)}%)")
        print(f"")
        print(f"Output: {stats['output_file']}")
        if stats['invalid_samples']:
            print(f"Invalid samples: {stats['invalid_samples']}")
        print(f"")
        print(f"STATUS: {'OK' if stats['invalid_email'] == 0 else 'WARNING - some invalid emails skipped'}")

    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
