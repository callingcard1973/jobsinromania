#!/usr/bin/env python3
"""
Worker 5: Trade Show Exhibitors
Extracts exhibitor lists from trade shows using Selenium
Targets: APAS Show, Fispal, Mercoagro, Expoaladi, Fenavinho
"""

import argparse
import csv
import json
import random
import re
import time
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

from config import OUTPUT_BASE, REQUEST_DELAY, TIMEOUTS, TRADE_SHOWS, USER_AGENTS

# Selenium imports
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

OUTPUT_DIR = OUTPUT_BASE / "tradeshows"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [tradeshows] {msg}")


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
        "example.com", "test.com", "wix", "wordpress", "sentry"
    ])]


def scrape_with_requests(show_key: str, show: Dict) -> List[Dict]:
    """Try scraping with plain requests first"""
    session = get_session()
    results = []

    try:
        response = session.get(show["url"], timeout=TIMEOUTS["request"])
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        selectors = show.get("selectors", {})

        exhibitor_selector = selectors.get("exhibitor_list", ".exhibitor, .expositor, .company")
        exhibitors = soup.select(exhibitor_selector)

        if not exhibitors:
            for pattern in [".exhibitor", ".expositor", ".company", ".card", "article", ".item"]:
                exhibitors = soup.select(pattern)
                if exhibitors:
                    break

        for exhibitor_elem in exhibitors:
            company = {
                "name": "",
                "website": "",
                "email": "",
                "stand": "",
                "country": show.get("country", ""),
                "sector": show.get("sector", ""),
                "source": show.get("name", show_key),
            }

            name_selector = selectors.get("name", "h3, h4, .name, .title")
            name_elem = exhibitor_elem.select_one(name_selector)
            if name_elem:
                company["name"] = sanitize(name_elem.get_text(strip=True), "company")

            stand_selector = selectors.get("stand", ".stand, .booth, .location")
            stand_elem = exhibitor_elem.select_one(stand_selector)
            if stand_elem:
                company["stand"] = sanitize(stand_elem.get_text(strip=True), "short")

            for link in exhibitor_elem.select("a[href*='http']"):
                href = link.get("href", "")
                if href.startswith("http") and show_key not in href.lower():
                    if not any(x in href.lower() for x in ["facebook", "twitter", "linkedin"]):
                        company["website"] = href
                        break

            for mailto in exhibitor_elem.select("a[href^='mailto:']"):
                href = mailto.get("href", "")
                email = href.replace("mailto:", "").split("?")[0].strip()
                if "@" in email:
                    company["email"] = sanitize(email.lower(), "email")
                    break

            if not company["email"]:
                text = exhibitor_elem.get_text()
                emails = extract_emails(text)
                if emails:
                    company["email"] = sanitize(emails[0], "email")

            if company["name"]:
                results.append(company)

    except Exception as e:
        log(f"Requests error for {show_key}: {e}")

    return results


def scrape_with_selenium(show_key: str, show: Dict, driver: webdriver.Chrome) -> List[Dict]:
    """Scrape with Selenium for JS-rendered pages"""
    results = []

    try:
        driver.get(show["url"])
        time.sleep(3)

        # Wait for content
        try:
            WebDriverWait(driver, TIMEOUTS["selenium_wait"]).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
        except:
            pass

        # Scroll to load lazy content
        for _ in range(3):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

        # Click "load more" buttons if present
        for _ in range(5):
            try:
                load_more = driver.find_element(By.XPATH,
                    "//button[contains(text(), 'Ver mais') or contains(text(), 'Load more') or contains(text(), 'Mais')]")
                load_more.click()
                time.sleep(2)
            except:
                break

        soup = BeautifulSoup(driver.page_source, "html.parser")
        selectors = show.get("selectors", {})

        exhibitor_selector = selectors.get("exhibitor_list", ".exhibitor, .expositor, .company")
        exhibitors = soup.select(exhibitor_selector)

        if not exhibitors or len(exhibitors) < 3:
            for pattern in [".exhibitor", ".expositor", ".company", ".card", "article", ".item", "li.list-item"]:
                exhibitors = soup.select(pattern)
                if len(exhibitors) > 3:
                    break

        for exhibitor_elem in exhibitors:
            company = {
                "name": "",
                "website": "",
                "email": "",
                "stand": "",
                "country": show.get("country", ""),
                "sector": show.get("sector", ""),
                "source": show.get("name", show_key),
            }

            name_selector = selectors.get("name", "h3, h4, .name, .title")
            name_elem = exhibitor_elem.select_one(name_selector)
            if name_elem:
                company["name"] = sanitize(name_elem.get_text(strip=True), "company")

            for link in exhibitor_elem.select("a[href*='http']"):
                href = link.get("href", "")
                if href.startswith("http") and show_key not in href.lower():
                    if not any(x in href.lower() for x in ["facebook", "twitter", "linkedin", "instagram"]):
                        company["website"] = href
                        break

            for mailto in exhibitor_elem.select("a[href^='mailto:']"):
                href = mailto.get("href", "")
                email = href.replace("mailto:", "").split("?")[0].strip()
                if "@" in email:
                    company["email"] = sanitize(email.lower(), "email")
                    break

            if not company["email"]:
                emails = extract_emails(exhibitor_elem.get_text())
                if emails:
                    company["email"] = sanitize(emails[0], "email")

            if company["name"] and len(company["name"]) > 2:
                results.append(company)

    except Exception as e:
        log(f"Selenium error for {show_key}: {e}")

    return results


def scrape_trade_show(show_key: str, show: Dict, use_selenium: bool = False) -> List[Dict]:
    """Scrape a single trade show"""
    log(f"Scraping {show.get('name', show_key)}...")

    results = scrape_with_requests(show_key, show)

    if len(results) < 10 and use_selenium and SELENIUM_AVAILABLE:
        log(f"Trying Selenium for {show_key} (only {len(results)} from requests)")
        driver = get_driver()
        if driver:
            try:
                selenium_results = scrape_with_selenium(show_key, show, driver)
                if len(selenium_results) > len(results):
                    results = selenium_results
            finally:
                driver.quit()

    log(f"{show_key}: Found {len(results)} exhibitors")
    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=3)
    parser.add_argument("--selenium", action="store_true", help="Enable Selenium")
    parser.add_argument("--show", type=str, help="Scrape specific show")
    parser.add_argument("--test", action="store_true", help="Test mode")
    args = parser.parse_args()

    log("Starting trade show scraper")
    log(f"Selenium available: {SELENIUM_AVAILABLE}")

    if args.show:
        if args.show not in TRADE_SHOWS:
            log(f"Unknown show: {args.show}")
            log(f"Available: {', '.join(TRADE_SHOWS.keys())}")
            return
        targets = {args.show: TRADE_SHOWS[args.show]}
    elif args.test:
        targets = dict(list(TRADE_SHOWS.items())[:2])
        log("TEST MODE: 2 shows")
    else:
        targets = TRADE_SHOWS

    log(f"Scraping {len(targets)} trade shows")

    all_results = []

    for show_key, show in targets.items():
        time.sleep(random.uniform(*REQUEST_DELAY))
        results = scrape_trade_show(show_key, show, use_selenium=args.selenium)
        all_results.extend(results)

    # Deduplicate
    seen = set()
    unique_results = []
    for r in all_results:
        key = r.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique_results.append(r)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = OUTPUT_DIR / f"tradeshows_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(unique_results, f, indent=2)

    csv_file = OUTPUT_DIR / f"tradeshows_{timestamp}.csv"
    if unique_results:
        with open(csv_file, "w", newline="") as f:
            fieldnames = ["name", "country", "sector", "website", "email", "stand", "source"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(unique_results)

    with_email = sum(1 for r in unique_results if r.get("email"))
    with_website = sum(1 for r in unique_results if r.get("website"))

    log("=" * 50)
    log("SUMMARY")
    log(f"Total exhibitors: {len(unique_results)}")
    log(f"With email: {with_email}")
    log(f"With website: {with_website}")
    log(f"JSON: {json_file}")
    log(f"CSV: {csv_file}")
    log("=" * 50)


if __name__ == "__main__":
    main()
