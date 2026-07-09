#!/usr/bin/env python3
"""DB-contract check over SSH: assert each contract's table + columns exist on its host/db.

Runs psql ON the host (DBs listen on localhost only), so no network DB exposure needed.
"""
import json
import subprocess
import sys
from pathlib import Path

SSH = ["ssh", "-o", "ConnectTimeout=10", "-o", "BatchMode=yes"]


def psql(host: str, db: str, sql: str):
    cmd = SSH + [f"tudor@{host}", f'PGHOST=localhost psql -d {db} -tAc {sql!r}']
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode, r.stdout.strip(), r.stderr.strip()


def check(c: dict) -> list:
    host, db, table = c["host"], c["db"], c["table"]
    rc, out, err = psql(host, db, f"SELECT to_regclass('{table}')")
    if rc != 0:
        return [f"PSQL FAIL {host}/{db}: {err.splitlines()[-1] if err else 'error'}"]
    if not out:
        return [f"TABLE MISSING: {db}.{table}"]
    rc, out, err = psql(
        host, db,
        f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'")
    have = set(out.splitlines())
    return [f"COLUMN MISSING: {db}.{table}.{col}"
            for col in c.get("columns", []) if col not in have]


def main():
    cfg = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "db_contracts.json"
    contracts = json.loads(cfg.read_text(encoding="utf-8")).get("contracts", [])
    print(f"Checking {len(contracts)} DB contracts from {cfg.name}\n")
    total = []
    for c in contracts:
        errs = check(c)
        print(f"  [{'FAIL' if errs else 'OK'}] {c['name']} -> {c['host']}/{c['db']}.{c['table']}")
        for e in errs:
            print(f"        {e}")
        total += errs
    print(f"\nRESULT: {'FAIL' if total else 'PASS'} ({len(total)} contract violations)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
