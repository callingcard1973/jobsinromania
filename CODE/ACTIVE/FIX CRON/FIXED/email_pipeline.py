#!/usr/bin/env python3
"""Unified email pipeline: scan ALL mailboxes → classify → route to orders/applicants/contacts/dnc.
Replaces: collect_orders, reply_detector, reply_classifier, email_organizer, response_contacts.
Usage: python3 email_pipeline.py [--dry-run] [--reprocess] [--accounts gmail] [--no-llm]
"""
import imaplib, email, json, csv, os, sys, ssl, re, pickle, requests
from email.header import decode_header
from datetime import datetime, timezone
from pathlib import Path
from email_accounts import (ACCOUNTS, SKIP_SENDERS, SKIP_SUBJ, APPLICANT_SUBJ,
    APPLICANT_BODY, BOUNCE_SENDERS, BOUNCE_SUBJ, UNSUB_BODY, SKIP_BODY,
    HANDOVER_BODY, HANDOVER_EMAIL, PARTNER_SUBJ, PERSONAL_DOMAINS, BOUNCE_EMAIL_PATTERNS,
    COUNTRY_RULES, TLD_MAP)
try:
    from email_pipeline_db import (mark_replied, get_campaign_source, mark_bounced,
        alert_comanda, save_cv_attachment, track_skip, schedule_followup, log_metric,
        notify_translated_reply)
    DB_HOOKS = True
except Exception:
    DB_HOOKS = False

DIR = Path(__file__).parent
DATA_DIR = Path("/opt/ACTIVE/EMAIL/ORDERS")
STATE_F = DATA_DIR/"pipeline_state.json"
ORDERS_F, APPLICANTS_F, CONTACTS_F, HANDOVER_F = DATA_DIR/"orders.csv", DATA_DIR/"applicants.csv", DATA_DIR/"contacts.csv", DATA_DIR/"handovers.csv"
LOG_F, BOUNCE_LOG_F = DATA_DIR/"pipeline.log", DATA_DIR/"bounces.log"
_clf_candidates = [os.environ.get("CLF_PATH",""), "/opt/ACTIVE/EMAIL/ORDERS/models/email_classifier.pkl",
    "D:/MEMORY/IDEAS/LLM/models/email_classifier.pkl", str(DIR/"models/email_classifier.pkl")]
CLF_PATH = next((Path(p) for p in _clf_candidates if p and Path(p).exists()), Path("email_classifier.pkl"))
LLM_URL = os.environ.get("LLM_URL", "http://localhost:1234/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5-coder-1.5b-instruct")

ORDER_COLS = ["Timestamp","Clasificare","Denumire companie","Nume persoană de contact","Telefon",
    "Email","Localitate","Număr persoane","Tip poziții","Observații","Sursa","Account"]
APPL_COLS = ["Timestamp","Name","Email","Phone","Country","Language","Subject","Account"]
CONTACT_COLS = ["Timestamp","Name","Email","Phone","Company","Intent","Account"]
HANDOVER_COLS = ["Timestamp","Old Contact","Old Email","New Contact","New Email","Company","Account"]
DB_HOST = os.environ.get("PGHOST", "localhost")
DB_AVAILABLE = None

PROMPT = '''Extract JSON from email. Return ONLY valid JSON, nothing else.
{"type":"","company":"","contact":"","phone":"","location":"","workers":"","positions":"","notes":""}
type: COMANDA (needs workers now), INTERESAT (interested no firm order), PARTENER (agency offering workers), SKIP (not order).
Extract phone from signature. workers=number only.
SENDER: <<<S>>>  SUBJECT: <<<J>>>  EMAIL: <<<B>>>
JSON:'''

_clf = None
_llm = None  # None=uninitialised, True=ready, False=offline


def _init_llm():
    global _llm
    if _llm is not None:
        return
    if "--no-llm" in sys.argv:
        _llm = False
        return
    try:
        r = requests.post(LLM_URL, json={"model": LLM_MODEL,
            "messages": [{"role": "user", "content": "ok"}], "max_tokens": 3}, timeout=30)
        _llm = r.ok and "choices" in r.json()
    except Exception:
        _llm = False
    log(f"  LLM: {'ready' if _llm else 'offline'}")  

def log(m):
    l=f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {m}"
    try: print(l)
    except UnicodeEncodeError: print(l.encode("ascii",errors="replace").decode())
    open(LOG_F,"a",encoding="utf-8").write(l+"\n")

def classify(subj, body):
    global _clf
    if _clf is None:
        try: _clf = pickle.loads(CLF_PATH.read_bytes()); log("  Classifier loaded")
        except: _clf = {}; log("  No classifier")
    if not _clf or "intent" not in _clf: return "unknown"
    try: return _clf["intent"].predict([f"Subject: {subj}\n\n{body[:1000]}"])[0]
    except: return "unknown"

def llm_extract(body, sender, subj):
    _init_llm()
    if not _llm: return None
    p = PROMPT.replace("<<<B>>>",body[:3000]).replace("<<<S>>>",sender).replace("<<<J>>>",subj)
    try:
        r = requests.post(LLM_URL, json={"model":LLM_MODEL,"messages":[{"role":"user","content":p}],"temperature":0.1,"max_tokens":300,"repeat_penalty":1.1}, timeout=120)
        m = re.search(r"\{[^{}]*\}", r.json()["choices"][0]["message"]["content"], re.DOTALL)
        return json.loads(m.group()) if m else None
    except: return None

def decode_h(v):
    if not v: return ""
    try: return " ".join(p.decode(c or "utf-8",errors="replace") if isinstance(p,bytes) else p for p,c in decode_header(v))
    except: return str(v)

def _dp(p):
    pl=p.get_payload(decode=True)
    return pl.decode(p.get_content_charset() or "utf-8",errors="replace") if pl else None

def get_body(msg):
    if msg.is_multipart():
        for ct in ["text/plain","text/html"]:
            for p in msg.walk():
                if p.get_content_type()==ct:
                    t=_dp(p)
                    if t: return re.sub(r"<[^>]+>","",t) if ct=="text/html" else t
    t=_dp(msg)
    return t or ""

def get_email(frm):
    m=re.search(r"<([^>]+)>",frm) or re.search(r"[\w.+-]+@[\w-]+\.[\w.]+",frm)
    if not m: return ""
    return (m.group(1) if m.group().startswith("<") else m.group()).lower()

def get_phone(body):
    ph = re.findall(r"(?:\+?\d[\d\s\-]{8,15})", body[:1500])
    return ph[0].strip() if ph else ""

def get_name(frm): return re.sub(r"<[^>]+>","",frm).strip().strip('"').strip()

def append_csv(path, cols, row):
    ex = path.exists()
    with open(path,"a",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=cols)
        if not ex: w.writeheader()
        w.writerow(row)

def save_order(ext, se, frm, subj, intent, acct, dry):
    t = ext.get("type","").upper()
    clf = t if t in ("COMANDA","INTERESAT","PARTENER") else "DE VERIFICAT"
    row = {"Timestamp":f"{datetime.now():%d/%m/%Y %H:%M:%S}","Clasificare":clf,
        "Denumire companie":ext.get("company",""),"Nume persoană de contact":ext.get("contact",""),
        "Telefon":ext.get("phone",""),"Email":ext.get("email","") or se,
        "Localitate":ext.get("location",""),"Număr persoane":ext.get("workers",""),
        "Tip poziții":ext.get("positions",""),"Observații":ext.get("notes",""),
        "Sursa":f"[{intent}]","Account":acct}
    if not dry: append_csv(ORDERS_F, ORDER_COLS, row)
    log(f"    -> {'[DRY]' if dry else 'ORDER'} [{clf}] {row['Denumire companie']} | {row['Număr persoane']} pax")


def detect_country(se, subj, body):
    text = f"{subj} {body[:800]} {se}"
    for code, pat in COUNTRY_RULES:
        if re.search(pat, text, re.I): return code
    m = re.search(r"@[\w.-]+\.([a-z]{2})$", se)
    if m and m.group(1) in TLD_MAP: return TLD_MAP[m.group(1)]
    return ""

def detect_lang(body):
    for l,p in [("AR", r"[؀-ۿ]"), ("RO", r"[ăîșț]"),
                ("CZ", r"[čďěňřšťůž]"),
                ("FR", r"[àèêëïùûüÿç]")]:
        if re.search(p, body[:200]): return l
    return "EN"
def save_applicant(se, frm, subj, body, acct, dry):
    row = {"Timestamp":f"{datetime.now():%d/%m/%Y %H:%M:%S}","Name":get_name(frm),
        "Email":se,"Phone":get_phone(body),"Country":detect_country(se,subj,body),
        "Language":detect_lang(body),"Subject":subj[:100],"Account":acct}
    if not dry: append_csv(APPLICANTS_F, APPL_COLS, row)
    log(f"    -> {'[DRY]' if dry else 'APPLICANT'} {se} ({row['Country']})")
def save_contact(se, frm, body, intent, acct, dry):
    if not dry: append_csv(CONTACTS_F, CONTACT_COLS, {"Timestamp":f"{datetime.now():%d/%m/%Y %H:%M:%S}",
        "Name":get_name(frm),"Email":se,"Phone":get_phone(body),"Company":"","Intent":intent,"Account":acct})

def save_handover(se, frm, body, acct, dry):
    m = HANDOVER_EMAIL.search(body[:1500])
    if not m: return False
    nn, ne = m.group(1).strip(), m.group(2).strip().lower()
    row = {"Timestamp":f"{datetime.now():%d/%m/%Y %H:%M:%S}","Old Contact":get_name(frm),
        "Old Email":se,"New Contact":nn,"New Email":ne,"Company":"","Account":acct}
    if not dry: append_csv(HANDOVER_F, HANDOVER_COLS, row)
    save_contact(ne, f"{nn} <{ne}>", body, "handover-new", acct, dry)
    log(f"    -> {'[DRY]' if dry else 'HANDOVER'} {se} -> {nn} <{ne}>")
    return True

def save_dnc(addr, reason, acct, dry):
    open(BOUNCE_LOG_F,"a",encoding="utf-8").write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {reason:15s} | {addr:40s} | {acct}\n")
    if dry: return
    global DB_AVAILABLE
    if DB_AVAILABLE is None:
        try: import psycopg2; DB_AVAILABLE = True
        except ImportError: DB_AVAILABLE = False
    if not DB_AVAILABLE: return
    import psycopg2
    for db, sql in [("interjob_master","INSERT INTO dnc_list(email,reason) VALUES(%s,%s) ON CONFLICT(email) DO NOTHING"),
        ("email_sender","INSERT INTO dnc_emails(email,reason,source) VALUES(%s,%s,'email_pipeline') ON CONFLICT(email) DO NOTHING")]:
        try:
            c=psycopg2.connect(host=DB_HOST,database=db,user="tudor",password="REDACTED"); cur=c.cursor()
            cur.execute(sql,(addr,reason)); c.commit(); cur.close(); c.close()
        except: pass

def extract_bounced_email(body):
    """Extract the failed recipient email from a bounce message."""
    for pat in BOUNCE_EMAIL_PATTERNS:
        m = re.search(pat, body, re.I)
        if m: return m.group(1).lower().strip("<>. ")
    return None

def process(acct_filter, state, dry):
    processed = set(state.get("processed",[]))
    accounts = ACCOUNTS
    if acct_filter:
        accounts = [a for a in ACCOUNTS if acct_filter in a[0] or acct_filter in a[3]]
    stats = {"orders":0,"applicants":0,"contacts":0,"dnc":0,"skipped":0}
    def _persist_state():
        if not dry:
            state["processed"] = list(processed)
            try: STATE_F.write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding="utf-8")
            except Exception: pass
    for em, pw, srv, label in accounts:
        log(f"Scanning {label} ({em})...")
        prev = dict(stats)
        try:
            imap = imaplib.IMAP4_SSL(srv, 993, ssl_context=ssl.create_default_context())
            imap.login(em, pw)
        except Exception as e: log(f"  FAIL: {e}"); continue
        imap.select("INBOX", readonly=dry)
        _, ids = imap.search(None, '(SINCE "01-Jan-2025")')
        if not ids[0]: imap.logout(); continue
        all_ids = ids[0].split()
        to_delete = []
        for mid in all_ids:
            try:
                _, hd = imap.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT MESSAGE-ID)])")
                hm = email.message_from_bytes(hd[0][1])
            except Exception as exc:
                log(f"  fetch fail {mid}: {exc}"); continue
            msgid = hm.get("Message-ID", mid.decode())
            if msgid in processed: continue
            frm, subj = decode_h(hm.get("From","")), decode_h(hm.get("Subject",""))
            se = get_email(frm)
            if any(s in se.lower() for s in SKIP_SENDERS) or SKIP_SUBJ.search(subj):
                stats["skipped"]+=1
                if not dry: processed.add(msgid)
                continue
            # Bounce: extract failed email, DNC if personal, delete bounce msg
            if BOUNCE_SENDERS.search(frm) or BOUNCE_SUBJ.search(subj):
                _, fd = imap.fetch(mid, "(RFC822)")
                bbody = get_body(email.message_from_bytes(fd[0][1]))
                bounced = extract_bounced_email(bbody)
                if bounced and bounced.endswith(PERSONAL_DOMAINS):
                    save_dnc(bounced, "non-existent", label, dry); stats["dnc"]+=1
                    to_delete.append(mid)
                    if DB_HOOKS and not dry: mark_bounced(bounced)
                elif bounced:
                    if DB_HOOKS and not dry: mark_bounced(bounced)
                    stats["skipped"]+=1
                else:
                    stats["skipped"]+=1
                if not dry: processed.add(msgid)
                continue
            _, fd = imap.fetch(mid, "(RFC822)")
            full_msg = email.message_from_bytes(fd[0][1])
            body = get_body(full_msg)
            if not body.strip():
                if not dry: processed.add(msgid)
                continue
            # Route
            if UNSUB_BODY.search(body[:500]):
                save_dnc(se, "unsubscribe", label, dry); stats["dnc"]+=1
                if DB_HOOKS and not dry: mark_replied(se, "unsubscribed")
            elif HANDOVER_BODY.search(body[:800]):
                if save_handover(se, frm, body, label, dry):
                    stats["contacts"]+=1
                    if DB_HOOKS and not dry: mark_replied(se, "handover")
                else: stats["skipped"]+=1
            elif SKIP_BODY.search(body[:800]):
                save_contact(se, frm, body, "skip-notinterested", label, dry); stats["skipped"]+=1
                if DB_HOOKS and not dry:
                    mark_replied(se, "not_interested"); track_skip(se)
            elif PARTNER_SUBJ.search(subj):
                save_contact(se, frm, body, "partner-reply", label, dry); stats["contacts"]+=1
                if DB_HOOKS and not dry: mark_replied(se, "partner")
            elif APPLICANT_SUBJ.search(subj) or APPLICANT_BODY.search(body[:1500]) or \
                 (classify(subj,body)=="application" and se.endswith(PERSONAL_DOMAINS)):
                save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1
                if DB_HOOKS and not dry:
                    country = detect_country(se, subj, body)
                    cvs = save_cv_attachment(full_msg, se, country)
                    if cvs: log(f"    CV: {len(cvs)} saved")
                    mark_replied(se, "applicant"); notify_translated_reply("APPLICANT", se, subj, body, detect_lang(body), label)
            else:
                intent = classify(subj, body)
                if intent in ("campaign_reply","inquiry","unknown"):
                    ext = llm_extract(body, frm, subj)
                    if ext and ext.get("type","").upper()!="SKIP":
                        save_order(ext, se, frm, subj, intent, label, dry); stats["orders"]+=1
                        save_contact(se, frm, body, intent, label, dry); stats["contacts"]+=1
                        if DB_HOOKS and not dry:
                            t = ext.get("type","").upper()
                            camp = get_campaign_source(se)
                            mark_replied(se, t.lower() if t in ("COMANDA","INTERESAT","PARTENER") else "reply")
                            lang = detect_lang(body)
                            notify_translated_reply(t, se, subj, body, lang, label)
                            if t == "COMANDA": alert_comanda(ext, se, subj, label, camp, lang, body)
                            elif t == "INTERESAT": schedule_followup(se, days=3, classification="INTERESAT", campaign=camp)
                    elif not ext:
                        save_contact(se, frm, body, intent, label, dry); stats["contacts"]+=1
                        if DB_HOOKS and not dry: mark_replied(se, "reply")
                else:
                    stats["skipped"]+=1
            if not dry: processed.add(msgid)
        # Delete bounce messages for non-existent personal emails
        if to_delete and not dry:
            try:
                for mid in to_delete: imap.store(mid, '+FLAGS', '\\Deleted')
                imap.expunge()
            except Exception as exc: log(f"  expunge fail: {exc}")
        try: imap.logout()
        except Exception: pass
        log(f"  {label}: done")
        if DB_HOOKS and not dry:
            diff = {k: stats[k]-prev[k] for k in stats}
            log_metric(label, diff)
        _persist_state()
    _persist_state()
    return stats

def main():
    dry, reprocess = "--dry-run" in sys.argv, "--reprocess" in sys.argv
    af = sys.argv[sys.argv.index("--accounts")+1] if "--accounts" in sys.argv else None
    log("="*50+f"\nPipeline {'(DRY)' if dry else ''} {af or 'ALL'}")
    _init_llm()
    state = json.loads(STATE_F.read_text(encoding="utf-8")) if STATE_F.exists() and not reprocess else {"processed":[]}
    stats = process(af, state, dry)
    if not dry:
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE_F.write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding="utf-8")
    log(f"Done: {stats}")

if __name__ == "__main__": main()
