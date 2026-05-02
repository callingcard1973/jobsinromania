#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
EURES Germany Enricher - Scrape emails from company websites

Processes EURES Germany contacts that have website URLs but no emails.
Uses impressum/contact page scraping.
"""
import sys
sys.path.insert(0, "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED")

import csv
import json
import re
import time
import random
import logging
import argparse
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
import requests

from skills_common import to_ascii

# Paths
SOURCE = Path("/mnt/hdd/SCRAPER_DATA/csv/EURES/Germany/Germany_contacts_50.csv")
OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/GERMANY_ENRICHED")
OUTPUT = OUTPUT_DIR / "EURES_Germany_ENRICHED.csv"
CACHE = OUTPUT_DIR / "eures_domain_cache.json"
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS/enricher")

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / f"eures_de_{datetime.now():%Y%m%d}.log")
    ]
)
logger = logging.getLogger(__name__)

# Email regex
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

def load_cache():
    if CACHE.exists():
        with open(CACHE) as f:
            return json.load(f)
    return {}

def save_cache(cache):
    with open(CACHE, "w") as f:
        json.dump(cache, f)

def extract_domain(url):
    if not url:
        return None
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        return parsed.netloc.lower().replace("www.", "")
    except:
        return None

def find_email_on_page(url, timeout=10):
    """Scrape a URL and find email addresses."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    try:
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if r.status_code == 200:
            emails = EMAIL_RE.findall(r.text)
            # Filter out common non-company emails
            valid = [e for e in emails if not any(x in e.lower() for x in 
                ["example.", "domain.", "email.", "test.", ".png", ".jpg", ".gif"])]
            return list(set(valid))[:3]  # Max 3 emails
    except:
        pass
    return []

def scrape_impressum(base_url):
    """Try to find and scrape impressum/contact page."""
    domain = extract_domain(base_url)
    if not domain:
        return []
    
    # Common impressum/contact paths
    paths = [
        "/impressum", "/kontakt", "/contact", "/about", "/ueber-uns",
        "/impressum.html", "/kontakt.html", "/imprint"
    ]
    
    base = f"https://{domain}"
    
    # First try base URL
    emails = find_email_on_page(base)
    if emails:
        return emails
    
    # Try impressum paths
    for path in paths:
        try:
            emails = find_email_on_page(f"{base}{path}")
            if emails:
                return emails
        except:
            pass
        time.sleep(0.5)
    
    return []

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=500, help="Max websites to process")
    parser.add_argument("--status", action="store_true", help="Show status")
    args = parser.parse_args()
    
    cache = load_cache()
    
    if args.status:
        print(f"Cache: {len(cache)} domains")
        found = sum(1 for v in cache.values() if v.get("emails"))
        print(f"Found emails: {found}")
        return
    
    # Load source
    with open(SOURCE) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    logger.info(f"Loaded {len(rows)} rows from EURES Germany")
    
    # Find rows with website but not in cache
    to_process = []
    for row in rows:
        website = row.get("company_website", "").strip()
        domain = extract_domain(website)
        if domain and domain not in cache:
            to_process.append((domain, website))
    
    # Dedupe by domain
    to_process = list(dict(to_process).items())
    logger.info(f"To process: {len(to_process)} unique domains (limit: {args.limit})")
    
    # Process
    found = 0
    for i, (domain, website) in enumerate(to_process[:args.limit]):
        if i > 0 and i % 50 == 0:
            logger.info(f"Progress: {i}/{min(len(to_process), args.limit)}, found: {found}")
            save_cache(cache)
        
        emails = scrape_impressum(website)
        cache[domain] = {
            "emails": emails,
            "website": website,
            "checked": datetime.now().isoformat()
        }
        
        if emails:
            found += 1
            logger.info(f"  {domain}: {emails[0]}")
        
        time.sleep(random.uniform(1, 2))
    
    save_cache(cache)
    
    # Write output CSV
    with open(OUTPUT, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["domain", "email", "website", "checked"])
        for domain, data in cache.items():
            if data.get("emails"):
                writer.writerow([
                    domain,
                    data["emails"][0],
                    data.get("website", ""),
                    data.get("checked", "")
                ])
    
    logger.info(f"Done! Processed {min(len(to_process), args.limit)}, found {found} emails")
    logger.info(f"Total in cache: {len(cache)}, with emails: {sum(1 for v in cache.values() if v.get(emails))}")

if __name__ == "__main__":
    main()
