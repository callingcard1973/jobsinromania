#!/usr/bin/env python3
"""
claudemd_stub_remover.py - Identify and remove stub CLAUDE.md files

A stub CLAUDE.md is a placeholder file with minimal or no useful content:
- File size < 100 bytes
- Content is only a reference (e.g., @AGENTS.md)
- Content has no actual documentation
- File contains only a title and no other content

Usage:
    python3 claudemd_stub_remover.py /opt/ACTIVE/              # Scan only
    python3 claudemd_stub_remover.py /opt/ACTIVE/ --delete     # Delete stubs
    python3 claudemd_stub_remover.py /opt/ACTIVE/ --interactive # Ask per file
    python3 claudemd_stub_remover.py /opt/ACTIVE/ --show-content # Show content
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Tuple


def is_stub(filepath: Path) -> Tuple[bool, str]:
    """
    Determine if a CLAUDE.md file is a stub.

    Returns:
        (is_stub: bool, reason: str)
    """
    try:
        content = filepath.read_text(encoding='utf-8', errors='ignore')
        size = filepath.stat().st_size
    except Exception as e:
        return False, f"Error reading: {e}"

    # Check 1: Reference-only file (starts with @ and very short)
    if content.strip().startswith('@') and len(content.strip()) < 80:
        return True, "Reference-only file"

    # Check 2: Only title, no content
    lines = [l.strip() for l in content.split('\n') if l.strip()]
    non_header_lines = [l for l in lines if not l.startswith('#')]

    if len(non_header_lines) == 0:
        return True, "No content beyond title"

    # Check 3: Very small file with no real documentation
    if size < 50:
        # Check if it's just a reference or placeholder
        if len(non_header_lines) < 2:
            return True, f"Too small ({size} bytes) with minimal content"

    # Check 4: Multiple headers but essentially empty
    if len(non_header_lines) < 2 and any(l.startswith('#') for l in lines):
        return True, "Minimal content (only headers)"

    return False, None


def find_stubs(root_path: Path) -> List[Tuple[Path, str]]:
    """Find all stub CLAUDE.md files in a directory tree."""
    stubs = []

    for claudemd in root_path.rglob('CLAUDE.md'):
        is_stub_file, reason = is_stub(claudemd)
        if is_stub_file:
            stubs.append((claudemd, reason))

    return stubs


def create_backup_dir() -> Path:
    """Create a timestamped backup directory."""
    backup_base = Path('/opt/ACTIVE/.claudemd_backups')
    backup_base.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_dir = backup_base / f'stubs_{timestamp}'
    backup_dir.mkdir(parents=True, exist_ok=True)

    return backup_dir


def backup_file(filepath: Path, backup_dir: Path) -> Path:
    """Backup a file, preserving directory structure."""
    # Create relative path structure in backup
    rel_path = filepath.relative_to('/')
    backup_path = backup_dir / rel_path
    backup_path.parent.mkdir(parents=True, exist_ok=True)

    shutil.copy2(filepath, backup_path)
    return backup_path


def print_stub_report(stubs: List[Tuple[Path, str]]) -> None:
    """Print a formatted report of stub files."""
    if not stubs:
        print("No stub files found.")
        return

    print("\nSTUB FILES DETECTED")
    print("=" * 70)

    for filepath, reason in sorted(stubs, key=lambda x: str(x[0])):
        size = filepath.stat().st_size
        print(f"\n{filepath}")
        print(f"  Size: {size} bytes")
        print(f"  Reason: {reason}")

    print(f"\n{'=' * 70}")
    print(f"Total: {len(stubs)} stub file(s) found\n")


def print_stub_content(stubs: List[Tuple[Path, str]]) -> None:
    """Print content of stub files."""
    if not stubs:
        print("No stub files found.")
        return

    print("\nSTUB FILES CONTENT")
    print("=" * 70)

    for filepath, reason in sorted(stubs, key=lambda x: str(x[0])):
        print(f"\n{filepath}")
        print(f"  Reason: {reason}")
        print(f"  Content:")
        print("  " + "-" * 66)

        try:
            content = filepath.read_text(encoding='utf-8', errors='ignore')
            for line in content.split('\n')[:20]:  # Max 20 lines
                print(f"  {line}")
            if content.count('\n') > 20:
                print(f"  ... ({content.count(chr(10)) - 20} more lines)")
        except Exception as e:
            print(f"  Error reading: {e}")

        print("  " + "-" * 66)

    print(f"\n{'=' * 70}\n")


def delete_stubs(stubs: List[Tuple[Path, str]], interactive: bool = False,
                 backup: bool = True) -> Tuple[int, int]:
    """
    Delete stub files.

    Returns:
        (deleted_count, skipped_count)
    """
    if not stubs:
        print("No stub files to delete.")
        return 0, 0

    deleted = 0
    skipped = 0
    backup_dir = None

    if backup:
        backup_dir = create_backup_dir()
        print(f"Backup directory: {backup_dir}\n")

    for filepath, reason in sorted(stubs, key=lambda x: str(x[0])):
        if interactive:
            print(f"\nDelete {filepath}?")
            print(f"  Reason: {reason}")
            response = input("  (y/n/skip): ").strip().lower()
            if response not in ['y', 'yes']:
                skipped += 1
                continue

        try:
            if backup_dir:
                backup_file(filepath, backup_dir)
                print(f"  Backed up to: {backup_dir}")

            filepath.unlink()
            print(f"  Deleted: {filepath}")
            deleted += 1
        except Exception as e:
            print(f"  ERROR deleting {filepath}: {e}")
            skipped += 1

    return deleted, skipped


def main():
    parser = argparse.ArgumentParser(
        description='Identify and remove stub CLAUDE.md files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /opt/ACTIVE/              # Scan only (default)
  %(prog)s /opt/ACTIVE/ --delete     # Delete stubs with backup
  %(prog)s /opt/ACTIVE/ --interactive # Ask for each file
  %(prog)s /opt/ACTIVE/ --show-content # Show stub content
        """
    )

    parser.add_argument(
        'root_path',
        type=Path,
        help='Root directory to scan for CLAUDE.md files'
    )

    parser.add_argument(
        '--delete',
        action='store_true',
        help='Delete stub files (creates backup by default)'
    )

    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Ask for each file before deletion (implies --delete)'
    )

    parser.add_argument(
        '--show-content',
        action='store_true',
        help='Show content of stub files'
    )

    parser.add_argument(
        '--backup',
        action='store_true',
        default=True,
        help='Create backup when deleting (default: True)'
    )

    parser.add_argument(
        '--no-backup',
        action='store_false',
        dest='backup',
        help='Delete without backup (dangerous)'
    )

    args = parser.parse_args()

    # Validate root path
    if not args.root_path.exists():
        print(f"ERROR: Path does not exist: {args.root_path}", file=sys.stderr)
        sys.exit(1)

    if not args.root_path.is_dir():
        print(f"ERROR: Path is not a directory: {args.root_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning for stub CLAUDE.md files in: {args.root_path}\n")

    # Find stubs
    stubs = find_stubs(args.root_path)

    # Show content if requested
    if args.show_content:
        print_stub_content(stubs)

    # Print report
    print_stub_report(stubs)

    # Handle deletion
    if args.interactive:
        args.delete = True

    if args.delete:
        if not not args.backup:
            print("WARNING: Deleting files. Backup will be created.\n")
        else:
            print("WARNING: Deleting files WITHOUT backup. This is dangerous!\n")

        if not args.interactive:
            response = input(f"Delete {len(stubs)} stub file(s)? (y/n): ").strip().lower()
            if response not in ['y', 'yes']:
                print("Cancelled.")
                sys.exit(0)

        deleted, skipped = delete_stubs(
            stubs,
            interactive=args.interactive,
            backup=args.backup
        )

        print(f"\n{'=' * 70}")
        print(f"Results: {deleted} deleted, {skipped} skipped")
        if args.backup and deleted > 0:
            print(f"Backup location: /opt/ACTIVE/.claudemd_backups/")
    else:
        if stubs:
            print("To delete these files, run with --delete flag")
            print("To see file contents, run with --show-content flag")


if __name__ == '__main__':
    main()
