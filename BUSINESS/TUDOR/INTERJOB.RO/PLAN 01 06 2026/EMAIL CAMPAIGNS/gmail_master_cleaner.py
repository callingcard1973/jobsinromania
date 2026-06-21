#!/usr/bin/env python3
"""Clean the master Gmail inbox (manpowerdristor@gmail.com) — the only inbox Tudor reads.

Every office@<domain> forwards here, so this sees all campaigns. Classifies each INBOX
message and Gmail-archives the noise (label + remove \\Inbox; nothing deleted — stays in
All Mail), so the inbox shows ONLY employer/business leads:
  worker_application -> fw_candidates + label Workers + archive
  bounce             -> label Bounces + archive   (DNC handled by bounce_manager/bridge)
  opt_out            -> norway_dnc + label OptOuts + archive
  auto_reply         -> label AutoReplies + archive
  ignore (noise)     -> label Notifications + archive
  interested/neutral business -> KEEP in inbox (the leads)

DRY_RUN=1 reports counts without changing anything.
"""
import os, sys, imaplib, email, email.utils, re
sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS")
import universal_reply_handler as h
import psycopg2

USER = "manpowerdristor@gmail.com"
APP = h.env("MANPOWER_GMAIL_APP")   # from /opt/ACTIVE/EMAIL/CAMPAIGNS/.env (gitignored)
DRY = os.environ.get("DRY_RUN", "0") == "1"
ROLE = {"buildjobs.eu": "Construction", "careworkers.eu": "Care/Healthcare", "meatworkers.eu": "Meat processing",
        "warehouseworkers.eu": "Warehouse/Logistics", "horecaworkers.eu": "Hospitality", "mechanicjobs.eu": "Mechanic",
        "electricjobs.eu": "Electrician", "farmworkers.eu": "Agriculture", "factoryjobs.eu": "Factory"}
LABEL = {"worker_application": "Workers", "bounce": "Bounces", "opt_out": "OptOuts",
         "auto_reply": "AutoReplies", "ignore": "Notifications"}  # these get archived; leads stay


def body_of(msg):
    b = ""
    for p in (msg.walk() if msg.is_multipart() else [msg]):
        if p.get_content_type() == "text/plain":
            try: b += p.get_payload(decode=True).decode(errors="ignore")[:1500]
            except Exception: pass
    return b


def main():
    m = imaplib.IMAP4_SSL("imap.gmail.com", 993); m.login(USER, APP); m.select("INBOX")
    st, ids = m.search(None, "ALL"); ids = ids[0].split() if ids and ids[0] else []
    conn = psycopg2.connect(host="/var/run/postgresql", dbname="interjob_master", user="tudor"); cur = conn.cursor()
    counts = {}; cands = 0; kept = 0
    for i in ids:
        st, d = m.fetch(i, "(RFC822)")
        if not d or not d[0]: continue
        msg = email.message_from_bytes(d[0][1])
        name, frm = email.utils.parseaddr(h.dec(msg.get("From", ""))); frm = frm.lower().strip()
        subj = h.dec(msg.get("Subject", "")); body = body_of(msg)
        rt = h.classify(frm, subj, body)
        if rt in ("interested", "neutral"):   # leads -> keep in inbox
            kept += 1; counts[rt] = counts.get(rt, 0) + 1; continue
        counts[rt] = counts.get(rt, 0) + 1
        if DRY: continue
        # side-effects
        if rt == "worker_application" and "@" in frm:
            to_all = (msg.get("To", "") + " " + msg.get("Delivered-To", "") + " " + msg.get("Cc", "")).lower()
            role = next((r for dom, r in ROLE.items() if dom in to_all), "General")
            pm = re.search(r"(\+?\d[\d ().-]{7,}\d)", body); phone = pm.group(1).strip()[:30] if pm else ""
            cur.execute("INSERT INTO fw_candidates(name,email,phone,role,message,source,created_at) "
                        "SELECT %s,%s,%s,%s,%s,%s,now() WHERE NOT EXISTS(SELECT 1 FROM fw_candidates WHERE lower(email)=lower(%s))",
                        (name[:120] or frm.split("@")[0], frm, phone, role, (subj + " | " + body.strip().replace("\n", " "))[:500], "reply_worker", frm))
            cands += cur.rowcount
        if rt == "opt_out" and "@" in frm:
            cur.execute("INSERT INTO norway_dnc(email,reason,added_at) SELECT %s,'reply_opt_out',now() "
                        "WHERE NOT EXISTS(SELECT 1 FROM norway_dnc WHERE lower(email)=lower(%s))", (frm, frm))
        # Gmail: label for organization, then archive via \Deleted+EXPUNGE
        # (Gmail removes it from INBOX but keeps it in All Mail — verified safe, not a delete)
        lab = LABEL.get(rt, "Notifications")
        try:
            m.store(i, "+X-GM-LABELS", lab)
            m.store(i, "+FLAGS", "\\Deleted")
        except Exception as e:
            print("archive fail:", e, file=sys.stderr)
    if not DRY:
        m.expunge()   # one expunge archives all the \Deleted (noise) messages
    conn.commit(); m.logout(); conn.close()
    mode = "DRY-RUN (no changes)" if DRY else "APPLIED"
    print(f"Gmail master cleaner [{mode}]  scanned {len(ids)}")
    for k, v in sorted(counts.items()): print(f"  {k:20} {v}")
    print(f"  -> kept in inbox (leads): {kept} | new candidates: {cands}")


if __name__ == "__main__":
    main()
