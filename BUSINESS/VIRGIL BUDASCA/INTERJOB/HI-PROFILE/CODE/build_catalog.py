#!/usr/bin/env python3
"""Build worker catalog — first name only, verified against CV text."""
import json, re

CV_FILE = r"D:\MEMORY\HI-PROFILE\DATA\cv_extracted.json"
OUTPUT = r"D:\MEMORY\HI-PROFILE\HTML\catalog_workers.html"

JUNK_FILES = {'unknown','sgaz','sgaz_1','sgaz_2','sgaz_3',
    'petroventures','petroventures_resourcessrl',
    'petroventures_resourcessrl_1','petroventures_resourcessrl_2',
    'club_antreprenor','club_antreprenor_1',
    'karl_dos_santos_1','chitra_prasad_1','taibur_bhuiyan_1',
    'taibur_bhuiyan_2','benson_chibuye_1','benson_chibuye_2',
    'benson_chibuye_3','abdelhakim_bouttar_1','maria_sicre_1',
    'rohan_kc_1','rohan_kc_3','murugan_k.murugan_2',
    'provat_mandal_9','provat_mandal_7','provat_mandal_4',
    'elie_choucair_1','nemeyemmanuel','michalzukal_1',
    'moussab_dahdi_1','cv_english','cv_agricolo_italiano',
    'cv_agricola_espanol','cv__professionnel','cv_professionnel',
    'resume_lena','resume_(vkp)','1'}

CONTACT_RE = [
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\+?\d[\d\s\-().]{8,15}\d"),
    re.compile(r"https?://\S+"),
    re.compile(r"\[REDACTED\]"),
]

CATEGORIES = {
    'Constructii': ['weld','sudor','construction','builder','mason',
        'carpenter','plumb','pipe','scaffold','concrete','beton',
        'steel','iron','painter','zugrav','facade','excavat',
        'install','montaj','electric','roofer'],
    'Productie': ['factory','machine','operator','cnc','assembl',
        'packaging','forklift','quality control','production',
        'electronic','automotive','wiring','warehouse','ambalare'],
    'Alimentar': ['butcher','meat','slaughter','baker','cook',
        'bucatar','food','restaurant','kitchen','pizz','chef',
        'catering'],
    'Logistica': ['driver','truck','transport','courier',
        'logistics','cargo','loading','delivery','shipping'],
    'Healthcare': ['nurse','medical','infirm','hospital',
        'care worker','pharma','health','clinic'],
    'Hospitality': ['hotel','waiter','bartender','barman',
        'housekeep','camerist','receptionist','barista','cleaning'],
    'Agricultura': ['farm','agri','harvest','picker','greenhouse',
        'livestock','animal','tractor','crop','garden'],
}


def get_first_name(filename):
    """Extract first name from filename."""
    f = filename.replace('.pdf','').replace('.PDF','')
    # Strip prefixes
    f = re.sub(r'^buildjobs\.eu_\d+_\d+_', '', f)
    f = re.sub(r'^\d+_\d+_', '', f)
    f = f.replace('_', ' ').replace('-', ' ').strip()
    f = re.sub(r'\s*\(\d+\)\s*$', '', f)
    f = re.sub(r'\s+\d+\s*$', '', f)
    f = f.strip()
    words = f.split()
    if not words:
        return None
    first = words[0].capitalize()
    if len(first) < 3 or not first.isalpha():
        return None
    BAD = {'resume','cv','my','professionnel','set','dos','kc',
        'club','sicre','english','painter','agricolo','agricola',
        'the','and','for','with','dear','sir','madam','hello',
        'cover','letter','doc','page','curriculum','europass',
        'official','full','soft','corporate','offer',
        'okegbenro','atolagbe','gurung','mandal','chibuye',
        'bhuiyan','thapa','choucair','darchashvili',
        'villadsen','bargayou','kolawole','ouldbara',
        'antreprenor','nekesa','sicre','krishnan',
        'santos','professionnel','lena'}
    if first.lower() in BAD:
        # Try second word
        if len(words) >= 2:
            second = words[1].capitalize()
            if len(second) >= 3 and second.isalpha() and second.lower() not in BAD:
                return second
        return None
    return first


def verify_name(first_name, cv_text):
    """Check if first name appears as standalone word in CV text."""
    pattern = r'\b' + re.escape(first_name) + r'\b'
    return bool(re.search(pattern, cv_text, re.IGNORECASE))


EMAIL_FILE = r"D:\MEMORY\HI-PROFILE\DATA\email_applicants.json"

with open(CV_FILE, encoding='utf-8') as f:
    raw = json.load(f)

# Also load email applicants
try:
    with open(EMAIL_FILE, encoding='utf-8') as f:
        email_apps = json.load(f)
except:
    email_apps = []

seen_files = set()
seen_names = set()
cvs = []

# First: email applicants (352, have profile text from subject)
for app in email_apps:
    first = app['name']
    if not first or len(first) < 3 or not first.isalpha():
        continue
    if first.lower() in seen_names:
        continue

    profile = app.get('profile', '') or app.get('account', '')
    country = app.get('country', '')
    body = f"Sector: {app.get('account','')}"
    if profile:
        body += f"\n{profile}"
    if country:
        body += f"\nCountry: {country}"
    if len(body) < 10:
        continue

    seen_names.add(first.lower())
    cvs.append({'name': first, 'text': body})

# Then: PDF CVs (39, have full CV body text)
for cv in raw:
    fname = cv.get('file', '')
    fkey = re.sub(r'_?\d+\.pdf$', '', fname.lower().replace(' ','_'))
    if fkey in JUNK_FILES or fname in seen_files:
        continue
    seen_files.add(fname)

    first = get_first_name(fname)
    if not first:
        continue

    ALL_BAD = {'resume','cv','my','professionnel','set','dos','kc',
        'club','sicre','english','painter','agricolo','agricola',
        'the','and','for','with','dear','sir','madam','hello',
        'cover','letter','doc','page','curriculum','europass',
        'official','full','soft','corporate','offer',
        'okegbenro','atolagbe','gurung','mandal','chibuye',
        'bhuiyan','thapa','choucair','darchashvili',
        'villadsen','bargayou','kolawole','ouldbara',
        'antreprenor','nekesa','sicre','krishnan',
        'santos','lena','report','builder','europe','romania',
        'denmark','norway','italy','spain','france','germany',
        'tak','new','application','job','object','projects',
        'security','multi','noreply','thank','thanks',
        'trekantsomraadet','office','info','admin','support',
        'rex','good','dear','subject','from','reply','fwd',
        'forward','sent','received','cc','bcc','attachment',
        'din','employment','email','hotel','available','alert',
        'authentication','status','zoho','raport','weekly',
        'kitchen','alicaba','hiring','please','would','like',
        'hope','looking','work','worker','position','company',
        'regarding','follow','urgent','important','daily',
        'monthly','report','notification','confirmation',
        'verification','reminder','update','newsletter',
        'unsubscribe','privacy','terms','conditions','barek'}

    # Verify against CV text
    if not verify_name(first, cv['text']) or first.lower() in ALL_BAD:
        words = fname.replace('.pdf','').replace('_',' ').split()
        found = False
        for w in words[1:]:
            alt = w.capitalize()
            if len(alt) >= 3 and alt.isalpha() and alt.lower() not in ALL_BAD and verify_name(alt, cv['text']):
                first = alt
                found = True
                break
        if not found:
            continue

    if first.lower() in ALL_BAD:
        continue

    if first.lower() in seen_names:
        continue
    seen_names.add(first.lower())

    # Clean body
    text = cv['text']
    for pat in CONTACT_RE:
        text = pat.sub('', text)
    lines = [l.strip() for l in text.split('\n')
             if l.strip() and len(l.strip()) > 2]
    body = '\n'.join(lines[:35])
    if len(body) < 50:
        continue

    cvs.append({'name': first, 'text': body})

# Classify
workers = {k: [] for k in CATEGORIES}
workers['General'] = []

for cv in cvs:
    blob = cv['text'].lower()
    placed = False
    for cat, kws in CATEGORIES.items():
        if any(kw in blob for kw in kws):
            workers[cat].append(cv)
            placed = True
            break
    if not placed:
        workers['General'].append(cv)

total = sum(len(ws) for ws in workers.values())
for cat, ws in workers.items():
    if ws:
        print(f"{cat:15} {len(ws):>3}")
print(f"{'TOTAL':15} {total:>3}")
print("\nNames:")
for cv in cvs:
    try:
        print(f"  {cv['name']}")
    except:
        pass

# HTML
html = '''<!DOCTYPE html>
<html lang="ro"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Candidati Disponibili - InterJob</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f0f23;color:#e0e0e0;font-family:Segoe UI,sans-serif;padding:20px}
.c{max-width:1000px;margin:0 auto}
h1{color:#00d4ff;text-align:center;font-size:2em;margin-bottom:5px}
.sub{text-align:center;color:#888;margin-bottom:30px}
h2{color:#ff6b35;border-bottom:2px solid #ff6b35;padding-bottom:8px;margin:35px 0 15px}
.cv{background:#16213e;border-radius:8px;padding:15px;margin:12px 0;border-left:4px solid #00d4ff;cursor:pointer}
.cv:hover{background:#1a2744}
.nm{font-weight:bold;color:#00d4ff;font-size:1.1em}
.body{color:#ccc;font-size:.85em;margin-top:8px;white-space:pre-line;line-height:1.5;max-height:120px;overflow:hidden;transition:max-height .3s}
.cv.open .body{max-height:3000px}
.toggle{color:#ff6b35;font-size:.8em;margin-top:5px;display:inline-block}
.stats{display:flex;gap:15px;justify-content:center;margin:25px 0;flex-wrap:wrap}
.st{background:#16213e;padding:12px 20px;border-radius:8px;text-align:center;min-width:120px}
.sn{font-size:1.8em;color:#00d4ff;font-weight:bold}
.sl{color:#888;font-size:.8em}
.cta{background:linear-gradient(135deg,#ff6b35,#ff4500);color:white;padding:20px;border-radius:10px;text-align:center;margin:40px 0}
.cta a{color:white;text-decoration:none;font-size:1.3em;font-weight:bold}
.cta small{display:block;margin-top:8px;opacity:.8}
footer{text-align:center;color:#555;margin-top:40px;padding:20px;border-top:1px solid #222;font-size:.85em}
</style></head><body><div class="c">
<h1>Candidati Disponibili</h1>
<p class="sub">InterJob Solutions Europe — CV-uri verificate</p>
<div class="stats">
'''
html += f'<div class="st"><div class="sn">{total}</div><div class="sl">CV-uri verificate</div></div>'
html += f'<div class="st"><div class="sn">{sum(1 for ws in workers.values() if ws)}</div><div class="sl">Categorii</div></div>'
html += '</div>'

for cat, ws in workers.items():
    if not ws:
        continue
    html += f'<h2>{cat} ({len(ws)} candidati)</h2>\n'
    for cv in ws:
        b = cv['text'][:1000].replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
        html += f'<div class="cv" onclick="this.classList.toggle(\'open\');this.querySelector(\'.toggle\').textContent=this.classList.contains(\'open\')?\'\\u25B2 inchide\':\'\\u25BC citeste mai mult\'">\n'
        html += f'<span class="nm">{cv["name"]}</span>\n'
        html += f'<div class="body">{b}</div>\n'
        html += f'<span class="toggle">&#9660; citeste mai mult</span></div>\n'

html += '''<div class="cta">
<a href="https://wa.me/33751171356">WhatsApp: +33 7 51 17 13 56</a>
<small>sau email: manpower.dristor@gmail.com | CV complete la cerere</small>
</div>
<footer>InterJob Solutions Europe | <a href="https://interjob.ro" style="color:#00d4ff">interjob.ro</a><br>
Doar prenumele afisat. CV complet disponibil dupa confirmare.</footer>
</div></body></html>'''

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"\nSaved: {OUTPUT}")
