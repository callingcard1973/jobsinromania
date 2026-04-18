"""
scrape_primari.py — Scrape 2024 elected mayor names from ziare.com and join to primarii_campanie.csv

Source: ziare.com/alegeri/alegeri-locale-2024/rezultate_{judet}/primarie/{localitate}/
Winner = first candidate listed (highest vote count, sorted by site).

Output:
  primarii_mayor_lookup.csv  — locality + county + primar (intermediate cache)
  primarii_campanie_cu_primar.csv  — input CSV + primar column

Usage:
    pip install requests beautifulsoup4 pandas tqdm
    python scrape_primari.py

Flags:
    --no-scrape   Skip scraping, only join from existing lookup cache
    --county alba  Scrape only one county (for testing)
"""

import sys
import time
import unicodedata
import re
import json
import argparse
import csv
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm

BASE_DIR = Path(__file__).parent
CAMPAIGN_CSV = BASE_DIR / "primarii_campanie.csv"
LOOKUP_CSV = BASE_DIR / "primarii_mayor_lookup.csv"
OUTPUT_CSV = BASE_DIR / "primarii_campanie_cu_primar.csv"

BASE_URL = "https://ziare.com/alegeri/alegeri-locale-2024"

COUNTIES = [
    "alba", "arad", "arges", "bacau", "bihor", "bistrita-nasaud", "botosani",
    "braila", "brasov", "bucuresti", "buzau", "calarasi", "caras-severin",
    "cluj", "constanta", "covasna", "dambovita", "dolj", "galati", "giurgiu",
    "gorj", "harghita", "hunedoara", "ialomita", "iasi", "ilfov", "maramures",
    "mehedinti", "mures", "neamt", "olt", "prahova", "salaj", "satu-mare",
    "sibiu", "suceava", "teleorman", "timis", "tulcea", "valcea", "vaslui", "vrancea",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def normalize(s):
    """Normalize locality name for matching."""
    if not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s+", " ", s)
    for prefix in ["municipiul ", "orasul ", "orasul ", "comuna ", "satul ",
                   "municipiu ", "oras ", "sat "]:
        if s.startswith(prefix):
            s = s[len(prefix):]
    return s.strip()


def county_slug_to_name(slug):
    """Convert URL slug to display name for matching."""
    return slug.replace("-", " ").title()


def fetch(url, retries=3, delay=1.0):
    """Fetch URL with retries."""
    for attempt in range(retries):
        try:
            r = SESSION.get(url, timeout=15)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
            time.sleep(delay * (attempt + 1))
        except Exception as e:
            if attempt == retries - 1:
                return None
            time.sleep(delay * (attempt + 1))
    return None


def get_locality_urls(county_slug):
    """Get all locality URLs for a county."""
    url = f"{BASE_URL}/rezultate_{county_slug}/"
    html = fetch(url)
    if not html:
        return []
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if f"/primarie/" in href and href.startswith(f"{BASE_URL}/rezultate_{county_slug}/"):
            if href not in links:
                links.append(href)
    return links


def get_winner_from_locality_page(url):
    """Extract winner name from a locality results page.

    ziare.com HTML structure:
      <div class="chart-line chart-elections__local">
        <div class="item-name fleft"> CANDIDATE NAME (PARTY) </div>
        <div class="item-percent fright">VOTES voturi</div>
      </div>
    First chart-line = winner (highest votes, sorted desc by site).
    """
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")

    # Primary: find first chart-line div -> item-name
    chart_lines = soup.find_all("div", class_="chart-line")
    for div in chart_lines:
        name_div = div.find("div", class_="item-name")
        if name_div:
            raw = name_div.get_text(strip=True)
            # Remove party abbreviation in parentheses: "PLEŞA GABRIEL (PNL)" -> "PLEŞA GABRIEL"
            name = re.sub(r'\s*\([^)]*\)\s*$', '', raw).strip()
            if name and len(name) > 2:
                return name.title()

    # Fallback: title attribute on chart-line div
    for div in chart_lines:
        title = div.get("title", "").strip()
        if title and len(title) > 2:
            return title.title()

    return None


def extract_locality_from_url(url):
    """Extract locality slug from URL."""
    # URL: .../rezultate_alba/primarie/alba-iulia/
    parts = url.rstrip("/").split("/")
    return parts[-1] if parts else ""


def extract_county_from_url(url):
    """Extract county slug from URL."""
    parts = url.rstrip("/").split("/")
    for p in parts:
        if p.startswith("rezultate_"):
            return p[len("rezultate_"):]
    return ""


def scrape_all(counties=None):
    """Scrape all counties. Returns list of {locality, county, primar, url}."""
    if counties is None:
        counties = COUNTIES

    results = []

    for county_slug in tqdm(counties, desc="Counties"):
        locality_urls = get_locality_urls(county_slug)
        if not locality_urls:
            tqdm.write(f"  [{county_slug}] No localities found")
            continue

        tqdm.write(f"  [{county_slug}] {len(locality_urls)} localities")

        for url in tqdm(locality_urls, desc=f"  {county_slug}", leave=False):
            loc_slug = extract_locality_from_url(url)
            winner = get_winner_from_locality_page(url)
            results.append({
                "locality_slug": loc_slug,
                "county_slug": county_slug,
                "locality_name": loc_slug.replace("-", " ").title(),
                "county_name": county_slug_to_name(county_slug),
                "primar": winner or "",
                "url": url,
            })
            time.sleep(0.3)  # polite delay

        time.sleep(0.5)

    return results


def save_lookup(results):
    df = pd.DataFrame(results)
    df.to_csv(LOOKUP_CSV, index=False, encoding="utf-8-sig")
    filled = sum(1 for r in results if r["primar"])
    print(f"[SAVE] Lookup: {len(results)} localities, {filled} with mayor names ({filled/max(1,len(results))*100:.1f}%)")
    print(f"[SAVE] Written to {LOOKUP_CSV}")
    return df


def join_to_campaign(lookup_df):
    """Join mayor names to campaign CSV."""
    camp = pd.read_csv(CAMPAIGN_CSV, encoding="utf-8-sig")
    camp.columns = [c.strip().lstrip("\ufeff") for c in camp.columns]
    print(f"[JOIN] Campaign rows: {len(camp)}")

    # Build lookup: (norm_locality, norm_county) -> primar
    lookup = {}
    for _, row in lookup_df.iterrows():
        loc = normalize(str(row.get("locality_name", row.get("locality_slug", ""))))
        cty = normalize(str(row.get("county_name", row.get("county_slug", ""))))
        primar = str(row.get("primar", "")).strip()
        if primar:
            lookup[(loc, cty)] = primar
            # Also store without county for fallback
            if loc not in lookup:
                lookup[loc] = primar

    matched = 0
    primari = []
    for _, row in camp.iterrows():
        loc = normalize(str(row.get("name", "")))
        cty = normalize(str(row.get("county", "")))
        name = lookup.get((loc, cty), "") or lookup.get(loc, "")
        if name:
            matched += 1
        primari.append(name)

    camp["primar"] = primari
    pct = matched / len(camp) * 100
    print(f"[JOIN] Matched: {matched}/{len(camp)} ({pct:.1f}%)")
    print(f"[JOIN] Missing: {len(camp) - matched}")

    camp.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")
    print(f"[DONE] Output: {OUTPUT_CSV}")

    # Show sample
    matched_df = camp[camp["primar"] != ""]
    if len(matched_df):
        print("\n[SAMPLE] First 10 matched:")
        print(matched_df[["name", "county", "primar"]].head(10).to_string(index=False))

    return camp, matched


def main():
    parser = argparse.ArgumentParser(description="Scrape 2024 Romanian mayor names")
    parser.add_argument("--no-scrape", action="store_true", help="Skip scraping, use existing lookup")
    parser.add_argument("--county", type=str, help="Scrape only this county (e.g. alba)")
    parser.add_argument("--join-only", action="store_true", help="Only join existing lookup to campaign CSV")
    args = parser.parse_args()

    if args.join_only or args.no_scrape:
        if not LOOKUP_CSV.exists():
            print(f"[ERROR] Lookup file not found: {LOOKUP_CSV}")
            sys.exit(1)
        lookup_df = pd.read_csv(LOOKUP_CSV, encoding="utf-8-sig")
        print(f"[LOAD] Lookup: {len(lookup_df)} rows")
    else:
        counties = [args.county] if args.county else None
        print(f"[SCRAPE] Starting scrape for {len(counties) if counties else len(COUNTIES)} counties...")
        results = scrape_all(counties=counties)
        lookup_df = save_lookup(results)

        if args.county:
            print("[INFO] Single county scraped — run without --county to get full dataset")
            print("[INFO] Use --join-only after full scrape to join to campaign CSV")
            return

    join_to_campaign(lookup_df)


if __name__ == "__main__":
    main()
