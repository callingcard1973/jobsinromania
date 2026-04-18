"""
bid_analyzer.py — Query ted_awards for market intelligence on a CPV code or keyword.
Output: JSON summary used by bid_writer.py and bid_api.py
"""
import json
import sys
import psycopg2
import psycopg2.extras

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 5433,
    "user": "tudor",
    "password": "tudor",
    "dbname": "interjob_master",
}

def get_conn():
    return psycopg2.connect(**DB_CONFIG)

def analyze_cpv(cpv_code: str = None, keyword: str = None) -> dict:
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Resolve CPV code from keyword if no direct CPV given
    if not cpv_code and keyword:
        cur.execute(
            """
            SELECT cpv_code, cpv_name, COUNT(*) as cnt
            FROM ted_awards
            WHERE cpv_name ILIKE %s AND cpv_code IS NOT NULL
            GROUP BY cpv_code, cpv_name
            ORDER BY cnt DESC LIMIT 1
            """,
            (f"%{keyword}%",),
        )
        row = cur.fetchone()
        if row:
            cpv_code = row["cpv_code"]
            cpv_name = row["cpv_name"]
        else:
            return {"error": f"No CPV found for keyword: {keyword}"}
    else:
        cur.execute(
            "SELECT DISTINCT cpv_name FROM ted_awards WHERE cpv_code = %s LIMIT 1",
            (cpv_code,),
        )
        row = cur.fetchone()
        cpv_name = row["cpv_name"] if row else cpv_code

    # Top 10 winners by frequency + total value
    cur.execute(
        """
        SELECT win_name,
               COUNT(*) AS contracts,
               SUM(value) AS total_value,
               AVG(value) AS avg_value
        FROM ted_awards
        WHERE cpv_code = %s AND win_name IS NOT NULL AND value > 0
        GROUP BY win_name
        ORDER BY contracts DESC, total_value DESC
        LIMIT 10
        """,
        (cpv_code,),
    )
    top_winners = [dict(r) for r in cur.fetchall()]

    # Price stats
    cur.execute(
        """
        SELECT
            COUNT(*) AS total_contracts,
            MIN(value) AS min_value,
            PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY value) AS median_value,
            MAX(value) AS max_value,
            AVG(value) AS avg_value
        FROM ted_awards
        WHERE cpv_code = %s AND value > 0
        """,
        (cpv_code,),
    )
    stats = dict(cur.fetchone() or {})

    # Buyer types (top 10 public authorities)
    cur.execute(
        """
        SELECT cae_name, COUNT(*) AS cnt
        FROM ted_awards
        WHERE cpv_code = %s AND cae_name IS NOT NULL
        GROUP BY cae_name
        ORDER BY cnt DESC LIMIT 10
        """,
        (cpv_code,),
    )
    top_buyers = [dict(r) for r in cur.fetchall()]

    # Year distribution (last 5 years)
    cur.execute(
        """
        SELECT year, COUNT(*) AS cnt, AVG(value) AS avg_value
        FROM ted_awards
        WHERE cpv_code = %s AND year >= EXTRACT(YEAR FROM NOW()) - 5
        GROUP BY year ORDER BY year DESC
        """,
        (cpv_code,),
    )
    yearly = [dict(r) for r in cur.fetchall()]

    # Country breakdown
    cur.execute(
        """
        SELECT country, COUNT(*) AS cnt
        FROM ted_awards
        WHERE cpv_code = %s AND country IS NOT NULL
        GROUP BY country ORDER BY cnt DESC LIMIT 10
        """,
        (cpv_code,),
    )
    countries = [dict(r) for r in cur.fetchall()]

    cur.close()
    conn.close()

    # Convert Decimal to float for JSON serialization
    def to_float(v):
        return float(v) if v is not None else None

    for w in top_winners:
        w["total_value"] = to_float(w["total_value"])
        w["avg_value"] = to_float(w["avg_value"])

    for k in ["min_value", "median_value", "max_value", "avg_value"]:
        stats[k] = to_float(stats.get(k))

    for y in yearly:
        y["avg_value"] = to_float(y["avg_value"])

    return {
        "cpv_code": cpv_code,
        "cpv_name": cpv_name,
        "stats": stats,
        "top_winners": top_winners,
        "top_buyers": top_buyers,
        "yearly_trend": yearly,
        "countries": countries,
    }


def format_summary(data: dict) -> str:
    """Human-readable summary for LLM prompt injection."""
    if "error" in data:
        return f"Eroare: {data['error']}"
    s = data["stats"]
    lines = [
        f"CPV: {data['cpv_code']} — {data['cpv_name']}",
        f"Total contracte analizate: {s.get('total_contracts', 0)}",
        f"Valoare medie: {s.get('avg_value', 0):,.0f} EUR",
        f"Valoare mediana: {s.get('median_value', 0):,.0f} EUR",
        f"Interval: {s.get('min_value', 0):,.0f} — {s.get('max_value', 0):,.0f} EUR",
        "",
        "Top castigatori:",
    ]
    for i, w in enumerate(data["top_winners"][:5], 1):
        lines.append(f"  {i}. {w['win_name']} ({w['contracts']} contracte, avg {w['avg_value']:,.0f} EUR)")
    lines.append("")
    lines.append("Principali cumparatori:")
    for b in data["top_buyers"][:5]:
        lines.append(f"  - {b['cae_name']} ({b['cnt']} contracte)")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Analiza piata TED pentru un CPV")
    parser.add_argument("--cpv", help="Cod CPV (ex: 45000000)")
    parser.add_argument("--keyword", help="Cuvant cheie (ex: constructii)")
    parser.add_argument("--json", action="store_true", help="Output JSON brut")
    args = parser.parse_args()

    if not args.cpv and not args.keyword:
        print("Folosire: bid_analyzer.py --cpv 45000000 sau --keyword constructii")
        sys.exit(1)

    result = analyze_cpv(cpv_code=args.cpv, keyword=args.keyword)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    else:
        print(format_summary(result))
