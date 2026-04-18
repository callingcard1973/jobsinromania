import csv, re, unicodedata

def norm(s):
    s = s.lower().strip()
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r'^(comuna|oras|municipiul|municipiu|orasul)\s+', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def valid_email(e):
    e = e.strip()
    return '@' in e and len(e) >= 6

# Load file 1
f1 = []
with open(r'D:\MEMORY\Z.AI\PRIMARII\primarii_romania.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        f1.append(row)

# Load file 2
f2 = []
with open(r'D:\MEMORY\Z.AI\PRIMARII\primarii_datagov_emails.csv', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        f2.append(row)

print(f"File1: {len(f1)} rows, File2: {len(f2)} rows")

# Build lookup from file1 by normalized name
lookup = {}
for row in f1:
    key = norm(row.get('name', ''))
    if key:
        lookup[key] = row

# Collect all records: start with file1
records = {}  # email -> best record

def add(name, email, county, phone):
    if not valid_email(email):
        return
    e = email.strip().lower()
    if e not in records:
        records[e] = {'name': name.strip(), 'email': e, 'county': county.strip(), 'phone': phone.strip()}

for row in f1:
    emails = [e.strip() for e in re.split(r'[;,]', row.get('email', '')) if e.strip()]
    for e in emails:
        add(row.get('name',''), e, row.get('county',''), row.get('phone',''))

for row in f2:
    emails = [e.strip() for e in re.split(r'[;,]', row.get('email', '')) if e.strip()]
    name = row.get('name', '')
    county = row.get('judet', '')
    phone = ''
    # Try to enrich from file1 lookup
    key = norm(name)
    if key in lookup:
        f1r = lookup[key]
        if not county:
            county = f1r.get('county', '')
        if not phone:
            phone = f1r.get('phone', '')
    for e in emails:
        add(name, e, county, phone)

out = sorted(records.values(), key=lambda r: r['name'])
print(f"Unique valid emails: {len(out)}")

with open(r'D:\MEMORY\BUSINESS\BOGDAN GAVRA\primarii_campanie.csv', 'w', newline='', encoding='utf-8-sig') as f:
    w = csv.DictWriter(f, fieldnames=['name','email','county','phone'])
    w.writeheader()
    w.writerows(out)

print("Saved to primarii_campanie.csv")
