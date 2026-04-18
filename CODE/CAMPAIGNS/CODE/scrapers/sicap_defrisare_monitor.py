"""
SICAP monitor for tree-cutting procurement (CPV 77211400, 77211500, keyword defrisare).
Scrapes sicap.pro announcement pages, filters by CPV/keyword.
Saves leads to sicap_defrisare_leads.csv, tracks seen IDs in sicap_defrisare_seen.json.
Sends Telegram alert on new entries.
"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import requests
from bs4 import BeautifulSoup
import csv, json, os, re, logging
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_CSV   = os.path.join(BASE_DIR, "sicap_defrisare_leads.csv")
SEEN_JSON = os.path.join(BASE_DIR, "sicap_defrisare_seen.json")
LOG_FILE  = os.path.join(BASE_DIR, "sicap_defrisare_monitor.log")

logging.basicConfig(filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s")

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
HEADERS = {"User-Agent": "Mozilla/5.0 (research bot)"}

TARGET_CPVS   = {"77211400", "77211500"}
KEYWORDS      = ["defrisare", "taiere arbori", "toaletare", "copaci", "arbori"]
REGIONS       = ["bucuresti", "ilfov", "prahova", "iasi", "cluj", "timis",
                 "arges", "dambovita", "giurgiu", "teleorman", "calarasi", "ialomita"]
BASE_URL      = "https://sicap.pro"
LISTING_TYPES = ["licitatii-publice", "achizitii-directe"]

def load_seen():
    if os.path.exists(SEEN_JSON):
        return set(json.load(open(SEEN_JSON)))
    return set()

def save_seen(seen):
    json.dump(list(seen), open(SEEN_JSON, "w"))

def fetch(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logging.warning(f"FAIL {url}: {e}")
        return None

def parse_list_page(html, region_url):
    """Return list of (id, title, authority, cpv, date, url) from a listing page."""
    soup = BeautifulSoup(html, "html.parser")
    items = []
    for li in soup.find_all("li"):
        a = li.find("a", href=re.compile(r"/anunturi/CN\d+"))
        if not a:
            continue
        href = a["href"]
        notice_id = re.search(r"CN(\d+)", href).group(0)
        title = a.get_text(strip=True)
        text  = li.get_text(" ", strip=True)
        # Extract CPV
        cpv_m = re.search(r"\b(772\d{5,6})-?\d*\b", text)
        cpv = cpv_m.group(1) if cpv_m else ""
        # Extract date
        date_m = re.search(r"\d{2}\.\d{2}\.\d{4}", text)
        date = date_m.group(0) if date_m else ""
        # Filter
        matches_cpv = cpv in TARGET_CPVS
        matches_kw  = any(kw in text.lower() for kw in KEYWORDS)
        if matches_cpv or matches_kw:
            items.append({
                "id": notice_id,
                "title": title[:120],
                "authority": "",
                "cpv": cpv,
                "date": date,
                "url": BASE_URL + href,
            })
    return items

def enrich_notice(url):
    """Fetch detail page and extract authority + value."""
    html = fetch(url)
    if not html:
        return {}, ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    # Authority usually in a link with /autoritate/
    auth_tag = soup.find("a", href=re.compile(r"/autoritate/"))
    authority = auth_tag.get_text(strip=True) if auth_tag else ""
    # Value
    val_m = re.search(r"([\d.,]+)\s*RON", text)
    value = val_m.group(0) if val_m else ""
    loc_m = re.search(r"\b(Bucuresti|Cluj|Timis|Iasi|Ilfov|Prahova)\b", text, re.IGNORECASE)
    localitate = loc_m.group(0) if loc_m else ""
    return {"authority": authority, "valoare": value, "localitate": localitate}, text

def send_telegram(msg):
    if not TELEGRAM_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT, "text": msg}, timeout=10)

def main():
    seen = load_seen()
    new_leads = []

    for ltype in LISTING_TYPES:
      for region in REGIONS:
        url = f"{BASE_URL}/anunturi/{ltype}/{region}"
        logging.info(f"Scanning {url}")
        html = fetch(url)
        if not html:
            continue
        items = parse_list_page(html, url)
        logging.info(f"  {len(items)} potential hits in {region}/{ltype}")
        for item in items:
            if item["id"] in seen:
                continue
            seen.add(item["id"])
            detail, _ = enrich_notice(item["url"])
            item.update(detail)
            new_leads.append(item)
            msg = f"[DEFRISARE] {item.get('authority','')} | {item['title']} | {item.get('valoare','')} | {item['url']}"
            print(msg.encode('utf-8', errors='replace').decode('utf-8', errors='replace'))
            send_telegram(msg)

    save_seen(seen)

    if new_leads:
        write_header = not os.path.exists(OUT_CSV)
        with open(OUT_CSV, "a", newline="", encoding="utf-8") as f:
            cols = ["id","title","authority","cpv","date","valoare","localitate","url"]
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            if write_header:
                w.writeheader()
            w.writerows(new_leads)

    print(f"Done. {len(new_leads)} new leads. Total seen: {len(seen)}.")

if __name__ == "__main__":
    main()
