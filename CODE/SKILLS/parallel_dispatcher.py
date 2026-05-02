#!/usr/bin/env python3
"""
Parallel Dispatcher Skill - Run multiple scrapers with resource management
Based on superpowers dispatching-parallel-agents pattern

Respects constraints:
- 1 browser at a time (Playwright/Selenium scrapers)
- Memory limits (Pi has limited RAM)
- CPU throttling via power_manager

Usage:
    python3 parallel_dispatcher.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ --max-parallel 3
    python3 parallel_dispatcher.py --list  # Show queue
    python3 parallel_dispatcher.py --countries SPAIN,FRANCE,POLAND

Examples:
    # Run all scrapers with smart scheduling
    python3 parallel_dispatcher.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ --max-parallel 4

    # Run specific countries
    python3 parallel_dispatcher.py --countries SPAIN,NORWAY,DENMARK

    # Dry run - show what would execute
    python3 parallel_dispatcher.py /opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/ --dry-run
"""

import sys
import os
import json
import subprocess
import time
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import psutil

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')


class ScraperType(Enum):
    """Scraper resource requirements."""
    LIGHTWEIGHT = "lightweight"  # httpx/requests only
    BROWSER = "browser"          # Playwright/Selenium
    UNKNOWN = "unknown"


@dataclass
class ScraperJob:
    """A scraper job in the queue."""
    path: Path
    country: str
    scraper_type: ScraperType = ScraperType.UNKNOWN
    priority: int = 5  # 1-10, lower = higher priority
    status: str = "pending"
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    exit_code: Optional[int] = None
    output: str = ""
    error: str = ""


class ResourceManager:
    """Manage system resources for parallel execution."""

    def __init__(self, max_memory_percent: float = 80.0):
        self.max_memory = max_memory_percent
        self.browser_lock = threading.Lock()
        self.browser_in_use = False

    def can_start_job(self, job: ScraperJob) -> bool:
        """Check if we have resources to start this job."""
        # Check memory
        mem = psutil.virtual_memory()
        if mem.percent > self.max_memory:
            return False

        # Check browser availability
        if job.scraper_type == ScraperType.BROWSER:
            if self.browser_in_use:
                return False

        return True

    def acquire_browser(self) -> bool:
        """Try to acquire browser lock."""
        with self.browser_lock:
            if not self.browser_in_use:
                self.browser_in_use = True
                return True
            return False

    def release_browser(self):
        """Release browser lock."""
        with self.browser_lock:
            self.browser_in_use = False

    def get_status(self) -> Dict[str, Any]:
        """Get current resource status."""
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=0.1)
        return {
            'memory_percent': mem.percent,
            'memory_available_mb': mem.available // (1024 * 1024),
            'cpu_percent': cpu,
            'browser_available': not self.browser_in_use
        }


class ParallelDispatcher:
    """Dispatch and manage parallel scraper execution."""

    def __init__(self, max_parallel: int = 3, max_memory: float = 80.0):
        self.max_parallel = max_parallel
        self.resources = ResourceManager(max_memory)
        self.job_queue: queue.PriorityQueue = queue.PriorityQueue()
        self.active_jobs: Dict[str, ScraperJob] = {}
        self.completed_jobs: List[ScraperJob] = []
        self.lock = threading.Lock()

    def detect_scraper_type(self, path: Path) -> ScraperType:
        """Detect if scraper uses browser or is lightweight."""
        try:
            content = path.read_text()
            browser_patterns = [
                'playwright',
                'selenium',
                'webdriver',
                'browser',
                'chromium',
                'firefox',
                'webkit'
            ]
            for pattern in browser_patterns:
                if pattern in content.lower():
                    return ScraperType.BROWSER
            return ScraperType.LIGHTWEIGHT
        except Exception:
            return ScraperType.UNKNOWN

    def discover_scrapers(self, path: Path) -> List[ScraperJob]:
        """Discover all scrapers in path."""
        jobs = []

        if path.is_file():
            country = path.parent.name
            job = ScraperJob(
                path=path,
                country=country,
                scraper_type=self.detect_scraper_type(path)
            )
            jobs.append(job)
        else:
            # Look for scraper patterns in subdirectories
            for country_dir in sorted(path.iterdir()):
                if not country_dir.is_dir():
                    continue
                if country_dir.name.startswith('.'):
                    continue

                # Find main scraper file
                scraper_files = list(country_dir.glob('*scraper*.py'))
                if not scraper_files:
                    scraper_files = list(country_dir.glob('main.py'))
                if not scraper_files:
                    scraper_files = list(country_dir.glob('scrape*.py'))

                for scraper in scraper_files:
                    job = ScraperJob(
                        path=scraper,
                        country=country_dir.name,
                        scraper_type=self.detect_scraper_type(scraper)
                    )
                    jobs.append(job)

        return jobs

    def prioritize_jobs(self, jobs: List[ScraperJob]) -> List[ScraperJob]:
        """Assign priorities to jobs."""
        # Lightweight scrapers get higher priority (run first)
        # Browser scrapers run one at a time anyway
        for job in jobs:
            if job.scraper_type == ScraperType.LIGHTWEIGHT:
                job.priority = 3
            elif job.scraper_type == ScraperType.BROWSER:
                job.priority = 7
            else:
                job.priority = 5
        return sorted(jobs, key=lambda j: j.priority)

    def run_job(self, job: ScraperJob) -> ScraperJob:
        """Run a single scraper job."""
        job.status = "running"
        job.start_time = datetime.now()

        # Acquire browser if needed
        if job.scraper_type == ScraperType.BROWSER:
            self.resources.acquire_browser()

        try:
            # Use cpu_protected_run for resource management
            cmd = [
                '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/cpu_protected_run.sh',
                '--',
                '/opt/ACTIVE/INFRA/venv/bin/python3',
                str(job.path)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=1800,  # 30 min timeout
                cwd=str(job.path.parent)
            )

            job.exit_code = result.returncode
            job.output = result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout
            job.error = result.stderr[-2000:] if len(result.stderr) > 2000 else result.stderr
            job.status = "completed" if result.returncode == 0 else "failed"

        except subprocess.TimeoutExpired:
            job.status = "timeout"
            job.error = "Job timed out after 30 minutes"
        except Exception as e:
            job.status = "error"
            job.error = str(e)
        finally:
            job.end_time = datetime.now()
            if job.scraper_type == ScraperType.BROWSER:
                self.resources.release_browser()

        return job

    def worker(self):
        """Worker thread for processing jobs."""
        while True:
            try:
                priority, job = self.job_queue.get(timeout=1)
            except queue.Empty:
                # Check if we should exit
                with self.lock:
                    if self.job_queue.empty() and not self.active_jobs:
                        break
                continue

            # Wait for resources
            while not self.resources.can_start_job(job):
                time.sleep(2)

            # Run the job
            with self.lock:
                self.active_jobs[job.country] = job

            print(f"  [{datetime.now().strftime('%H:%M:%S')}] Starting: {job.country} ({job.scraper_type.value})")

            job = self.run_job(job)

            with self.lock:
                del self.active_jobs[job.country]
                self.completed_jobs.append(job)

            duration = (job.end_time - job.start_time).total_seconds()
            status_icon = "✓" if job.status == "completed" else "✗"
            print(f"  [{datetime.now().strftime('%H:%M:%S')}] {status_icon} Finished: {job.country} ({duration:.0f}s)")

            self.job_queue.task_done()

    def run(self, jobs: List[ScraperJob], dry_run: bool = False) -> Dict[str, Any]:
        """Run all jobs with parallel execution."""
        print(f"\n{'='*70}")
        print(f"PARALLEL DISPATCHER")
        print(f"{'='*70}")
        print(f"Jobs: {len(jobs)}")
        print(f"Max parallel: {self.max_parallel}")
        print(f"Browser scrapers: {sum(1 for j in jobs if j.scraper_type == ScraperType.BROWSER)}")
        print(f"Lightweight scrapers: {sum(1 for j in jobs if j.scraper_type == ScraperType.LIGHTWEIGHT)}")

        if dry_run:
            print(f"\n[DRY RUN] Would execute:")
            for job in jobs:
                print(f"  - {job.country}: {job.path.name} ({job.scraper_type.value})")
            return {'dry_run': True, 'jobs': len(jobs)}

        # Prioritize and queue jobs
        jobs = self.prioritize_jobs(jobs)
        for job in jobs:
            self.job_queue.put((job.priority, job))

        print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Starting execution...")
        start_time = datetime.now()

        # Start worker threads
        # For browser jobs, effectively 1 at a time due to lock
        # For lightweight, up to max_parallel
        threads = []
        for _ in range(self.max_parallel):
            t = threading.Thread(target=self.worker, daemon=True)
            t.start()
            threads.append(t)

        # Wait for all jobs to complete
        self.job_queue.join()

        # Wait for threads to finish
        for t in threads:
            t.join(timeout=5)

        end_time = datetime.now()
        total_duration = (end_time - start_time).total_seconds()

        # Generate summary
        completed = [j for j in self.completed_jobs if j.status == "completed"]
        failed = [j for j in self.completed_jobs if j.status != "completed"]

        print(f"\n{'='*70}")
        print(f"SUMMARY")
        print(f"{'='*70}")
        print(f"Total time: {total_duration:.0f}s ({total_duration/60:.1f} min)")
        print(f"Completed: {len(completed)}/{len(jobs)}")
        print(f"Failed: {len(failed)}")

        if failed:
            print(f"\nFailed jobs:")
            for job in failed:
                print(f"  ✗ {job.country}: {job.status}")
                if job.error:
                    print(f"    Error: {job.error[:100]}")

        return {
            'total_jobs': len(jobs),
            'completed': len(completed),
            'failed': len(failed),
            'duration_seconds': total_duration,
            'jobs': [
                {
                    'country': j.country,
                    'status': j.status,
                    'duration': (j.end_time - j.start_time).total_seconds() if j.end_time else 0
                }
                for j in self.completed_jobs
            ]
        }


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Parallel Dispatcher - Run scrapers with resource management')
    parser.add_argument('path', nargs='?', default='/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE/', help='Path to scrapers directory')
    parser.add_argument('--max-parallel', type=int, default=3, help='Max parallel jobs (default: 3)')
    parser.add_argument('--max-memory', type=float, default=80.0, help='Max memory percent (default: 80)')
    parser.add_argument('--countries', help='Comma-separated list of countries to run')
    parser.add_argument('--dry-run', action='store_true', help='Show what would run without executing')
    parser.add_argument('--list', action='store_true', help='List discovered scrapers')
    parser.add_argument('--json', action='store_true', help='Output JSON results')

    args = parser.parse_args()

    dispatcher = ParallelDispatcher(
        max_parallel=args.max_parallel,
        max_memory=args.max_memory
    )

    # Discover scrapers
    path = Path(args.path)
    if not path.exists():
        print(f"Error: Path not found: {path}")
        sys.exit(1)

    jobs = dispatcher.discover_scrapers(path)

    # Filter by countries if specified
    if args.countries:
        countries = [c.strip().upper() for c in args.countries.split(',')]
        jobs = [j for j in jobs if j.country.upper() in countries]

    if not jobs:
        print("No scrapers found")
        sys.exit(1)

    if args.list:
        print(f"\nDiscovered {len(jobs)} scrapers:")
        for job in jobs:
            print(f"  [{job.scraper_type.value:11}] {job.country}: {job.path.name}")
        sys.exit(0)

    # Run dispatcher
    results = dispatcher.run(jobs, dry_run=args.dry_run)

    if args.json:
        print(json.dumps(results, indent=2, default=str))

    sys.exit(0 if results.get('failed', 0) == 0 else 1)


if __name__ == '__main__':
    main()
