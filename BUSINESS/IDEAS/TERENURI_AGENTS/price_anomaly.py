#!/usr/bin/env python3
"""
Agent 2: Price Anomaly Detector — gaseste terenuri sub pretul pietei.
Compara pret/mp cu mediana zonei. Flaggeaza anomalii.

Ruleaza dupa listing_hunter.py (care populeaza terenuri_listings).
Cron: zilnic dupa hunter, sau standalone.

Folosire:
  python3 price_anomaly.py              # analizeaza toate listings neanalizate
  python3 price_anomaly.py --threshold 50  # sub 50% din mediana = anomalie
"""
import argparse, logging, re, sys
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("price_anomaly")

try:
    import psycopg2
except ImportError:
    log.error("pip install psycopg2-binary")
    sys.exit(1)

DB = {"host": "localhost", "dbname": "interjob_master", "user": "tudor", "password": "tudor"}


def extract_area_mp(title):
    """Extrage suprafata din titlu (mp sau ha)."""
    title_lower = title.lower()
    # Cauta pattern: 500 mp, 500mp, 0.5 ha, 5000 m2
    mp_match = re.search(r'(\d+[\.,]?\d*)\s*(?:mp|m2|m²|metri)', title_lower)
    if mp_match:
        return float(mp_match.group(1).replace(",", "."))
    ha_match = re.search(r'(\d+[\.,]?\d*)\s*(?:ha|hectar)', title_lower)
    if ha_match:
        return float(ha_match.group(1).replace(",", ".")) * 10000
    # Ari
    ar_match = re.search(r'(\d+[\.,]?\d*)\s*(?:ar[ie]?\b)', title_lower)
    if ar_match:
        return float(ar_match.group(1).replace(",", ".")) * 100
    return None


def normalize_location(location):
    """Extrage judet din location string."""
    if not location:
        return "NECUNOSCUT"
    # OLX format: "Azi 10:25 - Ilfov"  sau "Cluj-Napoca - Cluj"
    parts = location.replace(",", " - ").split(" - ")
    # Ultimul element e de obicei judetul
    for part in reversed(parts):
        part = part.strip()
        if len(part) > 2 and not re.match(r'^\d', part) and "azi" not in part.lower():
            return part.upper()[:30]
    return "NECUNOSCUT"


def compute_zone_medians(conn):
    """Calculeaza mediana pret/mp pe zona din listings cu pret si suprafata."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT location, price_eur, title
            FROM terenuri_listings
            WHERE price_eur IS NOT NULL AND price_eur > 0
        """)
        rows = cur.fetchall()

    zone_prices = {}  # zona -> [pret_per_mp, ...]
    for location, price_eur, title in rows:
        area = extract_area_mp(title)
        if not area or area < 10:
            continue
        ppm = price_eur / area
        if ppm < 0.01 or ppm > 1000:  # filtreaza aberatii
            continue
        zone = normalize_location(location)
        zone_prices.setdefault(zone, []).append(ppm)

    # Calculeaza mediane
    medians = {}
    for zone, prices in zone_prices.items():
        prices.sort()
        mid = len(prices) // 2
        median = prices[mid] if len(prices) % 2 else (prices[mid - 1] + prices[mid]) / 2
        medians[zone] = {"median_ppm": round(median, 2), "count": len(prices)}

    log.info(f"Zone cu mediane: {len(medians)}")
    return medians


def detect_anomalies(conn, medians, threshold_pct=50):
    """Gaseste listings sub threshold% din mediana zonei."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, price_eur, location, url, urgency_score
            FROM terenuri_listings
            WHERE price_eur IS NOT NULL AND price_eur > 0
            AND analyzed_at IS NULL
        """)
        rows = cur.fetchall()

    anomalies = []
    for row_id, title, price_eur, location, url, urgency in rows:
        area = extract_area_mp(title)
        if not area or area < 10:
            continue
        ppm = price_eur / area
        zone = normalize_location(location)
        if zone not in medians:
            continue
        median = medians[zone]["median_ppm"]
        if median <= 0:
            continue
        pct_of_median = (ppm / median) * 100

        if pct_of_median < threshold_pct:
            anomalies.append({
                "id": row_id,
                "title": title,
                "price_eur": price_eur,
                "area_mp": int(area),
                "ppm": round(ppm, 2),
                "zone": zone,
                "median_ppm": median,
                "pct_of_median": round(pct_of_median, 1),
                "url": url,
                "urgency": urgency or 0,
                "deal_score": int(100 - pct_of_median + (urgency or 0) / 2),
            })

    anomalies.sort(key=lambda x: x["deal_score"], reverse=True)
    log.info(f"Anomalii detectate: {len(anomalies)} sub {threshold_pct}% din mediana")
    return anomalies


def mark_analyzed(conn, listing_ids):
    """Marcheaza listings ca analizate."""
    if not listing_ids:
        return
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE terenuri_listings SET analyzed_at = NOW() WHERE id = ANY(%s)",
            (listing_ids,)
        )
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Price Anomaly Detector")
    parser.add_argument("--threshold", type=int, default=50, help="Sub N%% din mediana = anomalie")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB)

    medians = compute_zone_medians(conn)
    if not medians:
        log.warning("Zero mediane — nevoie de mai multe date. Ruleaza listing_hunter.py intai.")
        conn.close()
        return

    anomalies = detect_anomalies(conn, medians, args.threshold)

    print(f"\n{'='*70}")
    print(f"ANOMALII PRET — sub {args.threshold}% din mediana zonei")
    print(f"{'='*70}")
    for a in anomalies[:20]:
        print(f"\n  [{a['deal_score']}] {a['title'][:70]}")
        print(f"       EUR {a['price_eur']} | {a['area_mp']} mp | {a['ppm']} EUR/mp")
        print(f"       Zona: {a['zone']} (mediana {a['median_ppm']} EUR/mp) = {a['pct_of_median']}%")
        print(f"       {a['url']}")

    if not args.dry_run:
        all_ids = [r[0] for r in conn.cursor().execute(
            "SELECT id FROM terenuri_listings WHERE analyzed_at IS NULL"
        ).fetchall()] if False else []
        # Mark all as analyzed
        with conn.cursor() as cur:
            cur.execute("UPDATE terenuri_listings SET analyzed_at = NOW() WHERE analyzed_at IS NULL")
        conn.commit()

    conn.close()

    # Returneaza anomaliile pentru deal_alert
    return anomalies


if __name__ == "__main__":
    main()
