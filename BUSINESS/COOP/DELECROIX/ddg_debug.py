import urllib.request, urllib.parse, re

query = 'AGROMEC DRAGASANI email'
url = 'https://html.duckduckgo.com/html/?' + urllib.parse.urlencode({'q': query})
req = urllib.request.Request(url, headers={
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
})
with urllib.request.urlopen(req, timeout=15) as resp:
    html = resp.read().decode('utf-8', errors='ignore')

with open(r'D:\MEMORY\DELECROIX\ddg_sample.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'Page size: {len(html)}')
print(f'Saved to ddg_sample.html')

# Try different patterns
patterns = [
    (r'result__a.*?href="([^"]+)"', 'result__a href'),
    (r'result__url[^>]*>([^<]+)', 'result__url'),
    (r'href="(https?://[^"]+)"', 'all links'),
    (r'<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>', 'all anchors'),
]

for pat, name in patterns:
    matches = re.findall(pat, html)
    print(f'\n{name}: {len(matches)} matches')
    for m in matches[:5]:
        print(f'  {str(m)[:100]}')
