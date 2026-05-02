#!/usr/bin/env python3
"""
Scraper Tester Skill - TDD-style testing framework for scrapers
Test scrapers before deployment to catch issues early

Usage:
    python3 scraper_tester.py <scraper_path> [--quick] [--full] [--report]

Examples:
    python3 scraper_tester.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SPAIN/
    python3 scraper_tester.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SPAIN/spain_scraper.py --quick
    python3 scraper_tester.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ --full --report
"""

import sys
import os
import json
import subprocess
import csv
import re
import ast
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')


class ScraperTest:
    """Individual test case for a scraper."""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.passed = None
        self.message = ''
        self.duration = 0

    def run(self, func, *args, **kwargs) -> bool:
        """Run test and capture result."""
        start = time.time()
        try:
            result = func(*args, **kwargs)
            self.passed = bool(result)
            if isinstance(result, str):
                self.message = result
        except Exception as e:
            self.passed = False
            self.message = str(e)
        self.duration = time.time() - start
        return self.passed


class ScraperTester:
    """TDD-style testing framework for scrapers."""

    def __init__(self, path: str, quick: bool = False):
        self.path = Path(path).resolve()
        self.quick = quick
        self.tests: List[ScraperTest] = []
        self.scrapers: List[Path] = []
        self.results: Dict[str, List[ScraperTest]] = defaultdict(list)

    def discover_scrapers(self) -> List[Path]:
        """Find all scraper files."""
        scrapers = []

        if self.path.is_file():
            scrapers.append(self.path)
        else:
            # Look for scraper patterns
            patterns = [
                '*scraper*.py',
                '*_scraper.py',
                'scrape_*.py',
                'fetch_*.py'
            ]
            for pattern in patterns:
                scrapers.extend(self.path.glob(f'**/{pattern}'))

            # Also check for main.py in scraper directories
            for main in self.path.glob('**/main.py'):
                if 'scraper' in str(main.parent).lower():
                    scrapers.append(main)

        # Deduplicate
        self.scrapers = list(set(scrapers))
        return self.scrapers

    def test_file_structure(self, scraper: Path) -> List[ScraperTest]:
        """Test basic file structure."""
        tests = []

        # Test: File exists and readable
        t = ScraperTest('file_exists', 'Scraper file exists and is readable')
        t.run(lambda: scraper.exists() and os.access(scraper, os.R_OK))
        tests.append(t)

        # Test: Has Python extension
        t = ScraperTest('python_file', 'File has .py extension')
        t.run(lambda: scraper.suffix == '.py')
        tests.append(t)

        # Test: Not empty
        t = ScraperTest('not_empty', 'File is not empty')
        t.run(lambda: scraper.stat().st_size > 100)
        tests.append(t)

        return tests

    def test_code_quality(self, scraper: Path) -> List[ScraperTest]:
        """Test code quality requirements."""
        tests = []

        try:
            content = scraper.read_text()
        except Exception:
            return tests

        # Test: Valid Python syntax
        t = ScraperTest('valid_syntax', 'Python syntax is valid')
        def check_syntax():
            try:
                ast.parse(content)
                return True
            except SyntaxError as e:
                return f'Line {e.lineno}: {e.msg}'
        t.run(check_syntax)
        tests.append(t)

        if not t.passed:
            return tests  # Can't continue without valid syntax

        # Test: Has docstring
        t = ScraperTest('has_docstring', 'Module has docstring')
        t.run(lambda: content.strip().startswith('"""') or content.strip().startswith("'''"))
        tests.append(t)

        # Test: Has main guard
        t = ScraperTest('main_guard', 'Has if __name__ == "__main__" guard')
        t.run(lambda: "__name__" in content and "__main__" in content)
        tests.append(t)

        # Test: Has error handling
        t = ScraperTest('error_handling', 'Has try/except blocks')
        t.run(lambda: 'try:' in content and 'except' in content)
        tests.append(t)

        # Test: Has logging
        t = ScraperTest('has_logging', 'Uses logging or print for output')
        t.run(lambda: 'logging' in content or 'print(' in content)
        tests.append(t)

        # Test: No hardcoded credentials
        t = ScraperTest('no_hardcoded_creds', 'No hardcoded passwords/tokens')
        def check_creds():
            patterns = [
                r'password\s*=\s*["\'][^"\']{5,}["\']',
                r'api_key\s*=\s*["\'][^"\']{15,}["\']',
                r'token\s*=\s*["\'][^"\']{15,}["\']',
            ]
            for p in patterns:
                if re.search(p, content, re.IGNORECASE):
                    return False
            return True
        t.run(check_creds)
        tests.append(t)

        return tests

    def test_imports(self, scraper: Path) -> List[ScraperTest]:
        """Test that all imports resolve."""
        tests = []

        try:
            content = scraper.read_text()
            tree = ast.parse(content)
        except Exception:
            return tests

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split('.')[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split('.')[0])

        # Test each import
        failed_imports = []
        for imp in imports:
            try:
                __import__(imp)
            except ImportError:
                failed_imports.append(imp)

        t = ScraperTest('imports_resolve', f'All {len(imports)} imports resolve')
        t.run(lambda: len(failed_imports) == 0 or f'Missing: {", ".join(failed_imports)}')
        t.passed = len(failed_imports) == 0
        if failed_imports:
            t.message = f'Missing: {", ".join(failed_imports)}'
        tests.append(t)

        return tests

    def test_output_format(self, scraper: Path) -> List[ScraperTest]:
        """Test that scraper output follows expected format."""
        tests = []

        try:
            content = scraper.read_text()
        except Exception:
            return tests

        # Test: Uses CSV output
        t = ScraperTest('csv_output', 'Uses CSV for output')
        t.run(lambda: 'csv' in content.lower() or 'to_csv' in content or 'writerow' in content)
        tests.append(t)

        # Test: Has expected column names
        t = ScraperTest('standard_columns', 'References standard column names')
        standard_cols = ['title', 'company', 'location', 'url', 'description', 'date']
        def check_cols():
            found = [c for c in standard_cols if c in content.lower()]
            return len(found) >= 3 or f'Found only: {found}'
        t.run(check_cols)
        tests.append(t)

        # Test: Has MASTER file pattern
        t = ScraperTest('master_pattern', 'Uses MASTER file naming convention')
        t.run(lambda: 'MASTER' in content or 'master' in content.lower())
        tests.append(t)

        return tests

    def test_execution(self, scraper: Path) -> List[ScraperTest]:
        """Test actual execution (skipped in quick mode)."""
        tests = []

        if self.quick:
            t = ScraperTest('execution', 'Execution test (skipped in quick mode)')
            t.passed = None
            t.message = 'Skipped'
            tests.append(t)
            return tests

        # Test: Script runs without immediate crash
        t = ScraperTest('runs_briefly', 'Script starts without immediate crash')
        def run_briefly():
            try:
                result = subprocess.run(
                    ['/opt/ACTIVE/INFRA/venv/bin/python3', str(scraper), '--help'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    cwd=str(scraper.parent)
                )
                # --help might not work, try just running for a bit
                if result.returncode != 0:
                    result = subprocess.run(
                        ['/opt/ACTIVE/INFRA/venv/bin/python3', str(scraper)],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        cwd=str(scraper.parent),
                        env={**os.environ, 'SCRAPER_TEST_MODE': '1'}
                    )
                return result.returncode == 0 or 'Traceback' not in result.stderr
            except subprocess.TimeoutExpired:
                return True  # Timeout is OK, means it started
            except Exception as e:
                return str(e)
        t.run(run_briefly)
        tests.append(t)

        return tests

    def test_scraper(self, scraper: Path) -> Dict[str, Any]:
        """Run all tests for a single scraper."""
        all_tests = []

        print(f"\n  Testing: {scraper.name}")

        # Run test suites
        all_tests.extend(self.test_file_structure(scraper))
        all_tests.extend(self.test_code_quality(scraper))
        all_tests.extend(self.test_imports(scraper))
        all_tests.extend(self.test_output_format(scraper))
        all_tests.extend(self.test_execution(scraper))

        self.results[str(scraper)] = all_tests

        # Count results
        passed = sum(1 for t in all_tests if t.passed is True)
        failed = sum(1 for t in all_tests if t.passed is False)
        skipped = sum(1 for t in all_tests if t.passed is None)

        return {
            'scraper': str(scraper),
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'tests': [{'name': t.name, 'passed': t.passed, 'message': t.message} for t in all_tests]
        }

    def run(self) -> Dict[str, Any]:
        """Run all tests on discovered scrapers."""
        print(f"\n{'='*70}")
        print(f"SCRAPER TESTER - {'Quick' if self.quick else 'Full'} Mode")
        print(f"Path: {self.path}")
        print(f"{'='*70}")

        self.discover_scrapers()
        print(f"\nDiscovered {len(self.scrapers)} scraper(s)")

        all_results = []
        total_passed = 0
        total_failed = 0
        total_skipped = 0

        for scraper in sorted(self.scrapers):
            result = self.test_scraper(scraper)
            all_results.append(result)
            total_passed += result['passed']
            total_failed += result['failed']
            total_skipped += result['skipped']

            # Print quick summary
            status = '✓' if result['failed'] == 0 else '✗'
            print(f"    {status} {result['passed']}/{result['passed']+result['failed']} passed")

        # Summary
        print(f"\n{'='*70}")
        print("SUMMARY")
        print(f"{'='*70}")
        print(f"Scrapers tested: {len(self.scrapers)}")
        print(f"Total tests: {total_passed + total_failed + total_skipped}")
        print(f"  Passed: {total_passed}")
        print(f"  Failed: {total_failed}")
        print(f"  Skipped: {total_skipped}")

        # List failures
        if total_failed > 0:
            print(f"\n{'='*70}")
            print("FAILURES")
            print(f"{'='*70}")
            for result in all_results:
                failures = [t for t in result['tests'] if t['passed'] is False]
                if failures:
                    print(f"\n{Path(result['scraper']).name}:")
                    for t in failures:
                        print(f"  ✗ {t['name']}: {t['message']}")

        return {
            'path': str(self.path),
            'mode': 'quick' if self.quick else 'full',
            'timestamp': datetime.now().isoformat(),
            'scrapers': len(self.scrapers),
            'total_passed': total_passed,
            'total_failed': total_failed,
            'total_skipped': total_skipped,
            'results': all_results
        }


def generate_report(results: Dict, output_path: Path):
    """Generate HTML report."""
    html = f'''<!DOCTYPE html>
<html>
<head>
    <title>Scraper Test Report</title>
    <style>
        body {{ font-family: monospace; margin: 20px; }}
        .pass {{ color: green; }}
        .fail {{ color: red; }}
        .skip {{ color: gray; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f4f4f4; }}
    </style>
</head>
<body>
    <h1>Scraper Test Report</h1>
    <p>Generated: {results['timestamp']}</p>
    <p>Path: {results['path']}</p>
    <p>Mode: {results['mode']}</p>

    <h2>Summary</h2>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Scrapers</td><td>{results['scrapers']}</td></tr>
        <tr><td class="pass">Passed</td><td>{results['total_passed']}</td></tr>
        <tr><td class="fail">Failed</td><td>{results['total_failed']}</td></tr>
        <tr><td class="skip">Skipped</td><td>{results['total_skipped']}</td></tr>
    </table>

    <h2>Details</h2>
'''

    for r in results['results']:
        scraper_name = Path(r['scraper']).name
        status_class = 'pass' if r['failed'] == 0 else 'fail'
        html += f'''
    <h3 class="{status_class}">{scraper_name}</h3>
    <table>
        <tr><th>Test</th><th>Result</th><th>Message</th></tr>
'''
        for t in r['tests']:
            if t['passed'] is True:
                result_class = 'pass'
                result_text = 'PASS'
            elif t['passed'] is False:
                result_class = 'fail'
                result_text = 'FAIL'
            else:
                result_class = 'skip'
                result_text = 'SKIP'

            html += f'''        <tr>
            <td>{t['name']}</td>
            <td class="{result_class}">{result_text}</td>
            <td>{t['message']}</td>
        </tr>
'''
        html += '    </table>\n'

    html += '''
</body>
</html>
'''

    output_path.write_text(html)
    print(f"\nReport saved: {output_path}")


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scraper Tester - TDD for scrapers')
    parser.add_argument('path', help='Path to scraper file or directory')
    parser.add_argument('--quick', action='store_true', help='Skip execution tests')
    parser.add_argument('--full', action='store_true', help='Run all tests including execution')
    parser.add_argument('--report', action='store_true', help='Generate HTML report')
    parser.add_argument('--json', action='store_true', help='Output JSON results')
    parser.add_argument('--output', help='Output directory for reports', default='/tmp')

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: Path not found: {args.path}")
        sys.exit(1)

    # Default to quick mode unless --full specified
    quick = not args.full

    tester = ScraperTester(args.path, quick=quick)
    results = tester.run()

    if args.json:
        print(json.dumps(results, indent=2))

    if args.report:
        report_path = Path(args.output) / f'scraper_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
        generate_report(results, report_path)

    # Exit with appropriate code
    sys.exit(0 if results['total_failed'] == 0 else 1)


if __name__ == '__main__':
    main()
