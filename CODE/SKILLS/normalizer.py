#!/usr/bin/env python3
"""
Data Normalizer - ASCII conversion, phone/J-number formatting
Runs automatically on Romanian data exports
"""
import sys
import csv
import re
import unicodedata
from pathlib import Path

def to_ascii(text):
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return text
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii')

def normalize_phone_ro(phone):
    """Normalize Romanian phone to +40XXXXXXXXX format."""
    if not phone:
        return phone

    # Remove all non-digits
    digits = re.sub(r'\D', '', str(phone))

    # Handle various formats
    if digits.startswith('40') and len(digits) >= 11:
        digits = digits[2:]
    elif digits.startswith('0040'):
        digits = digits[4:]

    # Remove leading zero
    if digits.startswith('0'):
        digits = digits[1:]

    # Must be 9 digits for Romanian numbers
    if len(digits) == 9 and digits[0] in '237':
        return f'+40{digits}'

    return phone  # Return original if can't normalize

def normalize_j_number(j_raw):
    """Convert J number from raw ONRC format to clean format."""
    if not j_raw:
        return j_raw

    j_str = str(j_raw).upper().strip()

    # Already in clean format?
    if re.match(r'^J\d+/\d+/\d{4}$', j_str):
        return j_str

    # Try to parse raw ONRC format: J{year4}{judet2}{nr}{check3}
    match = re.match(r'^J?(\d{4})(\d{2})(\d+)(\d{3})$', j_str.replace('J', ''))
    if match:
        year, judet, nr, _ = match.groups()
        # Judet 00 = Bucuresti (40)
        judet_int = int(judet)
        if judet_int == 0:
            judet_int = 40
        nr_int = int(nr)
        return f"J{judet_int}/{nr_int}/{year}"

    return j_raw  # Return original if can't parse

def normalize_csv(filepath, inplace=False):
    """Normalize all text fields in CSV."""
    filepath = Path(filepath)

    # Read
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        sample = f.read(4096)
        f.seek(0)
        delimiter = ';' if sample.count(';') > sample.count(',') else ','
        reader = csv.DictReader(f, delimiter=delimiter)
        rows = list(reader)
        fieldnames = reader.fieldnames

    # Detect special columns
    phone_cols = [c for c in fieldnames if 'phone' in c.lower() or 'tel' in c.lower()]
    j_cols = [c for c in fieldnames if c.lower() in ('j', 'j_number', 'reg_com', 'numar_reg')]

    # Normalize
    changes = {'ascii': 0, 'phone': 0, 'j': 0}

    for row in rows:
        for col, val in row.items():
            if not val:
                continue

            # ASCII all text
            ascii_val = to_ascii(val)
            if ascii_val != val:
                row[col] = ascii_val
                changes['ascii'] += 1
                val = ascii_val

            # Phone normalization
            if col in phone_cols:
                norm_phone = normalize_phone_ro(val)
                if norm_phone != val:
                    row[col] = norm_phone
                    changes['phone'] += 1

            # J number normalization
            if col in j_cols:
                norm_j = normalize_j_number(val)
                if norm_j != val:
                    row[col] = norm_j
                    changes['j'] += 1

    # Output
    out_path = filepath if inplace else filepath.with_suffix('.normalized.csv')

    with open(out_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter=delimiter)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Normalized {filepath.name}:")
    print(f"  ASCII conversions: {changes['ascii']}")
    print(f"  Phone normalizations: {changes['phone']}")
    print(f"  J-number normalizations: {changes['j']}")
    print(f"  Output: {out_path}")

    return changes

def main():
    if len(sys.argv) < 2:
        print("Usage: normalizer.py <file.csv> [--inplace]")
        sys.exit(1)

    filepath = sys.argv[1]
    inplace = '--inplace' in sys.argv

    normalize_csv(filepath, inplace)

if __name__ == '__main__':
    main()
