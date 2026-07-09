#!/usr/bin/env python3
"""SEAP food procurement alerts for cooperative members.

Queries tenders table for Romanian food contracts (CPV 15*, 03*),
cross-matches winners with food_distribution contacts,
identifies procurement opportunities.

Usage:
    python seap_food_alerts.py                    # Full report
    python seap_food_alerts.py --buyers           # List food buyers (authorities)
    python seap_food_alerts.py --winners          # List food winners (suppliers)
    python seap_food_alerts.py --overlap          # Cross-match with food_distribution
    python seap_food_alerts.py --export out.csv   # Export all food tenders
"""

import csv
import io
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

try:
    import psycopg2
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

from shared_utils import DB_MASTER, DB_FOOD
from seap_cross_match import cross_match, export_tenders

# -- CPV food codes
FOOD_CPV = [
    ("15%", "Food products"),
    ("03%", "Agricultural products"),
]

# -- Subcategories for detailed breakdown
CPV_SUBCATS = {
    "151": "meat", "152": "fish", "153": "fruit-veg",
    "154": "oils-fats", "155": "dairy", "156": "grain-starch",
    "157": "animal-feed", "158": "misc-food", "159": "beverages",
    "031": "crops", "032": "cereals-veg", "033": "fruit-nuts",
}


def cpv_subcat(cpv):
    if not cpv:
        return "other"
    code = str(cpv).replace(" ", "")[:3]
    return CPV_SUBCATS.get(code, "other")


def safe_query(conn, sql, params=None):
    cur = conn.cursor()
    cur.execute(sql, params or ())
    return cur.fetchall(), [d[0] for d in cur.description]


def report_food_tenders(conn):
    """Summary of Romanian food tenders."""
    print("=" * 60)
    print("SEAP FOOD TENDERS -- Romania")
    print("=" * 60)

    # -- Overall stats
    rows, _ = safe_query(conn, """
        SELECT
            COUNT(*) AS total,
            COUNT(DISTINCT winner_name) AS winners,
            COUNT(DISTINCT buyer_name) AS buyers,
            SUM(value) AS total_value,
            MIN(date_published) AS earliest,
            MAX(date_published) AS latest
        FROM tenders
        WHERE country = 'RO'
        AND (cpv_code LIKE '15%%' OR cpv_code LIKE '03%%')
    """)
    r = rows[0]
    print(f"\nTotal food tenders: {r[0]:,}")
    print(f"Unique winners: {r[1]:,}")
    print(f"Unique buyers: {r[2]:,}")
    print(f"Total value: {r[3]:,.0f}" if r[3] else "Total value: N/A")
    print(f"Period: {r[4]} to {r[5]}")

    # -- By CPV subcategory
    rows, _ = safe_query(conn, """
        SELECT LEFT(cpv_code, 3) AS cpv3,
               COUNT(*) AS cnt,
               COUNT(DISTINCT winner_name) AS winners,
               SUM(value) AS val
        FROM tenders
        WHERE country = 'RO'
        AND (cpv_code LIKE '15%%' OR cpv_code LIKE '03%%')
        GROUP BY cpv3 ORDER BY cnt DESC
    """)
    print(f"\nBy CPV subcategory:")
    for cpv3, cnt, winners, val in rows:
        label = CPV_SUBCATS.get(cpv3, cpv3)
        val_str = f"{val:,.0f} RON" if val else "N/A"
        print(f"  {cpv3} ({label}): {cnt:,} tenders, {winners} winners, {val_str}")


def list_buyers(conn, limit=30):
    """Top food procurement buyers (public authorities)."""
    print(f"\n{'=' * 60}")
    print("TOP FOOD BUYERS (Public Authorities)")
    print("=" * 60)

    rows, _ = safe_query(conn, """
        SELECT buyer_name, COUNT(*) AS cnt,
               SUM(value) AS total_val,
               MAX(date_published) AS last_tender
        FROM tenders
        WHERE country = 'RO'
        AND (cpv_code LIKE '15%%' OR cpv_code LIKE '03%%')
        AND buyer_name IS NOT NULL
        GROUP BY buyer_name
        ORDER BY cnt DESC
        LIMIT %s
    """, (limit,))

    for name, cnt, val, last in rows:
        val_str = f"{val:,.0f}" if val else "N/A"
        print(f"  {name[:50]:50s} | {cnt:4d} tenders | {val_str:>15s} RON | last: {last}")


def list_winners(conn, limit=30):
    """Top food tender winners (suppliers)."""
    print(f"\n{'=' * 60}")
    print("TOP FOOD WINNERS (Suppliers)")
    print("=" * 60)

    rows, _ = safe_query(conn, """
        SELECT winner_name, COUNT(*) AS cnt,
               SUM(value) AS total_val,
               MAX(date_published) AS last_win
        FROM tenders
        WHERE country = 'RO'
        AND (cpv_code LIKE '15%%' OR cpv_code LIKE '03%%')
        AND winner_name IS NOT NULL AND winner_name != ''
        GROUP BY winner_name
        ORDER BY cnt DESC
        LIMIT %s
    """, (limit,))

    for name, cnt, val, last in rows:
        val_str = f"{val:,.0f}" if val else "N/A"
        print(f"  {name[:50]:50s} | {cnt:4d} wins | {val_str:>15s} RON | last: {last}")


def main():
    args = sys.argv[1:]

    conn_master = psycopg2.connect(**DB_MASTER)

    if "--export" in args:
        idx = args.index("--export")
        output = args[idx + 1] if idx + 1 < len(args) else "seap_food_tenders.csv"
        export_tenders(conn_master, output)
        conn_master.close()
        return

    if "--buyers" in args:
        list_buyers(conn_master)
        conn_master.close()
        return

    if "--winners" in args:
        list_winners(conn_master)
        conn_master.close()
        return

    if "--overlap" in args:
        conn_food = psycopg2.connect(**DB_FOOD)
        cross_match(conn_master, conn_food)
        conn_food.close()
        conn_master.close()
        return

    # Full report
    report_food_tenders(conn_master)
    list_buyers(conn_master)
    list_winners(conn_master)

    conn_food = psycopg2.connect(**DB_FOOD)
    cross_match(conn_master, conn_food)
    conn_food.close()
    conn_master.close()


if __name__ == "__main__":
    main()
