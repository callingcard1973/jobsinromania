#!/usr/bin/env python3
"""
Contractor Enrichment Skill

Enriches SEAP contractors with contact info from internal data sources.
Runs on raspibig (16GB RAM).

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/contractor_enrichment.py status      # Check status
    python3 /opt/ACTIVE/INFRA/SKILLS/contractor_enrichment.py run         # Run enrichment
    python3 /opt/ACTIVE/INFRA/SKILLS/contractor_enrichment.py run --bg    # Run in background
    python3 /opt/ACTIVE/INFRA/SKILLS/contractor_enrichment.py watchdog    # Run watchdog check
    python3 /opt/ACTIVE/INFRA/SKILLS/contractor_enrichment.py output      # Show output stats

Machine: raspibig only (memory-intensive)
Schedule: Weekly or on-demand
"""

import subprocess
import sys
import os
from pathlib import Path
from datetime import datetime

SCRIPT = "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/run_enrich_contractors.sh"
WATCHDOG = "/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/watchdog_enrich_contractors.py"
OUTPUT = Path("/opt/ACTIVE/OPENDATA/DATA/CONTRACTOR_MATCHES/contractors_enriched.csv")
PID_FILE = Path("/tmp/enrich_contractors.pid")
LOG_DIR = Path("/opt/ACTIVE/INFRA/LOGS/scrapers")


def check_running():
    """Check if enrichment is running."""
    if not PID_FILE.exists():
        return False, None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True, pid
    except:
        return False, None


def get_output_stats():
    """Get stats from output file."""
    if not OUTPUT.exists():
        return None
    
    import pandas as pd
    df = pd.read_csv(OUTPUT, nrows=0)
    row_count = sum(1 for _ in open(OUTPUT)) - 1
    mtime = datetime.fromtimestamp(OUTPUT.stat().st_mtime)
    
    return {
        "rows": row_count,
        "columns": len(df.columns),
        "updated": mtime.strftime("%Y-%m-%d %H:%M"),
        "size_mb": OUTPUT.stat().st_size / 1024 / 1024
    }


def cmd_status():
    """Show current status."""
    running, pid = check_running()
    print("=" * 50)
    print("CONTRACTOR ENRICHMENT STATUS")
    print("=" * 50)
    
    if running:
        print(f"Status: 🔄 RUNNING (PID {pid})")
    else:
        print("Status: ⏹️  IDLE")
    
    stats = get_output_stats()
    if stats:
        print(f"\nOutput: {OUTPUT}")
        print(f"  Rows: {stats['rows']:,}")
        print(f"  Updated: {stats['updated']}")
        print(f"  Size: {stats['size_mb']:.1f} MB")
    else:
        print("\nOutput: Not found")
    
    # Recent log
    today = datetime.now().strftime("%Y%m%d")
    log_file = LOG_DIR / f"enrich_contractors_{today}.log"
    if log_file.exists():
        print(f"\nRecent log ({log_file.name}):")
        lines = log_file.read_text().strip().split("\n")[-5:]
        for line in lines:
            print(f"  {line[:80]}")


def cmd_run(background=False):
    """Run enrichment."""
    running, pid = check_running()
    if running:
        print(f"Already running (PID {pid})")
        return 1
    
    if background:
        print("Starting in background...")
        subprocess.Popen(
            ["nohup", SCRIPT],
            stdout=open("/dev/null", "w"),
            stderr=subprocess.STDOUT,
            start_new_session=True
        )
        print("Started. Use 'status' to monitor.")
    else:
        print("Running (foreground)...")
        return subprocess.call([SCRIPT])
    return 0


def cmd_watchdog():
    """Run watchdog check."""
    return subprocess.call([sys.executable, WATCHDOG])


def cmd_output():
    """Show output details."""
    stats = get_output_stats()
    if not stats:
        print("No output file found")
        return 1
    
    import pandas as pd
    df = pd.read_csv(OUTPUT, nrows=5)
    
    print(f"Output: {OUTPUT}")
    print(f"Rows: {stats['rows']:,}")
    print(f"Columns: {stats['columns']}")
    print(f"Updated: {stats['updated']}")
    print(f"\nColumns: {list(df.columns)}")
    print(f"\nSample (first 5 rows):")
    print(df.to_string())
    return 0


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 0
    
    cmd = sys.argv[1]
    
    if cmd == "status":
        cmd_status()
    elif cmd == "run":
        bg = "--bg" in sys.argv or "-b" in sys.argv
        return cmd_run(background=bg)
    elif cmd == "watchdog":
        return cmd_watchdog()
    elif cmd == "output":
        return cmd_output()
    else:
        print(f"Unknown command: {cmd}")
        print("Commands: status, run, run --bg, watchdog, output")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
