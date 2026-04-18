"""
SEAP Romania Scraper — current data (e-licitatie.ro)
Scrapes: CAN notices (type 3) + Direct Acquisitions (separate API)
Table: seap_ro_awards
Run: python seap_scraper.py [--type can|da|all] [--pages N]
"""
import requests
import psycopg2
import time
import argparse
import sys
from datetime import datetime, timezone

# --- Config ---
DB = dict(host="127.0.0.1", port=5433, dbname="interjob_master", user="tudor", password="tudor")
BASE = "http://e-licitatie.ro/api-pub"
HEADERS = {"Content-Type": "application/json", "Referer": "http://e-licitatie.ro/"}
PAGE_SIZE = 50
DELAY = 2          # seconds between pages
RETRY_MAX = 3

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS seap_ro_awards (
    notice_id       BIGINT PRIMARY KEY,
    notice_no       TEXT,
    notice_type     TEXT,        -- 'CAN' or 'DA'
    title           TEXT,
    buyer_name      TEXT,
    buyer_cui       TEXT,
    winner_name     TEXT,
    winner_cui      TEXT,
    value_ron       NUMERIC(18,2),
    cpv_code        TEXT,
    cpv_name        TEXT,
    publish_date    TIMESTAMPTZ,
    contract_date   TIMESTAMPTZ,
    procedure_type  TEXT,
    scraped_at      TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_seap_cpv  ON seap_ro_awards(cpv_code);
CREATE INDEX IF NOT EXISTS idx_seap_date ON seap_ro_awards(publish_date);
"""

def get_conn():
    return psycopg2.connect(**DB)

def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute(CREATE_SQL)
    conn.commit()

def get_existing_ids(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT notice_id FROM seap_ro_awards")
        return {r[0] for r in cur.fetchall()}

def post(url, payload, attempt=0):
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=30)
        if r.status_code == 429:
            print("  429 rate-limit, sleeping 60s...")
            time.sleep(60)
            return post(url, payload, attempt)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        if attempt < RETRY_MAX:
            print(f"  Error: {e} — retry {attempt+1}/{RETRY_MAX}")
            time.sleep(5 * (attempt + 1))
            return post(url, payload, attempt + 1)
        print(f"  Failed after {RETRY_MAX} retries: {e}")
        return None

def parse_buyer(raw):
    """'2843299 - Spitalul Orasenesc Sinaia' -> (cui, name)"""
    if not raw:
        return None, None
    parts = raw.split(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, raw.strip()

def parse_cpv(raw):
    """'09123000-7 - Gaze naturale (Rev.2)' -> (code, name)"""
    if not raw:
        return None, None
    parts = raw.split(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return raw.strip(), None

def upsert_rows(conn, rows):
    sql = """
    INSERT INTO seap_ro_awards
      (notice_id, notice_no, notice_type, title, buyer_name, buyer_cui,
       winner_name, winner_cui, value_ron, cpv_code, cpv_name,
       publish_date, contract_date, procedure_type, scraped_at)
    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,NOW())
    ON CONFLICT (notice_id) DO NOTHING
    """
    with conn.cursor() as cur:
        cur.executemany(sql, rows)
    conn.commit()

def scrape_can(conn, existing, max_pages=None):
    """Scrape Contract Award Notices (sysNoticeTypeId varies, atribuita state)."""
    url = f"{BASE}/NoticeCommon/GetCANoticeList/"
    total_saved = 0
    page = 0
    # Notice types that are award notices: 3=CAN, 18=SCNA, others
    notice_types = [3, 18]
    for ntype in notice_types:
        page = 0
        while True:
            if max_pages and page >= max_pages:
                break
            payload = {"pageSize": PAGE_SIZE, "pageIndex": page,
                       "noticeStateCode": 0, "sysNoticeTypeId": ntype}
            data = post(url, payload)
            if not data or "items" not in data:
                break
            items = data["items"]
            if not items:
                break
            rows = []
            for item in items:
                nid = item.get("caNoticeId") or item.get("noticeId")
                if nid in existing:
                    continue
                buyer_cui, buyer_name = parse_buyer(item.get("contractingAuthorityNameAndFN"))
                cpv_code, cpv_name = parse_cpv(item.get("cpvCodeAndName"))
                proc = (item.get("sysProcedureType") or {}).get("text")
                rows.append((
                    nid,
                    item.get("noticeNo"),
                    "CAN",
                    item.get("contractTitle"),
                    buyer_name, buyer_cui,
                    None, None,   # winner not in list API
                    item.get("ronContractValue"),
                    cpv_code, cpv_name,
                    item.get("noticeStateDate"),
                    None,
                    proc,
                ))
                existing.add(nid)
            if rows:
                upsert_rows(conn, rows)
                total_saved += len(rows)
            if total_saved % 100 < len(rows):
                print(f"  [CAN type={ntype}] page={page} saved={total_saved}")
            page += 1
            time.sleep(DELAY)
            total = data.get("total", 0)
            if page * PAGE_SIZE >= total:
                break
    print(f"CAN scrape done. Total saved: {total_saved}")
    return total_saved

def scrape_da(conn, existing, max_pages=None):
    """Scrape Direct Acquisitions — has both buyer and winner in list API."""
    url = f"{BASE}/DirectAcquisitionCommon/GetDirectAcquisitionList/"
    total_saved = 0
    page = 0
    while True:
        if max_pages and page >= max_pages:
            break
        payload = {"pageSize": PAGE_SIZE, "pageIndex": page}
        data = post(url, payload)
        if not data or "items" not in data:
            break
        items = data["items"]
        if not items:
            break
        rows = []
        for item in items:
            nid = item.get("directAcquisitionId")
            if nid in existing:
                continue
            buyer_cui, buyer_name = parse_buyer(item.get("contractingAuthority"))
            winner_cui, winner_name = parse_buyer(item.get("supplier"))
            cpv_code, cpv_name = parse_cpv(item.get("cpvCode"))
            rows.append((
                nid,
                item.get("uniqueIdentificationCode"),
                "DA",
                item.get("directAcquisitionName"),
                buyer_name, buyer_cui,
                winner_name, winner_cui,
                item.get("closingValue") or item.get("estimatedValueRon"),
                cpv_code, cpv_name,
                item.get("publicationDate"),
                item.get("finalizationDate"),
                "Achizitie directa",
            ))
            existing.add(nid)
        if rows:
            upsert_rows(conn, rows)
            total_saved += len(rows)
        if total_saved % 100 < len(rows) or page == 0:
            print(f"  [DA] page={page} saved={total_saved}")
        page += 1
        time.sleep(DELAY)
        total = data.get("total", 0)
        if page * PAGE_SIZE >= total:
            break
    print(f"DA scrape done. Total saved: {total_saved}")
    return total_saved

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--type", choices=["can", "da", "all"], default="all")
    ap.add_argument("--pages", type=int, default=None, help="Max pages per notice type (for testing)")
    args = ap.parse_args()

    print(f"Connecting to PostgreSQL...")
    conn = get_conn()
    ensure_table(conn)
    existing = get_existing_ids(conn)
    print(f"Existing rows: {len(existing)}")

    if args.type in ("can", "all"):
        print("Scraping CAN notices...")
        scrape_can(conn, existing, args.pages)
    if args.type in ("da", "all"):
        print("Scraping Direct Acquisitions...")
        scrape_da(conn, existing, args.pages)

    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
