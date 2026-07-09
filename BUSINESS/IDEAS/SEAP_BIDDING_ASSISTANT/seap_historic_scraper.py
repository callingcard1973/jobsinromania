"""
SEAP Romania Historic Scraper — 2007-2018 data (istoric.e-licitatie.ro)
Same table: seap_ro_awards
Run: python seap_historic_scraper.py [--pages N] [--start-page N]
"""
import requests
import psycopg2
import time
import argparse

DB = dict(host="127.0.0.1", port=5433, dbname="interjob_master", user="tudor", password="tudor")
BASE_HIST = "http://istoric.e-licitatie.ro/api-pub"
HEADERS = {"Content-Type": "application/json",
           "Referer": "http://istoric.e-licitatie.ro/"}
PAGE_SIZE = 50
DELAY = 2
RETRY_MAX = 3

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS seap_ro_awards (
    notice_id       BIGINT PRIMARY KEY,
    notice_no       TEXT,
    notice_type     TEXT,
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
    if not raw:
        return None, None
    parts = raw.split(" - ", 1)
    if len(parts) == 2:
        return parts[0].strip(), parts[1].strip()
    return None, raw.strip()

def parse_cpv(raw):
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

def probe_historic_api():
    """Test which endpoints exist on the historic server."""
    candidates = [
        "/NoticeCommon/GetCANoticeList/",
        "/DirectAcquisitionCommon/GetDirectAcquisitionList/",
    ]
    working = []
    for path in candidates:
        url = BASE_HIST + path
        try:
            r = requests.post(url, json={"pageSize": 3, "pageIndex": 0},
                              headers=HEADERS, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, dict) and "items" in data:
                    total = data.get("total", 0)
                    print(f"  OK: {path} — total={total}")
                    working.append((path, total))
                else:
                    print(f"  {path} — unexpected: {str(data)[:100]}")
            else:
                print(f"  {path} — HTTP {r.status_code}")
        except Exception as e:
            print(f"  {path} — error: {e}")
    return working

def scrape_historic_can(conn, existing, start_page=0, max_pages=None):
    url = f"{BASE_HIST}/NoticeCommon/GetCANoticeList/"
    total_saved = 0
    notice_types = [3, 18, 1, 2]  # try multiple types for historic
    for ntype in notice_types:
        page = start_page
        consecutive_empty = 0
        while True:
            if max_pages and (page - start_page) >= max_pages:
                break
            payload = {"pageSize": PAGE_SIZE, "pageIndex": page,
                       "noticeStateCode": 0, "sysNoticeTypeId": ntype}
            data = post(url, payload)
            if not data or "items" not in data:
                break
            items = data["items"]
            if not items:
                consecutive_empty += 1
                if consecutive_empty >= 3:
                    break
                page += 1
                continue
            consecutive_empty = 0
            rows = []
            for item in items:
                nid = item.get("caNoticeId") or item.get("noticeId")
                if not nid or nid in existing:
                    continue
                buyer_cui, buyer_name = parse_buyer(item.get("contractingAuthorityNameAndFN"))
                cpv_code, cpv_name = parse_cpv(item.get("cpvCodeAndName"))
                proc = (item.get("sysProcedureType") or {}).get("text")
                rows.append((
                    nid,
                    item.get("noticeNo"),
                    "CAN_HIST",
                    item.get("contractTitle"),
                    buyer_name, buyer_cui,
                    None, None,
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
            if total_saved > 0 and total_saved % 100 == 0:
                print(f"  [HIST CAN type={ntype}] page={page} saved={total_saved}")
            page += 1
            time.sleep(DELAY)
            total = data.get("total", 0)
            if page * PAGE_SIZE >= total:
                break
    print(f"Historic CAN done. Total saved: {total_saved}")
    return total_saved

def scrape_historic_da(conn, existing, start_page=0, max_pages=None):
    url = f"{BASE_HIST}/DirectAcquisitionCommon/GetDirectAcquisitionList/"
    total_saved = 0
    page = start_page
    while True:
        if max_pages and (page - start_page) >= max_pages:
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
            if not nid or nid in existing:
                continue
            buyer_cui, buyer_name = parse_buyer(item.get("contractingAuthority"))
            winner_cui, winner_name = parse_buyer(item.get("supplier"))
            cpv_code, cpv_name = parse_cpv(item.get("cpvCode"))
            rows.append((
                nid,
                item.get("uniqueIdentificationCode"),
                "DA_HIST",
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
        if total_saved > 0 and total_saved % 100 == 0:
            print(f"  [HIST DA] page={page} saved={total_saved}")
        page += 1
        time.sleep(DELAY)
        total = data.get("total", 0)
        if page * PAGE_SIZE >= total:
            break
    print(f"Historic DA done. Total saved: {total_saved}")
    return total_saved

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pages", type=int, default=None, help="Max pages per type (for testing)")
    ap.add_argument("--start-page", type=int, default=0)
    ap.add_argument("--probe", action="store_true", help="Just probe endpoints")
    args = ap.parse_args()

    if args.probe:
        print("Probing historic.e-licitatie.ro endpoints...")
        probe_historic_api()
        return

    print("Connecting to PostgreSQL...")
    conn = get_conn()
    ensure_table(conn)
    existing = get_existing_ids(conn)
    print(f"Existing rows: {len(existing)}")

    print("Scraping historic CAN notices (2007-2018)...")
    scrape_historic_can(conn, existing, args.start_page, args.pages)

    print("Scraping historic Direct Acquisitions...")
    scrape_historic_da(conn, existing, args.start_page, args.pages)

    conn.close()
    print("Done.")

if __name__ == "__main__":
    main()
