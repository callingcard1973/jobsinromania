"""Search A2 Hosting inboxes for CV attachments."""
import imaplib, email, os, re
from pathlib import Path

SAVE_DIR = Path("/tmp/cv_gmail")
SAVE_DIR.mkdir(exist_ok=True)

env = {}
with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
    for l in f:
        if "=" in l and not l.startswith("#"):
            k, v = l.strip().split("=", 1)
            env[k] = v.strip().strip('"')

HOST = "nl1-cl8-ats1.a2hosting.com"
ACCOUNTS = [
    ("office@interjob.ro", env.get("A2_EMAIL_PASSWORD", "")),
    ("office@buildjobs.eu", env.get("A2_EMAIL_PASSWORD", "")),
    ("office@factoryjobs.eu", env.get("A2_FACTORYJOBS_EU_PASSWORD", "")),
    ("office@careworkers.eu", env.get("A2_EMAIL_PASSWORD", "")),
    ("office@meatworkers.eu", env.get("A2_MEATWORKERS_EU_PASSWORD", "")),
    ("office@electricjobs.eu", env.get("A2_ELECTRICJOBS_EU_PASSWORD", "")),
]

total = 0
for user, pwd in ACCOUNTS:
    if not pwd:
        continue
    try:
        imap = imaplib.IMAP4_SSL(HOST, 993)
        imap.login(user, pwd)
        imap.select("INBOX")
        _, nums = imap.search(None, "ALL")
        if not nums[0]:
            imap.logout()
            continue
        pdfs = 0
        for num in nums[0].split()[-100:]:
            _, data = imap.fetch(num, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            for part in msg.walk():
                fn = part.get_filename()
                if fn and fn.lower().endswith((".pdf", ".doc", ".docx")):
                    safe = re.sub(r'[^\w\-_\.]', '_', fn)[:80]
                    prefix = user.split("@")[0].replace("office", user.split("@")[1].split(".")[0])
                    out = SAVE_DIR / f"a2_{prefix}_{safe}"
                    if not out.exists():
                        payload = part.get_payload(decode=True)
                        if payload and len(payload) > 500:
                            out.write_bytes(payload)
                            pdfs += 1
                            total += 1
        print(f"{user}: {pdfs} PDFs")
        imap.logout()
    except Exception as e:
        print(f"{user}: {str(e)[:60]}")

print(f"Total A2: {total}")
