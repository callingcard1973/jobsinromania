#!/usr/bin/env python3
"""
Crowdfunding Scraper Skill
Scrape crowdfunding platforms for real estate and agriculture leads.

Usage:
    /crowdfunding                    # Run all working scrapers
    /crowdfunding --platform miimosa # Run specific platform
    /crowdfunding --list             # List available platforms
    /crowdfunding --status           # Show data status
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

SCRAPER_DIR = Path("/opt/ACTIVE/SCRAPERS/EUROPE/CROWDFUNDING/SANDBOX")
DATA_DIR = Path("/opt/ACTIVE/SCRAPERS/EUROPE/CROWDFUNDING/DATA")
PYTHON = "/opt/ACTIVE/INFRA/venv/bin/python3"

# Platform configurations
PLATFORMS = {
    "miimosa": {
        "script": "test_miimosa_v2.py",
        "type": "Agriculture",
        "country": "France",
        "status": "working",
        "description": "French agriculture crowdfunding - farms, food production",
    },
    "clubfunding": {
        "script": "test_clubfunding_v2.py",
        "type": "Real Estate",
        "country": "France",
        "status": "working",
        "description": "French real estate - construction, property development",
    },
    "ethichub": {
        "script": "test_ethichub.py",
        "type": "Agriculture",
        "country": "Spain",
        "status": "partial",
        "description": "Spanish agriculture P2P - small farmers",
    },
    "recrowd": {
        "script": "test_recrowd.py",
        "type": "Real Estate",
        "country": "Italy",
        "status": "partial",
        "description": "Italian real estate crowdfunding",
    },
    "crowdcube": {
        "script": "test_crowdcube.py",
        "type": "Equity",
        "country": "UK",
        "status": "working",
        "description": "UK equity crowdfunding - startups, property",
    },
    "startengine": {
        "script": "test_startengine.py",
        "type": "Equity",
        "country": "USA",
        "status": "working",
        "description": "US equity crowdfunding - 50+ campaigns, no external websites",
    },
    "wefunder": {
        "script": "test_wefunder.py",
        "type": "Equity",
        "country": "USA",
        "status": "blocked",
        "description": "US equity crowdfunding - Cloudflare protected",
    },
    "seedrs": {
        "script": "test_seedrs.py",
        "type": "Equity",
        "country": "UK",
        "status": "blocked",
        "description": "UK equity crowdfunding - requires auth",
    },
    "urbanitae": {
        "script": "test_urbanitae.py",
        "type": "Real Estate",
        "country": "Spain",
        "status": "blocked",
        "description": "Spanish real estate - CloudFront blocking",
    },
    "kickstarter": {
        "script": "test_kickstarter.py",
        "type": "Rewards",
        "country": "Global",
        "status": "blocked",
        "description": "Global rewards crowdfunding - bot protection",
    },
    "estateguru": {
        "script": "test_estateguru.py",
        "type": "Real Estate",
        "country": "EU",
        "status": "blocked",
        "description": "EU real estate P2P - requires auth",
    },
    "lande": {
        "script": "test_lande.py",
        "type": "Agriculture",
        "country": "Latvia",
        "status": "blocked",
        "description": "Baltic agriculture P2P - requires auth",
    },
}


def list_platforms():
    """List all available platforms."""
    print("\n" + "=" * 70)
    print("CROWDFUNDING PLATFORMS")
    print("=" * 70)

    print("\n### Working (Recommended)")
    print("-" * 70)
    for name, info in PLATFORMS.items():
        if info["status"] == "working":
            print(f"  {name:15} | {info['type']:12} | {info['country']:8} | {info['description'][:40]}")

    print("\n### Partial (Limited Data)")
    print("-" * 70)
    for name, info in PLATFORMS.items():
        if info["status"] == "partial":
            print(f"  {name:15} | {info['type']:12} | {info['country']:8} | {info['description'][:40]}")

    print("\n### Blocked (Need Fix)")
    print("-" * 70)
    for name, info in PLATFORMS.items():
        if info["status"] == "blocked":
            print(f"  {name:15} | {info['type']:12} | {info['country']:8} | {info['description'][:40]}")

    print("\n" + "=" * 70)


def show_status():
    """Show current data status."""
    print("\n" + "=" * 70)
    print("DATA STATUS")
    print("=" * 70)

    if not DATA_DIR.exists():
        print("No data directory found")
        return

    csv_files = sorted(DATA_DIR.glob("*.csv"), key=lambda x: x.stat().st_mtime, reverse=True)

    if not csv_files:
        print("No CSV files found")
        return

    print(f"\n{'File':<45} {'Size':>10} {'Modified':<20}")
    print("-" * 70)

    for f in csv_files[:10]:
        size = f.stat().st_size
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        print(f"{f.name:<45} {size:>10} {mtime:<20}")

    print("\n" + "=" * 70)


def run_scraper(platform: str):
    """Run a specific platform scraper."""
    if platform not in PLATFORMS:
        print(f"Unknown platform: {platform}")
        print(f"Available: {', '.join(PLATFORMS.keys())}")
        return False

    info = PLATFORMS[platform]
    script = SCRAPER_DIR / info["script"]

    if not script.exists():
        print(f"Script not found: {script}")
        return False

    if info["status"] == "blocked":
        print(f"WARNING: {platform} is blocked/requires auth. May not return results.")

    print(f"\n{'=' * 60}")
    print(f"Running {platform.upper()} scraper")
    print(f"Type: {info['type']} | Country: {info['country']}")
    print(f"{'=' * 60}\n")

    result = subprocess.run([PYTHON, str(script)], cwd=str(SCRAPER_DIR))
    return result.returncode == 0


def run_all_working():
    """Run all working scrapers."""
    working = [name for name, info in PLATFORMS.items() if info["status"] == "working"]

    print(f"\nRunning {len(working)} working scrapers: {', '.join(working)}")

    results = {}
    for platform in working:
        success = run_scraper(platform)
        results[platform] = "OK" if success else "FAILED"

    print("\n" + "=" * 60)
    print("SCRAPE COMPLETE")
    print("=" * 60)
    for platform, status in results.items():
        print(f"  {platform}: {status}")

    show_status()


def main():
    args = sys.argv[1:] if len(sys.argv) > 1 else []

    if not args:
        # Default: run all working scrapers
        run_all_working()
        return

    if args[0] == "--list":
        list_platforms()
    elif args[0] == "--status":
        show_status()
    elif args[0] == "--platform" and len(args) > 1:
        run_scraper(args[1])
    elif args[0] == "--all":
        run_all_working()
    elif args[0] in PLATFORMS:
        run_scraper(args[0])
    else:
        print("Usage:")
        print("  /crowdfunding                    # Run all working scrapers")
        print("  /crowdfunding --platform NAME    # Run specific platform")
        print("  /crowdfunding --list             # List platforms")
        print("  /crowdfunding --status           # Show data status")
        print(f"\nPlatforms: {', '.join(PLATFORMS.keys())}")


if __name__ == "__main__":
    main()
