#!/usr/bin/env python3
"""Close the ANOFM feedback loop AUTOMATICALLY: employers who replied "interested"
to the cold ANOFM campaign get the deficit candidate catalog, in-thread, with zero
human curation.

feed: read domain_replies (raspibig interjob_master) for response_type='interested'
on the ANOFM sender domains -> for each not already catalog-sent (sent.json) and not
opt-out (raspi anofm.dnc_master), send the catalog via Brevo (domain's own verified
key), then the basket auto-responder (process_requests.py) handles the cart reply.
ASCII-only, gentle. Idempotent via sent.json."""
import base64, fcntl, json, socket, sys, time, unicodedata
from pathlib import Path

import psycopg2

# Force IPv4 so Brevo IP-allowlist (raspi 86.126.144.222) is honoured (IPv6 rotates).
_gai = socket.getaddrinfo
socket.getaddrinfo = lambda *a, **k: ([r for r in _gai(*a, **k) if r[0] == socket.AF_INET] or _gai(*a, **k))

sys.path.insert(0, "/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS/SHARED")
import sender

HERE = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CATALOG_FUNNEL")
CATALOG = HERE / "catalog_ocupatii_deficitare.html"   # client variant, zero contacts
SENTLOG = HERE / "sent.json"
LOCK = HERE / "funnel_autosend.lock"
CAP = 100   # safety cap per run (interested replies are low-volume)
KEYS = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/anofm_brevo_keys.json")
RASPIBIG = dict(dbname="interjob_master", user="tudor", host="192.168.100.21", password="tudor")
ANOFM = dict(dbname="anofm", user="tudor", host="localhost", password="tudor")
SENDER_NAME = "Echipa InterJob.ro"
# ANOFM sender domain -> (Brevo key_name, occupation label for the catalog body)
DOMAINS = {
    "factoryjobs.eu": ("FACTORYJOBS", "Sudor / Mecanic / Electrician"),
    "warehouseworkers.eu": ("WAREHOUSE", "Sofer / Zidar / Tamplar"),
    "careworkers.eu": ("CAREWORKERS", "Bucatar"),
    "buildjobs.eu": ("BUILDJOBS", "Zidar / Tamplar"),
    "horecaworkers2026.eu": ("HORECA2026EU", "Bucatar"),
    "electricjobs.eu": ("ELECTRICJOBS", "Electrician"),
    "bppltd.co.uk": ("BPPLTD", "Candidati deficitari"),   # catch-all (yahoo) sender
}
BODY = """Buna ziua,

Multumim pentru interesul aratat. Atasat gasiti catalogul nostru de candidati
InterJob.ro pentru {occupation} - profiluri cu experienta, disponibile pentru angajare.

Cum alegeti rapid:
1. Deschideti catalogul (fisier HTML, se deschide in orice browser).
2. Adaugati candidatii care va intereseaza in cos (butonul "+ Cos").
3. La final apasati "Trimite cererea" - ne ajunge lista cu candidatii alesi.

Va trimitem apoi CV-urile complete si organizam interviuri pentru candidatii selectati.

Cu stima,
Echipa InterJob.ro
office@interjob.ro
"""


def ascii_fold(s):
    for u, a in {"—": "-", "–": "-", "’": "'", "‘": "'", "“": '"', "”": '"', "…": "..."}.items():
        s = s.replace(u, a)
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")


def save_sent(sent):
    tmp = SENTLOG.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(sent, indent=2))
    tmp.replace(SENTLOG)


def main():
    dry = "--dry-run" in sys.argv
    fh = open(LOCK, "w")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("another funnel_autosend running — exit")
        return
    keys = json.loads(KEYS.read_text())
    sent = json.loads(SENTLOG.read_text()) if SENTLOG.exists() else {}
    attach = [{"content": base64.b64encode(CATALOG.read_bytes()).decode(),
               "name": "catalog_candidati_InterJob.html"}]

    # QUALITY GATE: only employers WE actually cold-emailed via ANOFM (real RO deficit
    # firms). Excludes misclassified/foreign replies (e.g. a reply to another campaign).
    with psycopg2.connect(**ANOFM) as ac:
        cur = ac.cursor()
        cur.execute("SELECT lower(email) FROM dnc_master")
        dnc = {r[0] for r in cur.fetchall()}
        cur.execute("SELECT lower(email) FROM send_log WHERE campaign LIKE 'ANOFM%'")
        anofm_sent = {r[0] for r in cur.fetchall() if r[0]}

    with psycopg2.connect(**RASPIBIG) as rc:
        cur = rc.cursor()
        cur.execute("SELECT lower(email), company, domain, subject FROM domain_replies "
                    "WHERE response_type='interested' AND domain = ANY(%s)",
                    (list(DOMAINS),))
        rows = cur.fetchall()

    n = 0
    for em, company, domain, subj in rows:
        if not em or em in sent or em in dnc or em not in anofm_sent:
            continue
        if n >= CAP:
            print(f"cap {CAP} reached — stopping")
            break
        key = keys.get(DOMAINS[domain][0])
        if not key:                     # missing Brevo key -> skip, don't crash the run
            print(f"SKIP {em}: no key for {domain}")
            continue
        occ = DOMAINS[domain][1]
        sender_email = f"office@{domain}"
        base = (subj or "Catalog candidati InterJob.ro")
        subject = ascii_fold("Re: " + (base[4:] if base.lower().startswith("re: ") else base))
        body = ascii_fold(BODY.format(occupation=occ))
        hdr = {"List-Unsubscribe": f"<mailto:office@{domain}?subject=unsubscribe>"}
        if dry:
            print(f"[DRY] catalog -> {em} <- {sender_email} ({occ})")
        else:
            ok, stt = sender.send_brevo(key, sender_email, SENDER_NAME, em,
                                        subject, body, reply_to=sender_email,
                                        attachment=attach, headers=hdr)
            if not ok:
                print(f"FAIL {em} {stt}")
                continue
            sent[em] = sender_email
            save_sent(sent)             # persist AFTER EACH send -> crash can't double-blast
            time.sleep(5)
        n += 1
    print(f"interested={len(rows)} catalog_sent_now={n} total_sent={len(sent)}")


if __name__ == "__main__":
    main()
