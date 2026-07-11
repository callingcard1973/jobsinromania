#!/usr/bin/env python3
"""Enrich producer/trader list with emails from master_emails and contacts.

Reads the unified CSV from extract_producers_by_caen.py, batch-queries
master_emails + contacts by CUI, appends best available email.

Usage:
  python GRAIN/enrich_producer_emails.py                        # dry-run stats
  python GRAIN/enrich_producer_emails.py --apply                # write enriched file
  python GRAIN/enrich_producer_emails.py --input <path> --output <path>
"""
import csv
import os
import sys
import time

try:
    import psycopg2
except ImportError:
    psycopg2 = None

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import config as CFG

BATCH_SIZE = 200  # CUI per batch query


def _conn():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not available")
    return psycopg2.connect(**CFG.DB)


def load_cuis(input_csv):
    """Load CUI from existing extract CSV. Returns list of (cui, row_dict)."""
    rows = []
    cuis = set()
    with open(input_csv, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            cui = (r.get("cui") or "").strip()
            if cui:
                cuis.add(cui)
            rows.append(r)
    return rows, cuis


def batch_query(conn, sql, cuis):
    """Run a query in batches of BATCH_SIZE, return {cui: value} dict."""
    result = {}
    cui_list = list(cuis)
    for i in range(0, len(cui_list), BATCH_SIZE):
        batch = cui_list[i:i + BATCH_SIZE]
        cur = conn.cursor()
        cur.execute(sql, (batch,))
        for row in cur.fetchall():
            result[row[0]] = row[1]
        cur.close()
        sys.stderr.write(".")
        sys.stderr.flush()
    return result


def batch_query_full(conn, sql, cuis):
    """Run a query in batches, return {cui: dict}."""
    result = {}
    cui_list = list(cuis)
    for i in range(0, len(cui_list), BATCH_SIZE):
        batch = cui_list[i:i + BATCH_SIZE]
        cur = conn.cursor()
        cur.execute(sql, (batch,))
        cols = [desc[0] for desc in cur.description]
        for row in cur.fetchall():
            result[row[0]] = dict(zip(cols, row))
        cur.close()
        sys.stderr.write(".")
        sys.stderr.flush()
    return result


def enrich(input_csv, output_path, dry=True):
    """Main enrichment: load CSV, query DB for emails, write enriched."""
    if not os.path.exists(input_csv):
        print("Input not found: %s" % input_csv, file=sys.stderr)
        return 1

    print("Loading %s ..." % input_csv, end=" ", flush=True)
    rows, cuis = load_cuis(input_csv)
    print("%d rows, %d unique CUI" % (len(rows), len(cuis)))
    if not cuis:
        print("No CUI found in input.")
        return 0

    conn = _conn()
    cur = conn.cursor()

    # Create temp table with target CUI for fast JOIN.
    cur.execute("CREATE TEMP TABLE _target_cuis (cui text)")
    sys.stderr.write("\n  Inserting %d CUI into temp table ... " % len(cuis))
    t0 = time.time()
    # Batch insert to avoid one huge VALUES.
    cui_list = list(cuis)
    for i in range(0, len(cui_list), 500):
        batch = cui_list[i:i+500]
        vals = ",".join("('%s')" % c.replace("'", "''") for c in batch)
        cur.execute("INSERT INTO _target_cuis VALUES " + vals)
    cur.execute("CREATE INDEX _tc_idx ON _target_cuis (cui)")
    conn.commit()
    sys.stderr.write("%.1fs\n" % (time.time() - t0))

    # Query master_emails via JOIN.
    print("Querying master_emails ...", end=" ", flush=True)
    t0 = time.time()
    emails_from_master = {}
    cur.execute(
        """SELECT DISTINCT ON (m.cui) m.cui, m.email
           FROM master_emails m
           JOIN _target_cuis t ON m.cui = t.cui
           WHERE m.email ~ '@' AND (m.is_bounced IS NULL OR m.is_bounced = false)
           ORDER BY m.cui, m.warmth_score DESC NULLS LAST""")
    for row in cur.fetchall():
        emails_from_master[row[0]] = row[1]
    print(" %d found in %.1fs" % (len(emails_from_master), time.time() - t0))

    # Query all enrichment data from master_emails.
    print("Querying enrichment data ...", end=" ", flush=True)
    t0 = time.time()
    enrich_data = {}
    cur.execute(
        """SELECT DISTINCT ON (m.cui) m.cui, m.email, m.phone, m.industry, m.domain,
                  m.is_bounced, m.is_catch_all, m.mx_valid, m.warmth_score
           FROM master_emails m
           JOIN _target_cuis t ON m.cui = t.cui
           WHERE m.email ~ '@'
           ORDER BY m.cui, m.warmth_score DESC NULLS LAST""")
    for row in cur.fetchall():
        enrich_data[row[0]] = {
            "email": row[1] or "",
            "phone": row[2] or "",
            "industry": row[3] or "",
            "domain": row[4] or "",
            "mx_valid": str(row[7] or ""),
            "warmth_score": str(row[8] or ""),
        }
    print(" %d enriched in %.1fs" % (len(enrich_data), time.time() - t0))

    # Cleanup temp table.
    try: cur.execute("DROP TABLE IF EXISTS _target_cuis")
    except: pass
    cur.close()
    conn.close()

    # Apply enrichment to rows.
    enriched_count = 0
    new_email_count = 0
    for r in rows:
        cui = (r.get("cui") or "").strip()
        existing = (r.get("email") or "").strip()

        # Best new email from master_emails or contacts.
        best_new = emails_from_master.get(cui) or ""
        r["email_master"] = best_new

        if best_new and not existing:
            new_email_count += 1
            r["email"] = best_new

        # Additional enrichment from master_emails.
        ed = enrich_data.get(cui, {})
        r["phone_master"] = ed.get("phone") or ""
        r["industry"] = ed.get("industry") or ""
        r["domain"] = ed.get("domain") or ""
        r["warmth_score"] = str(ed.get("warmth_score") or "")
        r["mx_valid"] = str(ed.get("mx_valid") or "")

        if best_new:
            enriched_count += 1

    if dry:
        has_email = sum(1 for r in rows if r.get("email") and "@" in r["email"])
        print("\n=== DRY-RUN ===")
        print("  Total rows: %d" % len(rows))
        print("  With email before: %d" % (has_email - new_email_count))
        print("  With email after:  %d" % has_email)
        print("  New emails found:  %d" % new_email_count)
        print("  Enriched rows:     %d" % enriched_count)
        print("  Use --apply to write %s" % output_path)
        return 0

    # Write enriched CSV.
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    cols = list(rows[0].keys()) if rows else []
    with open(output_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    has_email = sum(1 for r in rows if r.get("email") and "@" in r["email"])
    print("\n=== WROTE %s ===" % output_path)
    print("  Rows: %d | With email: %d | New: %d" % (len(rows), has_email, new_email_count))
    return 0


def main():
    default_in = os.path.join(CFG.DATA, "producers_by_caen_unified.csv")
    default_out = os.path.join(CFG.DATA, "producers_by_caen_enriched.csv")

    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    do_apply = "--apply" in sys.argv

    input_csv = os.environ.get("INPUT_CSV") or default_in
    output_csv = os.environ.get("OUTPUT_CSV") or default_out

    if "-i" in args:
        idx = args.index("-i") + 1
        if idx < len(args):
            input_csv = args[idx]
    if "-o" in args:
        idx = args.index("-o") + 1
        if idx < len(args):
            output_csv = args[idx]

    return enrich(input_csv, output_csv, dry=not do_apply)


if __name__ == "__main__":
    sys.exit(main())
