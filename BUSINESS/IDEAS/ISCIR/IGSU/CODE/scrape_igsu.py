#!/usr/bin/env python3
"""
IGSU PSI — Download and parse authorized companies PDFs from cnsipc.igsu.ro
Output: DATA/igsu_psi_raw.csv
6 authorization categories, all PDF with extractable text tables.
"""

import csv
import os
import time
import logging
from pathlib import Path

import pdfplumber
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent
DATA_DIR = BASE / "DATA"
DATA_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 Chrome/124 Safari/537.36"
    )
}

# All 6 IGSU PSI authorization categories + PDF URLs
PDFS = [
    {
        "tip": "semnalizare_instalare",
        "descriere": "Instalare/intretinere semnalizare alarmare incendiu",
        "url": "https://cnsipc.igsu.ro/resources/1e75d563-debc-4f4c-8647-dd9e925bfb98.pdf",
    },
    {
        "tip": "semnalizare_proiectare",
        "descriere": "Proiectare semnalizare alarmare incendiu",
        "url": "https://cnsipc.igsu.ro/resources/b28390d9-9efb-417d-84c8-faeca64daa02.pdf",
    },
    {
        "tip": "ventilare_instalare",
        "descriere": "Instalare/intretinere ventilare fum si gaze fierbinti",
        "url": "https://cnsipc.igsu.ro/resources/20a2477f-1768-4f16-9bd2-86f5bc1af899.pdf",
    },
    {
        "tip": "ventilare_proiectare",
        "descriere": "Proiectare ventilare fum si gaze fierbinti",
        "url": "https://cnsipc.igsu.ro/resources/8aab454f-6a2e-4f27-a4ad-5931560c0b2d.pdf",
    },
    {
        "tip": "ignifugare",
        "descriere": "Ignifugare materiale combustibile",
        "url": "https://cnsipc.igsu.ro/resources/da7a795c-0d3a-49c4-9196-e30b79057600.pdf",
    },
    {
        "tip": "stingatoare",
        "descriere": "Verificare/reincarcare/reparare stingatoare incendiu",
        "url": "https://cnsipc.igsu.ro/resources/c048890f-a413-4240-b3a8-7fc5e88854e6.pdf",
    },
    {
        "tip": "autospeciale",
        "descriere": "Intretinere instalatii speciale autospeciale pompieri",
        "url": "https://cnsipc.igsu.ro/resources/24c370c1-8835-463e-a764-392b9c94da62.pdf",
    },
]

OUT_CSV = DATA_DIR / "igsu_psi_raw.csv"
CHECKPOINT_DIR = DATA_DIR / "checkpoints"
CHECKPOINT_DIR.mkdir(exist_ok=True)


def download_pdf(tip: str, url: str) -> Path:
    """Download PDF with retries, cache locally."""
    dest = CHECKPOINT_DIR / f"igsu_{tip}.pdf"
    if dest.exists():
        log.info("Cached: %s", dest.name)
        return dest
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            r.raise_for_status()
            dest.write_bytes(r.content)
            log.info("Downloaded %s (%d bytes)", dest.name, len(r.content))
            return dest
        except requests.RequestException as e:
            log.warning("Attempt %d failed for %s: %s", attempt + 1, tip, e)
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Failed to download {tip}")


def parse_pdf(pdf_path: Path, tip: str, descriere: str) -> list[dict]:
    """Extract table rows from PDF. Columns: denumire, judet, adresa, telefon, nr_autorizatie, data_emiterii."""
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            for table in tables:
                for row in table:
                    if not row or not row[0]:
                        continue
                    # Skip header rows
                    cell0 = str(row[0]).strip().upper()
                    if cell0 in ("DENUMIRE PERSOANĂ", "DENUMIRE PERSOANA", "NR. CRT", "NR.CRT"):
                        continue
                    if len(row) >= 2:
                        rows.append(
                            {
                                "denumire": str(row[0] or "").strip(),
                                "judet": str(row[1] or "").strip() if len(row) > 1 else "",
                                "adresa": str(row[2] or "").strip() if len(row) > 2 else "",
                                "telefon": str(row[3] or "").strip() if len(row) > 3 else "",
                                "nr_autorizatie": str(row[4] or "").strip() if len(row) > 4 else "",
                                "data_emiterii": str(row[5] or "").strip() if len(row) > 5 else "",
                                "tip_autorizatie": tip,
                                "descriere_autorizatie": descriere,
                            }
                        )
    log.info("Parsed %d rows from %s", len(rows), pdf_path.name)
    return rows


def main() -> None:
    all_rows: list[dict] = []

    for entry in PDFS:
        tip = entry["tip"]
        url = entry["url"]
        descriere = entry["descriere"]
        log.info("Processing: %s", tip)
        try:
            pdf_path = download_pdf(tip, url)
            time.sleep(0.5)  # polite delay between downloads
            rows = parse_pdf(pdf_path, tip, descriere)
            all_rows.extend(rows)
        except Exception as e:
            log.error("Error processing %s: %s", tip, e)

    # Deduplicate by (denumire, tip_autorizatie)
    seen: set[tuple] = set()
    deduped = []
    for r in all_rows:
        key = (r["denumire"].lower(), r["tip_autorizatie"])
        if key not in seen:
            seen.add(key)
            deduped.append(r)

    log.info("Total rows: %d, after dedup: %d", len(all_rows), len(deduped))

    fieldnames = [
        "denumire", "judet", "adresa", "telefon",
        "nr_autorizatie", "data_emiterii",
        "tip_autorizatie", "descriere_autorizatie",
    ]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(deduped)

    log.info("Saved: %s (%d rows)", OUT_CSV, len(deduped))


if __name__ == "__main__":
    main()
