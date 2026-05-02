#!/usr/bin/env python3
"""
CSV Watcher - Uses inotify to auto-process new CSV files
Runs as daemon, triggers preprocessing pipeline
"""
import sys
import os
import time
import subprocess
from pathlib import Path

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

WATCH_DIRS = [
    '/home/tudor/SCRAPER_DATA',
    '/opt/ACTIVE/OPENDATA/DATA'
]

PYTHON = '/opt/ACTIVE/INFRA/venv/bin/python3'
PREPROCESSOR = '/opt/ACTIVE/INFRA/SKILLS/preprocessors/csv_preprocessor.py'
PIPELINE = '/opt/ACTIVE/INFRA/SKILLS/auto_pipeline.sh'

class CSVHandler(FileSystemEventHandler):
    """Handle CSV file events."""

    def __init__(self):
        self.processed = set()
        self.cooldown = {}

    def on_created(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.csv'):
            self.process_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory:
            return
        if event.src_path.endswith('.csv'):
            self.process_file(event.src_path)

    def process_file(self, filepath):
        # Cooldown: don't process same file within 60 seconds
        now = time.time()
        if filepath in self.cooldown:
            if now - self.cooldown[filepath] < 60:
                return

        self.cooldown[filepath] = now

        print(f"[{time.strftime('%H:%M:%S')}] New CSV: {filepath}")

        # Run preprocessor
        try:
            result = subprocess.run(
                [PYTHON, PREPROCESSOR, filepath],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode == 0:
                print(f"  Analyzed: OK")
            else:
                print(f"  Error: {result.stderr[:100]}")
        except Exception as e:
            print(f"  Exception: {e}")

def run_daemon():
    """Run as background daemon watching directories."""
    if not WATCHDOG_AVAILABLE:
        print("Error: watchdog not installed")
        print("Install with: pip install watchdog")
        sys.exit(1)

    print(f"CSV Watcher starting...")
    print(f"Watching: {', '.join(WATCH_DIRS)}")

    observer = Observer()
    handler = CSVHandler()

    for watch_dir in WATCH_DIRS:
        if Path(watch_dir).exists():
            observer.schedule(handler, watch_dir, recursive=True)
            print(f"  Added: {watch_dir}")

    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()

    observer.join()
    print("CSV Watcher stopped")

def run_once(directory):
    """Process all CSVs in directory once."""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Directory not found: {directory}")
        return

    csvs = list(dir_path.glob('**/*.csv'))
    print(f"Found {len(csvs)} CSV files in {directory}")

    for csv_file in csvs:
        print(f"\nProcessing: {csv_file.name}")
        subprocess.run([PYTHON, PREPROCESSOR, str(csv_file)])

def main():
    if len(sys.argv) < 2:
        print("Usage: csv_watcher.py <command>")
        print("\nCommands:")
        print("  daemon          - Run as background watcher")
        print("  once <dir>      - Process all CSVs in directory once")
        print("  test <file>     - Test processing single file")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'daemon':
        run_daemon()
    elif cmd == 'once':
        run_once(sys.argv[2] if len(sys.argv) > 2 else '/home/tudor/SCRAPER_DATA')
    elif cmd == 'test':
        if len(sys.argv) < 3:
            print("Usage: csv_watcher.py test <file.csv>")
            sys.exit(1)
        subprocess.run([PYTHON, PREPROCESSOR, sys.argv[2]])
    else:
        print(f"Unknown command: {cmd}")
        sys.exit(1)

if __name__ == '__main__':
    main()
