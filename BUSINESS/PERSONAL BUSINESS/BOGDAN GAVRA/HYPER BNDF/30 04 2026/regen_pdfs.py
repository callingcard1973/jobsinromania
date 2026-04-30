#!/usr/bin/env python3
"""Regenerate PDFs din HTML pentru FISA (A4) si PLANSA (A3 landscape)."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = Path(r"D:\MEMORY\BUSINESS\PERSONAL BUSINESS\BOGDAN GAVRA\HYPER BNDF\30 04 2026")

JOBS = []
for pkg in ("HYPER 1001", "HYPER 1002", "HYPER 1003"):
    fisa_html = BASE / "CATALOG" / "FISE COMERCIALE" / pkg / f"FISA_COMERCIALA_{pkg.replace(' ', '_')}.html"
    fisa_pdf = fisa_html.with_suffix(".pdf")
    JOBS.append((fisa_html, fisa_pdf, "A4", False))

    planse_dir = BASE / "CATALOG" / "PLANSE TEHNICE" / pkg
    p_tehnica_html = planse_dir / f"PLANSA_TEHNICA_{pkg.replace(' ', '_')}.html"
    p_tehnica_pdf = p_tehnica_html.with_suffix(".pdf")
    JOBS.append((p_tehnica_html, p_tehnica_pdf, "A3", True))

    p_alt_html = planse_dir / f"PLANSA_{pkg.replace(' ', '_')}.html"
    p_alt_pdf = p_alt_html.with_suffix(".pdf")
    JOBS.append((p_alt_html, p_alt_pdf, "A3", True))


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context()
        page = context.new_page()
        for src, dst, fmt, landscape in JOBS:
            url = src.as_uri()
            page.goto(url, wait_until="networkidle")
            page.pdf(path=str(dst), format=fmt, landscape=landscape, print_background=True,
                     margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
            size_kb = dst.stat().st_size // 1024
            print(f"OK [{fmt}{' L' if landscape else ''}] {size_kb} KB  {dst.name}")
        browser.close()


if __name__ == "__main__":
    main()
