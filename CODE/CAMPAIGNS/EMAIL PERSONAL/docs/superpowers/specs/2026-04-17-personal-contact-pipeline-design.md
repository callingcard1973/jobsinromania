# Personal Contact Pipeline — Design Spec
Date: 2026-04-17

## Overview

Staged pipeline to clean, deduplicate, score, segment, and export 8,083 personal Google Contacts into usable CSV + HTML viewer. Optional enrichment against raspibig `interjob_master` PostgreSQL.

## Source Data

- File: `contacts-fruitnature.csv` (Google Takeout export)
- 8,083 rows, 4,508 with email, 4,432 with phone, 482 with org
- 88 duplicate emails, garbled names, mixed personal/business contacts

## Architecture

6 independent staged scripts. Each reads previous stage's CSV output. Any stage can be re-run independently.

```
contacts-fruitnature.csv
  → 01_clean.py       → cleaned.csv
  → 02_dedupe.py      → deduped.csv
  → 03_score.py       → scored.csv
  → 04_segment.py     → segmented.csv
  → 05_export.py      → export/index.html + export/*.csv
  → 06_enrich.py      → enriched.csv (optional, needs raspibig)
```

## Stage 1: Clean (`01_clean.py`)

- Strip garbled name prefixes: `(*)`, `(%)`, HTML entities (`&amp;`, `&#39;`, etc.), emoji
- Normalize emails: lowercase, strip whitespace
- Remove rows with no email AND no phone
- Unescape HTML in Notes field
- Output: `cleaned.csv`

## Stage 2: Deduplicate (`02_dedupe.py`)

- Primary dedup key: normalized email (lowercase)
- Secondary key: normalized phone
- Merge strategy on conflict: keep longest name, concatenate notes (pipe-separated), preserve all emails/phones across rows
- Output: `deduped.csv`

## Stage 3: Score (`03_score.py`)

Score 0–100 per contact. Columns added: `score`.

| Signal | Points |
|--------|--------|
| Business email (non-personal domain) | +30 |
| Has organization name | +20 |
| Has phone | +15 |
| Has notes or category tag | +15 |
| Starred contact | +20 |
| Has 2nd email | +10 |
| Garbled/empty name | -20 |
| Airbnb guest domain | -30 |

Personal domains excluded from +30: gmail.com, yahoo.*, hotmail.com, msn.com, live.com, googlemail.com, mail.ru, aol.com, icloud.com.

Score clamped to [0, 100].

Output: `scored.csv`

## Stage 4: Segment (`04_segment.py`)

Assign one primary `segment` column per contact. Priority order (first match wins):

| Segment | Rule |
|---------|------|
| `business_austria` | `Objekt:` in notes OR domain in (aon.at, euroweb.at, etc.) |
| `business_ro` | `.ro` email domain OR Romanian org keyword |
| `business_intl` | Non-personal domain, not AT/RO |
| `recruitment` | org title contains: recruiter, HR, staffing, hiring, talent, placement |
| `personal_close` | Starred OR Messenger ID in notes OR `lista_contacte_email` category |
| `school` | `colegiliceu` in notes category |
| `airbnb` | `airbnb.com` email domain |
| `phone_only` | No email, has phone |
| `junk` | Score < 20 OR (no name AND no org) |

Output: `segmented.csv`

## Stage 5: Export (`05_export.py`)

### CSV export
- `export/<segment>.csv` — one file per segment, sorted by score descending

### HTML viewer (`export/index.html`)
- Self-contained single file (no server required)
- Segment tabs across top (workers catalog pattern)
- Tab badge shows contact count
- Each tab: live-searchable table (JS filter on name/email/org/score)
- Columns: Name, Email, Phone, Organization, Score, Segment, Notes (truncated 60 chars)
- Score badge: green (≥70), yellow (40–69), red (<40)

## Stage 6: Enrich (`06_enrich.py`) — Optional

Requires SSH tunnel or direct access to raspibig PostgreSQL (`interjob_master`, port 5432, host 192.168.100.21).

- Exact email match → tag `known_employer` or `known_worker`
- Domain match → tag `known_company`
- Adds columns: `in_master_db` (bool), `master_db_role`, `master_db_id`
- Score boost: +25 for contacts found in master DB
- Output: `enriched.csv`
- Graceful fallback: if raspibig unreachable, skip with warning, output unchanged segmented.csv

## File Layout

```
EMAIL PERSONAL/
  contacts-fruitnature.csv      # source (read-only)
  cleaned.csv
  deduped.csv
  scored.csv
  segmented.csv
  enriched.csv                  # optional
  export/
    index.html
    business_austria.csv
    business_ro.csv
    business_intl.csv
    recruitment.csv
    personal_close.csv
    school.csv
    airbnb.csv
    phone_only.csv
    junk.csv
  docs/superpowers/specs/
    2026-04-17-personal-contact-pipeline-design.md
```

## Dependencies

- Python 3.12 (stdlib only + `psycopg2` for stage 6)
- No pandas — use csv module (keeps scripts light, <250 lines each)
- Each script max 250 lines

## Success Criteria

- `cleaned.csv`: no garbled names, valid emails
- `deduped.csv`: zero duplicate emails
- `segmented.csv`: every contact has a segment
- `export/index.html`: opens in browser, all tabs work, search filters live
- Stage 6 optional — pipeline completes without raspibig
