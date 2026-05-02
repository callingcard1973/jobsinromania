#!/usr/bin/env python3
"""
Backup & Restore Skill - Full backup/restore for scrapers, skills, configs
Supports local and remote (raspi) backups

Usage:
    python3 backup_restore.py --backup               # Full backup to raspi
    python3 backup_restore.py --backup --local       # Local backup only
    python3 backup_restore.py --restore <backup_id>  # Restore from backup
    python3 backup_restore.py --list                 # List available backups
    python3 backup_restore.py --verify               # Verify backup integrity

Examples:
    python3 backup_restore.py --backup --include scrapers,skills
    python3 backup_restore.py --restore 2025-01-15_120000
"""

import sys
import os
import subprocess
import json
import hashlib
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

BACKUP_LOCAL_DIR = Path('/mnt/usb/BACKUPS')
BACKUP_REMOTE_HOST = 'raspi'
BACKUP_REMOTE_DIR = '/home/tudor/BACKUPS/raspibig'

# What to backup
BACKUP_SOURCES = {
    'scrapers': {
        'path': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE',
        'include': ['*.py', '*.md', '*.json', '*.yaml', '*.txt', '.env'],
        'exclude': ['__pycache__', '*.pyc', 'OUTPUT', 'results', 'logs', '*.csv'],
    },
    'skills': {
        'path': '/opt/ACTIVE/INFRA/SKILLS',
        'include': ['*.py', '*.md', '*.json'],
        'exclude': ['__pycache__', '*.pyc'],
    },
    'shared': {
        'path': '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED',
        'include': ['*.py', '*.sh', '*.md'],
        'exclude': ['__pycache__', '*.pyc'],
    },
    'configs': {
        'path': '/opt/ACTIVE/SCRAPERS/EUROPE',
        'include': ['.env', 'config.json', '*.yaml'],
        'exclude': [],
        'max_depth': 1,
    },
    'cron': {
        'path': '/var/spool/cron/crontabs',
        'include': ['*'],
        'exclude': [],
    },
    'claude_md': {
        'paths': ['/home/tudor/claude.md', '/opt/CLAUDE.md'],
    },
}


@dataclass
class BackupInfo:
    """Information about a backup."""
    id: str
    timestamp: datetime
    size_bytes: int
    components: List[str]
    location: str  # local or remote
    checksum: str
    manifest: Dict[str, int] = field(default_factory=dict)


class BackupRestore:
    """Full backup and restore system."""

    def __init__(self, local_only: bool = False):
        self.local_only = local_only
        self.backup_dir = BACKUP_LOCAL_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def _get_file_hash(self, filepath: Path) -> str:
        """Get MD5 hash of a file."""
        try:
            md5 = hashlib.md5()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5.update(chunk)
            return md5.hexdigest()
        except Exception:
            return ""

    def _run_rsync(self, source: str, dest: str, exclude: List[str] = None) -> bool:
        """Run rsync with given parameters."""
        cmd = ['rsync', '-avz', '--delete']
        if exclude:
            for ex in exclude:
                cmd.extend(['--exclude', ex])
        cmd.extend([source, dest])

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return result.returncode == 0
        except Exception as e:
            print(f"  rsync failed: {e}")
            return False

    def create_backup(self, components: List[str] = None) -> Optional[BackupInfo]:
        """Create a full backup."""
        if components is None:
            components = list(BACKUP_SOURCES.keys())

        timestamp = datetime.now()
        backup_id = timestamp.strftime('%Y-%m-%d_%H%M%S')
        backup_path = self.backup_dir / f"backup_{backup_id}.tar.gz"

        print(f"\n{'='*60}")
        print(f"CREATING BACKUP: {backup_id}")
        print(f"{'='*60}")
        print(f"Components: {', '.join(components)}")

        manifest = {}
        files_to_backup = []

        # Collect files
        for comp_name in components:
            if comp_name not in BACKUP_SOURCES:
                print(f"  Unknown component: {comp_name}")
                continue

            comp = BACKUP_SOURCES[comp_name]
            print(f"\n[{comp_name}]")

            # Handle single path or multiple paths
            paths = comp.get('paths', [comp.get('path')])
            if not paths or paths == [None]:
                continue

            for path_str in paths:
                path = Path(path_str)
                if not path.exists():
                    print(f"  Skip (not found): {path}")
                    continue

                if path.is_file():
                    files_to_backup.append((path, f"{comp_name}/{path.name}"))
                    manifest[str(path)] = path.stat().st_size
                    print(f"  + {path.name}")
                elif path.is_dir():
                    include_patterns = comp.get('include', ['*'])
                    exclude_patterns = comp.get('exclude', [])

                    for pattern in include_patterns:
                        for file in path.rglob(pattern):
                            if file.is_file():
                                # Check exclusions
                                skip = False
                                for ex in exclude_patterns:
                                    if ex in str(file) or file.match(ex):
                                        skip = True
                                        break
                                if skip:
                                    continue

                                rel_path = file.relative_to(path)
                                arc_name = f"{comp_name}/{rel_path}"
                                files_to_backup.append((file, arc_name))
                                manifest[str(file)] = file.stat().st_size

                    file_count = len([f for f, a in files_to_backup if a.startswith(f"{comp_name}/")])
                    print(f"  + {file_count} files from {path}")

        if not files_to_backup:
            print("\nNo files to backup!")
            return None

        # Create tarball
        print(f"\nCreating archive: {backup_path.name}")
        try:
            with tarfile.open(backup_path, 'w:gz') as tar:
                for file_path, arc_name in files_to_backup:
                    try:
                        tar.add(file_path, arcname=arc_name)
                    except Exception as e:
                        print(f"  Warning: Cannot add {file_path}: {e}")

            # Add manifest
            manifest_path = self.backup_dir / f"manifest_{backup_id}.json"
            manifest_data = {
                'id': backup_id,
                'timestamp': timestamp.isoformat(),
                'components': components,
                'files': manifest
            }
            manifest_path.write_text(json.dumps(manifest_data, indent=2))

            with tarfile.open(backup_path, 'a') as tar:
                tar.add(manifest_path, arcname='manifest.json')
            manifest_path.unlink()

        except Exception as e:
            print(f"Failed to create archive: {e}")
            return None

        # Get backup info
        backup_size = backup_path.stat().st_size
        checksum = self._get_file_hash(backup_path)

        print(f"  Size: {backup_size / 1024 / 1024:.2f} MB")
        print(f"  Checksum: {checksum[:16]}...")

        # Sync to remote
        if not self.local_only:
            print(f"\nSyncing to {BACKUP_REMOTE_HOST}...")
            try:
                # Ensure remote dir exists
                subprocess.run(
                    ['ssh', BACKUP_REMOTE_HOST, f'mkdir -p {BACKUP_REMOTE_DIR}'],
                    timeout=30
                )
                # Copy backup
                result = subprocess.run(
                    ['scp', str(backup_path), f'{BACKUP_REMOTE_HOST}:{BACKUP_REMOTE_DIR}/'],
                    capture_output=True, timeout=300
                )
                if result.returncode == 0:
                    print(f"  ✓ Synced to raspi")
                else:
                    print(f"  ✗ Sync failed: {result.stderr.decode()[:100]}")
            except Exception as e:
                print(f"  ✗ Sync failed: {e}")

        backup_info = BackupInfo(
            id=backup_id,
            timestamp=timestamp,
            size_bytes=backup_size,
            components=components,
            location='local' if self.local_only else 'local+remote',
            checksum=checksum,
            manifest=manifest
        )

        print(f"\n✓ Backup complete: {backup_id}")
        return backup_info

    def list_backups(self, include_remote: bool = True) -> List[BackupInfo]:
        """List available backups."""
        backups = []

        # Local backups
        for tar_file in sorted(self.backup_dir.glob('backup_*.tar.gz'), reverse=True):
            try:
                name = tar_file.stem.replace('backup_', '').replace('.tar', '')
                ts = datetime.strptime(name, '%Y-%m-%d_%H%M%S')

                backups.append(BackupInfo(
                    id=name,
                    timestamp=ts,
                    size_bytes=tar_file.stat().st_size,
                    components=[],
                    location='local',
                    checksum=self._get_file_hash(tar_file)
                ))
            except Exception:
                pass

        # Remote backups
        if include_remote and not self.local_only:
            try:
                result = subprocess.run(
                    ['ssh', BACKUP_REMOTE_HOST, f'ls -la {BACKUP_REMOTE_DIR}/backup_*.tar.gz 2>/dev/null'],
                    capture_output=True, text=True, timeout=30
                )
                for line in result.stdout.strip().split('\n'):
                    if 'backup_' in line:
                        parts = line.split()
                        if len(parts) >= 9:
                            filename = parts[-1]
                            name = Path(filename).stem.replace('backup_', '').replace('.tar', '')
                            try:
                                ts = datetime.strptime(name, '%Y-%m-%d_%H%M%S')
                                # Check if we already have this locally
                                if not any(b.id == name for b in backups):
                                    backups.append(BackupInfo(
                                        id=name,
                                        timestamp=ts,
                                        size_bytes=int(parts[4]),
                                        components=[],
                                        location='remote',
                                        checksum=''
                                    ))
                            except Exception:
                                pass
            except Exception:
                pass

        return sorted(backups, key=lambda b: b.timestamp, reverse=True)

    def restore_backup(self, backup_id: str, components: List[str] = None,
                       target_dir: Path = None, dry_run: bool = False) -> bool:
        """Restore from a backup."""
        print(f"\n{'='*60}")
        print(f"RESTORING BACKUP: {backup_id}")
        print(f"{'='*60}")

        # Find backup
        backup_path = self.backup_dir / f"backup_{backup_id}.tar.gz"

        if not backup_path.exists():
            # Try fetching from remote
            print(f"Backup not found locally, checking remote...")
            try:
                subprocess.run(
                    ['scp', f'{BACKUP_REMOTE_HOST}:{BACKUP_REMOTE_DIR}/backup_{backup_id}.tar.gz',
                     str(backup_path)],
                    timeout=300, check=True
                )
                print(f"  Downloaded from raspi")
            except Exception as e:
                print(f"Backup not found: {backup_id}")
                return False

        if dry_run:
            print("\n[DRY RUN - No changes will be made]\n")

        # Read manifest
        manifest = {}
        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                try:
                    manifest_file = tar.extractfile('manifest.json')
                    if manifest_file:
                        manifest = json.loads(manifest_file.read().decode())
                except Exception:
                    pass

                print(f"Backup contains {len(tar.getnames())} files")

                if components:
                    print(f"Restoring only: {', '.join(components)}")

                if target_dir:
                    print(f"Target directory: {target_dir}")
                    target_dir.mkdir(parents=True, exist_ok=True)

                for member in tar.getmembers():
                    if member.name == 'manifest.json':
                        continue

                    # Check component filter
                    comp = member.name.split('/')[0]
                    if components and comp not in components:
                        continue

                    # Determine restore path
                    if target_dir:
                        restore_path = target_dir / member.name
                    else:
                        # Restore to original location
                        comp_config = BACKUP_SOURCES.get(comp, {})
                        base_path = comp_config.get('path', '/tmp/restore')
                        rel_path = '/'.join(member.name.split('/')[1:])
                        restore_path = Path(base_path) / rel_path

                    if dry_run:
                        print(f"  Would restore: {restore_path}")
                    else:
                        # Extract file
                        try:
                            restore_path.parent.mkdir(parents=True, exist_ok=True)
                            if member.isfile():
                                with tar.extractfile(member) as src:
                                    restore_path.write_bytes(src.read())
                                print(f"  ✓ {restore_path}")
                        except Exception as e:
                            print(f"  ✗ {restore_path}: {e}")

        except Exception as e:
            print(f"Restore failed: {e}")
            return False

        if not dry_run:
            print(f"\n✓ Restore complete")

        return True

    def verify_backup(self, backup_id: str) -> Dict[str, Any]:
        """Verify backup integrity."""
        result = {
            'id': backup_id,
            'valid': False,
            'errors': [],
            'file_count': 0
        }

        backup_path = self.backup_dir / f"backup_{backup_id}.tar.gz"
        if not backup_path.exists():
            result['errors'].append("Backup file not found")
            return result

        try:
            with tarfile.open(backup_path, 'r:gz') as tar:
                members = tar.getmembers()
                result['file_count'] = len(members)

                # Check each file can be read
                for member in members:
                    if member.isfile():
                        try:
                            tar.extractfile(member).read()
                        except Exception as e:
                            result['errors'].append(f"Cannot read {member.name}: {e}")

                result['valid'] = len(result['errors']) == 0

        except Exception as e:
            result['errors'].append(f"Cannot open archive: {e}")

        return result

    def cleanup_old_backups(self, keep_count: int = 10, keep_days: int = 30) -> int:
        """Remove old backups, keeping recent ones."""
        backups = self.list_backups(include_remote=False)
        cutoff_date = datetime.now() - timedelta(days=keep_days)

        removed = 0
        for i, backup in enumerate(backups):
            # Keep first N backups or backups newer than cutoff
            if i < keep_count or backup.timestamp > cutoff_date:
                continue

            backup_path = self.backup_dir / f"backup_{backup.id}.tar.gz"
            try:
                backup_path.unlink()
                removed += 1
                print(f"  Removed: {backup.id}")
            except Exception:
                pass

        return removed


from datetime import timedelta


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Backup & Restore System')
    parser.add_argument('--backup', action='store_true', help='Create backup')
    parser.add_argument('--restore', help='Restore from backup ID')
    parser.add_argument('--list', action='store_true', help='List backups')
    parser.add_argument('--verify', help='Verify backup ID')
    parser.add_argument('--cleanup', action='store_true', help='Cleanup old backups')
    parser.add_argument('--local', action='store_true', help='Local only (no remote)')
    parser.add_argument('--include', help='Components to include (comma-separated)')
    parser.add_argument('--target', help='Target directory for restore')
    parser.add_argument('--dry-run', action='store_true', help='Dry run (no changes)')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    br = BackupRestore(local_only=args.local)

    if args.backup:
        components = args.include.split(',') if args.include else None
        backup_info = br.create_backup(components=components)
        if args.json and backup_info:
            print(json.dumps({
                'id': backup_info.id,
                'timestamp': backup_info.timestamp.isoformat(),
                'size': backup_info.size_bytes,
                'components': backup_info.components,
                'location': backup_info.location
            }, indent=2))

    elif args.restore:
        components = args.include.split(',') if args.include else None
        target = Path(args.target) if args.target else None
        br.restore_backup(args.restore, components=components,
                          target_dir=target, dry_run=args.dry_run)

    elif args.list:
        backups = br.list_backups()
        if args.json:
            print(json.dumps([{
                'id': b.id,
                'timestamp': b.timestamp.isoformat(),
                'size_mb': b.size_bytes / 1024 / 1024,
                'location': b.location
            } for b in backups], indent=2))
        else:
            print(f"\n{'='*60}")
            print("AVAILABLE BACKUPS")
            print(f"{'='*60}\n")
            for b in backups:
                size_mb = b.size_bytes / 1024 / 1024
                age_days = (datetime.now() - b.timestamp).days
                print(f"  {b.id}  {size_mb:.1f}MB  {b.location}  ({age_days}d ago)")
            print()

    elif args.verify:
        result = br.verify_backup(args.verify)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result['valid']:
                print(f"✓ Backup {args.verify} is valid ({result['file_count']} files)")
            else:
                print(f"✗ Backup {args.verify} has errors:")
                for err in result['errors']:
                    print(f"  - {err}")

    elif args.cleanup:
        removed = br.cleanup_old_backups()
        print(f"Removed {removed} old backup(s)")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
