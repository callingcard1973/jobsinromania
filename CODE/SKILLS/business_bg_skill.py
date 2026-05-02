#!/usr/bin/env python3
"""Skill: business.bg scraper management.

Usage:
  python3 business_bg_skill.py --stats        # show current counts
  python3 business_bg_skill.py --test         # test scrape 50 companies
  python3 business_bg_skill.py --full         # launch full scrape (nohup)
  python3 business_bg_skill.py --stop         # stop running scrape
  python3 business_bg_skill.py --log          # tail scrape log
"""

import argparse
import os
import subprocess
import sys

SCRAPER = "/opt/ACTIVE/BULGARIA/scrape_business_bg.py"
LOG = "/tmp/scrape_business_bg.log"
PID_FILE = "/tmp/scrape_business_bg.pid"


def run(cmd):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(r.stdout)
    if r.stderr:
        print(r.stderr, file=sys.stderr)
    return r.returncode


def stats():
    return run(f"python3 {SCRAPER} --stats")


def test():
    return run(f"python3 {SCRAPER} --limit 50 --delay 2.5")


def full():
    cmd = f"nohup python3 {SCRAPER} --delay 2.5 > {LOG} 2>&1 & echo $!"
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    pid = r.stdout.strip()
    if pid:
        with open(PID_FILE, "w") as f:
            f.write(pid)
        print(f"Scrape launched (PID {pid}), log: {LOG}")
    else:
        print("Failed to launch", file=sys.stderr)
        return 1
    return 0


def stop():
    if os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid = f.read().strip()
        run(f"kill {pid} 2>/dev/null")
        os.remove(PID_FILE)
        print(f"Stopped PID {pid}")
    else:
        run("pkill -f scrape_business_bg.py")
    return 0


def log():
    return run(f"tail -50 {LOG}")


def main():
    ap = argparse.ArgumentParser(description="business.bg scraper skill")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--test", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--stop", action="store_true")
    ap.add_argument("--log", action="store_true")
    args = ap.parse_args()

    if args.stats:
        return stats()
    elif args.test:
        return test()
    elif args.full:
        return full()
    elif args.stop:
        return stop()
    elif args.log:
        return log()
    else:
        ap.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
