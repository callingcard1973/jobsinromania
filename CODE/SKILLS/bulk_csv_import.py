#!/usr/bin/env python3
"""Bulk CSV Importer - Import CSVs into PostgreSQL, verify, delete source."""
import os, sys, csv, hashlib, argparse, logging
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values

DB_CONFIG = {'dbname': 'csv_raw', 'user': 'tudor'}  # Unix socket (peer auth)
DB_TABLESPACE = 'hdd_storage'  # Store on HDD, not NVMe (NVMe for hot data only)
DEFAULT_DIRS = ['/home/tudor/SCRAPER_DATA', '/opt/DATA/incoming', '/tmp/csv_import']
LOG_DIR = '/opt/LOGS/csv_import'
ARCHIVE_DIR = '/opt/DATA/csv_archive'
BATCH_SIZE = 5000  # Rows per batch insert
SPLIT_THRESHOLD = 100000  # Split files larger than this

os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(f"{LOG_DIR}/import_{datetime.now():%Y%m%d}.log"), logging.StreamHandler()])
log = logging.getLogger(__name__)

def ensure_db_on_hdd():
    """Ensure csv_raw database exists on HDD tablespace."""
    try:
        # Connect to postgres to check/create database
        conn = psycopg2.connect(dbname='postgres', user='tudor')
        conn.autocommit = True
        cur = conn.cursor()

        # Check if database exists
        cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (DB_CONFIG['dbname'],))
        if not cur.fetchone():
            # Create database on HDD tablespace
            cur.execute(f"CREATE DATABASE {DB_CONFIG['dbname']} TABLESPACE {DB_TABLESPACE}")
            log.info(f"Created database {DB_CONFIG['dbname']} on {DB_TABLESPACE}")
        else:
            # Check current tablespace
            cur.execute("""
                SELECT t.spcname FROM pg_database d
                JOIN pg_tablespace t ON d.dattablespace = t.oid
                WHERE d.datname = %s
            """, (DB_CONFIG['dbname'],))
            current_ts = cur.fetchone()[0]
            if current_ts != DB_TABLESPACE:
                log.warning(f"Database {DB_CONFIG['dbname']} is on {current_ts}, should be on {DB_TABLESPACE}")

        cur.close()
        conn.close()
    except Exception as e:
        log.warning(f"Could not verify DB tablespace: {e}")

def get_conn():
    ensure_db_on_hdd()
    try: return psycopg2.connect(**DB_CONFIG)
    except Exception as e: log.error(f"DB error: {e}"); return None

def table_name(path, suffix=''):
    name = os.path.splitext(os.path.basename(path))[0]
    clean = ''.join(c if c.isalnum() else '_' for c in name.lower())[:40]
    h = hashlib.md5((path + suffix).encode()).hexdigest()[:8]
    return f"{clean}_{datetime.now():%Y%m%d}_{h}"

def count_rows(path):
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            r = csv.reader(f); h = next(r, None)
            return (sum(1 for _ in r), h, None) if h else (0, None, "Empty")
    except Exception as e: return (0, None, str(e))

def sanitize_col(n):
    c = ''.join(x if x.isalnum() else '_' for x in n.lower().strip())
    return ('col_' + c) if c and c[0].isdigit() else (c or 'unnamed')

def split_csv(path, chunk_size=SPLIT_THRESHOLD):
    """Split large CSV into smaller chunks. Returns list of chunk paths."""
    rows, header, err = count_rows(path)
    if err or rows <= chunk_size: return [path]

    chunks = []
    base = os.path.splitext(path)[0]
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        reader = csv.reader(f); hdr = next(reader)
        chunk_num, chunk_rows = 0, []
        for row in reader:
            chunk_rows.append(row)
            if len(chunk_rows) >= chunk_size:
                chunk_path = f"{base}_chunk{chunk_num}.csv"
                with open(chunk_path, 'w', newline='', encoding='utf-8') as cf:
                    w = csv.writer(cf); w.writerow(hdr); w.writerows(chunk_rows)
                chunks.append(chunk_path); chunk_rows = []; chunk_num += 1
        if chunk_rows:  # Remaining rows
            chunk_path = f"{base}_chunk{chunk_num}.csv"
            with open(chunk_path, 'w', newline='', encoding='utf-8') as cf:
                w = csv.writer(cf); w.writerow(hdr); w.writerows(chunk_rows)
            chunks.append(chunk_path)
    log.info(f"Split {path} into {len(chunks)} chunks")
    return chunks

def import_csv(path, tbl, conn):
    rows, header, err = count_rows(path)
    if err: return False, 0, err
    if rows == 0: return False, 0, "No data"

    cols = [sanitize_col(c) for c in header]
    seen = {}
    for i, c in enumerate(cols):
        if c in seen: seen[c] += 1; cols[i] = f"{c}_{seen[c]}"
        else: seen[c] = 0

    cur = conn.cursor()
    col_defs = ', '.join([f'"{c}" TEXT' for c in cols])
    cur.execute(f'CREATE TABLE IF NOT EXISTS "{tbl}" ({col_defs}, _imported_at TIMESTAMP DEFAULT NOW(), _source TEXT)')

    imported, skipped, batch = 0, 0, []
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        r = csv.reader(f); next(r)
        for row in r:
            try:
                if len(row) < len(cols): row += [''] * (len(cols) - len(row))
                elif len(row) > len(cols): row = row[:len(cols)]
                row.append(path)
                batch.append(tuple(row))
                if len(batch) >= BATCH_SIZE:
                    cn = ','.join([f'"{c}"' for c in cols] + ['_source'])
                    execute_values(cur, f'INSERT INTO "{tbl}" ({cn}) VALUES %s', batch)
                    imported += len(batch); batch = []
            except: skipped += 1
        if batch:
            cn = ','.join([f'"{c}"' for c in cols] + ['_source'])
            execute_values(cur, f'INSERT INTO "{tbl}" ({cn}) VALUES %s', batch)
            imported += len(batch)
    conn.commit(); cur.close()
    return True, imported, f"OK: {imported}, skip: {skipped}"

def verify(tbl, expected, conn):
    try:
        cur = conn.cursor()
        cur.execute(f'SELECT COUNT(*) FROM "{tbl}"'); actual = cur.fetchone()[0]; cur.close()
        return actual >= expected * 0.99, actual
    except: return False, 0

def find_csvs(dirs):
    files = []
    for d in dirs:
        if not os.path.isdir(d): continue
        for root, _, fs in os.walk(d):
            files.extend(os.path.join(root, f) for f in fs if f.lower().endswith('.csv'))
    return files

def process_csv(path, conn, dry=False, archive=False, split=False):
    res = {'file': path, 'table': None, 'rows': 0, 'ok': False, 'err': None, 'del': False}
    if not os.path.exists(path): res['err'] = "Not found"; return res

    rows, _, err = count_rows(path)
    if err: res['err'] = err; return res
    res['rows'] = rows

    # Split large files if requested
    if split and rows > SPLIT_THRESHOLD:
        chunks = split_csv(path)
        total_imported = 0
        for chunk in chunks:
            tbl = table_name(chunk)
            ok, n, msg = import_csv(chunk, tbl, conn)
            if ok: total_imported += n
            if chunk != path: os.remove(chunk)  # Remove chunk files
        res['ok'] = True; res['rows'] = total_imported; res['table'] = f"{len(chunks)} chunks"
    else:
        tbl = table_name(path); res['table'] = tbl
        if dry: res['ok'] = True; res['err'] = "DRY RUN"; return res
        ok, n, msg = import_csv(path, tbl, conn)
        if not ok: res['err'] = msg; return res
        verified, actual = verify(tbl, rows, conn)
        if not verified: res['err'] = f"Verify fail: {rows} vs {actual}"; return res
        res['ok'] = True; res['rows'] = actual

    try:
        if archive:
            os.makedirs(ARCHIVE_DIR, exist_ok=True)
            os.rename(path, os.path.join(ARCHIVE_DIR, os.path.basename(path)))
        else: os.remove(path)
        res['del'] = True
    except Exception as e: res['err'] = f"Import OK, delete fail: {e}"
    return res

def status(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public'")
    tc = cur.fetchone()[0]
    cur.execute("SELECT COALESCE(SUM(n_live_tup),0) FROM pg_stat_user_tables")
    tr = cur.fetchone()[0]
    cur.execute("""SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))), n_live_tup
        FROM information_schema.tables t JOIN pg_stat_user_tables s ON t.table_name=s.relname
        WHERE t.table_schema='public' ORDER BY n_live_tup DESC LIMIT 10""")
    recent = cur.fetchall(); cur.close()
    print(f"\n=== CSV Raw DB ===\nTables: {tc}\nRows: {tr:,}\n\nTop tables by size:")
    for n, sz, r in recent: print(f"  {n[:45]:45} {sz:>8} {r:>10,}")

def list_tables(conn):
    cur = conn.cursor()
    cur.execute("""SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name)))
        FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name""")
    for n, sz in cur.fetchall(): print(f"  {n[:55]:55} {sz}")
    cur.close()

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--status', action='store_true')
    p.add_argument('--list-tables', action='store_true')
    p.add_argument('--dir', type=str)
    p.add_argument('--file', type=str)
    p.add_argument('--archive', action='store_true')
    p.add_argument('--split', action='store_true', help='Split large CSVs (>100K rows)')
    a = p.parse_args()

    conn = get_conn()
    if not conn: sys.exit(1)

    try:
        if a.status: status(conn); return
        if a.list_tables: list_tables(conn); return

        files = [a.file] if a.file and os.path.exists(a.file) else find_csvs([a.dir] if a.dir else DEFAULT_DIRS)
        if not files: log.info("No CSVs found"); return

        log.info(f"Found {len(files)} CSVs")
        ok, fail, dele = 0, 0, 0
        for f in files:
            log.info(f"Processing: {f}")
            r = process_csv(f, conn, a.dry_run, a.archive, a.split)
            if r['ok']: ok += 1; dele += r['del']; log.info(f"  -> {r['table']} ({r['rows']:,} rows)")
            else: fail += 1; log.error(f"  -> FAIL: {r['err']}")

        log.info(f"\n=== Summary ===\nImported: {ok}\nFailed: {fail}\nDeleted: {dele}")
    finally: conn.close()

if __name__ == '__main__': main()
