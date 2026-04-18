#!/usr/bin/env python3
"""
Upload real project photos to agroevolution.com WP Media Library
Then patch spatii-verzi (373) and mobilier-urban (383) pages with images.
"""
import urllib.request, base64, json, mimetypes
from pathlib import Path

WP_BASE = 'https://agroevolution.com/wp-json/wp/v2'
TOKEN = base64.b64encode(b'apaminerala:unzQWjnSo2EEGA0cajdXoW2P').decode()
HEADERS_BASE = {'Authorization': f'Basic {TOKEN}'}

IMAGES_DIR = Path(r'D:\MEMORY\BUSINESS\BOGDAN GAVRA\CATALOGS\IMAGES')

# All images — last one (11.26.16) is pergola/mobilier, rest are playground
images = sorted(IMAGES_DIR.glob('*.jpeg'))

def upload_image(path: Path, alt_text: str, title: str) -> dict | None:
    data = path.read_bytes()
    slug = path.stem.replace(' ', '-').replace('(', '').replace(')', '').replace('.', '')
    req = urllib.request.Request(
        f'{WP_BASE}/media',
        data=data,
        headers={
            **HEADERS_BASE,
            'Content-Type': 'image/jpeg',
            'Content-Disposition': f'attachment; filename="{slug}.jpg"',
        }
    )
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        result = json.loads(resp.read())
        media_id = result['id']
        # Update alt text + title
        patch_data = json.dumps({'alt_text': alt_text, 'title': title}).encode('utf-8')
        patch_req = urllib.request.Request(
            f'{WP_BASE}/media/{media_id}',
            data=patch_data,
            headers={**HEADERS_BASE, 'Content-Type': 'application/json; charset=utf-8'},
            method='POST'
        )
        urllib.request.urlopen(patch_req, timeout=30)
        print(f'  OK ID {media_id} - {title}')
        print(f'     URL: {result["source_url"]}')
        return result
    except Exception as e:
        print(f'  ERR {path.name}: {e}')
        return None

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

print('=== Uploading playground photos (spatii-verzi) ===')
playground_ids = []
playground_urls = []

playground_alts = [
    'Loc de joacă pentru copii — structură pirat cu tobogan, AVP Park Vidra Ilfov',
    'Parc de joacă colorat — structuri roșii și galbene cu tobogane multiple, Vidra Ilfov',
    'Echipamente loc de joacă copii — turn cu plasă și tobogan, parc comunal',
    'Ansamblu joacă copii cu structuri colorate și spații multiple, AVP Park Romania',
    'Loc de joacă modern pentru primărie — tobogane și structuri de cățărat, Vidra',
    'Parc copii cu structuri de cățărat și tobogane — instalare primărie Ilfov',
    'Echipamente joacă certificare EN 1176 — structuri colorate parc public',
    'Loc de joacă pentru copii — structuri de cățărat și tobogane, parc comunal Romania',
    'Parc de joacă premium — ansamblu complex cu turnuri și tobogane multiple',
    'Loc de joacă copii — structuri individuale și tobogane, parc public primărie',
    'Leagăne pentru copii — echipamente joacă certificare EN 1176, parc comunal',
]

playground_titles = [
    'Loc de joacă pirat AVP Park — Vidra Ilfov',
    'Structuri joacă roșu-galben — Vidra Ilfov',
    'Turn plasă tobogan — parc comunal',
    'Ansamblu joacă colorat AVP Park',
    'Loc de joacă modern primărie',
    'Structuri cățărat tobogane — Ilfov',
    'Echipamente EN 1176 parc public',
    'Parc copii comunal — Romania',
    'Ansamblu premium loc de joacă',
    'Structuri tobogane parc public',
    'Leagăne EN 1176 parc comunal',
]

for i, img in enumerate(images[:-1]):  # first 11 = playground
    print(f'\n[{i+1}/11] {img.name}')
    result = upload_image(img, playground_alts[i], playground_titles[i])
    if result:
        playground_ids.append(result['id'])
        playground_urls.append(result['source_url'])

print('\n=== Uploading pergola/mobilier urban photo ===')
mobilier_result = upload_image(
    images[-1],
    'Pergolă și mobilier urban — bancă parc și echipamente fitness exterior, Vidra Ilfov',
    'Pergolă mobilier urban — Vidra Ilfov'
)

print('\n=== Summary ===')
print(f'Playground IDs: {playground_ids}')
print(f'Playground URLs: {playground_urls[:3]}...')
if mobilier_result:
    print(f'Mobilier ID: {mobilier_result["id"]}')
    print(f'Mobilier URL: {mobilier_result["source_url"]}')

# Save results for next step
results = {
    'playground_ids': playground_ids,
    'playground_urls': playground_urls,
    'mobilier_id': mobilier_result['id'] if mobilier_result else None,
    'mobilier_url': mobilier_result['source_url'] if mobilier_result else None,
}
Path(r'D:\MEMORY\BUSINESS\BOGDAN GAVRA\CODE\upload_results.json').write_text(
    json.dumps(results, indent=2), encoding='utf-8'
)
print('\nResults saved to upload_results.json')
