#!/usr/bin/env python3
"""Parse MADR Excel files (XLSX + XLS) - ALL FORMATS."""
import re
from pathlib import Path
import csv
import sys

# Try openpyxl first, fall back to xlrd for .xls
try:
    from openpyxl import load_workbook as load_xlsx
except:
    load_xlsx = None

try:
    import xlrd
    HAS_XLRD = True
except:
    HAS_XLRD = False

DATA_DIR = Path(__file__).parent.parent / "DATA"
OUTPUT_CSV = Path(__file__).parent.parent / "SILOS_MASTER_CORRECTED.csv"

def extract_phone(text):
    """Extract phone from text like 'TEL.0742123456' or '0742 123 456'."""
    if not text:
        return ""
    text = str(text).upper()

    # Match TEL. followed by digits/spaces/dashes, or standalone phone numbers
    # Pattern: TEL.XXXX or just 07XX or 02XX starting patterns
    phone_match = re.search(r'TEL\.?\s*(\d[\d\s\-\(\)]{7,})', text)

    if phone_match:
        phone = phone_match.group(1)
        # Clean: remove spaces, parens, dashes
        phone = re.sub(r'[\s\-\(\)]', '', phone)
        # Keep only first 10 digits after 07 or 02
        if len(phone) > 10:
            phone = phone[:10]
        # Normalize
        if phone.startswith('0'):
            phone = '+40' + phone[1:]
        return phone

    return ""

def extract_email(text):
    """Extract email."""
    if not text:
        return ""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', str(text))
    return emails[0].lower() if emails else ""

def parse_xlsx_file(filepath):
    """Parse .xlsx file."""
    if not load_xlsx:
        return []

    facilities = []
    try:
        wb = load_xlsx(filepath, data_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        facilities = _extract_from_rows(rows, filepath.stem)
    except Exception as e:
        print(f"  ERROR {filepath.stem}: {e}")
    return facilities

def parse_xls_file(filepath):
    """Parse .xls file."""
    if not HAS_XLRD:
        return []

    facilities = []
    try:
        book = xlrd.open_workbook(str(filepath), on_demand=True)
        sheet = book.sheet_by_index(0)
        rows = [[sheet.cell_value(r, c) for c in range(sheet.ncols)] for r in range(sheet.nrows)]
        facilities = _extract_from_rows(rows, filepath.stem)
    except Exception as e:
        print(f"  ERROR {filepath.stem}: {e}")
    return facilities

def _extract_from_rows(rows, county_name):
    """Extract facilities from row data."""
    facilities = []

    # Find header row (contains 'autorizatia' or similar)
    header_row = None
    for i, row in enumerate(rows[:10]):
        row_text = ' '.join(str(c or '') for c in row).lower()
        if any(x in row_text for x in ['autorizatia', 'denumire', 'nr.crt', 'operator']):
            header_row = i
            break

    if header_row is None:
        header_row = 3

    data_start = header_row + 5
    i = data_start

    while i < len(rows):
        row = rows[i]

        # Skip empty rows
        if not any(row):
            i += 1
            continue

        str(row[0] or '').strip()
        col1_str = str(row[1] or '').strip()

        # Look for auth code (XX00123)
        if col1_str and re.match(r'^[A-Z]{2}\d{5}', col1_str):
            auth_num = col1_str
            operator_name = str(row[2] or '').strip() if len(row) > 2 else ''
            facility_name = str(row[3] or '').strip() if len(row) > 3 else ''
            capacity = str(row[4] or '').strip() if len(row) > 4 else ''

            # Collect contact info from next rows
            contact_lines = []
            if i + 1 < len(rows):
                contact_lines.append(' '.join(str(c or '') for c in rows[i + 1]))
            if i + 2 < len(rows):
                contact_lines.append(' '.join(str(c or '') for c in rows[i + 2]))

            contact_text = ' '.join(contact_lines)

            # Extract address (before TEL or EMAIL)
            address_match = re.search(r'^(.+?)(?:TEL|EMAIL|$)', contact_text, re.IGNORECASE)
            address = address_match.group(1).strip() if address_match else ''
            address = re.sub(r'\s+', ' ', address).strip()

            phone = extract_phone(contact_text)
            email = extract_email(contact_text)

            name = facility_name or operator_name
            if name and name.strip():
                facilities.append({
                    'county': county_name,
                    'name': name.strip(),
                    'address': address[:100],
                    'email': email,
                    'phone': phone,
                    'manager': operator_name.strip() if operator_name != facility_name else '',
                    'auth_num': auth_num,
                    'capacity_tonnes': capacity,
                })

            i += 3
        else:
            i += 1

    return facilities

def main():
    print("Parsing MADR files (XLSX + XLS)...\n")

    # Install xlrd if needed
    if not HAS_XLRD:
        print("Installing xlrd...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "xlrd", "-q"], timeout=30)

    all_facilities = []
    xlsx_count = xls_count = 0

    for file_path in sorted(DATA_DIR.glob("*.*")):
        suffix = file_path.suffix.lower()
        if suffix not in ['.xlsx', '.xls']:
            continue

        # Try to open as xlsx first, fall back to xls
        facilities = []
        if suffix == '.xlsx':
            try:
                facilities = parse_xlsx_file(file_path)
                xlsx_count += 1
            except:
                if HAS_XLRD:
                    facilities = parse_xls_file(file_path)
                    xls_count += 1
        else:  # .xls
            if HAS_XLRD:
                facilities = parse_xls_file(file_path)
                xls_count += 1

        all_facilities.extend(facilities)
        if facilities:
            print(f"[{file_path.stem}] {len(facilities)}")

    print(f"\nProcessed: {xlsx_count} .xlsx + {xls_count} .xls files")
    print(f"Total extracted: {len(all_facilities)}")

    # Dedup
    seen = {}
    for fac in all_facilities:
        key = (fac['name'].lower(), fac['phone'], fac['email'])
        if key not in seen:
            seen[key] = fac

    print(f"Unique: {len(seen)}")

    # Stats
    with_email = len([f for f in seen.values() if f['email']])
    with_phone = len([f for f in seen.values() if f['phone']])
    with_both = len([f for f in seen.values() if f['email'] and f['phone']])

    print("\nContact coverage:")
    print(f"  Email: {with_email} ({with_email*100/len(seen):.1f}%)")
    print(f"  Phone: {with_phone} ({with_phone*100/len(seen):.1f}%)")
    print(f"  Both: {with_both} ({with_both*100/len(seen):.1f}%)")

    # Write
    fieldnames = ['county', 'name', 'address', 'email', 'phone', 'manager', 'auth_num', 'capacity_tonnes']
    with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for fac in sorted(seen.values(), key=lambda x: (x['county'], x['name'])):
            writer.writerow(fac)

    print(f"\nOK: {OUTPUT_CSV}")
    print("\nTop 5 sample:")
    for fac in list(seen.values())[:5]:
        print(f"  {fac['county']}: {fac['name']}")
        if fac['phone']:
            print(f"    {fac['phone']}")

if __name__ == "__main__":
    main()
