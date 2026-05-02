#!/usr/bin/env python3
"""
PDF to Text converter - 100% offline, zero tokens

Methods:
  1. pdftotext (poppler) - fast, good for text PDFs
  2. pypdf - pure Python, handles most PDFs
  3. pdfplumber - best for tables/layouts
  4. tesseract OCR - for scanned PDFs

Usage:
  python3 pdf_to_text.py input.pdf                    # Auto-select best method
  python3 pdf_to_text.py input.pdf -o output.txt     # Save to file
  python3 pdf_to_text.py input.pdf --method pypdf    # Force specific method
  python3 pdf_to_text.py input.pdf --ocr             # Use OCR (scanned PDFs)
  python3 pdf_to_text.py input.pdf --all             # Try all methods, show best
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path

def pdftotext_extract(pdf_path: str) -> str:
    """Extract using poppler's pdftotext (fastest)"""
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', pdf_path, '-'],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0:
            return result.stdout
        return f"ERROR: {result.stderr}"
    except FileNotFoundError:
        return "ERROR: pdftotext not installed (apt install poppler-utils)"
    except Exception as e:
        return f"ERROR: {e}"

def pypdf_extract(pdf_path: str) -> str:
    """Extract using pypdf (pure Python)"""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        text_parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                text_parts.append(f"--- Page {i+1} ---\n{text}")
        return "\n\n".join(text_parts)
    except ImportError:
        return "ERROR: pypdf not installed (pip install pypdf)"
    except Exception as e:
        return f"ERROR: {e}"

def pdfplumber_extract(pdf_path: str) -> str:
    """Extract using pdfplumber (best for tables)"""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    text_parts.append(f"--- Page {i+1} ---\n{text}")
                # Also extract tables
                tables = page.extract_tables()
                for j, table in enumerate(tables):
                    if table:
                        text_parts.append(f"--- Table {j+1} ---")
                        for row in table:
                            text_parts.append(" | ".join(str(c) if c else "" for c in row))
        return "\n\n".join(text_parts)
    except ImportError:
        return "ERROR: pdfplumber not installed (pip install pdfplumber)"
    except Exception as e:
        return f"ERROR: {e}"

def tesseract_ocr(pdf_path: str) -> str:
    """OCR using tesseract (for scanned PDFs)"""
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Convert PDF to images
            result = subprocess.run(
                ['pdftoppm', '-png', pdf_path, f'{tmpdir}/page'],
                capture_output=True, timeout=120
            )
            if result.returncode != 0:
                return f"ERROR: pdftoppm failed: {result.stderr.decode()}"

            # OCR each page
            text_parts = []
            for img_file in sorted(Path(tmpdir).glob('page-*.png')):
                page_num = img_file.stem.split('-')[1]
                result = subprocess.run(
                    ['tesseract', str(img_file), 'stdout'],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    text_parts.append(f"--- Page {page_num} ---\n{result.stdout}")

            return "\n\n".join(text_parts) if text_parts else "ERROR: No text extracted"
    except FileNotFoundError as e:
        return f"ERROR: Missing tool: {e}"
    except Exception as e:
        return f"ERROR: {e}"

def auto_extract(pdf_path: str) -> tuple[str, str]:
    """Try methods in order, return first successful"""
    methods = [
        ('pdftotext', pdftotext_extract),
        ('pypdf', pypdf_extract),
        ('pdfplumber', pdfplumber_extract),
    ]

    for name, func in methods:
        result = func(pdf_path)
        if not result.startswith("ERROR:") and len(result.strip()) > 50:
            return result, name

    # Fallback to OCR
    result = tesseract_ocr(pdf_path)
    return result, 'tesseract'

def compare_all(pdf_path: str) -> dict:
    """Run all methods and compare"""
    results = {}
    methods = [
        ('pdftotext', pdftotext_extract),
        ('pypdf', pypdf_extract),
        ('pdfplumber', pdfplumber_extract),
        ('tesseract', tesseract_ocr),
    ]

    for name, func in methods:
        text = func(pdf_path)
        results[name] = {
            'chars': len(text),
            'lines': len(text.splitlines()),
            'error': text.startswith("ERROR:"),
            'preview': text[:200] if not text.startswith("ERROR:") else text,
        }

    return results

def main():
    parser = argparse.ArgumentParser(description='PDF to Text (offline)')
    parser.add_argument('pdf', help='Input PDF file')
    parser.add_argument('-o', '--output', help='Output text file')
    parser.add_argument('--method', choices=['pdftotext', 'pypdf', 'pdfplumber', 'auto'],
                        default='auto', help='Extraction method')
    parser.add_argument('--ocr', action='store_true', help='Use OCR (scanned PDFs)')
    parser.add_argument('--all', action='store_true', help='Compare all methods')
    args = parser.parse_args()

    if not os.path.exists(args.pdf):
        print(f"ERROR: File not found: {args.pdf}")
        sys.exit(1)

    if args.all:
        results = compare_all(args.pdf)
        print("=== METHOD COMPARISON ===\n")
        for method, data in results.items():
            status = "ERROR" if data['error'] else "OK"
            print(f"{method}: {status} | {data['chars']} chars | {data['lines']} lines")
            print(f"  Preview: {data['preview'][:100]}...\n")
        sys.exit(0)

    if args.ocr:
        text = tesseract_ocr(args.pdf)
        method = 'tesseract'
    elif args.method == 'auto':
        text, method = auto_extract(args.pdf)
    elif args.method == 'pdftotext':
        text = pdftotext_extract(args.pdf)
        method = 'pdftotext'
    elif args.method == 'pypdf':
        text = pypdf_extract(args.pdf)
        method = 'pypdf'
    elif args.method == 'pdfplumber':
        text = pdfplumber_extract(args.pdf)
        method = 'pdfplumber'

    if args.output:
        with open(args.output, 'w') as f:
            f.write(text)
        print(f"Saved to {args.output} ({len(text)} chars) using {method}")
    else:
        print(text)
        print(f"\n--- Extracted using: {method} ---", file=sys.stderr)

if __name__ == '__main__':
    main()
