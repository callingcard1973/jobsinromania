#!/usr/bin/env python3
"""
Daily CLAUDE.md audit — runs via Windows Task Scheduler.
Checks local D:\\MEMORY and remote raspibig for bloated CLAUDE.md files.
Logs results. No external dependencies.

Setup (run once):
  schtasks /create /tn "Claude MD Audit" /tr "python D:\\MEMORY\\OPTIMIZE TOKENS\\daily_audit.py" /sc daily /st 09:00
"""

import os
import re
import json
import subprocess
from datetime import datetime
from pathlib import Path

LOG_DIR = Path("D:\\MEMORY\\OPTIMIZE TOKENS\\logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

MAX_LINES = 50
MAX_TOKENS = 1500
CHARS_PER_TOKEN = 4

SKIP_SECTIONS = {
    "session state", "incidents", "lessons learned", "faq",
    "troubleshooting", "version", "implementation checklist",
    "pending responses", "next steps", "changelog", "history", "notes",
}
BOILERPLATE = [
    "this file provides guidance",
    "this file gives claude code",
    "claude code (claude.ai/code)",
]


def trim_file(path):
    """Auto-trim a single CLAUDE.md to <=50 lines."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return 0

    orig_lines = len(content.splitlines())
    if orig_lines <= MAX_LINES:
        return 0

    lines = content.splitlines()
    result = []
    in_code_block = False
    in_skip_section = False
    prev_blank = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if stripped.startswith("##"):
            section_name = stripped.lstrip("#").strip().lower()
            section_name = re.sub(r"\(.*?\)", "", section_name).strip()
            if any(skip in section_name for skip in SKIP_SECTIONS):
                in_skip_section = True
                continue
            else:
                in_skip_section = False
        if in_skip_section:
            continue
        if any(bp in stripped.lower() for bp in BOILERPLATE):
            continue
        if not stripped:
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False
        result.append(line)

    if len(result) > MAX_LINES:
        result = [l for l in result if not re.match(r"^\s*\|[-\s|:]+\|\s*$", l)]
    if len(result) > MAX_LINES:
        result = result[:MAX_LINES]
    while result and not result[-1].strip():
        result.pop()

    path.write_text("\n".join(result) + "\n", encoding="utf-8")
    return orig_lines - len(result)


def audit_and_trim_local():
    """Audit and auto-trim local CLAUDE.md files."""
    results = []
    trimmed_total = 0
    root = Path("D:\\MEMORY")
    for f in root.rglob("CLAUDE.md"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            lines = len(content.splitlines())
            tokens = len(content) // CHARS_PER_TOKEN
            bloated = lines > MAX_LINES or tokens > MAX_TOKENS
            if bloated:
                saved = trim_file(f)
                trimmed_total += saved
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
    return results, trimmed_total


def audit_local():
    """Audit local CLAUDE.md files (no trimming)."""
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

    print(f"[AUDIT+TRIM] {now.strftime('%Y-%m-%d %H:%M')}")

    local, trimmed_lines = audit_and_trim_local()
    local_bloated = [r for r in local if r.get("bloated")]
    local_total = sum(r.get("lines", 0) for r in local)
    print(f"  Local: {len(local)} files, {len(local_bloated)} bloated, {local_total} total lines")
    if trimmed_lines:
        print(f"  Auto-trimmed: {trimmed_lines} lines removed")

    # Auto-trim raspibig too
    try:
        subprocess.run(
            ["ssh", "tudor@192.168.100.21",
             "python3 /opt/ACTIVE/INFRA/SKILLS/claude_md_bulk_trim.py 2>/dev/null | tail -3"],
            capture_output=True, text=True, timeout=60
        )
    except Exception:
        pass

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
