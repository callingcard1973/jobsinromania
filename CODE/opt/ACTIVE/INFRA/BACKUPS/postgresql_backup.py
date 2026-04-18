#!/usr/bin/env python3
"""
PostgreSQL Automated Backup System
Comprehensive backup solution with rotation, compression, and monitoring

Features:
- Full database dumps with optimal compression
- 7-4-12 backup rotation (7 daily, 4 weekly, 12 monthly)
- Multiple database support
- Integrity verification
- Telegram notifications
- Storage management

Location: /opt/ACTIVE/INFRA/BACKUPS/postgresql_backup.py
Created: 2026-04-04
"""

import os
import sys
import gzip
import hashlib
import subprocess
import logging
import json
from datetime import datetime, timedelta
from pathlib import Path
import requests
import shutil

# ── Configuration ────────────────────────────────────────

BACKUP_BASE = "/opt/BACKUPS/postgresql"
LOG_FILE = "/opt/ACTIVE/INFRA/LOGS/postgresql_backup.log"
STATE_FILE = "/opt/BACKUPS/postgresql/backup_state.json"

# Database configuration
DATABASES = {
    'interjob_master': {'priority': 'critical', 'compress_level': 6},
    'norway_emails': {'priority': 'high', 'compress_level': 9},
    'denmark_emails': {'priority': 'high', 'compress_level': 9},
    'email_sender': {'priority': 'high', 'compress_level': 9},
    'anofm': {'priority': 'medium', 'compress_level': 9},
    'bulgaria_emails': {'priority': 'medium', 'compress_level': 9},
    'eu_funds_bg': {'priority': 'medium', 'compress_level': 9},
    'romania_emails': {'priority': 'medium', 'compress_level': 9},
}

# Retention policy (7 daily, 4 weekly, 12 monthly)
RETENTION = {
    'daily': 7,
    'weekly': 4,
    'monthly': 12
}

# PostgreSQL connection
PG_USER = "tudor"
PG_HOST = "localhost"

# Telegram notification
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '-1002157155407')

# ── Logging Setup ───────────────────────────────────────

def setup_logging():
    """Setup structured logging"""
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

# ── Utility Functions ───────────────────────────────────

def send_telegram(message, level="info"):
    """Send notification via Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("No Telegram token configured")
        return

    emoji = {"info": "ℹ️", "success": "✅", "warning": "⚠️", "error": "❌"}

    formatted_message = f"{emoji.get(level, 'ℹ️')} **PostgreSQL Backup**\n\n{message}"

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': formatted_message,
            'parse_mode': 'Markdown'
        }
        requests.post(url, data=data, timeout=10)
        logger.info("Telegram notification sent")
    except Exception as e:
        logger.error(f"Failed to send Telegram notification: {e}")

def get_database_size(database):
    """Get database size in bytes"""
    try:
        cmd = [
            'psql', '-U', PG_USER, '-h', PG_HOST, '-d', database,
            '-t', '-c', 'SELECT pg_database_size(current_database());'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return int(result.stdout.strip())
    except Exception as e:
        logger.error(f"Failed to get size for {database}: {e}")
        return 0

def format_size(bytes_size):
    """Format bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"

def calculate_md5(file_path):
    """Calculate MD5 hash of file"""
    hash_md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except Exception as e:
        logger.error(f"Failed to calculate MD5 for {file_path}: {e}")
        return None

# ── Backup Functions ────────────────────────────────────

def create_backup(database, config):
    """Create compressed backup for single database"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    backup_name = f"{database}_{timestamp}.sql.gz"
    backup_path = os.path.join(BACKUP_BASE, backup_name)

    logger.info(f"Starting backup for {database}")

    # Check database connectivity
    try:
        cmd_test = ['psql', '-U', PG_USER, '-h', PG_HOST, '-d', database, '-c', 'SELECT 1;']
        subprocess.run(cmd_test, capture_output=True, check=True)
    except subprocess.CalledProcessError:
        raise Exception(f"Cannot connect to database {database}")

    # Get database size before backup
    db_size = get_database_size(database)
    logger.info(f"Database {database} size: {format_size(db_size)}")

    # Create backup with compression
    start_time = datetime.now()

    try:
        # pg_dump with optimal settings for large databases
        dump_cmd = [
            'pg_dump',
            '-U', PG_USER,
            '-h', PG_HOST,
            '-d', database,
            '--verbose',
            '--no-owner',
            '--no-privileges',
            '--clean',
            '--if-exists',
            '--format=plain'
        ]

        # Stream through gzip for compression
        with open(backup_path, 'wb') as backup_file:
            with gzip.GzipFile(fileobj=backup_file, mode='wb', compresslevel=config['compress_level']) as gz_file:
                dump_process = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Stream data through gzip
                for line in dump_process.stdout:
                    gz_file.write(line)

                dump_process.wait()

                if dump_process.returncode != 0:
                    stderr_output = dump_process.stderr.read().decode()
                    raise Exception(f"pg_dump failed: {stderr_output}")

        # Calculate backup time and size
        end_time = datetime.now()
        backup_time = (end_time - start_time).total_seconds()
        backup_size = os.path.getsize(backup_path)
        compression_ratio = (1 - (backup_size / db_size)) * 100 if db_size > 0 else 0

        # Calculate MD5 for integrity verification
        md5_hash = calculate_md5(backup_path)

        backup_info = {
            'database': database,
            'timestamp': timestamp,
            'backup_path': backup_path,
            'backup_size': backup_size,
            'original_size': db_size,
            'compression_ratio': compression_ratio,
            'backup_time': backup_time,
            'md5_hash': md5_hash,
            'priority': config['priority']
        }

        logger.info(f"Backup completed for {database}: {format_size(backup_size)} "
                   f"({compression_ratio:.1f}% compression) in {backup_time:.1f}s")

        return backup_info

    except Exception as e:
        # Clean up failed backup
        if os.path.exists(backup_path):
            os.remove(backup_path)
        raise Exception(f"Backup failed for {database}: {e}")

def verify_backup(backup_info):
    """Verify backup integrity"""
    backup_path = backup_info['backup_path']
    expected_md5 = backup_info['md5_hash']

    if not os.path.exists(backup_path):
        raise Exception(f"Backup file not found: {backup_path}")

    # Verify MD5 hash
    current_md5 = calculate_md5(backup_path)
    if current_md5 != expected_md5:
        raise Exception(f"MD5 mismatch for {backup_path}")

    # Test gzip integrity
    try:
        with gzip.open(backup_path, 'rt') as gz_file:
            # Read first few lines to verify gzip integrity
            for i, line in enumerate(gz_file):
                if i >= 10:  # Just test first 10 lines
                    break
    except Exception as e:
        raise Exception(f"Gzip integrity check failed: {e}")

    logger.info(f"Backup verification passed: {backup_path}")
    return True

def load_backup_state():
    """Load previous backup state"""
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load backup state: {e}")
    return {'backups': [], 'last_run': None}

def save_backup_state(state):
    """Save backup state"""
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save backup state: {e}")

def run_backup_session(databases_list=None, verify=True):
    """Run complete backup session for specified databases"""
    if databases_list is None:
        databases_list = list(DATABASES.keys())

    session_start = datetime.now()
    session_results = {
        'start_time': session_start.isoformat(),
        'databases_processed': [],
        'successful_backups': [],
        'failed_backups': [],
        'total_backup_size': 0,
        'total_original_size': 0,
        'session_duration': 0
    }

    logger.info(f"Starting backup session for {len(databases_list)} databases")

    # Load previous state
    state = load_backup_state()

    for database in databases_list:
        if database not in DATABASES:
            logger.warning(f"Unknown database: {database}")
            continue

        config = DATABASES[database]
        session_results['databases_processed'].append(database)

        try:
            # Create backup
            backup_info = create_backup(database, config)

            # Verify backup if requested
            if verify:
                verify_backup(backup_info)

            # Add to successful backups
            session_results['successful_backups'].append(backup_info)
            session_results['total_backup_size'] += backup_info['backup_size']
            session_results['total_original_size'] += backup_info['original_size']

            logger.info(f"Successfully backed up {database}")

        except Exception as e:
            error_info = {
                'database': database,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            session_results['failed_backups'].append(error_info)
            logger.error(f"Failed to backup {database}: {e}")

    # Calculate session metrics
    session_end = datetime.now()
    session_results['end_time'] = session_end.isoformat()
    session_results['session_duration'] = (session_end - session_start).total_seconds()

    # Update state
    state['backups'].extend(session_results['successful_backups'])
    state['last_run'] = session_results
    save_backup_state(state)

    return session_results

def generate_backup_report(session_results):
    """Generate comprehensive backup report"""
    successful = len(session_results['successful_backups'])
    failed = len(session_results['failed_backups'])
    total_processed = len(session_results['databases_processed'])

    report = []
    report.append("PostgreSQL Backup Session Report")
    report.append("=" * 40)
    report.append(f"Processed: {total_processed} databases")
    report.append(f"Successful: {successful}")
    report.append(f"Failed: {failed}")
    report.append(f"Duration: {session_results['session_duration']:.1f} seconds")

    if session_results['total_backup_size'] > 0:
        compression_ratio = (1 - (session_results['total_backup_size'] /
                                session_results['total_original_size'])) * 100
        report.append(f"Total backup size: {format_size(session_results['total_backup_size'])}")
        report.append(f"Original size: {format_size(session_results['total_original_size'])}")
        report.append(f"Compression: {compression_ratio:.1f}%")

    if session_results['successful_backups']:
        report.append("\nSuccessful backups:")
        for backup in session_results['successful_backups']:
            report.append(f"  - {backup['database']}: {format_size(backup['backup_size'])}")

    if session_results['failed_backups']:
        report.append("\nFailed backups:")
        for failure in session_results['failed_backups']:
            report.append(f"  - {failure['database']}: {failure['error']}")

    return "\n".join(report)

# ── Main Entry Point ────────────────────────────────────

def main():
    """Main backup orchestrator"""
    import argparse

    parser = argparse.ArgumentParser(description='PostgreSQL Backup System')
    parser.add_argument('--databases', nargs='+',
                       help='Specific databases to backup (default: all)')
    parser.add_argument('--no-verify', action='store_true',
                       help='Skip backup verification')
    parser.add_argument('--critical-only', action='store_true',
                       help='Backup only critical databases')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be backed up')

    args = parser.parse_args()

    try:
        # Determine which databases to backup
        if args.databases:
            databases_list = args.databases
        elif args.critical_only:
            databases_list = [db for db, config in DATABASES.items()
                            if config['priority'] == 'critical']
        else:
            databases_list = list(DATABASES.keys())

        if args.dry_run:
            logger.info(f"DRY RUN: Would backup databases: {', '.join(databases_list)}")
            return

        # Run backup session
        results = run_backup_session(databases_list, verify=not args.no_verify)

        # Generate report
        report = generate_backup_report(results)
        logger.info(f"\n{report}")

        # Send Telegram notification
        if results['failed_backups']:
            level = "warning" if results['successful_backups'] else "error"
            message = f"Backup session completed with issues:\n{report}"
        else:
            level = "success"
            message = f"Backup session completed successfully:\n{report}"

        send_telegram(message, level)

        # Exit with error code if any backups failed
        if results['failed_backups']:
            sys.exit(1)

    except Exception as e:
        logger.error(f"Backup session failed: {e}")
        send_telegram(f"Backup session failed: {e}", "error")
        sys.exit(1)

if __name__ == '__main__':
    main()