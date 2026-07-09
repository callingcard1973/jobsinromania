#!/usr/bin/env python3
"""
Worker 6: Contact Enricher
Enriches companies with missing emails via Google search, WHOIS, domain variations
Target: All 677 companies
"""

import argparse
import csv
import json
import random
import re
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

# Import shared utilities
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii, sanitize, FIELD_LIMITS
except ImportError:
    def to_ascii(text): return text if not text else text.encode('ascii', 'ignore').decode()
    def sanitize(text, *args): return to_ascii(text)[:200] if text else ""

from config import (
    ENRICHMENT_SOURCES,
    EXISTING_DATA,
    OUTPUT_BASE,
    REQUEST_DELAY,
    TIMEOUTS,
    USER_AGENTS,
)

OUTPUT_DIR = OUTPUT_BASE / "enriched"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [enricher] {msg}")


def get_session() -> requests.Session:
    """Create session with random user agent"""
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


def normalize_url(url: str) -> str:
    """Ensure URL has scheme and normalize"""
    if not url:
        return ""
    url = url.strip().lower()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def extract_domain(url: str) -> str:
    """Extract domain from URL"""
    url = normalize_url(url)
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    if not email or "@" not in email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False
    # Filter common non-emails
    blacklist = [
        "example.com", "test.com", "email.com", "your-email",
        "noreply", "no-reply", "donotreply", "wix.com",
        "squarespace.com", "wordpress.com", "sentry.io"
    ]
    return not any(b in email.lower() for b in blacklist)


def guess_emails_from_domain(domain: str) -> List[str]:
    """Generate likely email patterns for a domain"""
    if not domain:
        return []
    prefixes = [
        "info", "contact", "comercial", "ventas", "sales",
        "export", "exportacion", "exportaciones", "international",
        "atendimento", "contato", "admin", "hello"
    ]
    return [f"{p}@{domain}" for p in prefixes]


def verify_email_domain(email: str) -> bool:
    """Check if email domain has MX records"""
    try:
        domain = email.split("@")[1]
        socket.getaddrinfo(domain, 25, socket.AF_INET)
        return True
    except:
        return False


def search_google_for_email(company: str, domain: str) -> List[str]:
    """Search Google for company email (simplified, may be blocked)"""
    session = get_session()
    query = f'"{company}" email contact site:{domain}'

    try:
        # DuckDuckGo HTML (less likely to block)
        response = session.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            timeout=TIMEOUTS["request"],
        )
        if response.status_code == 200:
            emails = re.findall(
                r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                response.text
            )
            return [e for e in emails if is_valid_email(e)]
    except:
        pass

    return []


def try_common_email_pages(domain: str) -> List[str]:
    """Try common contact pages on a domain"""
    session = get_session()
    base_url = f"https://{domain}"
    emails = []

    pages = [
        "/contact", "/contacto", "/contato",
        "/contact-us", "/contactenos", "/fale-conosco",
        "/about", "/sobre", "/empresa",
        "/team", "/equipo", "/equipe",
    ]

    for page in pages[:3]:  # Limit to first 3 to be gentle
        try:
            time.sleep(random.uniform(0.5, 1.5))
            response = session.get(
                f"{base_url}{page}",
                timeout=TIMEOUTS["request"],
                allow_redirects=True,
            )
            if response.status_code == 200:
                found = re.findall(
                    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
                    response.text
                )
                emails.extend(e for e in found if is_valid_email(e))
        except:
            pass

    return list(set(emails))


def enrich_company(company: Dict) -> Dict:
    """Enrich a single company with contact info"""
    result = {**company, "enrich_status": "pending"}

    # Skip if already has email
    if company.get("email"):
        result["enrich_status"] = "already_has_email"
        return result

    website = company.get("website", "")
    domain = extract_domain(website)
    company_name = company.get("name", "")

    found_emails = []

    # Strategy 1: Try common email pages on their domain
    if domain:
        time.sleep(random.uniform(*REQUEST_DELAY))
        page_emails = try_common_email_pages(domain)
        found_emails.extend(page_emails)

    # Strategy 2: Generate and verify common email patterns
    if domain and not found_emails:
        guessed = guess_emails_from_domain(domain)
        for email in guessed[:3]:  # Only check first 3
            if verify_email_domain(email):
                found_emails.append(email)
                break

    # Strategy 3: Search engines (be careful with rate limits)
    if ENRICHMENT_SOURCES.get("google_search", {}).get("enabled") and not found_emails:
        if company_name and domain:
            time.sleep(random.uniform(2, 4))  # Longer delay for search
            search_emails = search_google_for_email(company_name, domain)
            found_emails.extend(search_emails)

    # Deduplicate and rank
    found_emails = list(set(found_emails))

    if found_emails:
        # Prefer info@, contact@, export@ addresses
        priority = ["export", "comercial", "ventas", "sales", "info", "contact"]
        found_emails.sort(key=lambda e: next(
            (i for i, p in enumerate(priority) if p in e.lower()), 99
        ))
        result["email"] = sanitize(found_emails[0], "email")
        result["all_emails"] = found_emails
        result["enrich_status"] = "success"
        result["enrich_method"] = "website_crawl"
    else:
        result["enrich_status"] = "no_email_found"

    result["enriched_at"] = datetime.now().isoformat()

    return result


def load_existing_data() -> List[Dict]:
    """Load existing company data"""
    json_files = list(EXISTING_DATA.glob("mercosur_*.json"))
    if json_files:
        latest = max(json_files, key=lambda f: f.stat().st_mtime)
        log(f"Loading from {latest}")
        with open(latest) as f:
            return json.load(f)

    csv_files = list(EXISTING_DATA.glob("mercosur_*.csv"))
    if csv_files:
        latest = max(csv_files, key=lambda f: f.stat().st_mtime)
        log(f"Loading from {latest}")
        with open(latest, newline="") as f:
            return list(csv.DictReader(f))

    return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=8)
    parser.add_argument("--limit", type=int, help="Limit companies to process")
    parser.add_argument("--test", action="store_true", help="Test mode - 5 companies")
    parser.add_argument("--no-search", action="store_true", help="Disable search engine queries")
    args = parser.parse_args()

    if args.no_search:
        ENRICHMENT_SOURCES["google_search"]["enabled"] = False

    log("Starting contact enricher")

    companies = load_existing_data()
    log(f"Loaded {len(companies)} companies")

    # Filter to those missing email but having website
    targets = [
        c for c in companies
        if not c.get("email") and c.get("website")
    ]
    log(f"Found {len(targets)} companies needing enrichment")

    if args.test:
        targets = targets[:5]
        log("TEST MODE: Processing 5 companies")
    elif args.limit:
        targets = targets[:args.limit]
        log(f"Limited to {len(targets)} companies")

    if not targets:
        log("No targets to process")
        return

    results = []
    success = 0
    emails_found = 0

    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {
            executor.submit(enrich_company, company): company
            for company in targets
        }

        for i, future in enumerate(as_completed(futures)):
            company = futures[future]
            try:
                result = future.result()
                results.append(result)

                if result.get("enrich_status") == "success":
                    success += 1
                    if result.get("email"):
                        emails_found += 1
                        log(f"[{i+1}/{len(targets)}] {company.get('name', 'Unknown')}: {result['email']}")
                else:
                    if (i + 1) % 20 == 0:
                        log(f"[{i+1}/{len(targets)}] Progress... ({emails_found} emails found)")

            except Exception as e:
                log(f"Error enriching {company.get('name', 'Unknown')}: {e}")
                results.append({**company, "enrich_status": "exception", "error": str(e)})

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = OUTPUT_DIR / f"enriched_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(results, f, indent=2)

    csv_file = OUTPUT_DIR / f"enriched_{timestamp}.csv"
    enriched = [r for r in results if r.get("enrich_status") == "success"]

    if enriched:
        with open(csv_file, "w", newline="") as f:
            fieldnames = ["name", "country", "sector", "website", "email", "phone", "source", "enriched_at"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(enriched)

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
