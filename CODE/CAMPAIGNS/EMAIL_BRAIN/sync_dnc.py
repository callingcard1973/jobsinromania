#!/usr/bin/env python3
"""Sync master blacklist.txt to ALL per-campaign DNC tables. Daily cron."""
import psycopg2
from pathlib import Path

BL_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/EMAIL_CLEANUP/blacklist.txt")


def main():
    bl = set()
    if BL_FILE.exists():
        bl = {l.strip().lower() for l in BL_FILE.read_text().splitlines() if "@" in l}
    if not bl:
        print("Empty blacklist")
        return

    conn = psycopg2.connect(host="/var/run/postgresql",
        dbname="interjob_master", user="tudor", password="scraper123")
    cur = conn.cursor()

    cur.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%_dnc' AND table_schema='public'")
    tables = [r[0] for r in cur.fetchall()]

    total_added = 0
    for tbl in tables:
        try:
            # Check which columns exist (some have 3, some 4)
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s", (tbl,))
            cols = {r[0] for r in cur.fetchall()}
            has_reason = "reason" in cols

            added = 0
            for email in bl:
                if has_reason:
                    cur.execute(f"INSERT INTO {tbl} (email, reason) VALUES (%s, 'blacklist_sync') ON CONFLICT DO NOTHING", (email,))
                else:
                    cur.execute(f"INSERT INTO {tbl} (email) VALUES (%s) ON CONFLICT DO NOTHING", (email,))
                added += cur.rowcount
            conn.commit()
            if added:
                total_added += added
        except Exception:
            conn.rollback()

    # Also sync to email_sender.dnc
    try:
        conn2 = psycopg2.connect(host="/var/run/postgresql",
            dbname="email_sender", user="tudor")
        cur2 = conn2.cursor()
        for email in bl:
            cur2.execute("INSERT INTO dnc (email, reason) VALUES (%s, 'blacklist_sync') ON CONFLICT DO NOTHING", (email,))
        conn2.commit()
        cur2.close()
        conn2.close()
    except Exception:
        pass

    cur.close()
    conn.close()
    print(f"Synced {len(bl)} blacklist emails to {len(tables)} DNC tables. New: {total_added}")


if __name__ == "__main__":
    main()
