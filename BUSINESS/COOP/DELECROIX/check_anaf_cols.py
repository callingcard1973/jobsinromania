import csv

# Check ANAF full columns and first row
with open(r'D:\MEMORY\CLAUDE\OPT\AGRI_SCRAPERS\anaf_all_romania_full.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    print('Columns:', reader.fieldnames)
    row = next(reader)
    print()
    for k, v in row.items():
        print(f'{k}: {repr(v)}')
