#!/usr/bin/env python3
"""
European BPO/Call Center Scraper with Local LLM Enrichment

Scrapes BPO companies from multiple sources and enriches with local LLM.
Uses fuzzy matching for deduplication. No API tokens required.

Usage:
    python3 bpo_scraper_europe.py --scrape          # Scrape all sources
    python3 bpo_scraper_europe.py --enrich          # Enrich with LLM
    python3 bpo_scraper_europe.py --github          # Scrape GitHub repos
    python3 bpo_scraper_europe.py --status          # Show status
    python3 bpo_scraper_europe.py --export          # Export to CSV

Sources:
    - Clutch.co (BPO directory)
    - GitHub (awesome-bpo lists)
    - Web search results
    - Existing CAEN data (8220)
"""

import os
import sys
import csv
import json
import re
import time
import hashlib
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, urljoin

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Paths
DATA_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/BPO_EUROPE")
OUTPUT_FILE = DATA_DIR / "bpo_companies_europe.csv"
STATE_FILE = DATA_DIR / ".scraper_state.json"
LLM_URL = "http://localhost:1234/v1/chat/completions"

# BPO Keywords for classification
BPO_KEYWORDS = [
    "call center", "call centre", "bpo", "business process outsourcing",
    "customer service", "contact center", "contact centre", "helpdesk",
    "outsourcing", "back office", "front office", "telemarketing",
    "technical support", "customer support", "shared services"
]

# European countries
EU_COUNTRIES = [
    "Romania", "Poland", "Czech", "Bulgaria", "Hungary", "Slovakia",
    "Germany", "UK", "Spain", "Portugal", "France", "Italy",
    "Netherlands", "Belgium", "Sweden", "Norway", "Denmark", "Finland",
    "Ireland", "Austria", "Switzerland", "Greece", "Croatia", "Serbia"
]


def to_ascii(text):
    """Convert text to ASCII."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii')


def normalize_company(name):
    """Normalize company name for matching."""
    if not name:
        return ""
    name = to_ascii(name).upper()
    # Remove common suffixes
    for suffix in ['SRL', 'SA', 'LTD', 'GMBH', 'SP Z O O', 'S.R.O', 'INC', 'LLC', 'BV', 'AG']:
        name = re.sub(rf'\b{suffix}\b', '', name)
    # Remove punctuation and extra spaces
    name = re.sub(r'[^\w\s]', '', name)
    name = ' '.join(name.split())
    return name.strip()


def fuzzy_match(name1, name2, threshold=0.8):
    """Simple fuzzy matching using character overlap."""
    if not name1 or not name2:
        return False
    n1 = normalize_company(name1)
    n2 = normalize_company(name2)
    if n1 == n2:
        return True
    # Check if one contains the other
    if n1 in n2 or n2 in n1:
        return True
    # Character overlap
    set1 = set(n1.replace(' ', ''))
    set2 = set(n2.replace(' ', ''))
    if not set1 or not set2:
        return False
    overlap = len(set1 & set2) / max(len(set1), len(set2))
    return overlap >= threshold


def call_local_llm(prompt, model="llama-3.2-3b-instruct", max_tokens=200):
    """Call local LLM for enrichment (no API tokens)."""
    try:
        import requests
        response = requests.post(
            LLM_URL,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.3
            },
            timeout=30
        )
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        pass
    return None


def extract_email_from_text(text):
    """Extract email from text."""
    if not text:
        return None
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    matches = re.findall(pattern, text)
    if matches:
        email = matches[0].lower()
        # Skip generic emails
        if not any(x in email for x in ['example.com', 'test.com', 'noreply']):
            return email
    return None


def extract_phone_from_text(text):
    """Extract phone from text."""
    if not text:
        return None
    # Clean text
    text = re.sub(r'[^\d+\s()-]', ' ', text)
    # Find phone patterns
    patterns = [
        r'\+\d{1,3}[\s.-]?\d{2,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}',
        r'\d{3,4}[\s.-]?\d{3,4}[\s.-]?\d{3,4}'
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            phone = re.sub(r'[^\d+]', '', match.group())
            if len(phone) >= 8:
                return phone
    return None


def scrape_clutch_bpo(countries=None):
    """Scrape BPO companies from Clutch.co-style directories."""
    companies = []
    # Note: Actual scraping would require proper HTTP requests
    # This is a template that would be enhanced with real scraping

    print("Clutch.co scraping requires browser automation.")
    print("Using existing CAEN 8220 data as base...")

    # Load existing call center data
    caen_file = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS/call_centers_with_email.csv")
    if caen_file.exists():
        with open(caen_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append({
                    "company": row.get("company", ""),
                    "country": row.get("country", "RO"),
                    "city": row.get("city", ""),
                    "email": row.get("email", ""),
                    "phone": row.get("phone", ""),
                    "website": row.get("website", ""),
                    "source": "caen_8220",
                    "category": "call_center"
                })

    return companies


def scrape_github_awesome_lists():
    """Scrape BPO/outsourcing companies from GitHub awesome lists."""
    companies = []

    # Known awesome lists for outsourcing/BPO
    github_lists = [
        "https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md",
        "https://raw.githubusercontent.com/sindresorhus/awesome/main/readme.md"
    ]

    try:
        import requests

        for url in github_lists:
            try:
                print(f"Fetching: {url}")
                resp = requests.get(url, timeout=30)
                if resp.status_code == 200:
                    content = resp.text

                    # Extract company names and URLs from markdown
                    # Pattern: [Company Name](url) or **Company Name**
                    links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', content)

                    for name, link in links:
                        # Check if related to BPO/outsourcing
                        name_lower = name.lower()
                        if any(kw in name_lower for kw in ['outsourc', 'bpo', 'support', 'service']):
                            domain = urlparse(link).netloc
                            companies.append({
                                "company": to_ascii(name),
                                "website": link,
                                "domain": domain,
                                "source": "github",
                                "category": "bpo_service"
                            })

            except Exception as e:
                print(f"Error fetching {url}: {e}")
                continue

    except ImportError:
        print("requests module not available")

    print(f"Found {len(companies)} companies from GitHub")
    return companies


def scrape_bpo_services_europe():
    """Search for European BPO services companies."""
    companies = []

    # Load existing BPO services data if available
    bpo_file = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS/bpo_services_europe_with_email.csv")
    if bpo_file.exists():
        print(f"Loading existing BPO data from {bpo_file}")
        with open(bpo_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                companies.append({
                    "company": row.get("company", row.get("company_name", "")),
                    "country": row.get("country", ""),
                    "city": row.get("city", ""),
                    "email": row.get("email", ""),
                    "phone": row.get("phone", ""),
                    "website": row.get("website", ""),
                    "caen": row.get("caen", ""),
                    "source": "caen_bpo",
                    "category": "bpo_service"
                })

    return companies


def enrich_with_llm(company):
    """Enrich company data using local LLM."""
    name = company.get("company", "")
    if not name:
        return company

    # Generate enrichment prompt
    prompt = f"""Analyze this company and provide a brief classification:
Company: {name}
Country: {company.get('country', 'Unknown')}
Website: {company.get('website', 'N/A')}

Respond with ONLY a JSON object:
{{"type": "call_center|bpo|outsourcing|it_services|other", "confidence": 0.0-1.0, "services": "brief description"}}"""

    response = call_local_llm(prompt)

    if response:
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[^}]+\}', response)
            if json_match:
                data = json.loads(json_match.group())
                company["llm_type"] = data.get("type", "")
                company["llm_confidence"] = data.get("confidence", 0)
                company["llm_services"] = data.get("services", "")
        except json.JSONDecodeError:
            pass

    return company


def deduplicate_companies(companies):
    """Remove duplicates using fuzzy matching."""
    unique = []
    seen_names = []
    seen_emails = set()
    seen_domains = set()

    for company in companies:
        name = company.get("company", "")
        email = company.get("email", "")
        website = company.get("website", "")

        # Check email duplicate
        if email and email.lower() in seen_emails:
            continue

        # Check domain duplicate
        if website:
            domain = urlparse(website).netloc.lower()
            if domain and domain in seen_domains:
                continue
            if domain:
                seen_domains.add(domain)

        # Check fuzzy name match
        is_duplicate = False
        for seen_name in seen_names:
            if fuzzy_match(name, seen_name):
                is_duplicate = True
                break

        if not is_duplicate:
            unique.append(company)
            seen_names.append(name)
            if email:
                seen_emails.add(email.lower())

    return unique


def calculate_score(company):
    """Calculate lead score for company."""
    score = 0
    tags = []

    # Has email
    email = company.get("email", "")
    if email:
        score += 15
        domain = email.split("@")[1] if "@" in email else ""
        if domain and domain not in ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com"]:
            score += 15
            tags.append("corporate_email")

    # Has phone
    if company.get("phone"):
        score += 10
        tags.append("phone")

    # Has website
    if company.get("website"):
        score += 10
        tags.append("website")

    # In major city
    city = (company.get("city") or "").lower()
    major = ["bucuresti", "bucharest", "warsaw", "krakow", "prague", "budapest",
             "sofia", "berlin", "london", "paris", "amsterdam", "dublin"]
    if any(c in city for c in major):
        score += 5
        tags.append("major_city")

    # LLM confidence
    if company.get("llm_confidence", 0) >= 0.8:
        score += 10
        tags.append("llm_verified")

    company["score"] = score
    company["tags"] = ",".join(tags)
    return company


def export_to_csv(companies, output_path):
    """Export companies to 50-column CSV."""
    # Define 50 columns
    columns = [
        "company", "country", "county", "city", "address", "postal_code",
        "category", "subcategory", "type", "registration_id",
        "email", "email2", "email3", "phone", "phone2", "phone3",
        "website", "contact_person", "contact_dept", "contact_title",
        "products", "services", "activity", "employees", "revenue",
        "founded", "vat_id", "cui", "status", "notes",
        "anofm_email", "anofm_phone", "anofm_address", "web_email",
        "web_phone", "web_website", "best_email", "best_phone",
        "best_address", "verified", "source_file", "source_system",
        "scrape_date", "update_date", "export_date", "priority",
        "score", "tags", "campaign_id", "notes2"
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()

        for company in companies:
            row = {col: "" for col in columns}
            row["company"] = to_ascii(company.get("company", ""))
            row["country"] = company.get("country", "")
            row["city"] = to_ascii(company.get("city", ""))
            row["email"] = company.get("email", "")
            row["phone"] = company.get("phone", "")
            row["website"] = company.get("website", "")
            row["category"] = company.get("category", "bpo")
            row["services"] = company.get("llm_services", "")
            row["source_system"] = company.get("source", "")
            row["scrape_date"] = datetime.now().strftime("%Y-%m-%d")
            row["score"] = company.get("score", 0)
            row["tags"] = company.get("tags", "")
            writer.writerow(row)

    return len(companies)


def load_state():
    """Load scraper state."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"last_run": None, "companies_count": 0, "sources": []}


def save_state(state):
    """Save scraper state."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f, indent=2)


def show_status():
    """Show scraper status."""
    state = load_state()
    print("\n=== BPO Europe Scraper Status ===\n")
    print(f"Last run: {state.get('last_run', 'Never')}")
    print(f"Companies: {state.get('companies_count', 0)}")
    print(f"Sources: {', '.join(state.get('sources', []))}")

    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            rows = sum(1 for _ in f) - 1
        print(f"\nOutput file: {OUTPUT_FILE}")
        print(f"Rows: {rows}")
        print(f"Size: {OUTPUT_FILE.stat().st_size / 1024:.1f} KB")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="European BPO Scraper")
    parser.add_argument("--scrape", action="store_true", help="Scrape all sources")
    parser.add_argument("--enrich", action="store_true", help="Enrich with local LLM")
    parser.add_argument("--github", action="store_true", help="Scrape GitHub repos")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--export", action="store_true", help="Export to CSV")
    parser.add_argument("--all", action="store_true", help="Run full pipeline")

    args = parser.parse_args()

    if args.status:
        show_status()
        return

    if args.all or args.scrape:
        print("=== Scraping BPO Companies ===\n")

        all_companies = []

        # 1. Load CAEN 8220 (call centers)
        print("1. Loading CAEN 8220 (Call Centers)...")
        caen_companies = scrape_clutch_bpo()
        all_companies.extend(caen_companies)
        print(f"   Found: {len(caen_companies)}")

        # 2. Load BPO services
        print("2. Loading BPO Services data...")
        bpo_companies = scrape_bpo_services_europe()
        all_companies.extend(bpo_companies)
        print(f"   Found: {len(bpo_companies)}")

        # 3. GitHub awesome lists
        if args.github or args.all:
            print("3. Scraping GitHub awesome lists...")
            github_companies = scrape_github_awesome_lists()
            all_companies.extend(github_companies)
            print(f"   Found: {len(github_companies)}")

        print(f"\nTotal before dedup: {len(all_companies)}")

        # Deduplicate
        print("\n4. Deduplicating with fuzzy matching...")
        all_companies = deduplicate_companies(all_companies)
        print(f"   After dedup: {len(all_companies)}")

        # Score
        print("\n5. Calculating lead scores...")
        for company in all_companies:
            calculate_score(company)

        # Sort by score
        all_companies.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Save state
        state = {
            "last_run": datetime.now().isoformat(),
            "companies_count": len(all_companies),
            "sources": ["caen_8220", "bpo_services", "github"]
        }
        save_state(state)

        # Export
        if args.export or args.all:
            print(f"\n6. Exporting to {OUTPUT_FILE}...")
            count = export_to_csv(all_companies, OUTPUT_FILE)
            print(f"   Exported: {count} companies")

        # Summary
        print("\n=== Summary ===")
        print(f"Total companies: {len(all_companies)}")
        with_email = sum(1 for c in all_companies if c.get("email"))
        with_phone = sum(1 for c in all_companies if c.get("phone"))
        print(f"With email: {with_email}")
        print(f"With phone: {with_phone}")

        # Top scored
        print("\nTop 10 by score:")
        for c in all_companies[:10]:
            print(f"  {c.get('score', 0):3d} | {c.get('company', '')[:40]}")

    if args.enrich and not args.all:
        print("=== Enriching with Local LLM ===\n")

        # Load existing data
        if not OUTPUT_FILE.exists():
            print("No data to enrich. Run --scrape first.")
            return

        companies = []
        with open(OUTPUT_FILE, 'r') as f:
            reader = csv.DictReader(f)
            companies = list(reader)

        print(f"Loaded {len(companies)} companies")
        print("Enriching with local LLM (llama-3.2-3b)...")

        enriched = 0
        for i, company in enumerate(companies[:100]):  # Limit to 100 for speed
            if i % 10 == 0:
                print(f"  Progress: {i}/{min(100, len(companies))}")
            company = enrich_with_llm(company)
            if company.get("llm_type"):
                enriched += 1

        print(f"\nEnriched: {enriched} companies")

        # Re-export
        export_to_csv(companies, OUTPUT_FILE)
        print(f"Updated: {OUTPUT_FILE}")

    if not any([args.scrape, args.enrich, args.github, args.status, args.export, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
