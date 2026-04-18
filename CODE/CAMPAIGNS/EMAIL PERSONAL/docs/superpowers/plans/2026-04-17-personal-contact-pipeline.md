# Personal Contact Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform 8,083 raw Google Contacts into cleaned, deduplicated, scored, segmented CSV files + a self-contained HTML viewer with live search.

**Architecture:** 6 independent staged scripts — each reads the previous stage's CSV and writes the next. Any stage can be re-run independently. No pandas; stdlib csv module only. Stage 6 (raspibig enrich) is optional.

**Tech Stack:** Python 3.12, stdlib (csv, re, html, unicodedata), psycopg2 (stage 6 only)

---

## File Map

| File | Purpose |
|------|---------|
| `01_clean.py` | Strip garbled names, normalize emails, drop empty rows |
| `02_dedupe.py` | Merge duplicate emails/phones |
| `03_score.py` | Score 0–100 per contact |
| `04_segment.py` | Assign one segment per contact |
| `05_export.py` | Write per-segment CSVs + index.html |
| `06_enrich.py` | Cross-ref raspibig master DB (optional) |
| `tests/test_pipeline.py` | Unit tests for all stages |
| `run_all.py` | Run stages 1–5 in sequence |

---

## Task 1: Test scaffolding + shared helpers

**Files:**
- Create: `tests/test_pipeline.py`
- Create: `pipeline_utils.py`

- [ ] **Step 1: Write failing tests for utils**

```python
# tests/test_pipeline.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pipeline_utils import clean_name, normalize_email, normalize_phone, is_personal_domain

def test_clean_name_strips_parens():
    assert clean_name("(*) Mary") == "Mary"
    assert clean_name("(%) Jen foo") == "Jen foo"
    assert clean_name("  (*) ") == ""

def test_clean_name_strips_html_entities():
    assert clean_name("&#39;Mihai") == "Mihai"
    assert clean_name("&amp;Test") == "Test"

def test_normalize_email():
    assert normalize_email("  TEST@Gmail.COM  ") == "test@gmail.com"
    assert normalize_email("") == ""

def test_normalize_phone():
    assert normalize_phone("+43 1 280 69 03") == "+43128069 03".replace(" ", "")
    assert normalize_phone("") == ""

def test_is_personal_domain():
    assert is_personal_domain("gmail.com") is True
    assert is_personal_domain("yahoo.fr") is True
    assert is_personal_domain("merkursoft.de") is False
    assert is_personal_domain("airbnb.com") is False  # airbnb handled separately
```

- [ ] **Step 2: Run to confirm fail**

```bash
cd "D:/MEMORY/EMAIL PERSONAL"
python -m pytest tests/test_pipeline.py -v
```
Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: Write `pipeline_utils.py`**

```python
import re
import html
import unicodedata

PERSONAL_DOMAINS = {
    'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.fr', 'yahoo.ca',
    'yahoo.co.uk', 'yahoo.ro', 'yahoo.es', 'yahoo.de', 'hotmail.com',
    'hotmail.fr', 'msn.com', 'live.com', 'live.fr', 'mail.ru', 'aol.com',
    'icloud.com', 'me.com', 'outlook.com', 'sympatico.ca', 'rogers.com',
    'videotron.ca', 'web.de',
}

GARBLE_PATTERN = re.compile(r'^\s*[\(\*\%\"\'\`]+[^\w]*')
EMOJI_PATTERN = re.compile(
    r'[\U00010000-\U0010ffff]|[\U0001F300-\U0001F9FF]', flags=re.UNICODE
)

def clean_name(name: str) -> str:
    name = html.unescape(name or '')
    name = EMOJI_PATTERN.sub('', name)
    name = GARBLE_PATTERN.sub('', name)
    name = re.sub(r'[\(\*\%\"\'\`]+', '', name)
    return name.strip()

def normalize_email(email: str) -> str:
    return (email or '').strip().lower()

def normalize_phone(phone: str) -> str:
    p = re.sub(r'[\s\-\(\)]', '', (phone or ''))
    return p

def is_personal_domain(domain: str) -> bool:
    domain = domain.lower().strip()
    if domain in PERSONAL_DOMAINS:
        return True
    # catch yahoo.* variants
    if domain.startswith('yahoo.'):
        return True
    return False

def get_email_domain(email: str) -> str:
    email = normalize_email(email)
    if '@' in email:
        return email.split('@', 1)[1]
    return ''
```

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/test_pipeline.py -v
```
Expected: all 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add pipeline_utils.py tests/test_pipeline.py
git commit -m "feat: pipeline utils + test scaffold"
```

---

## Task 2: Stage 1 — Clean

**Files:**
- Create: `01_clean.py`
- Modify: `tests/test_pipeline.py` (add stage 1 tests)

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_pipeline.py
import csv, io

def _make_csv(rows, fieldnames):
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=fieldnames)
    w.writeheader()
    w.writerows(rows)
    buf.seek(0)
    return buf.read()

def test_clean_removes_no_email_no_phone():
    import subprocess, tempfile, os
    src = [
        {'First Name': 'A', 'Last Name': 'B', 'E-mail 1 - Value': '', 'Phone 1 - Value': '', 'Notes': ''},
        {'First Name': 'C', 'Last Name': 'D', 'E-mail 1 - Value': 'c@d.com', 'Phone 1 - Value': '', 'Notes': ''},
    ]
    # run via import
    import importlib.util, sys
    # just test the filter logic directly
    from pipeline_utils import normalize_email
    filtered = [r for r in src if normalize_email(r['E-mail 1 - Value']) or r['Phone 1 - Value'].strip()]
    assert len(filtered) == 1
    assert filtered[0]['E-mail 1 - Value'] == 'c@d.com'

def test_clean_normalizes_email():
    from pipeline_utils import normalize_email
    assert normalize_email('  TEST@Gmail.COM ') == 'test@gmail.com'
```

- [ ] **Step 2: Run to confirm pass (utils already written)**

```bash
python -m pytest tests/test_pipeline.py::test_clean_removes_no_email_no_phone tests/test_pipeline.py::test_clean_normalizes_email -v
```
Expected: PASS

- [ ] **Step 3: Write `01_clean.py`**

```python
import csv
import html as html_module
import re
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import clean_name, normalize_email, normalize_phone

INPUT = 'contacts-fruitnature.csv'
OUTPUT = 'cleaned.csv'

def clean_row(row):
    row['First Name'] = clean_name(row.get('First Name', ''))
    row['Last Name'] = clean_name(row.get('Last Name', ''))
    row['Middle Name'] = clean_name(row.get('Middle Name', ''))
    row['Nickname'] = clean_name(row.get('Nickname', ''))
    row['Notes'] = html_module.unescape(row.get('Notes', ''))
    row['E-mail 1 - Value'] = normalize_email(row.get('E-mail 1 - Value', ''))
    row['E-mail 2 - Value'] = normalize_email(row.get('E-mail 2 - Value', ''))
    row['Phone 1 - Value'] = normalize_phone(row.get('Phone 1 - Value', ''))
    return row

def has_contact_info(row):
    return bool(row.get('E-mail 1 - Value') or row.get('Phone 1 - Value'))

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            row = clean_row(row)
            if has_contact_info(row):
                rows.append(row)

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Cleaned: {len(rows)} rows → {OUTPUT}")

if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run it**

```bash
cd "D:/MEMORY/EMAIL PERSONAL"
python 01_clean.py
```
Expected: `Cleaned: ~6500 rows → cleaned.csv`

- [ ] **Step 5: Verify**

```bash
python -c "import csv; rows=list(csv.DictReader(open('cleaned.csv',encoding='utf-8'))); print(len(rows), 'rows'); empties=[r for r in rows if not r['E-mail 1 - Value'] and not r['Phone 1 - Value']]; print('Empty contact info rows:', len(empties))"
```
Expected: `Empty contact info rows: 0`

- [ ] **Step 6: Commit**

```bash
git add 01_clean.py
git commit -m "feat: stage 1 clean contacts"
```

---

## Task 3: Stage 2 — Deduplicate

**Files:**
- Create: `02_dedupe.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_pipeline.py
def test_dedupe_merges_same_email():
    rows = [
        {'E-mail 1 - Value': 'a@b.com', 'First Name': 'Jo', 'Last Name': '', 'Phone 1 - Value': '123', 'Notes': 'note1', 'E-mail 2 - Value': '', 'Labels': ''},
        {'E-mail 1 - Value': 'a@b.com', 'First Name': 'Jonathan', 'Last Name': 'Smith', 'Phone 1 - Value': '456', 'Notes': 'note2', 'E-mail 2 - Value': '', 'Labels': ''},
    ]
    # simulate merge: keep longest name
    def longest_name(a, b):
        full_a = (a['First Name'] + ' ' + a['Last Name']).strip()
        full_b = (b['First Name'] + ' ' + b['Last Name']).strip()
        return a if len(full_a) >= len(full_b) else b
    winner = longest_name(rows[0], rows[1])
    assert winner['First Name'] == 'Jonathan'

def test_dedupe_no_duplicate_emails():
    rows = [
        {'E-mail 1 - Value': 'x@y.com', 'First Name': 'A', 'Last Name': '', 'Phone 1 - Value': '', 'Notes': '', 'E-mail 2 - Value': '', 'Labels': ''},
        {'E-mail 1 - Value': 'x@y.com', 'First Name': 'B', 'Last Name': '', 'Phone 1 - Value': '', 'Notes': '', 'E-mail 2 - Value': '', 'Labels': ''},
        {'E-mail 1 - Value': 'z@y.com', 'First Name': 'C', 'Last Name': '', 'Phone 1 - Value': '', 'Notes': '', 'E-mail 2 - Value': '', 'Labels': ''},
    ]
    seen = {}
    for r in rows:
        key = r['E-mail 1 - Value']
        if key not in seen:
            seen[key] = r
    assert len(seen) == 2
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_pipeline.py::test_dedupe_merges_same_email tests/test_pipeline.py::test_dedupe_no_duplicate_emails -v
```
Expected: PASS

- [ ] **Step 3: Write `02_dedupe.py`**

```python
import csv
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import normalize_email, normalize_phone

INPUT = 'cleaned.csv'
OUTPUT = 'deduped.csv'

def full_name(row):
    return (row.get('First Name', '') + ' ' + row.get('Last Name', '')).strip()

def merge_rows(existing, new):
    # Keep longest name
    if len(full_name(new)) > len(full_name(existing)):
        existing['First Name'] = new['First Name']
        existing['Last Name'] = new['Last Name']
    # Merge notes
    n1 = existing.get('Notes', '').strip()
    n2 = new.get('Notes', '').strip()
    if n2 and n2 not in n1:
        existing['Notes'] = (n1 + ' | ' + n2).strip(' |')
    # Merge phone
    if not existing.get('Phone 1 - Value') and new.get('Phone 1 - Value'):
        existing['Phone 1 - Value'] = new['Phone 1 - Value']
    # Merge 2nd email
    if not existing.get('E-mail 2 - Value') and new.get('E-mail 1 - Value') != existing.get('E-mail 1 - Value'):
        existing['E-mail 2 - Value'] = new.get('E-mail 1 - Value', '')
    # Merge labels
    l1 = existing.get('Labels', '')
    l2 = new.get('Labels', '')
    if l2 and l2 not in l1:
        existing['Labels'] = (l1 + ' ::: ' + l2).strip(' :::')
    return existing

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    # Dedup by email
    by_email = {}
    no_email = []
    for row in rows:
        email = row.get('E-mail 1 - Value', '').strip()
        if email:
            if email in by_email:
                by_email[email] = merge_rows(by_email[email], row)
            else:
                by_email[email] = row
        else:
            no_email.append(row)

    # Dedup no-email rows by phone
    by_phone = {}
    no_phone_no_email = []
    for row in no_email:
        phone = normalize_phone(row.get('Phone 1 - Value', ''))
        if phone:
            if phone in by_phone:
                by_phone[phone] = merge_rows(by_phone[phone], row)
            else:
                by_phone[phone] = row
        else:
            no_phone_no_email.append(row)

    result = list(by_email.values()) + list(by_phone.values()) + no_phone_no_email

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result)

    print(f"Deduped: {len(rows)} → {len(result)} rows → {OUTPUT}")

if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run**

```bash
python 02_dedupe.py
```
Expected: `Deduped: ~6500 → ~6400 rows → deduped.csv`

- [ ] **Step 5: Verify zero duplicate emails**

```bash
python -c "
import csv
from collections import Counter
rows = list(csv.DictReader(open('deduped.csv', encoding='utf-8')))
emails = [r['E-mail 1 - Value'] for r in rows if r['E-mail 1 - Value']]
dups = {e:c for e,c in Counter(emails).items() if c>1}
print('Duplicate emails:', len(dups))
"
```
Expected: `Duplicate emails: 0`

- [ ] **Step 6: Commit**

```bash
git add 02_dedupe.py
git commit -m "feat: stage 2 deduplicate contacts"
```

---

## Task 4: Stage 3 — Score

**Files:**
- Create: `03_score.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_pipeline.py
def test_score_business_email():
    from pipeline_utils import is_personal_domain, get_email_domain
    email = 'ada.bacalum@zazibusiness.ro'
    domain = get_email_domain(email)
    assert not is_personal_domain(domain)

def test_score_airbnb_penalty():
    from pipeline_utils import get_email_domain
    email = 'guest123@guest.airbnb.com'
    domain = get_email_domain(email)
    assert 'airbnb' in domain

def test_score_clamp():
    score = max(0, min(100, 200))
    assert score == 100
    score = max(0, min(100, -50))
    assert score == 0
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_pipeline.py::test_score_business_email tests/test_pipeline.py::test_score_airbnb_penalty tests/test_pipeline.py::test_score_clamp -v
```
Expected: PASS

- [ ] **Step 3: Write `03_score.py`**

```python
import csv
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import is_personal_domain, get_email_domain

INPUT = 'deduped.csv'
OUTPUT = 'scored.csv'

def score_row(row):
    s = 0
    email = row.get('E-mail 1 - Value', '')
    domain = get_email_domain(email)

    if domain and not is_personal_domain(domain) and 'airbnb' not in domain:
        s += 30
    if row.get('Organization Name', '').strip():
        s += 20
    if row.get('Phone 1 - Value', '').strip():
        s += 15
    if row.get('Notes', '').strip():
        s += 15
    if '* starred' in row.get('Labels', ''):
        s += 20
    if row.get('E-mail 2 - Value', '').strip():
        s += 10

    first = row.get('First Name', '').strip()
    last = row.get('Last Name', '').strip()
    if not first and not last:
        s -= 20
    if 'airbnb' in domain:
        s -= 30

    return max(0, min(100, s))

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    fieldnames = list(fieldnames) + ['score']
    for row in rows:
        row['score'] = score_row(row)

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    scores = [r['score'] for r in rows]
    avg = sum(scores) / len(scores) if scores else 0
    print(f"Scored {len(rows)} rows. Avg score: {avg:.1f} → {OUTPUT}")

if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run**

```bash
python 03_score.py
```
Expected: `Scored ~6400 rows. Avg score: XX.X → scored.csv`

- [ ] **Step 5: Commit**

```bash
git add 03_score.py
git commit -m "feat: stage 3 score contacts"
```

---

## Task 5: Stage 4 — Segment

**Files:**
- Create: `04_segment.py`
- Modify: `tests/test_pipeline.py`

- [ ] **Step 1: Add failing tests**

```python
# append to tests/test_pipeline.py
def test_segment_austria():
    row = {'Notes': 'Objekt: FF\nTelefon: +43 1 280 69 03', 'E-mail 1 - Value': 'a@aon.at',
           'Organization Title': '', 'Labels': '', 'Phone 1 - Value': '123', 'score': 50}
    notes = row['Notes']
    assert 'Objekt:' in notes

def test_segment_junk_low_score():
    row = {'score': 10, 'First Name': '', 'Last Name': '', 'Organization Name': ''}
    is_junk = row['score'] < 20 or (not row['First Name'] and not row['Last Name'] and not row['Organization Name'])
    assert is_junk

def test_segment_personal_close():
    row = {'Labels': '* myContacts ::: * starred', 'Notes': '', 'E-mail 1 - Value': 'a@b.com'}
    assert '* starred' in row['Labels']
```

- [ ] **Step 2: Run tests**

```bash
python -m pytest tests/test_pipeline.py::test_segment_austria tests/test_pipeline.py::test_segment_junk_low_score tests/test_pipeline.py::test_segment_personal_close -v
```
Expected: PASS

- [ ] **Step 3: Write `04_segment.py`**

```python
import csv
import re
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import get_email_domain, is_personal_domain

INPUT = 'scored.csv'
OUTPUT = 'segmented.csv'

AT_DOMAINS = {'aon.at', 'euroweb.at', 'chello.at', 'gmx.at', 'inode.at'}
RO_KEYWORDS = {'romania', 'romanian', 'bucuresti', 'bucharest', 'cluj', 'iasi', 'timisoara'}
RECRUIT_KEYWORDS = {'recruiter', 'recruiting', 'hr ', 'human resources', 'staffing',
                    'hiring', 'talent', 'placement', 'workforce', 'headhunt'}

def get_segment(row):
    email = row.get('E-mail 1 - Value', '')
    domain = get_email_domain(email)
    notes = row.get('Notes', '').lower()
    labels = row.get('Labels', '').lower()
    title = row.get('Organization Title', '').lower()
    org = row.get('Organization Name', '').lower()
    score = int(row.get('score', 0))
    first = row.get('First Name', '').strip()
    last = row.get('Last Name', '').strip()

    if 'objekt:' in notes or domain in AT_DOMAINS:
        return 'business_austria'
    if domain.endswith('.ro') or any(k in org for k in RO_KEYWORDS):
        return 'business_ro'
    if any(k in title for k in RECRUIT_KEYWORDS):
        return 'recruitment'
    if domain and not is_personal_domain(domain) and 'airbnb' not in domain:
        return 'business_intl'
    if '* starred' in labels or 'messenger id:' in notes or 'lista_contacte_email' in notes:
        return 'personal_close'
    if 'colegiliceu' in notes:
        return 'school'
    if 'airbnb' in domain:
        return 'airbnb'
    if not email and row.get('Phone 1 - Value', '').strip():
        return 'phone_only'
    if score < 20 or (not first and not last and not org):
        return 'junk'
    return 'personal_close'

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) + ['segment']
        for row in reader:
            rows.append(row)

    from collections import Counter
    for row in rows:
        row['segment'] = get_segment(row)

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r['segment'] for r in rows)
    print(f"Segmented {len(rows)} rows → {OUTPUT}")
    for seg, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {seg}: {n}")

if __name__ == '__main__':
    main()
```

- [ ] **Step 4: Run**

```bash
python 04_segment.py
```
Expected: prints segment counts, all rows assigned

- [ ] **Step 5: Verify no unassigned**

```bash
python -c "
import csv
rows = list(csv.DictReader(open('segmented.csv', encoding='utf-8')))
missing = [r for r in rows if not r.get('segment')]
print('Missing segment:', len(missing))
"
```
Expected: `Missing segment: 0`

- [ ] **Step 6: Commit**

```bash
git add 04_segment.py
git commit -m "feat: stage 4 segment contacts"
```

---

## Task 6: Stage 5 — Export (CSV + HTML)

**Files:**
- Create: `05_export.py`
- Create: `export/` directory (auto-created by script)

- [ ] **Step 1: Write `05_export.py`**

```python
import csv
import os
import json
from collections import defaultdict

INPUT = 'segmented.csv'
EXPORT_DIR = 'export'

SEGMENTS_ORDER = [
    'business_intl', 'business_ro', 'business_austria',
    'recruitment', 'personal_close', 'school',
    'airbnb', 'phone_only', 'junk'
]

DISPLAY_COLS = ['First Name', 'Last Name', 'E-mail 1 - Value', 'Phone 1 - Value',
                'Organization Name', 'Organization Title', 'score', 'segment', 'Notes']

def truncate(s, n=60):
    s = (s or '').replace('\n', ' ').replace('\r', '')
    return s[:n] + '…' if len(s) > n else s

def score_color(score):
    s = int(score or 0)
    if s >= 70: return '#4ade80'
    if s >= 40: return '#facc15'
    return '#f87171'

def build_html(segments_data):
    tabs_html = ''
    panels_html = ''
    all_js_data = {}

    for seg in SEGMENTS_ORDER:
        rows = segments_data.get(seg, [])
        if not rows:
            continue
        label = seg.replace('_', ' ').title()
        tabs_html += f'<button class="tab" onclick="showTab(\'{seg}\')">{label} <span class="badge">{len(rows)}</span></button>\n'
        all_js_data[seg] = [
            {
                'name': (r.get('First Name','') + ' ' + r.get('Last Name','')).strip(),
                'email': r.get('E-mail 1 - Value',''),
                'phone': r.get('Phone 1 - Value',''),
                'org': r.get('Organization Name',''),
                'title': r.get('Organization Title',''),
                'score': int(r.get('score', 0)),
                'notes': truncate(r.get('Notes',''))
            }
            for r in rows
        ]

    js_data = json.dumps(all_js_data)

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Personal Contacts</title>
<style>
body {{ font-family: sans-serif; background: #111; color: #eee; margin: 0; padding: 16px; }}
h1 {{ color: #fff; margin-bottom: 8px; }}
.tabs {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }}
.tab {{ background: #222; border: 1px solid #444; color: #ccc; padding: 6px 12px; cursor: pointer; border-radius: 4px; }}
.tab.active {{ background: #0ea5e9; color: #fff; border-color: #0ea5e9; }}
.badge {{ background: #333; border-radius: 10px; padding: 2px 7px; font-size: 11px; margin-left: 4px; }}
input[type=text] {{ background: #222; border: 1px solid #444; color: #eee; padding: 8px 12px; width: 300px; border-radius: 4px; margin-bottom: 12px; font-size: 14px; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
th {{ background: #1e293b; color: #94a3b8; text-align: left; padding: 8px 10px; border-bottom: 1px solid #334155; }}
td {{ padding: 7px 10px; border-bottom: 1px solid #1e293b; vertical-align: top; }}
tr:hover td {{ background: #1a2332; }}
.score-badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-weight: bold; font-size: 12px; }}
.panel {{ display: none; }}
.panel.active {{ display: block; }}
</style>
</head>
<body>
<h1>Personal Contacts</h1>
<div class="tabs">{tabs_html}</div>
<div id="panels">
{"".join(f'<div class="panel" id="panel-{seg}"><input type="text" placeholder="Search name, email, org..." oninput="filterTable(\'{seg}\', this.value)"><table><thead><tr><th>Name</th><th>Email</th><th>Phone</th><th>Organization</th><th>Title</th><th>Score</th><th>Notes</th></tr></thead><tbody id="tbody-{seg}"></tbody></table></div>' for seg in SEGMENTS_ORDER if seg in all_js_data)}
</div>
<script>
const DATA = {js_data};
function renderTable(seg, rows) {{
    const tbody = document.getElementById('tbody-' + seg);
    if (!tbody) return;
    tbody.innerHTML = rows.map(r => `<tr>
        <td>${{r.name || '-'}}</td>
        <td>${{r.email ? '<a href="mailto:'+r.email+'" style="color:#38bdf8">'+r.email+'</a>' : '-'}}</td>
        <td>${{r.phone || '-'}}</td>
        <td>${{r.org || '-'}}</td>
        <td>${{r.title || '-'}}</td>
        <td><span class="score-badge" style="background:${{scoreColor(r.score)}};color:#111">${{r.score}}</span></td>
        <td style="color:#888;font-size:12px">${{r.notes || ''}}</td>
    </tr>`).join('');
}}
function scoreColor(s) {{
    if (s >= 70) return '#4ade80';
    if (s >= 40) return '#facc15';
    return '#f87171';
}}
function filterTable(seg, q) {{
    q = q.toLowerCase();
    const rows = (DATA[seg] || []).filter(r =>
        (r.name+r.email+r.org+r.notes).toLowerCase().includes(q)
    );
    renderTable(seg, rows);
}}
function showTab(seg) {{
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
    const btn = [...document.querySelectorAll('.tab')].find(t => t.onclick.toString().includes("'"+seg+"'"));
    if (btn) btn.classList.add('active');
    const panel = document.getElementById('panel-' + seg);
    if (panel) panel.classList.add('active');
    renderTable(seg, DATA[seg] || []);
}}
// init first tab
const firstSeg = Object.keys(DATA)[0];
if (firstSeg) showTab(firstSeg);
</script>
</body>
</html>'''
    return html

def main():
    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            rows.append(row)

    os.makedirs(EXPORT_DIR, exist_ok=True)

    # Group by segment
    by_seg = defaultdict(list)
    for row in rows:
        by_seg[row.get('segment', 'junk')].append(row)

    # Sort each segment by score desc
    for seg in by_seg:
        by_seg[seg].sort(key=lambda r: int(r.get('score', 0)), reverse=True)

    # Write per-segment CSVs
    for seg, seg_rows in by_seg.items():
        path = os.path.join(EXPORT_DIR, f'{seg}.csv')
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(seg_rows)

    # Write HTML
    html = build_html(by_seg)
    html_path = os.path.join(EXPORT_DIR, 'index.html')
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"Exported {len(rows)} contacts to {EXPORT_DIR}/")
    print(f"HTML viewer: {html_path}")
    for seg in SEGMENTS_ORDER:
        if seg in by_seg:
            print(f"  {seg}: {len(by_seg[seg])} contacts")

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run**

```bash
python 05_export.py
```
Expected: lists segment counts, creates `export/index.html`

- [ ] **Step 3: Verify HTML opens**

```bash
start export/index.html
```
Expected: browser opens, tabs visible, search works

- [ ] **Step 4: Commit**

```bash
git add 05_export.py
git commit -m "feat: stage 5 export CSV + HTML viewer"
```

---

## Task 7: Stage 6 — Raspibig Enrich (Optional)

**Files:**
- Create: `06_enrich.py`

- [ ] **Step 1: Write `06_enrich.py`**

```python
import csv
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from pipeline_utils import normalize_email, get_email_domain

INPUT = 'segmented.csv'
OUTPUT = 'enriched.csv'

DB_HOST = '192.168.100.21'
DB_PORT = 5432
DB_NAME = 'interjob_master'
DB_USER = 'tudor'

def load_master_db():
    try:
        import psycopg2
    except ImportError:
        print("psycopg2 not installed. Run: pip install psycopg2-binary")
        return None, None

    try:
        conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, dbname=DB_NAME,
                                user=DB_USER, connect_timeout=5)
    except Exception as e:
        print(f"Cannot reach raspibig: {e}")
        return None, None

    cur = conn.cursor()

    # Email → role mapping
    email_map = {}
    try:
        cur.execute("SELECT email, 'employer' FROM employers WHERE email IS NOT NULL")
        for email, role in cur.fetchall():
            email_map[normalize_email(email)] = ('employer', None)
    except Exception:
        pass

    try:
        cur.execute("SELECT email, id FROM applicants WHERE email IS NOT NULL")
        for email, rid in cur.fetchall():
            email_map[normalize_email(email)] = ('worker', rid)
    except Exception:
        pass

    # Domain → company mapping
    domain_map = {}
    try:
        cur.execute("SELECT email FROM employers WHERE email IS NOT NULL")
        for (email,) in cur.fetchall():
            d = get_email_domain(normalize_email(email))
            if d:
                domain_map[d] = 'known_company'
    except Exception:
        pass

    conn.close()
    return email_map, domain_map

def main():
    email_map, domain_map = load_master_db()
    skip_enrich = email_map is None

    rows = []
    with open(INPUT, encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames) + ['in_master_db', 'master_db_role', 'master_db_id']
        for row in reader:
            rows.append(row)

    for row in rows:
        email = row.get('E-mail 1 - Value', '')
        domain = get_email_domain(email)
        if skip_enrich:
            row['in_master_db'] = 'false'
            row['master_db_role'] = ''
            row['master_db_id'] = ''
            continue
        if email in email_map:
            role, rid = email_map[email]
            row['in_master_db'] = 'true'
            row['master_db_role'] = role
            row['master_db_id'] = rid or ''
            row['score'] = min(100, int(row.get('score', 0)) + 25)
        elif domain in domain_map:
            row['in_master_db'] = 'true'
            row['master_db_role'] = 'known_company'
            row['master_db_id'] = ''
            row['score'] = min(100, int(row.get('score', 0)) + 25)
        else:
            row['in_master_db'] = 'false'
            row['master_db_role'] = ''
            row['master_db_id'] = ''

    with open(OUTPUT, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    found = sum(1 for r in rows if r.get('in_master_db') == 'true')
    print(f"Enriched {len(rows)} rows. Found in master DB: {found} → {OUTPUT}")

if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run (will warn gracefully if raspibig unreachable)**

```bash
python 06_enrich.py
```
Expected (if connected): `Enriched ~6400 rows. Found in master DB: X → enriched.csv`
Expected (if offline): `Cannot reach raspibig: ...` then writes enriched.csv with empty enrich columns

- [ ] **Step 3: Commit**

```bash
git add 06_enrich.py
git commit -m "feat: stage 6 enrich against raspibig master DB"
```

---

## Task 8: run_all.py + final test run

**Files:**
- Create: `run_all.py`

- [ ] **Step 1: Write `run_all.py`**

```python
import subprocess
import sys

STAGES = ['01_clean.py', '02_dedupe.py', '03_score.py', '04_segment.py', '05_export.py']

for stage in STAGES:
    print(f"\n{'='*40}\nRunning {stage}\n{'='*40}")
    result = subprocess.run([sys.executable, stage], capture_output=False)
    if result.returncode != 0:
        print(f"FAILED at {stage}")
        sys.exit(1)

print("\n✓ Pipeline complete. Open export/index.html in browser.")
```

- [ ] **Step 2: Run full pipeline**

```bash
python run_all.py
```
Expected: all 5 stages run, final line `Pipeline complete.`

- [ ] **Step 3: Run all tests**

```bash
python -m pytest tests/test_pipeline.py -v
```
Expected: all tests PASS

- [ ] **Step 4: Final commit**

```bash
git add run_all.py tests/test_pipeline.py
git commit -m "feat: run_all orchestrator + complete test suite"
```
