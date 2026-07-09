#!/usr/bin/env python3
"""Inspect ALL PostgreSQL databases on raspibig — tables, row counts, emails.
Run ON raspibig: python3 /tmp/inspect_all_dbs.py
"""

import psycopg2

DBS = [
    "interjob_master", "romania", "opendata", "food_distribution",
    "norway_emails", "denmark_emails", "email_sender", "eures",
    "scraper", "business_intelligence", "romania_emails",
]

CONN = "dbname={} user=tudor password=tudor host=localhost"


def inspect_db(dbname):
    try:
        conn = psycopg2.connect(CONN.format(dbname))
        cur = conn.cursor()
        cur.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname='public' ORDER BY tablename")
        tables = [r[0] for r in cur.fetchall()]
        print(f"\n{'='*60}")
        print(f"DATABASE: {dbname} ({len(tables)} tables)")
        print(f"{'='*60}")
        for t in tables:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {t}")
                cnt = cur.fetchone()[0]
                # Check for email column
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = %s AND table_schema = 'public' "
                    "AND column_name ILIKE '%%email%%'", (t,))
                email_cols = [r[0] for r in cur.fetchall()]
                email_info = ""
                if email_cols:
                    ecol = email_cols[0]
                    cur.execute(
                        f"SELECT COUNT(*) FROM {t} WHERE {ecol} IS NOT NULL AND {ecol} != ''")
                    ecnt = cur.fetchone()[0]
                    email_info = f" | {ecol}: {ecnt:,} with email"
                # Check for phone/country
                cur.execute(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name = %s AND table_schema = 'public' "
                    "AND column_name ILIKE '%%country%%'", (t,))
                country_cols = [r[0] for r in cur.fetchall()]
                country_info = ""
                if country_cols and cnt > 100:
                    ccol = country_cols[0]
                    cur.execute(
                        f"SELECT {ccol}, COUNT(*) FROM {t} "
                        f"WHERE {ccol} IS NOT NULL GROUP BY {ccol} "
                        f"ORDER BY COUNT(*) DESC LIMIT 5")
                    tops = cur.fetchall()
                    if tops:
                        country_info = " | top: " + ", ".join(
                            f"{r[0]}({r[1]:,})" for r in tops)
                print(f"  {t:40s} {cnt:>12,}{email_info}{country_info}")
            except Exception as ex:
                print(f"  {t:40s} ERROR: {ex}")
                conn.rollback()
        conn.close()
    except Exception as ex:
        print(f"\n{dbname}: CONNECTION ERROR: {ex}")


def main():
    for db in DBS:
        inspect_db(db)


if __name__ == "__main__":
    main()
