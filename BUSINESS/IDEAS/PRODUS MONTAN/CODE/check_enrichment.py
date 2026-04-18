#!/usr/bin/env python3
import csv
filepath = r'd:\MEMORY\IDEAS\PRODUS MONTAN\CODE\SCRAPER AGRICULTURA ECOLOGICA\DATA\producers_enriched.csv'
with open(filepath, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    total = 0
    phones = 0
    for row in reader:
        total += 1
        if row.get('phone','').strip(): phones += 1
print('Total rows', total)
print('Rows with phone', phones)

# show some rows with phone
with open(filepath, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    count=0
    for row in reader:
        if row.get('phone'):
            print(row['name'][:50], row['phone'])
            count+=1
            if count>=5: break
