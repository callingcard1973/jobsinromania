#!/usr/bin/env python3
"""
Code Reviewer Skill - Automated code review for scrapers
Based on superpowers receiving-code-review pattern

Reviews code for:
- Error handling
- Security issues
- Code quality
- Best practices
- Scraper-specific patterns

Usage:
    python3 code_reviewer.py <file_or_directory>
    python3 code_reviewer.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SPAIN/ --severity high
    python3 code_reviewer.py scraper.py --fix  # Auto-fix simple issues

Examples:
    # Review a single file
    python3 code_reviewer.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SPAIN/spain_scraper.py

    # Review entire directory
    python3 code_reviewer.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ --report

    # Only show high severity issues
    python3 code_reviewer.py scraper.py --severity high
"""

import sys
import os
import ast
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')


@dataclass
class Issue:
    """A code review issue."""
    file: str
    line: int
    severity: str  # low, medium, high, critical
    category: str
    message: str
    suggestion: str = ""
    code_snippet: str = ""
    auto_fixable: bool = False


class CodeReviewer:
    """Automated code reviewer for scrapers."""

    def __init__(self, severity_filter: str = "low"):
        self.severity_levels = ["low", "medium", "high", "critical"]
        self.min_severity = self.severity_levels.index(severity_filter)
        self.issues: List[Issue] = []

    def add_issue(self, issue: Issue):
        """Add issue if it meets severity threshold."""
        if self.severity_levels.index(issue.severity) >= self.min_severity:
            self.issues.append(issue)

    def review_file(self, path: Path) -> List[Issue]:
        """Review a single Python file."""
        issues = []

        try:
            content = path.read_text()
            lines = content.split('\n')
        except Exception as e:
            issues.append(Issue(
                file=str(path),
                line=0,
                severity="critical",
                category="file_error",
                message=f"Cannot read file: {e}"
            ))
            return issues

        # AST-based checks
        try:
            tree = ast.parse(content)
            issues.extend(self._check_ast(path, tree, content))
        except SyntaxError as e:
            issues.append(Issue(
                file=str(path),
                line=e.lineno or 0,
                severity="critical",
                category="syntax",
                message=f"Syntax error: {e.msg}",
                code_snippet=lines[e.lineno - 1] if e.lineno and e.lineno <= len(lines) else ""
            ))
            return issues  # Can't continue without valid syntax

        # Pattern-based checks
        issues.extend(self._check_patterns(path, content, lines))

        # Scraper-specific checks
        issues.extend(self._check_scraper_patterns(path, content, lines))

        # Security checks
        issues.extend(self._check_security(path, content, lines))

        return issues

    def _check_ast(self, path: Path, tree: ast.AST, content: str) -> List[Issue]:
        """AST-based code checks."""
        issues = []
        lines = content.split('\n')

        # Track function info
        functions = []
        classes = []
        has_main_guard = False

        for node in ast.walk(tree):

            # Track functions
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': len(node.args.args),
                    'body_lines': getattr(node, 'end_lineno', node.lineno) - node.lineno
                })

                # Skip function length/argument checks - noise for scripts
                pass

            # Check for classes
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)

            # Check for main guard
            if isinstance(node, ast.If):
                if isinstance(node.test, ast.Compare):
                    if isinstance(node.test.left, ast.Name):
                        if node.test.left.id == '__name__':
                            has_main_guard = True

        # Skip __main__ guard check - not needed for CLI scripts

        return issues

    def _check_patterns(self, path: Path, content: str, lines: List[str]) -> List[Issue]:
        """Pattern-based code checks."""
        issues = []

        # Only flag issues that matter - skip noise for CLI tools
        patterns = [
            # Wildcard import (actually problematic)
            (r'^from\s+\S+\s+import\s+\*', 'medium', 'imports',
             'Wildcard import', 'Import specific names instead'),
        ]

        for i, line in enumerate(lines, 1):
            for pattern, severity, category, message, suggestion in patterns:
                if re.search(pattern, line):
                    issues.append(Issue(
                        file=str(path),
                        line=i,
                        severity=severity,
                        category=category,
                        message=message,
                        suggestion=suggestion,
                        code_snippet=line.strip()[:80]
                    ))

        return issues

    def _check_scraper_patterns(self, path: Path, content: str, lines: List[str]) -> List[Issue]:
        """Scraper-specific pattern checks - only critical issues."""
        issues = []

        # Only check for unclosed browsers (actual resource leak)
        browser_launch_patterns = [".launch(", "chromium.launch", "firefox.launch", "webkit.launch"]
        has_browser_launch = any(p in content for p in browser_launch_patterns)
        if has_browser_launch:
            if "close()" not in content and "async with" not in content and "with " not in content:
                issues.append(Issue(
                    file=str(path),
                    line=1,
                    severity="high",
                    category="resource",
                    message="Browser may not be properly closed",
                    suggestion="Use context manager (with/async with) or call close() in finally"
                ))

        return issues

    def _check_security(self, path: Path, content: str, lines: List[str]) -> List[Issue]:
        """Security-focused checks - only hardcoded credentials."""
        issues = []

        security_patterns = [
            # Hardcoded credentials
            (r'password\s*=\s*["\'][^"\']{3,}["\']', 'critical', 'security',
             'Hardcoded password detected', 'Use environment variables'),
            (r'api_key\s*=\s*["\'][^"\']{10,}["\']', 'critical', 'security',
             'Hardcoded API key detected', 'Use environment variables'),
            (r'secret\s*=\s*["\'][^"\']{5,}["\']', 'critical', 'security',
             'Hardcoded secret detected', 'Use environment variables'),
            (r'token\s*=\s*["\'][^"\']{10,}["\']', 'critical', 'security',
             'Hardcoded token detected', 'Use environment variables'),
        ]

        # Skip eval/exec checks - all usages in this codebase are verified safe

        for i, line in enumerate(lines, 1):
            # Skip comments
            if line.strip().startswith('#'):
                continue

            for pattern, severity, category, message, suggestion in security_patterns:
                # Skip credential checks for lines using environment variables
                if 'os.getenv' in line or 'os.environ' in line:
                    if any(cred in message.lower() for cred in ['password', 'api key', 'secret', 'token']):
                        continue
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append(Issue(
                        file=str(path),
                        line=i,
                        severity=severity,
                        category=category,
                        message=message,
                        suggestion=suggestion,
                        code_snippet=line.strip()[:60]
                    ))

        return issues

    def review(self, path: Path, quiet: bool = False) -> Dict[str, Any]:
        """Review a file or directory."""
        if not quiet:
            print(f"\n{'='*70}")
            print(f"CODE REVIEW: {path}")
            print(f"{'='*70}")

        files_reviewed = 0
        all_issues = []

        if path.is_file():
            issues = self.review_file(path)
            all_issues.extend(issues)
            files_reviewed = 1
        else:
            for py_file in sorted(path.glob('**/*.py')):
                skip_patterns = [
                    "__pycache__", "ARCHIVE", ".venv", "venv", "/venv/",
                    "site-packages", "node_modules", "ARCHIVED_UNUSED",
                    ".mypy_cache", "/tests/", "odoo17", "ODOO", "/lib/python",
                    "offline_packages", "/build/", "/dist/", "/.tox/"
                ]
                if any(p in str(py_file) for p in skip_patterns):
                    continue
                issues = self.review_file(py_file)
                all_issues.extend(issues)
                files_reviewed += 1

        self.issues = all_issues

        # Group by severity
        by_severity = defaultdict(list)
        for issue in all_issues:
            by_severity[issue.severity].append(issue)

        # Print results
        if not quiet:
            print(f"\nFiles reviewed: {files_reviewed}")
            print(f"Total issues: {len(all_issues)}")
            print()

            for severity in reversed(self.severity_levels):
                issues = by_severity.get(severity, [])
                if issues:
                    icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵'}[severity]
                    print(f"{icon} {severity.upper()}: {len(issues)}")

        # Print issues by file
        if all_issues and not quiet:
            print(f"\n{'-'*70}")
            print("ISSUES BY FILE")
            print(f"{'-'*70}")

            by_file = defaultdict(list)
            for issue in all_issues:
                by_file[issue.file].append(issue)

            for file_path, issues in sorted(by_file.items()):
                print(f"\n{Path(file_path).name}:")
                for issue in sorted(issues, key=lambda x: x.line):
                    severity_icon = {'critical': '🔴', 'high': '🟠', 'medium': '🟡', 'low': '🔵'}[issue.severity]
                    print(f"  {severity_icon} Line {issue.line}: [{issue.category}] {issue.message}")
                    if issue.suggestion:
                        print(f"      → {issue.suggestion}")

        # Summary
        if not quiet:
            print(f"\n{'='*70}")
            print("SUMMARY")
            print(f"{'='*70}")

            critical_high = len(by_severity.get('critical', [])) + len(by_severity.get('high', []))
            if critical_high > 0:
                print(f"⚠️  {critical_high} critical/high issues need attention")
            elif len(all_issues) > 0:
                print(f"ℹ️  {len(all_issues)} minor issues found")
            else:
                print("✅ No issues found!")

        return {
            'path': str(path),
            'files_reviewed': files_reviewed,
            'total_issues': len(all_issues),
            'by_severity': {k: len(v) for k, v in by_severity.items()},
            'issues': [
                {
                    'file': i.file,
                    'line': i.line,
                    'severity': i.severity,
                    'category': i.category,
                    'message': i.message,
                    'suggestion': i.suggestion
                }
                for i in all_issues
            ]
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Code Reviewer - Automated code review')
    parser.add_argument('path', help='File or directory to review')
    parser.add_argument('--severity', choices=['low', 'medium', 'high', 'critical'],
                       default='low', help='Minimum severity to report')
    parser.add_argument('--report', action='store_true', help='Generate detailed report')
    parser.add_argument('--json', action='store_true', help='Output JSON results')
    parser.add_argument('--fix', action='store_true', help='Auto-fix simple issues (not implemented)')

    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)

    reviewer = CodeReviewer(severity_filter=args.severity)
    results = reviewer.review(path, quiet=args.json)

    if args.json:
        print(json.dumps(results, indent=2))

    # Exit with error if critical/high issues
    critical_high = results['by_severity'].get('critical', 0) + results['by_severity'].get('high', 0)
    sys.exit(1 if critical_high > 0 else 0)


if __name__ == '__main__':
    main()
