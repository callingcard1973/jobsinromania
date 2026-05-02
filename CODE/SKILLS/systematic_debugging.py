#!/usr/bin/env python3
"""
Systematic Debugging Skill - Debug scraper/skill failures methodically
Based on superpowers methodology: isolate, hypothesize, test, verify

Usage:
    python3 systematic_debugging.py <script_path> [--log-dir /path] [--max-iterations 10]

Examples:
    python3 systematic_debugging.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/SPAIN/scraper.py
    python3 systematic_debugging.py /opt/ACTIVE/INFRA/SKILLS/skill_01_linkedin.py --log-dir /tmp/debug
"""

import sys
import os
import json
import traceback
import ast
import subprocess
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

class SystematicDebugger:
    """Methodical debugging following superpowers methodology."""

    def __init__(self, script_path: str, log_dir: str = '/tmp/debug'):
        self.script_path = Path(script_path).resolve()
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.findings: List[Dict] = []
        self.hypotheses: List[Dict] = []

    def log(self, category: str, message: str, data: Dict = None):
        """Log debugging activity."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'category': category,
            'message': message,
            'data': data or {}
        }
        self.findings.append(entry)
        print(f"[{category.upper()}] {message}")
        if data:
            for k, v in data.items():
                print(f"  {k}: {v}")

    def step1_reproduce(self) -> Dict[str, Any]:
        """Step 1: Reproduce the error."""
        self.log('reproduce', f'Attempting to run: {self.script_path}')

        result = {
            'success': False,
            'output': '',
            'error': '',
            'exit_code': None
        }

        try:
            proc = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', str(self.script_path)],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.script_path.parent)
            )
            result['output'] = proc.stdout[-2000:] if len(proc.stdout) > 2000 else proc.stdout
            result['error'] = proc.stderr[-2000:] if len(proc.stderr) > 2000 else proc.stderr
            result['exit_code'] = proc.returncode
            result['success'] = proc.returncode == 0

        except subprocess.TimeoutExpired:
            result['error'] = 'TIMEOUT: Script took longer than 60 seconds'
        except Exception as e:
            result['error'] = str(e)

        self.log('reproduce',
                 'Success' if result['success'] else 'Failed',
                 {'exit_code': result['exit_code'], 'error_preview': result['error'][:200] if result['error'] else None})

        return result

    def step2_analyze_error(self, error_output: str) -> List[Dict]:
        """Step 2: Analyze the error to form hypotheses."""
        hypotheses = []

        # Common error patterns and likely causes
        patterns = [
            (r'ModuleNotFoundError: No module named [\'"](\w+)[\'"]',
             'missing_module', 'Install missing module: {}'),
            (r'ImportError: cannot import name [\'"](\w+)[\'"]',
             'import_error', 'Check if {} exists in the module'),
            (r'FileNotFoundError: .*[\'"]([^"\']+)[\'"]',
             'missing_file', 'File not found: {}'),
            (r'PermissionError:',
             'permission', 'Check file/directory permissions'),
            (r'ConnectionError|ConnectionRefusedError|TimeoutError',
             'network', 'Network connectivity issue - check URL/endpoint'),
            (r'JSONDecodeError',
             'json_parse', 'Invalid JSON response - check API response format'),
            (r'KeyError: [\'"](\w+)[\'"]',
             'key_error', 'Missing key in dict: {}'),
            (r'AttributeError: [\'"](\w+)[\'"] object has no attribute [\'"](\w+)[\'"]',
             'attr_error', 'Object {} missing attribute {}'),
            (r'TypeError: .* argument',
             'type_error', 'Function called with wrong argument types'),
            (r'IndentationError|TabError',
             'syntax', 'Check indentation - mixed tabs/spaces?'),
            (r'SyntaxError:',
             'syntax', 'Syntax error in code'),
            (r'RecursionError',
             'recursion', 'Infinite recursion detected'),
            (r'MemoryError',
             'memory', 'Out of memory - process data in chunks'),
            (r'selenium.*WebDriverException',
             'selenium', 'Selenium/browser issue - check chromedriver'),
            (r'requests\.exceptions\.',
             'requests', 'HTTP request failed - check URL and headers'),
        ]

        for pattern, category, suggestion in patterns:
            match = re.search(pattern, error_output, re.IGNORECASE)
            if match:
                groups = match.groups()
                msg = suggestion.format(*groups) if groups else suggestion
                hypotheses.append({
                    'category': category,
                    'pattern': pattern,
                    'match': match.group(0),
                    'suggestion': msg,
                    'confidence': 'high'
                })

        # Extract traceback location
        tb_pattern = r'File "([^"]+)", line (\d+), in (\w+)'
        for match in re.finditer(tb_pattern, error_output):
            file_path, line_num, func_name = match.groups()
            if '/opt/' in file_path:  # Only our code
                hypotheses.append({
                    'category': 'traceback',
                    'file': file_path,
                    'line': int(line_num),
                    'function': func_name,
                    'suggestion': f'Check {file_path}:{line_num} in {func_name}()',
                    'confidence': 'high'
                })

        self.hypotheses = hypotheses
        self.log('analyze', f'Generated {len(hypotheses)} hypotheses',
                 {'categories': list(set(h['category'] for h in hypotheses))})

        return hypotheses

    def step3_static_analysis(self) -> Dict[str, Any]:
        """Step 3: Static code analysis."""
        results = {
            'syntax_valid': False,
            'imports': [],
            'functions': [],
            'issues': []
        }

        try:
            with open(self.script_path, 'r') as f:
                source = f.read()

            tree = ast.parse(source)
            results['syntax_valid'] = True

            # Extract imports
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        results['imports'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ''
                    for alias in node.names:
                        results['imports'].append(f'{module}.{alias.name}')
                elif isinstance(node, ast.FunctionDef):
                    results['functions'].append({
                        'name': node.name,
                        'line': node.lineno,
                        'args': [a.arg for a in node.args.args]
                    })

            # Check for common issues
            # 1. Hardcoded paths that might not exist
            hardcoded = re.findall(r'["\'](/[^"\']+)["\']', source)
            for path in hardcoded:
                if not os.path.exists(path) and '/opt/' in path:
                    results['issues'].append({
                        'type': 'hardcoded_path',
                        'path': path,
                        'exists': False
                    })

            # 2. Check for required imports
            if 'selenium' in source and 'webdriver' not in str(results['imports']):
                results['issues'].append({
                    'type': 'missing_import',
                    'detail': 'Uses selenium but may be missing webdriver import'
                })

        except SyntaxError as e:
            results['issues'].append({
                'type': 'syntax_error',
                'line': e.lineno,
                'message': str(e)
            })
        except Exception as e:
            results['issues'].append({
                'type': 'parse_error',
                'message': str(e)
            })

        self.log('static', 'Static analysis complete',
                 {'syntax_valid': results['syntax_valid'],
                  'imports': len(results['imports']),
                  'functions': len(results['functions']),
                  'issues': len(results['issues'])})

        return results

    def step4_check_dependencies(self) -> Dict[str, Any]:
        """Step 4: Check if all dependencies are available."""
        results = {
            'missing_modules': [],
            'file_issues': [],
            'env_issues': []
        }

        try:
            with open(self.script_path, 'r') as f:
                source = f.read()

            # Extract import names
            tree = ast.parse(source)
            imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name.split('.')[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module.split('.')[0])

            # Check each import
            for module in imports:
                try:
                    __import__(module)
                except ImportError:
                    results['missing_modules'].append(module)

            # Check referenced files
            file_refs = re.findall(r'["\'](/opt/[^"\']+)["\']', source)
            for ref in file_refs:
                if not os.path.exists(ref):
                    results['file_issues'].append({
                        'path': ref,
                        'issue': 'not_found'
                    })
                elif os.path.isfile(ref) and not os.access(ref, os.R_OK):
                    results['file_issues'].append({
                        'path': ref,
                        'issue': 'not_readable'
                    })

            # Check environment
            env_vars = re.findall(r'os\.environ\[["\'](\w+)["\']\]', source)
            env_vars += re.findall(r'os\.getenv\(["\'](\w+)["\']', source)
            for var in env_vars:
                if not os.environ.get(var):
                    results['env_issues'].append(var)

        except Exception as e:
            self.log('deps', f'Dependency check error: {e}')

        self.log('deps', 'Dependency check complete',
                 {'missing_modules': results['missing_modules'],
                  'file_issues': len(results['file_issues']),
                  'env_issues': results['env_issues']})

        return results

    def step5_isolate_problem(self) -> Dict[str, Any]:
        """Step 5: Try to isolate the problem to a specific function."""
        results = {
            'isolated_to': None,
            'tests': []
        }

        try:
            with open(self.script_path, 'r') as f:
                source = f.read()

            tree = ast.parse(source)

            # Find main entry point
            has_main = 'if __name__' in source

            # Get function list
            functions = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        'name': node.name,
                        'line': node.lineno,
                        'end_line': getattr(node, 'end_lineno', node.lineno + 10)
                    })

            # Check if error traceback points to specific function
            for hyp in self.hypotheses:
                if hyp.get('category') == 'traceback' and hyp.get('function'):
                    func_name = hyp['function']
                    for func in functions:
                        if func['name'] == func_name:
                            results['isolated_to'] = func
                            break

            results['tests'] = [
                {'test': 'has_main_guard', 'result': has_main},
                {'test': 'function_count', 'result': len(functions)},
                {'test': 'isolated', 'result': results['isolated_to'] is not None}
            ]

        except Exception as e:
            self.log('isolate', f'Isolation error: {e}')

        self.log('isolate', 'Problem isolation complete',
                 {'isolated_to': results['isolated_to']['name'] if results['isolated_to'] else None})

        return results

    def generate_report(self, all_results: Dict) -> str:
        """Generate comprehensive debugging report."""
        report = []
        report.append("=" * 70)
        report.append(f"SYSTEMATIC DEBUG REPORT - {self.session_id}")
        report.append(f"Script: {self.script_path}")
        report.append("=" * 70)

        # Reproduction
        repro = all_results.get('reproduce', {})
        report.append("\n## 1. REPRODUCTION")
        report.append(f"Status: {'SUCCESS' if repro.get('success') else 'FAILED'}")
        report.append(f"Exit Code: {repro.get('exit_code')}")
        if repro.get('error'):
            report.append(f"Error:\n{repro['error'][:500]}")

        # Hypotheses
        report.append("\n## 2. HYPOTHESES")
        for i, hyp in enumerate(self.hypotheses[:10], 1):
            report.append(f"{i}. [{hyp['category'].upper()}] {hyp['suggestion']}")
            if hyp.get('match'):
                report.append(f"   Match: {hyp['match'][:100]}")

        # Static Analysis
        static = all_results.get('static', {})
        report.append("\n## 3. STATIC ANALYSIS")
        report.append(f"Syntax Valid: {static.get('syntax_valid')}")
        report.append(f"Functions: {len(static.get('functions', []))}")
        if static.get('issues'):
            report.append("Issues:")
            for issue in static['issues'][:5]:
                report.append(f"  - {issue}")

        # Dependencies
        deps = all_results.get('deps', {})
        report.append("\n## 4. DEPENDENCIES")
        if deps.get('missing_modules'):
            report.append(f"Missing Modules: {', '.join(deps['missing_modules'])}")
        if deps.get('file_issues'):
            report.append(f"File Issues: {len(deps['file_issues'])}")
            for fi in deps['file_issues'][:3]:
                report.append(f"  - {fi['path']}: {fi['issue']}")
        if deps.get('env_issues'):
            report.append(f"Missing Env Vars: {', '.join(deps['env_issues'])}")

        # Isolation
        isolation = all_results.get('isolate', {})
        report.append("\n## 5. PROBLEM ISOLATION")
        if isolation.get('isolated_to'):
            func = isolation['isolated_to']
            report.append(f"Isolated to: {func['name']}() at line {func['line']}")
        else:
            report.append("Could not isolate to specific function")

        # Recommendations
        report.append("\n## 6. RECOMMENDED FIXES")
        recommendations = self._generate_recommendations(all_results)
        for i, rec in enumerate(recommendations[:5], 1):
            report.append(f"{i}. {rec}")

        report.append("\n" + "=" * 70)

        return '\n'.join(report)

    def _generate_recommendations(self, all_results: Dict) -> List[str]:
        """Generate actionable recommendations."""
        recs = []

        deps = all_results.get('deps', {})
        if deps.get('missing_modules'):
            for mod in deps['missing_modules']:
                recs.append(f"Install missing module: pip install {mod}")

        if deps.get('file_issues'):
            for fi in deps['file_issues']:
                if fi['issue'] == 'not_found':
                    recs.append(f"Create or fix path: {fi['path']}")

        if deps.get('env_issues'):
            for var in deps['env_issues']:
                recs.append(f"Set environment variable: export {var}=<value>")

        for hyp in self.hypotheses:
            if hyp['category'] == 'network':
                recs.append("Check network connectivity and target URL availability")
            elif hyp['category'] == 'selenium':
                recs.append("Update chromedriver or check browser installation")
            elif hyp['category'] == 'permission':
                recs.append("Check file/directory permissions (chmod)")

        static = all_results.get('static', {})
        if not static.get('syntax_valid'):
            recs.insert(0, "FIX SYNTAX ERROR FIRST - code cannot run")

        if not recs:
            recs.append("Review error traceback for specific line causing issue")
            recs.append("Add debug logging to isolate the problem")

        return recs

    def run(self) -> Dict[str, Any]:
        """Run full debugging session."""
        print(f"\n{'='*70}")
        print(f"SYSTEMATIC DEBUGGING: {self.script_path.name}")
        print(f"{'='*70}\n")

        all_results = {}

        # Step 1: Reproduce
        print("\n[STEP 1/5] Reproducing error...")
        all_results['reproduce'] = self.step1_reproduce()

        # Step 2: Analyze error
        print("\n[STEP 2/5] Analyzing error...")
        error_text = all_results['reproduce'].get('error', '') + all_results['reproduce'].get('output', '')
        all_results['hypotheses'] = self.step2_analyze_error(error_text)

        # Step 3: Static analysis
        print("\n[STEP 3/5] Static code analysis...")
        all_results['static'] = self.step3_static_analysis()

        # Step 4: Check dependencies
        print("\n[STEP 4/5] Checking dependencies...")
        all_results['deps'] = self.step4_check_dependencies()

        # Step 5: Isolate problem
        print("\n[STEP 5/5] Isolating problem...")
        all_results['isolate'] = self.step5_isolate_problem()

        # Generate report
        report = self.generate_report(all_results)
        print(report)

        # Save report
        report_path = self.log_dir / f'debug_{self.session_id}.txt'
        with open(report_path, 'w') as f:
            f.write(report)
        print(f"\nReport saved: {report_path}")

        # Save JSON data
        json_path = self.log_dir / f'debug_{self.session_id}.json'
        with open(json_path, 'w') as f:
            json.dump({
                'script': str(self.script_path),
                'session': self.session_id,
                'results': all_results,
                'findings': self.findings
            }, f, indent=2, default=str)

        return all_results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Systematic Debugging Skill')
    parser.add_argument('script', help='Path to script to debug')
    parser.add_argument('--log-dir', default='/tmp/debug', help='Directory for debug logs')
    parser.add_argument('--max-iterations', type=int, default=10, help='Max debug iterations')

    args = parser.parse_args()

    if not os.path.exists(args.script):
        print(f"Error: Script not found: {args.script}")
        sys.exit(1)

    debugger = SystematicDebugger(args.script, args.log_dir)
    results = debugger.run()

    # Exit with appropriate code
    if results.get('reproduce', {}).get('success'):
        print("\n✓ Script runs successfully - no debugging needed")
        sys.exit(0)
    else:
        print("\n✗ Script has issues - see report above")
        sys.exit(1)


if __name__ == '__main__':
    main()
