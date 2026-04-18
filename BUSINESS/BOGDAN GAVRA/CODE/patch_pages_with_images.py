#!/usr/bin/env python3
"""
Patch spatii-verzi (373) and mobilier-urban (383) pages:
- spatii-verzi: add gallery of 6 best playground photos + set featured image
- mobilier-urban: set featured image (pergola) + add image to page
"""
import urllib.request, base64, json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WP_BASE = 'https://agroevolution.com/wp-json/wp/v2'
TOKEN = base64.b64encode(b'apaminerala:unzQWjnSo2EEGA0cajdXoW2P').decode()
HEADERS = {'Authorization': f'Basic {TOKEN}', 'Content-Type': 'application/json; charset=utf-8'}

# Best 6 playground photos for gallery
GALLERY_IDS = [386, 387, 388, 389, 390, 391]
GALLERY_URLS = [
    'https://agroevolution.com/wp-content/uploads/2026/04/WhatsApp-Image-2026-04-17-at-112614-AM-1-1.jpg',
    'https://agroevolution.com/wp-content/uploads/2026/04/WhatsApp-Image-2026-04-17-at-112614-AM-2.jpg',
    'https://agroevolution.com/wp-content/uploads/2026/04/WhatsApp-Image-2026-04-17-at-112614-AM-3.jpg',
    'https://agroevolution.com/wp-content/uploads/2026/04/WhatsApp-Image-2026-04-17-at-112614-AM.jpg',
    'https://agroevolution.com/wp-content/uploads/2026/04/WhatsApp-Image-2026-04-17-at-112615-AM-1.jpg',
    'https://agroevolution.com/wp-content/uploads/2026/04/WhatsApp-Image-2026-04-17-at-112615-AM-2.jpg',
]
GALLERY_ALTS = [
    'Loc de joacă pirat AVP Park — Vidra Ilfov',
    'Structuri joacă roșu-galben — Vidra Ilfov',
    'Turn plasă tobogan — parc comunal',
    'Ansamblu joacă colorat AVP Park',
    'Loc de joacă modern primărie',
    'Structuri cățărat tobogane — Ilfov',
]

MOBILIER_ID = 397
MOBILIER_URL = 'https://agroevolution.com/wp-content/uploads/2026/04/WhatsApp-Image-2026-04-17-at-112616-AM.jpg'

def wp_get(page_id):
    req = urllib.request.Request(f'{WP_BASE}/pages/{page_id}?context=edit', headers={'Authorization': f'Basic {TOKEN}'})
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read())

def wp_patch(page_id, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        f'{WP_BASE}/pages/{page_id}',
        data=data, headers=HEADERS, method='POST'
    )
    resp = urllib.request.urlopen(req, timeout=30)
    return json.loads(resp.read())

# ─── Build gallery block HTML ───────────────────────────────
def gallery_block(ids, urls, alts):
    ids_str = ','.join(str(i) for i in ids)
    imgs = ''.join(
        f'<!-- wp:image {{"id":{ids[i]},"sizeSlug":"large","linkDestination":"none"}} -->\n'
        f'<figure class="wp-block-image size-large">'
        f'<img src="{urls[i]}" alt="{alts[i]}" class="wp-image-{ids[i]}"/>'
        f'</figure>\n<!-- /wp:image -->\n'
        for i in range(len(ids))
    )
    return (
        f'\n<!-- wp:heading -->\n<h2>Proiecte Realizate — Parcuri Copii în România</h2>\n<!-- /wp:heading -->\n\n'
        f'<!-- wp:paragraph -->\n<p>Fotografii reale din parcuri instalate de echipa noastră. Toate echipamentele respectă EN 1176, ISO 9001 și poartă marcaj CE.</p>\n<!-- /wp:paragraph -->\n\n'
        f'<!-- wp:gallery {{"ids":[{ids_str}],"columns":3,"linkTo":"none"}} -->\n'
        f'<figure class="wp-block-gallery has-nested-images columns-3 is-cropped">\n'
        + imgs +
        f'</figure>\n<!-- /wp:gallery -->\n'
    )

# ─── 1. Patch spatii-verzi (373) ────────────────────────────
print('Fetching spatii-verzi page (373)...')
page = wp_get(373)
old_content = page['content']['raw']

gallery_html = gallery_block(GALLERY_IDS, GALLERY_URLS, GALLERY_ALTS)
new_content = old_content + gallery_html

print('Patching spatii-verzi...')
result = wp_patch(373, {
    'content': new_content,
    'featured_media': GALLERY_IDS[0],  # first playground photo
})
print(f'  OK — spatii-verzi updated. Link: {result["link"]}')

# ─── 2. Patch mobilier-urban (383) ─────────────────────────
print('\nFetching mobilier-urban page (383)...')
page2 = wp_get(383)
old_content2 = page2['content']['raw']

# Add single image block before the first heading
mobilier_img_block = (
    f'<!-- wp:image {{"id":{MOBILIER_ID},"sizeSlug":"large","linkDestination":"none","align":"wide"}} -->\n'
    f'<figure class="wp-block-image alignwide size-large">'
    f'<img src="{MOBILIER_URL}" alt="Pergola si mobilier urban — bancă parc și echipamente fitness, Vidra Ilfov" class="wp-image-{MOBILIER_ID}"/>'
    f'<figcaption>Pergolă + bănci + fitness exterior — instalare reală, Vidra, Ilfov</figcaption>'
    f'</figure>\n<!-- /wp:image -->\n\n'
)

# Insert after first paragraph
insert_after = '<!-- /wp:paragraph -->'
idx = old_content2.find(insert_after)
if idx != -1:
    new_content2 = old_content2[:idx + len(insert_after)] + '\n\n' + mobilier_img_block + old_content2[idx + len(insert_after):]
else:
    new_content2 = mobilier_img_block + old_content2

print('Patching mobilier-urban...')
result2 = wp_patch(383, {
    'content': new_content2,
    'featured_media': MOBILIER_ID,
})
print(f'  OK — mobilier-urban updated. Link: {result2["link"]}')

print('\nDone! Pages live:')
print('  https://agroevolution.com/spatii-verzi/')
print('  https://agroevolution.com/mobilier-urban/')
