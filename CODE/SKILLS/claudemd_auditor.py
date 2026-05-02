#!/usr/bin/python3
"""
CLAUDE.md Auditor - Analyze and validate CLAUDE.md files across the codebase.

Scans directories for CLAUDE.md files, analyzes their structure and content,
and generates compliance reports with scoring.

Usage:
    python3 claudemd_auditor.py                    # Scan /opt/ACTIVE/
    python3 claudemd_auditor.py --path /opt/       # Custom path
    python3 claudemd_auditor.py --format json      # JSON output
    python3 claudemd_auditor.py --format markdown --output report.md
    python3 claudemd_auditor.py --category scraper # Filter by category
    python3 claudemd_auditor.py --verbose          # Detailed output
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ClaudeMdAnalysis:
    """Analysis results for a single CLAUDE.md file."""
    path: str
    size_bytes: int = 0
    size_lines: int = 0
    last_modified: str = ""
    has_h1_title: bool = False
    h1_title: str = ""
    sections: list = field(default_factory=list)
    has_metadata_block: bool = False
    category: str = "project"
    empty_sections: list = field(default_factory=list)
    broken_links: list = field(default_factory=list)
    missing_required_sections: list = field(default_factory=list)
    compliance_score: int = 0
    issues: list = field(default_factory=list)


# Category detection rules
CATEGORY_RULES = [
    ("/SCRAPERS/", "scraper"),
    ("/EMAIL/CAMPAIGNS/", "campaign"),
    ("/PROJECTS/", "project"),
    ("/INFRA/", "infrastructure"),
    ("/DB/", "database"),
    ("/DATABASE/", "database"),
]

# Required sections by category
REQUIRED_SECTIONS = {
    "scraper": ["Purpose", "Quick Start", "Output"],
    "campaign": ["Purpose", "Quick Start", "Files"],
    "project": ["Purpose"],
    "infrastructure": ["Purpose", "Quick Start", "Files"],
    "database": ["Purpose", "Tables"],
}


def detect_category(path: Path) -> str:
    """Detect category based on file path."""
    path_str = str(path)
    for pattern, category in CATEGORY_RULES:
        if pattern in path_str:
            return category
    return "project"


def find_claude_md_files(base_path: Path) -> list[Path]:
    """Find all CLAUDE.md files recursively."""
    files = []
    try:
        for f in base_path.rglob("CLAUDE.md"):
            if f.is_file():
                files.append(f)
    except PermissionError:
        pass
    return sorted(files)


def analyze_file(file_path: Path, base_path: Path) -> ClaudeMdAnalysis:
    """Analyze a single CLAUDE.md file."""
    analysis = ClaudeMdAnalysis(path=str(file_path))

    try:
        stat = file_path.stat()
        analysis.size_bytes = stat.st_size
        analysis.last_modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")
        analysis.size_lines = len(lines)

        # Detect category
        analysis.category = detect_category(file_path)

        # Check for H1 title
        h1_match = re.search(r"^# (.+)$", content, re.MULTILINE)
        if h1_match:
            analysis.has_h1_title = True
            analysis.h1_title = h1_match.group(1).strip()

        # Find sections (## headers)
        sections = re.findall(r"^## (.+)$", content, re.MULTILINE)
        analysis.sections = sections

        # Check for metadata block
        if re.search(r"<!--\s*METADATA.*?-->", content, re.DOTALL | re.IGNORECASE):
            analysis.has_metadata_block = True

        # Detect empty sections
        section_pattern = r"^## (.+?)$(.*?)(?=^## |\Z)"
        for match in re.finditer(section_pattern, content, re.MULTILINE | re.DOTALL):
            section_name = match.group(1).strip()
            section_content = match.group(2).strip()
            if len(section_content) < 10:  # Essentially empty
                analysis.empty_sections.append(section_name)

        # Check for broken internal CLAUDE.md links
        link_pattern = r"\[.*?\]\((.*?CLAUDE\.md.*?)\)"
        for match in re.finditer(link_pattern, content):
            link_path = match.group(1)
            # Handle relative paths
            if not link_path.startswith("/"):
                resolved = file_path.parent / link_path
            else:
                resolved = Path(link_path)
            if not resolved.exists():
                analysis.broken_links.append(link_path)

        # Also check plain path references
        path_refs = re.findall(r"(/opt/[^\s\)\"']+CLAUDE\.md)", content)
        for ref in path_refs:
            if not Path(ref).exists():
                if ref not in analysis.broken_links:
                    analysis.broken_links.append(ref)

        # Check required sections for category
        required = REQUIRED_SECTIONS.get(analysis.category, [])
        sections_lower = [s.lower() for s in analysis.sections]
        for req in required:
            # Fuzzy match - check if required section name is contained
            found = any(req.lower() in s for s in sections_lower)
            if not found:
                analysis.missing_required_sections.append(req)

        # Calculate compliance score
        score = 0

        # Has H1 title: +20 points
        if analysis.has_h1_title:
            score += 20
        else:
            analysis.issues.append("Missing H1 title")

        # Has metadata block: +20 points
        if analysis.has_metadata_block:
            score += 20
        else:
            analysis.issues.append("Missing metadata block")

        # Has all required sections: +30 points
        if not analysis.missing_required_sections:
            score += 30
        else:
            analysis.issues.append(f"Missing sections: {', '.join(analysis.missing_required_sections)}")

        # No empty sections: +15 points
        if not analysis.empty_sections:
            score += 15
        else:
            analysis.issues.append(f"Empty sections: {', '.join(analysis.empty_sections)}")

        # File size > 200 bytes: +15 points
        if analysis.size_bytes > 200:
            score += 15
        else:
            analysis.issues.append("File too small (<200 bytes)")

        # Broken links penalty
        if analysis.broken_links:
            analysis.issues.append(f"Broken links: {', '.join(analysis.broken_links)}")

        analysis.compliance_score = score

    except Exception as e:
        analysis.issues.append(f"Error reading file: {e}")
        analysis.compliance_score = 0

    return analysis


def generate_text_report(analyses: list[ClaudeMdAnalysis], verbose: bool = False) -> str:
    """Generate human-readable text report."""
    lines = []
    lines.append("=" * 70)
    lines.append("CLAUDE.md AUDIT REPORT")
    lines.append("=" * 70)
    lines.append("")

    # Summary statistics
    total = len(analyses)
    if total == 0:
        lines.append("No CLAUDE.md files found.")
        return "\n".join(lines)

    avg_size = sum(a.size_bytes for a in analyses) / total
    avg_score = sum(a.compliance_score for a in analyses) / total

    # Category breakdown
    categories = {}
    for a in analyses:
        categories[a.category] = categories.get(a.category, 0) + 1

    lines.append("SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Total files:     {total}")
    lines.append(f"Average size:    {avg_size:.0f} bytes")
    lines.append(f"Average score:   {avg_score:.1f}/100")
    lines.append("")
    lines.append("Category breakdown:")
    for cat, count in sorted(categories.items()):
        lines.append(f"  {cat:20s} {count:3d} files")
    lines.append("")

    # Score distribution
    excellent = sum(1 for a in analyses if a.compliance_score >= 85)
    good = sum(1 for a in analyses if 70 <= a.compliance_score < 85)
    fair = sum(1 for a in analyses if 50 <= a.compliance_score < 70)
    poor = sum(1 for a in analyses if a.compliance_score < 50)

    lines.append("Score distribution:")
    lines.append(f"  Excellent (85-100):  {excellent:3d}")
    lines.append(f"  Good (70-84):        {good:3d}")
    lines.append(f"  Fair (50-69):        {fair:3d}")
    lines.append(f"  Poor (0-49):         {poor:3d}")
    lines.append("")

    # Files with issues
    files_with_issues = [a for a in analyses if a.issues]
    if files_with_issues:
        lines.append("=" * 70)
        lines.append("FILES WITH ISSUES")
        lines.append("=" * 70)

        for a in sorted(files_with_issues, key=lambda x: x.compliance_score):
            lines.append("")
            lines.append(f"File: {a.path}")
            lines.append(f"Score: {a.compliance_score}/100 | Category: {a.category}")
            lines.append("Issues:")
            for issue in a.issues:
                lines.append(f"  - {issue}")

    # Verbose: show all files
    if verbose:
        lines.append("")
        lines.append("=" * 70)
        lines.append("ALL FILES")
        lines.append("=" * 70)

        for a in sorted(analyses, key=lambda x: x.path):
            lines.append("")
            lines.append(f"File: {a.path}")
            lines.append(f"  Size: {a.size_bytes} bytes ({a.size_lines} lines)")
            lines.append(f"  Modified: {a.last_modified}")
            lines.append(f"  Category: {a.category}")
            lines.append(f"  Score: {a.compliance_score}/100")
            if a.h1_title:
                lines.append(f"  Title: {a.h1_title}")
            if a.sections:
                lines.append(f"  Sections: {', '.join(a.sections[:5])}" +
                           ("..." if len(a.sections) > 5 else ""))
            if a.issues:
                lines.append("  Issues:")
                for issue in a.issues:
                    lines.append(f"    - {issue}")

    return "\n".join(lines)


def generate_json_report(analyses: list[ClaudeMdAnalysis]) -> str:
    """Generate JSON report."""
    total = len(analyses)
    avg_size = sum(a.size_bytes for a in analyses) / total if total else 0
    avg_score = sum(a.compliance_score for a in analyses) / total if total else 0

    categories = {}
    for a in analyses:
        categories[a.category] = categories.get(a.category, 0) + 1

    report = {
        "summary": {
            "total_files": total,
            "average_size_bytes": round(avg_size),
            "average_compliance_score": round(avg_score, 1),
            "category_breakdown": categories,
            "generated_at": datetime.now().isoformat(),
        },
        "files": [asdict(a) for a in analyses],
    }

    return json.dumps(report, indent=2)


def generate_markdown_report(analyses: list[ClaudeMdAnalysis]) -> str:
    """Generate Markdown report."""
    lines = []
    lines.append("# CLAUDE.md Audit Report")
    lines.append("")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")

    # Summary
    total = len(analyses)
    if total == 0:
        lines.append("No CLAUDE.md files found.")
        return "\n".join(lines)

    avg_size = sum(a.size_bytes for a in analyses) / total
    avg_score = sum(a.compliance_score for a in analyses) / total

    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total files | {total} |")
    lines.append(f"| Average size | {avg_size:.0f} bytes |")
    lines.append(f"| Average score | {avg_score:.1f}/100 |")
    lines.append("")

    # Category breakdown
    categories = {}
    for a in analyses:
        categories[a.category] = categories.get(a.category, 0) + 1

    lines.append("## Category Breakdown")
    lines.append("")
    lines.append("| Category | Count |")
    lines.append("|----------|-------|")
    for cat, count in sorted(categories.items()):
        lines.append(f"| {cat} | {count} |")
    lines.append("")

    # Files table
    lines.append("## All Files")
    lines.append("")
    lines.append("| Path | Category | Score | Issues |")
    lines.append("|------|----------|-------|--------|")

    for a in sorted(analyses, key=lambda x: x.compliance_score):
        # Truncate path for readability
        short_path = a.path.replace("/opt/ACTIVE/", "")
        if len(short_path) > 45:
            short_path = "..." + short_path[-42:]
        issue_count = len(a.issues)
        lines.append(f"| {short_path} | {a.category} | {a.compliance_score} | {issue_count} |")

    lines.append("")

    # Detailed issues
    files_with_issues = [a for a in analyses if a.issues]
    if files_with_issues:
        lines.append("## Files with Issues")
        lines.append("")

        for a in sorted(files_with_issues, key=lambda x: x.compliance_score):
            lines.append(f"### {a.path}")
            lines.append("")
            lines.append(f"- **Score:** {a.compliance_score}/100")
            lines.append(f"- **Category:** {a.category}")
            lines.append("- **Issues:**")
            for issue in a.issues:
                lines.append(f"  - {issue}")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Analyze and validate CLAUDE.md files across the codebase.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 claudemd_auditor.py                    # Scan /opt/ACTIVE/
  python3 claudemd_auditor.py --path /opt/       # Custom path
  python3 claudemd_auditor.py --format json      # JSON output
  python3 claudemd_auditor.py --format markdown --output report.md
  python3 claudemd_auditor.py --category scraper # Filter by category
  python3 claudemd_auditor.py --verbose          # Detailed output
        """
    )

    parser.add_argument(
        "--path",
        type=Path,
        default=Path("/opt/ACTIVE/"),
        help="Directory to scan (default: /opt/ACTIVE/)"
    )
    parser.add_argument(
        "--format",
        choices=["text", "json", "markdown"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for markdown format"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show details for each file"
    )
    parser.add_argument(
        "--category",
        choices=["scraper", "campaign", "project", "infrastructure", "database"],
        help="Filter by category"
    )

    args = parser.parse_args()

    # Validate path
    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(1)

    # Find files
    files = find_claude_md_files(args.path)

    if not files:
        print(f"No CLAUDE.md files found in {args.path}")
        sys.exit(0)

    # Analyze files
    analyses = [analyze_file(f, args.path) for f in files]

    # Filter by category if specified
    if args.category:
        analyses = [a for a in analyses if a.category == args.category]

    # Generate report
    if args.format == "text":
        report = generate_text_report(analyses, verbose=args.verbose)
        print(report)
    elif args.format == "json":
        report = generate_json_report(analyses)
        print(report)
    elif args.format == "markdown":
        report = generate_markdown_report(analyses)
        if args.output:
            args.output.write_text(report)
            print(f"Report saved to {args.output}")
        else:
            print(report)


if __name__ == "__main__":
    main()
