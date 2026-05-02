#!/usr/bin/env python3
"""
Data Quality Checker Skill - Validate CSV outputs for quality issues
Checks for empty fields, duplicates, encoding issues, data patterns

Usage:
    python3 data_quality_checker.py /path/to/file.csv
    python3 data_quality_checker.py /mnt/hdd/SCRAPER_DATA/csv/ --all
    python3 data_quality_checker.py --country NORWAY

Examples:
    python3 data_quality_checker.py data.csv --fix  # Auto-fix issues
    python3 data_quality_checker.py --all --report  # Full report
"""

import sys
import os
import csv
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass, field

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

DATA_BASE = Path('/mnt/hdd/SCRAPER_DATA/csv')
SCRAPERS_BASE = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE')


@dataclass
class QualityIssue:
    """A data quality issue."""
    severity: str  # low, medium, high, critical
    category: str
    message: str
    count: int = 1
    examples: List[str] = field(default_factory=list)
    row_numbers: List[int] = field(default_factory=list)
    auto_fixable: bool = False


@dataclass
class QualityReport:
    """Quality report for a CSV file."""
    file_path: str
    total_rows: int = 0
    total_columns: int = 0
    issues: List[QualityIssue] = field(default_factory=list)
    column_stats: Dict[str, Dict] = field(default_factory=dict)
    score: int = 100  # 0-100

    def add_issue(self, issue: QualityIssue):
        self.issues.append(issue)
        # Deduct from score based on severity
        penalty = {'low': 1, 'medium': 3, 'high': 5, 'critical': 10}
        self.score = max(0, self.score - penalty.get(issue.severity, 1) * min(issue.count, 10))


class DataQualityChecker:
    """Check data quality in CSV files."""

    # Expected columns for scraper outputs
    EXPECTED_COLUMNS = {
        'job': ['title', 'company', 'location', 'url'],
        'contact': ['email', 'name', 'company'],
        'eures': ['employer', 'job_title', 'country', 'job_url']
    }

    def __init__(self):
        self.reports: Dict[str, QualityReport] = {}

    def detect_encoding(self, file_path: Path) -> str:
        """Detect file encoding."""
        encodings = ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']
        for enc in encodings:
            try:
                with open(file_path, 'r', encoding=enc) as f:
                    f.read(1000)
                return enc
            except (UnicodeDecodeError, UnicodeError):
                continue
        return 'utf-8'

    def check_file(self, file_path: Path) -> QualityReport:
        """Check quality of a single CSV file."""
        report = QualityReport(file_path=str(file_path))

        try:
            encoding = self.detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                # Check if file is empty
                first_line = f.readline()
                if not first_line.strip():
                    report.add_issue(QualityIssue(
                        severity='critical',
                        category='empty_file',
                        message='File is empty'
                    ))
                    return report

                f.seek(0)
                reader = csv.DictReader(f)
                headers = reader.fieldnames or []
                report.total_columns = len(headers)

                # Check headers
                self._check_headers(report, headers)

                # Initialize column stats
                column_values = defaultdict(list)
                column_empty = defaultdict(int)
                column_unique = defaultdict(set)

                rows = list(reader)
                report.total_rows = len(rows)

                if report.total_rows == 0:
                    report.add_issue(QualityIssue(
                        severity='high',
                        category='no_data',
                        message='File has headers but no data rows'
                    ))
                    return report

                # Analyze each row
                duplicate_check = defaultdict(list)
                for row_num, row in enumerate(rows, 2):  # Start at 2 (1 = header)
                    # Check for encoding issues
                    for col, val in row.items():
                        if val:
                            column_values[col].append(val)
                            column_unique[col].add(val)

                            # Check for encoding problems
                            if '\ufffd' in val or '?' in val and len(val) > 10:
                                if 'encoding' not in [i.category for i in report.issues]:
                                    report.add_issue(QualityIssue(
                                        severity='medium',
                                        category='encoding',
                                        message='Possible encoding issues detected',
                                        examples=[val[:50]],
                                        row_numbers=[row_num],
                                        auto_fixable=True
                                    ))
                        else:
                            column_empty[col] += 1

                    # Build duplicate key
                    key_cols = ['email', 'url', 'job_url', 'company']
                    key_parts = [row.get(c, '') for c in key_cols if c in headers and row.get(c)]
                    if key_parts:
                        dup_key = '|'.join(key_parts)
                        duplicate_check[dup_key].append(row_num)

                # Check for duplicates
                duplicates = [(k, v) for k, v in duplicate_check.items() if len(v) > 1]
                if duplicates:
                    total_dups = sum(len(v) - 1 for k, v in duplicates)
                    report.add_issue(QualityIssue(
                        severity='medium',
                        category='duplicates',
                        message=f'Found {total_dups} duplicate rows across {len(duplicates)} unique entries',
                        count=total_dups,
                        examples=[k[:50] for k, v in duplicates[:3]],
                        row_numbers=[v[1] for k, v in duplicates[:5]],
                        auto_fixable=True
                    ))

                # Check column fill rates
                for col in headers:
                    empty_count = column_empty[col]
                    fill_rate = ((report.total_rows - empty_count) / report.total_rows) * 100 if report.total_rows > 0 else 0
                    unique_count = len(column_unique[col])

                    report.column_stats[col] = {
                        'fill_rate': fill_rate,
                        'empty_count': empty_count,
                        'unique_count': unique_count,
                        'unique_ratio': unique_count / report.total_rows if report.total_rows > 0 else 0
                    }

                    # Flag very empty columns
                    if fill_rate < 10 and empty_count > 5:
                        report.add_issue(QualityIssue(
                            severity='low',
                            category='sparse_column',
                            message=f"Column '{col}' is {100-fill_rate:.0f}% empty",
                            count=empty_count
                        ))

                    # Flag columns with very low uniqueness (might be data issue)
                    if unique_count == 1 and report.total_rows > 10:
                        report.add_issue(QualityIssue(
                            severity='low',
                            category='constant_column',
                            message=f"Column '{col}' has only 1 unique value",
                            examples=[list(column_unique[col])[0][:30]]
                        ))

                # Check for data quality in specific columns
                self._check_column_patterns(report, column_values, headers)

        except Exception as e:
            report.add_issue(QualityIssue(
                severity='critical',
                category='read_error',
                message=f'Could not read file: {e}'
            ))

        self.reports[str(file_path)] = report
        return report

    def _check_headers(self, report: QualityReport, headers: List[str]):
        """Check header quality."""
        # Check for empty headers
        empty_headers = [i for i, h in enumerate(headers) if not h or h.isspace()]
        if empty_headers:
            report.add_issue(QualityIssue(
                severity='medium',
                category='empty_header',
                message=f'Found {len(empty_headers)} empty column headers',
                count=len(empty_headers)
            ))

        # Check for duplicate headers
        header_counts = Counter(headers)
        duplicates = [h for h, c in header_counts.items() if c > 1]
        if duplicates:
            report.add_issue(QualityIssue(
                severity='high',
                category='duplicate_header',
                message=f'Duplicate column headers: {", ".join(duplicates)}',
                count=len(duplicates)
            ))

        # Check for expected columns
        headers_lower = [h.lower() for h in headers]
        for data_type, expected in self.EXPECTED_COLUMNS.items():
            matches = sum(1 for exp in expected if any(exp in h for h in headers_lower))
            if matches >= 2:  # Likely this type of data
                missing = [exp for exp in expected if not any(exp in h for h in headers_lower)]
                if missing:
                    report.add_issue(QualityIssue(
                        severity='low',
                        category='missing_expected',
                        message=f'Missing expected columns for {data_type} data: {", ".join(missing)}',
                        count=len(missing)
                    ))
                break

    def _check_column_patterns(self, report: QualityReport, column_values: Dict, headers: List[str]):
        """Check data patterns in specific columns."""
        headers_lower = {h.lower(): h for h in headers}

        # Email validation
        email_cols = [headers_lower.get(c) for c in ['email', 'email1', 'email2'] if c in headers_lower]
        for col in filter(None, email_cols):
            values = column_values.get(col, [])
            invalid_emails = []
            for val in values:
                if val and '@' not in val:
                    invalid_emails.append(val)
            if invalid_emails:
                report.add_issue(QualityIssue(
                    severity='medium',
                    category='invalid_email',
                    message=f"Column '{col}' has {len(invalid_emails)} invalid email addresses",
                    count=len(invalid_emails),
                    examples=invalid_emails[:3],
                    auto_fixable=False
                ))

        # URL validation
        url_cols = [headers_lower.get(c) for c in ['url', 'job_url', 'company_website', 'website'] if c in headers_lower]
        for col in filter(None, url_cols):
            values = column_values.get(col, [])
            invalid_urls = []
            for val in values:
                if val and not val.startswith(('http://', 'https://', 'www.')):
                    invalid_urls.append(val)
            if invalid_urls and len(invalid_urls) > len(values) * 0.1:  # More than 10% invalid
                report.add_issue(QualityIssue(
                    severity='low',
                    category='invalid_url',
                    message=f"Column '{col}' has {len(invalid_urls)} potentially invalid URLs",
                    count=len(invalid_urls),
                    examples=invalid_urls[:3]
                ))

        # Phone validation (basic)
        phone_cols = [headers_lower.get(c) for c in ['phone', 'phone1', 'phone2', 'phone3'] if c in headers_lower]
        for col in filter(None, phone_cols):
            values = column_values.get(col, [])
            short_phones = [v for v in values if v and len(re.sub(r'\D', '', v)) < 7]
            if short_phones and len(short_phones) > 5:
                report.add_issue(QualityIssue(
                    severity='low',
                    category='short_phone',
                    message=f"Column '{col}' has {len(short_phones)} suspiciously short phone numbers",
                    count=len(short_phones),
                    examples=short_phones[:3]
                ))

    def check_directory(self, dir_path: Path, pattern: str = '*MASTER*.csv') -> List[QualityReport]:
        """Check all CSV files in directory."""
        reports = []
        for csv_file in dir_path.glob(f'**/{pattern}'):
            report = self.check_file(csv_file)
            reports.append(report)
        return reports

    def generate_report(self, alert_only: bool = False) -> str:
        """Generate quality report."""
        lines = []
        lines.append("=" * 70)
        lines.append("DATA QUALITY REPORT")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 70)

        total_files = len(self.reports)
        avg_score = sum(r.score for r in self.reports.values()) / total_files if total_files > 0 else 0

        lines.append(f"\nFiles analyzed: {total_files}")
        lines.append(f"Average quality score: {avg_score:.0f}/100")

        # Sort by score (worst first)
        sorted_reports = sorted(self.reports.items(), key=lambda x: x[1].score)

        for file_path, report in sorted_reports:
            if alert_only and report.score >= 90:
                continue

            score_icon = '✓' if report.score >= 80 else '⚠' if report.score >= 50 else '✗'

            lines.append(f"\n{'-' * 70}")
            lines.append(f"{score_icon} {Path(file_path).name}")
            lines.append(f"   Score: {report.score}/100 | Rows: {report.total_rows} | Columns: {report.total_columns}")

            if report.issues:
                lines.append(f"   Issues ({len(report.issues)}):")
                for issue in sorted(report.issues, key=lambda x: {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}.get(x.severity, 4)):
                    severity_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵'}[issue.severity]
                    lines.append(f"     {severity_icon} [{issue.category}] {issue.message}")
                    if issue.examples:
                        lines.append(f"        Examples: {', '.join(str(e)[:30] for e in issue.examples[:2])}")

        lines.append(f"\n{'=' * 70}")

        return '\n'.join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'generated': datetime.now().isoformat(),
            'total_files': len(self.reports),
            'average_score': sum(r.score for r in self.reports.values()) / len(self.reports) if self.reports else 0,
            'files': {
                path: {
                    'score': r.score,
                    'total_rows': r.total_rows,
                    'total_columns': r.total_columns,
                    'issues': [
                        {
                            'severity': i.severity,
                            'category': i.category,
                            'message': i.message,
                            'count': i.count
                        }
                        for i in r.issues
                    ]
                }
                for path, r in self.reports.items()
            }
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Data Quality Checker')
    parser.add_argument('path', nargs='?', help='File or directory to check')
    parser.add_argument('--all', action='store_true', help='Check all MASTER CSVs')
    parser.add_argument('--country', help='Check specific country')
    parser.add_argument('--alert', action='store_true', help='Only show problems')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--fix', action='store_true', help='Auto-fix issues (not implemented)')

    args = parser.parse_args()

    checker = DataQualityChecker()

    if args.path:
        path = Path(args.path)
        if path.is_file():
            checker.check_file(path)
        else:
            checker.check_directory(path)
    elif args.country:
        country_dirs = [
            DATA_BASE / args.country.upper(),
            SCRAPERS_BASE / args.country.upper() / 'OUTPUT',
            SCRAPERS_BASE / args.country.upper() / 'results',
        ]
        for d in country_dirs:
            if d.exists():
                checker.check_directory(d)
    elif args.all:
        checker.check_directory(DATA_BASE)
        checker.check_directory(SCRAPERS_BASE)
    else:
        print("Specify a path, --country, or --all")
        sys.exit(1)

    if args.json:
        print(json.dumps(checker.to_dict(), indent=2))
    else:
        print(checker.generate_report(alert_only=args.alert))


if __name__ == '__main__':
    main()
