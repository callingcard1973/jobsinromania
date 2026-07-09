from __future__ import annotations

import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path


ACTIVE_FILE = Path("ONG_ACTIVE.csv")
LOCALITY_SUMMARY_FILE = Path("ONG_SUMAR_LOCALITATI.csv")
OUTPUT_FILE = Path("ONG_SHORTLIST_5000.csv")
OUTPUT_SUMMARY_FILE = Path("ONG_SHORTLIST_5000_SUMAR.md")
SHORTLIST_SIZE = 5000

TARGET_COUNTIES = [
    "BUCURESTI",
    "ILFOV",
    "CLUJ",
    "TIMIS",
    "IASI",
    "BRASOV",
    "BIHOR",
    "CONSTANTA",
    "PRAHOVA",
    "SIBIU",
]

CATEGORY_SCORE = {
    "federatie": 20,
    "fundatie": 16,
    "uniune": 14,
    "asociatie": 10,
    "persoana_juridica_straina": 8,
}


def normalize_text(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", " ", ascii_value).strip().upper()


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def locality_maps(summary_rows: list[dict[str, str]]) -> tuple[dict[tuple[str, str], int], dict[str, int]]:
    locality_counts: dict[tuple[str, str], int] = {}
    county_counts: dict[str, int] = Counter()

    for row in summary_rows:
        county = normalize_text(row["judet"] or "NEPRECIZAT")
        locality = normalize_text(row["localitate"] or "NEPRECIZAT")
        total = int(row["total_active"])

        locality_counts[(county, locality)] = locality_counts.get((county, locality), 0) + total
        county_counts[county] += total

    return locality_counts, county_counts


def locality_score(total: int) -> int:
    if total >= 2000:
        return 24
    if total >= 1000:
        return 18
    if total >= 500:
        return 12
    if total >= 200:
        return 8
    if total >= 100:
        return 4
    return 0


def county_score(county: str, county_rank: dict[str, int]) -> int:
    if county in map(normalize_text, TARGET_COUNTIES):
        return 40 - (TARGET_COUNTIES.index(next(name for name in TARGET_COUNTIES if normalize_text(name) == county)) * 2)
    rank = county_rank.get(county, 999)
    if rank <= 15:
        return 12
    if rank <= 25:
        return 6
    return 0


def status_bonus(status: str) -> int:
    return 8 if status == "activa" else 0


def main() -> None:
    active_rows = load_csv(ACTIVE_FILE)
    locality_rows = load_csv(LOCALITY_SUMMARY_FILE)
    locality_counts, county_totals = locality_maps(locality_rows)
    county_rank = {county: index + 1 for index, (county, _) in enumerate(county_totals.most_common())}

    scored_rows = []
    for row in active_rows:
        county = normalize_text(row["judet"] or "NEPRECIZAT")
        locality = normalize_text(row["localitate"] or "NEPRECIZAT")
        locality_total = locality_counts.get((county, locality), 0)

        score_components = {
            "county": county_score(county, county_rank),
            "locality": locality_score(locality_total),
            "category": CATEGORY_SCORE.get(row["categorie"], 0),
            "status": status_bonus(row["status_normalizat"]),
        }

        score = sum(score_components.values())
        reason = []
        if score_components["county"]:
            reason.append("judet_prioritar")
        if score_components["locality"]:
            reason.append(f"localitate_dense:{locality_total}")
        reason.append(f"categorie:{row['categorie']}")

        scored_rows.append(
            {
                **row,
                "priority_score": str(score),
                "localitate_total_active": str(locality_total),
                "judet_rank_active": str(county_rank.get(county, 999)),
                "judet_cheie": county,
                "localitate_cheie": locality,
                "priority_reason": " | ".join(reason),
            }
        )

    scored_rows.sort(
        key=lambda row: (
            -int(row["priority_score"]),
            int(row["judet_rank_active"]),
            -(int(row["localitate_total_active"]) if row["localitate_total_active"] else 0),
            row["categorie"],
            row["denumire"],
        )
    )

    shortlist = []
    seen = set()
    for row in scored_rows:
        dedupe_key = (row["denumire"], row["judet"], row["localitate"], row["categorie"])
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        shortlist.append(row)
        if len(shortlist) >= SHORTLIST_SIZE:
            break

    fieldnames = [
        "priority_rank",
        "priority_score",
        "priority_reason",
        "judet_rank_active",
        "localitate_total_active",
        "categorie",
        "denumire",
        "numar_registru_national",
        "status_normalizat",
        "judet_cheie",
        "localitate_cheie",
        "judet",
        "localitate",
        "adresa",
        "scop_initial",
        "hg_utilitate_publica",
        "data_hg_utilitate_publica",
        "sursa_url",
    ]

    for index, row in enumerate(shortlist, start=1):
        row["priority_rank"] = str(index)

    with OUTPUT_FILE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows({field: row.get(field, "") for field in fieldnames} for row in shortlist)

    top_counties = Counter(row["judet_cheie"] or "NEPRECIZAT" for row in shortlist).most_common(15)
    top_localities = Counter((row["judet_cheie"] or "NEPRECIZAT", row["localitate_cheie"] or "NEPRECIZAT") for row in shortlist).most_common(15)
    top_categories = Counter(row["categorie"] for row in shortlist).most_common()

    summary_lines = [
        "# ONG Shortlist 5000",
        "",
        f"Total lead-uri: {len(shortlist)}",
        "",
        "## Heuristica",
        "",
        "- numai ONG-uri active",
        "- prioritate pentru judetele: Bucuresti, Ilfov, Cluj, Timis, Iasi, Brasov, Bihor, Constanta, Prahova, Sibiu",
        "- bonus pentru localitati cu densitate mare de ONG-uri active",
        "- bonus de categorie pentru fundatii, federatii si uniuni",
        "",
        "## Top judete in shortlist",
        "",
    ]
    summary_lines.extend(f"- {county}: {count}" for county, count in top_counties)
    summary_lines.extend(["", "## Top localitati in shortlist", ""])
    summary_lines.extend(f"- {county} / {locality}: {count}" for (county, locality), count in top_localities)
    summary_lines.extend(["", "## Categorii in shortlist", ""])
    summary_lines.extend(f"- {category}: {count}" for category, count in top_categories)

    OUTPUT_SUMMARY_FILE.write_text("\n".join(summary_lines) + "\n", encoding="utf-8")

    print(f"Generated {OUTPUT_FILE}")
    print(f"Generated {OUTPUT_SUMMARY_FILE}")


if __name__ == "__main__":
    main()