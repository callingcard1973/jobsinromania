#!/usr/bin/env python3
"""
Worker 2: Government API Discovery
Probes government portals for API endpoints and extracts exporter data
Targets: APEX Brasil, ProChile, Uruguay XXI, Argentina Exporta, REDIEX Paraguay
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
from typing import Dict, List, Optional, Any
from urllib.parse import urljoin

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

from config import GOV_APIS, OUTPUT_BASE, REQUEST_DELAY, TIMEOUTS, USER_AGENTS

OUTPUT_DIR = OUTPUT_BASE / "govapis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [govapis] {msg}")


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "application/json, text/html, */*",
        "Accept-Language": "en-US,en;q=0.9,es;q=0.8,pt;q=0.7",
    })
    return session


def probe_endpoint(session: requests.Session, url: str) -> Optional[Dict]:
    """Probe an endpoint for JSON data"""
    try:
        response = session.get(url, timeout=TIMEOUTS["request"])

        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")

            # Check if JSON
            if "json" in content_type.lower():
                try:
                    data = response.json()
                    return {"type": "json", "data": data, "url": url}
                except:
                    pass

            # Check if HTML with embedded JSON
            if "html" in content_type.lower():
                text = response.text

                # Look for JSON in script tags
                json_patterns = [
                    r'var\s+\w+\s*=\s*(\[[\s\S]*?\]);',
                    r'data\s*:\s*(\[[\s\S]*?\])',
                    r'"items"\s*:\s*(\[[\s\S]*?\])',
                    r'exportadores\s*=\s*(\[[\s\S]*?\])',
                ]

                for pattern in json_patterns:
                    matches = re.findall(pattern, text)
                    for match in matches:
                        try:
                            data = json.loads(match)
                            if isinstance(data, list) and len(data) > 5:
                                return {"type": "embedded_json", "data": data, "url": url}
                        except:
                            pass

                # Return HTML for parsing
                return {"type": "html", "data": text, "url": url}

    except requests.exceptions.Timeout:
        log(f"Timeout: {url}")
    except Exception as e:
        log(f"Error probing {url}: {str(e)[:50]}")

    return None


def extract_from_json(data: Any, api_name: str, country: str) -> List[Dict]:
    """Extract company records from JSON data"""
    results = []

    def process_item(item: Dict) -> Optional[Dict]:
        if not isinstance(item, dict):
            return None

        # Common field mappings
        name_fields = ["name", "nome", "empresa", "company", "razao_social", "razonSocial"]
        email_fields = ["email", "correo", "e-mail", "emailContacto"]
        website_fields = ["website", "sitio", "url", "site", "pagina_web"]
        sector_fields = ["sector", "setor", "rubro", "industria", "industry"]

        company = {
            "name": "",
            "email": "",
            "website": "",
            "sector": "",
            "country": country,
            "source": api_name,
        }

        for field in name_fields:
            if field in item and item[field]:
                company["name"] = sanitize(str(item[field]), "company")
                break

        for field in email_fields:
            if field in item and item[field] and "@" in str(item[field]):
                company["email"] = sanitize(str(item[field]).lower(), "email")
                break

        for field in website_fields:
            if field in item and item[field]:
                website = str(item[field])
                if website.startswith("http"):
                    company["website"] = website
                break

        for field in sector_fields:
            if field in item and item[field]:
                company["sector"] = sanitize(str(item[field]), "short")
                break

        return company if company["name"] else None

    # Handle different JSON structures
    if isinstance(data, list):
        for item in data:
            company = process_item(item)
            if company:
                results.append(company)

    elif isinstance(data, dict):
        # Look for list in common keys
        for key in ["data", "items", "results", "empresas", "exportadores", "records"]:
            if key in data and isinstance(data[key], list):
                for item in data[key]:
                    company = process_item(item)
                    if company:
                        results.append(company)
                break

    return results


def extract_from_html(html: str, api_name: str, country: str) -> List[Dict]:
    """Extract company data from HTML"""
    results = []
    soup = BeautifulSoup(html, "html.parser")

    # Try common company list patterns
    selectors = [
        ".empresa", ".company", ".exporter", ".exportador",
        ".member", ".item", "article", ".card",
        "table tr", ".list-item"
    ]

    for selector in selectors:
        elements = soup.select(selector)
        if len(elements) > 5:
            for elem in elements:
                company = {
                    "name": "",
                    "email": "",
                    "website": "",
                    "sector": "",
                    "country": country,
                    "source": api_name,
                }

                # Name
                for name_sel in ["h3", "h4", ".name", ".title", "strong", "td:first-child"]:
                    name_elem = elem.select_one(name_sel)
                    if name_elem:
                        name = name_elem.get_text(strip=True)
                        if len(name) > 2 and len(name) < 200:
                            company["name"] = sanitize(name, "company")
                            break

                # Email
                for mailto in elem.select("a[href^='mailto:']"):
                    email = mailto.get("href", "").replace("mailto:", "").split("?")[0]
                    if "@" in email:
                        company["email"] = sanitize(email.lower(), "email")
                        break

                # Website
                for link in elem.select("a[href^='http']"):
                    href = link.get("href", "")
                    if not any(x in href.lower() for x in ["facebook", "twitter", "linkedin", "instagram"]):
                        company["website"] = href
                        break

                if company["name"]:
                    results.append(company)
            break

    return results


def discover_api_endpoints(api_key: str, api: Dict) -> List[str]:
    """Discover additional API endpoints by probing common patterns"""
    discovered = []
    session = get_session()
    base_url = api["base_url"]

    # Try sitemap
    try:
        sitemap_response = session.get(f"{base_url}/sitemap.xml", timeout=10)
        if sitemap_response.status_code == 200:
            soup = BeautifulSoup(sitemap_response.text, "xml")
            for loc in soup.find_all("loc"):
                url = loc.text
                if any(x in url.lower() for x in ["export", "empresa", "director"]):
                    discovered.append(url)
    except:
        pass

    # Try robots.txt for API hints
    try:
        robots_response = session.get(f"{base_url}/robots.txt", timeout=10)
        if robots_response.status_code == 200:
            for line in robots_response.text.split("\n"):
                if "api" in line.lower() and ":" in line:
                    path = line.split(":")[-1].strip()
                    discovered.append(urljoin(base_url, path))
    except:
        pass

    return discovered[:5]  # Limit discoveries


def scrape_gov_api(api_key: str, api: Dict) -> List[Dict]:
    """Scrape a government API"""
    log(f"Scraping {api.get('name', api_key)}...")
    session = get_session()
    all_results = []

    base_url = api["base_url"]
    endpoints = api.get("endpoints", [])

    # Add discovered endpoints
    discovered = discover_api_endpoints(api_key, api)
    endpoints = list(set(endpoints + discovered))

    for endpoint in endpoints:
        time.sleep(random.uniform(*REQUEST_DELAY))

        url = urljoin(base_url, endpoint) if not endpoint.startswith("http") else endpoint
        log(f"  Trying: {url}")

        result = probe_endpoint(session, url)

        if result:
            if result["type"] in ("json", "embedded_json"):
                companies = extract_from_json(result["data"], api.get("name", api_key), api.get("country", ""))
                log(f"    JSON: Found {len(companies)} companies")
                all_results.extend(companies)
            elif result["type"] == "html":
                companies = extract_from_html(result["data"], api.get("name", api_key), api.get("country", ""))
                log(f"    HTML: Found {len(companies)} companies")
                all_results.extend(companies)

    # Deduplicate by name
    seen = set()
    unique = []
    for r in all_results:
        key = r.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(r)

    log(f"{api_key}: Total {len(unique)} unique companies")
    return unique


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=5)
    parser.add_argument("--api", type=str, help="Scrape specific API")
    parser.add_argument("--test", action="store_true", help="Test mode - 2 APIs")
    args = parser.parse_args()

    log("Starting government API scraper")

    # Select APIs to scrape
    if args.api:
        if args.api not in GOV_APIS:
            log(f"Unknown API: {args.api}")
            log(f"Available: {', '.join(GOV_APIS.keys())}")
            return
        targets = {args.api: GOV_APIS[args.api]}
    elif args.test:
        targets = dict(list(GOV_APIS.items())[:2])
        log("TEST MODE: 2 APIs")
    else:
        targets = GOV_APIS

    log(f"Scraping {len(targets)} government APIs")

    all_results = []

    # Parallel API scraping
    with ThreadPoolExecutor(max_workers=min(args.threads, len(targets))) as executor:
        futures = {
            executor.submit(scrape_gov_api, api_key, api): api_key
            for api_key, api in targets.items()
        }

        for future in as_completed(futures):
            api_key = futures[future]
            try:
                results = future.result()
                all_results.extend(results)
            except Exception as e:
                log(f"Error scraping {api_key}: {e}")

    # Final deduplication
    seen = set()
    unique_results = []
    for r in all_results:
        key = r.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique_results.append(r)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = OUTPUT_DIR / f"govapis_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(unique_results, f, indent=2)

    csv_file = OUTPUT_DIR / f"govapis_{timestamp}.csv"
    if unique_results:
        with open(csv_file, "w", newline="") as f:
            fieldnames = ["name", "country", "sector", "website", "email", "source"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(unique_results)

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
