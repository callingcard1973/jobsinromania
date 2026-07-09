#!/usr/bin/env python3
"""End-to-end proof of delta_sync: insert a test row on raspibig, pull it to laptop,
enrich it on laptop, push back to raspibig, verify both directions, then clean up.
Uses the REAL pull()/push() functions. Push tested with lead_score (exists on raspibig);
the full multi-column push is identical SQL, gated only on the 13 columns landing."""
import psycopg2
import datetime
import delta_sync as ds

TID = 999999999  # sentinel test id, well above the real max (215,695,536)
lc = psycopg2.connect(**ds.LAP)
rc = psycopg2.connect(**ds.RAS)


def q(con, sql, args=None):
    c = con.cursor(); c.execute(sql, args or ()); return c.fetchone()


def cleanup():
    rc.cursor().execute("DELETE FROM public.companies WHERE id=%s", (TID,)); rc.commit()
    lc.cursor().execute("DELETE FROM companies_clean WHERE id=%s", (TID,)); lc.commit()


cleanup()  # start clean
fails = []

# watermark "now" so ONLY the test row qualifies (a '1970' ts would match all 40M rows via the OR clause)
t0 = datetime.datetime.now()

# 1. insert test row on raspibig
rc.cursor().execute("INSERT INTO public.companies (id, name, country, updated_at) VALUES (%s,%s,%s,%s)",
                    (TID, "__DELTA_SYNC_TEST__", "XX", datetime.datetime.now())); rc.commit()
print(f"[setup] inserted test row id={TID} on raspibig")

# 2. PULL proof: real pull() should bring it to the laptop
st = {"last_pull_id": TID - 1, "last_pull_ts": str(t0), "last_push_ts": str(t0)}
have = set(ds.cols(rc, ds.RTBL))
src = [c for c in have if c in set(ds.cols(lc, ds.LTBL)) and c not in ds.ENRICH]
ds.pull(lc, rc, st, src, apply=True)
row = q(lc, "SELECT name FROM companies_clean WHERE id=%s", (TID,))
print(f"[PULL] laptop now has test row: {row}")
fails.append("PULL") if not row or row[0] != "__DELTA_SYNC_TEST__" else print("[PULL] PASS")

# 3. enrich on laptop, then PUSH proof (lead_score only -> exists on raspibig)
t1 = datetime.datetime.now()  # push watermark "now" so only the test row's enrichment qualifies
lc.cursor().execute("UPDATE companies_clean SET lead_score=7777, updated_at=%s WHERE id=%s",
                    (datetime.datetime.now(), TID)); lc.commit()
ds.ENRICH = ["lead_score"]  # restrict push to a column that exists on raspibig today
st["last_push_ts"] = str(t1)
ds.push(lc, rc, st, apply=True)
back = q(rc, "SELECT lead_score FROM public.companies WHERE id=%s", (TID,))
print(f"[PUSH] raspibig test row lead_score: {back}")
fails.append("PUSH") if not back or back[0] != 7777 else print("[PUSH] PASS")

cleanup()
print("[cleanup] test row removed both sides")
print("=== RESULT:", "ALL PASS" if not fails else f"FAILED {fails}", "===")
