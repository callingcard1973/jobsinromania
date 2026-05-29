#!/usr/bin/env python3
"""Bulk CLAUDE.md trimmer - condenses all bloated files to <=50 lines."""
import os, re, subprocess, shutil
from datetime import datetime

MAX_LINES = 50
SKIP_SECTIONS = {
    "session state", "incidents", "lessons learned", "faq",
    "troubleshooting", "version", "implementation checklist",
    "pending responses", "next steps", "changelog", "history",
    "building sellable assets", "how to sell", "negotiation",
    "12-month action plan", "action plan", "notes",
}
BOILERPLATE = [
    "this file provides guidance",
    "this file gives claude code",
    "claude code (claude.ai/code)",
]


def trim_file(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return None, None, "read_error"

    orig_lines = len(content.splitlines())
    orig_tokens = len(content) // 4

    if orig_lines <= MAX_LINES and orig_tokens <= 1500:
        return orig_lines, orig_lines, "already_ok"

    lines = content.splitlines()
    result = []
    in_code_block = False
    in_skip_section = False
    prev_blank = False

    for line in lines:
        stripped = line.strip()

        # Toggle code blocks - remove them
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue

        # Check for skip sections
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

        # Remove boilerplate
        if any(bp in stripped.lower() for bp in BOILERPLATE):
            continue

        # Collapse multiple blank lines
        if not stripped:
            if prev_blank:
                continue
            prev_blank = True
        else:
            prev_blank = False

        result.append(line)

    # If still over, remove table separator lines
    if len(result) > MAX_LINES:
        result = [l for l in result if not re.match(r"^\s*\|[-\s|:]+\|\s*$", l)]

    # If still over, hard truncate
    if len(result) > MAX_LINES:
        result = result[:MAX_LINES]

    # Remove trailing blank lines
    while result and not result[-1].strip():
        result.pop()

    new_content = "\n".join(result) + "\n"
    new_lines = len(new_content.splitlines())

    # Archive before write (safety: prevent data loss)
    backup_path = f"{path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(path, backup_path)

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return orig_lines, new_lines, "trimmed"


def main():
    result = subprocess.run(
        ["find", "/opt", "-name", "CLAUDE.md", "-type", "f"],
        capture_output=True, text=True
    )
    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]

    total_before = 0
    total_after = 0
    trimmed_count = 0
    still_over = []

    for path in sorted(files):
        orig, new, status = trim_file(path)
        if status == "already_ok":
            total_before += orig
            total_after += orig
            continue
        if status == "read_error":
            continue

        total_before += orig
        total_after += new
        trimmed_count += 1
        short = path.replace("/opt/ACTIVE/", "").replace("/opt/INACTIVE/", "~")
        saved = orig - new
        flag = " [STILL OVER]" if new > MAX_LINES else ""
        print(f"  {orig:>4} -> {new:>3} ({saved:>+4}) {short}")
        if new > MAX_LINES:
            still_over.append((path, new))

    print()
    print("=== SUMMARY ===")
    print(f"  Files trimmed: {trimmed_count}")
    print(f"  Total lines: {total_before} -> {total_after} (saved {total_before - total_after})")
    print(f"  Still over 50: {len(still_over)}")
    for p, n in still_over:
        short = p.replace("/opt/ACTIVE/", "").replace("/opt/INACTIVE/", "~")
        print(f"    {n} lines: {short}")


if __name__ == "__main__":
    main()
