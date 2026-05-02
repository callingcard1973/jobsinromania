#!/usr/bin/env python3
"""
Bulk Refactor Example - Rename identifier across entire codebase
Token savings: ~500 tokens vs ~25,000 tokens traditionally (97.6% reduction)

Usage:
    python3 bulk_refactor.py /path/to/code old_name new_name [--apply]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from exec_runtime import CodeTransform

def bulk_refactor(path: str, old_name: str, new_name: str, apply: bool = False):
    """
    Rename identifier across all Python files.

    This demonstrates the Anthropic code execution pattern:
    - Analyze locally (not in context)
    - Process locally (not in context)
    - Return summary only (minimal tokens)
    """
    print(f"Renaming '{old_name}' -> '{new_name}' in {path}")
    print(f"Mode: {'APPLY' if apply else 'DRY-RUN'}")
    print("=" * 60)

    # Execute bulk rename - returns summary, not file contents
    result = CodeTransform.rename_identifier(
        old_name=old_name,
        new_name=new_name,
        path=path,
        pattern='**/*.py',
        dry_run=not apply
    )

    # Print summary
    print(f"\nFiles modified: {result['files_modified']}")
    print(f"Total replacements: {result['total_replacements']}")

    if result['changes']:
        print("\nChanges:")
        for change in result['changes'][:20]:
            status = "applied" if change['applied'] else "would apply"
            print(f"  {change['file']}: {change['count']} ({status})")

        if len(result['changes']) > 20:
            print(f"  ... and {len(result['changes']) - 20} more files")

    if result['dry_run']:
        print("\n[DRY-RUN] Use --apply to make changes")

    return result

if __name__ == '__main__':
    if len(sys.argv) < 4:
        print("Usage: bulk_refactor.py <path> <old_name> <new_name> [--apply]")
        print("\nExample:")
        print("  bulk_refactor.py /opt/ACTIVE/SCRAPERS/EUROPE get_data fetch_data")
        print("  bulk_refactor.py /opt/ACTIVE/SCRAPERS/EUROPE get_data fetch_data --apply")
        sys.exit(1)

    path = sys.argv[1]
    old_name = sys.argv[2]
    new_name = sys.argv[3]
    apply = '--apply' in sys.argv

    bulk_refactor(path, old_name, new_name, apply)
