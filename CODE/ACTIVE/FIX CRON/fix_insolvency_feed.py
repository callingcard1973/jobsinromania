#!/usr/bin/env python3
"""Refresh interjob_master.insolvency from the freshly-scraped opendata.faliment (upsert by CUI, no deletes)."""
import argparse
from datetime import datetime, timezone
import psycopg2

SRC = "host=localhost dbname=opendata user=tudor password=REDACTED"
DST = "host=localhost dbname=interjob_master user=tudor password=REDACTED"
TAG = "opendata_faliment"  # marks rows this ETL owns, so re-runs update in place (never duplicate/delete)


def split_contact(c):
    """bpi_liquidator_contact is free text; route an email vs a phone."""
    c = (c or "").strip()
    if "@" in c:
        return c, ""
    return "", c


def clean_date(d):
    """faliment.bpi_date is free text (often blank/odd formats); coerce to a date or NULL."""
    if d is None:
        return None
    if not isinstance(d, str):
        return d
    d = d.strip()
    if not d:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(d[:19] if " " in d else d, fmt).date()
        except ValueError:
            continue
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="report what would change, write nothing")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    src = psycopg2.connect(SRC)
    sc = src.cursor()
    sc.execute("SET statement_timeout='600s'")
    q = ("SELECT cui, company_name, county, sector, status_name, phone, email, "
         "bpi_liquidator, bpi_liquidator_contact, bpi_date FROM faliment")
    if args.limit:
        q += f" LIMIT {args.limit}"
    sc.execute(q)
    rows = sc.fetchall()
    src.close()
    print(f"opendata.faliment rows read: {len(rows)}")

    dst = psycopg2.connect(DST)
    dc = dst.cursor()
    dc.execute("SET statement_timeout='600s'")
    dc.execute("SELECT cui, id FROM insolvency WHERE source=%s AND cui IS NOT NULL", (TAG,))
    existing = {r[0]: r[1] for r in dc.fetchall()}
    print(f"existing {TAG} rows in insolvency: {len(existing)}")

    now = datetime.now(timezone.utc)
    ins = upd = 0
    try:
        for cui, name, county, sector, status, phone, email, liq, liqc, bpi_date in rows:
            if not cui:
                continue
            liq_email, liq_phone = split_contact(liqc)
            bpi_date = clean_date(bpi_date) or None
            if args.dry_run:
                if cui in existing:
                    upd += 1
                else:
                    ins += 1
                continue
            if cui in existing:
                dc.execute(
                    "UPDATE insolvency SET company_name=%s, liquidator_name=%s, liquidator_email=%s, "
                    "liquidator_phone=%s, status=%s, date_filed=%s, sector=%s, company_email=%s, "
                    "company_phone=%s, created_at=%s WHERE id=%s",
                    (name, liq, liq_email, liq_phone, status, bpi_date, sector, email, phone, now, existing[cui]))
                upd += 1
            else:
                dc.execute(
                    "INSERT INTO insolvency (company_name, cui, country, liquidator_name, liquidator_email, "
                    "liquidator_phone, status, date_filed, sector, source, company_email, company_phone, "
                    "campaign_status, created_at) VALUES (%s,%s,'RO',%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending',%s)",
                    (name, cui, liq, liq_email, liq_phone, status, bpi_date, sector, TAG, email, phone, now))
                ins += 1
            if (ins + upd) % 5000 == 0:
                dst.commit()
        if not args.dry_run:
            dst.commit()
            dc.execute("SELECT COUNT(*), MAX(created_at) FROM insolvency")
            print("insolvency now:", dc.fetchone())
    finally:
        dc.close()
        dst.close()
    print(f"{'DRY ' if args.dry_run else ''}inserted={ins} updated={upd}")


if __name__ == "__main__":
    main()
