#!/usr/bin/env python3
"""
PostgreSQL Backup System Setup and Management
Initialize, configure, and manage the automated backup system

Features:
- System setup and configuration
- Systemd service installation
- Environment validation
- Manual backup triggers
- Status monitoring

Location: /opt/ACTIVE/INFRA/BACKUPS/setup_postgresql_backup.py
Created: 2026-04-04
"""

import os
import sys
import subprocess
import json
import shutil
from pathlib import Path
import logging

# ── Configuration ────────────────────────────────────────

BACKUP_BASE = "/opt/BACKUPS/postgresql"
SYSTEMD_SERVICE_FILE = "/etc/systemd/system/postgresql-backup.service"
SYSTEMD_TIMER_FILE = "/etc/systemd/system/postgresql-backup.timer"
SERVICE_NAME = "postgresql-backup"
TIMER_NAME = "postgresql-backup.timer"

# ── Logging Setup ───────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ── Setup Functions ─────────────────────────────────────

def check_prerequisites():
    """Check system prerequisites"""
    logger.info("Checking system prerequisites...")

    checks = {
        'postgresql_client': False,
        'pg_dump': False,
        'systemd': False,
        'python3': False,
        'disk_space': False,
        'backup_directory': False
    }

    # Check PostgreSQL client tools
    try:
        subprocess.run(['which', 'psql'], check=True, capture_output=True)
        checks['postgresql_client'] = True
    except subprocess.CalledProcessError:
        logger.error("PostgreSQL client (psql) not found")

    try:
        subprocess.run(['which', 'pg_dump'], check=True, capture_output=True)
        checks['pg_dump'] = True
    except subprocess.CalledProcessError:
        logger.error("pg_dump not found")

    # Check systemd
    try:
        subprocess.run(['systemctl', '--version'], check=True, capture_output=True)
        checks['systemd'] = True
    except subprocess.CalledProcessError:
        logger.error("systemd not available")

    # Check Python 3
    try:
        subprocess.run([sys.executable, '--version'], check=True, capture_output=True)
        checks['python3'] = True
    except subprocess.CalledProcessError:
        logger.error("Python 3 not available")

    # Check disk space (need at least 50GB free for safety)
    try:
        result = subprocess.run(['df', '-BG', '/opt'], capture_output=True, text=True, check=True)
        output_lines = result.stdout.strip().split('\n')
        if len(output_lines) >= 2:
            fields = output_lines[1].split()
            available_gb = int(fields[3].rstrip('G'))
            if available_gb >= 50:
                checks['disk_space'] = True
            else:
                logger.warning(f"Low disk space: {available_gb}GB available (recommend 50GB+)")
        else:
            logger.error("Could not parse disk space information")
    except Exception as e:
        logger.error(f"Failed to check disk space: {e}")

    # Check/create backup directory
    try:
        os.makedirs(BACKUP_BASE, exist_ok=True)
        # Test write permissions
        test_file = os.path.join(BACKUP_BASE, '.write_test')
        with open(test_file, 'w') as f:
            f.write('test')
        os.remove(test_file)
        checks['backup_directory'] = True
    except Exception as e:
        logger.error(f"Cannot create/write to backup directory: {e}")

    # Summary
    passed = sum(checks.values())
    total = len(checks)
    logger.info(f"Prerequisites check: {passed}/{total} passed")

    if passed < total:
        logger.error("Some prerequisites failed. Please resolve before continuing.")
        for check, status in checks.items():
            status_str = "✓" if status else "✗"
            logger.info(f"  {status_str} {check}")
        return False

    logger.info("All prerequisites passed ✓")
    return True

def install_systemd_services():
    """Install systemd service and timer"""
    logger.info("Installing systemd services...")

    # Paths to service files
    service_source = "/opt/ACTIVE/INFRA/BACKUPS/postgresql-backup.service"
    timer_source = "/opt/ACTIVE/INFRA/BACKUPS/postgresql-backup.timer"

    if not os.path.exists(service_source):
        logger.error(f"Service file not found: {service_source}")
        return False

    if not os.path.exists(timer_source):
        logger.error(f"Timer file not found: {timer_source}")
        return False

    try:
        # Copy service files to systemd directory
        shutil.copy2(service_source, SYSTEMD_SERVICE_FILE)
        shutil.copy2(timer_source, SYSTEMD_TIMER_FILE)

        # Set proper permissions
        os.chmod(SYSTEMD_SERVICE_FILE, 0o644)
        os.chmod(SYSTEMD_TIMER_FILE, 0o644)

        # Reload systemd
        subprocess.run(['systemctl', 'daemon-reload'], check=True)

        # Enable timer (this will also enable the service)
        subprocess.run(['systemctl', 'enable', TIMER_NAME], check=True)

        logger.info("Systemd services installed and enabled ✓")
        return True

    except Exception as e:
        logger.error(f"Failed to install systemd services: {e}")
        return False

def start_backup_service():
    """Start the backup timer"""
    logger.info("Starting backup timer...")

    try:
        # Start timer
        subprocess.run(['systemctl', 'start', TIMER_NAME], check=True)

        # Check status
        result = subprocess.run(['systemctl', 'is-active', TIMER_NAME],
                              capture_output=True, text=True)
        if result.stdout.strip() == 'active':
            logger.info("Backup timer started successfully ✓")
            return True
        else:
            logger.error("Backup timer failed to start")
            return False

    except Exception as e:
        logger.error(f"Failed to start backup timer: {e}")
        return False

def test_database_connectivity():
    """Test connectivity to all configured databases"""
    logger.info("Testing database connectivity...")

    databases = [
        'interjob_master', 'norway_emails', 'denmark_emails',
        'email_sender', 'anofm', 'bulgaria_emails', 'eu_funds_bg', 'romania_emails'
    ]

    successful_connections = 0

    for database in databases:
        try:
            cmd = ['psql', '-U', 'tudor', '-h', 'localhost', '-d', database,
                  '-c', 'SELECT version();']
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            logger.info(f"✓ Connected to {database}")
            successful_connections += 1
        except subprocess.CalledProcessError as e:
            logger.warning(f"✗ Failed to connect to {database}: {e}")

    logger.info(f"Database connectivity: {successful_connections}/{len(databases)} successful")
    return successful_connections == len(databases)

def run_test_backup():
    """Run a test backup on a small database"""
    logger.info("Running test backup...")

    test_databases = ['email_sender', 'anofm', 'bulgaria_emails']
    backup_script = "/opt/ACTIVE/INFRA/BACKUPS/postgresql_backup.py"

    for db in test_databases:
        try:
            # Test if database exists and is accessible
            cmd_test = ['psql', '-U', 'tudor', '-h', 'localhost', '-d', db,
                       '-c', 'SELECT count(*) FROM information_schema.tables;']
            subprocess.run(cmd_test, capture_output=True, check=True)

            # Run backup
            logger.info(f"Testing backup for database: {db}")
            cmd_backup = [sys.executable, backup_script, '--databases', db]
            result = subprocess.run(cmd_backup, capture_output=True, text=True, check=True)

            logger.info(f"✓ Test backup successful for {db}")
            logger.info(f"Backup output: {result.stdout}")
            return True

        except subprocess.CalledProcessError as e:
            logger.warning(f"Test backup failed for {db}: {e}")
            continue

    logger.error("All test backups failed")
    return False

def check_environment_variables():
    """Check required environment variables"""
    logger.info("Checking environment variables...")

    required_vars = ['TELEGRAM_BOT_TOKEN']
    optional_vars = ['TELEGRAM_CHAT_ID']

    missing_required = []
    missing_optional = []

    for var in required_vars:
        if not os.environ.get(var):
            missing_required.append(var)

    for var in optional_vars:
        if not os.environ.get(var):
            missing_optional.append(var)

    if missing_required:
        logger.warning(f"Missing required environment variables: {', '.join(missing_required)}")
        logger.info("Note: Backup will work but Telegram notifications will be disabled")

    if missing_optional:
        logger.info(f"Missing optional environment variables: {', '.join(missing_optional)}")

    return len(missing_required) == 0

def show_status():
    """Show backup system status"""
    logger.info("Backup System Status")
    logger.info("=" * 30)

    # Service status
    try:
        result = subprocess.run(['systemctl', 'is-active', SERVICE_NAME],
                              capture_output=True, text=True)
        service_status = result.stdout.strip()
        logger.info(f"Service Status: {service_status}")
    except:
        logger.info("Service Status: unknown")

    # Timer status
    try:
        result = subprocess.run(['systemctl', 'is-active', TIMER_NAME],
                              capture_output=True, text=True)
        timer_status = result.stdout.strip()
        logger.info(f"Timer Status: {timer_status}")
    except:
        logger.info("Timer Status: unknown")

    # Next scheduled run
    try:
        result = subprocess.run(['systemctl', 'list-timers', '--all'],
                              capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'postgresql-backup.timer' in line:
                logger.info(f"Next Run: {line.strip()}")
                break
    except:
        logger.info("Next Run: unknown")

    # Backup directory status
    try:
        backup_files = len([f for f in os.listdir(BACKUP_BASE)
                          if f.endswith('.sql.gz')])
        logger.info(f"Backup Files: {backup_files}")

        # Disk usage
        result = subprocess.run(['du', '-sh', BACKUP_BASE],
                              capture_output=True, text=True)
        if result.returncode == 0:
            size = result.stdout.split()[0]
            logger.info(f"Backup Directory Size: {size}")
    except:
        logger.info("Backup Directory: unknown")

# ── Main Functions ──────────────────────────────────────

def setup_system():
    """Complete system setup"""
    logger.info("Setting up PostgreSQL Backup System...")

    steps = [
        ("Checking prerequisites", check_prerequisites),
        ("Testing database connectivity", test_database_connectivity),
        ("Checking environment variables", check_environment_variables),
        ("Installing systemd services", install_systemd_services),
        ("Starting backup service", start_backup_service),
        ("Running test backup", run_test_backup),
    ]

    failed_steps = []

    for step_name, step_func in steps:
        logger.info(f"\n--- {step_name} ---")
        try:
            if not step_func():
                failed_steps.append(step_name)
        except Exception as e:
            logger.error(f"Step failed with exception: {e}")
            failed_steps.append(step_name)

    # Summary
    logger.info(f"\n--- Setup Complete ---")
    if failed_steps:
        logger.error(f"Setup completed with {len(failed_steps)} failed steps:")
        for step in failed_steps:
            logger.error(f"  - {step}")
        logger.error("Please resolve the issues and run setup again.")
        return False
    else:
        logger.info("Setup completed successfully! ✓")
        logger.info("\nNext steps:")
        logger.info("- Monitor logs: journalctl -u postgresql-backup.timer -f")
        logger.info("- Check status: systemctl status postgresql-backup.timer")
        logger.info("- Manual backup: systemctl start postgresql-backup")
        return True

def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='PostgreSQL Backup System Management')
    parser.add_argument('action', choices=['setup', 'status', 'test', 'start', 'stop'],
                       help='Action to perform')

    args = parser.parse_args()

    if args.action == 'setup':
        success = setup_system()
        sys.exit(0 if success else 1)

    elif args.action == 'status':
        show_status()

    elif args.action == 'test':
        logger.info("Running backup system tests...")
        if test_database_connectivity() and run_test_backup():
            logger.info("All tests passed ✓")
        else:
            logger.error("Some tests failed")
            sys.exit(1)

    elif args.action == 'start':
        if start_backup_service():
            logger.info("Backup service started ✓")
        else:
            logger.error("Failed to start backup service")
            sys.exit(1)

    elif args.action == 'stop':
        try:
            subprocess.run(['systemctl', 'stop', TIMER_NAME], check=True)
            logger.info("Backup timer stopped ✓")
        except Exception as e:
            logger.error(f"Failed to stop backup timer: {e}")
            sys.exit(1)

if __name__ == '__main__':
    main()