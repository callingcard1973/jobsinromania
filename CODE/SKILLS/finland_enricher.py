#!/opt/ACTIVE/INFRA/venv/bin/python3
"""Finland Enricher - Scrape emails from Finnish company websites"""
import sys
sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")
import csv, json, re, time, random, logging, argparse
from pathlib import Path
from datetime import datetime
import requests

SOURCE = Path("/mnt/hdd/SCRAPER_DATA/csv/EURES/Finland/Finland_contacts_50.csv")
OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/ENRICHED")
OUTPUT = OUTPUT_DIR / "FI_ENRICHED.csv"
CACHE = OUTPUT_DIR / "fi_domain_cache.json"
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS/enricher")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_DIR / f"fi_{datetime.now():%Y%m%d}.log")])
logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

def load_cache():
    return json.load(open(CACHE)) if CACHE.exists() else {}

def save_cache(cache):
    with open(CACHE, "w") as f: json.dump(cache, f)

def extract_domain(url):
    if not url: return None
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc.lower().replace("www.", "")
    except: return None

def find_emails(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    paths = ["", "/yhteystiedot", "/contact", "/ota-yhteytta", "/about"]
    domain = extract_domain(url)
    if not domain: return []
    for path in paths:
        try:
            r = requests.get(f"https://{domain}{path}", headers=headers, timeout=10)
            if r.status_code == 200:
                emails = [e for e in EMAIL_RE.findall(r.text) if not any(x in e.lower() for x in ["example.", ".png", ".jpg"])]
                if emails: return list(set(emails))[:3]
        except: pass
        time.sleep(0.3)
    return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=1000)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()
    
    cache = load_cache()
    if args.status:
        print(f"Cache: {len(cache)} domains, Found: {sum(1 for v in cache.values() if v.get(emails))}")
        return
    
    with open(SOURCE) as f:
        rows = list(csv.DictReader(f))
    logger.info(f"Loaded {len(rows)} rows")
    
    to_process = []
    for row in rows:
        domain = extract_domain(row.get("company_website", ""))
        if domain and domain not in cache:
            to_process.append((domain, row.get("company_website", "")))
    to_process = list(dict(to_process).items())
    logger.info(f"To process: {len(to_process)} domains (limit: {args.limit})")
    
    found = 0
    for i, (domain, website) in enumerate(to_process[:args.limit]):
        if i > 0 and i % 100 == 0:
            logger.info(f"Progress: {i}/{min(len(to_process), args.limit)}, found: {found}")
            save_cache(cache)
        emails = find_emails(website)
        cache[domain] = {"emails": emails, "website": website, "checked": datetime.now().isoformat()}
        if emails:
            found += 1
            logger.info(f"  {domain}: {emails[0]}")
        time.sleep(random.uniform(0.5, 1.5))
    
    save_cache(cache)
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "email", "website", "checked"])
        for domain, data in cache.items():
            if data.get("emails"):
                writer.writerow([domain, data["emails"][0], data.get("website", ""), data.get("checked", "")])
    
    logger.info(f"Done! Found {found} emails. Total cache: {len(cache)}")

if __name__ == "__main__":
    main()
