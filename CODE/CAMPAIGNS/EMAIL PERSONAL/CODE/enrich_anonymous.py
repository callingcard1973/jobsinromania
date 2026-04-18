import csv
import re

INPUT = '../DATA/segmented.csv'
OUTPUT = '../DATA/segmented.csv'

def extract_notes(notes):
    org = ''
    title = ''
    # Hotel/pensiune pattern
    m = re.search(r'Nume Unitate:\s*([^\n]+)', notes)
    if m:
        org = m.group(1).strip().title()
    m = re.search(r'Tip unitate:\s*([^\n]+)', notes)
    if m:
        title = m.group(1).strip().title()
    # Individual person pattern
    if not org:
        m = re.search(r'NUMELE SI PRENUMELE:\s*([^\n]+)', notes, re.IGNORECASE)
        if m:
            parts = m.group(1).strip().split()
            # Format: LASTNAME FIRSTNAME → Firstname Lastname
            org = ' '.join(p.title() for p in reversed(parts)) if len(parts) >= 2 else m.group(1).strip().title()
    if not title:
        m = re.search(r'Job Ty[lt]le\s*:\s*([^\n]+)', notes, re.IGNORECASE)
        if m:
            title = m.group(1).strip().title()
    return org, title

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    enriched = 0
    for row in rows:
        if row.get('segment') != 'anonymous':
            continue
        if row.get('Organization Name', '').strip():
            continue
        org, title = extract_notes(row.get('Notes', ''))
        if org:
            row['Organization Name'] = org
            if not row.get('Organization Title', '').strip() and title:
                row['Organization Title'] = title
            enriched += 1

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Enriched {enriched} anonymous contacts with org name from notes")

if __name__ == '__main__':
    main()
