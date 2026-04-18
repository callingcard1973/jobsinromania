import requests, re, html as htmlmod
s = requests.Session()
s.verify = False
import urllib3
urllib3.disable_warnings()

# List page
r = s.get("https://beneficiar.fonduri-ue.ro:8080/proiecte/1/entry?search_form_id=1&limitstart=0")
ids = re.findall(r"details/1/(\d+)/", r.text)
total_m = re.search(r"din\s+(\d+)", r.text)
print(f"Page 1: {len(ids)} projects, total: {total_m.group(1) if total_m else '?'}")

# Detail page - raw HTML analysis
r2 = s.get(f"https://beneficiar.fonduri-ue.ro:8080/proiecte/details/1/17367/")
text = r2.text

# Find key fields by surrounding text
for label in ["Beneficiar:", "Cod SMIS", "Contact:", "Telefon:", "Adresa:", "Judet:", "Localitate:", "Program", "Data contract", "E-mail"]:
    idx = text.find(label)
    if idx > 0:
        snippet = text[idx:idx+300]
        snippet = re.sub(r"<[^>]+>", " ", snippet)
        snippet = re.sub(r"\s+", " ", snippet).strip()[:120]
        print(f"  {label:20s} -> {snippet}")

# Email decode
print("\nEmail JS decode:")
addy_lines = re.findall(r"(addy\d+ = .*?;)", text)
for line in addy_lines:
    decoded = htmlmod.unescape(re.sub(r"'|\s|\+|var\s+", "", line.split("=",1)[1].rstrip(";")))
    print(f"  {decoded}")

# Total pages
print(f"\n1599 projects / 10 per page = 160 pages to scrape")
print(f"Each has: company, contact, phone, email, address, judet, program, SMIS code")
