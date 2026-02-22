#!/usr/bin/env python3
"""
Daily CLAUDE.md audit — runs via Windows Task Scheduler.
Checks local D:\\MEMORY and remote raspibig for bloated CLAUDE.md files.
Logs results. No external dependencies.

Setup (run once):
  schtasks /create /tn "Claude MD Audit" /tr "python D:\\MEMORY\\OPTIMIZE TOKENS\\daily_audit.py" /sc daily /st 09:00
"""

import os
import json
import subprocess
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

MAX_LINES = 50
MAX_TOKENS = 1500
CHARS_PER_TOKEN = 4


def audit_local():
    """Audit local CLAUDE.md files."""
    results = []
    root = Path("D:\\MEMORY")
    for f in root.rglob("CLAUDE.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            lines = len(content.splitlines())
            tokens = len(content) // CHARS_PER_TOKEN
            bloated = lines > MAX_LINES or tokens > MAX_TOKENS
            results.append({
                "file": str(f),
                "lines": lines,
                "tokens": tokens,
                "bloated": bloated
            })
        except OSError:
            pass
    return results


def audit_raspibig():
    """Audit raspibig CLAUDE.md files via SSH."""
    try:
        cmd = [
            "ssh", "tudor@192.168.100.21",
            "find /opt -name CLAUDE.md -type f | xargs wc -lc 2>/dev/null | grep -v total"
        ]
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if out.returncode != 0:
            return [{"error": f"SSH failed: {out.stderr.strip()}"}]

        results = []
        for line in out.stdout.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split()
            if len(parts) >= 3:
                lines = int(parts[0])
                chars = int(parts[1])
                filepath = " ".join(parts[2:])
                tokens = chars // CHARS_PER_TOKEN
                bloated = lines > MAX_LINES or tokens > MAX_TOKENS
                results.append({
                    "file": filepath,
                    "lines": lines,
                    "tokens": tokens,
                    "bloated": bloated
                })
        return results
    except (subprocess.TimeoutExpired, OSError) as e:
        return [{"error": str(e)}]


def main():
    now = datetime.now()
    log_file = LOG_DIR / f"audit_{now.strftime('%Y%m%d')}.json"

    print(f"[AUDIT] {now.strftime('%Y-%m-%d %H:%M')}")

    local = audit_local()
    local_bloated = [r for r in local if r.get("bloated")]
    local_total = sum(r.get("lines", 0) for r in local)
    print(f"  Local: {len(local)} files, {len(local_bloated)} bloated, {local_total} total lines")

    remote = audit_raspibig()
    remote_bloated = [r for r in remote if r.get("bloated")]
    remote_total = sum(r.get("lines", 0) for r in remote if "lines" in r)
    print(f"  Raspibig: {len(remote)} files, {len(remote_bloated)} bloated, {remote_total} total lines")

    if local_bloated:
        print(f"\n  [WARN] Bloated local files:")
        for r in local_bloated[:5]:
            print(f"    {r['file']} — {r['lines']} lines, ~{r['tokens']} tokens")

    report = {
        "date": now.isoformat(),
        "local": {"total": len(local), "bloated": len(local_bloated), "total_lines": local_total},
        "raspibig": {"total": len(remote), "bloated": len(remote_bloated), "total_lines": remote_total},
        "local_bloated": local_bloated[:10],
        "remote_bloated": remote_bloated[:10]
    }

    with open(log_file, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n  Report: {log_file}")


if __name__ == "__main__":
    main()
