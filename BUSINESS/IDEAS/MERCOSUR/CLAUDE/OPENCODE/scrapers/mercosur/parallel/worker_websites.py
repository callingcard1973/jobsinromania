#!/usr/bin/env python3
"""
Worker 1: Website Scraper
Extracts contact info from company websites using ThreadPoolExecutor
Target: 267 companies with websites missing email
"""

import argparse
import csv
import json
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import (
    CONTACT_PAGE_PATTERNS,
    EMAIL_PATTERNS,
    EXISTING_DATA,
    OUTPUT_BASE,
    PHONE_PATTERNS,
    REQUEST_DELAY,
    TIMEOUTS,
    USER_AGENTS,
)

OUTPUT_DIR = OUTPUT_BASE / "websites"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [websites] {msg}")


def get_session() -> requests.Session:
    """Create session with random user agent"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8,pt;q=0.7",
    })
    return session


def normalize_url(url: str) -> str:
    """Ensure URL has scheme"""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def extract_emails(text: str) -> List[str]:
    """Extract emails from text"""
    emails = set()
    for pattern in EMAIL_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            email = match if isinstance(match, str) else match[0]
            email = email.lower().strip()
            # Filter out common non-emails
            if "@" in email and not any(x in email for x in [
                "example.com", "your-email", "email@", "test@",
                ".png", ".jpg", ".gif", "wixpress", "sentry"
            ]):
                emails.add(email)
    return list(emails)


def extract_phones(text: str) -> List[str]:
    """Extract phone numbers from text"""
    phones = set()
    for pattern in PHONE_PATTERNS:
        matches = re.findall(pattern, text)
        for match in matches:
            phone = re.sub(r"[^\d+]", "", match)
            if len(phone) >= 10:
                phones.add(phone)
    return list(phones)


def scrape_website(company: Dict) -> Dict:
    """Scrape a single website for contact info"""
    url = normalize_url(company.get("website", ""))
    if not url:
        return {**company, "scrape_status": "no_url"}

    session = get_session()
    result = {**company, "scrape_status": "pending"}
    found_emails = []
    found_phones = []

    # URLs to try
    urls_to_try = [url]

    # Parse domain for contact page URLs
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    for pattern in CONTACT_PAGE_PATTERNS[:5]:  # Top 5 patterns
        urls_to_try.append(urljoin(base_url, pattern))

    # Try www variant if not present
    if "www." not in parsed.netloc:
        www_url = f"{parsed.scheme}://www.{parsed.netloc}"
        urls_to_try.insert(1, www_url)

    for try_url in urls_to_try:
        try:
            time.sleep(random.uniform(*REQUEST_DELAY))

            response = session.get(
                try_url,
                timeout=TIMEOUTS["request"],
                allow_redirects=True,
            )

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")

                # Extract from mailto links
                for mailto in soup.find_all("a", href=re.compile(r"^mailto:")):
                    href = mailto.get("href", "")
                    email = href.replace("mailto:", "").split("?")[0].strip()
                    if "@" in email:
                        found_emails.append(email.lower())

                # Extract from tel links
                for tel in soup.find_all("a", href=re.compile(r"^tel:")):
                    href = tel.get("href", "")
                    phone = re.sub(r"[^\d+]", "", href.replace("tel:", ""))
                    if len(phone) >= 10:
                        found_phones.append(phone)

                # Extract from page text
                text = soup.get_text()
                found_emails.extend(extract_emails(text))
                found_phones.extend(extract_phones(text))

                # Also check meta tags
                for meta in soup.find_all("meta", {"name": re.compile(r"contact|email", re.I)}):
                    content = meta.get("content", "")
                    found_emails.extend(extract_emails(content))

        except requests.exceptions.Timeout:
            result["scrape_status"] = "timeout"
        except requests.exceptions.SSLError:
            # Try http instead
            try:
                http_url = try_url.replace("https://", "http://")
                response = session.get(http_url, timeout=TIMEOUTS["request"])
                if response.status_code == 200:
                    found_emails.extend(extract_emails(response.text))
            except:
                pass
        except Exception as e:
            result["scrape_error"] = str(e)[:100]

    # Deduplicate and update
    found_emails = list(set(found_emails))
    found_phones = list(set(found_phones))

    if found_emails:
        # Prefer info@, contact@, export@ addresses
        priority = ["export", "comercial", "ventas", "sales", "info", "contact"]
        found_emails.sort(key=lambda e: next(
            (i for i, p in enumerate(priority) if p in e.lower()), 99
        ))
        result["email"] = found_emails[0]
        result["all_emails"] = found_emails
        result["scrape_status"] = "success"

    if found_phones:
        result["phone"] = found_phones[0]
        result["all_phones"] = found_phones

    if not found_emails and not found_phones:
        result["scrape_status"] = "no_contact"

    result["scraped_at"] = datetime.now().isoformat()

    return result


def load_existing_data() -> List[Dict]:
    """Load existing company data"""
    # Try JSON first
    json_files = list(EXISTING_DATA.glob("mercosur_*.json"))
    if json_files:
        latest = max(json_files, key=lambda f: f.stat().st_mtime)
        log(f"Loading from {latest}")
        with open(latest) as f:
            return json.load(f)

    # Try CSV
    csv_files = list(EXISTING_DATA.glob("mercosur_*.csv"))
    if csv_files:
        latest = max(csv_files, key=lambda f: f.stat().st_mtime)
        log(f"Loading from {latest}")
        with open(latest, newline="") as f:
            return list(csv.DictReader(f))

    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=10)
    parser.add_argument("--limit", type=int, help="Limit companies to process")
    parser.add_argument("--test", action="store_true", help="Test mode - 3 companies")
    args = parser.parse_args()

    log("Starting website scraper")

    # Load existing data
    companies = load_existing_data()
    log(f"Loaded {len(companies)} companies")

    # Filter to those with website but missing email
    targets = [
        c for c in companies
        if c.get("website") and not c.get("email")
    ]
    log(f"Found {len(targets)} companies with website, missing email")

    if args.test:
        targets = targets[:3]
        log("TEST MODE: Processing 3 companies")
    elif args.limit:
        targets = targets[:args.limit]
        log(f"Limited to {len(targets)} companies")

    if not targets:
        log("No targets to process")
        return

    # Process with thread pool
    results = []
    success = 0
    emails_found = 0

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(scrape_website, company): company
            for company in targets
        }

        for i, future in enumerate(as_completed(futures)):
            company = futures[future]
            try:
                result = future.result()
                results.append(result)

                if result.get("scrape_status") == "success":
                    success += 1
                    if result.get("email"):
                        emails_found += 1
                        log(f"[{i+1}/{len(targets)}] {company.get('name', 'Unknown')}: {result['email']}")
                else:
                    if (i + 1) % 50 == 0:
                        log(f"[{i+1}/{len(targets)}] Progress...")

            except Exception as e:
                log(f"Error processing {company.get('name', 'Unknown')}: {e}")
                results.append({**company, "scrape_status": "exception", "error": str(e)})

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON output
    json_file = OUTPUT_DIR / f"websites_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2)

    # CSV output (only those with new data)
    csv_file = OUTPUT_DIR / f"websites_{timestamp}.csv"
    enriched = [r for r in results if r.get("scrape_status") == "success"]

    if enriched:
        with open(csv_file, "w", newline="") as f:
            fieldnames = ["name", "country", "sector", "website", "email", "phone", "source", "scraped_at"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(enriched)

    # Summary
    log("=" * 50)
    log("SUMMARY")
    log(f"Total processed: {len(targets)}")
    log(f"Success: {success}")
    log(f"Emails found: {emails_found}")
    log(f"JSON: {json_file}")
    log(f"CSV: {csv_file}")
    log("=" * 50)


if __name__ == "__main__":
    main()
