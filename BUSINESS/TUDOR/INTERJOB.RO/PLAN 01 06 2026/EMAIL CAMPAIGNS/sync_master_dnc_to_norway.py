#!/usr/bin/env python3
"""Bridge: MASTER_DNC.csv (bounce_manager output: Gmail mailer-daemon + Brevo bounces)
-> norway_dnc table, so the Norway sender actually suppresses bounced/blacklisted
addresses. bounce_manager runs every 7min and only writes MASTER_DNC.csv; send_norway
checks norway_dnc — this closes the gap. Idempotent (NOT EXISTS)."""
import csv
import psycopg2

MASTER_DNC = "/opt/ACTIVE/OPENDATA/DATA/MASTER_DNC.csv"


def main():
    conn = psycopg2.connect(host="/var/run/postgresql", dbname="interjob_master", user="tudor")
    cur = conn.cursor()
    added = 0
    try:
        rows = list(csv.DictReader(open(MASTER_DNC, encoding="utf-8", errors="ignore")))
    except OSError as e:
        print("MASTER_DNC.csv not readable:", e); return
    for row in rows:
        e = (row.get("email") or "").strip().lower()
        if "@" not in e:
            continue
        reason = "master_dnc:" + (row.get("type") or "bounce")
        cur.execute(
            "INSERT INTO norway_dnc(email,reason,added_at) SELECT %s,%s,now() "
            "WHERE NOT EXISTS(SELECT 1 FROM norway_dnc WHERE lower(email)=lower(%s))",
            (e, reason[:60], e))
        added += cur.rowcount
    conn.commit()
    cur.execute("SELECT count(*) FROM norway_dnc")
    print(f"MASTER_DNC -> norway_dnc: +{added} new (total norway_dnc now {cur.fetchone()[0]})")
    conn.close()


if __name__ == "__main__":
    main()
