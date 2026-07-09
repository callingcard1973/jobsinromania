---
name: content-creator
description: Generate bilingual (RO+EN) WordPress article HTML with SEO metadata, newsletter CTAs, batch translations. Returns ready-to-publish article content for both languages.
---

# Daily Content Creator Skill

## Input Requirements
Receive validated data from data-validator:
- ANOFM job count + sector distribution
- EURES jobs by country
- Run timestamp

## Article Structure (Both RO & EN)

### RO Article Template
```html
<p>Azi, <strong>23 iunie 2026</strong>, sunt disponibile <strong>5,795 locuri de muncă active în România</strong> și <strong>4,320+ oferte în Europa</strong>.</p>

<!-- Newsletter CTA -->
<div style="background:#f0f7ff;border:2px solid #0073aa;...">
  <h3>📩 Primești zilnic ofertele noi pe email</h3>
  <p>Abonează-te la newsletter-ul InterJob.ro și fii primul care află cele mai bune locuri de muncă din România și Europa.</p>
  <a href="https://interjob.ro/apply.html">Abonează-te gratuit</a>
</div>

<hr>

<h2>Locuri de muncă Construcții și IT în România — 23 iunie 2026</h2>

<h3>Construcții — 1,240 posturi</h3>
<ul>
  <li>Electrician — Bucharest (3,000 RON)</li>
  <li>Tâmplar — Iași</li>
  <li>Șef de echipă — Cluj</li>
  <li>Sudor — Constanța</li>
</ul>

<h3>IT & Tehnologie — 850 posturi</h3>
<ul>
  <li>Developer Senior — Bucharest (5,500 RON)</li>
  ...
</ul>

... (7 sectors total)

<hr>

<h2>Oferte de muncă în Europa — 23 iunie 2026</h2>
<p>Peste <strong>4,320 oferte</strong> în țările partenere.</p>

<h3>Norway</h3>
<ul>
  <li>Senior Developer — Oslo</li>
  ...
</ul>

... (EURES countries)

<!-- Newsletter CTA again -->
<div>...</div>

<!-- Apply button -->
<p style="text-align:center">
  <a href="https://interjob.ro/apply.html" style="background:#e65c00;...">Aplică acum</a>
</p>

<p style="font-size:0.8em;color:#999;text-align:center">Date actualizate zilnic. InterJob.ro</p>
```

### EN Article Template
Same structure, but:
- Title: "Job Market June 23, 2026: 5,795 Jobs in Romania + Europe Openings"
- H2: "{Top 2 Sectors} Jobs in Romania — June 23, 2026"
- ANOFM job titles translated RO → EN
- Apply button blue (#0073aa) instead of orange
- Footer: "Updated daily. InterJob.ro — European Workforce Solutions."

## Translation Pipeline

### Step 1: Batch RO → EN for ANOFM jobs
```python
from deep_translator import GoogleTranslator

# Collect all ANOFM titles that will be shown
titles_to_translate = []
for sector, jobs in by_sector.items():
    for job_dict in jobs[:4]:  # Only 4 jobs per sector
        titles_to_translate.append(job_dict['title'])

# Batch translate: concatenate with \n, translate once, split
if titles_to_translate:
    tr_en = GoogleTranslator(source="ro", target="en")
    joined = "\n".join(t[:120] for t in titles_to_translate)
    batch_result = tr_en.translate(joined[:4900])  # Google API limit ~5KB
    translated_titles = batch_result.split("\n")
    # Pad with fallbacks
    while len(translated_titles) < len(titles_to_translate):
        translated_titles.append(titles_to_translate[len(translated_titles)])
```

### Step 2: Translate EURES titles (original → RO and original → EN)
For each country's EURES jobs:
```python
orig_titles = [title for title, city in jobs[:4]]

# Translate to RO
tr_ro = GoogleTranslator(source="auto", target="ro")
ro_titles = tr_ro.translate("\n".join(t[:120] for t in orig_titles)).split("\n")
time.sleep(0.4)  # Anti rate-limit

# Translate to EN
tr_en = GoogleTranslator(source="auto", target="en")
en_titles = tr_en.translate("\n".join(t[:120] for t in orig_titles)).split("\n")
time.sleep(0.4)
```

### Step 3: Build lookup tables
```python
anofm_en = {}  # original RO title → EN translation
eures_by_lang = {}  # (country, idx) → (ro_title, en_title, city)
```

## Content Generation Functions

### build_ro_article(anofm_total, by_sector, count_sector, eures_total, by_country, today_date)
Returns: (title, slug, meta_description, focus_keyword, html_content)

**Title:** `"Piața muncii 23 iunie 2026: 5,795 locuri de muncă în România și Europa"`
**Slug:** `"piata-muncii-2026-06-23"`
**Meta:** `"Piața muncii 23 iunie 2026: 5,795 posturi active în România și 4,320+ în Europa. Construcții, IT, HoReCa, transport."` (max 155 chars)
**Focus keyword:** `"locuri de munca 23 iunie 2026"`

### build_en_article(anofm_total, by_sector, count_sector, anofm_en_translations, eures_total, by_country, eures_ro_ro_translations, today_date_en)
Returns: (title, slug, meta_description, focus_keyword, html_content)

**Title:** `"Job Market June 23, 2026: 5,795 Jobs in Romania + Europe Openings"`
**Slug:** `"job-market-2026-06-23"`
**Meta:** `"Romania job market June 23, 2026: 5,795 open positions + 4,320 in Europe. Construction, IT, HoReCa, transport."` (max 155 chars)
**Focus keyword:** `"jobs Romania Europe June 23, 2026"`

## Date Formatting

```python
from datetime import datetime

now = datetime.now()

# RO format: "23 iunie 2026"
RO_MONTHS = ["", "ianuarie", "februarie", "martie", "aprilie", "mai", "iunie", 
             "iulie", "august", "septembrie", "octombrie", "noiembrie", "decembrie"]
today_ro = f"{now.day} {RO_MONTHS[now.month]} {now.year}"

# EN format: "June 23, 2026"
today_en = now.strftime("%B %-d, %Y")  # %-d = day without leading zero
```

## Newsletter Block HTML

```python
def newsletter_block(lang: str) -> str:
    if lang == "ro":
        return '''<div style="background:#f0f7ff;border:2px solid #0073aa;border-radius:8px;padding:20px;margin:30px 0;text-align:center">
  <h3 style="margin-top:0;color:#0073aa">📩 Primești zilnic ofertele noi pe email</h3>
  <p style="margin:8px 0">Abonează-te la newsletter-ul InterJob.ro și fii primul care află cele mai bune locuri de muncă din România și Europa.</p>
  <a href="https://interjob.ro/apply.html" style="background:#0073aa;color:white;padding:10px 22px;text-decoration:none;border-radius:4px;display:inline-block;margin-top:8px">Abonează-te gratuit</a>
</div>'''
    else:  # en
        return '''<div style="background:#f0f7ff;border:2px solid #0073aa;border-radius:8px;padding:20px;margin:30px 0;text-align:center">
  <h3 style="margin-top:0;color:#0073aa">📩 Get daily job alerts by email</h3>
  <p style="margin:8px 0">Subscribe to InterJob.ro newsletter and be the first to know about new job openings in Romania and Europe.</p>
  <a href="https://interjob.ro/apply.html" style="background:#0073aa;color:white;padding:10px 22px;text-decoration:none;border-radius:4px;display:inline-block;margin-top:8px">Subscribe for free</a>
</div>'''
```

## Error Recovery

| Issue | Recovery |
|-------|----------|
| Translation fails for RO → EN | Return original RO title in EN article (human readable fallback) |
| Translation fails for EURES batch | Skip that country's jobs in EN, continue with other countries |
| Sector count > 7 | Show only top 7 by job count |
| Job title too long (> 100 chars) | Truncate to 90 chars + "…" |
| Null sector | Assign to 'altul' (Other fields) |
| Missing city | Skip city display, show only job title |
| Missing salary | Skip salary display, show only title + city |

## Output JSON

```json
{
  "status": "generated",
  "articles": {
    "ro": {
      "title": "Piața muncii 23 iunie 2026: 5,795 locuri de muncă în România și Europa",
      "slug": "piata-muncii-2026-06-23",
      "meta_description": "Piața muncii 23 iunie 2026: 5,795 posturi active în România și 4,320+ în Europa...",
      "focus_keyword": "locuri de munca 23 iunie 2026",
      "category": "Piata Muncii",
      "content_html": "<p>Azi...</p>...",
      "content_length": 8942,
      "newsletter_blocks": 2,
      "sectors_included": 7,
      "jobs_shown": 28
    },
    "en": {
      "title": "Job Market June 23, 2026: 5,795 Jobs in Romania + Europe Openings",
      "slug": "job-market-2026-06-23",
      "meta_description": "Romania job market June 23, 2026: 5,795 open positions + 4,320 in Europe...",
      "focus_keyword": "jobs Romania Europe June 23, 2026",
      "category": "Job Market",
      "content_html": "<p>Today...</p>...",
      "content_length": 9156,
      "newsletter_blocks": 2,
      "sectors_included": 7,
      "jobs_shown": 28
    }
  },
  "translations_made": 62,
  "warnings": [],
  "generation_timestamp": "2026-06-23T09:05:00Z"
}
```

## Success Criteria

✅ Both RO and EN articles generated (no nulls)  
✅ Content > 5,000 chars each  
✅ Newsletter blocks rendered with correct styling  
✅ Meta descriptions < 155 chars  
✅ All job titles have fallback if translation fails  
✅ No HTML syntax errors (`<li>` balanced, `</ul>` closed)
