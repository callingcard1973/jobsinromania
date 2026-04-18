#!/usr/bin/env python3
"""Extract text from CV PDFs, strip contacts, save clean text."""
import pdfplumber
import re
import json
import os

PDF_LIST = "/tmp/cv_pdfs.txt"
OUTPUT = "/opt/ACTIVE/WORKFORCE/cv_extracted.json"

CONTACT_RE = [
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
    re.compile(r"\+?\d[\d\s\-().]{8,15}\d"),
    re.compile(r"https?://\S+"),
    re.compile(r"linkedin\.com\S*", re.I),
    re.compile(r"facebook\.com\S*", re.I),
    re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),
]

with open(PDF_LIST) as f:
    pdfs = [l.strip() for l in f if l.strip()]

print(f"Processing {len(pdfs)} PDFs...")
results = []

for path in pdfs:
    fname = os.path.basename(path)
    try:
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:5]:
                t = page.extract_text()
                if t:
                    text += t + "\n"
        if not text.strip():
            continue

        clean = text
        for pat in CONTACT_RE:
            clean = pat.sub("[REDACTED]", clean)

        lines = [l.strip() for l in clean.split("\n") if l.strip()]
        name = lines[0][:50] if lines else "Unknown"

        results.append({
            "file": fname,
            "name": name,
            "text": clean[:2000],
            "length": len(clean)
        })
        print(f"  OK: {fname} ({len(clean)} chars)")
    except Exception as e:
        print(f"  SKIP: {fname} — {e}")

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print(f"\nExtracted {len(results)} CVs -> {OUTPUT}")
