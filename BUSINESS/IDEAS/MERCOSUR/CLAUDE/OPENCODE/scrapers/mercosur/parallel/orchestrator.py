#!/usr/bin/env python3
"""
MERCOSUR Parallel Scraping Orchestrator
Spawns workers, monitors progress, merges results
"""

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import OUTPUT_BASE, THREAD_COUNTS, TIMEOUTS

WORKERS = {
    "websites": "worker_websites.py",
    "govapis": "worker_govapis.py",
    "associations": "worker_associations.py",
    "registries": "worker_registries.py",
    "tradeshows": "worker_tradeshows.py",
    "enricher": "worker_enricher.py",
}

WORKER_DIR = Path(__file__).parent
LOG_DIR = OUTPUT_BASE / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str, worker: str = "orchestrator"):
    """Log with timestamp"""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{worker}] {msg}")


def run_worker(
    worker_name: str,
    threads: Optional[int] = None,
    timeout: Optional[int] = None,
    extra_args: Optional[List[str]] = None,
) -> Dict:
    """Run a single worker subprocess"""
    worker_file = WORKER_DIR / WORKERS.get(worker_name, f"worker_{worker_name}.py")

    if not worker_file.exists():
        return {
            "worker": worker_name,
            "status": "not_found",
            "error": f"Worker file not found: {worker_file}",
        }

    threads = threads or THREAD_COUNTS.get(worker_name, 5)
    timeout = timeout or TIMEOUTS.get("worker_total", 3600)

    cmd = [sys.executable, str(worker_file), "--threads", str(threads)]
    if extra_args:
        cmd.extend(extra_args)

    log(f"Starting with {threads} threads, timeout {timeout}s", worker_name)
    start_time = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(WORKER_DIR),
        )

        elapsed = time.time() - start_time

        log_file = LOG_DIR / f"{worker_name}_{datetime.now():%Y%m%d_%H%M%S}.log"
        with open(log_file, "w") as f:
            f.write(f"=== STDOUT ===\n{result.stdout}\n")
            f.write(f"=== STDERR ===\n{result.stderr}\n")
            f.write(f"=== RETURN CODE: {result.returncode} ===\n")

        if result.returncode == 0:
            # Try to parse output for stats
            stats = parse_worker_output(result.stdout)
            return {
                "worker": worker_name,
                "status": "success",
                "elapsed": round(elapsed, 1),
                "stats": stats,
                "log": str(log_file),
            }
        else:
            return {
                "worker": worker_name,
                "status": "error",
                "elapsed": round(elapsed, 1),
                "error": result.stderr[-500:] if result.stderr else "Unknown error",
                "log": str(log_file),
            }

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start_time
        log(f"TIMEOUT after {elapsed:.0f}s", worker_name)
        return {
            "worker": worker_name,
            "status": "timeout",
            "elapsed": round(elapsed, 1),
        }

    except Exception as e:
        elapsed = time.time() - start_time
        log(f"ERROR: {e}", worker_name)
        return {
            "worker": worker_name,
            "status": "exception",
            "error": str(e),
            "elapsed": round(elapsed, 1),
        }


def parse_worker_output(stdout: str) -> Dict:
    """Parse worker stdout for statistics"""
    stats = {}

    for line in stdout.split("\n"):
        line = line.strip()
        if "Total:" in line or "total:" in line:
            try:
                num = int("".join(c for c in line.split(":")[-1] if c.isdigit()))
                stats["total"] = num
            except:
                pass
        elif "Email:" in line or "emails:" in line:
            try:
                num = int("".join(c for c in line.split(":")[-1] if c.isdigit()))
                stats["emails"] = num
            except:
                pass
        elif "Saved:" in line or "saved:" in line:
            try:
                num = int("".join(c for c in line.split(":")[-1] if c.isdigit()))
                stats["saved"] = num
            except:
                pass

    return stats


def run_all_parallel(workers: List[str], max_parallel: int = 3) -> Dict[str, Dict]:
    """Run multiple workers in parallel"""
    results = {}

    with ThreadPoolExecutor(max_workers=max_parallel) as executor:
        futures = {
            executor.submit(run_worker, worker): worker
            for worker in workers
        }

        for future in as_completed(futures):
            worker = futures[future]
            try:
                result = future.result()
                results[worker] = result
                log(f"Completed: {result.get('status')}", worker)
            except Exception as e:
                results[worker] = {"worker": worker, "status": "exception", "error": str(e)}
                log(f"Exception: {e}", worker)

    return results


def run_sequential(workers: List[str]) -> Dict[str, Dict]:
    """Run workers one at a time"""
    results = {}

    for i, worker in enumerate(workers):
        log(f"[{i+1}/{len(workers)}] Starting {worker}")
        result = run_worker(worker)
        results[worker] = result
        log(f"[{i+1}/{len(workers)}] {worker}: {result.get('status')}")

        # Brief pause between workers
        if i < len(workers) - 1:
            time.sleep(2)

    return results


def get_status() -> Dict:
    """Get current scraping status"""
    status = {
        "output_dirs": {},
        "last_run": None,
    }

    for worker in WORKERS:
        worker_dir = OUTPUT_BASE / worker
        if worker_dir.exists():
            files = list(worker_dir.glob("*.json")) + list(worker_dir.glob("*.csv"))
            status["output_dirs"][worker] = {
                "files": len(files),
                "latest": max((f.stat().st_mtime for f in files), default=0),
            }

    # Check for merged output
    merged_dir = OUTPUT_BASE / "merged"
    if merged_dir.exists():
        merged_files = list(merged_dir.glob("*.json"))
        if merged_files:
            latest = max(merged_files, key=lambda f: f.stat().st_mtime)
            status["last_run"] = datetime.fromtimestamp(
                latest.stat().st_mtime
            ).isoformat()

    return status


def print_summary(results: Dict[str, Dict]):
    """Print execution summary"""
    print("\n" + "=" * 60)
    print("EXECUTION SUMMARY")
    print("=" * 60)

    success = sum(1 for r in results.values() if r.get("status") == "success")
    failed = len(results) - success

    print(f"Success: {success}/{len(results)}")
    print(f"Failed: {failed}/{len(results)}")
    print()

    for worker, result in results.items():
        status = result.get("status", "unknown")
        elapsed = result.get("elapsed", 0)
        stats = result.get("stats", {})

        line = f"  {worker}: {status} ({elapsed}s)"
        if stats:
            line += f" - {stats}"
        print(line)

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="MERCOSUR Parallel Scraper Orchestrator")
    parser.add_argument("--all", action="store_true", help="Run all workers")
    parser.add_argument("--worker", type=str, help="Run specific worker")
    parser.add_argument("--workers", type=str, help="Comma-separated list of workers")
    parser.add_argument("--threads", type=int, help="Override thread count")
    parser.add_argument("--parallel", type=int, default=3, help="Max parallel workers")
    parser.add_argument("--sequential", action="store_true", help="Run workers sequentially")
    parser.add_argument("--selenium", action="store_true", help="Enable Selenium mode")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--merge", action="store_true", help="Just run merger")
    parser.add_argument("--timeout", type=int, help="Override timeout per worker")

    args = parser.parse_args()

    print("=" * 60)
    print("MERCOSUR PARALLEL SCRAPER ORCHESTRATOR")
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Output: {OUTPUT_BASE}")
    print("=" * 60)

    if args.status:
        status = get_status()
        print(json.dumps(status, indent=2, default=str))
        return

    if args.merge:
        log("Running merger only")
        result = run_worker("merger", extra_args=[])
        print(json.dumps(result, indent=2))
        return

    # Determine which workers to run
    workers_to_run = []

    if args.all:
        workers_to_run = list(WORKERS.keys())
    elif args.worker:
        workers_to_run = [args.worker]
    elif args.workers:
        workers_to_run = [w.strip() for w in args.workers.split(",")]
    else:
        print("Usage: orchestrator.py --all | --worker NAME | --workers a,b,c")
        print(f"Available workers: {', '.join(WORKERS.keys())}")
        return

    # Validate workers
    invalid = [w for w in workers_to_run if w not in WORKERS]
    if invalid:
        print(f"Invalid workers: {invalid}")
        print(f"Available: {', '.join(WORKERS.keys())}")
        return

    log(f"Workers to run: {workers_to_run}")

    # Run workers
    if args.sequential or len(workers_to_run) == 1:
        results = run_sequential(workers_to_run)
    else:
        results = run_all_parallel(workers_to_run, max_parallel=args.parallel)

    # Print summary
    print_summary(results)

    # Save run report
    report_file = LOG_DIR / f"run_{datetime.now():%Y%m%d_%H%M%S}.json"
    with open(report_file, "w") as f:
        json.dump({
            "run_time": datetime.now().isoformat(),
            "workers": workers_to_run,
            "results": results,
        }, f, indent=2)

    log(f"Report saved: {report_file}")

    # Auto-merge if all workers ran
    if args.all and all(r.get("status") == "success" for r in results.values()):
        log("All workers successful, running merger...")
        merger_result = run_worker("merger", extra_args=[])
        log(f"Merger: {merger_result.get('status')}")


if __name__ == "__main__":
    main()
