#!/usr/bin/env python3
"""Patch email_pipeline.py to scan ALL IMAP folders, not just INBOX + spam."""
import re

f = "/opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py"
c = open(f).read()

# 1. Add SKIP_FOLDERS and _list_all_folders before _detect_spam_folder
insert_before = "def _detect_spam_folder(imap):"
new_code = '''SKIP_FOLDERS = {"[Gmail]/Drafts","[Gmail]/Sent Mail","[Gmail]/Starred","[Gmail]/All Mail",
    "[Gmail]/Trash","Drafts","Sent","Sent Items","Sent Messages","Trash","Deleted",
    "Deleted Items","Deleted Messages","INBOX.Drafts","INBOX.Sent","INBOX.Trash",
    "INBOX.Sent Messages","INBOX.Deleted Messages","Notes","Outbox"}

def _list_all_folders(imap):
    """List all IMAP folders, skip drafts/sent/trash, return with INBOX first."""
    try:
        _, folders = imap.list()
        all_folders = []
        for f in (folders or []):
            decoded = f.decode(errors="replace")
            m = re.search(r'"([^"]*)"$', decoded) or re.search(r'\\s(\\S+)$', decoded)
            if m:
                name = m.group(1)
                if name not in SKIP_FOLDERS and not any(name.lower()==s.lower() for s in SKIP_FOLDERS):
                    all_folders.append(name)
        result = []
        if "INBOX" in all_folders:
            result.append("INBOX")
            all_folders.remove("INBOX")
        result.extend(sorted(all_folders))
        return result if result else ["INBOX"]
    except:
        return ["INBOX"]

def _detect_spam_folder(imap):'''

c = c.replace(insert_before, new_code)

# 2. Replace folder detection to use _list_all_folders
old = """        # Detect spam folder before processing
        spam_folder = _detect_spam_folder(imap)
        folders_to_scan = ["INBOX"]
        if spam_folder:
            folders_to_scan.append(spam_folder)"""
new = """        # Scan ALL folders (INBOX, spam, custom labels, etc.)
        folders_to_scan = _list_all_folders(imap)"""
c = c.replace(old, new)

# 3. Fix log lines
c = c.replace('if is_spam: log(f"  + Scanning spam folder: {folder}")',
              'if is_spam: log(f"  + Scanning folder: {folder}")')
c = c.replace("""if is_spam: log(f"  Spam folder '{folder}': select failed, skipping")""",
              """if is_spam: log(f"  Folder '{folder}': select failed, skipping")""")

open(f, "w").write(c)
print("Patched: pipeline now scans ALL IMAP folders")
