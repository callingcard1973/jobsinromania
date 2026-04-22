"""Fetch TI CPI 2025 data for African countries → DATA/ti_cpi.json keyed by iso3."""
import csv
import json
from pathlib import Path

import requests
from bs4 import BeautifulSoup

DATA_DIR = Path(__file__).parent.parent / "DATA"
COUNTRIES_CSV = DATA_DIR / "africa_countries.csv"
OUT = DATA_DIR / "ti_cpi.json"

# Wikipedia CPI 2024 table (most recent stable public source)
WIKI_URL = "https://en.wikipedia.org/wiki/Corruption_Perceptions_Index"


def fetch_from_wikipedia() -> dict[str, dict]:
    """Scrape CPI scores from Wikipedia table, keyed by country name."""
    r = requests.get(WIKI_URL, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    result: dict[str, dict] = {}
    # Find the main sortable table with CPI scores
    for table in soup.select("table.wikitable"):
        headers = [th.get_text(strip=True).lower() for th in table.select("thead th, tr:first-child th")]
        if not any("score" in h or "cpi" in h for h in headers):
            continue
        for row in table.select("tbody tr"):
            cells = [td.get_text(strip=True) for td in row.select("td")]
            if len(cells) < 3:
                continue
            # Typical columns: Rank, Country/Territory, Score, ...
            try:
                rank = int(cells[0])
            except ValueError:
                continue
            country_name = cells[1].strip()
            try:
                score = int(cells[2])
            except ValueError:
                continue
            result[country_name.lower()] = {"cpi_score": score, "cpi_rank": rank}
        if result:
            break
    return result


def main() -> None:
    with open(COUNTRIES_CSV, newline="", encoding="utf-8") as f:
        countries = list(csv.DictReader(f))

    wiki_data = fetch_from_wikipedia()
    print(f"Fetched {len(wiki_data)} countries from Wikipedia")

    cpi: dict = {}
    for c in countries:
        iso3 = c["iso3"]
        name = c["name"].lower()

        # Try exact match first, then partial
        match = wiki_data.get(name)
        if not match:
            for wiki_name, vals in wiki_data.items():
                if name in wiki_name or wiki_name in name:
                    match = vals
                    break

        if match:
            cpi[iso3] = match
        else:
            print(f"  No CPI data for {c['name']}")
            cpi[iso3] = {"cpi_score": None, "cpi_rank": None}

    OUT.write_text(json.dumps(cpi, indent=2), encoding="utf-8")
    matched = sum(1 for v in cpi.values() if v["cpi_score"] is not None)
    print(f"Wrote {len(cpi)} entries ({matched} with scores) to {OUT}")


if __name__ == "__main__":
    main()
