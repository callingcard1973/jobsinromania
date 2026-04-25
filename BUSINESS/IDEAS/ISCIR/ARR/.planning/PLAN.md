# ARR Transport Registry — Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task-by-task.

**Goal:** 53,942 transport operators scraped, enriched, in Postgres + CSV.

**Architecture:** Paginated HTTP scrape → raw CSV → Postgres upsert → internal DB enrich → final CSV.

**Tech Stack:** Python 3.12, requests, BeautifulSoup4, psycopg2, csv

---

### Task 1: Explore ARR site pagination

**Files:**
- Create: `D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/explore_arr.py`

- [ ] Write quick explorer to fetch page 1 and page 2, print HTML structure and detect pagination params

```python
import requests
from bs4 import BeautifulSoup

BASE = "https://licente.arr.ro/publica"
r = requests.get(BASE, timeout=15)
soup = BeautifulSoup(r.text, "html.parser")
# Print table headers
table = soup.find("table")
if table:
    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    print("Headers:", headers)
    rows = table.find_all("tr")[1:3]
    for row in rows:
        print([td.get_text(strip=True) for td in row.find_all("td")])
# Check pagination links
for a in soup.find_all("a"):
    href = a.get("href", "")
    if "pagina" in href.lower() or "page" in href.lower() or "offset" in href.lower():
        print("Pagination link:", href)
# Check for total count text
for tag in soup.find_all(["p","span","div"]):
    t = tag.get_text(strip=True)
    if any(x in t for x in ["total","Total","înregistrări","inregistrari"]):
        print("Count text:", t[:100])
```

- [ ] Run: `python D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/explore_arr.py`
- [ ] Note: exact pagination URL format, column names, row structure
- [ ] Commit: `git add . && git commit -m "feat: ARR explore pagination"`

---

### Task 2: Scrape all pages → raw CSV

**Files:**
- Create: `D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/scrape_arr.py`
- Output: `D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/DATA/arr_raw.csv`

- [ ] Write scraper (adjust URL pattern from Task 1 findings):

```python
"""Scrape all ARR transport operator pages to CSV."""
import csv, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://licente.arr.ro/publica"
# Common pagination: ?page=N or /Pagina/N or ?start=N — adjust after Task 1
PAGE_PARAM = "page"  # UPDATE after Task 1
PAGE_SIZE = 20
OUTPUT = Path(__file__).parent.parent / "DATA" / "arr_raw.csv"
HEADERS_HTTP = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SLEEP = 0.3

FIELDS = ["judet", "cod_fiscal", "denumire", "adresa", "localitate"]


def fetch_page(session, page_num: int) -> list[dict]:
    params = {PAGE_PARAM: page_num}
    r = session.get(BASE, params=params, timeout=15)
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        return []
    rows = []
    for tr in table.find_all("tr")[1:]:
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) >= 5:
            rows.append({
                "judet": tds[0],
                "cod_fiscal": tds[1],
                "denumire": tds[2],
                "adresa": tds[3],
                "localitate": tds[4],
            })
    return rows


def main():
    session = requests.Session()
    session.headers.update(HEADERS_HTTP)

    all_rows = []
    page = 1
    consecutive_empty = 0

    while consecutive_empty < 3:
        rows = fetch_page(session, page)
        if not rows:
            consecutive_empty += 1
            page += 1
            continue
        consecutive_empty = 0
        all_rows.extend(rows)
        if page % 50 == 0:
            print(f"Page {page} | Total: {len(all_rows)}")
        page += 1
        time.sleep(SLEEP)

    print(f"\nDone. {len(all_rows)} rows")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(all_rows)
    print(f"Saved → {OUTPUT}")


if __name__ == "__main__":
    main()
```

- [ ] After Task 1 — update `PAGE_PARAM` and URL pattern to match actual pagination
- [ ] Run: `python D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/scrape_arr.py`
- [ ] Verify: `arr_raw.csv` has ~53,000+ rows
- [ ] Commit: `git add . && git commit -m "feat: ARR scraper raw CSV 53K operators"`

---

### Task 3: Import raw CSV → Postgres table

**Files:**
- Create: `D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/import_arr_db.py`

- [ ] Write importer:

```python
"""Import arr_raw.csv into interjob_master.arr_operators."""
import csv, sys
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values

sys.stdout.reconfigure(encoding="utf-8")

INPUT = Path(__file__).parent.parent / "DATA" / "arr_raw.csv"
DB = {"host": "localhost", "port": 5433, "dbname": "interjob_master",
      "user": "postgres", "password": "postgres"}

CREATE_SQL = """
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
"""

UPSERT_SQL = """
INSERT INTO arr_operators (judet, cod_fiscal, denumire, adresa, localitate)
VALUES %s
ON CONFLICT (cod_fiscal) DO UPDATE SET
    judet = EXCLUDED.judet,
    denumire = EXCLUDED.denumire,
    adresa = EXCLUDED.adresa,
    localitate = EXCLUDED.localitate,
    scraped_at = NOW();
"""


def main():
    with open(INPUT, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    print(f"Loaded {len(rows)} rows from CSV")

    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute(CREATE_SQL)
    conn.commit()

    batch = [
        (r["judet"], r["cod_fiscal"], r["denumire"], r["adresa"], r["localitate"])
        for r in rows
    ]
    execute_values(cur, UPSERT_SQL, batch, page_size=500)
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM arr_operators")
    count = cur.fetchone()[0]
    print(f"arr_operators table: {count} rows")
    conn.close()


if __name__ == "__main__":
    main()
```

- [ ] Run: `python D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/import_arr_db.py`
- [ ] Verify: table exists, count ~53K
- [ ] Commit: `git add . && git commit -m "feat: ARR import to Postgres arr_operators table"`

---

### Task 4: Enrich with internal DB emails

**Files:**
- Create: `D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/enrich_arr.py`
- Output: `D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/DATA/arr_final.csv`

- [ ] Write enricher (same pattern as ANCOM enrich_internal.py):

```python
"""Enrich arr_operators with emails from companies_clean."""
import csv, sys
from pathlib import Path
import psycopg2

sys.stdout.reconfigure(encoding="utf-8")

OUTPUT = Path(__file__).parent.parent / "DATA" / "arr_final.csv"
DB = {"host": "localhost", "port": 5433, "dbname": "interjob_master",
      "user": "postgres", "password": "postgres"}

FIELDS = ["judet", "cod_fiscal", "denumire", "adresa", "localitate",
          "email", "telefon", "sursa_contact"]


def enrich_batch(cur, rows: list[dict]) -> list[dict]:
    cuis = [r["cod_fiscal"] for r in rows if r["cod_fiscal"]]
    if not cuis:
        return rows

    cur.execute(
        "SELECT cui, email, phone FROM companies_clean "
        "WHERE cui = ANY(%s) AND country = 'RO' AND email IS NOT NULL AND email != ''",
        (cuis,)
    )
    lookup = {row[0]: {"email": row[1], "telefon": row[2] or ""} for row in cur.fetchall()}

    enriched = []
    for r in rows:
        match = lookup.get(r["cod_fiscal"], {})
        r = dict(r)
        r["email"] = match.get("email", "")
        r["telefon"] = match.get("telefon", "")
        r["sursa_contact"] = "companies_clean" if r["email"] else ""
        enriched.append(r)
    return enriched


def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()

    cur.execute("SELECT judet, cod_fiscal, denumire, adresa, localitate FROM arr_operators ORDER BY id")
    rows = [{"judet": r[0], "cod_fiscal": r[1], "denumire": r[2],
             "adresa": r[3], "localitate": r[4]} for r in cur.fetchall()]
    print(f"Loaded {len(rows)} rows from arr_operators")

    BATCH = 1000
    enriched = []
    for i in range(0, len(rows), BATCH):
        batch = enrich_batch(cur, rows[i:i+BATCH])
        enriched.extend(batch)
        if (i + BATCH) % 10000 == 0:
            found = sum(1 for r in enriched if r["email"])
            print(f"  {i+BATCH}/{len(rows)} enriched | emails: {found}")

    # Update DB
    cur.executemany(
        "UPDATE arr_operators SET email=%s, telefon=%s, sursa_contact=%s WHERE cod_fiscal=%s",
        [(r["email"], r["telefon"], r["sursa_contact"], r["cod_fiscal"]) for r in enriched]
    )
    conn.commit()
    conn.close()

    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(enriched)

    with_email = sum(1 for r in enriched if r["email"])
    print(f"\nDone. Email: {with_email} ({with_email*100//len(enriched)}%) | Saved → {OUTPUT}")


if __name__ == "__main__":
    main()
```

- [ ] Run: `python D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/CODE/enrich_arr.py`
- [ ] Verify: `arr_final.csv` has email column populated
- [ ] Commit: `git add . && git commit -m "feat: ARR enrich with companies_clean emails"`

---

### Task 5: Quality check + summary

- [ ] Run stats:

```bash
python -c "
import csv
rows = list(csv.DictReader(open('D:/MEMORY/BUSINESS/IDEAS/ISCIR/ARR/DATA/arr_final.csv', encoding='utf-8-sig')))
total = len(rows)
emails = sum(1 for r in rows if r['email'])
phones = sum(1 for r in rows if r['telefon'])
print(f'Total: {total}')
print(f'Email: {emails} ({emails*100//total}%)')
print(f'Phone: {phones} ({phones*100//total}%)')
from collections import Counter
print('Top judete:', Counter(r['judet'] for r in rows).most_common(5))
"
```

- [ ] Update memory: `C:/Users/apami/.claude/projects/D--MEMORY/memory/arr_session.md`
- [ ] Final commit: `git add . && git commit -m "feat: ARR 53K operators scraped enriched DB + CSV"`
