#!/usr/bin/env python3
"""
Agent 1: Listing Hunter — scaneaza OLX, Imobiliare.ro, Storia pentru terenuri/ferme.
Filtreaza chilipiruri. Salveaza in PostgreSQL. Cron 2x/zi.

Folosire:
  python3 listing_hunter.py                # scan toate sursele
  python3 listing_hunter.py --source olx   # doar OLX
  python3 listing_hunter.py --dry-run      # nu salveaza in DB

Tabela: terenuri_listings (creata automat)
"""
import argparse, hashlib, json, logging, os, re, sys, time
from datetime import datetime
from urllib.parse import quote_plus

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("hunter")

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    log.error("pip install requests beautifulsoup4")
    sys.exit(1)

DB = {"host": "localhost", "dbname": "interjob_master", "user": "tudor", "password": "tudor"}
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 Chrome/120"}

# Cuvinte cheie care indica chilipir
URGENT_KEYWORDS = [
    "urgent", "lichidare", "sub pret", "pret negociabil", "accept orice",
    "plec din tara", "emigrez", "vand rapid", "ocazie", "pret redus",
    "executare silita", "faliment", "cedez", "schimb", "ieftin",
]

SEARCHES_OLX = [
    "https://www.olx.ro/imobiliare/terenuri/?search%5Border%5D=created_at:desc",
    "https://www.olx.ro/imobiliare/terenuri/agricol/?search%5Border%5D=created_at:desc",
    "https://www.olx.ro/imobiliare/terenuri/constructii/?search%5Border%5D=created_at:desc",
]

SEARCHES_IMOBILIARE = [
    "https://www.imobiliare.ro/vanzare-terenuri?pagina=1",
    "https://www.imobiliare.ro/vanzare-terenuri/agricol?pagina=1",
]


def scrape_olx(max_pages=3):
    """Scrapeaza OLX terenuri."""
    listings = []
    for base_url in SEARCHES_OLX:
        for page in range(1, max_pages + 1):
            url = f"{base_url}&page={page}"
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select("[data-cy='l-card']")
                if not cards:
                    cards = soup.select(".css-1sw7q4x")  # fallback selector
                for card in cards:
                    title_el = card.select_one("h6") or card.select_one("[data-cy='ad-title']")
                    price_el = card.select_one("[data-testid='ad-price']") or card.select_one(".css-1q7gvpp")
                    link_el = card.select_one("a[href]")
                    location_el = card.select_one("[data-testid='location-date']") or card.select_one(".css-1a4brun")

                    title = title_el.get_text(strip=True) if title_el else ""
                    price_text = price_el.get_text(strip=True) if price_el else ""
                    link = link_el["href"] if link_el else ""
                    if link and not link.startswith("http"):
                        link = "https://www.olx.ro" + link
                    location = location_el.get_text(strip=True) if location_el else ""

                    if title:
                        listings.append({
                            "source": "olx",
                            "title": title[:300],
                            "price_text": price_text[:100],
                            "price_eur": parse_price(price_text),
                            "location": location[:200],
                            "url": link[:500],
                            "scraped_at": datetime.now().isoformat(),
                        })
                time.sleep(2)  # politete
            except Exception as e:
                log.warning(f"OLX eroare pagina {page}: {e}")
    log.info(f"OLX: {len(listings)} anunturi")
    return listings


def scrape_imobiliare(max_pages=3):
    """Scrapeaza Imobiliare.ro terenuri."""
    listings = []
    for base_url in SEARCHES_IMOBILIARE:
        for page in range(1, max_pages + 1):
            url = base_url.replace("pagina=1", f"pagina={page}")
            try:
                r = requests.get(url, headers=HEADERS, timeout=15)
                if r.status_code != 200:
                    continue
                soup = BeautifulSoup(r.text, "html.parser")
                cards = soup.select(".box-anunt") or soup.select("[class*='listing']")
                for card in cards:
                    title_el = card.select_one("h2 a") or card.select_one(".titlu-anunt a")
                    price_el = card.select_one(".pret-mare") or card.select_one("[class*='price']")
                    location_el = card.select_one(".localizare") or card.select_one("[class*='location']")

                    title = title_el.get_text(strip=True) if title_el else ""
                    price_text = price_el.get_text(strip=True) if price_el else ""
                    link = title_el["href"] if title_el and title_el.has_attr("href") else ""
                    if link and not link.startswith("http"):
                        link = "https://www.imobiliare.ro" + link
                    location = location_el.get_text(strip=True) if location_el else ""

                    if title:
                        listings.append({
                            "source": "imobiliare",
                            "title": title[:300],
                            "price_text": price_text[:100],
                            "price_eur": parse_price(price_text),
                            "location": location[:200],
                            "url": link[:500],
                            "scraped_at": datetime.now().isoformat(),
                        })
                time.sleep(2)
            except Exception as e:
                log.warning(f"Imobiliare eroare pagina {page}: {e}")
    log.info(f"Imobiliare.ro: {len(listings)} anunturi")
    return listings


def parse_price(text):
    """Extrage pret numeric din text. Returneaza EUR sau None."""
    if not text:
        return None
    text = text.replace(" ", "").replace(".", "").replace(",", "")
    nums = re.findall(r'\d+', text)
    if not nums:
        return None
    price = int(nums[0])
    if "eur" in text.lower() or "€" in text:
        return price
    if "lei" in text.lower() or "ron" in text.lower():
        return int(price / 5)  # RON -> EUR aproximativ
    return price


def score_urgency(title, price_text=""):
    """Scor urgenta 0-100 bazat pe cuvinte cheie."""
    text = (title + " " + price_text).lower()
    score = 0
    matches = []
    for kw in URGENT_KEYWORDS:
        if kw in text:
            score += 15
            matches.append(kw)
    return min(score, 100), matches


def ensure_table(conn):
    """Creeaza tabela daca nu exista."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS terenuri_listings (
                id SERIAL PRIMARY KEY,
                listing_hash VARCHAR(64) UNIQUE,
                source VARCHAR(20),
                title TEXT,
                price_text VARCHAR(100),
                price_eur INTEGER,
                location VARCHAR(200),
                url TEXT,
                urgency_score INTEGER DEFAULT 0,
                urgency_keywords TEXT,
                is_deal BOOLEAN DEFAULT FALSE,
                scraped_at TIMESTAMP DEFAULT NOW(),
                analyzed_at TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_terenuri_hash ON terenuri_listings(listing_hash)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_terenuri_deal ON terenuri_listings(is_deal)")
    conn.commit()


def save_listings(conn, listings):
    """Salveaza listings noi in DB. Returneaza count noi."""
    new_count = 0
    with conn.cursor() as cur:
        for L in listings:
            h = hashlib.md5((L["title"] + L.get("url", "")).encode()).hexdigest()
            urgency, keywords = score_urgency(L["title"], L.get("price_text", ""))
            is_deal = urgency >= 30
            try:
                cur.execute("""
                    INSERT INTO terenuri_listings (listing_hash, source, title, price_text, price_eur,
                        location, url, urgency_score, urgency_keywords, is_deal, scraped_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (listing_hash) DO NOTHING
                """, (h, L["source"], L["title"], L.get("price_text"), L.get("price_eur"),
                      L.get("location"), L.get("url"), urgency, ",".join(keywords),
                      is_deal, L.get("scraped_at")))
                if cur.rowcount > 0:
                    new_count += 1
            except Exception as e:
                log.warning(f"Insert eroare: {e}")
    conn.commit()
    return new_count


def main():
    parser = argparse.ArgumentParser(description="Listing Hunter — terenuri/ferme")
    parser.add_argument("--source", choices=["olx", "imobiliare", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--pages", type=int, default=3)
    args = parser.parse_args()

    listings = []
    if args.source in ("olx", "all"):
        listings.extend(scrape_olx(args.pages))
    if args.source in ("imobiliare", "all"):
        listings.extend(scrape_imobiliare(args.pages))

    log.info(f"Total: {len(listings)} anunturi scrapate")

    # Scor urgenta
    deals = [L for L in listings if score_urgency(L["title"], L.get("price_text", ""))[0] >= 30]
    log.info(f"Posibile chilipiruri: {len(deals)}")

    if args.dry_run:
        for d in deals[:10]:
            s, kw = score_urgency(d["title"], d.get("price_text", ""))
            print(f"  [{s}] {d['title'][:80]} — {d.get('price_text','')} — {','.join(kw)}")
        return

    import psycopg2
    conn = psycopg2.connect(**DB)
    ensure_table(conn)
    new = save_listings(conn, listings)
    conn.close()

    log.info(f"Salvat: {new} anunturi noi, {len(deals)} chilipiruri")


if __name__ == "__main__":
    main()
