#!/usr/bin/env python3
"""
Scraper Scheduler Skill - Smart scheduling for scrapers
Balances load, avoids conflicts, respects resource limits

Usage:
    python3 scraper_scheduler.py --generate        # Generate optimal schedule
    python3 scraper_scheduler.py --show            # Show current schedule
    python3 scraper_scheduler.py --validate        # Check for conflicts
    python3 scraper_scheduler.py --export cron     # Export as cron format

Examples:
    python3 scraper_scheduler.py --generate --max-concurrent 2
    python3 scraper_scheduler.py --export nodered
"""

import sys
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

SCRAPERS_BASE = Path('/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE')


@dataclass
class ScraperConfig:
    """Configuration for a scraper."""
    name: str
    path: Path
    estimated_duration_min: int = 30
    resource_type: str = "lightweight"  # lightweight, browser, heavy
    frequency: str = "daily"  # daily, weekly, monthly
    preferred_hour: Optional[int] = None
    priority: int = 5  # 1-10 (higher = more important)
    dependencies: List[str] = field(default_factory=list)
    enabled: bool = True
    notes: str = ""


@dataclass
class ScheduleSlot:
    """A scheduled time slot."""
    hour: int
    minute: int
    scrapers: List[str] = field(default_factory=list)
    total_duration: int = 0
    resource_types: List[str] = field(default_factory=list)


class ScraperScheduler:
    """Smart scheduler for scrapers."""

    # Known scraper configurations
    KNOWN_SCRAPERS = {
        'NORWAY': {'duration': 45, 'type': 'lightweight', 'priority': 8},
        'EURES': {'duration': 120, 'type': 'browser', 'priority': 9},
        'DENMARK': {'duration': 30, 'type': 'lightweight', 'priority': 7},
        'FINLAND': {'duration': 25, 'type': 'lightweight', 'priority': 7},
        'SWEDEN': {'duration': 35, 'type': 'lightweight', 'priority': 7},
        'ICELAND': {'duration': 20, 'type': 'lightweight', 'priority': 6},
        'IRELAND': {'duration': 40, 'type': 'lightweight', 'priority': 7},
        'UK': {'duration': 60, 'type': 'browser', 'priority': 8},
        'NETHERLANDS': {'duration': 30, 'type': 'lightweight', 'priority': 7},
        'FRANCE': {'duration': 45, 'type': 'lightweight', 'priority': 7},
        'POLAND': {'duration': 35, 'type': 'lightweight', 'priority': 7},
        'BULGARIA': {'duration': 25, 'type': 'lightweight', 'priority': 6},
        'MALTA': {'duration': 15, 'type': 'lightweight', 'priority': 5},
        'MOLDOVA': {'duration': 30, 'type': 'lightweight', 'priority': 6},
        'NORTH_MACEDONIA': {'duration': 20, 'type': 'lightweight', 'priority': 5},
        'ROMANIA': {'duration': 90, 'type': 'lightweight', 'priority': 8},
        'CAREWORKERS_EU': {'duration': 20, 'type': 'lightweight', 'priority': 6},
        'FACTORYJOBS_EU': {'duration': 20, 'type': 'lightweight', 'priority': 6},
    }

    def __init__(self, max_concurrent: int = 2, night_start: int = 0, night_end: int = 6):
        self.max_concurrent = max_concurrent
        self.night_start = night_start
        self.night_end = night_end
        self.scrapers: Dict[str, ScraperConfig] = {}
        self.schedule: Dict[int, ScheduleSlot] = {}  # hour -> slot

    def discover_scrapers(self) -> Dict[str, ScraperConfig]:
        """Discover all scrapers and their configurations."""
        scrapers = {}

        for item in SCRAPERS_BASE.iterdir():
            if not item.is_dir() or item.name.startswith('.'):
                continue

            # Check for scraper files
            py_files = list(item.glob('*scraper*.py')) + list(item.glob('main.py'))
            if not py_files:
                continue

            name = item.name
            known = self.KNOWN_SCRAPERS.get(name, {})

            config = ScraperConfig(
                name=name,
                path=py_files[0],
                estimated_duration_min=known.get('duration', 30),
                resource_type=known.get('type', 'lightweight'),
                priority=known.get('priority', 5),
                enabled=True
            )

            # Try to read CLAUDE.md for more info
            claude_md = item / 'CLAUDE.md'
            if claude_md.exists():
                content = claude_md.read_text()
                # Check if disabled
                if 'disabled' in content.lower() or 'expires' in content.lower():
                    # Check expiry date
                    import re
                    expiry_match = re.search(r'expires?:?\s*(\w+\s+\d{4})', content, re.IGNORECASE)
                    if expiry_match:
                        config.notes = f"Expires: {expiry_match.group(1)}"

            scrapers[name] = config

        self.scrapers = scrapers
        return scrapers

    def generate_schedule(self) -> Dict[int, ScheduleSlot]:
        """Generate optimal schedule."""
        if not self.scrapers:
            self.discover_scrapers()

        # Initialize schedule slots for night hours
        for hour in range(24):
            self.schedule[hour] = ScheduleSlot(hour=hour, minute=0)

        # Sort scrapers by priority (high first), then duration (long first)
        sorted_scrapers = sorted(
            [(n, c) for n, c in self.scrapers.items() if c.enabled],
            key=lambda x: (-x[1].priority, -x[1].estimated_duration_min)
        )

        # Group by resource type
        browser_scrapers = [(n, c) for n, c in sorted_scrapers if c.resource_type == 'browser']
        lightweight_scrapers = [(n, c) for n, c in sorted_scrapers if c.resource_type == 'lightweight']

        # Schedule browser scrapers first (one at a time, during night)
        current_hour = self.night_start
        for name, config in browser_scrapers:
            slot = self.schedule[current_hour]
            slot.scrapers.append(name)
            slot.total_duration += config.estimated_duration_min
            slot.resource_types.append('browser')

            # Move to next hour based on duration
            current_hour = (current_hour + (config.estimated_duration_min // 60) + 1) % 24
            if current_hour >= self.night_end and current_hour < 20:
                current_hour = 20  # Move to evening

        # Schedule lightweight scrapers (can run in parallel)
        current_hour = max(current_hour, 1)  # Start at 01:00 if browser scrapers done
        concurrent_count = 0

        for name, config in lightweight_scrapers:
            # Find a slot that isn't too full
            attempts = 0
            while attempts < 24:
                slot = self.schedule[current_hour]

                # Check if slot is available
                browser_running = 'browser' in slot.resource_types
                too_many = len(slot.scrapers) >= self.max_concurrent
                too_long = slot.total_duration + config.estimated_duration_min > 120

                if not browser_running and not too_many and not too_long:
                    slot.scrapers.append(name)
                    slot.total_duration += config.estimated_duration_min
                    slot.resource_types.append(config.resource_type)
                    break

                current_hour = (current_hour + 1) % 24
                attempts += 1

                # Prefer night hours
                if current_hour == self.night_end:
                    current_hour = 20  # Jump to evening

        return self.schedule

    def validate_schedule(self) -> List[str]:
        """Validate schedule for conflicts."""
        issues = []

        for hour, slot in self.schedule.items():
            # Check for browser conflicts
            browser_count = slot.resource_types.count('browser')
            if browser_count > 1:
                issues.append(f"Hour {hour:02d}: Multiple browser scrapers ({browser_count})")

            # Check for overload
            if len(slot.scrapers) > self.max_concurrent + 1:
                issues.append(f"Hour {hour:02d}: Too many scrapers ({len(slot.scrapers)})")

            # Check for very long slots
            if slot.total_duration > 180:
                issues.append(f"Hour {hour:02d}: Total duration too long ({slot.total_duration} min)")

        return issues

    def export_cron(self) -> str:
        """Export schedule as cron format."""
        lines = ["# Scraper Schedule - Generated by scraper_scheduler.py"]
        lines.append(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append("")

        for hour in range(24):
            slot = self.schedule.get(hour)
            if not slot or not slot.scrapers:
                continue

            minute = 0
            for scraper_name in slot.scrapers:
                config = self.scrapers.get(scraper_name)
                if not config:
                    continue

                # Stagger by 5-10 minutes
                cron_line = f"{minute} {hour} * * * cd {config.path.parent} && /opt/ACTIVE/INFRA/venv/bin/python3 {config.path.name}"
                lines.append(f"# {scraper_name} (~{config.estimated_duration_min}min)")
                lines.append(cron_line)
                lines.append("")

                minute += 10
                if minute >= 60:
                    break

        return '\n'.join(lines)

    def export_nodered(self) -> Dict:
        """Export schedule for Node-RED inject nodes."""
        nodes = []

        for hour in range(24):
            slot = self.schedule.get(hour)
            if not slot or not slot.scrapers:
                continue

            for i, scraper_name in enumerate(slot.scrapers):
                config = self.scrapers.get(scraper_name)
                if not config:
                    continue

                minute = i * 10
                node = {
                    "name": f"{scraper_name} Scraper",
                    "cron": f"{minute} {hour} * * *",
                    "command": f"cd {config.path.parent} && /opt/ACTIVE/INFRA/venv/bin/python3 {config.path.name}",
                    "duration": config.estimated_duration_min,
                    "type": config.resource_type
                }
                nodes.append(node)

        return {"scrapers": nodes}

    def show_schedule(self) -> str:
        """Show schedule in readable format."""
        lines = []
        lines.append("=" * 70)
        lines.append("SCRAPER SCHEDULE")
        lines.append(f"Max concurrent: {self.max_concurrent}")
        lines.append("=" * 70)

        for hour in range(24):
            slot = self.schedule.get(hour)
            if not slot or not slot.scrapers:
                continue

            hour_str = f"{hour:02d}:00"
            scrapers_str = ", ".join(slot.scrapers)
            duration_str = f"~{slot.total_duration}min"
            types = list(set(slot.resource_types))

            lines.append(f"\n{hour_str} [{', '.join(types)}] {duration_str}")
            for scraper in slot.scrapers:
                config = self.scrapers.get(scraper)
                if config:
                    lines.append(f"  - {scraper} (~{config.estimated_duration_min}min, P{config.priority})")

        # Summary
        lines.append(f"\n{'=' * 70}")
        lines.append("SUMMARY")
        total_scrapers = sum(len(s.scrapers) for s in self.schedule.values())
        total_duration = sum(s.total_duration for s in self.schedule.values())
        lines.append(f"Total scrapers scheduled: {total_scrapers}")
        lines.append(f"Total estimated runtime: {total_duration} min ({total_duration/60:.1f} hours)")
        lines.append("=" * 70)

        return '\n'.join(lines)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Scraper Scheduler')
    parser.add_argument('--generate', action='store_true', help='Generate optimal schedule')
    parser.add_argument('--show', action='store_true', help='Show schedule')
    parser.add_argument('--validate', action='store_true', help='Validate schedule')
    parser.add_argument('--export', choices=['cron', 'nodered', 'json'], help='Export format')
    parser.add_argument('--max-concurrent', type=int, default=2, help='Max concurrent scrapers')
    parser.add_argument('--list', action='store_true', help='List discovered scrapers')

    args = parser.parse_args()

    scheduler = ScraperScheduler(max_concurrent=args.max_concurrent)

    if args.list:
        scrapers = scheduler.discover_scrapers()
        print(f"Discovered {len(scrapers)} scrapers:\n")
        for name, config in sorted(scrapers.items()):
            print(f"  {name}: ~{config.estimated_duration_min}min, {config.resource_type}, P{config.priority}")
        sys.exit(0)

    if args.generate or args.show or args.validate or args.export:
        scheduler.discover_scrapers()
        scheduler.generate_schedule()

    if args.validate:
        issues = scheduler.validate_schedule()
        if issues:
            print("Schedule issues found:")
            for issue in issues:
                print(f"  - {issue}")
            sys.exit(1)
        else:
            print("Schedule is valid!")
            sys.exit(0)

    if args.export == 'cron':
        print(scheduler.export_cron())
    elif args.export == 'nodered':
        print(json.dumps(scheduler.export_nodered(), indent=2))
    elif args.export == 'json':
        print(json.dumps({
            'schedule': {
                str(h): {
                    'scrapers': s.scrapers,
                    'duration': s.total_duration,
                    'types': s.resource_types
                }
                for h, s in scheduler.schedule.items() if s.scrapers
            }
        }, indent=2))
    elif args.show or args.generate:
        print(scheduler.show_schedule())
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
