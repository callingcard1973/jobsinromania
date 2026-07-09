#!/usr/bin/env python3
import csv
import os

# Use direct path based on workspace structure
filepath = r'd:\MEMORY\IDEAS\PRODUS MONTAN\CODE\SCRAPER AGRICULTURA ECOLOGICA\DATA\producers.csv'

# Read a sample of rows to check phone field distribution
phone_sample = []
with open(filepath, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        if i < 20:  # Check first 20 rows
            phone = row.get('phone', '')
            email = row.get('email', '')
            if phone or email:
                phone_sample.append((row['name'][:50], phone, email))
                
print(f"Sample of {len(phone_sample)} producers with contact info (first 20 rows):")
for name, phone, email in phone_sample:
    print(f"  {name}: phone={phone[:50] if phone else 'EMPTY'}, email={email[:30] if email else 'EMPTY'}")

if not phone_sample:
    print("No phone/email found in first 20 rows - checking if any exist in entire file...")
    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        total = 0
        with_phone = 0
        with_email = 0
        for row in reader:
            total += 1
            if row.get('phone', '').strip():
                with_phone += 1
            if row.get('email', '').strip():
                with_email += 1
    print(f"\nTotal producers: {total}")
    print(f"With phone: {with_phone} ({100*with_phone/total:.1f}%)")
    print(f"With email: {with_email} ({100*with_email/total:.1f}%)")
