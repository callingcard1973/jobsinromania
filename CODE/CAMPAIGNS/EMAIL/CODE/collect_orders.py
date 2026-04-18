#!/usr/bin/env python3
"""Order Collector: Gmail → sklearn → LLM → orders.csv. Usage: [--dry-run] [--reprocess]"""
import imaplib, email, json, csv, os, sys, ssl, re, pickle, requests
from email.header import decode_header
from datetime import datetime, timezone
from pathlib import Path

DIR = Path(__file__).parent
STATE_F, CSV_F, LOG_F = DIR/"orders_state.json", DIR/"orders.csv", DIR/"orders_collector.log"
APPLICANTS_CSV = DIR/"applicants.csv"
CLF_PATH = Path("D:/MEMORY/IDEAS/LLM/models/email_classifier.pkl")
LLM_URL = os.environ.get("LLM_URL", "http://localhost:1234/v1/chat/completions")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen2.5-coder-1.5b-instruct")

ACCOUNTS = [
    {"email":"manpower.dristor@gmail.com","password":"tbdh pycf vbxo eung","server":"imap.gmail.com"},
    {"email":"elena.manpower.dristor@gmail.com","password":"wmfnpikkcierkmrq","server":"imap.gmail.com"},
]
COLS = ["Timestamp","Name Responsabil Proiect","Localitate / Județ / Locația de lucru","Address",
    "Nume persoană de contact","Funcție (HR / Admin / Manager etc.)","Date companie",
    "Denumire companie","CUI / CIF","Telefon","Email","Număr persoane necesare","Tip poziții",
    "Gen preferat","Interval vârstă","Tip contract","Când doriți să înceapă?",
    "Condiții cazare","Salariu / beneficii","Observații","Sursa","Message-ID","From Email"]

APPL_COLS = ["Timestamp","Name","Email","Phone","Country","Positions","Language","Subject","Account"]

SKIP_SENDERS = {"elena.manpower.dristor@gmail.com","manpower.dristor@gmail.com",
    "manpowerdristor@gmail.com","noreply@interjob.ro","elena@interjob.ro","office@interjob.ro",
    "tudor@interjob.ro","office@seicarescu.com","office@mivromania.info","mailer-daemon@",
    "noreply@","no-reply@","notifications@","newsletter@","@brevosend.com","@t.brevo.com",
    "account-alerts@","@supabase.com","@zohomail.com","@zohocorp.com","transport.work@",
    "workers.europe@","@jobteam.dk","support@contactsplus.com","@5099400.brevosend.com"}
SKIP_SUBJ = re.compile(r"(out of office|autoreply|automatic reply|automatische antwort|auto response|"
    r"delivery.*(fail|status)|undeliver|vacation|campaign alert|stalled campaign|smtp test|"
    r"security alert|verify a new ip|welcome to brevo|new smtp key|getting started|"
    r"has been paused|going to be paused|thank you for your message)", re.I)
SKIP_APPLICANT = re.compile(r"(job application|application for|job search|farm worker position|"
    r"hotel job|seeking.*employment|ans.gning|looking for.*work|looking for.*job|"
    r"candidature|bewerbung|candidatura|disponible pour|dispo.*saison|"
    r"i am.*looking|my name is.*from|je me permets|cherche.*emploi|"
    r"apply.*position|request for.*job|interested in.*working)", re.I)
# Body patterns for applicants that slip past subject filter
APPLICANT_BODY = re.compile(r"(attached my cv|my resume|i am looking for.{0,30}(job|work|employ)|"
    r"je suis.*motivé.*poste|available for work.*immediately|ready to start immediately|"
    r"zájem o.*práci|chtěla bych se.*zeptat|"
    r"i am \d+ years old.{0,50}(looking|work|job)|"
    r"i want to work|seasonal.*farm.*work|saisonnier.{0,30}logement|"
    r"please.*find my.*cv|cv.*attached|resume.*enclosed|"
    r"je me permets de vous adresser ma candidature)", re.I)

def save_applicant(se, frm, subj, body, acct):
    """Save job applicant to applicants.csv."""
    if not APPLICANTS_CSV.exists():
        with open(APPLICANTS_CSV,"w",newline="",encoding="utf-8-sig") as f:
            csv.DictWriter(f,fieldnames=APPL_COLS).writeheader()
    name = re.sub(r"<[^>]+>","",frm).strip().strip('"')
    ph = re.findall(r"(?:\+?\d[\d\s\-]{8,15})", body[:1000])
    phone = ph[0].strip() if ph else ""
    country, lang = "", "EN"
    for c,pat in [("Morocco","maroc|morocco"),("Nigeria","nigeria|lagos"),("Nepal","nepal"),
        ("India","india"),("Czech","czech|cz$"),("France","français"),("Sri Lanka","sri lanka"),
        ("Bangladesh","bangladesh")]:
        if re.search(pat, body[:500]+se, re.I): country = c; break
    if re.search(r"[àâéèêëïîôùûüÿç]",body[:200]): lang="FR"
    elif re.search(r"[áčďéěíňóřšťúůýž]",body[:200]): lang="CZ"
    elif re.search(r"[ăâîșț]",body[:200]): lang="RO"
    row = {"Timestamp":datetime.now().strftime("%d/%m/%Y %H:%M:%S"),"Name":name,
        "Email":se,"Phone":phone,"Country":country,"Positions":subj[:100],
        "Language":lang,"Subject":subj[:100],"Account":acct}
    with open(APPLICANTS_CSV,"a",newline="",encoding="utf-8-sig") as f:
        csv.DictWriter(f,fieldnames=APPL_COLS).writerow(row)

PROMPT = '''Extract JSON from email. Return ONLY valid JSON, nothing else.
{"type":"","company":"","contact":"","phone":"","location":"","workers":"","positions":"","notes":""}
type must be one of: COMANDA (employer needs workers now), INTERESAT (employer interested but no firm order), PARTENER (recruitment agency offering workers), SKIP (not an order).
Extract phone from signature. workers=number only.
SENDER: <<<SENDER>>>
SUBJECT: <<<SUBJECT>>>
EMAIL: <<<BODY>>>
JSON:'''

# --- Helpers ---
_clf, _llm_ok = None, None

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try: print(line)
    except UnicodeEncodeError: print(line.encode("ascii",errors="replace").decode())
    with open(LOG_F,"a",encoding="utf-8") as f: f.write(line+"\n")

def classify(subj, body):
    global _clf
    if _clf is None:
        if CLF_PATH.exists():
            try:
                with open(CLF_PATH,"rb") as f: _clf = pickle.load(f)
                log(f"  Classifier loaded")
            except: _clf = {}
        else: _clf = {}
    if not _clf or "intent" not in _clf: return "unknown","normal"
    txt = f"Subject: {subj}\n\n{body[:1000]}"
    try: return _clf["intent"].predict([txt])[0], _clf["priority"].predict([txt])[0]
    except: return "unknown","normal"

def llm_extract(body, sender, subject):
    global _llm_ok
    if _llm_ok is None:
        try:
            r = requests.post(LLM_URL, json={"model":LLM_MODEL,"messages":[{"role":"user","content":"say ok"}],"max_tokens":5}, timeout=30)
            _llm_ok = r.ok and "choices" in r.json()
            if _llm_ok: log(f"  LLM available: {LLM_MODEL}")
            else: log("  LLM: test failed, regex fallback")
        except: _llm_ok = False; log("  LLM: not reachable, regex fallback")
    if not _llm_ok: return None
    prompt = PROMPT.replace("<<<BODY>>>",body[:800]).replace("<<<SENDER>>>",sender).replace("<<<SUBJECT>>>",subject)
    try:
        r = requests.post(LLM_URL, json={"model":LLM_MODEL,"messages":[{"role":"user","content":prompt}],"temperature":0.1,"max_tokens":150}, timeout=120)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        m = re.search(r"\{[^{}]*\}", content, re.DOTALL)
        return json.loads(m.group()) if m else json.loads(content)
    except Exception as e: log(f"  LLM fail: {e}"); return None

def regex_extract(body, sender):
    d = {k:"" for k in ["company","contact","phone","location","workers","positions","notes"]}
    em = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", sender)
    if em: d["email"] = em.group()
    ph = re.findall(r"(?:\+?\d[\d\s\-]{8,15})", body)
    if ph: d["phone"] = ph[0].strip()
    nr = re.search(r"(\d+)\s*(?:persoane|muncitori|workers|oameni)", body, re.I)
    if nr: d["workers"] = nr.group(1)
    d["notes"] = "REGEX FALLBACK"
    return d

def decode_h(v):
    if not v: return ""
    parts = decode_header(v)
    return " ".join(p.decode(c or "utf-8",errors="replace") if isinstance(p,bytes) else p for p,c in parts)

def get_body(msg):
    if msg.is_multipart():
        for p in msg.walk():
            if p.get_content_type()=="text/plain":
                pl = p.get_payload(decode=True)
                if pl: return pl.decode(p.get_content_charset() or "utf-8",errors="replace")
        for p in msg.walk():
            if p.get_content_type()=="text/html":
                pl = p.get_payload(decode=True)
                if pl:
                    h = pl.decode(p.get_content_charset() or "utf-8",errors="replace")
                    return re.sub(r"<[^>]+>","",re.sub(r"<br\s*/?>","\n",h,flags=re.I))
    else:
        pl = msg.get_payload(decode=True)
        if pl: return pl.decode(msg.get_content_charset() or "utf-8",errors="replace")
    return ""

def sender_email(frm):
    m = re.search(r"<([^>]+)>", frm)
    if m: return m.group(1).lower()
    m = re.search(r"[\w.+-]+@[\w-]+\.[\w.]+", frm)
    return m.group().lower() if m else frm.lower()

def should_skip(s):
    return any(skip in s.lower() for skip in SKIP_SENDERS)

# --- Main ---
def process_account(acct, state, dry_run):
    orders, processed = [], set(state.get("processed",[]))
    log(f"Connecting to {acct['email']}...")
    try:
        imap = imaplib.IMAP4_SSL(acct["server"], 993, ssl_context=ssl.create_default_context())
        imap.login(acct["email"], acct["password"])
    except Exception as e: log(f"  Login failed: {e}"); return orders
    imap.select("INBOX", readonly=True)
    _, ids = imap.search(None, '(SINCE "01-Jan-2025")')
    if not ids[0]: imap.logout(); return orders
    all_ids = ids[0].split()
    log(f"  {len(all_ids)} messages")
    new_c, skip_c = 0, 0
    for mid in all_ids:
        _, hd = imap.fetch(mid, "(BODY[HEADER.FIELDS (FROM SUBJECT MESSAGE-ID)])")
        hm = email.message_from_bytes(hd[0][1])
        msgid = hm.get("Message-ID", mid.decode())
        if msgid in processed: continue
        frm, subj = decode_h(hm.get("From","")), decode_h(hm.get("Subject",""))
        se = sender_email(frm)
        if should_skip(se) or SKIP_SUBJ.search(subj):
            skip_c += 1; processed.add(msgid) if not dry_run else None; continue
        is_applicant_subj = bool(SKIP_APPLICANT.search(subj))
        _, fd = imap.fetch(mid, "(RFC822)")
        body = get_body(email.message_from_bytes(fd[0][1]))
        if not body.strip(): processed.add(msgid) if not dry_run else None; continue
        is_applicant_body = bool(APPLICANT_BODY.search(body[:1500]))
        intent, _ = classify(subj, body)
        # Applicant = subject/body regex match, or classifier says application AND from personal email
        is_personal = se.endswith(("@gmail.com","@yahoo.com","@hotmail.com","@outlook.com","@email.cz","@mail.ru"))
        is_applicant = is_applicant_subj or is_applicant_body or (intent == "application" and is_personal)
        if is_applicant:
            save_applicant(se, frm, subj, body, acct["email"])
            skip_c += 1; processed.add(msgid) if not dry_run else None; continue
        if intent not in ("campaign_reply","inquiry","unknown","application"):
            skip_c += 1; processed.add(msgid) if not dry_run else None; continue
        log(f"  [{intent}] {se} | {subj[:50]}")
        ext = llm_extract(body, frm, subj) or regex_extract(body, frm)
        etype = ext.get("type","").upper()
        notes = ext.get("notes","")
        if etype == "SKIP" or "SKIP" in notes.upper():
            log(f"    -> Skip (not order)"); processed.add(msgid) if not dry_run else None; continue
        clasificare = etype if etype in ("COMANDA","INTERESAT","PARTENER") else "DE VERIFICAT"
        row = {"Timestamp":datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "Localitate / Județ / Locația de lucru":ext.get("location",""),
            "Nume persoană de contact":ext.get("contact",""),
            "Denumire companie":ext.get("company",""),
            "Telefon":ext.get("phone",""), "Email":ext.get("email","") or se,
            "Număr persoane necesare":ext.get("workers",""),
            "Tip poziții":ext.get("positions",""),
            "Observații":f"[{clasificare}] {notes}", "Sursa":acct["email"],
            "Message-ID":msgid, "From Email":se}
        for c in COLS:
            if c not in row: row[c] = ""
        orders.append(row); new_c += 1
        if not dry_run:
            with open(CSV_F,"a",newline="",encoding="utf-8-sig") as f:
                csv.DictWriter(f,fieldnames=COLS).writerow(row)
        tag = "[DRY]" if dry_run else "SAVED"
        log(f"    -> {tag} [{clasificare}]: {row['Denumire companie']} | {row['Număr persoane necesare']} pax | {row['Tip poziții']}")
        processed.add(msgid) if not dry_run else None
    imap.logout()
    if not dry_run: state["processed"] = list(processed)
    log(f"  {acct['email']}: {new_c} orders, {skip_c} skipped")
    return orders

def main():
    dry_run, reprocess = "--dry-run" in sys.argv, "--reprocess" in sys.argv
    log("="*60 + f"\nOrder Collector {'(DRY RUN)' if dry_run else ''}")
    state = json.loads(STATE_F.read_text(encoding="utf-8")) if STATE_F.exists() and not reprocess else {"processed":[]}
    if not CSV_F.exists():
        with open(CSV_F,"w",newline="",encoding="utf-8-sig") as f:
            csv.DictWriter(f,fieldnames=COLS).writeheader()
    total = []
    for acct in ACCOUNTS:
        total.extend(process_account(acct, state, dry_run))
    if not dry_run:
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE_F.write_text(json.dumps(state,indent=2,ensure_ascii=False),encoding="utf-8")
    log(f"Done. {len(total)} orders.\n" + "="*60)

if __name__ == "__main__":
    main()
