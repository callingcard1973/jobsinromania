import csv
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import get_email_domain, is_personal_domain

INPUT = '../DATA/scored.csv'
OUTPUT = '../DATA/segmented.csv'

AT_DOMAINS = {'aon.at', 'euroweb.at', 'chello.at', 'gmx.at', 'inode.at'}
RO_KEYWORDS = {'romania', 'romanian', 'bucuresti', 'bucharest', 'cluj', 'iasi', 'timisoara'}
RECRUIT_KEYWORDS = {'recruiter', 'recruiting', 'hr ', 'human resources', 'staffing',
                    'hiring', 'talent', 'placement', 'workforce', 'headhunt'}

def get_segment(row):
    email = row.get('E-mail 1 - Value', '')
    domain = get_email_domain(email)
    notes = row.get('Notes', '').lower()
    labels = row.get('Labels', '').lower()
    title = row.get('Organization Title', '').lower()
    org = row.get('Organization Name', '').lower()
    score = int(row.get('score', 0))
    first = row.get('First Name', '').strip()
    last = row.get('Last Name', '').strip()

    if 'objekt:' in notes or domain in AT_DOMAINS:
        return 'business_austria'
    if domain.endswith('.ro') or any(k in org for k in RO_KEYWORDS):
        return 'business_ro'
    if any(k in title for k in RECRUIT_KEYWORDS):
        return 'recruitment'
    if domain and not is_personal_domain(domain) and 'airbnb' not in domain:
        return 'business_intl'
    if '* starred' in labels or 'messenger id:' in notes or 'lista_contacte_email' in notes:
        return 'personal_close'
    if 'colegiliceu' in notes:
        return 'school'
    if 'airbnb' in domain:
        return 'airbnb'
    if not email and row.get('Phone 1 - Value', '').strip():
        return 'phone_only'
    if not first and not last and not org:
        return 'anonymous'
    if score < 5:
        return 'junk'
    return 'personal_close'

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) + ['segment']
        for row in reader:
            rows.append(row)

    from collections import Counter
    for row in rows:
        row['segment'] = get_segment(row)

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r['segment'] for r in rows)
    print(f"Segmented {len(rows)} rows -> {OUTPUT}")
    for seg, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {seg}: {n}")

if __name__ == '__main__':
    main()
