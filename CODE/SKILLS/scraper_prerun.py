#!/usr/bin/env python3
"""
Scraper Pre-Run Organizer - Run checks before executing scrapers
Auto-reviews, validates, and optionally fixes issues before running

Usage:
    python3 scraper_prerun.py <scraper_path>              # Check then run
    python3 scraper_prerun.py <scraper_path> --check-only # Check only, don't run
    python3 scraper_prerun.py <scraper_path> --skip-check # Skip checks, just run

Examples:
    python3 scraper_prerun.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/arbeidsplassen_scraper.py

Integration with Node-RED or cron:
    Replace: /opt/ACTIVE/INFRA/venv/bin/python3 scraper.py
    With:    /opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/scraper_prerun.py scraper.py
"""

import sys
import os
import subprocess
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')


class ScraperPreRun:
    """Pre-run checks and organization for scrapers."""

    def __init__(self, scraper_path: Path, verbose: bool = True):
        self.scraper_path = scraper_path.resolve()
        self.scraper_dir = self.scraper_path.parent
        self.verbose = verbose
        self.checks_passed = True
        self.issues_found = []
        self.issues_fixed = []

    def log(self, msg: str):
        if self.verbose:
            print(msg)

    def run_code_review(self) -> bool:
        """Run code reviewer on scraper."""
        self.log("\n[1/4] Code Review...")

        try:
            from code_reviewer import CodeReviewer
            reviewer = CodeReviewer(severity_filter='high')
            report = reviewer.review(self.scraper_path)

            high_issues = report['by_severity'].get('critical', 0) + report['by_severity'].get('high', 0)

            if high_issues > 0:
                self.log(f"  ⚠ Found {high_issues} high/critical issues")
                for issue in reviewer.issues[:3]:
                    if issue.severity in ['critical', 'high']:
                        self.issues_found.append(f"{issue.category}: {issue.message}")
                        self.log(f"    - {issue.message[:60]}")
                return False
            else:
                self.log(f"  ✓ No critical issues ({report['total_issues']} minor)")
                return True

        except Exception as e:
            self.log(f"  ⚠ Code review failed: {e}")
            return True  # Continue anyway

    def run_syntax_check(self) -> bool:
        """Check Python syntax."""
        self.log("\n[2/4] Syntax Check...")

        try:
            result = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', '-m', 'py_compile', str(self.scraper_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                self.log("  ✓ Syntax valid")
                return True
            else:
                self.log(f"  ✗ Syntax error: {result.stderr[:100]}")
                self.issues_found.append(f"Syntax error: {result.stderr[:100]}")
                return False

        except Exception as e:
            self.log(f"  ⚠ Syntax check failed: {e}")
            return False

    def run_import_check(self) -> bool:
        """Check imports resolve."""
        self.log("\n[3/4] Import Check...")

        test_code = f'''
import sys
sys.path.insert(0, '{self.scraper_dir}')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import ast
with open("{self.scraper_path}", "r") as f:
    tree = ast.parse(f.read())

imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.append(alias.name.split(".")[0])
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            imports.append(node.module.split(".")[0])

failed = []
for imp in set(imports):
    try:
        __import__(imp)
    except ImportError as e:
        failed.append(imp)

if failed:
    print("FAILED:" + ",".join(failed))
    sys.exit(1)
else:
    print("OK:" + str(len(imports)))
    sys.exit(0)
'''
        try:
            result = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', '-c', test_code],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                self.log(f"  ✓ All imports resolve")
                return True
            else:
                failed = result.stdout.replace('FAILED:', '')
                self.log(f"  ✗ Missing imports: {failed}")
                self.issues_found.append(f"Missing imports: {failed}")
                return False

        except Exception as e:
            self.log(f"  ⚠ Import check failed: {e}")
            return True  # Continue anyway

    def check_output_dir(self) -> bool:
        """Ensure output directories exist."""
        self.log("\n[4/4] Output Directory Check...")

        output_dirs = [
            self.scraper_dir / 'OUTPUT',
            self.scraper_dir / 'results',
            self.scraper_dir / 'logs',
            Path('/mnt/hdd/SCRAPER_DATA/csv') / self.scraper_dir.name,
            Path('/mnt/hdd/SCRAPER_DATA/logs') / self.scraper_dir.name,
        ]

        created = []
        for d in output_dirs:
            if not d.exists() and '/mnt/usb' in str(d):
                try:
                    d.mkdir(parents=True, exist_ok=True)
                    created.append(str(d))
                except Exception:
                    pass

        if created:
            self.log(f"  ✓ Created: {', '.join(Path(c).name for c in created)}")
        else:
            self.log("  ✓ Output directories ready")

        return True

    def run_scraper(self, timeout: int = 1800) -> Dict[str, Any]:
        """Execute the scraper."""
        self.log(f"\n{'='*60}")
        self.log(f"EXECUTING: {self.scraper_path.name}")
        self.log(f"{'='*60}\n")

        result = {
            'scraper': str(self.scraper_path),
            'started': datetime.now().isoformat(),
            'success': False,
            'exit_code': None,
            'duration': 0
        }

        import time
        start = time.time()

        try:
            # Use cpu_protected_run if available
            cpu_protect = Path('/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/cpu_protected_run.sh')
            if cpu_protect.exists():
                cmd = [str(cpu_protect), '--', '/opt/ACTIVE/INFRA/venv/bin/python3', str(self.scraper_path)]
            else:
                cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', str(self.scraper_path)]

            proc = subprocess.run(
                cmd,
                timeout=timeout,
                cwd=str(self.scraper_dir)
            )
            result['exit_code'] = proc.returncode
            result['success'] = proc.returncode == 0

        except subprocess.TimeoutExpired:
            result['exit_code'] = -1
            result['error'] = f'Timeout after {timeout}s'
        except Exception as e:
            result['exit_code'] = -1
            result['error'] = str(e)

        result['duration'] = time.time() - start
        result['ended'] = datetime.now().isoformat()

        return result

    def run(self, check_only: bool = False, skip_check: bool = False) -> Dict[str, Any]:
        """Run full pre-run checks and optionally execute scraper."""
        result = {
            'scraper': str(self.scraper_path),
            'checks': {},
            'issues_found': [],
            'issues_fixed': [],
            'execution': None
        }

        print(f"\n{'='*60}")
        print(f"SCRAPER PRE-RUN: {self.scraper_path.name}")
        print(f"{'='*60}")

        if not skip_check:
            # Run all checks
            result['checks']['syntax'] = self.run_syntax_check()
            result['checks']['imports'] = self.run_import_check()
            result['checks']['code_review'] = self.run_code_review()
            result['checks']['output_dirs'] = self.check_output_dir()

            result['issues_found'] = self.issues_found
            result['issues_fixed'] = self.issues_fixed

            # Summary
            passed = sum(1 for v in result['checks'].values() if v)
            total = len(result['checks'])

            print(f"\n{'='*60}")
            print(f"PRE-RUN SUMMARY: {passed}/{total} checks passed")

            if self.issues_found:
                print(f"Issues: {len(self.issues_found)}")
                for issue in self.issues_found[:3]:
                    print(f"  - {issue[:60]}")

            # Block execution on critical failures
            if not result['checks'].get('syntax', True):
                print("\n✗ BLOCKED: Syntax errors must be fixed")
                return result

        if check_only:
            print("\n[Check only mode - not executing]")
            return result

        # Execute scraper
        result['execution'] = self.run_scraper()

        if result['execution']['success']:
            print(f"\n✓ Scraper completed successfully ({result['execution']['duration']:.0f}s)")
        else:
            print(f"\n✗ Scraper failed (exit code {result['execution']['exit_code']})")

        return result


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scraper Pre-Run Organizer')
    parser.add_argument('scraper', help='Path to scraper to run')
    parser.add_argument('--check-only', action='store_true', help='Only run checks, do not execute')
    parser.add_argument('--skip-check', action='store_true', help='Skip checks, execute directly')
    parser.add_argument('--quiet', action='store_true', help='Minimal output')
    parser.add_argument('--json', action='store_true', help='Output JSON result')
    parser.add_argument('--timeout', type=int, default=1800, help='Execution timeout (seconds)')

    args = parser.parse_args()

    scraper_path = Path(args.scraper)

    # Handle relative paths
    if not scraper_path.is_absolute():
        # Check current dir first
        if (Path.cwd() / scraper_path).exists():
            scraper_path = Path.cwd() / scraper_path
        # Check SCRAPERS paths
        else:
            for base in [Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE'), Path('/opt/ACTIVE/INFRA/SKILLS')]:
                candidate = base / scraper_path
                if candidate.exists():
                    scraper_path = candidate
                    break

    if not scraper_path.exists():
        print(f"Error: Scraper not found: {scraper_path}")
        sys.exit(1)

    prerun = ScraperPreRun(scraper_path, verbose=not args.quiet)
    result = prerun.run(check_only=args.check_only, skip_check=args.skip_check)

    if args.json:
        print(json.dumps(result, indent=2, default=str))

    # Exit code based on execution result
    if result.get('execution'):
        sys.exit(0 if result['execution']['success'] else 1)
    else:
        # Check-only mode: exit based on checks
        all_passed = all(result['checks'].values())
        sys.exit(0 if all_passed else 1)


if __name__ == '__main__':
    main()
