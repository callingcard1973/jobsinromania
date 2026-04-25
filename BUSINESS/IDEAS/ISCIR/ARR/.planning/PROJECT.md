# ARR Transport Registry Scraper

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task.

**Goal:** Scrape all 53,942 licensed transport operators from licente.arr.ro/publica into a Postgres table + enriched CSV with emails from internal DB.

**Architecture:** HTTP pagination scraper (20/page → ~2,700 pages) → CSV → Postgres import → internal DB enrichment (companies_clean CUI match) → final CSV.

**Tech Stack:** Python 3.12, requests, BeautifulSoup, psycopg2, csv, concurrent.futures

---

## Constraints

- Output dir: `D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/DATA/`
- Code dir: `D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/`
- Max 250 lines per file
- DB: interjob_master @ localhost:5433
- Max 5 concurrent workers (site may throttle)
- Re-run safe: upsert by cod_fiscal

## Columns

From licente.arr.ro/publica table:
- `judet` — county
- `cod_fiscal` — CUI/tax ID
- `denumire` — company name
- `adresa` — address
- `localitate` — city

After enrichment:
- `email` — from companies_clean
- `telefon` — from companies_clean
- `sursa_contact` — source

## Target Table

```sql
CREATE TABLE IF NOT EXISTS arr_operators (
    id SERIAL PRIMARY KEY,
    judet TEXT,
    cod_fiscal TEXT UNIQUE,
    denumire TEXT,
    adresa TEXT,
    localitate TEXT,
    email TEXT,
    telefon TEXT,
    sursa_contact TEXT,
    scraped_at TIMESTAMPTZ DEFAULT NOW()
);
```
