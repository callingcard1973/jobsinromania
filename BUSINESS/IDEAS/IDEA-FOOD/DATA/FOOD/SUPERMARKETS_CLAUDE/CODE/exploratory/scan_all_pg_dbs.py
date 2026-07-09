#!/usr/bin/env python3
"""Scan ALL PostgreSQL databases on raspibig for remaining SEAP emails.

Run ON raspibig: python3 /tmp/scan_all_pg_dbs.py
"""

import csv
import re
import unicodedata
import psycopg2

ENRICHED = "/opt/ACTIVE/OPENDATA/DATA/SEAP_ENRICHED/seap_food_winners_enriched.csv"
COLS = ["winner_name", "cui", "email", "phone", "website",
        "city", "address", "sector", "wins", "total_value_ron", "match_source"]
CONN = "dbname={} user=tudor password=tudor host=localhost"


def norm(name):
    if not name:
        return ""
    name = unicodedata.normalize("NFKD", str(name))
    name = name.encode("ascii", "ignore").decode("ascii").upper().strip()
    for s in [" SRL", " SA", " S.R.L.", " S.A.", " S.R.L", " S.A",
              " II", " PFA", " IF", " SNC", " SCS", " S.C.", " S.C", " SC"]:
        if name.endswith(s):
            name = name[:-len(s)].strip()
    if name.startswith("SC "):
        name = name[3:]
    if name.startswith("S.C. "):
        name = name[5:]
    name = re.sub(r"[^A-Z0-9 ]", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def strip_cui(cui):
    """Remove RO prefix and spaces from CUI."""
    return re.sub(r"[^0-9]", "", str(cui))


def load():
    enriched = {}
    with open(ENRICHED, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            enriched[row["cui"]] = row
    return enriched


def save(enriched):
    rows = sorted(enriched.values(), key=lambda x: -int(x.get("wins", 0)))
    with open(ENRICHED, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLS})


def scan_table(dbname, table, enriched, need, name_to_cui):
    """Scan a single table for CUI/email matches."""
    try:
        conn = psycopg2.connect(CONN.format(dbname))
        cur = conn.cursor()
        # Get columns
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = %s AND table_schema = 'public'", (table,))
        cols = [r[0] for r in cur.fetchall()]

        cui_cols = [c for c in cols if c.lower() in (
            "cui", "vat_id", "registration_id", "cod_fiscal",
            "cif", "cod_unic", "company_org_number", "tax_id")]
        email_cols = [c for c in cols if "email" in c.lower()]
        phone_cols = [c for c in cols if "phone" in c.lower() or "telefon" in c.lower()]
        name_cols = [c for c in cols if c.lower() in (
            "name", "company", "company_name", "denumire",
            "firma", "nume", "nume_firma", "company_name_ro")]

        if not email_cols:
            conn.close()
            return 0

        email_col = email_cols[0]
        cui_col = cui_cols[0] if cui_cols else None
        phone_col = phone_cols[0] if phone_cols else None
        name_col = name_cols[0] if name_cols else None

        # Build query
        sel_cols = [email_col]
        if cui_col:
            sel_cols.append(cui_col)
        if phone_col:
            sel_cols.append(phone_col)
        if name_col:
            sel_cols.append(name_col)

        cur.execute(
            f"SELECT {', '.join(sel_cols)} FROM {table} "
            f"WHERE {email_col} IS NOT NULL AND {email_col} != ''")

        hit = 0
        for row in cur:
            email = str(row[0]).strip()
            if not email or "@" not in email:
                continue
            # CUI match
            if cui_col:
                idx = sel_cols.index(cui_col)
                raw_cui = str(row[idx]).strip()
                c = strip_cui(raw_cui)
                if c in need:
                    enriched[need[c]]["email"] = email  # need maps stripped->original
                    if phone_col:
                        pi = sel_cols.index(phone_col)
                        enriched[need[c]]["phone"] = enriched[need[c]].get("phone") or str(row[pi] or "").strip()
                    enriched[need[c]]["match_source"] = f"pg:{dbname}.{table}"
                    hit += 1
                    continue
            # Name match
            if name_col:
                ni = sel_cols.index(name_col)
                n = norm(str(row[ni] or ""))
                if n and n in name_to_cui:
                    orig_cui = name_to_cui[n]
                    enriched[orig_cui]["email"] = email
                    if phone_col:
                        pi = sel_cols.index(phone_col)
                        enriched[orig_cui]["phone"] = enriched[orig_cui].get("phone") or str(row[pi] or "").strip()
                    enriched[orig_cui]["match_source"] = f"pg:{dbname}.{table}"
                    hit += 1
                    del name_to_cui[n]

        conn.close()
        return hit
    except Exception as ex:
        print(f"    ERROR {dbname}.{table}: {ex}")
        return 0


def main():
    enriched = load()

    # Build need dict with stripped CUIs
    need = {}  # stripped_cui -> original_cui
    name_to_cui = {}  # norm_name -> original_cui
    for cui, r in enriched.items():
        if r.get("email") or not cui:
            continue
        stripped = strip_cui(cui)
        if stripped:
            need[stripped] = cui
        n = norm(r.get("winner_name", ""))
        if n and len(n) >= 4:
            name_to_cui[n] = cui

    print(f"Need email: {len(need)}")

    # Databases and tables to scan
    DB_TABLES = [
        ("romania", "food_companies_master"),
        ("romania", "food_campaign_contacts"),
        ("romania", "rnpm_enriched_producers"),
        ("romania", "specialists"),
        ("romania", "contacts"),
        ("romania", "companies"),
        ("romania", "temp_auditori"),
        ("opendata", "companies"),
        ("opendata", "contacts"),
        ("email_sender", "contacts") if False else None,
        ("romania_emails", "contacts"),
        ("eures", "companies") if False else None,
        ("scraper", "companies") if False else None,
        ("denmark_emails", "contacts") if False else None,
        ("norway_emails", "contacts") if False else None,
        ("business_intelligence", "companies") if False else None,
    ]
    DB_TABLES = [x for x in DB_TABLES if x is not None]

    # Also scan ALL tables in romania and opendata
    for dbname in ["romania", "opendata", "scraper", "business_intelligence"]:
        try:
            conn = psycopg2.connect(CONN.format(dbname))
            cur = conn.cursor()
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname='public'")
            tables = [r[0] for r in cur.fetchall()]
            conn.close()
            for t in tables:
                key = (dbname, t)
                if key not in DB_TABLES:
                    DB_TABLES.append(key)
        except Exception:
            pass

    total_hit = 0
    for dbname, table in DB_TABLES:
        hit = scan_table(dbname, table, enriched, need, name_to_cui)
        if hit:
            print(f"  {dbname}.{table}: {hit} new emails")
            total_hit += hit

    print(f"\nTotal new from PG scan: {total_hit}")

    total = len(enriched)
    we = sum(1 for r in enriched.values() if r.get("email"))
    wp = sum(1 for r in enriched.values() if r.get("phone"))
    print(f"FINAL: {total} total")
    print(f"  email: {we} ({100 * we // total}%)")
    print(f"  phone: {wp} ({100 * wp // total}%)")
    print(f"  still need: {total - we}")

    save(enriched)
    print(f"Saved: {ENRICHED}")


if __name__ == "__main__":
    main()
