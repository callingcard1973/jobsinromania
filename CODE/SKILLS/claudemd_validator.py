#!/usr/bin/env python3
"""
CLAUDE.md Validator - CI/pre-commit validation for CLAUDE.md compliance.

Validates CLAUDE.md files against the standard template with proper exit codes
for CI integration. Supports caching for faster re-runs and Telegram alerts.

Usage:
    # Validate single file
    python3 claudemd_validator.py /path/to/CLAUDE.md

    # Validate directory
    python3 claudemd_validator.py /opt/ACTIVE/ --recursive

    # Check specific category only
    python3 claudemd_validator.py /opt/ACTIVE/SCRAPERS/ --category scraper

    # Output formats
    python3 claudemd_validator.py /opt/ACTIVE/ --format text|json|github

    # Alert mode (for cron)
    python3 claudemd_validator.py /opt/ACTIVE/ --alert

Exit codes:
    0 = all valid
    1 = validation errors
    2 = runtime error
"""

import argparse
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

# Cache location
CACHE_FILE = Path("/tmp/claudemd_validator_cache.json")

# Category detection rules (reused from claudemd_auditor.py)
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

# Valid metadata categories
VALID_CATEGORIES = {"scraper", "campaign", "project", "infrastructure", "database"}

# Required metadata fields
REQUIRED_METADATA_FIELDS = {"Status", "Owner", "Updated", "Category"}


@dataclass
class ValidationIssue:
    """A single validation issue."""
    file: str
    line: int
    level: str  # "error" or "warning"
    message: str


@dataclass
class ValidationResult:
    """Validation result for a single file."""
    path: str
    valid: bool = True
    issues: List[ValidationIssue] = field(default_factory=list)
    category: str = "project"
    size_bytes: int = 0
    mtime: float = 0
    cached: bool = False

    def add_error(self, line: int, message: str):
        """Add an error (causes validation to fail)."""
        self.issues.append(ValidationIssue(self.path, line, "error", message))
        self.valid = False

    def add_warning(self, line: int, message: str):
        """Add a warning (does not fail validation unless --strict)."""
        self.issues.append(ValidationIssue(self.path, line, "warning", message))


def detect_category(path: Path) -> str:
    """Detect category based on file path."""
    path_str = str(path)
    for pattern, category in CATEGORY_RULES:
        if pattern in path_str:
            return category
    return "project"


def load_cache() -> Dict[str, Any]:
    """Load validation cache from disk."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_cache(cache: Dict[str, Any]):
    """Save validation cache to disk."""
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except IOError:
        pass


def get_file_hash(path: Path) -> str:
    """Get MD5 hash of file for cache validation."""
    try:
        content = path.read_bytes()
        return hashlib.md5(content).hexdigest()
    except IOError:
        return ""


def find_claude_md_files(base_path: Path, recursive: bool = True) -> List[Path]:
    """Find CLAUDE.md files in directory."""
    files = []
    try:
        if recursive:
            for f in base_path.rglob("CLAUDE.md"):
                if f.is_file():
                    files.append(f)
        else:
            f = base_path / "CLAUDE.md"
            if f.is_file():
                files.append(f)
    except PermissionError:
        pass
    return sorted(files)


def validate_date_format(date_str: str) -> bool:
    """Check if date is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str.strip(), "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_file(file_path: Path, cache: Dict[str, Any] = None) -> ValidationResult:
    """
    Validate a single CLAUDE.md file.

    Checks:
    - H1 title present and properly formatted
    - Metadata block present with required fields
    - Required sections for category present
    - No empty sections
    - File size > 200 bytes
    - Valid markdown syntax (no unclosed code blocks)
    - Internal links resolve
    - Date format valid (YYYY-MM-DD)
    - Category value valid
    """
    result = ValidationResult(path=str(file_path))

    try:
        stat = file_path.stat()
        result.size_bytes = stat.st_size
        result.mtime = stat.st_mtime
        result.category = detect_category(file_path)

        # Check cache
        if cache:
            cache_key = str(file_path)
            if cache_key in cache:
                cached = cache[cache_key]
                if cached.get("mtime") == result.mtime:
                    # Return cached result
                    result.valid = cached.get("valid", True)
                    result.cached = True
                    for issue in cached.get("issues", []):
                        result.issues.append(ValidationIssue(**issue))
                    return result

        content = file_path.read_text(encoding="utf-8", errors="replace")
        lines = content.split("\n")

        # Check 1: File size > 200 bytes
        if result.size_bytes < 200:
            result.add_error(1, f"File too small ({result.size_bytes} bytes, minimum 200)")

        # Check 2: H1 title present
        h1_match = re.search(r"^# (.+)$", content, re.MULTILINE)
        if not h1_match:
            result.add_error(1, "Missing H1 title (# Title)")
        else:
            # Check title formatting (should have content after #)
            title = h1_match.group(1).strip()
            if len(title) < 3:
                result.add_warning(
                    content[:h1_match.start()].count("\n") + 1,
                    f"H1 title too short: '{title}'"
                )

        # Check 3: Metadata block present with required fields
        # Look for HTML comment block or table with Status/Owner/Updated/Category
        metadata_pattern = r"<!--\s*METADATA.*?-->"
        table_pattern = r"\|\s*(Status|Owner|Updated|Category)\s*\|"

        has_metadata = False
        metadata_fields_found = set()

        # Check HTML comment metadata
        if re.search(metadata_pattern, content, re.DOTALL | re.IGNORECASE):
            has_metadata = True
            # Parse fields from comment
            metadata_match = re.search(r"<!--\s*METADATA(.*?)-->", content, re.DOTALL | re.IGNORECASE)
            if metadata_match:
                for field in REQUIRED_METADATA_FIELDS:
                    if re.search(rf"{field}\s*:", metadata_match.group(1), re.IGNORECASE):
                        metadata_fields_found.add(field)

        # Check table-style metadata
        for match in re.finditer(table_pattern, content, re.IGNORECASE):
            has_metadata = True
            metadata_fields_found.add(match.group(1).strip().title())

        # Also check for key: value style at top of file
        for line_num, line in enumerate(lines[:20], 1):  # Check first 20 lines
            for field in REQUIRED_METADATA_FIELDS:
                if re.match(rf"^\s*{field}\s*:", line, re.IGNORECASE):
                    has_metadata = True
                    metadata_fields_found.add(field)

        if not has_metadata:
            result.add_error(1, "Missing metadata block (Status, Owner, Updated, Category)")
        else:
            missing_fields = REQUIRED_METADATA_FIELDS - metadata_fields_found
            if missing_fields:
                result.add_warning(1, f"Metadata missing fields: {', '.join(sorted(missing_fields))}")

        # Check 4: Valid category value
        category_match = re.search(r"Category\s*[:\|]\s*(\w+)", content, re.IGNORECASE)
        if category_match:
            cat_value = category_match.group(1).lower()
            if cat_value not in VALID_CATEGORIES:
                line_num = content[:category_match.start()].count("\n") + 1
                result.add_error(
                    line_num,
                    f"Invalid category '{cat_value}', must be one of: {', '.join(sorted(VALID_CATEGORIES))}"
                )

        # Check 5: Date format valid (YYYY-MM-DD)
        date_match = re.search(r"Updated\s*[:\|]\s*(\d{4}[-/]\d{2}[-/]\d{2})", content)
        if date_match:
            date_str = date_match.group(1).replace("/", "-")
            if not validate_date_format(date_str):
                line_num = content[:date_match.start()].count("\n") + 1
                result.add_warning(line_num, f"Invalid date format: {date_match.group(1)}, use YYYY-MM-DD")

        # Check 6: Required sections for category
        sections = re.findall(r"^##\s+(.+)$", content, re.MULTILINE)
        sections_lower = [s.lower().strip() for s in sections]

        required = REQUIRED_SECTIONS.get(result.category, [])
        for req in required:
            found = any(req.lower() in s for s in sections_lower)
            if not found:
                result.add_error(1, f"Missing required section for {result.category}: {req}")

        # Check 7: No empty sections
        section_pattern = r"^##\s+(.+?)$(.*?)(?=^##\s+|\Z)"
        for match in re.finditer(section_pattern, content, re.MULTILINE | re.DOTALL):
            section_name = match.group(1).strip()
            section_content = match.group(2).strip()
            if len(section_content) < 10:  # Essentially empty
                line_num = content[:match.start()].count("\n") + 1
                result.add_warning(line_num, f"Empty section: {section_name}")

        # Check 8: Valid markdown syntax - unclosed code blocks
        code_block_count = len(re.findall(r"^```", content, re.MULTILINE))
        if code_block_count % 2 != 0:
            result.add_error(1, "Unclosed code block (odd number of ``` markers)")

        # Check 9: Internal CLAUDE.md links resolve
        # Check markdown links
        link_pattern = r"\[.*?\]\((.*?CLAUDE\.md.*?)\)"
        for match in re.finditer(link_pattern, content):
            link_path = match.group(1)
            # Handle relative paths
            if not link_path.startswith("/"):
                resolved = file_path.parent / link_path
            else:
                resolved = Path(link_path)
            if not resolved.exists():
                line_num = content[:match.start()].count("\n") + 1
                result.add_warning(line_num, f"Broken link: {link_path}")

        # Check plain path references
        path_refs = re.findall(r"(/opt/[^\s\)\"']+CLAUDE\.md)", content)
        for ref in path_refs:
            if not Path(ref).exists():
                line_num = content.find(ref)
                if line_num >= 0:
                    line_num = content[:line_num].count("\n") + 1
                else:
                    line_num = 1
                result.add_warning(line_num, f"Broken path reference: {ref}")

    except Exception as e:
        result.add_error(1, f"Error reading file: {e}")

    # Update cache
    if cache is not None:
        cache[str(file_path)] = {
            "mtime": result.mtime,
            "valid": result.valid,
            "issues": [asdict(i) for i in result.issues],
        }

    return result


def format_text(results: List[ValidationResult], verbose: bool = False) -> str:
    """Format results as plain text."""
    lines = []
    lines.append("=" * 70)
    lines.append("CLAUDE.md VALIDATION REPORT")
    lines.append("=" * 70)
    lines.append("")

    total = len(results)
    valid_count = sum(1 for r in results if r.valid)
    cached_count = sum(1 for r in results if r.cached)
    error_count = sum(len([i for i in r.issues if i.level == "error"]) for r in results)
    warning_count = sum(len([i for i in r.issues if i.level == "warning"]) for r in results)

    lines.append(f"Files checked:  {total}")
    lines.append(f"Valid:          {valid_count}")
    lines.append(f"Invalid:        {total - valid_count}")
    lines.append(f"Errors:         {error_count}")
    lines.append(f"Warnings:       {warning_count}")
    lines.append(f"From cache:     {cached_count}")
    lines.append("")

    # Show failures
    failures = [r for r in results if not r.valid]
    if failures:
        lines.append("-" * 70)
        lines.append("VALIDATION FAILURES")
        lines.append("-" * 70)

        for r in sorted(failures, key=lambda x: x.path):
            lines.append("")
            lines.append(f"File: {r.path}")
            lines.append(f"Category: {r.category}")
            for issue in r.issues:
                marker = "ERROR" if issue.level == "error" else "WARN"
                lines.append(f"  [{marker}] Line {issue.line}: {issue.message}")

    # Verbose: show all files
    if verbose:
        lines.append("")
        lines.append("-" * 70)
        lines.append("ALL FILES")
        lines.append("-" * 70)

        for r in sorted(results, key=lambda x: x.path):
            status = "VALID" if r.valid else "INVALID"
            cached = " (cached)" if r.cached else ""
            lines.append(f"  [{status}] {r.path}{cached}")
            if r.issues:
                for issue in r.issues:
                    marker = "E" if issue.level == "error" else "W"
                    lines.append(f"      [{marker}] L{issue.line}: {issue.message}")

    return "\n".join(lines)


def format_json(results: List[ValidationResult]) -> str:
    """Format results as JSON."""
    total = len(results)
    valid_count = sum(1 for r in results if r.valid)

    report = {
        "summary": {
            "total_files": total,
            "valid": valid_count,
            "invalid": total - valid_count,
            "errors": sum(len([i for i in r.issues if i.level == "error"]) for r in results),
            "warnings": sum(len([i for i in r.issues if i.level == "warning"]) for r in results),
            "generated_at": datetime.now().isoformat(),
        },
        "files": [
            {
                "path": r.path,
                "valid": r.valid,
                "category": r.category,
                "size_bytes": r.size_bytes,
                "cached": r.cached,
                "issues": [asdict(i) for i in r.issues],
            }
            for r in results
        ],
    }

    return json.dumps(report, indent=2)


def format_github(results: List[ValidationResult]) -> str:
    """Format results for GitHub Actions annotations."""
    lines = []

    for r in results:
        for issue in r.issues:
            if issue.level == "error":
                lines.append(f"::error file={r.path},line={issue.line}::{issue.message}")
            else:
                lines.append(f"::warning file={r.path},line={issue.line}::{issue.message}")

    return "\n".join(lines)


def send_telegram_alert(message: str) -> bool:
    """Send alert via Telegram using shared alerting module."""
    try:
        # Try to import from shared module
        sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
        from alerting import AlertManager

        alerter = AlertManager()
        result = alerter.send("CLAUDE.md Compliance", message, level="warning")
        return result.get('telegram', False)
    except ImportError:
        # Fallback: direct API call
        try:
            import requests
            from dotenv import load_dotenv

            load_dotenv('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env')

            token = os.getenv('TELEGRAM_BOT_TOKEN')
            chat_id = os.getenv('TELEGRAM_CHAT_ID')

            if not token or not chat_id:
                return False

            response = requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    'chat_id': chat_id,
                    'text': f"CLAUDE.md Compliance Alert\n\n{message}",
                    'parse_mode': 'Markdown',
                },
                timeout=10,
            )
            return response.status_code == 200
        except Exception:
            return False


def main():
    parser = argparse.ArgumentParser(
        description="Validate CLAUDE.md files for CI/pre-commit checks.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python3 claudemd_validator.py /path/to/CLAUDE.md
    python3 claudemd_validator.py /opt/ACTIVE/ --recursive
    python3 claudemd_validator.py /opt/ACTIVE/SCRAPERS/ --category scraper
    python3 claudemd_validator.py /opt/ACTIVE/ --format github
    python3 claudemd_validator.py /opt/ACTIVE/ --alert

Exit codes:
    0 = all valid
    1 = validation errors
    2 = runtime error
        """
    )

    parser.add_argument(
        "path",
        type=Path,
        nargs="?",
        default=Path("/opt/ACTIVE/"),
        help="File or directory to validate (default: /opt/ACTIVE/)"
    )
    parser.add_argument(
        "--recursive", "-r",
        action="store_true",
        default=True,
        help="Recursively scan directory (default: true)"
    )
    parser.add_argument(
        "--category",
        choices=list(VALID_CATEGORIES),
        help="Filter by category"
    )
    parser.add_argument(
        "--format", "-f",
        choices=["text", "json", "github"],
        default="text",
        help="Output format (default: text)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show details for each file"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors"
    )
    parser.add_argument(
        "--alert",
        action="store_true",
        help="Send Telegram alert if violations found"
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore cache, re-validate all files"
    )

    args = parser.parse_args()

    # Validate path exists
    if not args.path.exists():
        print(f"Error: Path does not exist: {args.path}", file=sys.stderr)
        sys.exit(2)

    # Find files to validate
    if args.path.is_file():
        if args.path.name != "CLAUDE.md":
            print(f"Error: Not a CLAUDE.md file: {args.path}", file=sys.stderr)
            sys.exit(2)
        files = [args.path]
    else:
        files = find_claude_md_files(args.path, recursive=args.recursive)

    if not files:
        print(f"No CLAUDE.md files found in {args.path}")
        sys.exit(0)

    # Load cache
    cache = {} if args.no_cache else load_cache()

    # Validate files
    results = []
    for f in files:
        result = validate_file(f, cache)

        # Apply strict mode
        if args.strict:
            for issue in result.issues:
                if issue.level == "warning":
                    result.valid = False

        results.append(result)

    # Filter by category if specified
    if args.category:
        results = [r for r in results if r.category == args.category]

    # Save cache
    if not args.no_cache:
        save_cache(cache)

    # Generate output
    if args.format == "text":
        print(format_text(results, verbose=args.verbose))
    elif args.format == "json":
        print(format_json(results))
    elif args.format == "github":
        output = format_github(results)
        if output:
            print(output)

    # Check for failures
    failures = [r for r in results if not r.valid]

    # Send alert if requested and there are failures
    if args.alert and failures:
        error_count = sum(len([i for i in r.issues if i.level == "error"]) for r in failures)
        warning_count = sum(len([i for i in r.issues if i.level == "warning"]) for r in failures)

        msg = f"{len(failures)} files with issues\n"
        msg += f"Errors: {error_count}, Warnings: {warning_count}\n\n"

        # List first 5 failures
        for r in failures[:5]:
            short_path = r.path.replace("/opt/ACTIVE/", "")
            errors = [i for i in r.issues if i.level == "error"]
            if errors:
                msg += f"- {short_path}: {errors[0].message}\n"

        if len(failures) > 5:
            msg += f"\n... and {len(failures) - 5} more"

        send_telegram_alert(msg)

    # Exit code
    if failures:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
