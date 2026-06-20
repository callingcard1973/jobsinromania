#!/usr/bin/env python3
"""Universal reply handler — all office@<domain> inboxes.

Classifies replies, auto-adds opt-outs to the shared DNC (compliance across the whole
domain portfolio), auto-replies job-seekers with the apply link (recruitment domains that
have a Brevo key), and surfaces business-domain leads in a digest. Bounces are handled
separately by bounce_manager.py (universal-bounce-monitor, every 7min)."""
import json, imaplib, email, email.utils, os, re, sys, hashlib, requests, psycopg2
from email.header import decode_header
from datetime import datetime, timedelta

CRED="/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json"
STATE="/opt/ACTIVE/EMAIL/CAMPAIGNS/state/universal_reply_seen.json"
WR_STATE="/opt/ACTIVE/EMAIL/CAMPAIGNS/state/universal_worker_replied.json"
DNC_CSV="/opt/ACTIVE/EMAIL/CAMPAIGNS/dnc_list.csv"
WORKER_TPL="/opt/ACTIVE/EMAIL/CAMPAIGNS/NORWAY/templates/worker_autoreply.txt"
ALERT_TO="fruitnature4@gmail.com"

_ENV=None
def env(k):
    global _ENV
    if _ENV is None:
        _ENV={}
        for ln in open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env"):
            if "=" in ln and not ln.lstrip().startswith("#"):
                kk,_,vv=ln.partition("="); _ENV[kk.strip()]=vv.strip()
    return _ENV.get(k,"")

# A domain can send a worker auto-reply iff it has a BREVO_<NAME>_API_KEY in .env
def brevo_key(dom):
    return env("BREVO_"+dom.split(".")[0].upper().replace("-","")+"_API_KEY")

SKIP={"nepalezi.com","mivromania.info","mivromania.online","mivromania.com"}  # dead/expiring

def load_set(path):
    try: return set(json.load(open(path)))
    except Exception: return set()  # missing/corrupt -> start clean, never crash

def save_set(path,s):
    tmp=path+".tmp"; json.dump(list(s),open(tmp,"w")); os.replace(tmp,path)  # atomic

OPTOUT=("unsubscribe","dezabonare","please remove","remove me","take me off","do not contact","do not email","stop sending","stop emailing","nu ma mai","nu mă mai","scoateti-ma","scoateți-mă","radiati-ma")
BOUNCE=("mailer-daemon","postmaster","delivery failed","delivery status","undeliverable","mail delivery","user unknown","mailbox full","550 ","not found","recipient")
AUTO=("out of office","automatic reply","autosvar","fraver","thank you for your message","ute av kontoret","vil bli besvart","concediu","odihna","tack for din ansok")
TICKET=("ticket received","ticket closed","nytt arende","arende skapat","case #","sak #","ref:")
WORKER=("applying for","apply for","looking for job","looking for work","i have experience","ready to join","visa procedure","my cv","attached cv","jobb som","i am a ","seeking employment","interested in applying")
INTEREST=("send profiles","send rates","send your","interested in your","need workers","need crew","looking for crew","tilbud","prosjekt i","kontakt oss","please call","price per","how much","more details","send details","send catalog","send me")
IGNORE_FROM=("noreply","no-reply","mailer-daemon","postmaster","@system.","freshservice","zohomail.eu","workers.europe","e-conomic","notifications@","m.brevo.com","@brevo.com","t.brevo.com","wordpress@","@customeriotest")
FREE={"gmail.com","yahoo.com","hotmail.com","outlook.com","live.com","icloud.com","me.com","aol.com","yahoo.co.uk","proton.me","protonmail.com"}

def dec(s):
    if not s: return ""
    out=[]
    for p,c in decode_header(s):
        if isinstance(p,bytes):
            try: out.append(p.decode(c or "utf-8","ignore"))
            except LookupError: out.append(p.decode("utf-8","ignore"))
        else: out.append(p)
    return "".join(out)

# Cut the quoted/original portion so we classify only the new reply text.
QMARK=[re.compile(p, re.IGNORECASE) for p in (
    r"\nOn .{0,80} wrote:", r"\n-----+ ?Original Message", r"\n_{5,}",
    r"\nFrom:.{0,200}\nSent:", r"\nDen .{0,80} skrev:", r"\nLe .{0,80} a .{0,5}crit",
    r"\n>", r"\nTo stop receiving emails", r"\nreply STOP",
    r"\n(Best regards|Kind regards|Med vennlig hilsen|Cu stima|Mvh)\b")]
def strip_quotes(body):
    cut=len(body)
    for m in QMARK:
        x=m.search(body)
        if x and x.start()<cut: cut=x.start()
    return body[:cut]

def classify(frm,subj,body):
    body=strip_quotes(body)
    fl=frm.lower(); t=(subj+" "+body).lower()
    if any(k in fl for k in IGNORE_FROM): return "ignore"
    if any(k in fl for k in BOUNCE): return "bounce"  # by sender only; body keywords false-positive on human replies
    if any(k in t for k in TICKET) or any(k in t for k in AUTO): return "auto_reply"
    if any(k in t for k in OPTOUT): return "opt_out"
    if any(k in t for k in WORKER): return "worker_application"
    if any(k in t for k in INTEREST): return "interested"
    return "neutral"

def add_dnc(cur,email_addr):
    cur.execute("INSERT INTO norway_dnc(email,reason,added_at) SELECT %s,'reply_opt_out',now() WHERE NOT EXISTS(SELECT 1 FROM norway_dnc WHERE lower(email)=lower(%s))",(email_addr,email_addr))
    if cur.rowcount:  # only append CSV when the DB row was actually new -> no duplicate CSV rows
        try:
            with open(DNC_CSV,"a",encoding="utf-8") as f:
                f.write(f'{email_addr},optout,reply,universal,{datetime.now().isoformat()}\n')
        except OSError: pass

def main():
    creds=json.load(open(CRED))
    doms=[k.replace("office_at_","") for k in creds if k.startswith("office_at_") and k.replace("office_at_","") not in SKIP]
    os.makedirs(os.path.dirname(STATE),exist_ok=True)
    seen=load_set(STATE); wr=load_set(WR_STATE)
    WTDIR="/opt/ACTIVE/EMAIL/CAMPAIGNS/worker_templates"
    _wtc={}
    def wtpl(dom):
        if dom not in _wtc:
            fp=f"{WTDIR}/{dom}.txt"
            w=open(fp if os.path.exists(fp) else WORKER_TPL,encoding="utf-8").read().split("\n")
            _wtc[dom]=(w[0].replace("Subject: ","").strip(), "\n".join(w[1:]).strip())
        return _wtc[dom]
    try:
        conn=psycopg2.connect(host="/var/run/postgresql",dbname="interjob_master",user="tudor"); cur=conn.cursor()
    except Exception as e:
        print("DB connect failed, aborting:",e); return
    cutoff=datetime.now()-timedelta(days=2)
    totals={}; leads=[]
    for dom in doms:
        c=creds["office_at_"+dom]
        try:
            m=imaplib.IMAP4_SSL("mail."+dom,993); m.login(c["email"],c["password"]); m.select("INBOX")
        except Exception: continue
        # batched header fetch (last 45d only -> bounded scan + seen-set) to find unseen
        since=(datetime.now()-timedelta(days=45)).strftime("%d-%b-%Y")
        st,ids=m.search(None,f'(SINCE {since})')
        idlist=ids[0].split() if ids and ids[0] else []
        unseen=[]
        if idlist:
            st,hdrs=m.fetch(b",".join(idlist),"(BODY.PEEK[HEADER.FIELDS (MESSAGE-ID FROM SUBJECT DATE)])")
            for it in hdrs:
                if not isinstance(it,tuple): continue
                seq=it[0].split(b" ",1)[0]
                blob=it[1].decode(errors="ignore")
                mid=""
                for ln in blob.splitlines():
                    if ln.lower().startswith("message-id:"): mid=ln.split(":",1)[1].strip(); break
                if not mid:  # no Message-ID -> stable hash fallback so it isn't skipped forever
                    mid="h:"+hashlib.md5(blob.strip().encode("utf-8","ignore")).hexdigest()
                if mid not in seen:
                    seen.add(mid); unseen.append(seq)
        for i in unseen:
          try:
            st,d=m.fetch(i,"(RFC822)")
            if not d or not d[0]: continue
            msg=email.message_from_bytes(d[0][1])
            name,frm=email.utils.parseaddr(dec(msg.get("From",""))); frm=frm.lower()
            subj=dec(msg.get("Subject",""));
            try: mdate=email.utils.parsedate_to_datetime(msg.get("Date","")).replace(tzinfo=None)
            except Exception: mdate=datetime(2000,1,1)  # undated -> treat as old, never auto-reply
            body=""
            for part in (msg.walk() if msg.is_multipart() else [msg]):
                if part.get_content_type()=="text/plain":
                    try: body+=part.get_payload(decode=True).decode(errors="ignore")[:2000]
                    except Exception: pass
            rt=classify(frm,subj,body)
            if rt=="ignore" or "@" not in frm: continue
            totals[rt]=totals.get(rt,0)+1
            cur.execute("INSERT INTO domain_replies(domain,email,company,response_type,subject,msg_date,created_at) VALUES(%s,%s,%s,%s,%s,%s,now())",(dom,frm,name[:200],rt,subj[:300],mdate))
            if rt=="opt_out": add_dnc(cur,frm)
            bk=brevo_key(dom) if rt=="worker_application" else ""
            if bk and frm not in wr and mdate>cutoff:
                try:
                    wsubj,wbody=wtpl(dom)
                    requests.post("https://api.brevo.com/v3/smtp/email",headers={"api-key":bk,"Content-Type":"application/json"},json={"sender":{"email":c["email"],"name":dom.split(".")[0].title()},"to":[{"email":frm}],"replyTo":{"email":c["email"]},"subject":wsubj,"textContent":wbody,"headers":{"List-Unsubscribe":f"<mailto:unsubscribe@{dom}>"}},timeout=15)
                    wr.add(frm)
                except Exception: pass
            d2=frm.split("@")[-1]
            if (rt=="interested" or (rt=="neutral" and d2 not in FREE)): leads.append(f"[{dom}][{rt}] {name} <{frm}>: {subj}")
            conn.commit(); save_set(STATE,seen); save_set(WR_STATE,wr)  # durable after each message: a crash can't re-send or re-insert
          except Exception as e:
            conn.rollback(); print(f"[skip] {dom}: {e}",file=sys.stderr); continue  # one bad message must not abort the domain
        try: m.logout()
        except Exception: pass
    conn.close()
    summary=f"Universal reply handler {datetime.now():%F %H:%M}\nDomains scanned: {len(doms)}\n"+"\n".join(f"  {k}: {v}" for k,v in sorted(totals.items()))+(f"\n\nLEADS / REVIEW ({len(leads)}):\n"+"\n".join(leads[:60]) if leads else "")
    print(summary)
    api=env("BREVO_BUILDJOBS_API_KEY")
    if api and totals:
        requests.post("https://api.brevo.com/v3/smtp/email",headers={"api-key":api,"Content-Type":"application/json"},json={"sender":{"email":"office@buildjobs.eu","name":"Reply Monitor"},"to":[{"email":ALERT_TO}],"subject":f"[All domains] {len(leads)} leads, {sum(totals.values())} new replies","textContent":summary},timeout=20)

if __name__=="__main__": main()
