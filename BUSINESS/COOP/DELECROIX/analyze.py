import re, os

def extract_text(html):
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL|re.IGNORECASE)
    html = re.sub(r'<[^>]+>', ' ', html)
    html = re.sub(r'&nbsp;', ' ', html)
    html = re.sub(r'&amp;', '&', html)
    html = re.sub(r'&euro;', 'EUR', html)
    html = re.sub(r'&[a-z]+;', ' ', html)
    html = re.sub(r'\s+', ' ', html)
    return html.strip()

base = r'D:\MEMORY\DELECROIX'

for fname in ['marcoser.html', 'agritech.html', 'eqinto.html', 'greengarden.html', 'agrialianta.html']:
    path = os.path.join(base, fname)
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = extract_text(f.read())
        print(f"=== {fname} ({len(text)} chars) ===")
        print(text[:2000])
        print("...")
        print()
    except Exception as e:
        print(f"{fname}: ERROR {e}")
        print()
