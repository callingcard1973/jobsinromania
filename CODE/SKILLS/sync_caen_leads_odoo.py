#!/usr/bin/env python3
"""
Sync CAEN Sector Leads to Odoo CRM

Pushes scored leads from CAEN exports to Odoo CRM.
Creates leads in crm.lead with scores and tags.

Usage:
    python3 sync_caen_leads_odoo.py --sector horeca      # Sync HORECA leads
    python3 sync_caen_leads_odoo.py --all                # Sync all sectors
    python3 sync_caen_leads_odoo.py --bpo                # Sync BPO leads
    python3 sync_caen_leads_odoo.py --status             # Show sync status
    python3 sync_caen_leads_odoo.py --test               # Test Odoo connection

Odoo connection via SSH to raspibig docker.
"""

import subprocess
import json
import csv
import sys
from datetime import datetime
from pathlib import Path

# Paths
CAEN_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS")
BPO_EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/BPO_EUROPE")
STATE_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/.odoo_sync_state.json")

# Sectors to sync
SECTORS = [
    "call_centers", "horeca", "construction", "recruitment",
    "it_services", "transport", "manufacturing", "wholesale",
    "retail", "agriculture", "healthcare", "finance"
]


def run_odoo_sql(sql):
    """Execute SQL on Odoo DB via SSH + docker."""
    cmd = ["ssh", "raspibig", "docker", "exec", "-i", "odoo-db",
           "psql", "-U", "odoo", "-d", "odoo_db"]
    result = subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=30)
    if result.returncode != 0 and "ERROR" in result.stderr:
        print(f"SQL Error: {result.stderr}")
        return None
    return result.stdout.strip()


def run_odoo_sql_fetch(sql):
    """Execute SQL and return results."""
    cmd = ["ssh", "raspibig", "docker", "exec", "-i", "odoo-db",
           "psql", "-U", "odoo", "-d", "odoo_db", "-tA"]
    result = subprocess.run(cmd, input=sql, capture_output=True, text=True, timeout=30)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def escape_sql(s):
    """Escape single quotes for SQL."""
    if s is None or s == "":
        return "NULL"
    return "'" + str(s).replace("'", "''") + "'"


def test_connection():
    """Test Odoo connection."""
    print("Testing Odoo connection...")
    result = run_odoo_sql_fetch("SELECT 1")
    if result == "1":
        print("  ✓ Connected to Odoo DB")
        return True
    else:
        print("  ✗ Connection failed")
        return False


def ensure_tables():
    """Ensure custom tables exist in Odoo."""
    # Create caen_leads table if not exists
    sql = """
    CREATE TABLE IF NOT EXISTS caen_leads (
        id SERIAL PRIMARY KEY,
        company VARCHAR(255),
        email VARCHAR(255),
        phone VARCHAR(50),
        city VARCHAR(100),
        county VARCHAR(100),
        country VARCHAR(10) DEFAULT 'RO',
        sector VARCHAR(50),
        caen VARCHAR(20),
        caen_description VARCHAR(255),
        website VARCHAR(255),
        score INTEGER DEFAULT 0,
        tags VARCHAR(255),
        source VARCHAR(50),
        synced_at TIMESTAMP DEFAULT NOW(),
        UNIQUE(email, company)
    );

    CREATE INDEX IF NOT EXISTS idx_caen_leads_email ON caen_leads(email);
    CREATE INDEX IF NOT EXISTS idx_caen_leads_sector ON caen_leads(sector);
    CREATE INDEX IF NOT EXISTS idx_caen_leads_score ON caen_leads(score DESC);
    """
    run_odoo_sql(sql)
    print("  ✓ Tables ready")


def load_sector_csv(sector):
    """Load sector CSV file."""
    filepath = CAEN_EXPORT_DIR / f"{sector}_with_email.csv"
    if not filepath.exists():
        return []

    leads = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("email", "").strip().lower()
            if not email:
                continue
            leads.append({
                "company": row.get("company", row.get("company_name", "")),
                "email": email,
                "phone": row.get("phone", ""),
                "city": row.get("city", ""),
                "county": row.get("county", ""),
                "country": row.get("country", "RO"),
                "caen": row.get("caen", ""),
                "caen_description": row.get("caen_description", ""),
                "website": row.get("website", ""),
                "score": int(row.get("score", 0) or 0),
                "tags": row.get("tags", ""),
                "sector": sector
            })

    return leads


def load_bpo_csv():
    """Load BPO companies CSV."""
    filepath = BPO_EXPORT_DIR / "bpo_companies_europe.csv"
    if not filepath.exists():
        return []

    leads = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            email = row.get("email", "").strip().lower()
            if not email:
                continue
            leads.append({
                "company": row.get("company", ""),
                "email": email,
                "phone": row.get("phone", ""),
                "city": row.get("city", ""),
                "county": row.get("county", ""),
                "country": row.get("country", "RO"),
                "caen": row.get("caen", "8220"),
                "caen_description": "BPO/Call Center",
                "website": row.get("website", ""),
                "score": int(row.get("score", 0) or 0),
                "tags": row.get("tags", ""),
                "sector": "bpo"
            })

    return leads


def sync_leads_batch(leads, batch_size=100):
    """Sync leads to Odoo in batches."""
    synced = 0
    skipped = 0

    for i in range(0, len(leads), batch_size):
        batch = leads[i:i+batch_size]

        for lead in batch:
            # Check if already exists
            check_sql = f"SELECT id FROM caen_leads WHERE email = {escape_sql(lead['email'])}"
            existing = run_odoo_sql_fetch(check_sql)

            if existing:
                # Update score if higher
                update_sql = f"""
                UPDATE caen_leads SET
                    score = GREATEST(score, {lead['score']}),
                    tags = COALESCE(tags || ',' || {escape_sql(lead['tags'])}, {escape_sql(lead['tags'])}),
                    synced_at = NOW()
                WHERE email = {escape_sql(lead['email'])} AND score < {lead['score']};
                """
                run_odoo_sql(update_sql)
                skipped += 1
            else:
                # Insert new
                insert_sql = f"""
                INSERT INTO caen_leads
                (company, email, phone, city, county, country, sector, caen, caen_description, website, score, tags, source)
                VALUES (
                    {escape_sql(lead['company'][:255] if lead['company'] else '')},
                    {escape_sql(lead['email'])},
                    {escape_sql(lead['phone'])},
                    {escape_sql(lead['city'])},
                    {escape_sql(lead['county'])},
                    {escape_sql(lead['country'])},
                    {escape_sql(lead['sector'])},
                    {escape_sql(lead['caen'])},
                    {escape_sql(lead['caen_description'][:255] if lead['caen_description'] else '')},
                    {escape_sql(lead['website'])},
                    {lead['score']},
                    {escape_sql(lead['tags'])},
                    'caen_export'
                );
                """
                run_odoo_sql(insert_sql)
                synced += 1

        print(f"  Batch {i//batch_size + 1}: {synced} synced, {skipped} skipped")

    return synced, skipped


def sync_to_crm_lead(leads, source_sector):
    """Also create CRM leads in native Odoo crm.lead table."""
    # Get or create sales team
    team_id = run_odoo_sql_fetch("SELECT id FROM crm_team WHERE name = 'CAEN Leads' LIMIT 1")
    if not team_id:
        run_odoo_sql("""
            INSERT INTO crm_team (name, active, create_date, write_date)
            VALUES ('CAEN Leads', true, NOW(), NOW())
            RETURNING id;
        """)
        team_id = run_odoo_sql_fetch("SELECT id FROM crm_team WHERE name = 'CAEN Leads' LIMIT 1")

    created = 0
    for lead in leads:
        if lead['score'] < 30:  # Only high-value leads to CRM
            continue

        # Check if exists
        check = run_odoo_sql_fetch(f"SELECT id FROM crm_lead WHERE email_from = {escape_sql(lead['email'])}")
        if check:
            continue

        # Priority based on score
        priority = '0'  # Low
        if lead['score'] >= 50:
            priority = '2'  # High
        elif lead['score'] >= 40:
            priority = '1'  # Medium

        # Create CRM lead
        sql = f"""
        INSERT INTO crm_lead
        (name, partner_name, email_from, phone, city, country_id,
         type, active, probability, priority, description,
         team_id, create_date, write_date)
        VALUES (
            {escape_sql(f"[{source_sector.upper()}] {lead['company'][:100]}")},
            {escape_sql(lead['company'][:255])},
            {escape_sql(lead['email'])},
            {escape_sql(lead['phone'])},
            {escape_sql(lead['city'])},
            (SELECT id FROM res_country WHERE code = {escape_sql(lead['country'][:2])} LIMIT 1),
            'lead',
            true,
            {min(lead['score'], 100)},
            {escape_sql(priority)},
            {escape_sql(f"CAEN: {lead['caen']} - {lead['caen_description']}\nScore: {lead['score']}\nTags: {lead['tags']}")},
            {team_id},
            NOW(),
            NOW()
        );
        """
        run_odoo_sql(sql)
        created += 1

    return created


def show_status():
    """Show sync status."""
    print("\n=== CAEN Leads Odoo Sync Status ===\n")

    # Check connection
    if not test_connection():
        return

    # Get counts
    total = run_odoo_sql_fetch("SELECT COUNT(*) FROM caen_leads") or "0"
    by_sector = run_odoo_sql_fetch("""
        SELECT sector || ': ' || COUNT(*) FROM caen_leads GROUP BY sector ORDER BY COUNT(*) DESC
    """) or ""

    high_score = run_odoo_sql_fetch("SELECT COUNT(*) FROM caen_leads WHERE score >= 50") or "0"
    crm_leads = run_odoo_sql_fetch("SELECT COUNT(*) FROM crm_lead WHERE name LIKE '[%]%'") or "0"

    print(f"Total leads in Odoo: {total}")
    print(f"High-value (score>=50): {high_score}")
    print(f"CRM leads created: {crm_leads}")
    print(f"\nBy sector:")
    for line in by_sector.split('\n'):
        if line.strip():
            print(f"  {line}")

    # Local files
    print("\nLocal exports:")
    for sector in SECTORS:
        filepath = CAEN_EXPORT_DIR / f"{sector}_with_email.csv"
        if filepath.exists():
            with open(filepath) as f:
                rows = sum(1 for _ in f) - 1
            print(f"  {sector}: {rows} rows")


def load_state():
    """Load sync state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_sync": None, "synced_sectors": []}


def save_state(state):
    """Save sync state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Sync CAEN leads to Odoo")
    parser.add_argument("--sector", help="Sync specific sector")
    parser.add_argument("--all", action="store_true", help="Sync all sectors")
    parser.add_argument("--bpo", action="store_true", help="Sync BPO leads")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--test", action="store_true", help="Test connection")
    parser.add_argument("--crm", action="store_true", help="Also create CRM leads")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.test:
        test_connection()
        return

    # Test connection first
    if not test_connection():
        print("Cannot connect to Odoo. Exiting.")
        return

    # Ensure tables
    ensure_tables()

    state = load_state()
    total_synced = 0
    total_skipped = 0

    if args.bpo:
        print("\n=== Syncing BPO Leads ===")
        leads = load_bpo_csv()
        print(f"Loaded {len(leads)} BPO leads")
        synced, skipped = sync_leads_batch(leads)
        total_synced += synced
        total_skipped += skipped

        if args.crm:
            crm_created = sync_to_crm_lead(leads, "bpo")
            print(f"  ✓ Created {crm_created} CRM leads")

    sectors_to_sync = []
    if args.all:
        sectors_to_sync = SECTORS
    elif args.sector:
        sectors_to_sync = [args.sector]

    for sector in sectors_to_sync:
        print(f"\n=== Syncing {sector.upper()} ===")
        leads = load_sector_csv(sector)
        if not leads:
            print(f"  No leads found for {sector}")
            continue

        print(f"  Loaded {len(leads)} leads")
        synced, skipped = sync_leads_batch(leads)
        total_synced += synced
        total_skipped += skipped

        if args.crm:
            crm_created = sync_to_crm_lead(leads, sector)
            print(f"  ✓ Created {crm_created} CRM leads")

        state["synced_sectors"].append(sector)

    # Save state
    state["last_sync"] = datetime.now().isoformat()
    save_state(state)

    print(f"\n=== Summary ===")
    print(f"Synced: {total_synced}")
    print(f"Skipped (existing): {total_skipped}")
    print(f"Total: {total_synced + total_skipped}")

    if not args.all and not args.sector and not args.bpo:
        parser.print_help()


if __name__ == "__main__":
    main()
