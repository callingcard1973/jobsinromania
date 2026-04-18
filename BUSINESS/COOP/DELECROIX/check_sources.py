import csv

# Check all data sources
print("Checking DDG contacts...")
ddg_cui = {}
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\ddg_contacts.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        email = row.get('email', '').strip()
        website = row.get('website', '').strip()
        if cui:
            if cui not in ddg_cui:
                ddg_cui[cui] = {'emails': [], 'websites': []}
            if email and '@' in email:
                ddg_cui[cui]['emails'].append(email)
            if website:
                ddg_cui[cui]['websites'].append(website)

ddg_with_email = sum(1 for v in ddg_cui.values() if v['emails'])
print(f"DDG: {len(ddg_cui)} CUIs, {ddg_with_email} with email")

print("\nChecking Harvested emails...")
harv_cui = {}
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\harvested_emails.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        cui = row.get('cui', '').strip()
        email = row.get('email_found', '').strip()
        if cui and email and '@' in email:
            if cui not in harv_cui:
                harv_cui[cui] = []
            harv_cui[cui].append(email)

print(f"Harvested: {len(harv_cui)} CUIs with email")

print("\nChecking Romania Agriculture...")
ragri_cui = {}
tot = 0
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\romania_agriculture_companies.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    print(f"Columns: email? {'email' in cols}, email_madr? {'email_madr' in cols}, email_dsvsa? {'email_dsvsa' in cols}, email_agri? {'email_agri' in cols}")
    for row in reader:
        tot += 1
        cui = row.get('cui', '').strip()
        if not cui:
            continue
        
        emails = []
        for field in ['email', 'email_madr', 'email_dsvsa', 'email_agri', 'email_eu']:
            e = row.get(field, '').strip()
            if e and '@' in e:
                emails.append(e)
        
        website = row.get('website', '').strip() or row.get('website_eu', '').strip() or row.get('website_onrc', '').strip()
        
        if emails or website:
            ragri_cui[cui] = {'emails': emails, 'website': website}

ragri_with_email = sum(1 for v in ragri_cui.values() if v['emails'])
print(f"Romania Agri: {tot} total rows, {len(ragri_cui)} with contact, {ragri_with_email} with email")

# Now check how many of our 1185 distributors match
print("\n\nMatching against our distributors...")
distri_cuis = set()
with open(r'D:\MEMORY\DELECROIX\distribuitori_utilaje_agricole.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    for row in reader:
        distri_cuis.add(row['CUI'].strip())

print(f"Our distributors: {len(distri_cuis)} CUIs")

# Match with DDG
ddg_match = distri_cuis & set(ddg_cui.keys())
ddg_match_email = sum(1 for c in ddg_match if ddg_cui[c]['emails'])
print(f"Match DDG: {len(ddg_match)}, with email: {ddg_match_email}")

# Match with harvested
harv_match = distri_cuis & set(harv_cui.keys())
print(f"Match Harvested: {len(harv_match)}")

# Match with romania agri
ragri_match = distri_cuis & set(ragri_cui.keys())
ragri_match_email = sum(1 for c in ragri_match if ragri_cui[c]['emails'])
print(f"Match Romania Agri: {len(ragri_match)}, with email: {ragri_match_email}")

# Total unique emails we can get
all_matched = set()
all_matched |= ddg_match
all_matched |= harv_match
all_matched |= ragri_match
print(f"\nTotal matched (any source): {len(all_matched)} / {len(distri_cuis)}")

with open(r'D:\MEMORY\DELECROIX\match_report.txt', 'w', encoding='utf-8') as out:
    out.write(f'MATCH REPORT\n')
    out.write(f'Distributors: {len(distri_cuis)}\n')
    out.write(f'Matched DDG: {len(ddg_match)} (email: {ddg_match_email})\n')
    out.write(f'Matched Harvested: {len(harv_match)}\n')
    out.write(f'Matched Romania Agri: {len(ragri_match)} (email: {ragri_match_email})\n')
    out.write(f'Total matched: {len(all_matched)}\n')
    out.write(f'STILL MISSING: {len(distri_cuis) - len(all_matched)}\n')
