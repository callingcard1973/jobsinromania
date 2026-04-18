#!/usr/bin/env python3
"""
Agent 6: CMA (Comparative Market Analysis) — mini-evaluator automat.
Compara un listing cu vanzari similare din zona.
Estimeaza pret real vs pret cerut.

Folosire:
  python3 cma_agent.py --id 123           # analiza un listing specific
  python3 cma_agent.py --deals            # analiza toate deal-urile
  python3 cma_agent.py --zone "ILFOV"     # raport zona
"""
import argparse, logging, sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("cma")

try:
    import psycopg2
except ImportError:
    log.error("pip install psycopg2-binary")
    sys.exit(1)

from price_anomaly import extract_area_mp, normalize_location

DB = {"host": "localhost", "dbname": "interjob_master", "user": "tudor", "password": "tudor"}


def get_comparables(conn, zone, area_mp, radius_pct=50):
    """Gaseste anunturi similare in aceeasi zona cu suprafata +/- radius%."""
    min_area = area_mp * (1 - radius_pct / 100)
    max_area = area_mp * (1 + radius_pct / 100)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, price_eur, location, url
            FROM terenuri_listings
            WHERE price_eur IS NOT NULL AND price_eur > 0
        """)
        rows = cur.fetchall()

    comps = []
    for row_id, title, price, location, url in rows:
        if normalize_location(location) != zone:
            continue
        area = extract_area_mp(title)
        if not area or area < 10:
            continue
        if min_area <= area <= max_area:
            comps.append({
                "id": row_id,
                "title": title,
                "price_eur": price,
                "area_mp": int(area),
                "ppm": round(price / area, 2),
                "url": url,
            })

    comps.sort(key=lambda x: x["ppm"])
    return comps


def cma_report(conn, listing_id):
    """Genereaza raport CMA pentru un listing."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, price_eur, location, url FROM terenuri_listings WHERE id = %s",
            (listing_id,)
        )
        row = cur.fetchone()
        if not row:
            log.error(f"Listing {listing_id} nu exista")
            return None

    row_id, title, price, location, url = row
    area = extract_area_mp(title)
    zone = normalize_location(location)

    if not area or area < 10:
        log.warning(f"Nu pot extrage suprafata din: {title}")
        return None

    ppm = round(price / area, 2) if price and area else 0
    comps = get_comparables(conn, zone, area)

    if len(comps) < 2:
        log.warning(f"Prea putine comparabile in {zone} ({len(comps)})")
        return None

    # Statistici comparabile
    prices_ppm = [c["ppm"] for c in comps]
    prices_ppm.sort()
    median_ppm = prices_ppm[len(prices_ppm) // 2]
    avg_ppm = sum(prices_ppm) / len(prices_ppm)
    min_ppm = prices_ppm[0]
    max_ppm = prices_ppm[-1]

    # Estimare valoare
    estimated_value = int(median_ppm * area)
    diff = estimated_value - price if price else 0
    diff_pct = round((diff / price) * 100, 1) if price else 0

    report = {
        "listing_id": row_id,
        "title": title,
        "price_asked": price,
        "area_mp": int(area),
        "ppm_asked": ppm,
        "zone": zone,
        "comparables_count": len(comps),
        "median_ppm": round(median_ppm, 2),
        "avg_ppm": round(avg_ppm, 2),
        "min_ppm": round(min_ppm, 2),
        "max_ppm": round(max_ppm, 2),
        "estimated_value": estimated_value,
        "difference_eur": diff,
        "difference_pct": diff_pct,
        "verdict": "SUB PIATA" if diff_pct > 20 else ("LA PIATA" if abs(diff_pct) <= 20 else "SUPRA PIATA"),
        "url": url,
    }
    return report


def print_report(r):
    """Afiseaza raport CMA frumos."""
    if not r:
        return
    print(f"\n{'='*60}")
    print(f"CMA REPORT — #{r['listing_id']}")
    print(f"{'='*60}")
    print(f"  {r['title'][:70]}")
    print(f"  Zona: {r['zone']}")
    print(f"  Suprafata: {r['area_mp']} mp")
    print(f"")
    print(f"  Pret cerut:    EUR {r['price_asked']:>10,} ({r['ppm_asked']} EUR/mp)")
    print(f"  Valoare estim: EUR {r['estimated_value']:>10,} ({r['median_ppm']} EUR/mp mediana)")
    print(f"  Diferenta:     EUR {r['difference_eur']:>+10,} ({r['difference_pct']:+.1f}%)")
    print(f"")
    print(f"  Comparabile: {r['comparables_count']} in {r['zone']}")
    print(f"    Min: {r['min_ppm']} | Mediana: {r['median_ppm']} | Max: {r['max_ppm']} EUR/mp")
    print(f"")
    v = r["verdict"]
    if v == "SUB PIATA":
        print(f"  >>> VERDICT: {v} — POSIBIL CHILIPIR <<<")
    elif v == "SUPRA PIATA":
        print(f"  >>> VERDICT: {v} — PRET UMFLAT <<<")
    else:
        print(f"  >>> VERDICT: {v} <<<")
    print(f"  URL: {r['url']}")


def zone_report(conn, zone_name):
    """Raport complet pe o zona."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, price_eur, location
            FROM terenuri_listings
            WHERE price_eur IS NOT NULL AND price_eur > 0
        """)
        rows = cur.fetchall()

    zone_listings = []
    for row_id, title, price, location in rows:
        if normalize_location(location) != zone_name.upper():
            continue
        area = extract_area_mp(title)
        if area and area > 10:
            zone_listings.append({"id": row_id, "ppm": round(price / area, 2), "area": int(area), "price": price})

    if not zone_listings:
        print(f"Zero listings in {zone_name}")
        return

    ppms = sorted([l["ppm"] for l in zone_listings])
    print(f"\n{'='*60}")
    print(f"ZONA: {zone_name.upper()} — {len(zone_listings)} terenuri")
    print(f"{'='*60}")
    print(f"  Pret/mp: {ppms[0]:.1f} — {ppms[-1]:.1f} EUR/mp")
    print(f"  Mediana: {ppms[len(ppms)//2]:.1f} EUR/mp")
    print(f"  Media:   {sum(ppms)/len(ppms):.1f} EUR/mp")


def main():
    parser = argparse.ArgumentParser(description="CMA Agent — evaluator automat")
    parser.add_argument("--id", type=int, help="Analiza listing specific")
    parser.add_argument("--deals", action="store_true", help="Analiza toate deal-urile")
    parser.add_argument("--zone", help="Raport pe zona")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB)

    if args.id:
        r = cma_report(conn, args.id)
        print_report(r)
    elif args.zone:
        zone_report(conn, args.zone)
    elif args.deals:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM terenuri_listings WHERE is_deal = TRUE ORDER BY urgency_score DESC LIMIT 20")
            deal_ids = [r[0] for r in cur.fetchall()]
        for did in deal_ids:
            r = cma_report(conn, did)
            print_report(r)
    else:
        parser.print_help()

    conn.close()


if __name__ == "__main__":
    main()
