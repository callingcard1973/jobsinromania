#!/usr/bin/python3
"""
CLAUDE.md Migrator - Updates CLAUDE.md files to standardized format.

Migrates existing CLAUDE.md files to the standardized format with metadata
blocks and consistent sections.

Usage:
    python3 claudemd_migrator.py /opt/ACTIVE/SCRAPERS/                    # Dry run
    python3 claudemd_migrator.py /opt/ACTIVE/SCRAPERS/ --apply            # Apply changes
    python3 claudemd_migrator.py /opt/ACTIVE/SCRAPERS/CLAUDE.md --diff    # Show diff
    python3 claudemd_migrator.py /opt/ACTIVE/ --category scraper --apply  # Filter by category
    python3 claudemd_migrator.py /opt/ACTIVE/ --interactive               # Ask before each change
"""

import argparse
import difflib
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Backup directory for all migrations
BACKUP_DIR = Path('/opt/ACTIVE/.claudemd_backups')

# Header normalization map - old names to standard names
HEADER_MAP = {
    'overview': 'Purpose',
    'project overview': 'Purpose',
    'description': 'Purpose',
    'about': 'Purpose',
    'introduction': 'Purpose',
    'what is this': 'Purpose',
    'quick commands': 'Quick Start',
    'commands': 'Quick Start',
    'usage': 'Quick Start',
    'how to run': 'Quick Start',
    'running': 'Quick Start',
    'getting started': 'Quick Start',
    'file structure': 'Files',
    'directory structure': 'Files',
    'structure': 'Files',
    'project structure': 'Files',
    'data paths': 'Output',
    'paths': 'Output',
    'output paths': 'Output',
    'data output': 'Output',
    'database tables': 'Tables',
    'tables': 'Tables',
    'schema': 'Tables',
    'data sources': 'Data Sources',
    'sources': 'Data Sources',
    'sending': 'Quick Start',
    'campaign ready': 'Output',
}

# Required sections in order
REQUIRED_SECTIONS = ['Purpose', 'Quick Start', 'Files']

# Optional but common sections
OPTIONAL_SECTIONS = ['Output', 'Tables', 'Data Sources', 'Notes', 'Related']

# Placeholder content for missing required sections
PLACEHOLDERS = {
    'Purpose': '{TODO: Describe what this component does and why it exists.}',
    'Quick Start': '```bash\n# TODO: Add common commands\n```',
    'Files': '| File | Purpose |\n|------|---------|\n| `TODO` | Description |',
    'Output': '{TODO: Describe output location and format.}',
    'Tables': '| Table | Rows | Description |\n|-------|------|-------------|\n| `TODO` | ~ | Description |',
}

# Category inference from path
CATEGORY_PATTERNS = {
    'scraper': ['/SCRAPERS/', '/SCRAPER_'],
    'campaign': ['/EMAIL/CAMPAIGNS/', '/CAMPAIGNS/'],
    'skill': ['/SKILLS/'],
    'project': ['/PROJECTS/'],
    'web': ['/WEB/', '/WEBSITES/'],
    'data': ['/DATA/', '/OPENDATA/'],
    'infra': ['/INFRA/'],
    'db': ['/DB/'],
}


@dataclass
class MigrationChange:
    """Represents a single change to be made."""
    change_type: str  # 'add_metadata', 'normalize_header', 'remove_empty', 'add_section'
    description: str
    line_before: Optional[str] = None
    line_after: Optional[str] = None


@dataclass
class MigrationResult:
    """Result of migrating a single file."""
    filepath: Path
    original_content: str
    new_content: str
    changes: List[MigrationChange] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def modified(self) -> bool:
        return self.original_content != self.new_content


def infer_category(filepath: Path) -> str:
    """Infer category from file path."""
    filepath_str = str(filepath)
    for category, patterns in CATEGORY_PATTERNS.items():
        for pattern in patterns:
            if pattern in filepath_str:
                return category
    return 'other'


def infer_status(filepath: Path) -> str:
    """Infer status from file path."""
    filepath_str = str(filepath)
    if '/INACTIVE/' in filepath_str or '/ARCHIVE/' in filepath_str:
        return 'archived'
    return 'active'


def infer_owner() -> str:
    """Default owner."""
    return 'tudor'


def get_file_updated(filepath: Path) -> str:
    """Get file modification date in YYYY-MM-DD format."""
    try:
        mtime = os.path.getmtime(filepath)
        return datetime.fromtimestamp(mtime).strftime('%Y-%m-%d')
    except (OSError, ValueError):
        return datetime.now().strftime('%Y-%m-%d')


def extract_title(content: str) -> Optional[str]:
    """Extract the H1 title from content."""
    lines = content.split('\n')
    for line in lines:
        line = line.strip()
        if line.startswith('# ') and not line.startswith('##'):
            return line[2:].strip()
    return None


def has_metadata_block(content: str) -> bool:
    """Check if content already has a metadata block."""
    # Look for YAML-like metadata block after title
    lines = content.split('\n')
    in_metadata = False
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Skip title
        if stripped.startswith('# ') and not stripped.startswith('##'):
            continue
        # Skip empty lines after title
        if not stripped:
            continue
        # Check for metadata indicators
        if stripped.startswith('category:') or stripped.startswith('status:'):
            return True
        if stripped.startswith('| category |') or stripped.startswith('|category|'):
            return True
        # If we hit a section header without finding metadata, no metadata exists
        if stripped.startswith('##'):
            return False
        # Only check first few meaningful lines
        break
    return False


def parse_sections(content: str) -> List[Tuple[str, str, int]]:
    """
    Parse content into sections.
    Returns list of (header_text, section_content, line_number).
    """
    lines = content.split('\n')
    sections = []
    current_header = None
    current_content = []
    current_line = 0

    for i, line in enumerate(lines):
        if line.strip().startswith('## '):
            # Save previous section
            if current_header is not None:
                sections.append((current_header, '\n'.join(current_content), current_line))
            # Start new section
            current_header = line.strip()[3:].strip()
            current_content = []
            current_line = i
        elif current_header is not None:
            current_content.append(line)

    # Don't forget the last section
    if current_header is not None:
        sections.append((current_header, '\n'.join(current_content), current_line))

    return sections


def normalize_header(header: str) -> str:
    """Normalize a header to standard form."""
    header_lower = header.lower().strip()
    return HEADER_MAP.get(header_lower, header)


def is_section_empty(content: str) -> bool:
    """Check if section content is effectively empty."""
    stripped = content.strip()
    if not stripped:
        return True
    # Check for tables with only header row
    lines = [l for l in stripped.split('\n') if l.strip()]
    if len(lines) <= 2:
        # Could be just a table header + separator
        if all('|' in l for l in lines):
            return True
    return False


def create_metadata_block(filepath: Path, content: str) -> str:
    """Create a metadata block for the file."""
    category = infer_category(filepath)
    status = infer_status(filepath)
    owner = infer_owner()
    updated = get_file_updated(filepath)

    metadata = f"""
| category | status | owner | updated |
|----------|--------|-------|---------|
| {category} | {status} | {owner} | {updated} |
"""
    return metadata.strip()


def migrate_file(filepath: Path) -> MigrationResult:
    """
    Migrate a single CLAUDE.md file to standard format.
    Returns MigrationResult with original and new content.
    """
    result = MigrationResult(
        filepath=filepath,
        original_content="",
        new_content="",
        changes=[]
    )

    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception as e:
        result.skipped = True
        result.skip_reason = f"Could not read file: {e}"
        return result

    result.original_content = content
    lines = content.split('\n')

    # Find title line
    title_line_idx = None
    title = None
    for i, line in enumerate(lines):
        if line.strip().startswith('# ') and not line.strip().startswith('##'):
            title_line_idx = i
            title = line.strip()[2:].strip()
            break

    if title_line_idx is None:
        result.skipped = True
        result.skip_reason = "No H1 title found"
        result.new_content = content
        return result

    # Check for existing metadata
    has_meta = has_metadata_block(content)

    # Build new content
    new_lines = []

    # Add title
    new_lines.append(lines[title_line_idx])
    new_lines.append('')

    # Add metadata if missing
    if not has_meta:
        metadata = create_metadata_block(filepath, content)
        new_lines.append(metadata)
        new_lines.append('')
        result.changes.append(MigrationChange(
            change_type='add_metadata',
            description=f"Added metadata block (category={infer_category(filepath)}, status={infer_status(filepath)})"
        ))

    # Find where content after title starts (skip title and any existing metadata)
    content_start_idx = title_line_idx + 1

    # Skip blank lines after title
    while content_start_idx < len(lines) and not lines[content_start_idx].strip():
        content_start_idx += 1

    # If there's existing metadata (table-style), skip it
    if has_meta and content_start_idx < len(lines):
        # Skip metadata table
        if lines[content_start_idx].strip().startswith('|'):
            while content_start_idx < len(lines) and lines[content_start_idx].strip().startswith('|'):
                new_lines.append(lines[content_start_idx])
                content_start_idx += 1
            new_lines.append('')
        # Skip YAML-style metadata
        elif ':' in lines[content_start_idx]:
            while content_start_idx < len(lines) and ':' in lines[content_start_idx] and not lines[content_start_idx].strip().startswith('#'):
                new_lines.append(lines[content_start_idx])
                content_start_idx += 1

    # Skip blank lines
    while content_start_idx < len(lines) and not lines[content_start_idx].strip():
        content_start_idx += 1

    # Check for intro paragraph (non-section text before first ##)
    intro_lines = []
    while content_start_idx < len(lines) and not lines[content_start_idx].strip().startswith('##'):
        intro_lines.append(lines[content_start_idx])
        content_start_idx += 1

    # Add intro as Purpose section if not empty and no Purpose section exists
    intro_text = '\n'.join(intro_lines).strip()
    sections = parse_sections(content)
    has_purpose = any(normalize_header(h) == 'Purpose' for h, _, _ in sections)

    # Track which normalized sections we've already added (to avoid duplicates)
    added_sections = set()

    if intro_text and not has_purpose:
        new_lines.append('## Purpose')
        new_lines.append('')
        new_lines.append(intro_text)
        new_lines.append('')
        added_sections.add('Purpose')
        result.changes.append(MigrationChange(
            change_type='add_section',
            description="Converted intro paragraph to Purpose section"
        ))
    elif intro_text:
        # Keep intro as-is if Purpose section exists
        new_lines.extend(intro_lines)

    # Process sections - merge sections that normalize to the same name
    section_contents = {}  # normalized_name -> list of (original_header, content)
    for header, section_content, _ in sections:
        normalized = normalize_header(header)
        if normalized not in section_contents:
            section_contents[normalized] = []
        section_contents[normalized].append((header, section_content))

    # Now output merged sections
    for normalized, contents_list in section_contents.items():
        # Skip if we already added this section (e.g., from intro)
        if normalized in added_sections:
            # But still merge content if there's more
            if contents_list:
                # Append to the Purpose section we already created
                for orig_header, section_content in contents_list:
                    if not is_section_empty(section_content):
                        # Find where we added Purpose and append
                        # For simplicity, just log this as a note
                        result.changes.append(MigrationChange(
                            change_type='normalize_header',
                            description=f"Merged '{orig_header}' content into existing {normalized} section"
                        ))
            continue

        added_sections.add(normalized)

        # Check if any original header differs from normalized
        for orig_header, _ in contents_list:
            if orig_header != normalized:
                result.changes.append(MigrationChange(
                    change_type='normalize_header',
                    description=f"Renamed '{orig_header}' to '{normalized}'",
                    line_before=f"## {orig_header}",
                    line_after=f"## {normalized}"
                ))

        # Merge all contents for this normalized section
        merged_content_parts = []
        for orig_header, section_content in contents_list:
            if not is_section_empty(section_content):
                merged_content_parts.append(section_content.strip())

        merged_content = '\n\n'.join(merged_content_parts)

        # Check if section is empty
        if not merged_content.strip():
            result.changes.append(MigrationChange(
                change_type='remove_empty',
                description=f"Flagged empty section: {normalized}"
            ))
            # Still include it but add TODO placeholder
            new_lines.append(f'## {normalized}')
            new_lines.append('')
            new_lines.append(PLACEHOLDERS.get(normalized, '{TODO: Add content}'))
            new_lines.append('')
        else:
            new_lines.append(f'## {normalized}')
            new_lines.append('')
            # Preserve content with proper spacing
            new_lines.append(merged_content)
            # Ensure blank line before next section
            if new_lines[-1].strip():
                new_lines.append('')

    # Add missing required sections
    for required in REQUIRED_SECTIONS:
        if required not in added_sections:
            result.changes.append(MigrationChange(
                change_type='add_section',
                description=f"Added missing required section: {required}"
            ))
            new_lines.append(f'## {required}')
            new_lines.append('')
            new_lines.append(PLACEHOLDERS.get(required, '{TODO: Add content}'))
            new_lines.append('')

    # Clean up multiple blank lines
    cleaned_lines = []
    prev_blank = False
    for line in new_lines:
        is_blank = not line.strip()
        if is_blank and prev_blank:
            continue
        cleaned_lines.append(line)
        prev_blank = is_blank

    # Remove trailing blank lines but keep one
    while len(cleaned_lines) > 1 and not cleaned_lines[-1].strip() and not cleaned_lines[-2].strip():
        cleaned_lines.pop()

    # Ensure file ends with newline
    if cleaned_lines and cleaned_lines[-1].strip():
        cleaned_lines.append('')

    result.new_content = '\n'.join(cleaned_lines)

    # Check if already compliant (no changes made)
    if not result.changes:
        result.skipped = True
        result.skip_reason = "Already compliant"

    return result


def backup_file(filepath: Path, timestamp: str) -> Path:
    """Create a backup of the file before modification."""
    backup_subdir = BACKUP_DIR / timestamp

    # Try to make path relative to /opt/ACTIVE
    try:
        relative = filepath.relative_to('/opt/ACTIVE')
    except ValueError:
        relative = filepath.name

    backup_path = backup_subdir / relative
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(filepath, backup_path)
    return backup_path


def show_diff(original: str, new: str, filepath: Path) -> str:
    """Generate a unified diff between original and new content."""
    original_lines = original.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)

    diff = difflib.unified_diff(
        original_lines,
        new_lines,
        fromfile=f'{filepath} (original)',
        tofile=f'{filepath} (migrated)',
        lineterm=''
    )
    return ''.join(diff)


def find_claude_md_files(path: Path, category_filter: Optional[str] = None) -> List[Path]:
    """Find all CLAUDE.md files under a path."""
    files = []

    if path.is_file():
        if path.name == 'CLAUDE.md':
            files.append(path)
    else:
        for root, dirs, filenames in os.walk(path):
            # Skip backup directories
            if '.claudemd_backups' in root:
                continue
            for filename in filenames:
                if filename == 'CLAUDE.md':
                    filepath = Path(root) / filename
                    if category_filter:
                        if infer_category(filepath) == category_filter:
                            files.append(filepath)
                    else:
                        files.append(filepath)

    return sorted(files)


def print_report(results: List[MigrationResult], applied: bool, backup_timestamp: Optional[str] = None):
    """Print migration report."""
    print("\n" + "=" * 60)
    print("MIGRATION REPORT")
    print("=" * 60)

    modified = [r for r in results if r.modified and not r.skipped]
    skipped_compliant = [r for r in results if r.skipped and r.skip_reason == "Already compliant"]
    skipped_other = [r for r in results if r.skipped and r.skip_reason != "Already compliant"]

    print(f"\nFiles processed: {len(results)}")
    print(f"Files {'modified' if applied else 'to modify'}: {len(modified)}")
    print(f"Files skipped (already compliant): {len(skipped_compliant)}")
    if skipped_other:
        print(f"Files skipped (other reasons): {len(skipped_other)}")
    if applied and backup_timestamp:
        print(f"Backups created: {len(modified)}")

    # Changes summary
    change_counts = {}
    for result in modified:
        for change in result.changes:
            change_counts[change.change_type] = change_counts.get(change.change_type, 0) + 1

    if change_counts:
        print("\nChanges made:" if applied else "\nChanges to make:")
        for change_type, count in sorted(change_counts.items()):
            label = {
                'add_metadata': 'Added metadata block',
                'normalize_header': 'Normalized headers',
                'remove_empty': 'Flagged empty sections',
                'add_section': 'Added placeholder sections',
            }.get(change_type, change_type)
            print(f"  - {label}: {count} files")

    if applied and backup_timestamp:
        print(f"\nBackup location: {BACKUP_DIR / backup_timestamp}/")

    # List files with issues
    if skipped_other:
        print("\nSkipped files (issues):")
        for result in skipped_other:
            print(f"  - {result.filepath}: {result.skip_reason}")


def main():
    parser = argparse.ArgumentParser(
        description='Migrate CLAUDE.md files to standardized format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s /opt/ACTIVE/SCRAPERS/                    # Dry run on directory
  %(prog)s /opt/ACTIVE/SCRAPERS/ --apply            # Apply changes
  %(prog)s /opt/ACTIVE/SCRAPERS/CLAUDE.md --diff    # Show diff for single file
  %(prog)s /opt/ACTIVE/ --category scraper --apply  # Filter by category
  %(prog)s /opt/ACTIVE/ --interactive               # Ask before each change
        """
    )

    parser.add_argument('path', type=Path,
                        help='Path to CLAUDE.md file or directory')
    parser.add_argument('--apply', action='store_true',
                        help='Apply changes (default is dry run)')
    parser.add_argument('--diff', action='store_true',
                        help='Show unified diff for each file')
    parser.add_argument('--category', type=str,
                        choices=['scraper', 'campaign', 'skill', 'project', 'web', 'data', 'infra', 'db', 'other'],
                        help='Only process files matching this category')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Ask before modifying each file')
    parser.add_argument('--no-backup', action='store_true',
                        help='Skip creating backups (not recommended)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Show detailed output for each file')

    args = parser.parse_args()

    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Find files
    files = find_claude_md_files(args.path, args.category)

    if not files:
        print("No CLAUDE.md files found matching criteria.")
        sys.exit(0)

    print(f"Found {len(files)} CLAUDE.md file(s)")

    # Process files
    results = []
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    for filepath in files:
        if args.verbose:
            print(f"\nProcessing: {filepath}")

        result = migrate_file(filepath)
        results.append(result)

        if result.skipped:
            if args.verbose:
                print(f"  Skipped: {result.skip_reason}")
            continue

        if not result.modified:
            if args.verbose:
                print("  No changes needed")
            continue

        # Show changes
        if args.verbose or args.diff:
            print(f"\n--- {filepath} ---")
            for change in result.changes:
                print(f"  * {change.description}")

        if args.diff:
            diff = show_diff(result.original_content, result.new_content, filepath)
            if diff:
                print(diff)

        # Interactive mode
        if args.interactive and args.apply:
            response = input(f"\nApply changes to {filepath}? [y/N] ").strip().lower()
            if response != 'y':
                print("  Skipped by user")
                result.skipped = True
                result.skip_reason = "Skipped by user"
                continue

        # Apply changes
        if args.apply and result.modified:
            if not args.no_backup:
                backup_path = backup_file(filepath, timestamp)
                if args.verbose:
                    print(f"  Backed up to: {backup_path}")

            filepath.write_text(result.new_content, encoding='utf-8')
            if args.verbose:
                print(f"  Applied changes")

    # Print report
    print_report(results, args.apply, timestamp if args.apply and not args.no_backup else None)

    if not args.apply:
        modified_count = sum(1 for r in results if r.modified and not r.skipped)
        if modified_count > 0:
            print(f"\nRun with --apply to make these changes.")


if __name__ == '__main__':
    main()
