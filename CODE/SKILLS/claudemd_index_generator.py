#!/usr/bin/python3
"""
CLAUDE.md Index Generator

Generates a master index document listing all CLAUDE.md files, organized by
category, with summaries and compliance scores.

Usage:
    python3 claudemd_index_generator.py
    python3 claudemd_index_generator.py --output /path/to/INDEX.md
    python3 claudemd_index_generator.py --path /opt/ACTIVE/SCRAPERS/
    python3 claudemd_index_generator.py --include-inactive
    python3 claudemd_index_generator.py --format json --output index.json

Author: Tudor
Created: 2026-03-29
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


# =============================================================================
# Configuration
# =============================================================================

DEFAULT_SCAN_PATH = Path('/opt/ACTIVE')
DEFAULT_OUTPUT_PATH = Path('/opt/ACTIVE/CLAUDE_INDEX.md')
INACTIVE_PATH = Path('/opt/INACTIVE')

# Category detection patterns (order matters - first match wins)
CATEGORY_PATTERNS = [
    ('scraper', [
        r'/SCRAPERS?/',
        r'/SCRAPER_',
        r'scraper',
        r'_scraper\.md$',
    ]),
    ('campaign', [
        r'/EMAIL/',
        r'/CAMPAIGNS?/',
        r'campaign',
        r'/COMMS/',
    ]),
    ('infrastructure', [
        r'/INFRA/',
        r'/GOVERNOR/',
        r'/SKILLS/',
        r'/DB/',
        r'/BACKUPS?/',
    ]),
    ('database', [
        r'/DATABASE/',
        r'/POSTGRES/',
        r'/SQL/',
        r'_db/',
    ]),
    ('web', [
        r'/WEB/',
        r'/WEBSITES?/',
        r'/HTML/',
        r'/WORDPRESS/',
    ]),
    ('project', [
        # Catch-all for everything else
        r'.*',
    ]),
]

# Required sections for compliance scoring
REQUIRED_SECTIONS = [
    'purpose',
    'overview',
    'structure',
    'files',
    'usage',
    'quick start',
    'commands',
]


# =============================================================================
# Compliance Scoring (based on auditor logic)
# =============================================================================

def calculate_compliance_score(content: str, filepath: Path) -> tuple[int, list[str]]:
    """
    Calculate compliance score for a CLAUDE.md file.
    Returns (score 0-100, list of issues).
    """
    score = 0
    issues = []

    # Empty or stub check
    if len(content.strip()) < 50:
        return 5, ['Stub file (< 50 bytes of content)']

    lines = content.split('\n')

    # Check for H1 header (# Title)
    has_h1 = any(line.strip().startswith('# ') for line in lines[:5])
    if has_h1:
        score += 20
    else:
        issues.append('Missing H1 header')

    # Check for description/overview in first 10 lines
    first_content = '\n'.join(lines[:10]).lower()
    has_description = len(first_content) > 100 and not all(
        line.strip().startswith('#') or line.strip() == ''
        for line in lines[:10] if line.strip()
    )
    if has_description:
        score += 15
    else:
        issues.append('Missing description/overview')

    content_lower = content.lower()

    # Check for at least one required section
    found_sections = []
    for section in REQUIRED_SECTIONS:
        if f'## {section}' in content_lower or f'### {section}' in content_lower:
            found_sections.append(section)

    if found_sections:
        section_score = min(30, len(found_sections) * 10)
        score += section_score
    else:
        issues.append('Missing standard sections')

    # Check for tables (structured content)
    has_tables = '|' in content and '---' in content
    if has_tables:
        score += 10

    # Check for code blocks
    has_code = '```' in content
    if has_code:
        score += 10

    # Check for links (internal references)
    has_links = '[' in content and '](' in content
    if has_links:
        score += 5

    # Check for reasonable length (200-5000 chars is good)
    content_len = len(content.strip())
    if 200 <= content_len <= 5000:
        score += 10
    elif content_len < 200:
        issues.append('Too short (< 200 chars)')

    # Cap at 100
    score = min(100, score)

    return score, issues


def extract_purpose(content: str) -> str:
    """
    Extract purpose/summary from CLAUDE.md content.
    Returns first sentence of Purpose section, or first non-header line.
    """
    lines = content.split('\n')

    # First, try to find Purpose or Overview section
    in_purpose = False
    for i, line in enumerate(lines):
        line_lower = line.lower().strip()

        # Check for purpose/overview header
        if line_lower.startswith('## purpose') or line_lower.startswith('## overview'):
            in_purpose = True
            continue

        # If we're in purpose section, get first non-empty line
        if in_purpose:
            if line.strip() and not line.strip().startswith('#'):
                # Get first sentence (up to 80 chars)
                text = line.strip()
                # Find first sentence end
                for end in ['. ', '.\n', '!', '?']:
                    if end in text:
                        text = text[:text.index(end) + 1]
                        break
                return text[:80] + ('...' if len(text) > 80 else '')

    # Fallback: get first non-header, non-empty line
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#') and not stripped.startswith('|'):
            # Get first sentence
            text = stripped
            for end in ['. ', '.\n', '!', '?']:
                if end in text:
                    text = text[:text.index(end) + 1]
                    break
            return text[:80] + ('...' if len(text) > 80 else '')

    return '(no description)'


def detect_category(filepath: Path) -> str:
    """
    Detect category based on file path.
    """
    path_str = str(filepath)

    for category, patterns in CATEGORY_PATTERNS:
        for pattern in patterns:
            if re.search(pattern, path_str, re.IGNORECASE):
                return category

    return 'project'


def get_file_modified_time(filepath: Path) -> datetime:
    """
    Get file modification time.
    """
    try:
        mtime = filepath.stat().st_mtime
        return datetime.fromtimestamp(mtime)
    except Exception:
        return datetime.min


# =============================================================================
# Index Generation
# =============================================================================

def scan_claudemd_files(scan_path: Path, include_inactive: bool = False) -> list[dict]:
    """
    Scan for all CLAUDE.md files and collect metadata.
    """
    files = []

    # Find all CLAUDE.md files
    for filepath in scan_path.rglob('CLAUDE.md'):
        # Skip inactive unless requested
        if not include_inactive and INACTIVE_PATH in filepath.parents:
            continue

        try:
            content = filepath.read_text(encoding='utf-8', errors='replace')
            score, issues = calculate_compliance_score(content, filepath)

            file_info = {
                'path': filepath,
                'relative_path': filepath.relative_to(scan_path),
                'content': content,
                'size': filepath.stat().st_size,
                'modified': get_file_modified_time(filepath),
                'category': detect_category(filepath),
                'score': score,
                'issues': issues,
                'purpose': extract_purpose(content),
            }
            files.append(file_info)

        except Exception as e:
            print(f"Error reading {filepath}: {e}", file=sys.stderr)
            continue

    return files


def make_relative_link(filepath: Path, base_path: Path) -> str:
    """
    Create a markdown link with relative path.
    """
    try:
        rel = filepath.relative_to(base_path)
        # Use parent folder name as display
        display_name = str(rel.parent)
        if display_name == '.':
            display_name = 'ROOT'
        return f"[{display_name}]({rel})"
    except ValueError:
        return f"[{filepath.name}]({filepath})"


def generate_markdown_index(files: list[dict], base_path: Path) -> str:
    """
    Generate the markdown index document.
    """
    now = datetime.now()

    # Calculate statistics
    total_files = len(files)
    if total_files == 0:
        return "# CLAUDE.md Index\n\nNo files found.\n"

    avg_score = sum(f['score'] for f in files) / total_files

    # Group by category
    by_category = {}
    for f in files:
        cat = f['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(f)

    # Sort categories by count (descending)
    category_order = sorted(by_category.keys(), key=lambda c: -len(by_category[c]))

    # Build output
    lines = []
    lines.append("# CLAUDE.md Index")
    lines.append("")
    lines.append(f"**Generated:** {now.strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(f"**Total files:** {total_files}")
    lines.append(f"**Average compliance:** {avg_score:.1f}%")
    lines.append("")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Files | Avg Score |")
    lines.append("|----------|-------|-----------|")

    for cat in category_order:
        cat_files = by_category[cat]
        cat_avg = sum(f['score'] for f in cat_files) / len(cat_files)
        lines.append(f"| {cat} | {len(cat_files)} | {cat_avg:.0f}% |")

    lines.append("")

    # By category sections
    lines.append("## By Category")
    lines.append("")

    for cat in category_order:
        cat_files = sorted(by_category[cat], key=lambda f: str(f['relative_path']))
        cat_name = cat.title()

        lines.append(f"### {cat_name} ({len(cat_files)} files)")
        lines.append("")
        lines.append("| File | Purpose | Score | Updated |")
        lines.append("|------|---------|-------|---------|")

        for f in cat_files:
            link = make_relative_link(f['path'], base_path)
            purpose = f['purpose'][:50] + ('...' if len(f['purpose']) > 50 else '')
            score = f"{f['score']}%"
            updated = f['modified'].strftime('%Y-%m-%d')
            lines.append(f"| {link} | {purpose} | {score} | {updated} |")

        lines.append("")

    # Recently updated (last 10)
    lines.append("## Recently Updated")
    lines.append("")
    recent = sorted(files, key=lambda f: f['modified'], reverse=True)[:10]
    lines.append("| File | Category | Updated |")
    lines.append("|------|----------|---------|")

    for f in recent:
        link = make_relative_link(f['path'], base_path)
        lines.append(f"| {link} | {f['category']} | {f['modified'].strftime('%Y-%m-%d')} |")

    lines.append("")

    # Needs attention (score < 50%)
    needs_attention = [f for f in files if f['score'] < 50]
    if needs_attention:
        needs_attention = sorted(needs_attention, key=lambda f: f['score'])

        lines.append("## Needs Attention (Score < 50%)")
        lines.append("")
        lines.append("| File | Score | Issues |")
        lines.append("|------|-------|--------|")

        for f in needs_attention[:20]:  # Limit to 20
            link = make_relative_link(f['path'], base_path)
            issues_str = ', '.join(f['issues'][:3]) if f['issues'] else 'Low content'
            lines.append(f"| {link} | {f['score']}% | {issues_str} |")

        lines.append("")

    # Stubs (< 100 bytes)
    stubs = [f for f in files if f['size'] < 100]
    if stubs:
        lines.append("## Stubs (< 100 bytes)")
        lines.append("")
        lines.append("| File | Size |")
        lines.append("|------|------|")

        for f in sorted(stubs, key=lambda f: f['size']):
            link = make_relative_link(f['path'], base_path)
            lines.append(f"| {link} | {f['size']} bytes |")

        lines.append("")

    return '\n'.join(lines)


def generate_json_index(files: list[dict], base_path: Path) -> str:
    """
    Generate JSON index for programmatic use.
    """
    output = {
        'generated': datetime.now().isoformat(),
        'total_files': len(files),
        'average_score': sum(f['score'] for f in files) / len(files) if files else 0,
        'files': []
    }

    for f in files:
        output['files'].append({
            'path': str(f['path']),
            'relative_path': str(f['relative_path']),
            'category': f['category'],
            'score': f['score'],
            'issues': f['issues'],
            'purpose': f['purpose'],
            'size': f['size'],
            'modified': f['modified'].isoformat(),
        })

    return json.dumps(output, indent=2)


# =============================================================================
# Main
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='Generate master index of CLAUDE.md files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                                    # Generate default index
  %(prog)s --output /path/to/INDEX.md         # Custom output location
  %(prog)s --path /opt/ACTIVE/SCRAPERS/       # Scan specific directory
  %(prog)s --include-inactive                 # Include /opt/INACTIVE
  %(prog)s --format json --output index.json  # JSON output
        """
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help=f'Output file path (default: {DEFAULT_OUTPUT_PATH})'
    )

    parser.add_argument(
        '--path', '-p',
        type=Path,
        default=DEFAULT_SCAN_PATH,
        help=f'Directory to scan (default: {DEFAULT_SCAN_PATH})'
    )

    parser.add_argument(
        '--include-inactive',
        action='store_true',
        help='Include files from /opt/INACTIVE'
    )

    parser.add_argument(
        '--format', '-f',
        choices=['markdown', 'json'],
        default='markdown',
        help='Output format (default: markdown)'
    )

    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress progress output'
    )

    args = parser.parse_args()

    # Validate paths
    if not args.path.exists():
        print(f"Error: Scan path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Scan files
    if not args.quiet:
        print(f"Scanning {args.path} for CLAUDE.md files...")

    files = scan_claudemd_files(args.path, args.include_inactive)

    if not files:
        print("No CLAUDE.md files found.", file=sys.stderr)
        sys.exit(0)

    if not args.quiet:
        print(f"Found {len(files)} CLAUDE.md files")

    # Generate output
    if args.format == 'json':
        output = generate_json_index(files, args.path)
    else:
        output = generate_markdown_index(files, args.path)

    # Write output
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output, encoding='utf-8')
        if not args.quiet:
            print(f"Index written to: {args.output}")
    except Exception as e:
        print(f"Error writing output: {e}", file=sys.stderr)
        sys.exit(1)

    # Print summary stats
    if not args.quiet:
        avg_score = sum(f['score'] for f in files) / len(files)
        needs_attention = len([f for f in files if f['score'] < 50])
        stubs = len([f for f in files if f['size'] < 100])

        print(f"\nSummary:")
        print(f"  Total files: {len(files)}")
        print(f"  Average compliance: {avg_score:.1f}%")
        print(f"  Needs attention (< 50%): {needs_attention}")
        print(f"  Stubs (< 100 bytes): {stubs}")


if __name__ == '__main__':
    main()
