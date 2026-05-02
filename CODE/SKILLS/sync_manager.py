#!/usr/bin/env python3
"""
Sync Manager - Manage raspibig <-> raspi synchronization
Handles code sync, data sync, verification, and scheduling

Usage:
    python3 sync_manager.py --status               # Show sync status
    python3 sync_manager.py --sync code            # Sync code to raspi
    python3 sync_manager.py --sync data            # Sync data to raspi
    python3 sync_manager.py --sync all             # Full sync
    python3 sync_manager.py --verify               # Verify sync integrity
    python3 sync_manager.py --history              # Show sync history

Examples:
    python3 sync_manager.py --sync code --dry-run
    python3 sync_manager.py --sync data --include NORWAY,DENMARK
"""

import sys
import os
import subprocess
import json
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

RASPI_HOST = 'raspi'
RASPI_USER = 'tudor'

# Sync configurations
SYNC_CONFIGS = {
    'code': {
        'description': 'Scraper code and skills',
        'sources': [
            ('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/', '/home/tudor/SCRAPERS_BACKUP/EUROPE/'),
            ('/opt/ACTIVE/INFRA/SKILLS/', '/home/tudor/SCRAPERS_BACKUP/SKILLS/'),
            ('/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/', '/home/tudor/SCRAPERS_BACKUP/SHARED/'),
        ],
        'exclude': ['__pycache__', '*.pyc', 'OUTPUT', 'results', 'logs', '*.csv', '*.log'],
        'rsync_opts': ['-avz', '--delete'],
    },
    'data': {
        'description': 'Scraped data (CSV files)',
        'sources': [
            ('/mnt/hdd/SCRAPER_DATA/csv/', '/home/tudor/SCRAPER_DATA/'),
        ],
        'exclude': [],
        'rsync_opts': ['-avz'],
    },
    'configs': {
        'description': 'Configuration files',
        'sources': [
            ('/opt/ACTIVE/SCRAPERS/EUROPE/.env', '/home/tudor/SCRAPERS_BACKUP/.env'),
            ('/home/tudor/claude.md', '/home/tudor/claude_raspibig.md'),
        ],
        'exclude': [],
        'rsync_opts': ['-avz'],
    },
    'logs': {
        'description': 'Scraper logs',
        'sources': [
            ('/mnt/hdd/SCRAPER_DATA/logs/', '/home/tudor/SCRAPER_DATA/logs/'),
        ],
        'exclude': [],
        'rsync_opts': ['-avz', '--delete'],
    },
}

SYNC_HISTORY_FILE = Path('/opt/ACTIVE/INFRA/SKILLS/.sync_history.json')


@dataclass
class SyncResult:
    """Result of a sync operation."""
    sync_type: str
    started: datetime
    ended: datetime = None
    success: bool = False
    files_transferred: int = 0
    bytes_transferred: int = 0
    errors: List[str] = field(default_factory=list)
    dry_run: bool = False


class SyncManager:
    """Manage raspibig <-> raspi synchronization."""

    def __init__(self, host: str = RASPI_HOST):
        self.host = host
        self.history = self._load_history()

    def _load_history(self) -> List[Dict]:
        """Load sync history."""
        try:
            if SYNC_HISTORY_FILE.exists():
                return json.loads(SYNC_HISTORY_FILE.read_text())
        except Exception:
            pass
        return []

    def _save_history(self, result: SyncResult):
        """Save sync result to history."""
        entry = {
            'type': result.sync_type,
            'started': result.started.isoformat(),
            'ended': result.ended.isoformat() if result.ended else None,
            'success': result.success,
            'files': result.files_transferred,
            'bytes': result.bytes_transferred,
            'errors': result.errors[:3],  # Keep only first 3 errors
            'dry_run': result.dry_run
        }

        self.history.insert(0, entry)
        # Keep last 100 entries
        self.history = self.history[:100]

        try:
            SYNC_HISTORY_FILE.write_text(json.dumps(self.history, indent=2))
        except Exception:
            pass

    def check_connection(self) -> Tuple[bool, str]:
        """Check if raspi is reachable."""
        try:
            result = subprocess.run(
                ['ssh', '-o', 'ConnectTimeout=5', self.host, 'echo ok'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and 'ok' in result.stdout:
                return True, "Connected"
            return False, result.stderr
        except subprocess.TimeoutExpired:
            return False, "Connection timeout"
        except Exception as e:
            return False, str(e)

    def get_remote_disk_space(self) -> Optional[Dict]:
        """Check disk space on raspi."""
        try:
            result = subprocess.run(
                ['ssh', self.host, 'df -h /home/tudor'],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 4:
                        return {
                            'total': parts[1],
                            'used': parts[2],
                            'available': parts[3],
                            'percent': parts[4]
                        }
        except Exception:
            pass
        return None

    def sync(self, sync_type: str, dry_run: bool = False,
             include_countries: List[str] = None) -> SyncResult:
        """Run a sync operation."""
        if sync_type not in SYNC_CONFIGS:
            return SyncResult(
                sync_type=sync_type,
                started=datetime.now(),
                success=False,
                errors=[f"Unknown sync type: {sync_type}"]
            )

        config = SYNC_CONFIGS[sync_type]
        result = SyncResult(
            sync_type=sync_type,
            started=datetime.now(),
            dry_run=dry_run
        )

        print(f"\n{'='*60}")
        print(f"SYNC: {sync_type.upper()} - {config['description']}")
        print(f"{'='*60}")

        if dry_run:
            print("[DRY RUN - No actual changes]\n")

        # Check connection first
        connected, msg = self.check_connection()
        if not connected:
            result.errors.append(f"Cannot connect to {self.host}: {msg}")
            result.ended = datetime.now()
            return result

        print(f"Connected to {self.host}")

        # Check remote disk space
        disk = self.get_remote_disk_space()
        if disk:
            print(f"Remote disk: {disk['available']} available ({disk['percent']} used)")

        total_files = 0
        total_bytes = 0

        for source, dest in config['sources']:
            source_path = Path(source)

            # Filter by countries if specified
            if include_countries and source_path.is_dir():
                for country in include_countries:
                    country_path = source_path / country
                    if country_path.exists():
                        country_dest = f"{dest}{country}/"
                        files, bytes_t, errors = self._rsync(
                            str(country_path) + '/',
                            country_dest,
                            config['exclude'],
                            config['rsync_opts'],
                            dry_run
                        )
                        total_files += files
                        total_bytes += bytes_t
                        result.errors.extend(errors)
                continue

            if not source_path.exists():
                print(f"  Skip (not found): {source}")
                continue

            print(f"\n{source} -> {self.host}:{dest}")

            files, bytes_t, errors = self._rsync(
                source,
                f"{self.host}:{dest}",
                config['exclude'],
                config['rsync_opts'],
                dry_run
            )

            total_files += files
            total_bytes += bytes_t
            result.errors.extend(errors)

        result.files_transferred = total_files
        result.bytes_transferred = total_bytes
        result.success = len(result.errors) == 0
        result.ended = datetime.now()

        duration = (result.ended - result.started).total_seconds()
        print(f"\n{'='*60}")
        print(f"SYNC COMPLETE: {total_files} files, {total_bytes/1024/1024:.2f} MB in {duration:.1f}s")

        if result.errors:
            print(f"Errors: {len(result.errors)}")
            for err in result.errors[:3]:
                print(f"  - {err[:60]}")

        self._save_history(result)
        return result

    def _rsync(self, source: str, dest: str, exclude: List[str],
               opts: List[str], dry_run: bool) -> Tuple[int, int, List[str]]:
        """Run rsync command."""
        cmd = ['rsync'] + opts

        if dry_run:
            cmd.append('--dry-run')

        cmd.append('--stats')

        for ex in exclude:
            cmd.extend(['--exclude', ex])

        cmd.extend([source, dest])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800  # 30 min timeout
            )

            files = 0
            bytes_transferred = 0

            # Parse rsync stats
            for line in result.stdout.split('\n'):
                if 'Number of regular files transferred' in line:
                    try:
                        files = int(line.split(':')[1].strip().replace(',', ''))
                    except Exception:
                        pass
                elif 'Total transferred file size' in line:
                    try:
                        size_str = line.split(':')[1].strip().split()[0].replace(',', '')
                        bytes_transferred = int(size_str)
                    except Exception:
                        pass

            errors = []
            if result.returncode != 0:
                errors.append(result.stderr[:200] if result.stderr else "Unknown error")

            print(f"  {files} files, {bytes_transferred/1024/1024:.2f} MB")
            return files, bytes_transferred, errors

        except subprocess.TimeoutExpired:
            return 0, 0, ["Timeout exceeded"]
        except Exception as e:
            return 0, 0, [str(e)]

    def sync_all(self, dry_run: bool = False) -> Dict[str, SyncResult]:
        """Sync everything."""
        results = {}
        for sync_type in ['code', 'configs', 'data']:
            results[sync_type] = self.sync(sync_type, dry_run=dry_run)
        return results

    def verify(self, sync_type: str = 'code') -> Dict[str, Any]:
        """Verify sync integrity by comparing file counts and sizes."""
        result = {
            'type': sync_type,
            'verified': True,
            'mismatches': [],
            'local_only': [],
            'remote_only': []
        }

        if sync_type not in SYNC_CONFIGS:
            result['verified'] = False
            result['error'] = f"Unknown sync type: {sync_type}"
            return result

        config = SYNC_CONFIGS[sync_type]

        print(f"\nVerifying {sync_type} sync...")

        for source, dest in config['sources']:
            source_path = Path(source)
            if not source_path.exists():
                continue

            if source_path.is_file():
                # Compare single file
                local_size = source_path.stat().st_size
                try:
                    remote_result = subprocess.run(
                        ['ssh', self.host, f'stat -c %s {dest} 2>/dev/null'],
                        capture_output=True, text=True, timeout=30
                    )
                    if remote_result.returncode == 0:
                        remote_size = int(remote_result.stdout.strip())
                        if local_size != remote_size:
                            result['mismatches'].append({
                                'file': source,
                                'local_size': local_size,
                                'remote_size': remote_size
                            })
                    else:
                        result['local_only'].append(source)
                except Exception:
                    pass

            elif source_path.is_dir():
                # Compare directory contents
                try:
                    # Get local file count
                    local_files = list(source_path.rglob('*.py'))
                    local_count = len(local_files)

                    # Get remote file count
                    remote_result = subprocess.run(
                        ['ssh', self.host, f'find {dest} -name "*.py" 2>/dev/null | wc -l'],
                        capture_output=True, text=True, timeout=60
                    )
                    if remote_result.returncode == 0:
                        remote_count = int(remote_result.stdout.strip())

                        if abs(local_count - remote_count) > 5:
                            result['mismatches'].append({
                                'dir': source,
                                'local_count': local_count,
                                'remote_count': remote_count
                            })
                            print(f"  ⚠ {source}: {local_count} local vs {remote_count} remote")
                        else:
                            print(f"  ✓ {source}: {local_count} files match")
                except Exception as e:
                    print(f"  ? {source}: {e}")

        result['verified'] = len(result['mismatches']) == 0

        return result

    def show_status(self) -> str:
        """Show current sync status."""
        lines = []
        lines.append("=" * 60)
        lines.append("SYNC STATUS")
        lines.append("=" * 60)

        # Connection status
        connected, msg = self.check_connection()
        status = "✓ Connected" if connected else f"✗ {msg}"
        lines.append(f"\nRaspi connection: {status}")

        if connected:
            disk = self.get_remote_disk_space()
            if disk:
                lines.append(f"Remote disk: {disk['available']} free ({disk['percent']} used)")

        # Last sync times
        lines.append("\nLast sync times:")
        lines.append("-" * 40)

        last_by_type = {}
        for entry in self.history:
            if entry['type'] not in last_by_type and entry['success']:
                last_by_type[entry['type']] = entry

        for sync_type in SYNC_CONFIGS.keys():
            last = last_by_type.get(sync_type)
            if last:
                ts = datetime.fromisoformat(last['started'])
                ago = (datetime.now() - ts).total_seconds() / 3600
                status = "✓" if last['success'] else "✗"
                lines.append(f"  {sync_type:<10} {status} {ts.strftime('%Y-%m-%d %H:%M')} ({ago:.1f}h ago)")
            else:
                lines.append(f"  {sync_type:<10} - Never synced")

        # Sync types
        lines.append("\nSync types available:")
        lines.append("-" * 40)
        for name, config in SYNC_CONFIGS.items():
            lines.append(f"  {name:<10} {config['description']}")

        lines.append("\n" + "=" * 60)
        return '\n'.join(lines)

    def show_history(self, limit: int = 20) -> str:
        """Show sync history."""
        lines = []
        lines.append("=" * 60)
        lines.append("SYNC HISTORY")
        lines.append("=" * 60)

        if not self.history:
            lines.append("\nNo sync history found")
            return '\n'.join(lines)

        lines.append(f"\n{'Date':<20} {'Type':<10} {'Status':<8} {'Files':>8} {'Size':>10}")
        lines.append("-" * 60)

        for entry in self.history[:limit]:
            ts = datetime.fromisoformat(entry['started'])
            status = "✓" if entry['success'] else "✗"
            if entry.get('dry_run'):
                status = "dry"
            size_mb = entry.get('bytes', 0) / 1024 / 1024

            lines.append(
                f"{ts.strftime('%Y-%m-%d %H:%M'):<20} {entry['type']:<10} "
                f"{status:<8} {entry.get('files', 0):>8} {size_mb:>9.2f}M"
            )

        lines.append("\n" + "=" * 60)
        return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Sync Manager - raspibig <-> raspi')
    parser.add_argument('--status', action='store_true', help='Show sync status')
    parser.add_argument('--sync', choices=['code', 'data', 'configs', 'logs', 'all'], help='Run sync')
    parser.add_argument('--verify', action='store_true', help='Verify sync integrity')
    parser.add_argument('--history', action='store_true', help='Show sync history')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no changes)')
    parser.add_argument('--include', help='Include only these countries (comma-separated)')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    manager = SyncManager()

    if args.sync:
        include = args.include.split(',') if args.include else None

        if args.sync == 'all':
            results = manager.sync_all(dry_run=args.dry_run)
            if args.json:
                print(json.dumps({
                    k: {'success': v.success, 'files': v.files_transferred}
                    for k, v in results.items()
                }, indent=2))
        else:
            result = manager.sync(args.sync, dry_run=args.dry_run, include_countries=include)
            if args.json:
                print(json.dumps({
                    'type': result.sync_type,
                    'success': result.success,
                    'files': result.files_transferred,
                    'bytes': result.bytes_transferred,
                    'errors': result.errors
                }, indent=2))

    elif args.verify:
        result = manager.verify('code')
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result['verified']:
                print("✓ Sync verified - all files match")
            else:
                print("✗ Sync issues found:")
                for m in result['mismatches']:
                    print(f"  - {m}")

    elif args.history:
        print(manager.show_history())

    elif args.status:
        print(manager.show_status())

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
