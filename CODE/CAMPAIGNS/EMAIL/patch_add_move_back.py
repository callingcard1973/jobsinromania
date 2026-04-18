#!/usr/bin/env python3
"""Re-enable move-to-APPLICANTS while scanning. Move from INBOX only, women stay."""
f = "/opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py"
c = open(f).read()

# Re-add return woman to save_applicant
old = '''    log(f"    -> {\'[DRY]\' if dry else \'APPLICANT\'} {se} ({cty})")'''
new = '''    tag = "F" if woman else ""
    log(f"    -> {\'[DRY]\' if dry else \'APPLICANT\'} {se} ({cty}) {tag}")
    return woman'''
c = c.replace(old, new)

# Re-add move logic after save_applicant call
old = '''                save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1'''
new = '''                woman = save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1
                    # Move male applicant CVs to APPLICANTS folder, women stay in INBOX
                    if not dry and not woman and folder == "INBOX":
                        if ensure_folder(imap, "APPLICANTS"):
                            if move_email(imap, mid, folder, "APPLICANTS"):
                                log(f"      moved to APPLICANTS")
                            try:
                                imap.select(f\'"{folder}"\', readonly=True)
                            except: pass'''
c = c.replace(old, new)

open(f, "w").write(c)
print("Move feature re-enabled")
