"""Fetch World Bank indicators for all 54 African countries."""
import csv
import json
import time
from pathlib import Path

import requests

INDICATORS = {
    "gdp_usd": "NY.GDP.MKTP.CD",
    "gdp_per_capita": "NY.GDP.PCAP.CD",
    "gdp_growth_pct": "NY.GDP.MKTP.KD.ZG",
    "population": "SP.POP.TOTL",
    "ease_of_business": "IC.BUS.EASE.XQ",
    "exports_usd": "NE.EXP.GNFS.CD",
    "imports_usd": "NE.IMP.GNFS.CD",
    "inflation_pct": "FP.CPI.TOTL.ZG",
    "unemployment_pct": "SL.UEM.TOTL.ZS",
}

BASE = "https://api.worldbank.org/v2/country/{iso2}/indicator/{code}"
DATA_DIR = Path(__file__).parent.parent / "DATA"
RAW_DIR = DATA_DIR / "wb_raw"
COUNTRIES_CSV = DATA_DIR / "africa_countries.csv"


def fetch_indicator(iso2: str, code: str) -> float | None:
    url = BASE.format(iso2=iso2, code=code)
    params = {"format": "json", "mrv": 3, "per_page": 3}
    try:
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        data = r.json()
        if len(data) < 2 or not data[1]:
            return None
        for entry in data[1]:
            if entry.get("value") is not None:
                return entry["value"]
    except Exception as e:
        print(f"  WARN {iso2} {code}: {e}")
    return None


def fetch_country(iso2: str, name: str) -> dict:
    print(f"Fetching {name} ({iso2})...")
    result: dict = {}
    for key, code in INDICATORS.items():
        result[key] = fetch_indicator(iso2, code)
        time.sleep(0.2)
    return result


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    with open(COUNTRIES_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        countries = list(reader)

    for c in countries:
        out_path = RAW_DIR / f"{c['iso2'].lower()}.json"
        if out_path.exists():
            print(f"Skip {c['name']} (cached)")
            continue
        wb_data = fetch_country(c["iso2"], c["name"])
        out_path.write_text(json.dumps(wb_data, indent=2), encoding="utf-8")
        time.sleep(0.5)

    print(f"Done. {len(countries)} countries fetched to {RAW_DIR}")


if __name__ == "__main__":
    main()
