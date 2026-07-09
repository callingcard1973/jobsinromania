#!/usr/bin/env python3
"""Scrape MADR agricultural-land sale offers (Legea 17/2014, extravilan).

oferte.html = latest; arhiva.html = full history; detail pages carry an Anexa PDF
with the real fields (vanzator, suprafata, categorie, pret, comuna/judet).
Output: land_offers.csv keyed by offer id. Polite: UA + delay, tolerant per-offer.
"""
import csv
import os
import re
import subprocess
import sys
import time
import requests
from bs4 import BeautifulSoup

BASE = "https://www.madr.ro"
LIST = BASE + "/terenuri-agricole/arhiva.html"
UA = {"User-Agent": "Mozilla/5.0 (compatible; AgroEvolution-research/1.0)"}
DELAY = 1.5

# Patterns tuned to REAL OCR text (verified on samples). OCR quirks handled:
# diacritics garble (ţ/ț/t, ă/a), TLD dot becomes a space ("agriterenuri ro"),
# "Subsemnatul/Subsemnata" or "Subscrisa," precede the seller, CNP|CUI follows.
FIELDS = {
    "suprafata": r"suprafa[tțţ][ăaã]?\s*de\s*([\d][\d.,]*)\s*\(?\s*ha",
    "pret": r"pre[tțţj]ul?\s*de\s*([\d][\d.,]*)\s*(?:lei|ron)",
    "vanzator": r"(?:Subsemnat\w*|Subscris\w*)[,\s*\d\)]*([A-ZĂÂÎŞŢ][\w\.\s\-]{3,45}?)\s+(?:CNP|CUI)",
    "cui": r"CUI\s*(RO?\s?\d[\d\s]{5,12})",
    # email: allow OCR-split TLD (dot turned to space) -> normalized in clean step
    "email": r"([\w.\-]+@[\w.\-]+(?:\.\w{2,}|\s+(?:ro|com|net|eu|it)))",
    "telefon": r"(?:tel\w*|telefon)\s*[:.]?\s*(\+?\d[\d\s.\-]{7,13}\d)",
}


def _clean(key, val):
    val = val.strip().strip(".,;")
    if key == "email":
        val = re.sub(r"\s+(ro|com|net|eu|it)$", r".\1", val).replace(" ", "")
    if key in ("pret", "telefon", "cui"):
        val = re.sub(r"\s+", "", val)
    return val


def get(url):
    r = requests.get(url, headers=UA, timeout=30, verify=True)
    r.raise_for_status()
    return r


def list_offers(max_pages):
    """Yield (id, judet, slug, url) from the archive listing pages."""
    seen = set()
    for p in range(max_pages):
        url = LIST + (f"?start={p*20}" if p else "")
        try:
            soup = BeautifulSoup(get(url).text, "html.parser")
        except Exception as e:
            print(f"[list] {url} -> {e}", file=sys.stderr)
            break
        found = 0
        for a in soup.select("a[href*='/terenuri-agricole/']"):
            href = a.get("href", "")
            m = re.search(r"/terenuri-agricole/([a-z-]+)/(\d+)-([^/]+?)\.html", href)
            if not m:
                continue
            oid = m.group(2)
            if oid in seen:
                continue
            seen.add(oid)
            full = href if href.startswith("http") else BASE + href
            yield oid, m.group(1), m.group(3), full
            found += 1
        if not found:
            break
        time.sleep(DELAY)


def pdf_link(detail_url):
    soup = BeautifulSoup(get(detail_url).text, "html.parser")
    date = ""
    dm = re.search(r"(\d{1,2}\s+\w+\s+20\d\d)", soup.get_text())
    if dm:
        date = dm.group(1)
    for a in soup.select("a[href$='.pdf'], a[href*='.pdf']"):
        href = a.get("href", "")
        return (href if href.startswith("http") else BASE + href), date
    return None, date


# OCR is CPU-bound. The raspibig Pi CANNOT OCR these forms (>300s/page even at 150dpi)
# -> OCR must run on a real CPU (laptop). Two zero-token backends:
#   OCR_BACKEND=tesseract : pdftoppm + tesseract (needs system binaries)
#   OCR_BACKEND=easyocr   : PyMuPDF render + EasyOCR (pure-Python, no admin, bundles ro)
OCR_BACKEND = os.getenv("OCR_BACKEND", "easyocr")
OCR_DPI = int(os.getenv("OCR_DPI", "200"))
OCR_LANG = os.getenv("OCR_LANG", "ron")
OCR_PAGE_TIMEOUT = int(os.getenv("OCR_PAGE_TIMEOUT", "90"))
_READER = None


def _easyocr_text(pdf_path):
    """Render with PyMuPDF, OCR with EasyOCR (ro+en). Lazy, cached reader."""
    global _READER
    import fitz  # PyMuPDF
    import easyocr
    if _READER is None:
        _READER = easyocr.Reader(["ro", "en"], gpu=False, verbose=False)
    doc = fitz.open(pdf_path)
    chunks = []
    for page in doc:
        pix = page.get_pixmap(dpi=OCR_DPI)
        png = pdf_path + f"_p{page.number}.png"
        pix.save(png)
        try:
            chunks.append("\n".join(_READER.readtext(png, detail=0, paragraph=True)))
        finally:
            os.path.exists(png) and os.remove(png)
    doc.close()
    return "\n".join(chunks)


def pdf_text(pdf_path):
    """Text layer if present; else zero-token OCR (backend per OCR_BACKEND)."""
    txt = subprocess.run(["pdftotext", "-layout", pdf_path, "-"],
                         capture_output=True, text=True, timeout=60).stdout
    if len(txt.strip()) >= 200:
        return txt, "digital"
    if OCR_BACKEND == "easyocr":
        try:
            t = _easyocr_text(pdf_path)
            return t, ("ocr" if t.strip() else "ocr_timeout")
        except Exception:
            return "", "ocr_timeout"
    base = pdf_path + "_p"
    try:
        subprocess.run(["pdftoppm", "-r", str(OCR_DPI), "-png", pdf_path, base],
                       capture_output=True, timeout=180)
    except subprocess.TimeoutExpired:
        return "", "ocr_timeout"
    d = os.path.dirname(pdf_path) or "."
    pages = sorted(p for p in os.listdir(d)
                   if os.path.basename(base) in p and p.endswith(".png"))
    ocr = []
    for pg in pages:
        full = os.path.join(d, pg)
        try:
            ocr.append(subprocess.run(["tesseract", full, "-", "-l", OCR_LANG, "--psm", "6"],
                                      capture_output=True, text=True,
                                      timeout=OCR_PAGE_TIMEOUT).stdout)
        except subprocess.TimeoutExpired:
            pass  # skip the slow page; partial OCR still yields email/phone leads
        finally:
            os.remove(full)
    return "\n".join(ocr), ("ocr" if ocr else "ocr_timeout")


def parse_pdf(url, tmp):
    r = get(url)
    with open(tmp, "wb") as f:
        f.write(r.content)
    txt, mode = pdf_text(tmp)
    out = {"_extract_mode": mode}
    for key, pat in FIELDS.items():
        m = re.search(pat, txt, re.IGNORECASE)
        out[key] = _clean(key, m.group(1)) if m else ""
    filled = sum(1 for k in FIELDS if out[k])
    out["needs_review"] = "1" if filled < 3 else ""
    return out


def _done_ids(out_csv):
    """Offer ids already in the CSV — enables resume after a crash on long runs."""
    if not os.path.exists(out_csv):
        return set()
    with open(out_csv, newline="", encoding="utf-8") as f:
        return {r["id"] for r in csv.DictReader(f)}


def main():
    max_pages = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    out_csv = sys.argv[2] if len(sys.argv) > 2 else "land_offers.csv"
    tmp = os.path.join(os.path.dirname(out_csv) or ".", "_anexa.pdf")
    cols = (["id", "judet_url", "slug", "detail_url", "pdf_url", "data_publicare"]
            + list(FIELDS) + ["_extract_mode", "needs_review"])
    done = _done_ids(out_csv)
    new_file = not os.path.exists(out_csv)
    ok = fail = skip = 0
    # stream-write: append each offer immediately so a multi-hour run is crash-safe
    f = open(out_csv, "a", newline="", encoding="utf-8")
    w = csv.DictWriter(f, fieldnames=cols)
    if new_file:
        w.writeheader()
    for oid, judet, slug, url in list_offers(max_pages):
        if oid in done:
            skip += 1
            continue
        try:
            pdf, date = pdf_link(url)
            rec = {"id": oid, "judet_url": judet, "slug": slug, "detail_url": url,
                   "pdf_url": pdf or "", "data_publicare": date}
            if pdf:
                rec.update(parse_pdf(pdf, tmp))
                ok += 1
            else:
                fail += 1
            w.writerow({k: rec.get(k, "") for k in cols})
            f.flush()
            print(f"{oid} {judet}: {rec.get('suprafata','?')}ha "
                  f"email={rec.get('email','')} tel={rec.get('telefon','')}")
            time.sleep(DELAY)
        except Exception as e:
            fail += 1
            print(f"[offer {oid}] {e}", file=sys.stderr)
    f.close()
    rows = ok + fail  # processed this run
    print(f"(resumed: skipped {skip} already-done)")
    if os.path.exists(tmp):
        os.remove(tmp)
    print(f"\nDONE: {rows} processed ({ok} parsed, {fail} no-pdf), skipped {skip} -> {out_csv}")


if __name__ == "__main__":
    main()
