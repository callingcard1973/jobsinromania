#!/usr/bin/env python3
"""
MERCOSUR Data Merger
Consolidates output from all workers into unified dataset
"""

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set

# Import shared utilities
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii, sanitize
except ImportError:
    def to_ascii(text): return text if not text else text.encode('ascii', 'ignore').decode()
    def sanitize(text, *args): return to_ascii(text)[:200] if text else ""

from config import EXISTING_DATA, OUTPUT_BASE, OUTPUT_SCHEMA

OUTPUT_DIR = OUTPUT_BASE / "merged"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

WORKER_DIRS = [
    "websites",
    "govapis",
    "associations",
    "registries",
    "tradeshows",
    "enriched",
]


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [merger] {msg}")


def load_json_files(directory: Path) -> List[Dict]:
    """Load all JSON files from a directory"""
    results = []

    if not directory.exists():
        return results

    for json_file in sorted(directory.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True):
        try:
            with open(json_file) as f:
                data = json.load(f)
                if isinstance(data, list):
                    results.extend(data)
                    log(f"  Loaded {len(data)} records from {json_file.name}")
        except Exception as e:
            log(f"  Error loading {json_file.name}: {e}")

    return results


def load_existing_data() -> List[Dict]:
    """Load existing base dataset"""
    if not EXISTING_DATA.exists():
        return []

    json_files = list(EXISTING_DATA.glob("mercosur_*.json"))
    if not json_files:
        return []

    latest = max(json_files, key=lambda f: f.stat().st_mtime)
    log(f"Loading existing data from {latest}")

    try:
        with open(latest) as f:
            data = json.load(f)
            log(f"  Loaded {len(data)} existing records")
            return data
    except Exception as e:
        log(f"  Error loading existing data: {e}")
        return []


def normalize_company_name(name: str) -> str:
    """Normalize company name for deduplication"""
    if not name:
        return ""

    name = to_ascii(name).lower().strip()

    # Remove common suffixes
    suffixes = [
        " s.a.", " sa", " s/a", " ltda", " ltd", " inc", " corp",
        " gmbh", " ag", " co.", " cia", " s.r.l.", " srl",
        " s.a.s.", " s.a.c.", " e.i.r.l.",
    ]
    for suffix in suffixes:
        if name.endswith(suffix):
            name = name[:-len(suffix)]

    # Remove punctuation
    name = "".join(c for c in name if c.isalnum() or c == " ")

    # Normalize whitespace
    name = " ".join(name.split())

    return name


def merge_records(existing: Dict, new: Dict) -> Dict:
    """Merge two records, preferring non-empty new values"""
    merged = existing.copy()

    for key, value in new.items():
        if not value:
            continue

        existing_value = merged.get(key, "")

        # Always prefer email if new one exists
        if key == "email" and value and "@" in str(value):
            merged[key] = value

        # Prefer longer/more complete values
        elif key in ("name", "sector", "website"):
            if len(str(value)) > len(str(existing_value)):
                merged[key] = value

        # Add source info
        elif key == "source":
            if existing_value and value not in existing_value:
                merged[key] = f"{existing_value}, {value}"
            elif not existing_value:
                merged[key] = value

        # Fill in missing values
        elif not existing_value:
            merged[key] = value

    return merged


def deduplicate_and_merge(records: List[Dict]) -> List[Dict]:
    """Deduplicate records by normalized company name"""

    # Group by normalized name
    groups: Dict[str, List[Dict]] = defaultdict(list)

    for record in records:
        name = record.get("name", "")
        if not name:
            continue

        normalized = normalize_company_name(name)
        if normalized:
            groups[normalized].append(record)

    # Merge each group
    merged_records = []

    for normalized_name, group in groups.items():
        if len(group) == 1:
            merged_records.append(group[0])
        else:
            # Sort by priority: prefer records with email, then website
            group.sort(key=lambda r: (
                bool(r.get("email")),
                bool(r.get("website")),
                len(r.get("name", "")),
            ), reverse=True)

            # Merge all into first
            merged = group[0]
            for other in group[1:]:
                merged = merge_records(merged, other)

            merged_records.append(merged)

    return merged_records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-existing", action="store_true",
                        help="Include existing base data")
    parser.add_argument("--output-dir", type=str,
                        help="Override output directory")
    args = parser.parse_args()

    log("Starting data merger")

    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR

    # Load all worker outputs
    all_records = []

    for worker in WORKER_DIRS:
        worker_dir = OUTPUT_BASE / worker
        log(f"Loading from {worker}/...")
        records = load_json_files(worker_dir)
        all_records.extend(records)

    log(f"Total from workers: {len(all_records)}")

    # Optionally include existing base data
    if args.include_existing:
        existing = load_existing_data()
        all_records.extend(existing)
        log(f"Total with existing: {len(all_records)}")

    # Deduplicate and merge
    log("Deduplicating...")
    merged = deduplicate_and_merge(all_records)
    log(f"After dedup: {len(merged)}")

    # Normalize output schema
    final_records = []
    for record in merged:
        clean_record = {}
        for field in OUTPUT_SCHEMA:
            value = record.get(field, "")
            if isinstance(value, str):
                clean_record[field] = sanitize(value, field if field in ("email", "name") else "medium")
            else:
                clean_record[field] = value
        clean_record["scraped_at"] = record.get("scraped_at", record.get("enriched_at", datetime.now().isoformat()))
        final_records.append(clean_record)

    # Sort by country, then name
    final_records.sort(key=lambda r: (r.get("country", ""), r.get("name", "")))

    # Calculate stats
    stats = {
        "total": len(final_records),
        "with_email": sum(1 for r in final_records if r.get("email")),
        "with_website": sum(1 for r in final_records if r.get("website")),
        "with_phone": sum(1 for r in final_records if r.get("phone")),
        "by_country": defaultdict(int),
        "by_sector": defaultdict(int),
        "by_source": defaultdict(int),
    }

    for r in final_records:
        stats["by_country"][r.get("country", "Unknown")] += 1
        stats["by_sector"][r.get("sector", "Unknown")] += 1
        for source in r.get("source", "Unknown").split(", "):
            stats["by_source"][source] += 1

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # JSON (full data)
    json_file = output_dir / f"mercosur_all_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(final_records, f, indent=2)

    # CSV (full data)
    csv_file = output_dir / f"mercosur_all_{timestamp}.csv"
    with open(csv_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_SCHEMA, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(final_records)

    # Contacts CSV (only records with email)
    contacts_file = output_dir / f"mercosur_contacts_{timestamp}.csv"
    contacts = [r for r in final_records if r.get("email")]
    with open(contacts_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["name", "email", "country", "sector", "website", "source"],
                                extrasaction="ignore")
        writer.writeheader()
        writer.writerows(contacts)

    # Stats JSON
    stats_file = output_dir / f"stats_{timestamp}.json"
    with open(stats_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_records": stats["total"],
            "with_email": stats["with_email"],
            "email_rate": round(stats["with_email"] / stats["total"] * 100, 1) if stats["total"] else 0,
            "with_website": stats["with_website"],
            "with_phone": stats["with_phone"],
            "by_country": dict(stats["by_country"]),
            "by_sector": dict(stats["by_sector"]),
            "by_source": dict(stats["by_source"]),
        }, f, indent=2)

    # Print summary
    log("=" * 60)
    log("MERGE SUMMARY")
    log("=" * 60)
    log(f"Total records: {stats['total']}")
    log(f"With email: {stats['with_email']} ({stats['with_email']/stats['total']*100:.1f}%)" if stats['total'] else "With email: 0")
    log(f"With website: {stats['with_website']}")
    log(f"With phone: {stats['with_phone']}")
    log("")
    log("By Country:")
    for country, count in sorted(stats["by_country"].items(), key=lambda x: -x[1])[:10]:
        log(f"  {country}: {count}")
    log("")
    log("By Sector:")
    for sector, count in sorted(stats["by_sector"].items(), key=lambda x: -x[1])[:10]:
        log(f"  {sector}: {count}")
    log("")
    log("Files:")
    log(f"  JSON: {json_file}")
    log(f"  CSV: {csv_file}")
    log(f"  Contacts: {contacts_file}")
    log(f"  Stats: {stats_file}")
    log("=" * 60)


if __name__ == "__main__":
    main()
