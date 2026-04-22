"""Merge all data sources into DATA/countries.json (one entry per country)."""
import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "DATA"
COUNTRIES_CSV = DATA_DIR / "africa_countries.csv"
WB_RAW_DIR = DATA_DIR / "wb_raw"
TI_JSON = DATA_DIR / "ti_cpi.json"
VISA_JSON = DATA_DIR / "visa_requirements.json"
TREATIES_JSON = DATA_DIR / "treaties.json"
OUT = DATA_DIR / "countries.json"


def fmt_number(val: float | None, decimals: int = 0) -> str | None:
    if val is None:
        return None
    if decimals == 0:
        return f"{int(val):,}"
    return f"{val:.{decimals}f}"


def main() -> None:
    with open(COUNTRIES_CSV, newline="", encoding="utf-8") as f:
        countries = list(csv.DictReader(f))

    ti = json.loads(TI_JSON.read_text(encoding="utf-8")) if TI_JSON.exists() else {}
    visa_data = json.loads(VISA_JSON.read_text(encoding="utf-8")) if VISA_JSON.exists() else {}
    treaties_data = json.loads(TREATIES_JSON.read_text(encoding="utf-8")) if TREATIES_JSON.exists() else {}

    profiles = []
    for c in countries:
        iso2 = c["iso2"].lower()
        iso3 = c["iso3"]

        wb_path = WB_RAW_DIR / f"{iso2}.json"
        wb = json.loads(wb_path.read_text(encoding="utf-8")) if wb_path.exists() else {}

        cpi = ti.get(iso3, {})
        visa = visa_data.get(c["iso2"], {})
        treaties = treaties_data.get(iso3, [])

        profile = {
            "iso2": c["iso2"],
            "iso3": iso3,
            "name": c["name"],
            "region": c["region"],
            "capital": c["capital"],
            "currency": c["currency"],
            "language": c["language"],
            # World Bank
            "gdp_usd": wb.get("gdp_usd"),
            "gdp_per_capita": wb.get("gdp_per_capita"),
            "gdp_growth_pct": wb.get("gdp_growth_pct"),
            "population": wb.get("population"),
            "ease_of_business": wb.get("ease_of_business"),
            "exports_usd": wb.get("exports_usd"),
            "imports_usd": wb.get("imports_usd"),
            "inflation_pct": wb.get("inflation_pct"),
            "unemployment_pct": wb.get("unemployment_pct"),
            # TI CPI
            "cpi_score": cpi.get("cpi_score"),
            "cpi_rank": cpi.get("cpi_rank"),
            # Formatted display
            "gdp_display": fmt_number(wb.get("gdp_usd")),
            "population_display": fmt_number(wb.get("population")),
            # Visa
            "visa_free_count": visa.get("visa_free_count"),
            "voa_count": visa.get("voa_count"),
            "evisa_count": visa.get("evisa_count"),
            "visa_required_count": visa.get("visa_required_count"),
            "schengen_access": visa.get("schengen_access"),
            # Treaties
            "treaties": treaties,
            "treaty_count": len(treaties),
        }
        profiles.append(profile)

    OUT.write_text(json.dumps(profiles, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Merged {len(profiles)} profiles -> {OUT}")


if __name__ == "__main__":
    main()
