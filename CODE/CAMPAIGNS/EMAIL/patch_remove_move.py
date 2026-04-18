#!/usr/bin/env python3
"""Remove the move-to-APPLICANTS feature. Keep scan all folders + classify only."""
f = "/opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py"
c = open(f).read()

# Remove the move block after save_applicant call
old = '''                woman = save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1
                    # Move male applicant CVs to APPLICANTS folder, women stay in INBOX
                    if not dry and not woman and folder == "INBOX":
                        if ensure_folder(imap, "APPLICANTS"):
                            if move_email(imap, mid, folder, "APPLICANTS"):
                                log(f"      moved to APPLICANTS")
                            # Re-select current folder after move
                            try:
                                imap.select(f\'"{folder}"\', readonly=True)
                            except: pass'''
new = '''                save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1'''
c = c.replace(old, new)

# Revert save_applicant to not return woman flag
old_save = '''    tag = "F" if woman else ""
    log(f"    -> {\'[DRY]\' if dry else \'APPLICANT\'} {se} ({cty}) {tag}")
    return woman'''
new_save = '''    log(f"    -> {\'[DRY]\' if dry else \'APPLICANT\'} {se} ({cty})")'''
c = c.replace(old_save, new_save)

open(f, "w").write(c)
print("Removed move feature. Scan + classify only.")
