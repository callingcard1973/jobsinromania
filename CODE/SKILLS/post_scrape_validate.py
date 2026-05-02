#!/opt/ACTIVE/INFRA/venv/bin/python3
"""
Post-Scrape Email Validator
Validates emails in newly scraped CSV files before sync to raspi.

Usage:
    python3 post_scrape_validate.py                    # Validate recent files (last 1 hour)
    python3 post_scrape_validate.py --hours 24         # Validate last 24 hours
    python3 post_scrape_validate.py --file path.csv    # Validate specific file
    python3 post_scrape_validate.py --dir /path/       # Validate all CSVs in dir
"""
import sys
import os
import argparse
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS/lib')
from email_validator import validate_email_full, check_mx_record

def find_recent_csvs(base_dir: str, hours: int = 1) -> list:
    """Find CSV files modified in last N hours."""
    cutoff = datetime.now() - timedelta(hours=hours)
    csvs = []
    
    for csv_file in Path(base_dir).rglob('*.csv'):
        if csv_file.stat().st_mtime > cutoff.timestamp():
            csvs.append(csv_file)
    
    return csvs

def validate_csv_file(csv_path: Path, in_place: bool = True) -> dict:
    """Validate emails in CSV file."""
    import csv
    
    stats = {'total': 0, 'valid': 0, 'invalid': 0, 'file': str(csv_path)}
    
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Detect delimiter
        first_line = content.split('\n')[0]
        delimiter = ',' if ',' in first_line else ';' if ';' in first_line else '\t'
        
        lines = content.strip().split('\n')
        if len(lines) < 2:
            return stats
        
        header = lines[0]
        header_lower = header.lower()
        
        # Find email column
        cols = header.split(delimiter)
        email_col = -1
        for i, col in enumerate(cols):
            if 'email' in col.lower():
                email_col = i
                break
        
        if email_col == -1:
            # No email column, skip
            return stats
        
        # Collect unique domains for batch MX check
        domains = set()
        for line in lines[1:]:
            parts = line.split(delimiter)
            if email_col < len(parts):
                email = parts[email_col].strip().strip('"').strip("'")
                if '@' in email:
                    domain = email.split('@')[-1].lower()
                    domains.add(domain)
        
        # Pre-check MX for all domains
        for domain in domains:
            check_mx_record(domain)
        
        # Validate each row
        valid_lines = [header]
        
        for line in lines[1:]:
            stats['total'] += 1
            parts = line.split(delimiter)
            
            if email_col < len(parts):
                email = parts[email_col].strip().strip('"').strip("'")
                result = validate_email_full(email, check_mx=True)
                
                if result['is_valid']:
                    stats['valid'] += 1
                    # Update with cleaned email
                    parts[email_col] = result['email']
                    valid_lines.append(delimiter.join(parts))
                else:
                    stats['invalid'] += 1
            else:
                valid_lines.append(line)
        
        # Write back if in_place
        if in_place and stats['invalid'] > 0:
            # Backup original
            backup_path = csv_path.with_suffix('.csv.pre_validation')
            if not backup_path.exists():
                os.rename(csv_path, backup_path)
            
            with open(csv_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(valid_lines))
        
    except Exception as e:
        stats['error'] = str(e)
    
    return stats

def main():
    parser = argparse.ArgumentParser(description='Post-scrape email validation')
    parser.add_argument('--hours', type=int, default=1, help='Validate files from last N hours')
    parser.add_argument('--file', help='Validate specific file')
    parser.add_argument('--dir', help='Validate all CSVs in directory')
    parser.add_argument('--dry-run', action='store_true', help='Report only, no changes')
    args = parser.parse_args()
    
    print(f"=== Post-Scrape Validation - {datetime.now().strftime('%Y-%m-%d %H:%M')} ===")
    
    if args.file:
        files = [Path(args.file)]
    elif args.dir:
        files = list(Path(args.dir).rglob('*.csv'))
    else:
        # Default: scan SCRAPER_DATA for recent files
        base_dirs = [
            '/mnt/hdd/SCRAPER_DATA/csv',
            '/mnt/hdd/SCRAPER_DATA/CONTACTS',
            '/mnt/hdd/SCRAPER_DATA/MASTER',
        ]
        files = []
        for base in base_dirs:
            if Path(base).exists():
                files.extend(find_recent_csvs(base, args.hours))
    
    if not files:
        print(f"No CSV files found (last {args.hours} hour(s))")
        return
    
    print(f"Found {len(files)} CSV files to validate\n")
    
    total_stats = {'total': 0, 'valid': 0, 'invalid': 0}
    
    for csv_file in files:
        stats = validate_csv_file(csv_file, in_place=not args.dry_run)
        
        if stats['total'] > 0:
            pct = 100 * stats['valid'] / stats['total']
            inv = stats['invalid']
            print(f"  {csv_file.name}: {stats['valid']}/{stats['total']} valid ({pct:.0f}%)" + 
                  (f" - removed {inv}" if inv > 0 else ""))
            
            total_stats['total'] += stats['total']
            total_stats['valid'] += stats['valid']
            total_stats['invalid'] += stats['invalid']
    
    print(f"\n=== Total ===")
    print(f"Emails: {total_stats['total']}")
    print(f"Valid: {total_stats['valid']}")
    print(f"Invalid removed: {total_stats['invalid']}")

if __name__ == '__main__':
    main()
