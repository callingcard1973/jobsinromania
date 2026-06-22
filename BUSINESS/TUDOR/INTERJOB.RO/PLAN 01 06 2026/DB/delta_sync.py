#!/usr/bin/env python3
"""Two-way column-partitioned delta sync: laptop companies_clean <-> raspibig public.companies.

Both sides' work is preserved: raspibig owns row existence + SOURCE columns (new companies,
scraped fields); laptop owns ENRICHMENT columns. Same id space (PK=id on raspibig). Keyed on id.
Dry-run by default; pass --apply to write. Watermark persisted to delta_sync_state.json.

STRAGGLER HANDLING: pull selects `id > last_pull_id OR updated_at > last_pull_ts`, so a lower id that
commits after a higher one (sequence values aren't commit-ordered) is still caught by the updated_at
clause on the next run. An index on updated_at (created by ensure_updated_at_index) keeps that cheap.
CAVEAT: this relies on raspibig's writers setting updated_at on INSERT/UPDATE; if a writer leaves
updated_at NULL/stale on insert, that row is only caught by the id clause (still fine for pure inserts).
"""
import sys
import json
import os
import datetime
import psycopg2
from psycopg2.extras import execute_values

# raspibig has a global statement_timeout=10min that would cancel long sync scans/index builds;
# disable it for these controlled batch connections (production is still protected by lock_timeout on DDL).
_KA = dict(keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=5,
           options="-c statement_timeout=0")
LAP = dict(host="127.0.0.1", port=5433, dbname="interjob_master", user="tudor", password="tudor", **_KA)
RAS = dict(host="192.168.100.21", port=5432, dbname="interjob_master", user="tudor", password="tudor", **_KA)
LTBL, RTBL = "companies_clean", "public.companies"
STATE = os.path.join(os.path.dirname(__file__), "delta_sync_state.json")

# laptop-owned enrichment columns (only these are pushed up; everything else is raspibig-owned source).
# NOTE: when the pipeline adds a new enrichment column, add it here too -- main() warns about any
# laptop column that is neither classified here nor a raspibig source column (drift -> silent loss).
ENRICH = ["lead_score", "email", "enriched_email", "enriched_phone", "is_agency", "ted_wins",
          "contact_first_name", "email_domain", "gdpr_basis", "gdpr_basis_date", "last_contacted_at",
          "last_ted_year", "linkedin_url", "phone_e164", "seap_total_ron", "seap_wins",
          "size_segment", "standard_sector", "times_contacted"]
BATCH = 5000


def load_state():
    if os.path.exists(STATE):
        with open(STATE) as f:
            return json.load(f)
    return {"last_pull_id": 0, "last_pull_ts": "1970-01-01", "last_push_ts": "1970-01-01"}


def save_state(s):
    with open(STATE, "w") as f:
        json.dump(s, f, indent=2, default=str)


def ensure_id_unique(conn):
    """Idempotently ensure companies_clean(id) has a unique key (needed for ON CONFLICT (id))."""
    c = conn.cursor()
    c.execute("SELECT 1 FROM pg_constraint WHERE conrelid=%s::regclass AND contype IN ('p','u')", (LTBL,))
    if not c.fetchone():
        c.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {LTBL.split('.')[-1]}_id_uk ON {LTBL} (id)")
        conn.commit()


def ensure_updated_at_index(conn, tbl, concurrently=False):
    """Idempotently ensure an index on updated_at so the pull/push watermark predicate stays cheap."""
    name = tbl.split(".")[-1] + "_updated_at_idx"
    cc = " CONCURRENTLY" if concurrently else ""
    try:
        if concurrently:
            conn.rollback()         # close any open txn so autocommit can be toggled
            conn.autocommit = True  # CREATE INDEX CONCURRENTLY cannot run in a transaction block
        conn.cursor().execute(f"CREATE INDEX{cc} IF NOT EXISTS {name} ON {tbl} (updated_at)")
        if not concurrently:
            conn.commit()
    except psycopg2.Error as e:
        conn.rollback()
        print(f"[idx] skip {name}: {str(e).splitlines()[0]}")
    finally:
        if concurrently:
            conn.autocommit = False


def cols(conn, tbl):
    sch, _, t = tbl.rpartition(".")
    c = conn.cursor()
    c.execute("SELECT column_name FROM information_schema.columns WHERE table_schema=%s AND table_name=%s",
              (sch or "public", t))
    return [r[0] for r in c.fetchall()]


def schema_sync(lcon, rcon, have, apply):
    """Add laptop enrichment columns missing on raspibig so push can land."""
    c = lcon.cursor()
    c.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=%s", (LTBL,))
    ltypes = dict(c.fetchall())
    missing = [col for col in ENRICH if col not in have]
    print(f"[schema] enrichment cols missing on raspibig: {missing or 'none'}")
    if missing and apply:
        # one ALTER (single lock grab) for all columns; short lock_timeout so production is never blocked,
        # retried with backoff to catch a gap between raspibig's writes to companies.
        adds = ",".join(f'ADD COLUMN IF NOT EXISTS "{c}" {ltypes.get(c, "text")}' for c in missing)
        for attempt in range(1, 11):
            cur = rcon.cursor()
            try:
                cur.execute("SET lock_timeout='5s'")
                cur.execute(f'ALTER TABLE {RTBL} {adds}')
                rcon.commit()
                print(f"[schema] added {len(missing)} columns (attempt {attempt})")
                break
            except psycopg2.errors.LockNotAvailable:
                rcon.rollback()
                print(f"[schema] lock busy, retry {attempt}/10 in 30s")
                import time
                time.sleep(30)
        else:
            print("[schema] WARN could not acquire lock after 10 tries; push deferred to next run")
            return


def pull(lcon, rcon, st, src, apply):
    """raspibig -> laptop: new rows (id>watermark) OR changed rows (updated_at>watermark),
    source columns only (preserves laptop enrichment). The updated_at clause also catches
    'stragglers' -- lower ids that commit after a higher one under concurrent inserts."""
    rc = rcon.cursor()
    args = (st["last_pull_id"], st["last_pull_ts"])
    # UNION of two indexed conditions (PK on id, idx on updated_at). A single `id>.. OR updated_at>..`
    # makes the planner seq-scan 40M; UNION lets each side use its index.
    sel = (f"SELECT {{cols}} FROM {RTBL} WHERE id > %s"
           f" UNION SELECT {{cols}} FROM {RTBL} WHERE updated_at > %s")
    rc.execute(f"SELECT count(*) FROM ({sel.format(cols='id')}) x", args)
    print(f"[pull] raspibig rows new/changed (id>{st['last_pull_id']} or updated_at>{st['last_pull_ts']}): {rc.fetchone()[0]}")
    if not apply:
        return
    ensure_id_unique(lcon)  # ON CONFLICT (id) requires a unique key on the laptop table
    cutoff = datetime.datetime.now()  # snapshot cutoff BEFORE the query so mid-run changes aren't skipped
    collist = ",".join(f'"{c}"' for c in src)
    upd = ",".join(f'"{c}"=EXCLUDED."{c}"' for c in src if c != "id")
    id_idx = src.index("id")
    cur = rcon.cursor(name="pull_cur")  # server-side: stream, don't buffer 40M rows client-side
    cur.itersize = BATCH
    cur.execute(f"SELECT * FROM ({sel.format(cols=collist)}) x ORDER BY id", args)
    lc = lcon.cursor()
    moved = 0
    maxid = st["last_pull_id"]
    while True:
        rows = cur.fetchmany(BATCH)
        if not rows:
            break
        execute_values(lc, f'INSERT INTO {LTBL} ({collist}) VALUES %s ON CONFLICT (id) DO UPDATE SET {upd}', rows)
        moved += len(rows)
        maxid = max(maxid, rows[-1][id_idx])  # ORDER BY id; max() guards against a changed old row regressing it
    lcon.commit()
    st["last_pull_id"] = maxid
    st["last_pull_ts"] = str(cutoff)
    print(f"[pull] upserted {moved} rows into laptop (source columns only)")


def push(lcon, rcon, st, apply):
    """laptop -> raspibig: enrichment columns for rows changed since last push (preserves source)."""
    lc = lcon.cursor()
    lc.execute(f"SELECT count(*) FROM {LTBL} WHERE updated_at > %s", (st["last_push_ts"],))
    print(f"[push] laptop rows with enrichment changes since {st['last_push_ts']}: {lc.fetchone()[0]}")
    if not apply:
        return
    push_cols = [c for c in ENRICH if c != "id"]
    collist = ",".join(f'"{c}"' for c in (["id"] + push_cols))
    setc = ",".join(f'"{c}"=d."{c}"' for c in push_cols)
    cutoff = datetime.datetime.now()  # snapshot cutoff BEFORE the query, so rows changed mid-run aren't skipped
    cur = lcon.cursor(name="push_cur")  # server-side stream
    cur.itersize = BATCH
    cur.execute(f'SELECT {collist} FROM {LTBL} WHERE updated_at > %s ORDER BY id', (st["last_push_ts"],))
    rcur = rcon.cursor()
    moved = 0
    while True:
        rows = cur.fetchmany(BATCH)
        if not rows:
            break
        execute_values(rcur, f'UPDATE {RTBL} t SET {setc} FROM (VALUES %s) AS d({collist}) WHERE t.id=d.id', rows)
        moved += len(rows)
    rcon.commit()
    st["last_push_ts"] = str(cutoff)
    print(f"[push] updated enrichment on {moved} raspibig rows")


def main():
    apply = "--apply" in sys.argv
    print(f"=== delta_sync ({'APPLY' if apply else 'dry-run'}) {datetime.datetime.now()} ===")
    st = load_state()
    print(f"[state] {st}")
    lcon = psycopg2.connect(**LAP)
    rcon = psycopg2.connect(**RAS)

    if "init" in sys.argv:
        # baseline: laptop and raspibig are currently in sync (same rows/ids).
        rc = rcon.cursor()
        rc.execute(f"SELECT max(id) FROM {RTBL}")
        st["last_pull_id"] = rc.fetchone()[0]
        now = str(datetime.datetime.now())
        st["last_pull_ts"] = now
        st["last_push_ts"] = now
        save_state(st)
        print(f"[init] baselined watermark to current state: {st}")
        lcon.close()
        rcon.close()
        return

    lap_cols = set(cols(lcon, LTBL))
    have = set(cols(rcon, RTBL))           # raspibig columns, reused by schema_sync + pull
    src = [c for c in have if c in lap_cols and c not in ENRICH]  # raspibig-owned source columns
    # drift guard: a laptop column that is neither classified enrichment nor a known source column
    # would be silently overwritten by pull -> warn loudly so it gets added to ENRICH.
    unclassified = sorted(lap_cols - set(ENRICH) - set(src))
    if unclassified:
        print(f"[WARN] unclassified laptop columns (add to ENRICH or they may be overwritten): {unclassified}")

    # schema/index upkeep must never abort the data sync (lock busy, connection drop, etc.).
    try:
        schema_sync(lcon, rcon, have, apply)
        if apply:
            ensure_updated_at_index(lcon, LTBL)                       # laptop: fast, own DB
            ensure_updated_at_index(rcon, RTBL, concurrently=True)    # raspibig: CONCURRENTLY, never block prod
    except psycopg2.Error as e:
        if rcon.closed:
            rcon = psycopg2.connect(**RAS)  # reconnect if the schema attempt dropped the connection
        else:
            rcon.rollback()
        print(f"[schema] non-fatal: {str(e).splitlines()[0]} -- continuing to data sync")
    sel = {a for a in sys.argv if a in ("pull", "push", "all")}
    do_pull = not sel or sel & {"pull", "all"}
    do_push = not sel or sel & {"push", "all"}
    if do_pull:
        pull(lcon, rcon, st, src, apply)
    if do_push:
        push(lcon, rcon, st, apply)
    if apply:
        save_state(st)
        print(f"[state] saved {st}")
    lcon.close()
    rcon.close()


if __name__ == "__main__":
    main()
