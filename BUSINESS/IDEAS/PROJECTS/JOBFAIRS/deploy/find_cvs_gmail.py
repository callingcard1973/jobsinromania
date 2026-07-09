"""Search all Gmail accounts for CV/application emails with attachments."""
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

ACCOUNTS = [
    ("manpower.dristor@gmail.com", env.get("GMAIL_MANPOWERDRISTOR_APP_PASSWORD", "")),
    ("manpowersearchromania@gmail.com", env.get("GMAIL_MANPOWER_APP_PASSWORD", "")),
    ("elena.manpower.dristor@gmail.com", env.get("GMAIL_ELENA_APP_PASSWORD", "")),
    ("cumparlegume@gmail.com", env.get("GMAIL_CUMPARLEGUME_APP_PASSWORD", "")),
    ("casafaurbucuresti@gmail.com", env.get("GMAIL_CASAFAUR_APP_PASSWORD", "")),
]

SEARCHES = [
    '(SUBJECT "CV")',
    '(SUBJECT "application")',
    '(SUBJECT "resume")',
    '(SUBJECT "job application")',
    '(SUBJECT "apply")',
    '(SUBJECT "candidatura")',
    '(SUBJECT "bewerbung")',
]

total_saved = 0

for user, pwd in ACCOUNTS:
    if not pwd:
        print(f"SKIP {user}: no password")
        continue
    try:
        imap = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        imap.login(user, pwd)

        # Check all relevant folders
        folders_to_check = ["INBOX"]
        _, folder_list = imap.list()
        for f in folder_list:
            name = f.decode().split('"/"')[-1].strip().strip('"').strip()
            if any(kw in name.lower() for kw in ["applic", "cv", "candid", "worker"]):
                folders_to_check.append(name)

        account_pdfs = 0
        seen_ids = set()
        for folder in folders_to_check:
            try:
                imap.select(folder)
            except Exception:
                continue
            for search in SEARCHES:
                try:
                    _, nums = imap.search(None, search)
                except Exception:
                    continue
                if not nums[0]:
                    continue
                for num in nums[0].split()[-50:]:  # Last 50 per search
                    if num in seen_ids:
                        continue
                    seen_ids.add(num)
                    _, data = imap.fetch(num, "(RFC822)")
                    msg = email.message_from_bytes(data[0][1])
                    for part in msg.walk():
                        fn = part.get_filename()
                        if fn and (fn.lower().endswith(".pdf") or fn.lower().endswith(".doc") or fn.lower().endswith(".docx")):
                            safe_fn = re.sub(r'[^\w\-_\.]', '_', fn)[:100]
                            prefix = user.split("@")[0][:10]
                            out_path = SAVE_DIR / f"{prefix}_{safe_fn}"
                            if not out_path.exists():
                                payload = part.get_payload(decode=True)
                                if payload and len(payload) > 500:
                                    out_path.write_bytes(payload)
                                    account_pdfs += 1
                                    total_saved += 1

        print(f"{user}: {len(seen_ids)} emails scanned, {account_pdfs} PDFs saved")
        imap.logout()
    except Exception as e:
        print(f"{user}: ERROR {str(e)[:80]}")

print(f"\nTotal: {total_saved} PDFs saved to {SAVE_DIR}")
