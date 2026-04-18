#!/usr/bin/env python3
"""Patch email_pipeline.py to move applicant CVs to APPLICANTS folder while scanning.
Women applicants stay in INBOX."""
import re

f = "/opt/ACTIVE/EMAIL/ORDERS/email_pipeline.py"
c = open(f).read()

# 1. Add WOMEN_NAMES pattern after PERSONAL_DOMAINS import area
# Find a good insertion point - after _clf, _llm = None, None
insert_after = "_clf, _llm = None, None"
women_code = '''_clf, _llm = None, None

# Women name patterns for keeping CVs in INBOX
WOMEN_NAMES = re.compile(r"\\b(mrs|ms|miss|madam|lady|doamna|d-na|"
    r"fatima|maria|ana|elena|ioana|alexandra|andreea|cristina|diana|"
    r"raluca|mihaela|alina|simona|camelia|florina|roxana|anca|"
    r"mariana|daniela|adriana|gabriela|nicoleta|monica|laura|"
    r"aisha|amina|khadija|nadia|sara|hiba|maryam|salma|"
    r"priya|anita|sunita|rekha|sita|gita|lakshmi|"
    r"mary|grace|blessing|faith|joy|rose|victoria|"
    r"sophie|anna|emma|julia|lisa|nina|eva|sarah|"
    r"she|her|female|woman|femme|femeie|doamna)\\b", re.I)

def is_woman(name, subj, body_start):
    """Check if applicant is likely female based on name/content."""
    text = f"{name} {subj} {body_start[:300]}"
    return bool(WOMEN_NAMES.search(text))

def ensure_folder(imap, folder):
    """Create IMAP folder if it doesn't exist."""
    try:
        st, _ = imap.select(f\'"{folder}"\', readonly=True)
        if st == "OK":
            return True
        imap.create(folder)
        return True
    except:
        try:
            imap.create(folder)
            return True
        except:
            return False

def move_email(imap, mid, src_folder, dst_folder):
    """Move email from src to dst folder via copy+delete."""
    try:
        # Must be in src folder, read-write
        imap.select(f\'"{src_folder}"\', readonly=False)
        imap.copy(mid, f\'"{dst_folder}"\')
        imap.store(mid, "+FLAGS", "\\\\Deleted")
        imap.expunge()
        return True
    except Exception as e:
        return False'''

c = c.replace(insert_after, women_code)

# 2. Modify save_applicant to return whether it's a woman
old_save = '''def save_applicant(se, frm, subj, body, acct, dry):
    cty, lang = "", "EN"
    for c,p in [("MA","maroc|morocco"),("NG","nigeria"),("NP","nepal"),("IN","india"),("CZ","cz$"),("BD","bangladesh")]:
        if re.search(p,body[:500]+se,re.I): cty=c; break
    for l,p in [("FR",r"[àâéèêëïîôùûüÿç]"),("CZ",r"[áčďéě]"),("RO",r"[ăâîșț]")]:
        if re.search(p,body[:200]): lang=l; break
    row = {"Timestamp":f"{datetime.now():%d/%m/%Y %H:%M:%S}","Name":get_name(frm),
        "Email":se,"Phone":get_phone(body),"Country":cty,"Language":lang,"Subject":subj[:100],"Account":acct}
    if not dry: append_csv(APPLICANTS_F, APPL_COLS, row)
    log(f"    -> {\'[DRY]\' if dry else \'APPLICANT\'} {se} ({cty})")'''

new_save = '''def save_applicant(se, frm, subj, body, acct, dry):
    cty, lang = "", "EN"
    for c,p in [("MA","maroc|morocco"),("NG","nigeria"),("NP","nepal"),("IN","india"),("CZ","cz$"),("BD","bangladesh")]:
        if re.search(p,body[:500]+se,re.I): cty=c; break
    for l,p in [("FR",r"[àâéèêëïîôùûüÿç]"),("CZ",r"[áčďéě]"),("RO",r"[ăâîșț]")]:
        if re.search(p,body[:200]): lang=l; break
    name = get_name(frm)
    woman = is_woman(name, subj, body)
    row = {"Timestamp":f"{datetime.now():%d/%m/%Y %H:%M:%S}","Name":name,
        "Email":se,"Phone":get_phone(body),"Country":cty,"Language":lang,"Subject":subj[:100],"Account":acct}
    if not dry: append_csv(APPLICANTS_F, APPL_COLS, row)
    tag = "F" if woman else ""
    log(f"    -> {\'[DRY]\' if dry else \'APPLICANT\'} {se} ({cty}) {tag}")
    return woman'''

c = c.replace(old_save, new_save)

# 3. Add move logic after applicant classification in process()
# Find where applicants are saved and add move logic
old_applicant_block = '''                save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1'''
new_applicant_block = '''                    woman = save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1
                    # Move male applicant CVs to APPLICANTS folder, women stay in INBOX
                    if not dry and not woman and folder == "INBOX":
                        if ensure_folder(imap, "APPLICANTS"):
                            if move_email(imap, mid, folder, "APPLICANTS"):
                                log(f"      moved to APPLICANTS")
                            # Re-select current folder after move
                            try:
                                imap.select(f\'"{folder}"\', readonly=True)
                            except: pass'''

# This replacement is tricky because there are two occurrences with different indentation
# Let me be more precise - find the exact line in context
c = c.replace(
    '                save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1',
    '                woman = save_applicant(se, frm, subj, body, label, dry); stats["applicants"]+=1\n'
    '                    # Move male applicant CVs to APPLICANTS folder, women stay in INBOX\n'
    '                    if not dry and not woman and folder == "INBOX":\n'
    '                        if ensure_folder(imap, "APPLICANTS"):\n'
    '                            if move_email(imap, mid, folder, "APPLICANTS"):\n'
    '                                log(f"      moved to APPLICANTS")\n'
    '                            # Re-select current folder after move\n'
    '                            try:\n'
    '                                imap.select(f\'"{folder}"\', readonly=True)\n'
    '                            except: pass'
)

open(f, "w").write(c)
print("Patched: applicant CVs move to APPLICANTS, women stay in INBOX")
