#!/usr/bin/env python3
"""
File Organizer - Intelligently organize CSVs and data files
Usage: python3 file_organizer.py [analyze|organize|archive|dedupe] [path] [--dry-run]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import shutil
import hashlib
import glob
import re
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict, Counter
from typing import Dict, List, Tuple

# ============================================================
# CONFIGURATION
# ============================================================

COUNTRIES = {
    'NORWAY': ['norway', 'norse', 'no_', '_no'],
    'SWEDEN': ['sweden', 'swedish', 'se_', '_se'],
    'FINLAND': ['finland', 'finnish', 'fi_', '_fi'],
    'DENMARK': ['denmark', 'danish', 'dk_', '_dk'],
    'ICELAND': ['iceland', 'icelandic', 'is_', '_is'],
    'POLAND': ['poland', 'polish', 'pl_', '_pl', 'kraz'],
    'ROMANIA': ['romania', 'romanian', 'ro_', '_ro', 'anofm'],
    'BULGARIA': ['bulgaria', 'bulgarian', 'bg_', '_bg'],
    'MALTA': ['malta', 'maltese', 'mt_', '_mt'],
    'MOLDOVA': ['moldova', 'moldovan', 'md_', '_md'],
    'EURES': ['eures'],
    'UK': ['uk_', '_uk', 'united_kingdom', 'britain'],
    'IRELAND': ['ireland', 'irish', 'ie_', '_ie'],
    'FRANCE': ['france', 'french', 'fr_', '_fr'],
    'NETHERLANDS': ['netherlands', 'dutch', 'nl_', '_nl'],
}

FILE_TYPES = {
    'MASTER': ['master', 'consolidated', 'all_', 'complete', 'full_'],
    'CONTACTS': ['contact', 'email', 'employer'],
    'JOBS': ['job', 'vacancy', 'position', 'listing'],
    'DAILY': ['daily', 'today', datetime.now().strftime('%Y%m%d')],
    'ARCHIVE': ['archive', 'old', 'backup'],
}

STRUCTURE = """
Proposed structure:
├── MASTER/           # Consolidated master files
├── CONTACTS/         # Contact/email lists
│   ├── NORDIC/       # NO, SE, DK, FI, IS
│   ├── EASTERN/      # PL, RO, BG, MD
│   └── OTHER/        # MT, UK, IE, etc.
├── DAILY/            # Daily scraper outputs
├── ARCHIVE/          # Old/dated files (>30 days)
└── RAW/              # Unprocessed scraper output
"""

# ============================================================
# ANALYSIS
# ============================================================

def analyze(path: str) -> Dict:
    """Analyze directory structure and files"""
    results = {
        'total_files': 0,
        'total_size_mb': 0,
        'by_type': defaultdict(list),
        'by_country': defaultdict(list),
        'by_age': {'recent': [], 'old': [], 'undated': []},
        'duplicates': [],
        'issues': [],
        'suggestions': [],
    }

    hash_map = defaultdict(list)  # For duplicate detection

    for f in glob.glob(os.path.join(path, '**/*.csv'), recursive=True):
        fpath = Path(f)
        results['total_files'] += 1
        results['total_size_mb'] += fpath.stat().st_size / 1024 / 1024

        name_lower = fpath.name.lower()
        path_lower = str(fpath).lower()

        # Detect country
        country = detect_country(path_lower)
        results['by_country'][country].append(f)

        # Detect file type
        ftype = detect_file_type(name_lower)
        results['by_type'][ftype].append(f)

        # Detect age
        age = detect_age(fpath)
        if age == 'old':
            results['by_age']['old'].append(f)
        elif age == 'recent':
            results['by_age']['recent'].append(f)
        else:
            results['by_age']['undated'].append(f)

        # Check for duplicates (by content hash)
        file_hash = get_file_hash(f)
        hash_map[file_hash].append(f)

    # Find duplicates
    for h, files in hash_map.items():
        if len(files) > 1:
            results['duplicates'].append(files)

    # Generate suggestions
    results['suggestions'] = generate_suggestions(results)

    return results

def detect_country(path_lower: str) -> str:
    """Detect country from file path"""
    for country, patterns in COUNTRIES.items():
        if any(p in path_lower for p in patterns):
            return country
    return 'UNKNOWN'

def detect_file_type(name_lower: str) -> str:
    """Detect file type from filename"""
    for ftype, patterns in FILE_TYPES.items():
        if any(p in name_lower for p in patterns):
            return ftype
    return 'OTHER'

def detect_age(fpath: Path) -> str:
    """Detect if file is old based on name or mtime"""
    name = fpath.name

    # Try to extract date from filename
    date_patterns = [
        r'(\d{8})',  # 20251225
        r'(\d{4}-\d{2}-\d{2})',  # 2025-12-25
        r'(\d{4}_\d{2}_\d{2})',  # 2025_12_25
    ]

    for pattern in date_patterns:
        match = re.search(pattern, name)
        if match:
            date_str = match.group(1).replace('-', '').replace('_', '')
            try:
                file_date = datetime.strptime(date_str, '%Y%m%d')
                if file_date < datetime.now() - timedelta(days=30):
                    return 'old'
                return 'recent'
            except Exception:
                pass

    # Fall back to mtime
    mtime = datetime.fromtimestamp(fpath.stat().st_mtime)
    if mtime < datetime.now() - timedelta(days=30):
        return 'old'
    return 'undated'

def get_file_hash(filepath: str, chunk_size: int = 8192) -> str:
    """Get MD5 hash of file for duplicate detection"""
    hasher = hashlib.md5()
    try:
        with open(filepath, 'rb') as f:
            # Only hash first 1MB for speed
            chunk = f.read(1024 * 1024)
            hasher.update(chunk)
    except Exception:
        pass
    return hasher.hexdigest()

def generate_suggestions(results: Dict) -> List[str]:
    """Generate organization suggestions"""
    suggestions = []

    if results['duplicates']:
        suggestions.append(f"Remove {len(results['duplicates'])} duplicate file sets")

    if len(results['by_age']['old']) > 5:
        suggestions.append(f"Archive {len(results['by_age']['old'])} old files (>30 days)")

    if len(results['by_country']['UNKNOWN']) > 3:
        suggestions.append(f"Categorize {len(results['by_country']['UNKNOWN'])} unknown-country files")

    if len(results['by_type']['OTHER']) > 5:
        suggestions.append(f"Review {len(results['by_type']['OTHER'])} uncategorized files")

    return suggestions

# ============================================================
# ORGANIZATION
# ============================================================

def organize(path: str, dry_run: bool = True) -> Dict:
    """Organize files into structured directories"""
    results = {
        'moved': [],
        'skipped': [],
        'errors': [],
    }

    # Create target structure
    target_dirs = {
        'MASTER': os.path.join(path, 'MASTER'),
        'CONTACTS/NORDIC': os.path.join(path, 'CONTACTS/NORDIC'),
        'CONTACTS/EASTERN': os.path.join(path, 'CONTACTS/EASTERN'),
        'CONTACTS/OTHER': os.path.join(path, 'CONTACTS/OTHER'),
        'DAILY': os.path.join(path, 'DAILY'),
        'ARCHIVE': os.path.join(path, 'ARCHIVE'),
        'JOBS': os.path.join(path, 'JOBS'),
    }

    nordic = ['NORWAY', 'SWEDEN', 'DENMARK', 'FINLAND', 'ICELAND']
    eastern = ['POLAND', 'ROMANIA', 'BULGARIA', 'MOLDOVA']

    if not dry_run:
        for d in target_dirs.values():
            os.makedirs(d, exist_ok=True)

    for f in glob.glob(os.path.join(path, '**/*.csv'), recursive=True):
        fpath = Path(f)

        # Skip if already in organized directory
        if any(d in str(fpath) for d in ['MASTER', 'CONTACTS', 'ARCHIVE', 'DAILY']):
            results['skipped'].append(f)
            continue

        name_lower = fpath.name.lower()
        path_lower = str(fpath).lower()

        # Determine target
        country = detect_country(path_lower)
        ftype = detect_file_type(name_lower)
        age = detect_age(fpath)

        # Decide where to move
        if age == 'old':
            target = target_dirs['ARCHIVE']
        elif 'master' in name_lower:
            target = target_dirs['MASTER']
        elif ftype == 'CONTACTS' or 'contact' in name_lower or 'email' in name_lower:
            if country in nordic:
                target = target_dirs['CONTACTS/NORDIC']
            elif country in eastern:
                target = target_dirs['CONTACTS/EASTERN']
            else:
                target = target_dirs['CONTACTS/OTHER']
        elif ftype == 'JOBS':
            target = target_dirs['JOBS']
        elif ftype == 'DAILY':
            target = target_dirs['DAILY']
        else:
            results['skipped'].append(f)
            continue

        # Move file
        target_path = os.path.join(target, fpath.name)

        if not dry_run:
            try:
                shutil.move(f, target_path)
                results['moved'].append((f, target_path))
            except Exception as e:
                results['errors'].append((f, str(e)))
        else:
            results['moved'].append((f, target_path))

    return results

def archive_old(path: str, days: int = 30, dry_run: bool = True) -> Dict:
    """Move old files to archive"""
    results = {'archived': [], 'errors': []}
    archive_dir = os.path.join(path, 'ARCHIVE')

    if not dry_run:
        os.makedirs(archive_dir, exist_ok=True)

    for f in glob.glob(os.path.join(path, '**/*.csv'), recursive=True):
        if 'ARCHIVE' in f:
            continue

        fpath = Path(f)
        age = detect_age(fpath)

        if age == 'old':
            target = os.path.join(archive_dir, fpath.name)
            if not dry_run:
                try:
                    shutil.move(f, target)
                    results['archived'].append((f, target))
                except Exception as e:
                    results['errors'].append((f, str(e)))
            else:
                results['archived'].append((f, target))

    return results

def dedupe(path: str, dry_run: bool = True) -> Dict:
    """Remove duplicate files, keeping newest"""
    results = {'removed': [], 'kept': [], 'errors': []}

    hash_map = defaultdict(list)

    for f in glob.glob(os.path.join(path, '**/*.csv'), recursive=True):
        file_hash = get_file_hash(f)
        mtime = os.path.getmtime(f)
        hash_map[file_hash].append((f, mtime))

    for h, files in hash_map.items():
        if len(files) > 1:
            # Sort by mtime, keep newest
            sorted_files = sorted(files, key=lambda x: -x[1])
            results['kept'].append(sorted_files[0][0])

            for f, _ in sorted_files[1:]:
                if not dry_run:
                    try:
                        os.remove(f)
                        results['removed'].append(f)
                    except Exception as e:
                        results['errors'].append((f, str(e)))
                else:
                    results['removed'].append(f)

    return results

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if not args:
        print(f"""
{'='*60}
FILE ORGANIZER - Intelligent file organization
{'='*60}

Usage: file_organizer.py <command> [path] [--dry-run]

Commands:
  analyze   - Analyze current structure, find issues
  organize  - Organize files into structured directories
  archive   - Move old files (>30 days) to archive
  dedupe    - Find and remove duplicate files

Options:
  --dry-run - Show what would happen without making changes

{STRUCTURE}
""")
        return

    command = args[0]
    path = args[1] if len(args) > 1 and not args[1].startswith('--') else '/mnt/hdd/SCRAPER_DATA'
    dry_run = '--dry-run' in args

    print(f"\n{'='*60}")
    print(f"FILE ORGANIZER - {command.upper()}")
    print(f"Path: {path}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print(f"{'='*60}\n")

    if command == 'analyze':
        results = analyze(path)

        print(f"SUMMARY:")
        print(f"  Total files: {results['total_files']}")
        print(f"  Total size: {results['total_size_mb']:.2f} MB")

        print(f"\nBY COUNTRY:")
        for country, files in sorted(results['by_country'].items(), key=lambda x: -len(x[1])):
            print(f"  {country}: {len(files)}")

        print(f"\nBY TYPE:")
        for ftype, files in sorted(results['by_type'].items(), key=lambda x: -len(x[1])):
            print(f"  {ftype}: {len(files)}")

        print(f"\nBY AGE:")
        print(f"  Recent (<30 days): {len(results['by_age']['recent'])}")
        print(f"  Old (>30 days): {len(results['by_age']['old'])}")
        print(f"  Undated: {len(results['by_age']['undated'])}")

        if results['duplicates']:
            print(f"\nDUPLICATES: {len(results['duplicates'])} sets")
            for files in results['duplicates'][:3]:
                print(f"  - {[Path(f).name for f in files]}")

        if results['suggestions']:
            print(f"\nSUGGESTIONS:")
            for s in results['suggestions']:
                print(f"  - {s}")

    elif command == 'organize':
        results = organize(path, dry_run)

        print(f"RESULTS:")
        print(f"  Would move: {len(results['moved'])}" if dry_run else f"  Moved: {len(results['moved'])}")
        print(f"  Skipped: {len(results['skipped'])}")
        print(f"  Errors: {len(results['errors'])}")

        if results['moved'][:10]:
            print(f"\nMOVES:")
            for src, dst in results['moved'][:10]:
                print(f"  {Path(src).name} -> {Path(dst).parent.name}/")

        if dry_run:
            print(f"\n(Run without --dry-run to apply changes)")

    elif command == 'archive':
        results = archive_old(path, dry_run=dry_run)

        print(f"ARCHIVED: {len(results['archived'])}")
        for src, dst in results['archived'][:10]:
            print(f"  {Path(src).name}")

        if dry_run:
            print(f"\n(Run without --dry-run to apply changes)")

    elif command == 'dedupe':
        results = dedupe(path, dry_run)

        print(f"DUPLICATES FOUND: {len(results['removed']) + len(results['kept'])}")
        print(f"Would remove: {len(results['removed'])}" if dry_run else f"Removed: {len(results['removed'])}")
        print(f"Kept: {len(results['kept'])}")

        if dry_run:
            print(f"\n(Run without --dry-run to apply changes)")

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
