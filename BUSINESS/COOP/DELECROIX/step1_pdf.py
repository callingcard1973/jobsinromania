#!/usr/bin/env python3
import sys
sys.stdout.reconfigure(encoding='utf-8')

filepath = r'D:\MEMORY\DELECROIX\Gmail - Devis Delecroix & Partenariat commercial.pdf'

# Try PyMuPDF first
try:
    import fitz
    doc = fitz.open(filepath)
    print(f"Pages: {len(doc)}")
    for i, page in enumerate(doc):
        text = page.get_text()
        print(f"\n--- Page {i+1} ---")
        print(text)
    doc.close()
except Exception as e:
    print(f"PyMuPDF error: {e}")

# Try pdfplumber
try:
    import pdfplumber
    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            print(f"\n--- pdfplumber Page {i+1} ---")
            print(text)
except Exception as e:
    print(f"pdfplumber error: {e}")
