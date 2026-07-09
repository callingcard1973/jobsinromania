"""
SEAP DB Quick Check
Usage: python seap_check.py [--cpv PREFIX] [--buyer KEYWORD]
"""
import psycopg2
import argparse

DB = dict(host="127.0.0.1", port=5433, dbname="interjob_master", user="tudor", password="tudor")

def get_conn():
    return psycopg2.connect(**DB)

def table_exists(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'seap_ro_awards'
            )
        """)
        return cur.fetchone()[0]

def run_check(args):
    conn = get_conn()
    if not table_exists(conn):
        print("Table seap_ro_awards does not exist yet. Run seap_scraper.py first.")
        conn.close()
        return

    with conn.cursor() as cur:
        # Row counts
        cur.execute("SELECT COUNT(*), notice_type FROM seap_ro_awards GROUP BY notice_type ORDER BY COUNT(*) DESC")
        rows = cur.fetchall()
        print("=== Row counts by type ===")
        total = 0
        for cnt, ntype in rows:
            print(f"  {ntype or 'NULL':12s}: {cnt:>10,}")
            total += cnt
        print(f"  {'TOTAL':12s}: {total:>10,}")

        # Date range
        cur.execute("""
            SELECT
                MIN(publish_date)::date AS oldest,
                MAX(publish_date)::date AS newest,
                MIN(scraped_at)::date   AS first_scraped,
                MAX(scraped_at)::date   AS last_scraped
            FROM seap_ro_awards
        """)
        row = cur.fetchone()
        print("\n=== Date range ===")
        print(f"  Publish range : {row[0]} to {row[1]}")
        print(f"  Scraped range : {row[2]} to {row[3]}")

        # Top CPV codes by total value
        print("\n=== Top 10 CPV codes by total value (RON) ===")
        cur.execute("""
            SELECT cpv_code, cpv_name, COUNT(*) AS n,
                   ROUND(SUM(value_ron)/1e6, 2) AS total_m_ron
            FROM seap_ro_awards
            WHERE cpv_code IS NOT NULL AND value_ron IS NOT NULL
            GROUP BY cpv_code, cpv_name
            ORDER BY SUM(value_ron) DESC
            LIMIT 10
        """)
        print(f"  {'CPV':15s} {'Count':>8} {'M RON':>12}  Name")
        for cpv, name, n, m in cur.fetchall():
            nm = (name or "")[:50]
            print(f"  {cpv or '':15s} {n:>8,} {m:>12.2f}  {nm}")

        # Top buyers
        print("\n=== Top 10 buyers by contract count ===")
        cur.execute("""
            SELECT buyer_name, buyer_cui, COUNT(*) AS n,
                   ROUND(SUM(value_ron)/1e6, 2) AS total_m_ron
            FROM seap_ro_awards
            WHERE buyer_name IS NOT NULL
            GROUP BY buyer_name, buyer_cui
            ORDER BY COUNT(*) DESC
            LIMIT 10
        """)
        print(f"  {'Buyer':40s} {'CUI':12} {'Count':>8} {'M RON':>10}")
        for name, cui, n, m in cur.fetchall():
            nm = (name or "")[:40]
            print(f"  {nm:40s} {cui or '':12} {n:>8,} {m or 0:>10.2f}")

        # DA winners (only DA type has winner data)
        print("\n=== Top 10 DA winners by value ===")
        cur.execute("""
            SELECT winner_name, winner_cui, COUNT(*) AS n,
                   ROUND(SUM(value_ron)/1e6, 2) AS total_m_ron
            FROM seap_ro_awards
            WHERE winner_name IS NOT NULL AND notice_type LIKE 'DA%'
            GROUP BY winner_name, winner_cui
            ORDER BY SUM(value_ron) DESC
            LIMIT 10
        """)
        print(f"  {'Winner':40s} {'CUI':12} {'Count':>8} {'M RON':>10}")
        for name, cui, n, m in cur.fetchall():
            nm = (name or "")[:40]
            print(f"  {nm:40s} {cui or '':12} {n:>8,} {m or 0:>10.2f}")

        # Optional: filter by CPV prefix
        if args.cpv:
            print(f"\n=== Notices with CPV starting '{args.cpv}' ===")
            cur.execute("""
                SELECT notice_id, notice_no, title, buyer_name, value_ron, publish_date::date
                FROM seap_ro_awards
                WHERE cpv_code LIKE %s
                ORDER BY value_ron DESC NULLS LAST
                LIMIT 20
            """, (args.cpv + "%",))
            for row in cur.fetchall():
                print(f"  {row[1] or '':15s} {str(row[5] or ''):12s} {(row[4] or 0):>12,.0f} RON  {(row[2] or '')[:50]}")

        # Optional: filter by buyer keyword
        if args.buyer:
            print(f"\n=== Notices from buyer matching '{args.buyer}' ===")
            cur.execute("""
                SELECT notice_id, notice_no, title, buyer_name, value_ron, publish_date::date
                FROM seap_ro_awards
                WHERE buyer_name ILIKE %s
                ORDER BY value_ron DESC NULLS LAST
                LIMIT 20
            """, ("%" + args.buyer + "%",))
            for row in cur.fetchall():
                print(f"  {row[1] or '':15s} {str(row[5] or ''):12s} {(row[4] or 0):>12,.0f} RON  {(row[3] or '')[:40]}")

    conn.close()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpv", default=None, help="CPV prefix filter e.g. 45 or 71")
    ap.add_argument("--buyer", default=None, help="Buyer name keyword")
    args = ap.parse_args()
    run_check(args)

if __name__ == "__main__":
    main()
