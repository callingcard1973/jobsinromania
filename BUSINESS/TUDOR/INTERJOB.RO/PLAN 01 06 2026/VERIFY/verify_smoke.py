#!/usr/bin/env python3
"""Smoke-test scheduled scripts on their host: remote py_compile (always) + optional dry-run."""
import json
import subprocess
import sys
from pathlib import Path

SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]


def ssh_run(host: str, cmd: str):
    r = subprocess.run(SSH + [f"tudor@{host}", cmd], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    cfg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "scheduled_scripts.json"
    scripts = json.loads(cfg.read_text(encoding="utf-8")).get("scripts", [])
    print(f"Smoke-testing {len(scripts)} scheduled scripts from {cfg.name}\n")

    fails = 0
    for s in scripts:
        host, path, name = s["host"], s["path"], s["name"]
        rc, out = ssh_run(host, f"python3 -m py_compile {path!r} && echo COMPILE_OK")
        if rc != 0 or "COMPILE_OK" not in out:
            print(f"  [FAIL] {name}: compile -> {out.splitlines()[-1] if out else 'error'}")
            fails += 1
            continue
        if s.get("dry_run"):
            rc, out = ssh_run(host, s["dry_run"])
            if rc != 0:
                print(f"  [FAIL] {name}: dry-run rc={rc} -> {out.splitlines()[-1] if out else ''}")
                fails += 1
                continue
            print(f"  [OK]   {name}: compile + dry-run")
        else:
            print(f"  [OK]   {name}: compile (no dry-run configured)")

    print(f"\nRESULT: {'FAIL' if fails else 'PASS'} ({fails} failures)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
