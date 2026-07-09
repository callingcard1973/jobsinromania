#!/usr/bin/env python3
"""Integration test: opt-out (norway_dnc) and bounce/send (norway_send_log) actually
SUPPRESS a contact in the real send_norway.get_contacts() path. Closes the compliance
loop — proves a STOP'd or already-sent/bounced address is never re-sent.

Self-contained: inserts a sentinel into norway_campaign, asserts exclusion, cleans up."""
import sys
import pytest
sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS/NORWAY")
# Norway-harness integration test: needs send_norway + live DB (only on raspibig).
# Skip collection cleanly off-host instead of erroring the whole test run.
s = pytest.importorskip("send_norway")

EMAIL = "zz-suppression-test@example-sentinel.no"


def _exec(sql, args=()):
    conn = s.get_db(); cur = conn.cursor()
    cur.execute(sql, args); conn.commit(); conn.close()


def _cleanup():
    for t in ("norway_campaign", "norway_dnc", "norway_send_log"):
        _exec(f"DELETE FROM {t} WHERE lower(email)=lower(%s)", (EMAIL,))


def present():
    # sentinel has max employees_count so it's #1 in get_contacts ordering -> always in top-5 unless suppressed
    rows = s.get_contacts("CONSTRUCTION", 5)
    return any((r.get("email") or "").lower() == EMAIL.lower() for r in rows)


def main():
    _cleanup()
    _exec("INSERT INTO norway_campaign(name,email,sector,sector_name,employees_count,campaign_status,tier,org_number,source) "
          "VALUES('Suppression Test',%s,'41.000','Test',99999999,'pending','T2','TEST','test')", (EMAIL,))
    r_base = present()                                   # expect True (eligible)
    _exec("INSERT INTO norway_dnc(email,reason,added_at) VALUES(%s,'test',now())", (EMAIL,))
    r_dnc = present()                                    # expect False (DNC excludes)
    _exec("DELETE FROM norway_dnc WHERE lower(email)=lower(%s)", (EMAIL,))
    _exec("INSERT INTO norway_send_log(email,company,campaign,status,sent_at) "
          "VALUES(%s,'t','NORWAY_CONSTRUCTION','sent',now())", (EMAIL,))
    r_log = present()                                    # expect False (send-log excludes)
    _cleanup()

    print(f"baseline eligible : {r_base}  (expect True)")
    print(f"after norway_dnc  : {r_dnc}   (expect False)")
    print(f"after send_log    : {r_log}   (expect False)")
    ok = r_base and (not r_dnc) and (not r_log)
    print("SUPPRESSION:", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
