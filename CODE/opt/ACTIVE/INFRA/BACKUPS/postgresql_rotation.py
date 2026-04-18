#!/usr/bin/env python3
"""
PostgreSQL Backup Rotation Manager
Implements 7-4-12 retention policy with intelligent cleanup

Location: /opt/ACTIVE/INFRA/BACKUPS/postgresql_rotation.py
Created: 2026-04-04
"""

import os
import json
import glob
import logging
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuration ────────────────────────────────────────

BACKUP_BASE = "/opt/BACKUPS/postgresql"
LOG_FILE = "/opt/ACTIVE/INFRA/LOGS/postgresql_rotation.log"
STATE_FILE = "/opt/BACKUPS/postgresql/rotation_state.json"

# Retention policy
RETENTION = {
    'daily': 7,      # Keep 7 daily backups
    'weekly': 4,     # Keep 4 weekly backups (Sunday backups)
    'monthly': 12    # Keep 12 monthly backups (first of month)
}

# ── Logging Setup ───────────────────────────────────────

def setup_logging():
    """Setup logging for rotation operations"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logging()

# ── Rotation Functions ──────────────────────────────────

def parse_backup_filename(filename):
    """Parse backup filename to extract metadata"""
    # Format: {database}_{YYYY-MM-DD}_{HH-MM}.sql.gz
    try:
        base_name = os.path.basename(filename)
        if not base_name.endswith('.sql.gz'):
            return None

        # Remove .sql.gz extension
        name_part = base_name[:-7]
        parts = name_part.rsplit('_', 2)

        if len(parts) != 3:
            return None

        database, date_part, time_part = parts
        timestamp_str = f"{date_part}_{time_part}"
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M")

        return {
            'filename': filename,
            'database': database,
            'timestamp': timestamp,
            'date': timestamp.date(),
            'weekday': timestamp.weekday(),  # 0=Monday, 6=Sunday
            'is_first_of_month': timestamp.day == 1,
            'is_sunday': timestamp.weekday() == 6
        }
    except Exception as e:
        logger.warning(f"Failed to parse filename {filename}: {e}")
        return None

def get_all_backups():
    """Get all backup files with metadata"""
    backup_pattern = os.path.join(BACKUP_BASE, "*_????-??-??_??-??.sql.gz")
    backup_files = glob.glob(backup_pattern)

    backups = []
    for file_path in backup_files:
        metadata = parse_backup_filename(file_path)
        if metadata:
            # Add file size
            try:
                metadata['size'] = os.path.getsize(file_path)
            except OSError:
                metadata['size'] = 0
            backups.append(metadata)

    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x['timestamp'], reverse=True)
    return backups

def categorize_backups(backups):
    """Categorize backups by database and retention type"""
    categorized = {}

    for backup in backups:
        database = backup['database']
        if database not in categorized:
            categorized[database] = {
                'daily': [],
                'weekly': [],
                'monthly': []
            }

        # Always add to daily (most recent ones)
        categorized[database]['daily'].append(backup)

        # Add to weekly if it's a Sunday backup
        if backup['is_sunday']:
            categorized[database]['weekly'].append(backup)

        # Add to monthly if it's first of month
        if backup['is_first_of_month']:
            categorized[database]['monthly'].append(backup)

    return categorized

def apply_retention_policy(categorized_backups):
    """Apply retention policy and identify files for deletion"""
    to_delete = []
    to_keep = []

    for database, categories in categorized_backups.items():
        logger.info(f"Processing retention for database: {database}")

        # Track which files should be kept
        keep_files = set()

        # Keep recent daily backups
        daily_backups = categories['daily'][:RETENTION['daily']]
        for backup in daily_backups:
            keep_files.add(backup['filename'])
        logger.info(f"Keeping {len(daily_backups)} daily backups")

        # Keep weekly backups (Sundays)
        weekly_backups = categories['weekly'][:RETENTION['weekly']]
        for backup in weekly_backups:
            keep_files.add(backup['filename'])
        logger.info(f"Keeping {len(weekly_backups)} weekly backups")

        # Keep monthly backups (first of month)
        monthly_backups = categories['monthly'][:RETENTION['monthly']]
        for backup in monthly_backups:
            keep_files.add(backup['filename'])
        logger.info(f"Keeping {len(monthly_backups)} monthly backups")

        # Determine which files to delete
        all_backups = categories['daily']  # Contains all backups for this database
        for backup in all_backups:
            if backup['filename'] in keep_files:
                to_keep.append(backup)
            else:
                to_delete.append(backup)

    return to_keep, to_delete

def delete_expired_backups(to_delete):
    """Delete expired backup files"""
    total_freed_space = 0
    deleted_count = 0

    for backup in to_delete:
        try:
            file_size = backup['size']
            os.remove(backup['filename'])
            total_freed_space += file_size
            deleted_count += 1
            logger.info(f"Deleted expired backup: {os.path.basename(backup['filename'])}")
        except Exception as e:
            logger.error(f"Failed to delete {backup['filename']}: {e}")

    if deleted_count > 0:
        logger.info(f"Deleted {deleted_count} expired backups, "
                   f"freed {format_size(total_freed_space)} space")

    return deleted_count, total_freed_space

def format_size(bytes_size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

def generate_rotation_report(kept_backups, deleted_backups, freed_space):
    """Generate rotation summary report"""
    # Group by database
    db_summary = {}
    for backup in kept_backups:
        db = backup['database']
        if db not in db_summary:
            db_summary[db] = {'count': 0, 'size': 0}
        db_summary[db]['count'] += 1
        db_summary[db]['size'] += backup['size']

    report = []
    report.append("PostgreSQL Backup Rotation Summary")
    report.append("=" * 40)

    total_size = 0
    for database, stats in db_summary.items():
        report.append(f"{database}: {stats['count']} backups, "
                     f"{format_size(stats['size'])}")
        total_size += stats['size']

    report.append(f"\nTotal kept: {len(kept_backups)} backups, "
                 f"{format_size(total_size)}")

    if deleted_backups:
        report.append(f"Deleted: {len(deleted_backups)} backups, "
                     f"freed {format_size(freed_space)}")

    return "\n".join(report)

def save_rotation_state(kept_backups, deleted_backups):
    """Save rotation state for monitoring"""
    state = {
        'last_rotation': datetime.now().isoformat(),
        'kept_backups': len(kept_backups),
        'deleted_backups': len(deleted_backups),
        'databases': list(set(b['database'] for b in kept_backups)),
        'retention_policy': RETENTION
    }

    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
        logger.info(f"Rotation state saved to {STATE_FILE}")
    except Exception as e:
        logger.error(f"Failed to save rotation state: {e}")

# ── Main Rotation Logic ─────────────────────────────────

def run_rotation(dry_run=False):
    """Run backup rotation with retention policy"""
    logger.info(f"Starting backup rotation (dry_run={dry_run})")

    try:
        # Get all backup files
        all_backups = get_all_backups()
        if not all_backups:
            logger.info("No backup files found")
            return

        logger.info(f"Found {len(all_backups)} backup files")

        # Categorize backups by retention type
        categorized = categorize_backups(all_backups)

        # Apply retention policy
        to_keep, to_delete = apply_retention_policy(categorized)

        logger.info(f"Retention analysis: {len(to_keep)} to keep, "
                   f"{len(to_delete)} to delete")

        freed_space = 0
        if to_delete and not dry_run:
            _, freed_space = delete_expired_backups(to_delete)
        elif to_delete:
            freed_space = sum(b['size'] for b in to_delete)
            logger.info(f"DRY RUN: Would delete {len(to_delete)} files, "
                       f"freeing {format_size(freed_space)}")

        # Generate report
        report = generate_rotation_report(to_keep, to_delete, freed_space)
        logger.info(f"\n{report}")

        # Save state
        if not dry_run:
            save_rotation_state(to_keep, to_delete)

        return {
            'kept': len(to_keep),
            'deleted': len(to_delete),
            'freed_space': freed_space,
            'report': report
        }

    except Exception as e:
        logger.error(f"Rotation failed: {e}")
        raise

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='PostgreSQL Backup Rotation')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be deleted without actually deleting')
    args = parser.parse_args()

    try:
        result = run_rotation(dry_run=args.dry_run)
        print(f"\nRotation complete: {result['kept']} kept, {result['deleted']} deleted")
        if result['freed_space'] > 0:
            print(f"Space freed: {format_size(result['freed_space'])}")
    except Exception as e:
        logger.error(f"Rotation failed: {e}")
        sys.exit(1)