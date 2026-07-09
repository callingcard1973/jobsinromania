# DAILY ROUNDUP — CLAUDE.md

**v1.0 | 2026-06-03 | Articol zilnic piața muncii pe interjob.ro**

---

## Ce face

Publică zilnic 2 articole pe interjob.ro:
- **RO** (română): "Piața muncii 3 iunie 2026: 5,795 locuri de muncă în România și Europa"
- **EN** (engleză): "Job Market June 3, 2026: 5,795 Jobs in Romania + Europe Openings"

Surse de date:
- **România**: PostgreSQL `ij_jobs` (sursă: anofm, ~5,800 posturi active) — titluri deja în română
- **Europa**: CSV-uri EURES din `/opt/ACTIVE/SCRAPER_DATA/csv/EURES/` — titluri traduse RO+EN via `deep_translator`

---

## Fișiere

| Fișier | Locație raspibig | Scop |
|--------|-----------------|------|
| `daily_roundup.py` | `/opt/ACTIVE/EVENT_PUBLISHER/` | Script principal |

---

## Structură articol

```
[Intro paragraph cu numere totale]
[Newsletter CTA box]
<h2>Top 2 sectoare Jobs in Romania — dată</h2>
  <h3>Sector 1 — N posturi</h3>
    <ul> titluri exemplu </ul>
  ... (7 sectoare total)
<h2>European Job Openings — dată</h2>
  <h3>Norway</h3> <ul>...</ul>
  ... (6 țări)
[Newsletter CTA box]
[Apply Now button]
```

---

## SEO implementat

| Element | Valoare |
|---------|---------|
| Title tag | "Job Market June 3, 2026: 5,795 Jobs in Romania + Europe Openings" |
| Meta description | Max 155 chars, conține numere reale |
| H1 | Identic cu title |
| H2 | Include top 2 sectoare + dată (keyword-rich) |
| Canonical | Auto-setat de WordPress |
| Yoast focus kw | "jobs Romania Europe June 3, 2026" |
| Yoast meta desc | PATCH separat după POST (limitare API Yoast) |
| Slug | `job-market-YYYY-MM-DD` / `piata-muncii-YYYY-MM-DD` |

---

## Traducere EURES

Titlurile EURES (norvegiană/daneză/suedeză/finlandeză) sunt traduse **batch** via `deep_translator.GoogleTranslator`:
- Cerere: toate titlurile dintr-o țară concatenate cu `\n`
- Răspuns split pe linii → 2 variante (ro + en) per articol
- Sleep 0.4s între țări (anti rate-limit Google)

---

## DB tracking

Tabel `wp_roundup_log` în interjob_master:
```sql
roundup_date DATE, lang CHAR(2), wp_post_id INT
UNIQUE(roundup_date, lang)
```
Nu publică de două ori în aceeași zi pentru același lang.

---

## Cron (pe raspibig)

```bash
0 9 * * * cd /opt/ACTIVE/EVENT_PUBLISHER && python3 daily_roundup.py >> /opt/ACTIVE/INFRA/LOGS/wp_roundup.log 2>&1
```

---

## Comenzi manuale

```bash
# Publică ambele limbi
python3 daily_roundup.py

# Publică doar EN
python3 daily_roundup.py --lang en

# Test fără publicare
python3 daily_roundup.py --dry-run --force

# Re-publică forțat (chiar dacă azi există deja)
python3 daily_roundup.py --force
```

---

## Newsletter CTA

Fiecare articol conține 2 blocuri newsletter (sus + jos) cu link la `https://interjob.ro/apply.html`.
Când FastAPI e live, acțiunea formularului devine `https://api.interjob.ro/subscribe`.

---

---

## 🤖 HARNESS: Daily Roundup Orchestrator (v1.0 | 2026-06-23)

**Obiectiv:** Automatizează publicarea zilnică a articolelor de piață a muncii bilingve (RO+EN) pe interjob.ro cu validare, generare conținut, publishing + monitoring.

**Arhitectură:** 4 agenți (data-validator, content-creator, publisher, monitor) orkestrați de `daily-roundup-orchestrator` skill.

**Trigger:** Rulează automat la 09:00 UTC via cron pe raspibig, sau manual: `daily-roundup-orchestrator` skill pentru rulări ad-hoc.

**Locații:**
- Agenți: `.claude/agents/` (4 fișiere .md)
- Skills: `.claude/skills/` (5 foldere cu SKILL.md)
- Orchestrator: `.claude/skills/daily-roundup-orchestrator/SKILL.md`
- Workspace: `_workspace/` (output JSON files for resumability)

**Phase workflow:**
```
01: Data Validator (ANOFM + EURES validation)
    ↓
02: Content Creator (RO + EN article generation + translation)
    ↓
03: Publisher (WordPress REST API + Yoast metadata)
    ↓
04: Monitor (TTFB, load time, alerts)
    ↓
Final Report (JSON + console output)
```

**Schimbări din original:**
| Data | Schimbare | Motiv |
|------|----------|-------|
| 2026-06-23 | Construire harness complet | Modularizare, testabilitate, monitoring |

---

## Îmbunătățiri posibile (viitor)

- Imagini featured auto-generate (job sector icon)
- Internal links către joburile individuale din același sector
- Structured data `JobPosting` schema per sector
- A/B test titluri (cu/fără cifre)
- PostHog analytics integration (view tracking per article)
