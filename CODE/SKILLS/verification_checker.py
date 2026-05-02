#!/usr/bin/env python3
"""
Verification Checker Skill - Verify scraper/skill works before claiming done
Based on superpowers methodology: never claim done without verification

Usage:
    python3 verification_checker.py <script_path> [--output-dir /path] [--timeout 120]

Examples:
    python3 verification_checker.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SPAIN/scraper.py
    python3 verification_checker.py /opt/ACTIVE/INFRA/SKILLS/skill_01_linkedin.py --timeout 300
"""

import sys
import os
import json
import subprocess
import csv
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')


class VerificationChecker:
    """Verify that code actually works before claiming completion."""

    def __init__(self, script_path: str, output_dir: str = None, timeout: int = 120):
        self.script_path = Path(script_path).resolve()
        self.script_dir = self.script_path.parent
        self.output_dir = Path(output_dir) if output_dir else self.script_dir
        self.timeout = timeout
        self.checks: List[Dict] = []
        self.passed = 0
        self.failed = 0

    def check(self, name: str, condition: bool, detail: str = ''):
        """Record a check result."""
        status = 'PASS' if condition else 'FAIL'
        self.checks.append({
            'name': name,
            'passed': condition,
            'detail': detail
        })
        if condition:
            self.passed += 1
            print(f"  ✓ {name}")
        else:
            self.failed += 1
            print(f"  ✗ {name}: {detail}")

    def verify_file_exists(self) -> bool:
        """Check script file exists and is readable."""
        print("\n[1/7] File Verification")

        exists = self.script_path.exists()
        self.check('Script exists', exists, f'Not found: {self.script_path}')

        if exists:
            readable = os.access(self.script_path, os.R_OK)
            self.check('Script readable', readable)

            size = self.script_path.stat().st_size
            self.check('Script not empty', size > 0, f'Size: {size} bytes')

            # Check shebang or python content
            with open(self.script_path, 'r') as f:
                first_line = f.readline()
            is_python = 'python' in first_line or self.script_path.suffix == '.py'
            self.check('Is Python script', is_python)

            return readable and size > 0
        return False

    def verify_syntax(self) -> bool:
        """Check Python syntax is valid."""
        print("\n[2/7] Syntax Verification")

        try:
            result = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', '-m', 'py_compile', str(self.script_path)],
                capture_output=True,
                text=True,
                timeout=30
            )
            valid = result.returncode == 0
            self.check('Python syntax valid', valid, result.stderr[:200] if result.stderr else '')
            return valid
        except Exception as e:
            self.check('Python syntax valid', False, str(e))
            return False

    def verify_imports(self) -> bool:
        """Check all imports resolve."""
        print("\n[3/7] Import Verification")

        try:
            # Create test script that just imports
            test_code = f'''
import sys
sys.path.insert(0, '{self.script_dir}')
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Try importing the module
import importlib.util
spec = importlib.util.spec_from_file_location("test_module", "{self.script_path}")
module = importlib.util.module_from_spec(spec)

# Get imports from AST
import ast
with open("{self.script_path}", "r") as f:
    tree = ast.parse(f.read())

imports = []
for node in ast.walk(tree):
    if isinstance(node, ast.Import):
        for alias in node.names:
            imports.append(alias.name)
    elif isinstance(node, ast.ImportFrom):
        if node.module:
            imports.append(node.module)

# Try each import
failed = []
for imp in imports:
    try:
        __import__(imp.split(".")[0])
    except ImportError as e:
        failed.append(f"{{imp}}: {{e}}")

if failed:
    print("FAILED:" + "\\n".join(failed))
    sys.exit(1)
else:
    print("OK:" + str(len(imports)))
    sys.exit(0)
'''
            result = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', '-c', test_code],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                import_count = result.stdout.replace('OK:', '').strip()
                self.check('All imports resolve', True, f'{import_count} imports checked')
                return True
            else:
                failed = result.stdout.replace('FAILED:', '').strip()
                self.check('All imports resolve', False, failed[:200])
                return False

        except Exception as e:
            self.check('All imports resolve', False, str(e))
            return False

    def verify_execution(self) -> Tuple[bool, str, str]:
        """Run the script and check it completes."""
        print("\n[4/7] Execution Verification")

        try:
            result = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', str(self.script_path)],
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(self.script_dir),
                env={**os.environ, 'VERIFICATION_MODE': '1'}
            )

            # Check exit code
            success = result.returncode == 0
            self.check('Script completes', True, f'Exit code: {result.returncode}')
            self.check('Exit code zero', success, f'Got: {result.returncode}')

            # Check for error patterns in output
            error_patterns = [
                r'Traceback \(most recent call last\)',
                r'Error:',
                r'Exception:',
                r'CRITICAL:',
                r'FATAL:'
            ]

            combined = result.stdout + result.stderr
            has_errors = any(re.search(p, combined, re.IGNORECASE) for p in error_patterns)
            self.check('No error patterns', not has_errors,
                      'Found error patterns in output' if has_errors else '')

            return success, result.stdout, result.stderr

        except subprocess.TimeoutExpired:
            self.check('Script completes', False, f'Timeout after {self.timeout}s')
            return False, '', 'TIMEOUT'
        except Exception as e:
            self.check('Script completes', False, str(e))
            return False, '', str(e)

    def verify_output_files(self, stdout: str) -> bool:
        """Check if expected output files were created."""
        print("\n[5/7] Output Verification")

        # Look for CSV files in output
        csv_pattern = self.output_dir / '*.csv'
        master_pattern = self.output_dir / '*MASTER*.csv'

        # Check for any CSV
        csv_files = list(self.output_dir.glob('*.csv'))
        self.check('CSV files exist', len(csv_files) > 0,
                  f'Found {len(csv_files)} CSV files')

        # Check for MASTER CSV (common pattern)
        master_files = list(self.output_dir.glob('*MASTER*.csv'))
        if master_files:
            self.check('MASTER CSV exists', True, str(master_files[0].name))

            # Verify CSV is valid
            try:
                with open(master_files[0], 'r', encoding='utf-8') as f:
                    reader = csv.reader(f)
                    headers = next(reader, None)
                    rows = list(reader)

                self.check('CSV has headers', headers is not None and len(headers) > 0)
                self.check('CSV has data rows', len(rows) > 0, f'{len(rows)} rows')

                # Check for expected scraper columns
                expected_cols = ['company', 'title', 'location', 'url']
                has_expected = any(any(exp in h.lower() for h in headers) for exp in expected_cols)
                self.check('CSV has expected columns', has_expected,
                          f'Headers: {headers[:5]}...' if len(headers) > 5 else f'Headers: {headers}')

            except Exception as e:
                self.check('CSV readable', False, str(e))

        # Check stdout for success indicators
        success_patterns = [
            r'saved.*\d+.*records',
            r'wrote.*\d+.*rows',
            r'exported.*\d+',
            r'completed.*successfully',
            r'total.*\d+.*jobs'
        ]

        has_success = any(re.search(p, stdout, re.IGNORECASE) for p in success_patterns)
        self.check('Success message in output', has_success)

        return len(csv_files) > 0

    def verify_no_hardcoded_secrets(self) -> bool:
        """Check script doesn't contain hardcoded secrets."""
        print("\n[6/7] Security Verification")

        try:
            with open(self.script_path, 'r') as f:
                content = f.read()

            # Patterns that might indicate secrets
            secret_patterns = [
                (r'password\s*=\s*["\'][^"\']+["\']', 'hardcoded password'),
                (r'api_key\s*=\s*["\'][^"\']{20,}["\']', 'hardcoded API key'),
                (r'secret\s*=\s*["\'][^"\']+["\']', 'hardcoded secret'),
                (r'token\s*=\s*["\'][^"\']{20,}["\']', 'hardcoded token'),
            ]

            found_secrets = []
            for pattern, desc in secret_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    found_secrets.append(desc)

            no_secrets = len(found_secrets) == 0
            self.check('No hardcoded secrets', no_secrets,
                      f'Found: {", ".join(found_secrets)}' if found_secrets else '')

            # Check uses environment variables or config
            uses_env = 'os.environ' in content or 'os.getenv' in content
            uses_config = 'config' in content.lower() or '.env' in content
            self.check('Uses env vars or config', uses_env or uses_config or no_secrets,
                      'Consider using environment variables for credentials')

            return no_secrets

        except Exception as e:
            self.check('Security check', False, str(e))
            return False

    def verify_error_handling(self) -> bool:
        """Check script has proper error handling."""
        print("\n[7/7] Quality Verification")

        try:
            with open(self.script_path, 'r') as f:
                content = f.read()

            # Check for try/except
            has_try = 'try:' in content
            self.check('Has try/except blocks', has_try)

            # Check for logging
            has_logging = 'logging' in content or 'print(' in content
            self.check('Has logging/print statements', has_logging)

            # Check for main guard
            has_main = "if __name__ == '__main__'" in content or 'if __name__ == "__main__"' in content
            self.check('Has main guard', has_main)

            # Check docstring
            has_docstring = '"""' in content[:500] or "'''" in content[:500]
            self.check('Has module docstring', has_docstring)

            return has_try and has_main

        except Exception as e:
            self.check('Quality check', False, str(e))
            return False

    def run(self) -> Dict[str, Any]:
        """Run full verification suite."""
        print(f"\n{'='*70}")
        print(f"VERIFICATION CHECK: {self.script_path.name}")
        print(f"{'='*70}")

        results = {
            'script': str(self.script_path),
            'timestamp': datetime.now().isoformat(),
            'checks': [],
            'passed': 0,
            'failed': 0,
            'verified': False
        }

        # Run all verifications
        file_ok = self.verify_file_exists()
        if not file_ok:
            results['checks'] = self.checks
            results['passed'] = self.passed
            results['failed'] = self.failed
            return results

        syntax_ok = self.verify_syntax()
        imports_ok = self.verify_imports()

        if syntax_ok and imports_ok:
            exec_ok, stdout, stderr = self.verify_execution()
            self.verify_output_files(stdout)

        self.verify_no_hardcoded_secrets()
        self.verify_error_handling()

        # Summary
        results['checks'] = self.checks
        results['passed'] = self.passed
        results['failed'] = self.failed
        results['verified'] = self.failed == 0

        print(f"\n{'='*70}")
        print(f"VERIFICATION SUMMARY")
        print(f"{'='*70}")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")
        print(f"Status: {'✓ VERIFIED' if results['verified'] else '✗ NOT VERIFIED'}")
        print(f"{'='*70}\n")

        if self.failed > 0:
            print("Failed checks:")
            for check in self.checks:
                if not check['passed']:
                    print(f"  - {check['name']}: {check['detail']}")

        return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Verification Checker Skill')
    parser.add_argument('script', help='Path to script to verify')
    parser.add_argument('--output-dir', help='Directory to check for output files')
    parser.add_argument('--timeout', type=int, default=120, help='Execution timeout in seconds')
    parser.add_argument('--json', action='store_true', help='Output results as JSON')

    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"Error: Script not found: {args.script}")
        sys.exit(1)

    checker = VerificationChecker(args.script, args.output_dir, args.timeout)
    results = checker.run()

    if args.json:
        print(json.dumps(results, indent=2))

    # Exit with appropriate code
    sys.exit(0 if results['verified'] else 1)


if __name__ == '__main__':
    main()
