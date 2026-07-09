#!/usr/bin/env python3
"""Refresh anofm.dnc_master on raspi from raspibig's FRESH DNC files.

DNC generation stays on raspibig (gmail_bounce_cleaner.py: Gmail+Brevo bounces;
universal_reply_handler.py: explicit opt-out replies -> dnc_list.csv) — both
rewritten every 2h. raspi pulls the fresh files and rebuilds the unified
dnc_master, which the ANOFM campaign + audience rebuild suppress against.
NOTE: master_dnc.csv is STALE (Apr 2026) — do NOT use it; pull the live files."""
import re
import subprocess
import sys
import psycopg2
from pathlib import Path

DB = dict(dbname="anofm", user="tudor", host="localhost", password="tudor")
REMOTE = "tudor@192.168.100.21:/opt/ACTIVE/EMAIL/CAMPAIGNS"
LOCAL = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/DATA")
# live, every-2h sources on raspibig (bounces + opt-out replies)
FILES = ["dnc_bounces.txt", "dnc_list.csv", "dnc_bounces_annotated.csv"]
RX = re.compile(r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}")


def pull():
    for f in FILES:
        try:
            subprocess.run(
                ["rsync", "-az", "-e", "ssh -o BatchMode=yes -o StrictHostKeyChecking=no",
                 f"{REMOTE}/{f}", str(LOCAL / f)],
                check=True, timeout=60)
        except Exception as e:
            print(f"WARN: pull {f} failed ({e})", file=sys.stderr)


def emails_from(path):
    s = set()
    try:
        for line in open(path, encoding="utf-8", errors="ignore"):
            s.update(RX.findall(line.lower()))
    except FileNotFoundError:
        pass
    return s


def main():
    pull()
    dnc = set()
    for f in FILES:
        dnc |= emails_from(LOCAL / f)
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    # keep legacy anofm.dnc unioned in
    cur.execute("SELECT lower(email) FROM dnc")
    dnc |= {r[0] for r in cur.fetchall() if r[0]}
    cur.execute("CREATE TABLE IF NOT EXISTS dnc_master(email text primary key, added_at timestamp default now())")
    cur.execute("TRUNCATE dnc_master")
    cur.executemany("INSERT INTO dnc_master(email) VALUES(%s) ON CONFLICT DO NOTHING",
                    [(e,) for e in dnc])
    conn.commit()
    cur.execute("SELECT count(*) FROM dnc_master")
    print(f"dnc_master refreshed: {cur.fetchone()[0]} emails")
    conn.close()


if __name__ == "__main__":
    main()
