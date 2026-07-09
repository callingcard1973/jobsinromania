#!/usr/bin/env python3
"""
Worker 3: Association Members Scraper
Extracts member lists from trade associations using Selenium for JS-rendered pages
Targets: ABIEC, ABIOVE, ABPA, IPCVA, Wines of Argentina, SalmonChile, ASOEX, ABEMEL
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

import requests
from bs4 import BeautifulSoup

# Import shared utilities
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii, sanitize
except ImportError:
    def to_ascii(text): return text if not text else text.encode('ascii', 'ignore').decode()
    def sanitize(text, *args): return to_ascii(text)[:200] if text else ""

from config import ASSOCIATIONS, OUTPUT_BASE, REQUEST_DELAY, TIMEOUTS, USER_AGENTS

# Selenium imports (optional - graceful fallback)
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

OUTPUT_DIR = OUTPUT_BASE / "associations"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [associations] {msg}")


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })
    return session


def get_driver() -> Optional[webdriver.Chrome]:
    """Create headless Chrome driver"""
    if not SELENIUM_AVAILABLE:
        return None

    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(TIMEOUTS["page_load"])
        return driver
    except Exception as e:
        log(f"Failed to create driver: {e}")
        return None


def extract_emails(text: str) -> List[str]:
    """Extract emails from text"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(pattern, text)
    return [e.lower() for e in emails if not any(x in e.lower() for x in [
        "example.com", "test.com", "wix", "wordpress"
    ])]


def scrape_with_requests(assoc_key: str, assoc: Dict) -> List[Dict]:
    """Try scraping with plain requests first"""
    session = get_session()
    results = []

    try:
        response = session.get(assoc["url"], timeout=TIMEOUTS["request"])
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        selectors = assoc.get("selectors", {})

        # Try to find company elements
        company_selector = selectors.get("company_list", ".member, .company, .associado")
        companies = soup.select(company_selector)

        if not companies:
            # Try common patterns
            for pattern in [".member", ".company", ".associado", ".partner", "article", ".card"]:
                companies = soup.select(pattern)
                if companies:
                    break

        for company_elem in companies:
            company = {
                "name": "",
                "website": "",
                "email": "",
                "country": assoc.get("country", ""),
                "sector": assoc.get("sector", ""),
                "source": assoc.get("name", assoc_key),
            }

            # Extract name
            name_selector = selectors.get("name", "h3, h4, .name, .title")
            name_elem = company_elem.select_one(name_selector)
            if name_elem:
                company["name"] = sanitize(name_elem.get_text(strip=True), "company")

            # Extract website
            website_selector = selectors.get("website", "a[href*='http']")
            for link in company_elem.select(website_selector):
                href = link.get("href", "")
                if href.startswith("http") and assoc_key not in href.lower():
                    company["website"] = href
                    break

            # Extract email
            for mailto in company_elem.select("a[href^='mailto:']"):
                href = mailto.get("href", "")
                email = href.replace("mailto:", "").split("?")[0].strip()
                if "@" in email:
                    company["email"] = sanitize(email.lower(), "email")
                    break

            if not company["email"]:
                text = company_elem.get_text()
                emails = extract_emails(text)
                if emails:
                    company["email"] = sanitize(emails[0], "email")

            if company["name"]:
                results.append(company)

    except Exception as e:
        log(f"Requests error for {assoc_key}: {e}")

    return results


def scrape_with_selenium(assoc_key: str, assoc: Dict, driver: webdriver.Chrome) -> List[Dict]:
    """Scrape with Selenium for JS-rendered pages"""
    results = []

    try:
        driver.get(assoc["url"])
        time.sleep(3)  # Wait for JS

        # Wait for content
        try:
            WebDriverWait(driver, TIMEOUTS["selenium_wait"]).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass

        # Scroll to load lazy content
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        selectors = assoc.get("selectors", {})

        company_selector = selectors.get("company_list", ".member, .company, .associado")
        companies = soup.select(company_selector)

        if not companies:
            for pattern in [".member", ".company", ".associado", ".partner", "article", ".card", "li"]:
                companies = soup.select(pattern)
                if len(companies) > 3:
                    break

        for company_elem in companies:
            company = {
                "name": "",
                "website": "",
                "email": "",
                "country": assoc.get("country", ""),
                "sector": assoc.get("sector", ""),
                "source": assoc.get("name", assoc_key),
            }

            name_selector = selectors.get("name", "h3, h4, .name, .title")
            name_elem = company_elem.select_one(name_selector)
            if name_elem:
                company["name"] = sanitize(name_elem.get_text(strip=True), "company")

            for link in company_elem.select("a[href*='http']"):
                href = link.get("href", "")
                if href.startswith("http") and assoc_key not in href.lower():
                    company["website"] = href
                    break

            for mailto in company_elem.select("a[href^='mailto:']"):
                href = mailto.get("href", "")
                email = href.replace("mailto:", "").split("?")[0].strip()
                if "@" in email:
                    company["email"] = sanitize(email.lower(), "email")
                    break

            if not company["email"]:
                emails = extract_emails(company_elem.get_text())
                if emails:
                    company["email"] = sanitize(emails[0], "email")

            if company["name"] and len(company["name"]) > 2:
                results.append(company)

    except Exception as e:
        log(f"Selenium error for {assoc_key}: {e}")

    return results


def scrape_association(assoc_key: str, assoc: Dict, use_selenium: bool = False) -> List[Dict]:
    """Scrape a single association"""
    log(f"Scraping {assoc.get('name', assoc_key)}...")

    # Try requests first
    results = scrape_with_requests(assoc_key, assoc)

    # If few results and selenium available, try selenium
    if len(results) < 5 and use_selenium and SELENIUM_AVAILABLE:
        log(f"Trying Selenium for {assoc_key} (only {len(results)} from requests)")
        driver = get_driver()
        if driver:
            try:
                selenium_results = scrape_with_selenium(assoc_key, assoc, driver)
                if len(selenium_results) > len(results):
                    results = selenium_results
            finally:
                driver.quit()

    log(f"{assoc_key}: Found {len(results)} companies")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=5)
    parser.add_argument("--selenium", action="store_true", help="Enable Selenium")
    parser.add_argument("--association", type=str, help="Scrape specific association")
    parser.add_argument("--test", action="store_true", help="Test mode - 2 associations")
    args = parser.parse_args()

    log("Starting association scraper")
    log(f"Selenium available: {SELENIUM_AVAILABLE}")

    # Select associations to scrape
    if args.association:
        if args.association not in ASSOCIATIONS:
            log(f"Unknown association: {args.association}")
            log(f"Available: {', '.join(ASSOCIATIONS.keys())}")
            return
        targets = {args.association: ASSOCIATIONS[args.association]}
    elif args.test:
        targets = dict(list(ASSOCIATIONS.items())[:2])
        log("TEST MODE: 2 associations")
    else:
        targets = ASSOCIATIONS

    log(f"Scraping {len(targets)} associations")

    all_results = []

    # Sequential scraping (associations have rate limits)
    for assoc_key, assoc in targets.items():
        time.sleep(random.uniform(*REQUEST_DELAY))
        results = scrape_association(assoc_key, assoc, use_selenium=args.selenium)
        all_results.extend(results)

    # Deduplicate by name
    seen = set()
    unique_results = []
    for r in all_results:
        key = r.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique_results.append(r)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = OUTPUT_DIR / f"associations_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(unique_results, f, indent=2)

    csv_file = OUTPUT_DIR / f"associations_{timestamp}.csv"
    if unique_results:
        with open(csv_file, "w", newline="") as f:
            fieldnames = ["name", "country", "sector", "website", "email", "source"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(unique_results)

    # Summary
    with_email = sum(1 for r in unique_results if r.get("email"))
    with_website = sum(1 for r in unique_results if r.get("website"))

    log("=" * 50)
    log("SUMMARY")
    log(f"Total companies: {len(unique_results)}")
    log(f"With email: {with_email}")
    log(f"With website: {with_website}")
    log(f"JSON: {json_file}")
    log(f"CSV: {csv_file}")
    log("=" * 50)


if __name__ == "__main__":
    main()
