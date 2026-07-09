#!/usr/bin/env python3
"""Load DATA/leads/*.csv into the romania DB as iscir_<stem> tables (all text cols).
Usage: python CODE/load_leads_pg.py <host> <port>
Runs psql (pg18 client) for DDL + \\copy. Idempotent: drops+recreates each table.
"""
import sys, re, csv, glob, os, subprocess, pathlib

PSQL = r"C:\Users\apami\pg18\bin\psql.exe"
ENV = {**os.environ, "PGPASSWORD": "tudor"}


def col(name, i):
    c = re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')
    if not c or c[0].isdigit():
        c = 'c_' + c
    return c


def psql(host, port, sql=None, copy=None):
    cmd = [PSQL, "-h", host, "-p", port, "-U", "tudor", "-d", "romania",
           "-q", "-v", "ON_ERROR_STOP=1", "-c", sql or copy]
    r = subprocess.run(cmd, env=ENV, capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    host, port = sys.argv[1], sys.argv[2]
    for f in sorted(glob.glob("DATA/leads/*.csv")):
        stem = re.sub(r'[^a-z0-9]+', '_', pathlib.Path(f).stem.lower()).strip('_')
        tbl = f"iscir_{stem}".replace("iscir_iscir_", "iscir_")
        with open(f, encoding='utf-8') as fh:
            hdr = next(csv.reader(fh))
        seen, cols = {}, []
        for i, h in enumerate(hdr):
            c = col(h, i)
            seen[c] = seen.get(c, 0) + 1
            cols.append(c if seen[c] == 1 else f"{c}_{seen[c]}")
        ddl = f'DROP TABLE IF EXISTS {tbl}; CREATE TABLE {tbl} (' + \
              ', '.join(f'"{c}" text' for c in cols) + ');'
        rc, out = psql(host, port, sql=ddl)
        if rc:
            print(f"  DDL-FAIL {tbl}: {out[:80]}"); continue
        abspath = str(pathlib.Path(f).resolve())
        rc, out = psql(host, port, copy=f"\\copy {tbl} FROM '{abspath}' WITH (FORMAT csv, HEADER true)")
        if rc:
            print(f"  COPY-FAIL {tbl}: {out[:80]}"); continue
        rc, n = psql(host, port, sql=f"SELECT count(*) FROM {tbl};")
        print(f"  {tbl:<44} {n}")


if __name__ == "__main__":
    main()
