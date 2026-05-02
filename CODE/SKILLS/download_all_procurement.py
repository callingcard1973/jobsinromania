#!/usr/bin/env python3
"""
Master European Procurement Data Downloader

Coordinates downloading from all European procurement sources:
- OpenTender/DIGIWHIST (35 countries)
- France BOAMP
- Italy ANAC
- Netherlands TenderNed
- Spain PLACSP
- Germany e-Vergabe
- European Auctions
- Building Permits (Eurostat)

All data saved to: /opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT/

Usage:
    python3 download_all_procurement.py --all      # Download everything
    python3 download_all_procurement.py --status   # Check status
    python3 download_all_procurement.py --run FR IT DE  # Specific countries
"""

import argparse
import importlib
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_PROCUREMENT")
SKILLS_DIR = Path("/opt/ACTIVE/INFRA/SKILLS")

# Download scripts and their functions
DOWNLOADERS = {
    "opentender": {
        "script": "download_opentender.py",
        "function": "download_all",
        "description": "OpenTender/DIGIWHIST (35 countries, 10M+ records)",
        "priority": 1,
    },
    "boamp": {
        "script": "download_boamp.py",
        "function": "download_all",
        "description": "France BOAMP (160K contracts/year)",
        "priority": 2,
    },
    "anac": {
        "script": "download_anac.py",
        "function": "download_all",
        "description": "Italy ANAC (100K+ contracts/year)",
        "priority": 2,
    },
    "tenderned": {
        "script": "download_tenderned.py",
        "function": "download_all",
        "description": "Netherlands TenderNed (50K/year)",
        "priority": 3,
    },
    "placsp": {
        "script": "download_placsp.py",
        "function": "download_all",
        "description": "Spain PLACSP (100K/year)",
        "priority": 3,
    },
    "evergabe": {
        "script": "download_evergabe.py",
        "function": "download_all",
        "description": "Germany e-Vergabe (30K/year)",
        "priority": 3,
    },
    "auctions": {
        "script": "download_auctions.py",
        "function": "download_all",
        "description": "European government auctions",
        "priority": 4,
    },
    "permits": {
        "script": "download_permits.py",
        "function": "download_all",
        "description": "Building permits (Eurostat + national)",
        "priority": 4,
    },
}


def run_downloader(name, timeout=3600):
    """Run a specific downloader script."""
    if name not in DOWNLOADERS:
        print(f"Unknown downloader: {name}")
        return False

    info = DOWNLOADERS[name]
    script_path = SKILLS_DIR / info["script"]

    if not script_path.exists():
        print(f"Script not found: {script_path}")
        return False

    print(f"\n{'='*60}")
    print(f" {name.upper()}: {info['description']}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(
            ["python3", str(script_path), "--all"],
            timeout=timeout,
            capture_output=False,
            cwd=str(SKILLS_DIR)
        )
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {timeout}s")
        return False
    except Exception as e:
        print(f"  ERROR: {e}")
        return False


def download_all():
    """Run all downloaders in priority order."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "master_download.log"

    print("\n" + "="*60)
    print(" MASTER PROCUREMENT DATA DOWNLOAD")
    print("="*60)
    print(f"\n Start time: {datetime.now()}")
    print(f" Output: {OUTPUT_DIR}")

    with open(log_file, "w") as f:
        f.write(f"Master Download Started: {datetime.now()}\n\n")

    # Sort by priority
    sorted_downloaders = sorted(
        DOWNLOADERS.items(),
        key=lambda x: x[1]["priority"]
    )

    results = {}
    for name, info in sorted_downloaders:
        print(f"\n[{info['priority']}] Running: {name}")
        start = time.time()

        success = run_downloader(name)
        elapsed = time.time() - start

        results[name] = {
            "success": success,
            "time": elapsed,
        }

        with open(log_file, "a") as f:
            status = "SUCCESS" if success else "FAILED"
            f.write(f"{name}: {status} ({elapsed:.1f}s)\n")

        # Brief pause between downloaders
        time.sleep(5)

    # Summary
    print("\n" + "="*60)
    print(" DOWNLOAD SUMMARY")
    print("="*60)

    success_count = sum(1 for r in results.values() if r["success"])
    total_time = sum(r["time"] for r in results.values())

    for name, result in results.items():
        status = "OK" if result["success"] else "FAIL"
        print(f"  {name}: {status} ({result['time']:.1f}s)")

    print(f"\n  Completed: {success_count}/{len(results)}")
    print(f"  Total time: {total_time/60:.1f} minutes")

    with open(log_file, "a") as f:
        f.write(f"\nCompleted: {datetime.now()}\n")
        f.write(f"Success: {success_count}/{len(results)}\n")

    return success_count == len(results)


def status():
    """Check status of all downloads."""
    print("\n" + "="*60)
    print(" PROCUREMENT DATA STATUS")
    print("="*60)

    total_size = 0
    total_files = 0

    if not OUTPUT_DIR.exists():
        print(f"\n  Output directory not found: {OUTPUT_DIR}")
        return

    # Check each subdirectory
    for subdir in sorted(OUTPUT_DIR.iterdir()):
        if subdir.is_dir():
            files = list(subdir.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            size = sum(f.stat().st_size for f in files if f.is_file())

            total_files += file_count
            total_size += size

            print(f"\n  {subdir.name}:")
            print(f"    Files: {file_count}")
            print(f"    Size: {size / 1024 / 1024:.1f} MB")

    print(f"\n{'='*60}")
    print(f"  TOTAL: {total_files} files, {total_size / 1024 / 1024 / 1024:.2f} GB")

    # Check log file
    log_file = OUTPUT_DIR / "master_download.log"
    if log_file.exists():
        print(f"\n  Last download log:")
        with open(log_file, "r") as f:
            for line in f.readlines()[-10:]:
                print(f"    {line.rstrip()}")


def run_specific(sources):
    """Run specific downloaders."""
    for source in sources:
        source = source.lower()
        if source in DOWNLOADERS:
            run_downloader(source)
        else:
            # Try to match by country code
            country_map = {
                "fr": "boamp",
                "it": "anac",
                "nl": "tenderned",
                "es": "placsp",
                "de": "evergabe",
            }
            if source in country_map:
                run_downloader(country_map[source])
            else:
                print(f"Unknown source: {source}")


def list_downloaders():
    """List available downloaders."""
    print("\n" + "="*60)
    print(" AVAILABLE DOWNLOADERS")
    print("="*60)

    sorted_downloaders = sorted(
        DOWNLOADERS.items(),
        key=lambda x: x[1]["priority"]
    )

    for name, info in sorted_downloaders:
        print(f"\n  {name}:")
        print(f"    {info['description']}")
        print(f"    Script: {info['script']}")
        print(f"    Priority: {info['priority']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Master European Procurement Downloader")
    parser.add_argument("--all", action="store_true", help="Download from all sources")
    parser.add_argument("--status", action="store_true", help="Check download status")
    parser.add_argument("--list", action="store_true", help="List available downloaders")
    parser.add_argument("--run", nargs="+", help="Run specific downloaders")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.list:
        list_downloaders()
    elif args.all:
        download_all()
    elif args.run:
        run_specific(args.run)
    else:
        parser.print_help()
