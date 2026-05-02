#!/usr/bin/env python3
"""
Lusha Company Directory Scraper

Scrapes company names from Lusha's public directory pages.
Note: Contact data requires login - this extracts public listing info only.

Usage:
    python3 lusha_scraper.py --industry "wholesale-import-and-export" --country argentina
    python3 lusha_scraper.py --url "https://www.lusha.com/company-search/..." --pages 5
    python3 lusha_scraper.py --enrich lusha_companies.csv  # Add websites via web search
"""

import asyncio
import argparse
import csv
import re
import sys
from pathlib import Path

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("Playwright not installed. Run: pip install playwright && playwright install")
    sys.exit(1)


async def scrape_lusha_listing(url: str, max_pages: int = 10) -> list:
    """Scrape company listings from Lusha directory page"""
    companies = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = await context.new_page()

        for pg in range(1, max_pages + 1):
            page_url = url if pg == 1 else f"{url.rstrip('/')}page/{pg}/"

            print(f"Page {pg}: {page_url[:70]}...")

            try:
                await page.goto(page_url, timeout=30000)
                await page.wait_for_timeout(2000)

                content = await page.content()

                # Extract company links
                links = re.findall(
                    r'href="(https://www\.lusha\.com/business/[^"]+)"[^>]*>\s*([^<]+)',
                    content
                )

                if not links:
                    print(f"  No companies on page {pg}, stopping")
                    break

                for href, name in links:
                    name = name.strip()
                    # Decode HTML entities
                    name = name.replace('&amp;', '&').replace('&#39;', "'")
                    if name and name not in [c['company'] for c in companies]:
                        companies.append({
                            'company': name,
                            'lusha_url': href,
                        })

                print(f"  Found {len(links)} companies, total: {len(companies)}")

                # Check for next page
                if f'page/{pg+1}/' not in content:
                    break

            except Exception as e:
                print(f"  Error on page {pg}: {e}")
                break

        await browser.close()

    return companies


def extract_country_from_url(url: str) -> str:
    """Extract country name from Lusha URL"""
    match = re.search(r'/([a-z-]+)/\d+/?$', url)
    if match:
        country = match.group(1).replace('-', ' ').title()
        return country
    return 'Unknown'


async def main():
    parser = argparse.ArgumentParser(description='Scrape Lusha company directory')
    parser.add_argument('--url', help='Full Lusha directory URL to scrape')
    parser.add_argument('--industry', help='Industry slug (e.g., wholesale-import-and-export)')
    parser.add_argument('--country', help='Country slug (e.g., argentina, brazil)')
    parser.add_argument('--pages', type=int, default=10, help='Max pages to scrape')
    parser.add_argument('--output', help='Output CSV file', default='lusha_companies.csv')
    parser.add_argument('--enrich', help='CSV file to enrich with websites')

    args = parser.parse_args()

    if args.enrich:
        print(f"Website enrichment requires manual web search or Hunter.io API")
        print(f"Consider using: python3 /opt/ACTIVE/INFRA/SKILLS/website_finder.py {args.enrich}")
        return

    if args.url:
        url = args.url
    elif args.industry and args.country:
        # Build URL - note: Lusha uses industry hashes, this is approximate
        url = f"https://www.lusha.com/company-search/{args.industry}/ba66d803b2/{args.country}/"
        print(f"Warning: Industry hash may not match. Use --url for exact scraping.")
    else:
        parser.print_help()
        return

    print(f"Scraping: {url}")
    companies = await scrape_lusha_listing(url, args.pages)

    if not companies:
        print("No companies found")
        return

    # Add country
    country = extract_country_from_url(url)
    for c in companies:
        c['country'] = country

    # Save
    output = Path(args.output)
    with open(output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['company', 'lusha_url', 'country'])
        writer.writeheader()
        writer.writerows(companies)

    print(f"\nSaved {len(companies)} companies to {output}")
    print(f"Country breakdown:")
    from collections import Counter
    for c, cnt in Counter([x['country'] for x in companies]).most_common():
        print(f"  {c}: {cnt}")


if __name__ == '__main__':
    asyncio.run(main())
