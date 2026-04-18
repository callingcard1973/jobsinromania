import csv
import html as html_module
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import clean_name, normalize_email, normalize_phone

INPUT = '../DATA/merged.csv'
OUTPUT = '../DATA/cleaned.csv'

def clean_row(row):
    row['First Name'] = clean_name(row.get('First Name', ''))
    row['Last Name'] = clean_name(row.get('Last Name', ''))
    row['Middle Name'] = clean_name(row.get('Middle Name', ''))
    row['Nickname'] = clean_name(row.get('Nickname', ''))
    row['Notes'] = html_module.unescape(row.get('Notes', ''))
    row['E-mail 1 - Value'] = normalize_email(row.get('E-mail 1 - Value', ''))
    row['E-mail 2 - Value'] = normalize_email(row.get('E-mail 2 - Value', ''))
    row['Phone 1 - Value'] = normalize_phone(row.get('Phone 1 - Value', ''))
    return row

def has_contact_info(row):
    return bool(row.get('E-mail 1 - Value') or row.get('Phone 1 - Value'))

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            row = clean_row(row)
            if has_contact_info(row):
                rows.append(row)

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Cleaned: {len(rows)} rows -> {OUTPUT}")

if __name__ == '__main__':
    main()
