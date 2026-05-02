#!/usr/bin/env python3
"""
Health Monitor Skill - Monitor scraper health across all countries
Tracks success rates, run times, failures, and trends

Usage:
    python3 health_monitor.py                    # Full health report
    python3 health_monitor.py --country NORWAY   # Single country
    python3 health_monitor.py --days 7           # Last 7 days
    python3 health_monitor.py --alert            # Only show problems

Examples:
    python3 health_monitor.py --days 30 --json
    python3 health_monitor.py --country SPAIN --verbose
"""

import sys
import os
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

SCRAPERS_BASE = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE')
LOGS_BASE = Path('/mnt/hdd/SCRAPER_DATA/logs')
DATA_BASE = Path('/mnt/hdd/SCRAPER_DATA/csv')


@dataclass
class ScraperHealth:
    """Health metrics for a single scraper."""
    country: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    last_run: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    avg_duration_seconds: float = 0
    last_output_rows: int = 0
    last_output_size_kb: float = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return (self.successful_runs / self.total_runs) * 100

    @property
    def health_status(self) -> str:
        if self.total_runs == 0:
            return "unknown"
        if self.success_rate >= 90:
            return "healthy"
        elif self.success_rate >= 70:
            return "degraded"
        else:
            return "unhealthy"


class HealthMonitor:
    """Monitor health of all scrapers."""

    def __init__(self, days: int = 7):
        self.days = days
        self.cutoff = datetime.now() - timedelta(days=days)
        self.health_data: Dict[str, ScraperHealth] = {}

    def discover_countries(self) -> List[str]:
        """Find all scraper countries."""
        countries = []
        if SCRAPERS_BASE.exists():
            for item in SCRAPERS_BASE.iterdir():
                if item.is_dir() and not item.name.startswith('.'):
                    # Check if it has Python files
                    if list(item.glob('*.py')):
                        countries.append(item.name)
        return sorted(countries)

    def parse_log_file(self, log_path: Path) -> Dict[str, Any]:
        """Parse a log file for metrics."""
        metrics = {
            'success': False,
            'duration': 0,
            'errors': [],
            'warnings': [],
            'rows': 0,
            'timestamp': None
        }

        try:
            # Get timestamp from filename or file mtime
            mtime = datetime.fromtimestamp(log_path.stat().st_mtime)
            metrics['timestamp'] = mtime

            content = log_path.read_text(errors='replace')

            # Check for success indicators
            success_patterns = [
                r'completed successfully',
                r'saved \d+ (jobs|records|rows)',
                r'finished.*\d+ total',
                r'export.*complete',
                r'scraping complete'
            ]
            for pattern in success_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    metrics['success'] = True
                    break

            # Check for failure indicators
            failure_patterns = [
                r'(error|exception|failed|traceback)',
                r'exit code [1-9]',
                r'critical:',
                r'fatal:'
            ]
            for pattern in failure_patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    metrics['success'] = False
                    # Extract error message
                    error_match = re.search(r'(Error|Exception):?\s*(.{0,100})', content, re.IGNORECASE)
                    if error_match:
                        metrics['errors'].append(error_match.group(0)[:100])
                    break

            # Extract duration
            duration_match = re.search(r'duration[:\s]+(\d+(?:\.\d+)?)\s*(s|sec|seconds|min|minutes)?', content, re.IGNORECASE)
            if duration_match:
                duration = float(duration_match.group(1))
                unit = duration_match.group(2) or 's'
                if 'min' in unit.lower():
                    duration *= 60
                metrics['duration'] = duration

            # Extract row count
            rows_match = re.search(r'(\d+)\s*(jobs|records|rows|entries)', content, re.IGNORECASE)
            if rows_match:
                metrics['rows'] = int(rows_match.group(1))

            # Extract warnings
            warning_matches = re.findall(r'warning:?\s*(.{0,80})', content, re.IGNORECASE)
            metrics['warnings'] = warning_matches[:5]

        except Exception as e:
            metrics['errors'].append(f"Log parse error: {e}")

        return metrics

    def analyze_country(self, country: str) -> ScraperHealth:
        """Analyze health for a single country."""
        health = ScraperHealth(country=country)

        # Check multiple log locations
        log_dirs = [
            LOGS_BASE / country,
            SCRAPERS_BASE / country / 'logs',
            SCRAPERS_BASE / country / 'results',
            SCRAPERS_BASE / country / 'DATA',
        ]

        log_files = []
        for log_dir in log_dirs:
            if log_dir.exists():
                log_files.extend(log_dir.glob('*.log'))
                log_files.extend(log_dir.glob('*scraper*.log'))

        # Filter by date and parse
        durations = []
        for log_file in log_files:
            try:
                mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
                if mtime < self.cutoff:
                    continue

                metrics = self.parse_log_file(log_file)
                health.total_runs += 1

                if metrics['success']:
                    health.successful_runs += 1
                    if not health.last_success or mtime > health.last_success:
                        health.last_success = mtime
                else:
                    health.failed_runs += 1
                    if not health.last_failure or mtime > health.last_failure:
                        health.last_failure = mtime
                    health.errors.extend(metrics['errors'][:3])

                if not health.last_run or mtime > health.last_run:
                    health.last_run = mtime
                    health.last_output_rows = metrics['rows']

                if metrics['duration'] > 0:
                    durations.append(metrics['duration'])

                health.warnings.extend(metrics['warnings'][:2])

            except Exception:
                continue

        if durations:
            health.avg_duration_seconds = sum(durations) / len(durations)

        # Check latest output file
        output_dirs = [
            DATA_BASE / country,
            SCRAPERS_BASE / country / 'OUTPUT',
            SCRAPERS_BASE / country / 'results',
        ]
        for output_dir in output_dirs:
            if output_dir.exists():
                csv_files = list(output_dir.glob('*MASTER*.csv'))
                if csv_files:
                    latest = max(csv_files, key=lambda p: p.stat().st_mtime)
                    health.last_output_size_kb = latest.stat().st_size / 1024
                    break

        # Add warnings for concerning patterns
        if health.last_run:
            days_since_run = (datetime.now() - health.last_run).days
            if days_since_run > 3:
                health.warnings.append(f"No runs in {days_since_run} days")

        if health.success_rate < 50 and health.total_runs > 2:
            health.warnings.append(f"Low success rate: {health.success_rate:.0f}%")

        return health

    def analyze_all(self, countries: List[str] = None) -> Dict[str, ScraperHealth]:
        """Analyze health for all countries."""
        if countries is None:
            countries = self.discover_countries()

        for country in countries:
            self.health_data[country] = self.analyze_country(country)

        return self.health_data

    def generate_report(self, alert_only: bool = False) -> str:
        """Generate health report."""
        lines = []
        lines.append("=" * 70)
        lines.append(f"SCRAPER HEALTH REPORT - Last {self.days} days")
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("=" * 70)

        # Summary
        total = len(self.health_data)
        healthy = sum(1 for h in self.health_data.values() if h.health_status == "healthy")
        degraded = sum(1 for h in self.health_data.values() if h.health_status == "degraded")
        unhealthy = sum(1 for h in self.health_data.values() if h.health_status == "unhealthy")
        unknown = sum(1 for h in self.health_data.values() if h.health_status == "unknown")

        lines.append(f"\nSUMMARY: {total} scrapers")
        lines.append(f"  Healthy:   {healthy}")
        lines.append(f"  Degraded:  {degraded}")
        lines.append(f"  Unhealthy: {unhealthy}")
        lines.append(f"  Unknown:   {unknown}")

        # Details
        lines.append(f"\n{'-' * 70}")
        lines.append("DETAILS BY COUNTRY")
        lines.append(f"{'-' * 70}")

        # Sort by health status (worst first)
        status_order = {'unhealthy': 0, 'degraded': 1, 'unknown': 2, 'healthy': 3}
        sorted_health = sorted(
            self.health_data.items(),
            key=lambda x: (status_order.get(x[1].health_status, 4), x[0])
        )

        for country, health in sorted_health:
            if alert_only and health.health_status == "healthy":
                continue

            status_icon = {
                'healthy': '✓',
                'degraded': '⚠',
                'unhealthy': '✗',
                'unknown': '?'
            }.get(health.health_status, '?')

            lines.append(f"\n{status_icon} {country}")
            lines.append(f"  Status: {health.health_status.upper()}")
            lines.append(f"  Runs: {health.total_runs} ({health.successful_runs} ok, {health.failed_runs} failed)")
            lines.append(f"  Success rate: {health.success_rate:.0f}%")

            if health.last_run:
                lines.append(f"  Last run: {health.last_run.strftime('%Y-%m-%d %H:%M')}")
            if health.avg_duration_seconds > 0:
                lines.append(f"  Avg duration: {health.avg_duration_seconds:.0f}s")
            if health.last_output_rows > 0:
                lines.append(f"  Last output: {health.last_output_rows} rows")

            if health.errors:
                lines.append(f"  Errors:")
                for err in health.errors[:3]:
                    lines.append(f"    - {err[:60]}")

            if health.warnings:
                lines.append(f"  Warnings:")
                for warn in health.warnings[:3]:
                    lines.append(f"    - {warn[:60]}")

        lines.append(f"\n{'=' * 70}")

        return '\n'.join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            'generated': datetime.now().isoformat(),
            'days': self.days,
            'summary': {
                'total': len(self.health_data),
                'healthy': sum(1 for h in self.health_data.values() if h.health_status == "healthy"),
                'degraded': sum(1 for h in self.health_data.values() if h.health_status == "degraded"),
                'unhealthy': sum(1 for h in self.health_data.values() if h.health_status == "unhealthy"),
                'unknown': sum(1 for h in self.health_data.values() if h.health_status == "unknown"),
            },
            'countries': {
                country: {
                    'status': h.health_status,
                    'total_runs': h.total_runs,
                    'successful_runs': h.successful_runs,
                    'failed_runs': h.failed_runs,
                    'success_rate': h.success_rate,
                    'last_run': h.last_run.isoformat() if h.last_run else None,
                    'avg_duration_seconds': h.avg_duration_seconds,
                    'last_output_rows': h.last_output_rows,
                    'errors': h.errors[:5],
                    'warnings': h.warnings[:5]
                }
                for country, h in self.health_data.items()
            }
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Health Monitor - Track scraper health')
    parser.add_argument('--country', help='Check specific country only')
    parser.add_argument('--days', type=int, default=7, help='Days to analyze (default: 7)')
    parser.add_argument('--alert', action='store_true', help='Only show problems')
    parser.add_argument('--json', action='store_true', help='Output JSON')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')

    args = parser.parse_args()

    monitor = HealthMonitor(days=args.days)

    if args.country:
        monitor.analyze_all([args.country.upper()])
    else:
        monitor.analyze_all()

    if args.json:
        print(json.dumps(monitor.to_dict(), indent=2))
    else:
        print(monitor.generate_report(alert_only=args.alert))


if __name__ == '__main__':
    main()
