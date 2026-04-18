import csv
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import normalize_email, normalize_phone

INPUT = '../DATA/cleaned.csv'
OUTPUT = '../DATA/deduped.csv'

def full_name(row):
    return (row.get('First Name', '') + ' ' + row.get('Last Name', '')).strip()

def merge_rows(existing, new):
    if len(full_name(new)) > len(full_name(existing)):
        existing['First Name'] = new['First Name']
        existing['Last Name'] = new['Last Name']
    n1 = existing.get('Notes', '').strip()
    n2 = new.get('Notes', '').strip()
    if n2 and n2 not in n1:
        existing['Notes'] = (n1 + ' | ' + n2).strip(' |')
    if not existing.get('Phone 1 - Value') and new.get('Phone 1 - Value'):
        existing['Phone 1 - Value'] = new['Phone 1 - Value']
    if not existing.get('E-mail 2 - Value') and new.get('E-mail 1 - Value') != existing.get('E-mail 1 - Value'):
        existing['E-mail 2 - Value'] = new.get('E-mail 1 - Value', '')
    l1 = existing.get('Labels', '')
    l2 = new.get('Labels', '')
    if l2 and l2 not in l1:
        existing['Labels'] = (l1 + ' ::: ' + l2).strip(' :::')
    return existing

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    by_email = {}
    no_email = []
    for row in rows:
        email = row.get('E-mail 1 - Value', '').strip()
        if email:
            if email in by_email:
                by_email[email] = merge_rows(by_email[email], row)
            else:
                by_email[email] = row
        else:
            no_email.append(row)

    by_phone = {}
    no_phone_no_email = []
    for row in no_email:
        phone = normalize_phone(row.get('Phone 1 - Value', ''))
        if phone:
            if phone in by_phone:
                by_phone[phone] = merge_rows(by_phone[phone], row)
            else:
                by_phone[phone] = row
        else:
            no_phone_no_email.append(row)

    result = list(by_email.values()) + list(by_phone.values()) + no_phone_no_email

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result)

    print(f"Deduped: {len(rows)} -> {len(result)} rows -> {OUTPUT}")

if __name__ == '__main__':
    main()
