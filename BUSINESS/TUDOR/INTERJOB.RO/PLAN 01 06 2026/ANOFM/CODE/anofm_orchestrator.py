#!/usr/bin/env python3
"""ANOFM multi-sender gentle orchestrator on raspi (like raspibig's campaign
orchestrator). Occupation-routed segments, per-domain warmup ramp, DB
suppression (anofm.dnc_master + anofm.send_log), List-Unsubscribe, logs every
send to send_log. Singleton via flock. Config: anofm_orchestrator.json (no
secrets); keys: anofm_brevo_keys.json (raspi, chmod 600)."""
import fcntl, json, logging, os, random, re, socket, sys, threading, time, unicodedata
from datetime import date
from pathlib import Path

import psycopg2

# Force IPv4: Brevo IP-allowlist holds raspi's stable IPv4 (86.126.144.222), but
# default calls go out over rotating IPv6 -> blocked on restricted domains.
_gai = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: ([r for r in _gai(*a, **k) if r[0] == socket.AF_INET] or _gai(*a, **k))

sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED")
import sender

BASE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI")
CFG, STATE, LOCK = BASE / "anofm_orchestrator.json", BASE / "anofm_orchestrator_state.json", BASE / "anofm_orchestrator.lock"
KEYS, TPL = BASE / "anofm_brevo_keys.json", BASE / "TEMPLATES" / "template_anofm_angajatori.txt"
A2_CREDS = {}
try:
    import json as _json
    _c = _json.load(open("/opt/EMAIL/CAMPAIGNS/a2_smtp_credentials.json"))
    for _v in (_c if isinstance(_c, list) else _c.values()):
        if isinstance(_v, dict) and _v.get("email"):
            A2_CREDS[_v["email"]] = _v.get("password", "")
except Exception:
    pass
DB = dict(dbname="anofm", user="tudor", host="localhost", password="tudor")
SCRAPE_DB = dict(dbname="anofm_scrapes", user="tudor", host="localhost", password="tudor")
SENDER_NAME = "Elena Vasilescu - InterJob.ro"
FREE_NONYAHOO = ("hotmail.", "outlook.", "live.", "aol.com", "yandex.", "icloud.com",
                 "protonmail.", "proton.me", "mail.ru", "inbox.lv", "gmx.", "tutanota.", "zoho.")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("anofm-orch")


def norm(s):
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn")


def parse_tpl():
    L = TPL.read_text(encoding="utf-8").splitlines()
    return L[0].split(":", 1)[1].strip(), "\n".join(L[2:]).lstrip("\n")


_PUNCT = {"—": "-", "–": "-", "‘": "'", "’": "'",
          "“": '"', "”": '"', "…": "...", " ": " "}


def ascii_fold(s):
    # rule: outbound email is ASCII-only ALWAYS. Map typographic punctuation to
    # ASCII first (em-dash -> -, smart quotes -> '), then strip diacritics via NFKD.
    for u, a in _PUNCT.items():
        s = s.replace(u, a)
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def fill(t, r):
    for k in ("company_name", "sector", "county", "job_title", "positions_available"):
        t = t.replace("{" + k + "}", (r.get(k) or "").strip())
    return ascii_fold(t)


# Brevo rejects addresses with no dotted TLD or embedded spaces (HTTP_400
# "email is not valid in to"). Require local@domain.tld with no whitespace.
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")


def valid_email(v):
    return bool(EMAIL_RE.match(v))


# Durable repair for common typos so a real lead is not parked. SAFE only:
# collapse whitespace around @, keep the first token (drops trailing " tel..",
# a second email, and fragmented local parts like "mihail masca@"), and complete
# a missing/mistyped TLD ONLY for known free providers. Never guesses corp TLDs.
_PROV = {"gmail": "gmail.com", "gmailcom": "gmail.com", "gmai": "gmail.com",
         "yahoo": "yahoo.com", "yahoocom": "yahoo.com",
         "hotmail": "hotmail.com", "hotmailcom": "hotmail.com"}


def repair_email(v):
    v = re.sub(r"\s*@\s*", "@", (v or "").strip().lower())
    tok = v.split()[0] if v.split() else ""
    if "@" not in tok:                 # fragmented local part (space before @) -> unsafe
        return None
    if valid_email(tok):
        return tok
    if tok.count("@") == 1:
        loc, dom = tok.split("@")
        if loc and dom in _PROV:
            cand = f"{loc}@{_PROV[dom]}"
            if valid_email(cand):
                return cand
    return None


def pick_email(r, allow_yahoo, skipped=None):
    for k in ("email_1", "email_2", "email_3"):
        v = (r.get(k) or "").strip().lower()
        if v and "@" in v:
            if not valid_email(v):     # try durable repair; only park if unrepairable
                fixed = repair_email(v)
                if not fixed:          # let a valid email_2/email_3 still win
                    if skipped is not None:
                        skipped.append(v)
                    continue
                v = fixed
            if any(d in v for d in FREE_NONYAHOO):
                continue
            if not allow_yahoo and "yahoo." in v:
                continue
            return v
    return None


def ramp_cap(days, ramp):
    if not ramp:                       # guard: empty ramp -> nothing to send
        return 0
    for thr, cap in ramp:
        if days < thr:
            return cap
    return ramp[-1][1]


def seg_delay(seg):
    # gentle: random 3-6 min between sends. delay may be [min,max] seconds or a scalar.
    d = seg.get("delay", [180, 360])
    if isinstance(d, list):
        return random.uniform(d[0], d[1]) if len(d) >= 2 else (d[0] if d else 180)
    return d


def build_audience(seg, sent, dnc):
    occ, ay = tuple(seg["occupations"]), seg.get("allow_yahoo", False)
    conn = psycopg2.connect(**SCRAPE_DB)
    cur = conn.cursor()
    cur.execute("SELECT email_1,email_2,email_3,company_name,company_org_number,"
                "sector,city,job_title,positions_available FROM scrape_jobs")
    comp = {}
    skipped = []
    for e1, e2, e3, name, org, sector, city, jt, pos in cur.fetchall():
        if not any(o in norm(jt) for o in occ):
            continue
        em = pick_email(dict(email_1=e1, email_2=e2, email_3=e3), ay, skipped)
        if not em or em in sent or em in dnc:
            continue
        key = (org or "").strip() or (name or "").strip().lower()
        if not key:
            continue
        try:
            p = int(pos or 0)
        except ValueError:
            p = 0
        if key not in comp or p > comp[key]["_p"]:
            comp[key] = dict(email=em, company_name=(name or "").strip(),
                             sector=(sector or "").strip(),
                             county=(city.split(">")[0].strip() if city else ""),
                             job_title=(jt or "").strip(), positions_available=str(p), _p=p)
    conn.close()
    if skipped:
        log.info(f"[{seg['name']}] parked {len(skipped)} malformed email(s) pre-send")
    seen, out = set(), []
    for r in sorted(comp.values(), key=lambda x: x["_p"], reverse=True):
        if r["email"] not in seen:
            seen.add(r["email"])
            out.append(r)
    return out


def run_segment(seg, subj_t, body_t, keys, dry):
    # one thread per segment. Audience (seg["_aud"]) is pre-partitioned in main so
    # NO email appears in two segments -> no cross-thread double-send. Own DB conn.
    name = seg["name"]
    conn = None
    try:
        conn = psycopg2.connect(**DB)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM send_log WHERE campaign=%s AND sent_at::date=current_date", (name,))
        rem = seg["_cap"] - cur.fetchone()[0]
        log.info(f"[{name}] cap={seg['_cap']} remaining={rem} audience={len(seg['_aud'])} sender={seg['sender_email']}")
        if rem <= 0:
            return
        dom = seg["sender_email"].split("@")[1]
        hdr = {"List-Unsubscribe": f"<mailto:office@{dom}?subject=unsubscribe>"}
        if not dry:
            time.sleep(random.uniform(0, 60))   # stagger threads' first send (no thundering herd)
        n = 0
        for r in seg["_aud"]:
            if n >= rem:
                break
            em = r["email"]
            subj, body = fill(subj_t, r), fill(body_t, r)
            if dry:
                log.info(f"[{name}][DRY] -> {em}")
            else:
                if seg.get("method") == "smtp":
                    ok, stt = sender.send_smtp("mail." + dom, seg["sender_email"],
                                               A2_CREDS.get(seg["sender_email"], ""), SENDER_NAME,
                                               em, subj, body, reply_to=seg["sender_email"], headers=hdr)
                    meth = "smtp"
                else:
                    ok, stt = sender.send_brevo(keys[seg["key_name"]], seg["sender_email"],
                                                SENDER_NAME, em, subj, body,
                                                reply_to=seg["sender_email"], headers=hdr)
                    meth = "brevo"
                if not ok:
                    log.info(f"[{name}] FAIL {em} {stt}")
                    continue
                try:
                    cur.execute("INSERT INTO send_log(email,company,sector,campaign,sender,"
                                "method,status,sent_at) VALUES(%s,%s,%s,%s,%s,%s,'sent',now())",
                                (em, r["company_name"], r["sector"], name, seg["sender_email"], meth))
                    conn.commit()
                except Exception as e:   # sent OK but not recorded -> will resend next run; make it loud
                    log.error(f"[{name}] SENT_BUT_NOT_LOGGED {em}: {e}")
                    conn.rollback()
            n += 1
            if not dry:
                time.sleep(seg_delay(seg))
        log.info(f"[{name}] sent={n}")
    except Exception as e:
        log.error(f"[{name}] segment crashed: {e}")
    finally:
        if conn:
            conn.close()


def main():
    fh = open(LOCK, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        log.info("another orchestrator running — exit")
        return
    fh.write(str(os.getpid()))           # diagnosability: which PID holds the lock
    fh.flush()
    dry = "--dry-run" in sys.argv
    cfg = json.loads(CFG.read_text())
    keys = json.loads(KEYS.read_text())
    subj_t, body_t = parse_tpl()
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("SELECT lower(email) FROM dnc_master")
    dnc = {r[0] for r in cur.fetchall()}
    cur.execute("SELECT lower(email) FROM send_log")
    sent = {r[0] for r in cur.fetchall() if r[0]}
    conn.close()
    state = json.loads(STATE.read_text()) if STATE.exists() else {}
    today = date.today().isoformat()

    active = [s for s in cfg["segments"] if s.get("enabled")]
    # Build audiences sequentially + PARTITION disjointly: a company posting jobs in
    # several occupations matches several segments, so each email is claimed by the
    # FIRST (config-order = priority) segment only. Eliminates cross-thread double-send.
    claimed = set()
    for seg in active:
        seg["_start"] = state.setdefault(seg["name"], {}).setdefault("start_date", today)
        days = (date.today() - date.fromisoformat(seg["_start"])).days
        seg["_cap"] = seg.get("daily_cap") or ramp_cap(days, seg.get("ramp", []))
        aud = build_audience(seg, sent, dnc)
        seg["_aud"] = [r for r in aud if r["email"] not in claimed]
        claimed.update(r["email"] for r in seg["_aud"])
        log.info(f"[{seg['name']}] day={days} cap={seg['_cap']} eligible={len(aud)} unique={len(seg['_aud'])}")
    if not dry:
        STATE.write_text(json.dumps(state, indent=2))

    threads = [threading.Thread(target=run_segment, args=(seg, subj_t, body_t, keys, dry))
               for seg in active]
    for t in threads:
        t.start()
    for t in threads:
        t.join()


if __name__ == "__main__":
    main()
