#!/usr/bin/env python3
"""
MERCOSUR2 Inventory Script
Scans /opt and /home/tudor for scrapers, scripts, datasets, databases, and notebooks.
Outputs a structured inventory report (inventory_report.txt).
"""
import os
from datetime import datetime

TARGET_DIRS = ["/opt", "/home/tudor"]
REPORT_FILE = "inventory_report.txt"

EXTENSIONS = [
    ".py", ".sh", ".ipynb", ".csv", ".json", ".db", ".sqlite", ".sql", ".md"
]


def scan_dir(base):
    results = []
    for root, dirs, files in os.walk(base):
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext in EXTENSIONS:
                path = os.path.join(root, f)
                try:
                    stat = os.stat(path)
                    size = stat.st_size
                    mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
                except Exception as e:
                    size = -1
                    mtime = "ERROR"
                results.append({
                    "path": path,
                    "ext": ext,
                    "size": size,
                    "mtime": mtime
                })
    return results


def main():
    all_results = []
    for d in TARGET_DIRS:
        all_results.extend(scan_dir(d))
    all_results.sort(key=lambda x: x["path"])
    with open(REPORT_FILE, "w") as f:
        f.write(f"MERCOSUR2 Inventory Report\nGenerated: {datetime.now().isoformat()}\n\n")
        for r in all_results:
            f.write(f"{r['path']} | {r['ext']} | {r['size']} bytes | {r['mtime']}\n")
    print(f"Inventory complete. Report saved to {REPORT_FILE}")

if __name__ == "__main__":
    main()
