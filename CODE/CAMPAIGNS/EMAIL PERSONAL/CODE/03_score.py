import csv
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import is_personal_domain, get_email_domain

INPUT = '../DATA/deduped.csv'
OUTPUT = '../DATA/scored.csv'

def score_row(row):
    s = 0
    email = row.get('E-mail 1 - Value', '')
    domain = get_email_domain(email)

    if domain and not is_personal_domain(domain) and 'airbnb' not in domain:
        s += 30
    if row.get('Organization Name', '').strip():
        s += 20
    if row.get('Phone 1 - Value', '').strip():
        s += 15
    if row.get('Notes', '').strip():
        s += 15
    if '* starred' in row.get('Labels', ''):
        s += 20
    if row.get('E-mail 2 - Value', '').strip():
        s += 10

    first = row.get('First Name', '').strip()
    last = row.get('Last Name', '').strip()
    if first or last:
        s += 10
    else:
        s -= 20
    if 'airbnb' in domain:
        s -= 30

    return max(0, min(100, s))

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    fieldnames = list(fieldnames) + ['score']
    for row in rows:
        row['score'] = score_row(row)

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    scores = [r['score'] for r in rows]
    avg = sum(scores) / len(scores) if scores else 0
    print(f"Scored {len(rows)} rows. Avg score: {avg:.1f} -> {OUTPUT}")

if __name__ == '__main__':
    main()
