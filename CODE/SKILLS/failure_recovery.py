#!/usr/bin/env python3
"""
Failure Recovery Skill - Auto-recover from common scraper failures
Retry, switch fallback, diagnose, notify

Usage:
    python3 failure_recovery.py <scraper_path>           # Run with recovery
    python3 failure_recovery.py --diagnose <log_path>    # Diagnose failure
    python3 failure_recovery.py --retry <scraper_path>   # Retry failed scraper

Examples:
    python3 failure_recovery.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/NORWAY/arbeidsplassen_scraper.py
    python3 failure_recovery.py --diagnose /var/log/scraper.log
"""

import sys
import os
import subprocess
import time
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')


class FailureType(Enum):
    """Types of failures."""
    NETWORK = "network"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"
    RATE_LIMIT = "rate_limit"
    AUTH = "authentication"
    PARSE = "parse_error"
    RESOURCE = "resource_exhausted"
    DEPENDENCY = "dependency"
    UNKNOWN = "unknown"


@dataclass
class RecoveryAction:
    """A recovery action to try."""
    name: str
    description: str
    action: str  # command or strategy
    wait_seconds: int = 0
    max_attempts: int = 1


class FailureRecovery:
    """Auto-recovery for scraper failures."""

    # Recovery strategies by failure type
    RECOVERY_STRATEGIES = {
        FailureType.NETWORK: [
            RecoveryAction("wait_retry", "Wait and retry", "retry", wait_seconds=60, max_attempts=3),
            RecoveryAction("dns_flush", "Flush DNS cache", "sudo systemd-resolve --flush-caches", wait_seconds=5),
        ],
        FailureType.TIMEOUT: [
            RecoveryAction("extend_timeout", "Retry with longer timeout", "retry_extended", wait_seconds=30, max_attempts=2),
            RecoveryAction("reduce_workers", "Retry with fewer workers", "retry_reduced"),
        ],
        FailureType.BLOCKED: [
            RecoveryAction("wait_long", "Wait longer before retry", "retry", wait_seconds=300, max_attempts=2),
            RecoveryAction("change_ip", "Change IP (if available)", "change_ip"),
            RecoveryAction("use_proxy", "Try with proxy", "use_proxy"),
        ],
        FailureType.RATE_LIMIT: [
            RecoveryAction("backoff", "Exponential backoff", "retry", wait_seconds=120, max_attempts=3),
        ],
        FailureType.RESOURCE: [
            RecoveryAction("gc_cleanup", "Run garbage collection", "gc", wait_seconds=10),
            RecoveryAction("kill_browsers", "Kill orphan browsers", "pkill -f chromium; pkill -f firefox", wait_seconds=5),
            RecoveryAction("reduce_memory", "Retry with reduced memory", "retry_reduced"),
        ],
        FailureType.PARSE: [
            RecoveryAction("report", "Report parse error (no auto-fix)", "notify"),
        ],
        FailureType.DEPENDENCY: [
            RecoveryAction("install_deps", "Try installing dependencies", "pip_install"),
        ],
    }

    # Error patterns for diagnosis
    ERROR_PATTERNS = [
        (r'connection.*refused|ECONNREFUSED', FailureType.NETWORK),
        (r'timeout|timed out|TimeoutError', FailureType.TIMEOUT),
        (r'403|forbidden|blocked|captcha', FailureType.BLOCKED),
        (r'429|too many requests|rate limit', FailureType.RATE_LIMIT),
        (r'401|unauthorized|auth', FailureType.AUTH),
        (r'JSONDecodeError|ParseError|invalid syntax', FailureType.PARSE),
        (r'MemoryError|out of memory|killed', FailureType.RESOURCE),
        (r'ModuleNotFoundError|ImportError', FailureType.DEPENDENCY),
    ]

    def __init__(self, notify_telegram: bool = True):
        self.notify_telegram = notify_telegram
        self.attempts = []
        self.recovery_log = []

    def diagnose(self, error_output: str) -> Tuple[FailureType, str]:
        """Diagnose failure type from error output."""
        for pattern, failure_type in self.ERROR_PATTERNS:
            if re.search(pattern, error_output, re.IGNORECASE):
                match = re.search(pattern, error_output, re.IGNORECASE)
                return failure_type, match.group(0) if match else ""

        return FailureType.UNKNOWN, "Unknown error"

    def run_with_recovery(self, scraper_path: Path, max_attempts: int = 3) -> Dict[str, Any]:
        """Run scraper with automatic recovery."""
        result = {
            'scraper': str(scraper_path),
            'started': datetime.now().isoformat(),
            'attempts': [],
            'success': False,
            'final_error': None
        }

        print(f"\n{'='*70}")
        print(f"RUNNING WITH RECOVERY: {scraper_path.name}")
        print(f"{'='*70}")

        for attempt in range(1, max_attempts + 1):
            print(f"\n[Attempt {attempt}/{max_attempts}]")

            attempt_result = self._run_scraper(scraper_path)
            result['attempts'].append(attempt_result)

            if attempt_result['success']:
                result['success'] = True
                print(f"✓ Success on attempt {attempt}")
                break

            # Diagnose failure
            failure_type, error_detail = self.diagnose(attempt_result['error'])
            print(f"  Failure type: {failure_type.value}")
            print(f"  Detail: {error_detail[:100]}")

            # Try recovery strategies
            strategies = self.RECOVERY_STRATEGIES.get(failure_type, [])
            recovered = False

            for strategy in strategies:
                print(f"  Trying recovery: {strategy.name}")
                self.recovery_log.append({
                    'time': datetime.now().isoformat(),
                    'strategy': strategy.name,
                    'failure_type': failure_type.value
                })

                if strategy.action == "retry":
                    if strategy.wait_seconds > 0:
                        print(f"    Waiting {strategy.wait_seconds}s...")
                        time.sleep(strategy.wait_seconds)
                    recovered = True
                    break

                elif strategy.action.startswith("pkill") or strategy.action.startswith("sudo"):
                    try:
                        subprocess.run(strategy.action, shell=True, timeout=30)
                        time.sleep(strategy.wait_seconds)
                        recovered = True
                        break
                    except Exception as e:
                        print(f"    Recovery action failed: {e}")

                elif strategy.action == "gc":
                    import gc
                    gc.collect()
                    time.sleep(strategy.wait_seconds)
                    recovered = True
                    break

                elif strategy.action == "pip_install":
                    # Try to install missing module
                    module_match = re.search(r"No module named '(\w+)'", attempt_result['error'])
                    if module_match:
                        module = module_match.group(1)
                        print(f"    Installing {module}...")
                        try:
                            subprocess.run(['/opt/ACTIVE/INFRA/venv/bin/pip', 'install', module], timeout=120)
                            recovered = True
                            break
                        except Exception:
                            pass

                elif strategy.action == "notify":
                    # Just notify, no recovery
                    result['final_error'] = error_detail
                    break

            if not recovered:
                result['final_error'] = error_detail
                if attempt == max_attempts:
                    print(f"\n✗ All recovery attempts exhausted")

        result['ended'] = datetime.now().isoformat()
        result['recovery_log'] = self.recovery_log

        # Send notification if failed
        if not result['success'] and self.notify_telegram:
            self._notify_failure(scraper_path, result)

        return result

    def _run_scraper(self, scraper_path: Path, timeout: int = 1800) -> Dict[str, Any]:
        """Run scraper and capture result."""
        result = {
            'started': datetime.now().isoformat(),
            'success': False,
            'exit_code': None,
            'output': '',
            'error': '',
            'duration': 0
        }

        start = time.time()
        try:
            proc = subprocess.run(
                ['/opt/ACTIVE/INFRA/venv/bin/python3', str(scraper_path)],
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(scraper_path.parent)
            )
            result['exit_code'] = proc.returncode
            result['output'] = proc.stdout[-5000:] if len(proc.stdout) > 5000 else proc.stdout
            result['error'] = proc.stderr[-5000:] if len(proc.stderr) > 5000 else proc.stderr
            result['success'] = proc.returncode == 0

        except subprocess.TimeoutExpired:
            result['error'] = f"Timeout after {timeout} seconds"
        except Exception as e:
            result['error'] = str(e)

        result['duration'] = time.time() - start
        result['ended'] = datetime.now().isoformat()

        return result

    def _notify_failure(self, scraper_path: Path, result: Dict):
        """Send failure notification via Telegram."""
        try:
            # Import telegram notifier if available
            from telegram_notifier import send_telegram_message
            msg = f"❌ Scraper failed: {scraper_path.name}\n"
            msg += f"Attempts: {len(result['attempts'])}\n"
            msg += f"Error: {result.get('final_error', 'Unknown')[:200]}"
            send_telegram_message(msg)
        except ImportError:
            print("  (Telegram notification not available)")
        except Exception as e:
            print(f"  (Notification failed: {e})")

    def diagnose_log(self, log_path: Path) -> Dict[str, Any]:
        """Diagnose a log file for failures."""
        try:
            content = log_path.read_text(errors='replace')
        except Exception as e:
            return {'error': f'Cannot read log: {e}'}

        failures = []
        for pattern, failure_type in self.ERROR_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                failures.append({
                    'type': failure_type.value,
                    'count': len(matches),
                    'examples': matches[:3]
                })

        # Suggest recovery
        suggestions = []
        for failure in failures:
            ft = FailureType(failure['type'])
            strategies = self.RECOVERY_STRATEGIES.get(ft, [])
            if strategies:
                suggestions.append({
                    'failure': failure['type'],
                    'recovery': strategies[0].name,
                    'description': strategies[0].description
                })

        return {
            'log_file': str(log_path),
            'failures': failures,
            'suggestions': suggestions
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Failure Recovery - Auto-recover from scraper failures')
    parser.add_argument('path', nargs='?', help='Scraper path to run with recovery')
    parser.add_argument('--diagnose', help='Diagnose a log file')
    parser.add_argument('--retry', help='Retry a failed scraper')
    parser.add_argument('--max-attempts', type=int, default=3, help='Max recovery attempts')
    parser.add_argument('--no-notify', action='store_true', help='Disable Telegram notifications')
    parser.add_argument('--json', action='store_true', help='Output JSON')

    args = parser.parse_args()

    recovery = FailureRecovery(notify_telegram=not args.no_notify)

    if args.diagnose:
        result = recovery.diagnose_log(Path(args.diagnose))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\nDiagnosis for: {args.diagnose}")
            print("-" * 50)
            for f in result.get('failures', []):
                print(f"  {f['type']}: {f['count']} occurrences")
            print("\nSuggested recovery:")
            for s in result.get('suggestions', []):
                print(f"  - {s['failure']}: {s['description']}")

    elif args.path or args.retry:
        scraper_path = Path(args.retry or args.path)
        if not scraper_path.exists():
            print(f"Error: Scraper not found: {scraper_path}")
            sys.exit(1)

        result = recovery.run_with_recovery(scraper_path, max_attempts=args.max_attempts)

        if args.json:
            print(json.dumps(result, indent=2, default=str))

        sys.exit(0 if result['success'] else 1)

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
