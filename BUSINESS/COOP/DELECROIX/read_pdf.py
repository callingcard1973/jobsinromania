#!/usr/bin/env python3
"""Read the Delecroix PDF quote"""
import sys
try:
    import pdfplumber
    pdf = pdfplumber.open(r'D:\MEMORY\DELECROIX\Gmail - Devis Delecroix & Partenariat commercial.pdf')
    print(f'Pages: {len(pdf.pages)}')
    for i, page in enumerate(pdf.pages):
        text = page.extract_text()
        if text:
            print(f'--- Page {i+1} ---')
            print(text)
        else:
            print(f'--- Page {i+1}: (no text extracted) ---')
    pdf.close()
except Exception as e:
    print(f'pdfplumber error: {e}', file=sys.stderr)

try:
    import fitz  # PyMuPDF
    doc = fitz.open(r'D:\MEMORY\DELECROIX\Gmail - Devis Delecroix & Partenariat commercial.pdf')
    print(f'\nPyMuPDF Pages: {len(doc)}')
    for i in range(len(doc)):
        text = doc[i].get_text()
        if text.strip():
            print(f'--- Page {i+1} (PyMuPDF) ---')
            print(text)
        else:
            print(f'--- Page {i+1} (PyMuPDF): (no text) ---')
    doc.close()
except Exception as e:
    print(f'PyMuPDF error: {e}', file=sys.stderr)
