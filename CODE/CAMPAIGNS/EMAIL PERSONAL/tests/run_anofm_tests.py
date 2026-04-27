#!/usr/bin/env python3
"""
Run ANOFM PostgreSQL migration test suite with reporting.

Usage:
    python run_anofm_tests.py
    python run_anofm_tests.py --only connection
    python run_anofm_tests.py --fast
    python run_anofm_tests.py --html
"""

import subprocess
import sys
import argparse
import json
from pathlib import Path
from datetime import datetime


def run_tests(args):
    """Execute pytest with appropriate options."""
    cmd = ["pytest", "test_anofm_pg.py"]

    # Verbosity
    if args.verbose:
        cmd.append("-vv")
    else:
        cmd.append("-v")

    # Specific test class
    if args.only:
        cmd.append(f"-k {args.only}")

    # Skip slow tests
    if args.fast:
        cmd.append("-m 'not slow'")

    # Show print statements
    if args.show_output:
        cmd.append("-s")

    # HTML report
    if args.html:
        cmd.append("--html=test_report.html --self-contained-html")

    # Coverage
    if args.coverage:
        cmd.append("--cov=. --cov-report=html")

    # Parallel execution
    if args.parallel:
        cmd.append(f"-n {args.parallel}")

    # Fail on first error
    if args.exit_first:
        cmd.append("-x")

    # Filter warnings
    cmd.append("-W ignore::DeprecationWarning")

    print(f"\n{'='*70}")
    print(f"ANOFM PostgreSQL Migration Test Suite")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*70}\n")

    # Run pytest
    result = subprocess.run(" ".join(cmd), shell=True, cwd=Path(__file__).parent)

    return result.returncode


def print_summary():
    """Print test summary."""
    print(f"\n{'='*70}")
    print(f"Test Summary")
    print(f"{'='*70}")
    print(f"Connection Health Tests:    6")
    print(f"Data Integrity Tests:       4")
    print(f"Idempotency Tests:          2")
    print(f"Send Operations Tests:      4")
    print(f"Audit Logging Tests:        4")
    print(f"Rollback Recovery Tests:    3")
    print(f"Load Simulation Tests:      2")
    print(f"GDPR Compliance Tests:      3")
    print(f"{'='*70}")
    print(f"Total Test Cases:          28")
    print(f"{'='*70}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run ANOFM PostgreSQL migration test suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_anofm_tests.py              # Run all tests
  python run_anofm_tests.py --fast       # Skip slow tests (load, concurrent)
  python run_anofm_tests.py --only connection  # Only connection health tests
  python run_anofm_tests.py --html       # Generate HTML report
  python run_anofm_tests.py -vv --show-output  # Verbose + print statements
        """
    )

    parser.add_argument(
        "--only",
        help="Run only tests matching pattern (connection, integrity, etc)",
        default=None
    )

    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip slow tests (load simulation, concurrent)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Extra verbose output"
    )

    parser.add_argument(
        "-s", "--show-output",
        action="store_true",
        help="Show print statements and logging"
    )

    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML test report (test_report.html)"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report (htmlcov/)"
    )

    parser.add_argument(
        "-n", "--parallel",
        type=int,
        help="Run N tests in parallel",
        default=None
    )

    parser.add_argument(
        "-x", "--exit-first",
        action="store_true",
        help="Exit on first failure"
    )

    args = parser.parse_args()

    # Print summary
    print_summary()

    # Run tests
    exit_code = run_tests(args)

    # Print results
    print(f"\n{'='*70}")
    if exit_code == 0:
        print("[OK] All tests PASSED")
    else:
        print(f"[FAIL] Tests FAILED (exit code: {exit_code})")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}\n")

    if args.html:
        print(f"HTML Report: test_report.html\n")

    if args.coverage:
        print(f"Coverage Report: htmlcov/index.html\n")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
