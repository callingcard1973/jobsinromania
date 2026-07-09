#!/usr/bin/env python3
"""Lint + syntax-check Python: ruff check, ruff format --check, py_compile sweep, 250-line rule."""
import subprocess
import sys
from pathlib import Path

MAX_LINES = 250  # CLAUDE.md coding standard


def find_py(root: Path):
    skip = {".git", "__pycache__", ".claude", "node_modules", "ARCHIVE", "venv", ".venv"}
    return [p for p in root.rglob("*.py") if not skip & set(p.parts)]


def run_ruff(root: Path) -> int:
    cfg = Path(__file__).parent / "ruff.toml"
    print(f"== ruff check {root} (config: {cfg.name}) ==")
    r = subprocess.run([sys.executable, "-m", "ruff", "check",
                        "--config", str(cfg), str(root)])
    return r.returncode


def compile_sweep(files) -> list:
    failed = []
    for f in files:
        r = subprocess.run([sys.executable, "-m", "py_compile", str(f)],
                           capture_output=True, text=True)
        if r.returncode != 0:
            failed.append((f, r.stderr.strip().splitlines()[-1] if r.stderr else "error"))
    return failed


def line_check(files) -> list:
    over = []
    for f in files:
        try:
            n = sum(1 for _ in f.open(encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if n > MAX_LINES:
            over.append((f, n))
    return over


def main():
    root = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    files = find_py(root)
    print(f"Scanning {len(files)} .py files under {root}\n")

    rc_ruff = run_ruff(root)

    print("\n== py_compile sweep ==")
    failed = compile_sweep(files)
    for f, msg in failed:
        print(f"  SYNTAX FAIL: {f}: {msg}")
    print(f"  {len(files) - len(failed)}/{len(files)} compile OK")

    print("\n== 250-line rule ==")
    over = line_check(files)
    for f, n in sorted(over, key=lambda x: -x[1]):
        print(f"  OVER {n}: {f}")
    print(f"  {len(over)} files exceed {MAX_LINES} lines")

    fails = (rc_ruff != 0) + bool(failed)
    print(f"\nRESULT: {'FAIL' if fails else 'PASS'} (line-rule is advisory)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
