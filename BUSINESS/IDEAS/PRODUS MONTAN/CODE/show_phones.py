#!/usr/bin/env python3
import csv

filepath = r'd:\MEMORY\IDEAS\PRODUS MONTAN\CODE\SCRAPER AGRICULTURA ECOLOGICA\DATA\producers_enriched.csv'
with open(filepath, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    count = 0
    print("=== Sample Normalized Phone Numbers ===\n")
    for row in reader:
        if row.get('phone', '').strip():
            name = row.get('name', '')[:40]
            phone = row.get('phone', '')
            print(f"{name:40} | {phone}")
            count += 1
            if count >= 10:
                break
