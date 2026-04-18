#!/usr/bin/env python3
"""
Agent 5: Data Quality — Valideaza emailuri, detecteaza radiate, deduplica.
Ruleaza pe raspibig. Cron saptamanal.

Tabele verificate: master_romania_companies
Actiuni:
  1. Marcheaza emailuri invalide (regex)
  2. Detecteaza duplicate (exact email match)
  3. Detecteaza companii radiate (status)
  4. Raport Telegram + log

Folosire:
  python3 agent_data_quality.py [--dry-run] [--table master_romania_companies]
  python3 agent_data_quality.py --fix  # aplica corectii
"""
import argparse, json, logging, os, re, sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("data_quality")

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    log.error("pip install psycopg2-binary")
    sys.exit(1)

DB = {"host": "localhost", "dbname": "interjob_master", "user": "tudor", "password": "tudor"}

# Regex email valid — strict dar practic
EMAIL_RE = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
)

# Domenii invalide cunoscute (spam, placeholder, test)
BAD_DOMAINS = {
    "example.com", "test.com", "email.com", "mail.com", "domain.com",
    "asdf.com", "abc.com", "xxx.com", "noemail.com", "none.com",
    "na.com", "n-a.com", "nomail.com", "invalid.com",
}

TABLES = {
    "master_romania_companies": {
        "col_email": "email",
        "col_name": "name",
        "col_city": "city",
        "col_status": "status",
        "col_id": "id",
        "col_quality": "data_quality",
    },
}


def validate_emails(conn, table_cfg, table_name, dry_run=True):
    """Gaseste emailuri invalide sau suspecte."""
    col_email = table_cfg["col_email"]
    col_id = table_cfg["col_id"]

    sql = f"""
        SELECT {col_id}, {col_email}
        FROM {table_name}
        WHERE {col_email} IS NOT NULL AND length({col_email}) > 0
        LIMIT 100000
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        rows = cur.fetchall()

    invalid = []
    suspicious = []
    for row_id, email in rows:
        if not email or not email.strip():
            continue
        email = email.strip().lower()

        # Format invalid
        if not EMAIL_RE.match(email):
            invalid.append((row_id, email, "format_invalid"))
            continue

        # Domeniu suspect
        domain = email.split("@")[1] if "@" in email else ""
        if domain in BAD_DOMAINS:
            invalid.append((row_id, email, "domeniu_suspect"))
            continue

        # Email prea scurt (a@b.co)
        if len(email) < 6:
            suspicious.append((row_id, email, "prea_scurt"))

        # Contine spatii sau caractere ciudate dupa strip
        if " " in email or "\t" in email:
            invalid.append((row_id, email, "contine_spatii"))

    log.info(f"Emailuri verificate: {len(rows)}")
    log.info(f"  Invalide: {len(invalid)}")
    log.info(f"  Suspecte: {len(suspicious)}")

    if not dry_run and invalid:
        # Seteaza emailurile invalide pe NULL
        ids = [r[0] for r in invalid]
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE {table_name}
                SET {col_email} = NULL, data_quality = COALESCE(data_quality,'') || ',email_invalid'
                WHERE {col_id} = ANY(%s)
            """, (ids,))
        conn.commit()
        log.info(f"  Corectate: {len(ids)} emailuri setate NULL")

    return invalid, suspicious


def find_duplicates(conn, table_cfg, table_name):
    """Gaseste duplicate pe email exact."""
    col_email = table_cfg["col_email"]
    col_name = table_cfg["col_name"]
    col_id = table_cfg["col_id"]

    sql = f"""
        SELECT {col_email}, count(*) as cnt, array_agg({col_id} ORDER BY {col_id}) as ids
        FROM {table_name}
        WHERE {col_email} IS NOT NULL AND length({col_email}) > 3
        GROUP BY {col_email}
        HAVING count(*) > 1
        ORDER BY cnt DESC
        LIMIT 1000
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        dupes = cur.fetchall()

    total_dupes = sum(r[1] - 1 for r in dupes)  # -1 ca pastram unul
    log.info(f"Emailuri duplicate: {len(dupes)} grupuri, {total_dupes} intrari redundante")

    return dupes


def find_radiated(conn, table_cfg, table_name):
    """Gaseste companii radiate (status = RADIAT)."""
    col_status = table_cfg.get("col_status")
    col_email = table_cfg["col_email"]
    if not col_status:
        return []

    sql = f"""
        SELECT count(*)
        FROM {table_name}
        WHERE {col_status} = 'RADIAT'
        AND {col_email} IS NOT NULL AND length({col_email}) > 3
    """
    with conn.cursor() as cur:
        cur.execute(sql)
        count = cur.fetchone()[0]

    log.info(f"Companii radiate cu email: {count}")
    return count


def generate_report(invalid, suspicious, dupes, radiated, table_name):
    """Genereaza raport text."""
    lines = [
        f"=== DATA QUALITY REPORT — {table_name} ===",
        f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"Emailuri invalide: {len(invalid)}",
        f"Emailuri suspecte: {len(suspicious)}",
        f"Grupuri duplicate: {len(dupes)}",
        f"Intrari redundante: {sum(r[1]-1 for r in dupes) if dupes else 0}",
        f"Radiate cu email: {radiated}",
        "",
        "TOP 10 invalide:",
    ]
    for row_id, email, reason in invalid[:10]:
        lines.append(f"  {email} — {reason}")

    lines.append("")
    lines.append("TOP 10 duplicate (cele mai multe copii):")
    for email, cnt, ids in dupes[:10]:
        lines.append(f"  {email} — {cnt}x (ids: {ids[:5]}...)")

    return "\n".join(lines)


def send_telegram(text, max_len=4000):
    """Trimite raport pe Telegram daca configurat."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        return

    import requests
    text = text[:max_len]
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(description="Agent Data Quality")
    parser.add_argument("--table", default="master_romania_companies")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--fix", action="store_true", help="Aplica corectii")
    args = parser.parse_args()

    if args.fix:
        args.dry_run = False

    table_name = args.table
    if table_name not in TABLES:
        log.error(f"Tabela necunoscuta: {table_name}. Disponibile: {list(TABLES.keys())}")
        sys.exit(1)

    table_cfg = TABLES[table_name]
    log.info(f"Data Quality scan: {table_name} ({'DRY RUN' if args.dry_run else 'FIX MODE'})")

    conn = psycopg2.connect(**DB)

    invalid, suspicious = validate_emails(conn, table_cfg, table_name, dry_run=args.dry_run)
    dupes = find_duplicates(conn, table_cfg, table_name)
    radiated = find_radiated(conn, table_cfg, table_name)

    report = generate_report(invalid, suspicious, dupes, radiated, table_name)
    print(report)

    # Salveaza raport
    report_dir = "/opt/ACTIVE/INFRA/LOGS"
    os.makedirs(report_dir, exist_ok=True)
    report_file = f"{report_dir}/data_quality_{datetime.now().strftime('%Y%m%d')}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    log.info(f"Raport salvat: {report_file}")

    # Telegram doar daca sunt probleme
    if invalid or (dupes and len(dupes) > 100):
        send_telegram(f"🔍 Data Quality Alert\n{len(invalid)} invalid, {len(dupes)} duplicate groups\n{report_file}")

    conn.close()


if __name__ == "__main__":
    main()
