"""
Fetch visa access data for 54 African countries.
Primary: Henley passport index dataset (GitHub CSV, free, no auth).
Output: DATA/visa_requirements.json keyed by ISO2.
Each entry: visa_free_count, voa_count, evisa_count, visa_required_count, schengen_access
"""
import csv
import io
import json
from collections import defaultdict
from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "DATA"
COUNTRIES_CSV = DATA_DIR / "africa_countries.csv"
OUT = DATA_DIR / "visa_requirements.json"

# Public Henley passport index dataset — tidy format
# Columns: Passport, Destination, Requirement
# Requirement values: visa free, visa on arrival, e-visa, visa required, no admission
DATASET_URL = "https://raw.githubusercontent.com/ilyankou/passport-index-dataset/master/passport-index-tidy.csv"

# Schengen representative
SCHENGEN_ISO2 = "DE"

CATEGORY_MAP = {
    "visa free": "visa_free",
    "visa on arrival": "voa",
    "e-visa": "evisa",
    "visa required": "visa_required",
    "no admission": "visa_required",
}


def load_dataset() -> list[dict]:
    print("Downloading Henley passport index dataset...")
    r = requests.get(DATASET_URL, timeout=30)
    r.raise_for_status()
    reader = csv.DictReader(io.StringIO(r.text))
    return list(reader)


def main() -> None:
    with open(COUNTRIES_CSV, newline="", encoding="utf-8") as f:
        countries = list(csv.DictReader(f))

    rows = load_dataset()
    print(f"Loaded {len(rows)} rows from dataset")

    # Group by passport (country name)
    by_passport: dict[str, list] = defaultdict(list)
    for row in rows:
        by_passport[row.get("Passport", "")].append(row)

    results: dict = {}
    for c in countries:
        iso2 = c["iso2"]
        country_name = c["name"]
        passport_rows = by_passport.get(country_name, [])

        counts: dict[str, int] = {"visa_free": 0, "voa": 0, "evisa": 0, "visa_required": 0}
        schengen_access = "visa_required"

        for row in passport_rows:
            dest = row.get("Destination", "").upper()
            req = row.get("Requirement", "").lower().strip()
            category = CATEGORY_MAP.get(req, "visa_required")
            counts[category] = counts.get(category, 0) + 1
            if dest == SCHENGEN_ISO2:
                schengen_access = category.replace("_", " ") if category != "voa" else "visa_on_arrival"

        results[iso2] = {
            "visa_free_count": counts["visa_free"],
            "voa_count": counts["voa"],
            "evisa_count": counts["evisa"],
            "visa_required_count": counts["visa_required"],
            "schengen_access": schengen_access,
        }
        print(f"  {c['name']}: {counts['visa_free']} VF, Schengen={schengen_access}")

    OUT.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(results)} entries to {OUT}")


if __name__ == "__main__":
    main()
