#!/usr/bin/env python3
import csv
import os

data_dir = r'd:\MEMORY\IDEAS\PRODUS MONTAN\CODE\SCRAPER AGRICULTURA ECOLOGICA\DATA'
filepath = os.path.join(data_dir, 'producers_clean.csv')

print("=== CLEANED DATA SAMPLE ===\n")

with open(filepath, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        if row.get('phone') or row.get('email'):
            name = row.get('name', '')[:50]
            city = row.get('location_city', '')
            county = row.get('location_county', '')
            phone = row.get('phone', '')
            email = row.get('email', '')
            
            print(f"Name: {name}")
            print(f"Location: {city}, {county}")
            if phone:
                print(f"Phone: {phone}")
            if email:
                print(f"Email: {email}")
            print()
            
            count += 1
            if count >= 10:
                break
