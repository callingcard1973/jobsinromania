#!/usr/bin/env python3
"""
PDF Extractor - Extract text, tables, and metadata from PDFs
Usage: python3 pdf_extractor.py <input.pdf> [--output file.txt] [--format txt|json|csv]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import os
import re
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Try different PDF libraries
PDF_LIBRARY = None

try:
    import pdfplumber
    PDF_LIBRARY = 'pdfplumber'
except ImportError:
    try:
        import PyPDF2
        PDF_LIBRARY = 'pypdf2'
    except ImportError:
        try:
            import fitz  # PyMuPDF
            PDF_LIBRARY = 'pymupdf'
        except ImportError:
            pass

# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_with_pdfplumber(filepath: str) -> Dict:
    """Extract using pdfplumber (best for tables)"""
    import pdfplumber

    result = {
        'file': filepath,
        'pages': 0,
        'text': '',
        'tables': [],
        'metadata': {},
        'extracted_at': datetime.now().isoformat(),
    }

    with pdfplumber.open(filepath) as pdf:
        result['pages'] = len(pdf.pages)
        result['metadata'] = pdf.metadata or {}

        all_text = []
        for i, page in enumerate(pdf.pages):
            # Extract text
            text = page.extract_text() or ''
            all_text.append(f"--- Page {i+1} ---\n{text}")

            # Extract tables
            tables = page.extract_tables()
            for table in tables:
                if table:
                    result['tables'].append({
                        'page': i + 1,
                        'rows': len(table),
                        'data': table,
                    })

        result['text'] = '\n\n'.join(all_text)

    return result

def extract_with_pypdf2(filepath: str) -> Dict:
    """Extract using PyPDF2 (basic text extraction)"""
    import PyPDF2

    result = {
        'file': filepath,
        'pages': 0,
        'text': '',
        'tables': [],
        'metadata': {},
        'extracted_at': datetime.now().isoformat(),
    }

    with open(filepath, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        result['pages'] = len(reader.pages)

        if reader.metadata:
            result['metadata'] = {
                'title': reader.metadata.get('/Title', ''),
                'author': reader.metadata.get('/Author', ''),
                'creator': reader.metadata.get('/Creator', ''),
            }

        all_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ''
            all_text.append(f"--- Page {i+1} ---\n{text}")

        result['text'] = '\n\n'.join(all_text)

    return result

def extract_with_pymupdf(filepath: str) -> Dict:
    """Extract using PyMuPDF (fast, good quality)"""
    import fitz

    result = {
        'file': filepath,
        'pages': 0,
        'text': '',
        'tables': [],
        'metadata': {},
        'extracted_at': datetime.now().isoformat(),
    }

    doc = fitz.open(filepath)
    result['pages'] = len(doc)
    result['metadata'] = doc.metadata or {}

    all_text = []
    for i, page in enumerate(doc):
        text = page.get_text() or ''
        all_text.append(f"--- Page {i+1} ---\n{text}")

    result['text'] = '\n\n'.join(all_text)
    doc.close()

    return result

def extract_pdf(filepath: str) -> Dict:
    """Extract PDF using available library"""
    if PDF_LIBRARY == 'pdfplumber':
        return extract_with_pdfplumber(filepath)
    elif PDF_LIBRARY == 'pypdf2':
        return extract_with_pypdf2(filepath)
    elif PDF_LIBRARY == 'pymupdf':
        return extract_with_pymupdf(filepath)
    else:
        return {
            'error': 'No PDF library available. Install: pip install pdfplumber',
            'file': filepath,
        }

# ============================================================
# TEXT PROCESSING
# ============================================================

def extract_emails(text: str) -> List[str]:
    """Extract email addresses from text"""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text)))

def extract_phones(text: str) -> List[str]:
    """Extract phone numbers from text"""
    patterns = [
        r'\+\d{1,3}[-.\s]?\d{2,4}[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        r'\(\d{2,4}\)[-.\s]?\d{3,4}[-.\s]?\d{3,4}',
        r'\d{3,4}[-.\s]\d{3,4}[-.\s]\d{3,4}',
    ]
    phones = []
    for pattern in patterns:
        phones.extend(re.findall(pattern, text))
    return list(set(phones))

def extract_urls(text: str) -> List[str]:
    """Extract URLs from text"""
    pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return list(set(re.findall(pattern, text)))

def extract_dates(text: str) -> List[str]:
    """Extract dates from text"""
    patterns = [
        r'\d{4}-\d{2}-\d{2}',
        r'\d{2}/\d{2}/\d{4}',
        r'\d{2}\.\d{2}\.\d{4}',
    ]
    dates = []
    for pattern in patterns:
        dates.extend(re.findall(pattern, text))
    return list(set(dates))

def analyze_content(result: Dict) -> Dict:
    """Analyze extracted content"""
    text = result.get('text', '')

    analysis = {
        'word_count': len(text.split()),
        'char_count': len(text),
        'emails': extract_emails(text),
        'phones': extract_phones(text),
        'urls': extract_urls(text),
        'dates': extract_dates(text),
    }

    return analysis

# ============================================================
# OUTPUT FORMATTING
# ============================================================

def format_as_text(result: Dict, analysis: Dict = None) -> str:
    """Format extraction as plain text"""
    lines = [
        "=" * 60,
        f"PDF EXTRACTION: {Path(result['file']).name}",
        "=" * 60,
        "",
        f"Pages: {result.get('pages', 0)}",
        f"Extracted: {result.get('extracted_at', '')}",
    ]

    if result.get('metadata'):
        lines.extend([
            "",
            "METADATA:",
            "-" * 40,
        ])
        for key, value in result['metadata'].items():
            if value:
                lines.append(f"  {key}: {value}")

    if analysis:
        lines.extend([
            "",
            "ANALYSIS:",
            "-" * 40,
            f"  Words: {analysis['word_count']}",
            f"  Characters: {analysis['char_count']}",
            f"  Emails found: {len(analysis['emails'])}",
            f"  Phones found: {len(analysis['phones'])}",
            f"  URLs found: {len(analysis['urls'])}",
        ])

        if analysis['emails']:
            lines.append(f"\n  Emails: {', '.join(analysis['emails'][:5])}")
        if analysis['phones']:
            lines.append(f"  Phones: {', '.join(analysis['phones'][:5])}")

    lines.extend([
        "",
        "=" * 60,
        "CONTENT:",
        "=" * 60,
        "",
        result.get('text', ''),
    ])

    if result.get('tables'):
        lines.extend([
            "",
            "=" * 60,
            f"TABLES ({len(result['tables'])} found):",
            "=" * 60,
        ])
        for i, table in enumerate(result['tables'][:5]):
            lines.append(f"\nTable {i+1} (Page {table['page']}, {table['rows']} rows):")
            for row in table['data'][:5]:
                lines.append(f"  {row}")

    return '\n'.join(lines)

def format_as_csv(result: Dict) -> str:
    """Format tables as CSV"""
    lines = []

    for table in result.get('tables', []):
        lines.append(f"# Table from page {table['page']}")
        for row in table['data']:
            if row:
                cleaned = [str(cell).replace(',', ';') if cell else '' for cell in row]
                lines.append(','.join(cleaned))
        lines.append("")

    return '\n'.join(lines)

# ============================================================
# BATCH PROCESSING
# ============================================================

def process_multiple(filepaths: List[str], output_dir: str = None) -> List[Dict]:
    """Process multiple PDFs"""
    results = []

    for filepath in filepaths:
        print(f"  Processing: {Path(filepath).name}...")
        result = extract_pdf(filepath)
        results.append(result)

        if output_dir:
            output_file = os.path.join(output_dir, Path(filepath).stem + '.txt')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(format_as_text(result))

    return results

# ============================================================
# MAIN
# ============================================================

def main():
    args = sys.argv[1:]

    if not args or '-h' in args or '--help' in args:
        print(f"""
{'='*60}
PDF EXTRACTOR
{'='*60}

Usage: pdf_extractor.py <input.pdf> [options]
       pdf_extractor.py *.pdf --output-dir /tmp/extracted

Options:
  --output FILE     Save to specific file
  --output-dir DIR  Directory for batch output
  --format FORMAT   Output format: txt, json, csv (default: txt)
  --analyze         Include content analysis (emails, phones, etc.)
  --tables-only     Extract only tables

Available library: {PDF_LIBRARY or 'NONE - install pdfplumber'}

Features:
  - Text extraction
  - Table extraction (with pdfplumber)
  - Metadata extraction
  - Email/phone/URL detection
  - Batch processing

Examples:
  pdf_extractor.py document.pdf
  pdf_extractor.py report.pdf --format json --output report.json
  pdf_extractor.py invoice.pdf --analyze
  pdf_extractor.py *.pdf --output-dir /tmp/extracted
""")
        return

    if not PDF_LIBRARY:
        print("Error: No PDF library available")
        print("Install one of: pip install pdfplumber pypdf2 pymupdf")
        return

    # Parse arguments
    input_files = []
    output_file = None
    output_dir = None
    output_format = 'txt'
    do_analyze = '--analyze' in args
    tables_only = '--tables-only' in args

    for i, arg in enumerate(args):
        if arg == '--output' and i + 1 < len(args):
            output_file = args[i + 1]
        elif arg == '--output-dir' and i + 1 < len(args):
            output_dir = args[i + 1]
        elif arg == '--format' and i + 1 < len(args):
            output_format = args[i + 1]
        elif arg.endswith('.pdf') and os.path.exists(arg):
            input_files.append(arg)

    if not input_files:
        print("Error: No valid PDF files found")
        return

    print(f"\n{'='*60}")
    print(f"PDF EXTRACTOR - using {PDF_LIBRARY}")
    print(f"{'='*60}\n")
    print(f"Files: {len(input_files)}")

    if len(input_files) == 1:
        # Single file
        result = extract_pdf(input_files[0])

        if result.get('error'):
            print(f"Error: {result['error']}")
            return

        analysis = analyze_content(result) if do_analyze else None

        print(f"Pages: {result['pages']}")
        print(f"Words: {len(result['text'].split())}")

        if result.get('tables'):
            print(f"Tables: {len(result['tables'])}")

        # Format output
        if output_format == 'json':
            if analysis:
                result['analysis'] = analysis
            output = json.dumps(result, indent=2, ensure_ascii=False)
        elif output_format == 'csv' and result.get('tables'):
            output = format_as_csv(result)
        else:
            output = format_as_text(result, analysis)

        # Save or print
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"\nSaved to: {output_file}")
        else:
            print(f"\n{output[:3000]}")
            if len(output) > 3000:
                print(f"\n... ({len(output)} chars total)")

    else:
        # Batch processing
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        results = process_multiple(input_files, output_dir)

        print(f"\nProcessed: {len(results)} files")
        total_pages = sum(r.get('pages', 0) for r in results)
        print(f"Total pages: {total_pages}")

        if output_dir:
            print(f"Output directory: {output_dir}")

    print(f"\n{'='*60}\n")

if __name__ == '__main__':
    main()
