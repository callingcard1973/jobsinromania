#!/usr/bin/env python3
"""Feed latest ANOFM CSV → tudor.db (ANOFM_TUDOR campaign).
Run after each scrape. Deduplicates on email. Maps sectors.
"""
import csv
import glob
import os
import re
import sqlite3
from pathlib import Path

CSV_DIR  = Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ROMANIA/ANOFM/DOCKER/PROGRAMS")
DB_PATH  = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_TUDOR_MIGRATED_TO_RASPI/tudor.db")
DNC_FILE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_list.csv")

JOB_TITLE_MAP = {
    # Productie
    "operator": "productie", "masini": "productie", "cnc": "productie",
    "sudor": "productie", "lacatus": "productie", "strungar": "productie",
    "frezor": "productie", "rectificator": "productie", "montator": "productie",
    "asamblor": "productie", "ambalator": "productie", "confectioner": "productie",
    "croitor": "productie", "tesator": "productie", "tricoteur": "productie",
    "electrotehnist": "productie", "electrician": "productie", "automatist": "productie",
    "mecanic utilaj": "productie", "sculer": "productie", "matriter": "productie",
    "vopsitor": "productie", "galvanizator": "productie",
    # Constructii
    "zidar": "constructii", "zugrav": "constructii", "faiantar": "constructii",
    "dulgher": "constructii", "fierar": "constructii", "betonist": "constructii",
    "tencuitor": "constructii", "instalator": "constructii", "electrician instal": "constructii",
    "hidroizolator": "constructii", "constructor": "constructii",
    # Transport
    "sofer": "transport", "conducator auto": "transport", "curier": "transport",
    "dispecer": "transport", "logistician": "transport", "stivuitorist": "transport",
    "manipulant": "transport", "depozit": "transport",
    # Agricultura
    "lucrator agricol": "agricultura", "agricultor": "agricultura",
    "crescator": "agricultura", "zootehnist": "agricultura", "gradinar": "agricultura",
    # Sanatate
    "asistent": "sanatate", "medic": "sanatate", "farmacist": "sanatate",
    "infirmier": "sanatate", "kinetoterapeut": "sanatate",
    # IT
    "programator": "it", "developer": "it", "analist": "it",
    "administrator retea": "it", "tehnician it": "it",
    # Auto
    "mecanic auto": "auto", "tinichigiu": "auto", "vulcanizator": "auto",
    "electrician auto": "auto",
    # Mobila/Lemn
    "tamplar": "mobila", "lemnar": "mobila", "lacuitor": "mobila",
    # Cleaning
    "ingrijitor": "cleaning", "muncitor curatenie": "cleaning",
    # Paza
    "agent paza": "paza", "paznic": "paza", "agent securitate": "paza",
}

SECTOR_MAP = {
    "construc": "constructii", "instalat": "constructii",
    "transport": "transport", "logistic": "transport",
    "horeca": "horeca", "turism": "horeca", "alimenta": "horeca",
    "productie": "productie", "manufactur": "productie", "industrie": "productie",
    "agricol": "agricultura", "agri": "agricultura",
    "it": "it", "software": "it", "telecomunica": "it",
    "sanatate": "sanatate", "medical": "sanatate", "farma": "sanatate",
    "comert": "comert", "retail": "comert", "vanzari": "vanzari",
    "curatenie": "cleaning", "menaj": "cleaning",
    "paza": "paza", "securitate": "paza",
    "confectii": "confectii", "textile": "confectii",
    "mobila": "mobila", "lemn": "mobila",
    "auto": "auto", "mecanic": "auto",
}

def map_sector(job_title: str, sector_raw: str = "") -> str:
    title_low = job_title.lower() if job_title else ""
    for key, val in JOB_TITLE_MAP.items():
        if key in title_low:
            return val
    sector_low = sector_raw.lower() if sector_raw else ""
    for key, val in SECTOR_MAP.items():
        if key in sector_low:
            return val
    return "general"

def load_dnc() -> set:
    if not DNC_FILE.exists():
        return set()
    with open(DNC_FILE) as f:
        return {line.strip().lower() for line in f if line.strip()}

def latest_csv() -> Path | None:
    files = sorted(CSV_DIR.glob("anofm_jobs_*.csv"), reverse=True)
    return files[0] if files else None

def norm_email(e: str) -> str:
    e = e.strip().lower()
    if re.match(r'^[\w.+-]+@[\w.-]+\.[a-z]{2,}$', e):
        return e
    return ""

def feed(csv_path: Path) -> tuple[int, int]:
    dnc = load_dnc()
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    added = skipped = 0

    with open(csv_path, newline="", encoding="utf-8-sig", errors="ignore") as f:
        for row in csv.DictReader(f):
            company   = (row.get("company_name") or "").strip()
            city      = (row.get("city") or row.get("company_city") or "").strip()
            job_title = (row.get("job_title") or "").strip().title()
            job_id    = (row.get("job_id") or "").strip()
            sector    = map_sector(job_title, row.get("sector") or "")
            contact   = (row.get("contact_person_1") or "").strip()
            county    = (row.get("region") or "").strip()

            for field in ("email_1", "email_2", "email_3"):
                email = norm_email(row.get(field) or "")
                if not email or email in dnc:
                    continue
                try:
                    # Check if email already pending — append position
                    existing = cur.execute(
                        "SELECT id, position FROM contacts WHERE email=? AND status='pending'",
                        (email,)
                    ).fetchone()
                    if existing:
                        existing_id, existing_pos = existing
                        positions = [p.strip() for p in (existing_pos or "").split("\n") if p.strip()]
                        if job_title and job_title not in positions:
                            positions.append(job_title)
                            cur.execute(
                                "UPDATE contacts SET position=? WHERE id=?",
                                ("\n".join(positions), existing_id)
                            )
                        skipped += 1
                    else:
                        cur.execute(
                            "INSERT OR IGNORE INTO contacts "
                            "(email,job_id,company,city,county,contact_name,sector,source,status,position) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?)",
                            (email, job_id, company, city, county, contact, sector, "anofm_csv", "pending", job_title)
                        )
                        if cur.rowcount:
                            added += 1
                        else:
                            skipped += 1
                except Exception:
                    skipped += 1

    conn.commit()
    conn.close()
    return added, skipped

def trigger_sender(new_count: int):
    import fcntl
    import json
    import subprocess
    import sys
    import time

    sender     = Path(__file__).parent / "tudor_sender.py"
    state_file = Path(__file__).parent / ".tudor_sender_state.json"
    lock_file  = Path(__file__).parent / ".tudor_sender.lock"

    BREVO_DAY_LIMIT = 290
    GMAIL_DAY_LIMIT = 550
    A2_DAY_LIMIT    = 30

    def daily_limits_reached():
        if not state_file.exists():
            return False
        state = json.loads(state_file.read_text())
        return (state.get("brevo_today", 0) >= BREVO_DAY_LIMIT and
                state.get("gmail_today",  0) >= GMAIL_DAY_LIMIT and
                state.get("a2_today",     0) >= A2_DAY_LIMIT)

    def pending_count():
        conn = sqlite3.connect(DB_PATH)
        n = conn.execute("SELECT COUNT(*) FROM contacts WHERE status='pending'").fetchone()[0]
        conn.close()
        return n

    try:
        lock_fd = open(lock_file, "w")
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("Sender already running (lockfile held). Skipping trigger.")
        return

    run = 0
    try:
        while not daily_limits_reached() and pending_count() > 0:
            run += 1
            cmd = [
                sys.executable, str(sender),
                "--limit", "9999",
                "--brevo-limit", "290",
                "--gmail-per-run", "1",
                "--a2-limit", "5",
                "--force",
            ]
            print(f"[run {run}] Triggering sender...")
            proc = subprocess.run(cmd)
            if proc.returncode != 0:
                print(f"[run {run}] sender exited {proc.returncode}, stopping loop")
                break
            time.sleep(5)
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        lock_fd.close()

    print(f"Auto-sender done after {run} run(s).")


if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else latest_csv()
    if not path or not path.exists():
        print("No CSV found"); raise SystemExit(1)
    print(f"Feeding: {path.name}")
    a, s = feed(path)
    print(f"Added: {a}  Skipped/dup: {s}")
    if a > 0:
        trigger_sender(a)
