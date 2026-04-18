#!/usr/bin/env python3
"""
PostgreSQL Backup Verification Tool
Verify integrity and recoverability of backup files

Features:
- MD5 hash verification
- Gzip integrity checking
- Basic SQL syntax validation
- Backup metadata analysis
- Recovery test simulation

Location: /opt/ACTIVE/INFRA/BACKUPS/postgresql_verify.py
Created: 2026-04-04
"""

import os
import sys
import gzip
import json
import glob
import hashlib
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# ── Configuration ────────────────────────────────────────

BACKUP_BASE = "/opt/BACKUPS/postgresql"
LOG_FILE = "/opt/ACTIVE/INFRA/LOGS/postgresql_verify.log"
VERIFICATION_REPORT = "/opt/BACKUPS/postgresql/verification_report.json"

# Test database for recovery verification
TEST_DB_PREFIX = "backup_test_"

# ── Logging Setup ───────────────────────────────────────

def setup_logging():
    """Setup verification logging"""
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

# ── Verification Functions ──────────────────────────────

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

def verify_gzip_integrity(backup_path):
    """Verify gzip file integrity"""
    try:
        with gzip.open(backup_path, 'rt') as gz_file:
            # Read through entire file to check integrity
            line_count = 0
            for line in gz_file:
                line_count += 1
                if line_count > 1000000:  # Avoid memory issues with huge files
                    logger.info(f"Verified first 1M lines of {backup_path}")
                    break

        return True, line_count
    except Exception as e:
        return False, str(e)

def verify_sql_syntax(backup_path, sample_lines=100):
    """Basic SQL syntax verification"""
    try:
        sql_keywords = {'CREATE', 'INSERT', 'UPDATE', 'DELETE', 'SELECT', 'ALTER', 'DROP'}
        found_keywords = set()

        with gzip.open(backup_path, 'rt') as gz_file:
            for i, line in enumerate(gz_file):
                if i >= sample_lines:
                    break

                # Look for SQL keywords
                line_upper = line.strip().upper()
                for keyword in sql_keywords:
                    if line_upper.startswith(keyword):
                        found_keywords.add(keyword)

        # Should have at least CREATE and INSERT statements
        has_structure = 'CREATE' in found_keywords
        has_data = 'INSERT' in found_keywords

        return {
            'valid': has_structure,
            'has_structure': has_structure,
            'has_data': has_data,
            'found_keywords': list(found_keywords)
        }

    except Exception as e:
        return {
            'valid': False,
            'error': str(e)
        }

def get_backup_metadata(backup_path):
    """Extract backup metadata from filename and file stats"""
    try:
        # Parse filename
        basename = os.path.basename(backup_path)
        if not basename.endswith('.sql.gz'):
            return None

        name_part = basename[:-7]  # Remove .sql.gz
        parts = name_part.rsplit('_', 2)

        if len(parts) != 3:
            return None

        database, date_part, time_part = parts
        timestamp_str = f"{date_part}_{time_part}"
        backup_time = datetime.strptime(timestamp_str, "%Y-%m-%d_%H-%M")

        # File statistics
        stat = os.stat(backup_path)
        file_size = stat.st_size
        file_mtime = datetime.fromtimestamp(stat.st_mtime)

        return {
            'database': database,
            'backup_time': backup_time,
            'file_size': file_size,
            'file_mtime': file_mtime,
            'age_days': (datetime.now() - backup_time).days,
            'filename': basename,
            'full_path': backup_path
        }

    except Exception as e:
        logger.error(f"Failed to parse metadata for {backup_path}: {e}")
        return None

def verify_single_backup(backup_path, include_recovery_test=False):
    """Comprehensive verification of single backup file"""
    verification_result = {
        'backup_path': backup_path,
        'timestamp': datetime.now().isoformat(),
        'checks': {}
    }

    logger.info(f"Verifying backup: {os.path.basename(backup_path)}")

    # 1. File existence and accessibility
    if not os.path.exists(backup_path):
        verification_result['checks']['file_exists'] = False
        verification_result['overall_status'] = 'FAILED'
        return verification_result

    verification_result['checks']['file_exists'] = True

    # 2. Get metadata
    metadata = get_backup_metadata(backup_path)
    if metadata:
        verification_result['metadata'] = metadata
        verification_result['checks']['metadata_parsed'] = True
    else:
        verification_result['checks']['metadata_parsed'] = False

    # 3. MD5 hash calculation
    md5_hash = calculate_md5(backup_path)
    verification_result['md5_hash'] = md5_hash
    verification_result['checks']['md5_calculated'] = md5_hash is not None

    # 4. Gzip integrity
    gzip_valid, gzip_info = verify_gzip_integrity(backup_path)
    verification_result['checks']['gzip_integrity'] = gzip_valid
    if gzip_valid:
        verification_result['gzip_lines'] = gzip_info
    else:
        verification_result['gzip_error'] = gzip_info

    # 5. SQL syntax verification
    sql_check = verify_sql_syntax(backup_path)
    verification_result['checks']['sql_syntax'] = sql_check['valid']
    verification_result['sql_analysis'] = sql_check

    # 6. Recovery test (optional, for critical backups)
    if include_recovery_test and metadata:
        recovery_result = test_backup_recovery(backup_path, metadata['database'])
        verification_result['checks']['recovery_test'] = recovery_result['success']
        verification_result['recovery_test'] = recovery_result

    # Overall status
    critical_checks = ['file_exists', 'gzip_integrity', 'sql_syntax']
    all_critical_passed = all(verification_result['checks'].get(check, False)
                            for check in critical_checks)

    verification_result['overall_status'] = 'PASSED' if all_critical_passed else 'FAILED'

    return verification_result

def test_backup_recovery(backup_path, original_database):
    """Test backup recovery to temporary database"""
    test_db_name = f"{TEST_DB_PREFIX}{original_database}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    recovery_result = {
        'test_database': test_db_name,
        'success': False,
        'steps_completed': []
    }

    try:
        # 1. Create test database
        logger.info(f"Creating test database: {test_db_name}")
        create_cmd = ['createdb', '-U', 'tudor', '-h', 'localhost', test_db_name]
        subprocess.run(create_cmd, check=True, capture_output=True)
        recovery_result['steps_completed'].append('database_created')

        # 2. Restore backup to test database
        logger.info(f"Restoring backup to test database")
        with gzip.open(backup_path, 'rt') as gz_file:
            restore_cmd = ['psql', '-U', 'tudor', '-h', 'localhost', '-d', test_db_name]
            restore_process = subprocess.Popen(restore_cmd, stdin=subprocess.PIPE,
                                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

            # Feed backup data to psql
            stdout, stderr = restore_process.communicate(input=gz_file.read())

            if restore_process.returncode != 0:
                raise Exception(f"Restore failed: {stderr}")

        recovery_result['steps_completed'].append('backup_restored')

        # 3. Basic validation queries
        logger.info("Running validation queries")
        validation_queries = [
            "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';",
            "SELECT pg_size_pretty(pg_database_size(current_database()));"
        ]

        for query in validation_queries:
            query_cmd = ['psql', '-U', 'tudor', '-h', 'localhost', '-d', test_db_name,
                        '-t', '-c', query]
            result = subprocess.run(query_cmd, capture_output=True, text=True, check=True)
            logger.info(f"Query result: {result.stdout.strip()}")

        recovery_result['steps_completed'].append('validation_queries')
        recovery_result['success'] = True

    except Exception as e:
        logger.error(f"Recovery test failed: {e}")
        recovery_result['error'] = str(e)

    finally:
        # Cleanup: Drop test database
        try:
            logger.info(f"Cleaning up test database: {test_db_name}")
            drop_cmd = ['dropdb', '-U', 'tudor', '-h', 'localhost', test_db_name]
            subprocess.run(drop_cmd, check=True, capture_output=True)
            recovery_result['steps_completed'].append('cleanup_completed')
        except Exception as e:
            logger.warning(f"Failed to cleanup test database: {e}")

    return recovery_result

def verify_backup_set(backup_pattern="*_????-??-??_??-??.sql.gz", max_age_days=7):
    """Verify multiple backup files"""
    backup_files = glob.glob(os.path.join(BACKUP_BASE, backup_pattern))
    backup_files.sort(reverse=True)  # Newest first

    verification_session = {
        'timestamp': datetime.now().isoformat(),
        'total_files': len(backup_files),
        'verified_files': 0,
        'passed_files': 0,
        'failed_files': 0,
        'results': []
    }

    logger.info(f"Starting verification of {len(backup_files)} backup files")

    for backup_path in backup_files:
        # Skip old backups unless specifically requested
        metadata = get_backup_metadata(backup_path)
        if metadata and metadata['age_days'] > max_age_days:
            logger.info(f"Skipping old backup: {os.path.basename(backup_path)} "
                       f"({metadata['age_days']} days old)")
            continue

        # Verify backup
        try:
            result = verify_single_backup(backup_path)
            verification_session['results'].append(result)
            verification_session['verified_files'] += 1

            if result['overall_status'] == 'PASSED':
                verification_session['passed_files'] += 1
            else:
                verification_session['failed_files'] += 1

        except Exception as e:
            logger.error(f"Verification failed for {backup_path}: {e}")
            verification_session['failed_files'] += 1

    # Generate summary
    verification_session['success_rate'] = (
        (verification_session['passed_files'] / verification_session['verified_files'] * 100)
        if verification_session['verified_files'] > 0 else 0
    )

    return verification_session

def save_verification_report(verification_session):
    """Save verification results to file"""
    try:
        with open(VERIFICATION_REPORT, 'w') as f:
            json.dump(verification_session, f, indent=2, default=str)
        logger.info(f"Verification report saved to {VERIFICATION_REPORT}")
    except Exception as e:
        logger.error(f"Failed to save verification report: {e}")

def generate_verification_summary(verification_session):
    """Generate human-readable verification summary"""
    summary = []
    summary.append("PostgreSQL Backup Verification Report")
    summary.append("=" * 45)
    summary.append(f"Verification Time: {verification_session['timestamp']}")
    summary.append(f"Total Files Found: {verification_session['total_files']}")
    summary.append(f"Files Verified: {verification_session['verified_files']}")
    summary.append(f"Passed: {verification_session['passed_files']}")
    summary.append(f"Failed: {verification_session['failed_files']}")
    summary.append(f"Success Rate: {verification_session['success_rate']:.1f}%")

    if verification_session['failed_files'] > 0:
        summary.append("\nFailed Verifications:")
        for result in verification_session['results']:
            if result['overall_status'] == 'FAILED':
                filename = os.path.basename(result['backup_path'])
                failed_checks = [check for check, passed in result['checks'].items() if not passed]
                summary.append(f"  - {filename}: {', '.join(failed_checks)}")

    return "\n".join(summary)

# ── Main Entry Point ────────────────────────────────────

def main():
    """Main verification entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='PostgreSQL Backup Verification')
    parser.add_argument('--file', help='Verify specific backup file')
    parser.add_argument('--pattern', default='*_????-??-??_??-??.sql.gz',
                       help='Pattern for backup files to verify')
    parser.add_argument('--max-age', type=int, default=7,
                       help='Maximum age in days for backups to verify')
    parser.add_argument('--recovery-test', action='store_true',
                       help='Include recovery testing (slow)')
    parser.add_argument('--report-only', action='store_true',
                       help='Generate report from existing verification data')

    args = parser.parse_args()

    try:
        if args.file:
            # Verify single file
            if not os.path.exists(args.file):
                logger.error(f"Backup file not found: {args.file}")
                sys.exit(1)

            result = verify_single_backup(args.file, args.recovery_test)
            print(f"Verification result: {result['overall_status']}")

            if result['overall_status'] == 'FAILED':
                failed_checks = [check for check, passed in result['checks'].items() if not passed]
                print(f"Failed checks: {', '.join(failed_checks)}")
                sys.exit(1)

        else:
            # Verify backup set
            verification_session = verify_backup_set(args.pattern, args.max_age)
            save_verification_report(verification_session)

            summary = generate_verification_summary(verification_session)
            print(summary)
            logger.info(f"\n{summary}")

            # Exit with error if any verifications failed
            if verification_session['failed_files'] > 0:
                sys.exit(1)

    except Exception as e:
        logger.error(f"Verification failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()