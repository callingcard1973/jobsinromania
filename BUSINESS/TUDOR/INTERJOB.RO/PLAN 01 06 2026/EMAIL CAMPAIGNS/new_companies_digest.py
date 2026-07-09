#!/usr/bin/env python3
"""Weekly 'new Romanian companies' digest from the romania.companies table.

Surfaces companies first inserted in the last N days (created_at), grouped by
county, as a CSV + HTML digest. Foundation for SEO county pages, a lead-gen
feed, and a paid data subscription. Source is populated nightly by
romania_nightly.py (STEP 6 detect_new_companies + other enrichment steps).
"""
import csv
import os
from datetime import datetime

import psycopg2

DB = dict(host="127.0.0.1", port=5432, user="tudor", dbname="romania")
DAYS = int(os.environ.get("DIGEST_DAYS", "45"))
# founding_date = real "newly founded" business signal (ONRC monthly dump).
# Fall back to created_at (DB insert) only if explicitly requested.
DATE_COL = os.environ.get("DIGEST_DATE_COL", "founding_date")
OUT_DIR = "/opt/ACTIVE/EMAIL/CAMPAIGNS/NEW_COMPANIES"


def fetch():
    sql = f"""
        SELECT cui, company_name, county, city, email, phone, website,
               sector, {DATE_COL}::date
        FROM companies
        WHERE {DATE_COL} >= now() - interval '{DAYS} days'
        ORDER BY {DATE_COL} DESC, county
    """
    with psycopg2.connect(**DB) as conn, conn.cursor() as cur:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return cols, cur.fetchall()


def write_csv(path, cols, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        w.writerows(rows)


def write_html(path, rows, by_county):
    today = datetime.now().strftime("%Y-%m-%d")
    parts = [
        "<!doctype html><meta charset=utf-8>",
        f"<title>Firme noi RO — {today}</title>",
        "<style>body{font:14px system-ui;margin:2rem;max-width:60rem}"
        "table{border-collapse:collapse;width:100%}td,th{border:1px solid #ddd;"
        "padding:4px 8px;text-align:left}th{background:#f4f4f4}</style>",
        f"<h1>Firme noi în România — ultimele {DAYS} zile</h1>",
        f"<p>Generat {today} · {len(rows)} firme noi.</p>",
        "<h2>Pe județe</h2><table><tr><th>Județ</th><th>Firme noi</th></tr>",
    ]
    for county, n in by_county:
        parts.append(f"<tr><td>{county or '?'}</td><td>{n}</td></tr>")
    parts.append("</table>")
    if rows:
        parts.append("<h2>Detaliu</h2><table><tr><th>CUI</th><th>Nume</th>"
                     "<th>Județ</th><th>Oraș</th><th>Email</th><th>Telefon</th></tr>")
        for r in rows[:500]:
            parts.append(
                f"<tr><td>{r[0]}</td><td>{r[1] or ''}</td><td>{r[2] or ''}</td>"
                f"<td>{r[3] or ''}</td><td>{r[4] or ''}</td><td>{r[5] or ''}</td></tr>")
        parts.append("</table>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(parts))


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    cols, rows = fetch()
    by_county = {}
    for r in rows:
        by_county[r[2]] = by_county.get(r[2], 0) + 1
    by_county = sorted(by_county.items(), key=lambda kv: -kv[1])
    stamp = datetime.now().strftime("%Y%m%d")
    csv_path = os.path.join(OUT_DIR, f"new_companies_{stamp}.csv")
    html_path = os.path.join(OUT_DIR, f"new_companies_{stamp}.html")
    write_csv(csv_path, cols, rows)
    write_html(html_path, rows, by_county)
    top = ", ".join(f"{c}:{n}" for c, n in by_county[:5]) or "(none)"
    print(f"{len(rows)} new companies (last {DAYS}d). Top counties: {top}")
    print(f"  -> {csv_path}\n  -> {html_path}")


if __name__ == "__main__":
    main()
