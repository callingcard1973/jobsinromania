#!/usr/bin/env python3
"""
Plan Executor Skill - Execute multi-step pipelines
Based on superpowers executing-plans pattern

Define pipelines as YAML/JSON and execute step by step with:
- Conditional execution
- Error handling and rollback
- Progress tracking
- Notifications

Usage:
    python3 plan_executor.py <plan_file.yaml>
    python3 plan_executor.py --template scrape_sync  # Use built-in template
    python3 plan_executor.py --list-templates

Examples:
    # Execute a plan file
    python3 plan_executor.py /opt/ACTIVE/SCRAPERS/EUROPE/plans/spain_pipeline.yaml

    # Use built-in scrape-sync template
    python3 plan_executor.py --template scrape_sync --country SPAIN

    # Dry run
    python3 plan_executor.py plan.yaml --dry-run
"""

import sys
import os
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import re

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

# Try to import yaml, fall back to JSON-only if not available
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


@dataclass
class Step:
    """A single step in a plan."""
    name: str
    command: str
    description: str = ""
    working_dir: str = ""
    timeout: int = 300
    continue_on_error: bool = False
    condition: str = ""  # Python expression
    on_success: str = ""  # Next step name
    on_failure: str = ""  # Step name or "abort"
    env: Dict[str, str] = field(default_factory=dict)
    # Runtime
    status: str = "pending"
    exit_code: Optional[int] = None
    output: str = ""
    error: str = ""
    duration: float = 0


@dataclass
class Plan:
    """A complete execution plan."""
    name: str
    description: str = ""
    steps: List[Step] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    on_complete: str = ""  # Command to run on completion
    on_failure: str = ""   # Command to run on failure
    notify: bool = True


# Built-in templates
TEMPLATES = {
    'scrape_sync': {
        'name': 'Scrape and Sync Pipeline',
        'description': 'Scrape a country, dedupe, sync to raspi',
        'variables': {
            'country': 'SPAIN',
            'scraper_base': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE'
        },
        'steps': [
            {
                'name': 'scrape',
                'description': 'Run the scraper',
                'command': '/opt/ACTIVE/INFRA/venv/bin/python3 ${scraper_base}/${country}/*scraper*.py',
                'working_dir': '${scraper_base}/${country}',
                'timeout': 1800
            },
            {
                'name': 'verify_output',
                'description': 'Verify scraper produced output',
                'command': 'ls -la *MASTER*.csv | head -5',
                'working_dir': '${scraper_base}/${country}',
                'timeout': 10
            },
            {
                'name': 'dedupe',
                'description': 'Remove duplicates from output',
                'command': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/contact_dedup.py *MASTER*.csv --in-place',
                'working_dir': '${scraper_base}/${country}',
                'timeout': 120,
                'continue_on_error': True
            },
            {
                'name': 'sync_to_raspi',
                'description': 'Sync output to raspi',
                'command': 'rsync -avz *MASTER*.csv raspi:/home/tudor/SCRAPER_DATA/${country}/',
                'working_dir': '${scraper_base}/${country}',
                'timeout': 60
            },
            {
                'name': 'notify',
                'description': 'Send completion notification',
                'command': 'echo "Pipeline complete for ${country}"',
                'timeout': 10
            }
        ]
    },
    'full_pipeline': {
        'name': 'Full Scraping Pipeline',
        'description': 'Scrape all countries, dedupe, sync, report',
        'variables': {
            'scraper_base': '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE'
        },
        'steps': [
            {
                'name': 'parallel_scrape',
                'description': 'Run all scrapers in parallel',
                'command': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/parallel_dispatcher.py ${scraper_base} --max-parallel 3',
                'timeout': 7200  # 2 hours
            },
            {
                'name': 'audit',
                'description': 'Audit all outputs',
                'command': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/code_execution.py audit ${scraper_base}',
                'timeout': 300
            },
            {
                'name': 'sync_all',
                'description': 'Sync all data to raspi',
                'command': 'rsync -avz /mnt/hdd/SCRAPER_DATA/ raspi:/home/tudor/SCRAPER_DATA/',
                'timeout': 600
            }
        ]
    },
    'test_scraper': {
        'name': 'Test Scraper Pipeline',
        'description': 'Test a scraper before deployment',
        'variables': {
            'scraper_path': ''
        },
        'steps': [
            {
                'name': 'syntax_check',
                'description': 'Check Python syntax',
                'command': '/opt/ACTIVE/INFRA/venv/bin/python3 -m py_compile ${scraper_path}',
                'timeout': 30
            },
            {
                'name': 'test',
                'description': 'Run scraper tests',
                'command': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/scraper_tester.py ${scraper_path} --quick',
                'timeout': 120
            },
            {
                'name': 'verify',
                'description': 'Verify scraper works',
                'command': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/verification_checker.py ${scraper_path} --timeout 60',
                'timeout': 120
            },
            {
                'name': 'review',
                'description': 'Code review',
                'command': '/opt/ACTIVE/INFRA/venv/bin/python3 /opt/ACTIVE/INFRA/SKILLS/code_reviewer.py ${scraper_path}',
                'timeout': 60,
                'continue_on_error': True
            }
        ]
    }
}


class PlanExecutor:
    """Execute multi-step plans."""

    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.context: Dict[str, Any] = {}
        self.current_step: Optional[Step] = None

    def load_plan(self, path: Path) -> Plan:
        """Load plan from YAML or JSON file."""
        content = path.read_text()

        if path.suffix in ['.yaml', '.yml']:
            if not HAS_YAML:
                raise ValueError("PyYAML not installed. Use JSON or: pip install pyyaml")
            data = yaml.safe_load(content)
        else:
            data = json.loads(content)

        return self._parse_plan(data)

    def load_template(self, name: str, variables: Dict[str, str] = None) -> Plan:
        """Load a built-in template."""
        if name not in TEMPLATES:
            raise ValueError(f"Unknown template: {name}. Available: {list(TEMPLATES.keys())}")

        data = TEMPLATES[name].copy()
        if variables:
            data['variables'].update(variables)

        return self._parse_plan(data)

    def _parse_plan(self, data: Dict) -> Plan:
        """Parse plan data into Plan object."""
        steps = []
        for step_data in data.get('steps', []):
            steps.append(Step(
                name=step_data['name'],
                command=step_data['command'],
                description=step_data.get('description', ''),
                working_dir=step_data.get('working_dir', ''),
                timeout=step_data.get('timeout', 300),
                continue_on_error=step_data.get('continue_on_error', False),
                condition=step_data.get('condition', ''),
                on_success=step_data.get('on_success', ''),
                on_failure=step_data.get('on_failure', ''),
                env=step_data.get('env', {})
            ))

        return Plan(
            name=data.get('name', 'Unnamed Plan'),
            description=data.get('description', ''),
            steps=steps,
            variables=data.get('variables', {}),
            on_complete=data.get('on_complete', ''),
            on_failure=data.get('on_failure', ''),
            notify=data.get('notify', True)
        )

    def substitute_variables(self, text: str, variables: Dict[str, str]) -> str:
        """Substitute ${var} patterns in text."""
        result = text
        for key, value in variables.items():
            result = result.replace(f'${{{key}}}', str(value))
        # Also handle $var syntax
        for key, value in variables.items():
            result = re.sub(rf'\$\b{key}\b', str(value), result)
        return result

    def check_condition(self, condition: str, variables: Dict[str, str]) -> bool:
        """Evaluate a condition expression."""
        if not condition:
            return True

        # Substitute variables
        condition = self.substitute_variables(condition, variables)

        # Safe evaluation context
        safe_context = {
            'exists': os.path.exists,
            'isfile': os.path.isfile,
            'isdir': os.path.isdir,
            'env': os.environ.get,
            'True': True,
            'False': False,
        }
        safe_context.update(variables)

        try:
            return bool(eval(condition, {"__builtins__": {}}, safe_context))
        except Exception as e:
            print(f"  Warning: Condition evaluation failed: {e}")
            return True

    def execute_step(self, step: Step, variables: Dict[str, str]) -> Step:
        """Execute a single step."""
        step.status = "running"
        start_time = time.time()

        # Substitute variables
        command = self.substitute_variables(step.command, variables)
        working_dir = self.substitute_variables(step.working_dir, variables) if step.working_dir else None

        # Merge environment
        env = os.environ.copy()
        for key, value in step.env.items():
            env[key] = self.substitute_variables(value, variables)

        if self.dry_run:
            step.status = "skipped (dry-run)"
            step.duration = 0
            print(f"  [DRY RUN] Would execute: {command}")
            return step

        try:
            # Handle glob patterns in command
            if '*' in command:
                # Use shell=True for glob expansion
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=step.timeout,
                    cwd=working_dir,
                    env=env
                )
            else:
                result = subprocess.run(
                    command.split(),
                    capture_output=True,
                    text=True,
                    timeout=step.timeout,
                    cwd=working_dir,
                    env=env
                )

            step.exit_code = result.returncode
            step.output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
            step.error = result.stderr[-1000:] if len(result.stderr) > 1000 else result.stderr
            step.status = "completed" if result.returncode == 0 else "failed"

        except subprocess.TimeoutExpired:
            step.status = "timeout"
            step.error = f"Step timed out after {step.timeout}s"
        except Exception as e:
            step.status = "error"
            step.error = str(e)

        step.duration = time.time() - start_time
        return step

    def run(self, plan: Plan) -> Dict[str, Any]:
        """Execute the entire plan."""
        print(f"\n{'='*70}")
        print(f"PLAN EXECUTOR: {plan.name}")
        print(f"{'='*70}")
        print(f"Description: {plan.description}")
        print(f"Steps: {len(plan.steps)}")
        print(f"Variables: {plan.variables}")
        if self.dry_run:
            print("[DRY RUN MODE]")
        print()

        start_time = datetime.now()
        variables = plan.variables.copy()
        completed = 0
        failed = 0

        for i, step in enumerate(plan.steps, 1):
            self.current_step = step

            # Check condition
            if step.condition and not self.check_condition(step.condition, variables):
                step.status = "skipped (condition)"
                print(f"[{i}/{len(plan.steps)}] {step.name}: SKIPPED (condition not met)")
                continue

            print(f"[{i}/{len(plan.steps)}] {step.name}: {step.description}")

            step = self.execute_step(step, variables)

            if step.status == "completed":
                completed += 1
                print(f"  ✓ Completed ({step.duration:.1f}s)")
                if step.output.strip():
                    # Show first few lines of output
                    lines = step.output.strip().split('\n')[:3]
                    for line in lines:
                        print(f"    {line[:80]}")
            elif step.status in ["failed", "error", "timeout"]:
                failed += 1
                print(f"  ✗ {step.status.upper()}: {step.error[:100]}")

                if not step.continue_on_error:
                    if step.on_failure == "abort" or not step.on_failure:
                        print(f"\n  ABORTING: Step failed and continue_on_error=False")
                        break
            else:
                print(f"  - {step.status}")

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Run completion/failure hooks
        all_passed = failed == 0
        if all_passed and plan.on_complete:
            print(f"\nRunning on_complete hook...")
            subprocess.run(plan.on_complete, shell=True, timeout=60)
        elif not all_passed and plan.on_failure:
            print(f"\nRunning on_failure hook...")
            subprocess.run(plan.on_failure, shell=True, timeout=60)

        # Summary
        print(f"\n{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        print(f"Duration: {duration:.1f}s")
        print(f"Completed: {completed}/{len(plan.steps)}")
        print(f"Failed: {failed}")
        print(f"Status: {'SUCCESS' if all_passed else 'FAILED'}")

        return {
            'plan': plan.name,
            'success': all_passed,
            'duration': duration,
            'completed': completed,
            'failed': failed,
            'total_steps': len(plan.steps),
            'steps': [
                {
                    'name': s.name,
                    'status': s.status,
                    'duration': s.duration,
                    'exit_code': s.exit_code
                }
                for s in plan.steps
            ]
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Plan Executor - Run multi-step pipelines')
    parser.add_argument('plan_file', nargs='?', help='Path to plan file (YAML or JSON)')
    parser.add_argument('--template', help='Use built-in template')
    parser.add_argument('--list-templates', action='store_true', help='List available templates')
    parser.add_argument('--dry-run', action='store_true', help='Show what would run without executing')
    parser.add_argument('--var', action='append', help='Set variable: --var key=value')
    parser.add_argument('--country', help='Shortcut for --var country=X')
    parser.add_argument('--json', action='store_true', help='Output JSON results')

    args = parser.parse_args()

    if args.list_templates:
        print("\nAvailable templates:")
        for name, template in TEMPLATES.items():
            print(f"\n  {name}:")
            print(f"    {template['description']}")
            print(f"    Variables: {template['variables']}")
            print(f"    Steps: {len(template['steps'])}")
        sys.exit(0)

    # Parse variables
    variables = {}
    if args.var:
        for v in args.var:
            key, value = v.split('=', 1)
            variables[key] = value
    if args.country:
        variables['country'] = args.country

    executor = PlanExecutor(dry_run=args.dry_run)

    # Load plan
    if args.template:
        plan = executor.load_template(args.template, variables)
    elif args.plan_file:
        plan = executor.load_plan(Path(args.plan_file))
        plan.variables.update(variables)
    else:
        print("Error: Provide a plan file or --template")
        sys.exit(1)

    # Execute
    results = executor.run(plan)

    if args.json:
        print(json.dumps(results, indent=2, default=str))

    sys.exit(0 if results['success'] else 1)


if __name__ == '__main__':
    main()
