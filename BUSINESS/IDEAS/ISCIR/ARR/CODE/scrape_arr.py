"""Scrape all ARR transport operators from licente.arr.ro/publica.
Uses checkpoint to resume if interrupted.
"""
import csv, json, sys, time
from pathlib import Path
import requests
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding="utf-8")

BASE = "https://licente.arr.ro/publica"
OUTPUT = Path(__file__).parent.parent / "DATA" / "arr_raw.csv"
CHECKPOINT = Path(__file__).parent.parent / "DATA" / "arr_checkpoint.json"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
SLEEP = 0.5
MAX_PAGES = 3000
FIELDS = ["judet", "cod_fiscal", "denumire", "adresa", "localitate"]


def fetch_page(session: requests.Session, page: int) -> list[dict]:  # noqa: ARG001
    for attempt in range(3):
        try:
            r = requests.get(BASE, params={"page": page}, headers=HEADERS, timeout=20)
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
        except Exception as e:
            if attempt < 2:
                time.sleep(3)
            else:
                print(f"  page {page} failed after 3 attempts: {e}")
                return []
    return []


def save_checkpoint(page: int, rows: list[dict]) -> None:
    with open(CHECKPOINT, "w", encoding="utf-8") as f:
        json.dump({"page": page, "count": len(rows)}, f)
    with open(OUTPUT, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def load_checkpoint() -> tuple[int, list[dict]]:
    if not CHECKPOINT.exists() or not OUTPUT.exists():
        return 1, []
    try:
        cp = json.loads(CHECKPOINT.read_text())
        rows = list(csv.DictReader(open(OUTPUT, encoding="utf-8-sig")))
        print(f"Resuming from page {cp['page']} ({len(rows)} rows already)")
        return cp["page"], rows
    except Exception:
        return 1, []


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    start_page, all_rows = load_checkpoint()
    empty_streak = 0

    for page in range(start_page, MAX_PAGES + 1):
        rows = fetch_page(session, page)
        if rows:
            all_rows.extend(rows)
            empty_streak = 0
        else:
            empty_streak += 1
            if empty_streak >= 5:
                print(f"  5 empty pages at {page} — done")
                break

        if page % 50 == 0:
            print(f"  page {page} | total: {len(all_rows)}")
            save_checkpoint(page + 1, all_rows)

        time.sleep(SLEEP)

    save_checkpoint(MAX_PAGES + 1, all_rows)
    print(f"\nDone. {len(all_rows)} rows | Saved → {OUTPUT}")


if __name__ == "__main__":
    main()
