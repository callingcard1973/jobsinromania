#!/usr/bin/env python3
"""
Agent 3: Geo Intelligence — analiza infrastructura teren via OSM/Nominatim/ORS.
Imbogateste fiecare listing din terenuri_listings cu date geo reale.

Pipeline:
  1. Nominatim: adresa → coordonate (lat, lon)
  2. Overpass: drumuri, cladiri, utilitati in raza de 1km
  3. OpenRouteService: distanta reala pana la cel mai apropiat oras
  4. Scor geo 0-100 + verdict

Cron: ruleaza dupa listing_hunter (in run_terenuri.sh)
Rate limits: 1 req/sec Nominatim, Overpass variabil

Folosire:
  python3 geo_intelligence.py                # analizeaza listings noi
  python3 geo_intelligence.py --id 123       # analizeaza un listing
  python3 geo_intelligence.py --dry-run      # nu salveaza in DB
"""
import argparse, json, logging, math, os, re, sys, time
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("geo_intel")

try:
    import requests
    import psycopg2
except ImportError:
    log.error("pip install requests psycopg2-binary")
    sys.exit(1)

DB = {"host": "localhost", "dbname": "interjob_master", "user": "tudor", "password": "tudor"}
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
ORS_URL = "https://api.openrouteservice.org"  # nevoie de API key gratuit
HEADERS = {"User-Agent": "InterJob-GeoIntel/1.0 (tudor@interjob.ro)"}

# Orase principale Romania cu coordonate
CITIES_RO = {
    "BUCURESTI": (44.4268, 26.1025), "CLUJ-NAPOCA": (46.7712, 23.6236),
    "TIMISOARA": (45.7489, 21.2087), "IASI": (47.1585, 27.6014),
    "CONSTANTA": (44.1598, 28.6348), "CRAIOVA": (44.3302, 23.7949),
    "BRASOV": (45.6427, 25.5887), "GALATI": (45.4353, 28.0080),
    "PLOIESTI": (44.9462, 26.0254), "ORADEA": (47.0465, 21.9189),
    "BRAILA": (45.2692, 27.9575), "ARAD": (46.1866, 21.3123),
    "PITESTI": (44.8565, 24.8692), "SIBIU": (45.7983, 24.1256),
    "BACAU": (46.5670, 26.9146), "TARGU MURES": (46.5386, 24.5575),
    "BAIA MARE": (47.6567, 23.5850), "BUZAU": (45.1500, 26.8333),
    "BOTOSANI": (47.7487, 26.6616), "SATU MARE": (47.7921, 22.8857),
    "SUCEAVA": (47.6635, 26.2596), "PIATRA NEAMT": (46.9275, 26.3708),
    "DROBETA": (44.6369, 22.6597), "TARGOVISTE": (44.9254, 25.4567),
    "FOCSANI": (45.6967, 27.1833), "BISTRITA": (47.1333, 24.5000),
    "RESITA": (45.2967, 21.8883), "ALBA IULIA": (46.0667, 23.5800),
}


def ensure_geo_columns(conn):
    """Adauga coloane geo daca nu exista."""
    cols = {
        "lat": "DOUBLE PRECISION",
        "lon": "DOUBLE PRECISION",
        "nearest_city": "VARCHAR(100)",
        "distance_city_km": "DOUBLE PRECISION",
        "has_paved_road": "BOOLEAN",
        "road_distance_m": "INTEGER",
        "buildings_nearby": "INTEGER",
        "geo_score": "INTEGER",
        "geo_verdict": "VARCHAR(50)",
        "geo_details": "JSONB",
        "geo_analyzed_at": "TIMESTAMP",
    }
    with conn.cursor() as cur:
        for col, dtype in cols.items():
            try:
                cur.execute(f"ALTER TABLE terenuri_listings ADD COLUMN {col} {dtype}")
            except Exception:
                conn.rollback()
                continue
    conn.commit()


def geocode_location(location_text):
    """Nominatim: text → (lat, lon). Rate limit: 1/sec."""
    if not location_text:
        return None, None
    # Curata textul
    clean = re.sub(r'(Azi|Ieri|\d{1,2}:\d{2}|luna trecuta)', '', location_text).strip(" -,")
    clean = clean + ", Romania" if "romania" not in clean.lower() else clean

    try:
        r = requests.get(NOMINATIM_URL, params={
            "q": clean, "format": "json", "limit": 1, "countrycodes": "ro"
        }, headers=HEADERS, timeout=10)
        time.sleep(1.1)  # respecta rate limit
        if r.status_code == 200 and r.json():
            result = r.json()[0]
            return float(result["lat"]), float(result["lon"])
    except Exception as e:
        log.warning(f"Geocode eroare '{clean}': {e}")
    return None, None


def haversine_km(lat1, lon1, lat2, lon2):
    """Distanta in km intre 2 puncte."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def find_nearest_city(lat, lon):
    """Gaseste cel mai apropiat oras si distanta."""
    best_city, best_dist = "NECUNOSCUT", 999
    for city, (clat, clon) in CITIES_RO.items():
        d = haversine_km(lat, lon, clat, clon)
        if d < best_dist:
            best_dist = d
            best_city = city
    return best_city, round(best_dist, 1)


def overpass_infrastructure(lat, lon, radius_m=1000):
    """Overpass API: drumuri + cladiri + utilitati in raza."""
    query = f"""
    [out:json][timeout:15];
    (
      way["highway"](around:{radius_m},{lat},{lon});
      way["building"](around:{radius_m},{lat},{lon});
      node["amenity"](around:{radius_m},{lat},{lon});
    );
    out count;
    """
    try:
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=20)
        time.sleep(2)  # rate limit
        if r.status_code == 200:
            data = r.json()
            elements = data.get("elements", [])
            # Count by type
            total = 0
            for el in elements:
                total += el.get("tags", {}).get("total", 0) if "tags" in el else 1
            return total
    except Exception as e:
        log.warning(f"Overpass eroare: {e}")
    return None


def overpass_roads(lat, lon, radius_m=500):
    """Verifica daca exista drum asfaltat aproape."""
    query = f"""
    [out:json][timeout:10];
    way["highway"~"primary|secondary|tertiary|residential|unclassified"](around:{radius_m},{lat},{lon});
    out count;
    """
    try:
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=15)
        time.sleep(2)
        if r.status_code == 200:
            data = r.json()
            elements = data.get("elements", [])
            count = len(elements)
            if count == 0 and elements:
                count = elements[0].get("tags", {}).get("total", 0)
            return count > 0, count
    except Exception as e:
        log.warning(f"Overpass roads eroare: {e}")
    return None, 0


def overpass_buildings(lat, lon, radius_m=1000):
    """Numara cladiri in raza."""
    query = f"""
    [out:json][timeout:10];
    way["building"](around:{radius_m},{lat},{lon});
    out count;
    """
    try:
        r = requests.post(OVERPASS_URL, data={"data": query}, timeout=15)
        time.sleep(2)
        if r.status_code == 200:
            data = r.json()
            elements = data.get("elements", [])
            if elements and "tags" in elements[0]:
                return int(elements[0]["tags"].get("total", 0))
            return len(elements)
    except Exception as e:
        log.warning(f"Overpass buildings eroare: {e}")
    return 0


def compute_geo_score(distance_km, has_road, buildings, price_eur=None):
    """Calculeaza scor geo 0-100."""
    score = 50  # start neutru

    # Distanta oras (-30 la +20)
    if distance_km < 5:
        score += 20
    elif distance_km < 15:
        score += 10
    elif distance_km < 30:
        score += 0
    elif distance_km < 50:
        score -= 10
    else:
        score -= 30

    # Drum asfaltat (-20 la +15)
    if has_road is True:
        score += 15
    elif has_road is False:
        score -= 20

    # Cladiri vecine (-10 la +15)
    if buildings and buildings > 20:
        score += 15
    elif buildings and buildings > 5:
        score += 5
    elif buildings is not None and buildings == 0:
        score -= 10

    return max(0, min(100, score))


def geo_verdict(score, distance_km, has_road):
    """Genereaza verdict text."""
    if score >= 70:
        return "LOCATIE BUNA"
    elif score >= 50:
        if not has_road:
            return "ACCES SLAB"
        return "ACCEPTABIL"
    elif score >= 30:
        if distance_km > 50:
            return "PREA IZOLAT"
        return "PROBLEMATIC"
    else:
        return "EVITA"


def analyze_listing(conn, listing_id, dry_run=False):
    """Analiza geo completa pentru un listing."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id, title, location, price_eur FROM terenuri_listings WHERE id = %s",
            (listing_id,)
        )
        row = cur.fetchone()
        if not row:
            return None

    lid, title, location, price = row

    # 1. Geocode
    lat, lon = geocode_location(location)
    if not lat or not lon:
        log.warning(f"#{lid} nu pot geocoda: {location}")
        return None

    # 2. Nearest city
    city, dist_km = find_nearest_city(lat, lon)

    # 3. Overpass: drumuri
    has_road, road_count = overpass_roads(lat, lon, 500)

    # 4. Overpass: cladiri
    buildings = overpass_buildings(lat, lon, 1000)

    # 5. Scor + verdict
    score = compute_geo_score(dist_km, has_road, buildings, price)
    verdict = geo_verdict(score, dist_km, has_road)

    details = {
        "nearest_city": city,
        "distance_km": dist_km,
        "has_paved_road": has_road,
        "road_count_500m": road_count,
        "buildings_1km": buildings,
    }

    log.info(f"#{lid} [{score}] {verdict} — {city} {dist_km}km, drum={'DA' if has_road else 'NU'}, cladiri={buildings}")

    if not dry_run:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE terenuri_listings SET
                    lat=%s, lon=%s, nearest_city=%s, distance_city_km=%s,
                    has_paved_road=%s, road_distance_m=%s, buildings_nearby=%s,
                    geo_score=%s, geo_verdict=%s, geo_details=%s, geo_analyzed_at=NOW()
                WHERE id=%s
            """, (lat, lon, city, dist_km, has_road, road_count,
                  buildings, score, verdict, json.dumps(details), lid))
        conn.commit()

    return {"id": lid, "score": score, "verdict": verdict, **details}


def main():
    parser = argparse.ArgumentParser(description="Geo Intelligence Agent")
    parser.add_argument("--id", type=int, help="Analizeaza un listing")
    parser.add_argument("--limit", type=int, default=20, help="Max listings de analizat")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(**DB)
    ensure_geo_columns(conn)

    if args.id:
        result = analyze_listing(conn, args.id, args.dry_run)
        if result:
            print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        # Analizeaza listings neanalizate
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id FROM terenuri_listings
                WHERE geo_analyzed_at IS NULL
                AND location IS NOT NULL AND length(location) > 3
                ORDER BY urgency_score DESC NULLS LAST, id DESC
                LIMIT %s
            """, (args.limit,))
            ids = [r[0] for r in cur.fetchall()]

        log.info(f"De analizat: {len(ids)} listings")
        for lid in ids:
            analyze_listing(conn, lid, args.dry_run)

    conn.close()


if __name__ == "__main__":
    main()
