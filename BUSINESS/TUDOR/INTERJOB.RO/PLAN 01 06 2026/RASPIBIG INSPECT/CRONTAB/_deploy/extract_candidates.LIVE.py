#!/usr/bin/env python3
"""Orchestrate CV extraction: PDF → JSON + CSV + HTML. Zero LLM."""

import json
import csv
import logging
from pathlib import Path

from cv_parsers import extract_text, parse_candidate, safe_name
from cv_html import candidate_page, index_page

BASE_DIR      = Path(__file__).parent
CV_SOURCES = [
    Path("/opt/ACTIVE/FARMWORKERS/candidates"),
    Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/APPLICANTS"),
    Path("/opt/ACTIVE/FARMWORKERS/CV_INBOX"),
]
HASH_FILE = Path("/opt/ACTIVE/FARMWORKERS/.processed_hashes")
OUTPUT_DIR = Path("/opt/ACTIVE/FARMWORKERS/candidates_output")
HTML_DIR      = OUTPUT_DIR / "candidates_html"
LOG_FILE      = OUTPUT_DIR / "extraction_log.txt"
JSON_FILE     = OUTPUT_DIR / "candidates_master.json"
CSV_FILE      = OUTPUT_DIR / "candidates_index.csv"

FIELDNAMES = ["idx","filename","name","email","phone","location","skills",
              "languages","experience_years","desired_roles","availability",
              "salary_expectation","status","extraction_method","error"]

OUTPUT_DIR.mkdir(exist_ok=True)
HTML_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()],
)
log = logging.getLogger(__name__)





def _file_hash(p):
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_hashes():
    if HASH_FILE.exists():
        return set(HASH_FILE.read_text().split())
    return set()


def _add_hash(h):
    with open(HASH_FILE, "a") as f:
        f.write(h + "\n")

def process_pdf(idx: int, pdf_path: Path) -> tuple:
    """Returns (candidate_dict_or_None, csv_row_dict)."""
    log.info("[%d] %s", idx, pdf_path.name)
    try:
        text, method = extract_text(pdf_path)
        if not text:
            log.error("  ✗ no text extracted")
            return None, {"filename": pdf_path.name, "name": "ERROR",
                          "status": "FAILED", "error": "no text"}
        c = parse_candidate(text, pdf_path.name)
        c["extraction_method"] = method

        html = candidate_page(c)
        (HTML_DIR / f"{idx:03d}_{safe_name(c['name'])}.html").write_text(html, encoding="utf-8")

        row = {
            "idx": idx, "filename": pdf_path.name, "name": c["name"],
            "email": c["email"] or "", "phone": c["phone"] or "",
            "location": c["location"] or "",
            "skills": "; ".join(c["skills"]),
            "languages": "; ".join(c["languages"]),
            "experience_years": c["experience_years"],
            "desired_roles": "; ".join(c["desired_roles"]),
            "availability": c["availability"],
            "salary_expectation": c["salary_expectation"] or "",
            "status": "SUCCESS", "extraction_method": method, "error": "",
        }
        log.info("  ✓ %s | %s | %d chars", c["name"], method, len(text))
        return c, row
    except Exception as e:
        log.error("  ✗ %s", e)
        return None, {"filename": pdf_path.name, "name": "ERROR",
                      "status": "EXCEPTION", "error": str(e)}


def save_json(candidates: list):
    tmp = JSON_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(candidates, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(JSON_FILE)


def save_csv(rows: list):
    tmp = CSV_FILE.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(CSV_FILE)


def main():
    # Merge all sources, dedup by file content hash
    all_pdfs = []
    for src_dir in CV_SOURCES:
        if src_dir.exists():
            all_pdfs.extend(sorted(src_dir.glob("**/*.pdf")))
    log.info("Found %d PDFs across %d sources", len(all_pdfs), len(CV_SOURCES))
    if not all_pdfs:
        log.error("No PDFs found.")
        return

    seen = _load_hashes()
    candidates, rows = [], []
    start_idx = 1
    for p in all_pdfs:
        fh = _file_hash(p)
        if fh in seen:
            continue
        idx = start_idx + len(candidates)
        log.info("[new] %s", p.name)
        c, row = process_pdf(idx, p)
        if c:
            candidates.append(c)
            _add_hash(fh)
            seen.add(fh)
        rows.append(row)

    save_json(candidates)
    save_csv(rows)
    (HTML_DIR / "index.html").write_text(index_page(candidates), encoding="utf-8")

    ok = sum(1 for r in rows if r.get("status") == "SUCCESS")
    log.info("DONE: %d/%d OK | JSON %s | CSV %s | HTML %s",
             ok, len(all_pdfs), JSON_FILE, CSV_FILE, HTML_DIR)


if __name__ == "__main__":
    main()
