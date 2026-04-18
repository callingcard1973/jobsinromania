import csv

with open(r'D:\MEMORY\DELECROIX\distribuitori_utilaje_FINAL.csv', 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    
    print(f'{"Denumire":<45} | {"Email":<35} | {"Judet":<15} | {"Telefon"}')
    print('-' * 120)
    
    count = 0
    for row in reader:
        if row.get('email'):
            name = row['denumire'][:44]
            email = row['email'][:34]
            judet = row.get('sediu_judet', '')[:14]
            phone = row.get('telefon_anaf', '')
            print(f'{name:<45} | {email:<35} | {judet:<15} | {phone}')
            count += 1
            if count >= 30:
                break
    
    print(f'\n... (total cu email: 137)')
