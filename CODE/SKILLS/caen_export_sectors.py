#!/usr/bin/env python3
"""
CAEN Sector Export Skill

Exports companies by CAEN code sector with email to CSV files.

Usage:
    # Export all sectors
    python3 caen_export_sectors.py --all

    # Export specific sector
    python3 caen_export_sectors.py --sector horeca
    python3 caen_export_sectors.py --sector construction

    # List available sectors
    python3 caen_export_sectors.py --list

    # Custom CAEN export
    python3 caen_export_sectors.py --caen "55*,56*" --name my_export

    # With lead scoring
    python3 caen_export_sectors.py --sector horeca --score

    # Status of exports
    python3 caen_export_sectors.py --status
"""

import os
import sys
import csv
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

# Paths
EXPORT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/CAEN_EXPORTS")
SEARCH_SCRIPT = "/opt/ACTIVE/INFRA/SKILLS/csv_caen_search.py"
DB_PATH = "/opt/ACTIVE/OPENDATA/DATA/CAEN_INDEX/caen_search.db"

# Sector definitions
SECTORS = {
    "call_centers": {
        "caen": "8220",
        "desc": "Call centres & BPO",
        "keywords": ["call center", "bpo", "outsourcing", "customer service"]
    },
    "horeca": {
        "caen": "55*,56*",
        "desc": "Hotels, Restaurants, Catering",
        "keywords": ["hotel", "restaurant", "catering", "hospitality"]
    },
    "construction": {
        "caen": "41*,42*,43*",
        "desc": "Construction & Building",
        "keywords": ["construction", "building", "contractor"]
    },
    "recruitment": {
        "caen": "78*",
        "desc": "Recruitment & HR agencies",
        "keywords": ["recruitment", "hr", "staffing", "employment"]
    },
    "it_services": {
        "caen": "62*,63*",
        "desc": "IT & Software services",
        "keywords": ["software", "it", "programming", "tech"]
    },
    "transport": {
        "caen": "49*,50*,51*,52*",
        "desc": "Transport & Logistics",
        "keywords": ["transport", "logistics", "shipping", "freight"]
    },
    "manufacturing": {
        "caen": "10*,11*,12*,13*,14*,15*,16*,17*,18*,19*,20*,21*,22*,23*,24*,25*",
        "desc": "Manufacturing & Production",
        "keywords": ["factory", "manufacturing", "production"]
    },
    "wholesale": {
        "caen": "46*",
        "desc": "Wholesale trade",
        "keywords": ["wholesale", "distribution", "b2b"]
    },
    "retail": {
        "caen": "47*",
        "desc": "Retail trade",
        "keywords": ["retail", "shop", "store"]
    },
    "agriculture": {
        "caen": "01*,02*,03*",
        "desc": "Agriculture & Farming",
        "keywords": ["agriculture", "farming", "agri"]
    },
    "healthcare": {
        "caen": "86*,87*,88*",
        "desc": "Healthcare & Social work",
        "keywords": ["healthcare", "medical", "care", "nursing"]
    },
    "finance": {
        "caen": "64*,65*,66*",
        "desc": "Finance & Insurance",
        "keywords": ["finance", "bank", "insurance"]
    },
}


def export_sector(sector_name, with_score=False):
    """Export a single sector to CSV."""
    if sector_name not in SECTORS:
        print(f"Unknown sector: {sector_name}")
        print(f"Available: {', '.join(SECTORS.keys())}")
        return None

    sector = SECTORS[sector_name]
    output = EXPORT_DIR / f"{sector_name}_with_email.csv"

    cmd = [
        "python3", SEARCH_SCRIPT,
        "--caen", sector["caen"],
        "--email-only",
        "--limit", "50000",
        "--output", str(output)
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)

    if output.exists():
        with open(output) as f:
            rows = sum(1 for _ in f) - 1

        if with_score:
            add_scores(output)

        return {"sector": sector_name, "rows": rows, "path": str(output)}

    return None


def add_scores(filepath):
    """Add lead scores to exported CSV."""
    rows = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        if 'score' not in fieldnames:
            fieldnames.append('score')
        if 'tags' not in fieldnames:
            fieldnames.append('tags')

        for row in reader:
            score, tags = calculate_score(row)
            row['score'] = str(score)
            row['tags'] = ','.join(tags)
            rows.append(row)

    # Sort by score
    rows.sort(key=lambda x: int(x.get('score', 0)), reverse=True)

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def calculate_score(row):
    """Calculate lead score based on available data."""
    score = 0
    tags = []

    # Has email
    if row.get('email'):
        score += 10
        email = row['email'].lower()
        domain = email.split('@')[1] if '@' in email else ''
        if domain not in ['gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com']:
            score += 15
            tags.append("corporate_email")

    # Has phone
    if row.get('phone'):
        score += 10
        tags.append("phone")

    # Has CUI
    if row.get('cui'):
        score += 10
        tags.append("registered")

    # Major city
    city = (row.get('city') or '').lower()
    major = ['bucuresti', 'cluj', 'timisoara', 'iasi', 'brasov', 'constanta']
    if any(c in city for c in major):
        score += 5
        tags.append("major_city")

    return score, tags


def export_all(with_score=False):
    """Export all sectors."""
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    results = []
    for name in SECTORS:
        print(f"Exporting {name}...", end=" ", flush=True)
        result = export_sector(name, with_score)
        if result:
            print(f"{result['rows']} rows")
            results.append(result)
        else:
            print("failed")

    return results


def show_status():
    """Show status of exported files."""
    print(f"\nExport directory: {EXPORT_DIR}\n")
    print(f"{'Sector':<20} {'Rows':<10} {'Size':<12} {'Modified'}")
    print("-" * 60)

    total_rows = 0
    for name in SECTORS:
        filepath = EXPORT_DIR / f"{name}_with_email.csv"
        if filepath.exists():
            with open(filepath) as f:
                rows = sum(1 for _ in f) - 1
            size = filepath.stat().st_size
            mtime = datetime.fromtimestamp(filepath.stat().st_mtime)
            print(f"{name:<20} {rows:<10} {size/1024:.1f} KB     {mtime:%Y-%m-%d %H:%M}")
            total_rows += rows
        else:
            print(f"{name:<20} {'--':<10} {'--':<12} not exported")

    print("-" * 60)
    print(f"Total: {total_rows:,} contacts")


def main():
    parser = argparse.ArgumentParser(description="CAEN Sector Export Skill")
    parser.add_argument("--all", action="store_true", help="Export all sectors")
    parser.add_argument("--sector", "-s", help="Export specific sector")
    parser.add_argument("--list", "-l", action="store_true", help="List available sectors")
    parser.add_argument("--status", action="store_true", help="Show export status")
    parser.add_argument("--score", action="store_true", help="Add lead scoring")
    parser.add_argument("--caen", help="Custom CAEN code(s)")
    parser.add_argument("--name", help="Custom export name")

    args = parser.parse_args()

    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    if args.list:
        print("\nAvailable sectors:\n")
        for name, info in SECTORS.items():
            print(f"  {name:<20} CAEN {info['caen']:<30} {info['desc']}")
        return

    if args.status:
        show_status()
        return

    if args.all:
        results = export_all(args.score)
        print(f"\nExported {len(results)} sectors, {sum(r['rows'] for r in results):,} total contacts")
        return

    if args.sector:
        result = export_sector(args.sector, args.score)
        if result:
            print(f"Exported {result['rows']} rows to {result['path']}")
        return

    if args.caen and args.name:
        output = EXPORT_DIR / f"{args.name}_with_email.csv"
        cmd = f"python3 {SEARCH_SCRIPT} --caen \"{args.caen}\" --email-only --limit 50000 --output {output}"
        subprocess.run(cmd, shell=True)
        if output.exists():
            with open(output) as f:
                rows = sum(1 for _ in f) - 1
            if args.score:
                add_scores(output)
            print(f"Exported {rows} rows to {output}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()
