#!/usr/bin/env python3
"""Replenish EXPORT_ES and EXPORT_BE campaign CSV lists from master DB.

Connects to raspibig PostgreSQL and extracts fresh wholesale buyer contacts
for Spain and Belgium, excluding already-sent addresses.

Usage:
    python3 export_replenish.py --dry-run    # Preview only
    python3 export_replenish.py              # Write new CSV files
"""

import argparse
import csv
import json
import os
import subprocess
import tempfile

RSYNC_CMD = "ssh tudor@192.168.100.21"
PG_CMD = "psql -U tudor -d interjob_master -At"

CAMPAIGNS = {
    "ES": {
        "csv_path": "/opt/ACTIVE/EMAIL/CAMPAIGNS/EXPORT_ES/DATA/export_buyers_spain.csv",
        "sent_path": "/opt/ACTIVE/EMAIL/CAMPAIGNS/EXPORT_ES/DATA/export_es_sent.json",
        "target_contacts": 300,
    },
    "BE": {
        "csv_path": "/opt/ACTIVE/EMAIL/CAMPAIGNS/EXPORT_BE/DATA/export_buyers_belgium.csv",
        "sent_path": "/opt/ACTIVE/EMAIL/CAMPAIGNS/EXPORT_BE/DATA/export_be_sent.json",
        "target_contacts": 200,
    },
}

COUNTRY_QUERIES = {
    "ES": {
        "code": "ES",
        "market_terms": ["fruta", "verdura", "hortofruticola", "alimentacion", "distribucion",
                        "mayorista", "import", "export", "fruit", "vegetable", "horti",
                        "mercado", "merca", "grocery", "supermercado"],
    },
    "BE": {
        "code": "BE",
        "market_terms": ["fruit", "vegetable", "grocery", "wholesale", "import", "export",
                        "horticulture", "distribution", "supermarket", "food"],
    },
}


def run_ssh(sql: str) -> str:
    result = subprocess.run(
        [*RSYNC_CMD.split(), f"{PG_CMD} -c {sql}"],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout.strip()


def run_ssh_file(sql_file: str) -> str:
    result = subprocess.run(
        [*RSYNC_CMD.split(), f"psql -U tudor -d interjob_master -f {sql_file}"],
        capture_output=True, text=True, timeout=300
    )
    return result.stdout.strip()


def get_existing_sent(path: str) -> set:
    try:
        raw = subprocess.run(
            [*RSYNC_CMD.split(), f"cat {path}"],
            capture_output=True, text=True, timeout=30
        )
        if raw.returncode != 0 or not raw.stdout.strip():
            return set()
        data = json.loads(raw.stdout)
        if isinstance(data, list):
            return set(data)
        if isinstance(data, dict):
            return set(data.keys())
        return set()
    except Exception:
        return set()


def get_existing_csv_emails(country: str) -> set:
    """Get already-used emails from existing CSV + sent."""
    cfg = CAMPAIGNS[country]
    existing = set()

    # Parse existing CSV
    raw = subprocess.run(
        [*RSYNC_CMD.split(), f"head -200 {cfg['csv_path']}"],
        capture_output=True, text=True, timeout=30
    )
    if raw.returncode == 0 and raw.stdout.strip():
        reader = csv.DictReader(raw.stdout.strip().split("\n"))
        for row in reader:
            email = row.get("email", "").strip().lower()
            if email:
                existing.add(email)

    # Parse sent file
    sent_raw = subprocess.run(
        [*RSYNC_CMD.split(), f"cat {cfg['sent_path']}"],
        capture_output=True, text=True, timeout=30
    )
    if sent_raw.returncode == 0 and sent_raw.stdout.strip():
        data = json.loads(sent_raw.stdout)
        if isinstance(data, list):
            existing.update(data)
        elif isinstance(data, dict):
            existing.update(data.keys())

    return existing


def find_fresh_contacts(country: str, exclude: set, count: int) -> list:
    """Find fresh wholesale buyer emails for given country."""
    info = COUNTRY_QUERIES[country]
    code = info["code"]

    queries = []
    for term in info["market_terms"]:
        queries.append(
            f"(country_detected='{code}' AND is_b2b=true AND is_bounced=false "
            f"AND (company ILIKE '%{term}%' OR industry ILIKE '%{term}%'))"
        )

    sql = (
        "SELECT DISTINCT LOWER(TRIM(email)), COALESCE(NULLIF(TRIM(company), ''), 'Unknown'), "
        f"'{code}' "
        "FROM master_emails WHERE "
        + " OR ".join(queries)
        + f" AND email !~ 'gmail|yahoo|hotmail|outlook|icloud|aol|mail\\.ru|yandex' "
        f"LIMIT {count * 2}"
    )

    with tempfile.NamedTemporaryFile(mode="w", suffix=".sql", delete=False) as f:
        f.write(sql + ";\n")

    try:
        remote_tmp = f"/tmp/export_fetch_{code}.sql"
        subprocess.run(
            ["scp", f.name, f"tudor@192.168.100.21:{remote_tmp}"],
            capture_output=True, timeout=30
        )
        output = run_ssh_file(remote_tmp)
    finally:
        os.unlink(f.name)
        subprocess.run(
            [*RSYNC_CMD.split(), f"rm -f /tmp/export_fetch_{code}.sql"],
            capture_output=True, timeout=15
        )

    contacts = []
    if not output:
        return contacts

    for line in output.strip().split("\n"):
        parts = line.split("|")
        if len(parts) < 2:
            continue
        email = parts[0].strip().lower()
        name = parts[1].strip() if len(parts) > 1 else "Unknown"
        ccode = parts[2].strip() if len(parts) > 2 else code
        if email and email not in exclude:
            contacts.append({"email": email, "name": name, "country": ccode})

    return contacts[:count]


def write_csv(country: str, contacts: list, dry_run: bool = False):
    """Write fresh CSV to raspibig."""
    if dry_run:
        print(f"\n[DRY RUN] Would write {len(contacts)} contacts to {CAMPAIGNS[country]['csv_path']}")
        for c in contacts[:5]:
            print(f"  {c['email']} | {c['name']} | {c['country']}")
        if len(contacts) > 5:
            print(f"  ... and {len(contacts) - 5} more")
        return

    lines = ["email,name,country"]
    for c in contacts:
        esc_name = c["name"].replace('"', '""')
        lines.append(f'{c["email"]},"{esc_name}",{c["country"]}')
    content = "\n".join(lines) + "\n"

    remote_path = CAMPAIGNS[country]["csv_path"]
    backup_path = remote_path + f".bak_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # Backup existing
    subprocess.run(
        [*RSYNC_CMD.split(), f"cp {remote_path} {backup_path}"],
        capture_output=True, timeout=15
    )

    # Write new CSV
    result = subprocess.run(
        [*RSYNC_CMD.split(), f"cat > {remote_path} << 'CSVEOF'\n{content}\nCSVEOF"],
        capture_output=True, text=True, timeout=30, shell=True
    )
    if result.returncode == 0:
        print(f"  Written {len(contacts)} contacts to {remote_path}")
        print(f"  Backup: {backup_path}")
    else:
        print(f"  ERROR writing CSV: {result.stderr}")


def main():
    parser = argparse.ArgumentParser(description="Replenish export campaign CSVs")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    args = parser.parse_args()

    for country, cfg in CAMPAIGNS.items():
        print(f"\n{'='*60}")
        print(f"Country: {country}")
        print(f"  Existing CSV: {cfg['csv_path']}")
        print(f"  Sent file: {cfg['sent_path']}")
        print(f"  Target: {cfg['target_contacts']} contacts")

        existing = get_existing_csv_emails(country)
        print(f"  Already used emails: {len(existing)}")

        contacts = find_fresh_contacts(country, existing, cfg["target_contacts"])
        print(f"  Fresh contacts found: {len(contacts)}")

        if contacts:
            write_csv(country, contacts, dry_run=args.dry_run)
        else:
            print("  No fresh contacts found — need alternative source")

    print("\nDone.")


if __name__ == "__main__":
    main()
