#!/usr/bin/env python3
"""
ANOFM Scandinavia Matcher - Match Romanian workers to Scandinavian job requirements.

Reads ANOFM job postings, filters construction sector, and matches workers
to Scandinavian opportunities (Norway, Denmark, Sweden).

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/anofm_scandinavia_matcher.py
    python3 /opt/ACTIVE/INFRA/SKILLS/anofm_scandinavia_matcher.py --dry-run
    python3 /opt/ACTIVE/INFRA/SKILLS/anofm_scandinavia_matcher.py --no-telegram

Output:
    /opt/ACTIVE/SCRAPER_DATA/csv/ANOFM/matched_workers.csv
"""

import sys
import os
import csv
import glob
import argparse
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field

# Add shared code path
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

from skills_common import to_ascii, sanitize
from alerting import send_telegram

# =============================================================================
# CONFIGURATION
# =============================================================================

ANOFM_DIR = '/opt/ACTIVE/SCRAPER_DATA/csv/ANOFM'
OUTPUT_FILE = os.path.join(ANOFM_DIR, 'matched_workers.csv')

# Construction sector filter
CONSTRUCTION_SECTORS = ['Constructii', 'Instalatii', 'construcții', 'instalații']

# Occupation code prefixes for construction trades
# 721* - Sheet and structural metal workers, moulders and welders
# 711* - Building frame and related trades workers
# 712* - Building finishers and related trades workers
CONSTRUCTION_OCCUPATION_PREFIXES = ('721', '711', '712', '713', '723', '931')

# =============================================================================
# WORKER TYPE DEFINITIONS
# =============================================================================

@dataclass
class WorkerType:
    """Definition of a worker type with matching patterns."""
    name: str
    name_en: str
    patterns: List[str]  # Romanian keywords to match in job_title
    occupation_codes: List[str]  # Specific occupation codes
    scandinavia_match: str  # Target country/industry
    priority: int = 1  # Higher = more valuable match

WORKER_TYPES = [
    # Welders - High priority for Norway offshore and Denmark shipyards
    WorkerType(
        name='Sudor',
        name_en='Welder',
        patterns=['sudor', 'sudura', 'arc electric', 'tig', 'mig', 'mag', 'wps'],
        occupation_codes=['721204', '721205', '721206', '721201'],
        scandinavia_match='Norway offshore, Denmark shipyards',
        priority=3
    ),
    # Scaffolders - Norway construction
    WorkerType(
        name='Schele',
        name_en='Scaffolder',
        patterns=['schel', 'scaffold', 'eşafodaj', 'esafodaj', 'montator schele'],
        occupation_codes=['711501', '711502'],
        scandinavia_match='Norway construction',
        priority=3
    ),
    # Concrete workers - Denmark infrastructure
    WorkerType(
        name='Betonist',
        name_en='Concrete Worker',
        patterns=['betonist', 'beton', 'cofrag', 'fier-beton', 'fierar beton', 'armat'],
        occupation_codes=['711401', '711402', '711403', '931301'],
        scandinavia_match='Denmark infrastructure',
        priority=3
    ),
    # Pipe fitters / Plumbers
    WorkerType(
        name='Instalator',
        name_en='Pipe Fitter',
        patterns=['instalator', 'tevi', 'conducte', 'tub', 'fitinguri', 'sudor conducte'],
        occupation_codes=['712101', '712102', '712103'],
        scandinavia_match='Norway offshore, Denmark industrial',
        priority=2
    ),
    # Metal workers / Locksmiths
    WorkerType(
        name='Lacatus',
        name_en='Metal Worker',
        patterns=['lacatus', 'lacatuș', 'metal', 'constructii metalice', 'naval'],
        occupation_codes=['721407', '721424', '721401', '721417'],
        scandinavia_match='Denmark shipyards, Sweden manufacturing',
        priority=2
    ),
    # Electricians
    WorkerType(
        name='Electrician',
        name_en='Electrician',
        patterns=['electrician', 'electric', 'cablaj', 'tablou', 'automatizari'],
        occupation_codes=['741101', '741102', '741201', '311306'],
        scandinavia_match='Norway offshore, Denmark industrial',
        priority=2
    ),
    # Carpenters
    WorkerType(
        name='Tamplar',
        name_en='Carpenter',
        patterns=['tamplar', 'tâmplar', 'dulgher', 'lemn', 'cofrajist'],
        occupation_codes=['711101', '711102', '711301'],
        scandinavia_match='Norway/Sweden construction',
        priority=1
    ),
    # Painters
    WorkerType(
        name='Vopsitor',
        name_en='Painter',
        patterns=['vopsitor', 'zugrav', 'finisaj', 'anticoroziv'],
        occupation_codes=['713101', '713102', '713205'],
        scandinavia_match='Denmark shipyards, construction',
        priority=1
    ),
    # Tilers/Masons
    WorkerType(
        name='Faiantar/Zidar',
        name_en='Tiler/Mason',
        patterns=['faiantar', 'faianta', 'gresie', 'zidar', 'zidarie', 'placar'],
        occupation_codes=['712201', '712202', '711201'],
        scandinavia_match='Denmark/Sweden construction',
        priority=1
    ),
    # General construction workers
    WorkerType(
        name='Muncitor Constructii',
        name_en='Construction Worker',
        patterns=['muncitor necalificat', 'muncitor constructii', 'demolari', 'sapator'],
        occupation_codes=['931301', '931302', '931303'],
        scandinavia_match='Scandinavia general construction',
        priority=1
    ),
]

# =============================================================================
# MATCHING LOGIC
# =============================================================================

def get_latest_anofm_csv() -> Optional[str]:
    """Find the most recent ANOFM CSV file (non-enriched)."""
    pattern = os.path.join(ANOFM_DIR, 'anofm_*.csv')
    files = glob.glob(pattern)

    # Exclude enriched files
    files = [f for f in files if '_enriched' not in f]

    if not files:
        return None

    # Sort by modification time, newest first
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]


def is_construction_sector(row: Dict) -> bool:
    """Check if job is in construction sector."""
    sector = row.get('sector', '').lower()
    occupation = row.get('occupation', '')

    # Check sector name
    for cs in CONSTRUCTION_SECTORS:
        if cs.lower() in sector:
            return True

    # Check occupation code prefix
    if occupation:
        for prefix in CONSTRUCTION_OCCUPATION_PREFIXES:
            if occupation.startswith(prefix):
                return True

    return False


def match_worker_type(row: Dict) -> Tuple[Optional[WorkerType], int]:
    """
    Match a job row to a worker type.

    Returns:
        Tuple of (WorkerType or None, match_score 0-100)
    """
    job_title = to_ascii(row.get('job_title', '')).lower()
    occupation = row.get('occupation', '')

    best_match = None
    best_score = 0

    for wt in WORKER_TYPES:
        score = 0

        # Check occupation code (exact match = high score)
        if occupation in wt.occupation_codes:
            score += 50

        # Check patterns in job title
        pattern_matches = 0
        for pattern in wt.patterns:
            if pattern.lower() in job_title:
                pattern_matches += 1

        if pattern_matches > 0:
            # More pattern matches = higher score
            score += min(50, pattern_matches * 20)

        # Priority bonus
        score += wt.priority * 5

        if score > best_score:
            best_score = score
            best_match = wt

    # Normalize score to 0-100
    final_score = min(100, best_score)

    # Minimum threshold
    if final_score < 30:
        return None, 0

    return best_match, final_score


def extract_salary(row: Dict) -> str:
    """Extract formatted salary from row."""
    salary_min = row.get('salary_min', '0')
    salary_max = row.get('salary_max', '0')
    currency = row.get('salary_currency', 'RON')

    try:
        min_val = float(salary_min) if salary_min else 0
        max_val = float(salary_max) if salary_max else 0
    except (ValueError, TypeError):
        min_val = max_val = 0

    if min_val > 0 and max_val > 0 and min_val != max_val:
        return f"{int(min_val)}-{int(max_val)} {currency}"
    elif max_val > 0:
        return f"{int(max_val)} {currency}"
    elif min_val > 0:
        return f"{int(min_val)} {currency}"
    else:
        return "N/A"


def clean_phone(phone: str) -> str:
    """Normalize phone number."""
    if not phone:
        return ''
    # Remove common separators
    phone = re.sub(r'[\s\-/]', '', str(phone))
    return phone


def process_anofm_csv(csv_path: str) -> List[Dict]:
    """
    Process ANOFM CSV and extract matches.

    Returns:
        List of matched worker dicts
    """
    matches = []
    seen_companies = set()  # Dedup by company+job

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)

        for row in reader:
            # Skip non-construction
            if not is_construction_sector(row):
                continue

            # Match to worker type
            worker_type, score = match_worker_type(row)
            if not worker_type:
                continue

            # Extract key fields
            company = to_ascii(row.get('company_name', ''))
            email = row.get('email_1', '') or row.get('email_2', '')
            phone = clean_phone(row.get('phone_1', '') or row.get('phone_2', ''))
            job_title = to_ascii(row.get('job_title', ''))
            positions = row.get('positions_available', '1')
            salary = extract_salary(row)
            location = to_ascii(row.get('city', '') or row.get('location', ''))

            # Skip duplicates
            dedup_key = f"{company}|{job_title}"
            if dedup_key in seen_companies:
                continue
            seen_companies.add(dedup_key)

            # Skip if no contact info
            if not email and not phone:
                continue

            match = {
                'worker_type': worker_type.name_en,
                'worker_type_ro': worker_type.name,
                'company': sanitize(company, 'company'),
                'email': sanitize(email, 'email'),
                'phone': phone[:30] if phone else '',
                'job_title': sanitize(job_title, 'title'),
                'positions': positions,
                'salary': salary,
                'location': sanitize(location, 'city'),
                'scandinavia_match': worker_type.scandinavia_match,
                'match_score': score,
                'priority': worker_type.priority,
            }
            matches.append(match)

    # Sort by priority (desc), then score (desc)
    matches.sort(key=lambda x: (-x['priority'], -x['match_score']))

    return matches


def write_output_csv(matches: List[Dict], output_path: str):
    """Write matches to CSV file."""
    fieldnames = [
        'worker_type', 'company', 'email', 'phone', 'positions',
        'salary', 'location', 'match_score', 'scandinavia_match'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(matches)


def generate_summary(matches: List[Dict]) -> str:
    """Generate summary for Telegram."""
    # Count by worker type
    type_counts = {}
    total_positions = 0

    for m in matches:
        wt = m['worker_type']
        type_counts[wt] = type_counts.get(wt, 0) + 1
        try:
            total_positions += int(m['positions'])
        except (ValueError, TypeError):
            total_positions += 1

    # Build summary
    lines = [
        f"<b>ANOFM Scandinavia Match</b>",
        f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        f"<b>Workers Available:</b>",
    ]

    # Sort by count desc
    for wt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"  - {wt}: {count} companies")

    lines.extend([
        "",
        f"<b>Total:</b> {len(matches)} matches, ~{total_positions} positions",
        "",
        "<i>Priority targets: Norway offshore, Denmark shipyards</i>",
    ])

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Match ANOFM workers to Scandinavia jobs')
    parser.add_argument('--dry-run', action='store_true', help='Do not write output or send telegram')
    parser.add_argument('--no-telegram', action='store_true', help='Skip Telegram notification')
    parser.add_argument('--input', type=str, help='Specific input CSV (default: latest)')
    parser.add_argument('--output', type=str, default=OUTPUT_FILE, help='Output CSV path')
    args = parser.parse_args()

    # Find input file
    if args.input:
        csv_path = args.input
    else:
        csv_path = get_latest_anofm_csv()

    if not csv_path or not os.path.exists(csv_path):
        print(f"ERROR: No ANOFM CSV found in {ANOFM_DIR}")
        sys.exit(1)

    print(f"Processing: {csv_path}")

    # Process
    matches = process_anofm_csv(csv_path)
    print(f"Found {len(matches)} matches")

    # Count by type
    type_counts = {}
    for m in matches:
        wt = m['worker_type']
        type_counts[wt] = type_counts.get(wt, 0) + 1

    print("\nMatches by type:")
    for wt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"  {wt}: {count}")

    # Write output
    if not args.dry_run:
        write_output_csv(matches, args.output)
        print(f"\nOutput written to: {args.output}")
    else:
        print("\n[DRY RUN] Output not written")

    # Send Telegram summary
    if not args.dry_run and not args.no_telegram and matches:
        summary = generate_summary(matches)
        print("\nSending Telegram summary...")
        if send_telegram(summary):
            print("Telegram sent successfully")
        else:
            print("Telegram send failed (check TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID)")

    return 0


if __name__ == '__main__':
    sys.exit(main())
