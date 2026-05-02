#!/usr/bin/env python3
"""
PDF Tools - Comprehensive PDF manipulation for large files
Usage:
    python3 pdf_tools.py info file.pdf
    python3 pdf_tools.py extract file.pdf [--pages 1-10] [--output text.txt]
    python3 pdf_tools.py split file.pdf --pages 1-10 [--output split.pdf]
    python3 pdf_tools.py merge file1.pdf file2.pdf [--output merged.pdf]
    python3 pdf_tools.py compress file.pdf [--output compressed.pdf]
    python3 pdf_tools.py search file.pdf "search term"
    python3 pdf_tools.py to-images file.pdf [--output-dir images/]
    python3 pdf_tools.py ocr file.pdf [--output text.txt]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii

import os
import argparse
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime

# Check available libraries
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pikepdf
    HAS_PIKEPDF = True
except ImportError:
    HAS_PIKEPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


def get_pdf_info(pdf_path: str) -> dict:
    """Get comprehensive PDF information"""
    info = {'path': pdf_path, 'size_mb': os.path.getsize(pdf_path) / (1024*1024)}

    # Use pdfinfo CLI (fast)
    try:
        result = subprocess.run(['pdfinfo', pdf_path], capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    info[key.strip().lower().replace(' ', '_')] = val.strip()
    except Exception as e:
        info['pdfinfo_error'] = str(e)

    # Use PyMuPDF for more details
    if HAS_PYMUPDF:
        try:
            doc = fitz.open(pdf_path)
            info['pages'] = len(doc)
            info['encrypted'] = doc.is_encrypted
            info['metadata'] = doc.metadata
            info['has_toc'] = len(doc.get_toc()) > 0

            # Check for images/text
            has_text = False
            has_images = False
            for i, page in enumerate(doc):
                if i > 5:  # Sample first 5 pages
                    break
                if page.get_text().strip():
                    has_text = True
                if page.get_images():
                    has_images = True
            info['has_text'] = has_text
            info['has_images'] = has_images
            info['likely_scanned'] = has_images and not has_text
            doc.close()
        except Exception as e:
            info['pymupdf_error'] = str(e)

    return info


def extract_text(pdf_path: str, pages: str = None, output: str = None) -> str:
    """Extract text from PDF"""
    text_parts = []
    page_range = parse_page_range(pages) if pages else None

    if HAS_PYMUPDF:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            if page_range and (i + 1) not in page_range:
                continue
            text = page.get_text()
            if text.strip():
                text_parts.append(f"--- Page {i+1} ---\n{text}")
        doc.close()
    elif HAS_PDFPLUMBER:
        import pdfplumber
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                if page_range and (i + 1) not in page_range:
                    continue
                text = page.extract_text()
                if text:
                    text_parts.append(f"--- Page {i+1} ---\n{text}")
    else:
        # Fallback to pdftotext
        cmd = ['pdftotext', '-layout', pdf_path, '-']
        if pages:
            start, end = pages.split('-') if '-' in pages else (pages, pages)
            cmd = ['pdftotext', '-f', start, '-l', end, '-layout', pdf_path, '-']
        result = subprocess.run(cmd, capture_output=True, text=True)
        text_parts.append(result.stdout)

    full_text = '\n\n'.join(text_parts)
    full_text = to_ascii(full_text)

    if output:
        Path(output).write_text(full_text, encoding='utf-8')
        print(f"Text saved to: {output}")

    return full_text


def split_pdf(pdf_path: str, pages: str, output: str = None) -> str:
    """Split PDF to extract specific pages"""
    if not output:
        base = Path(pdf_path).stem
        output = f"{base}_pages_{pages.replace('-', '_')}.pdf"

    page_range = parse_page_range(pages)

    if HAS_PIKEPDF:
        with pikepdf.open(pdf_path) as pdf:
            new_pdf = pikepdf.Pdf.new()
            for p in page_range:
                if p <= len(pdf.pages):
                    new_pdf.pages.append(pdf.pages[p - 1])
            new_pdf.save(output)
    elif HAS_PYMUPDF:
        doc = fitz.open(pdf_path)
        new_doc = fitz.open()
        for p in page_range:
            if p <= len(doc):
                new_doc.insert_pdf(doc, from_page=p-1, to_page=p-1)
        new_doc.save(output)
        new_doc.close()
        doc.close()
    else:
        # Fallback to pdftk
        page_spec = pages.replace('-', '-')
        subprocess.run(['pdftk', pdf_path, 'cat', page_spec, 'output', output], check=True)

    print(f"Split PDF saved to: {output}")
    return output


def merge_pdfs(pdf_paths: list, output: str = None) -> str:
    """Merge multiple PDFs into one"""
    if not output:
        output = f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    if HAS_PIKEPDF:
        merged = pikepdf.Pdf.new()
        for path in pdf_paths:
            with pikepdf.open(path) as pdf:
                merged.pages.extend(pdf.pages)
        merged.save(output)
    elif HAS_PYMUPDF:
        merged = fitz.open()
        for path in pdf_paths:
            doc = fitz.open(path)
            merged.insert_pdf(doc)
            doc.close()
        merged.save(output)
        merged.close()
    else:
        # Fallback to pdftk
        subprocess.run(['pdftk'] + pdf_paths + ['cat', 'output', output], check=True)

    print(f"Merged PDF saved to: {output}")
    return output


def compress_pdf(pdf_path: str, output: str = None) -> str:
    """Compress PDF to reduce file size"""
    if not output:
        base = Path(pdf_path).stem
        output = f"{base}_compressed.pdf"

    original_size = os.path.getsize(pdf_path)

    # Try qpdf first (best compression)
    try:
        subprocess.run([
            'qpdf', '--linearize', '--compress-streams=y',
            '--object-streams=generate', pdf_path, output
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # Fallback to pikepdf
        if HAS_PIKEPDF:
            with pikepdf.open(pdf_path) as pdf:
                pdf.save(output, linearize=True, compress_streams=True)
        else:
            # Last resort: ghostscript
            subprocess.run([
                'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                '-dPDFSETTINGS=/ebook', '-dNOPAUSE', '-dBATCH', '-dQUIET',
                f'-sOutputFile={output}', pdf_path
            ], check=True)

    new_size = os.path.getsize(output)
    ratio = (1 - new_size / original_size) * 100

    print(f"Compressed: {original_size/1024/1024:.2f}MB -> {new_size/1024/1024:.2f}MB ({ratio:.1f}% reduction)")
    print(f"Saved to: {output}")
    return output


def search_pdf(pdf_path: str, search_term: str) -> list:
    """Search for text in PDF and return page numbers with context"""
    results = []
    search_lower = search_term.lower()

    if HAS_PYMUPDF:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text = page.get_text()
            if search_lower in text.lower():
                # Get context around match
                lines = text.split('\n')
                for j, line in enumerate(lines):
                    if search_lower in line.lower():
                        context = '\n'.join(lines[max(0, j-1):j+2])
                        results.append({
                            'page': i + 1,
                            'line': j + 1,
                            'context': to_ascii(context[:200])
                        })
        doc.close()
    else:
        # Fallback to pdftotext + grep
        result = subprocess.run(['pdftotext', '-layout', pdf_path, '-'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        for i, line in enumerate(lines):
            if search_lower in line.lower():
                results.append({
                    'line': i + 1,
                    'context': to_ascii(line[:200])
                })

    return results


def pdf_to_images(pdf_path: str, output_dir: str = None, dpi: int = 150) -> list:
    """Convert PDF pages to images"""
    if not output_dir:
        output_dir = Path(pdf_path).stem + "_images"

    Path(output_dir).mkdir(parents=True, exist_ok=True)
    images = []

    if HAS_PYMUPDF:
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi)
            img_path = os.path.join(output_dir, f"page_{i+1:04d}.png")
            pix.save(img_path)
            images.append(img_path)
        doc.close()
    else:
        # Fallback to pdftoppm
        base = os.path.join(output_dir, "page")
        subprocess.run(['pdftoppm', '-png', '-r', str(dpi), pdf_path, base], check=True)
        images = sorted(Path(output_dir).glob('*.png'))

    print(f"Saved {len(images)} images to: {output_dir}")
    return images


def ocr_pdf(pdf_path: str, output: str = None) -> str:
    """OCR a scanned PDF (requires tesseract)"""
    # Check if tesseract is installed
    try:
        subprocess.run(['tesseract', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: tesseract not installed. Run: sudo apt-get install tesseract-ocr")
        return ""

    text_parts = []

    with tempfile.TemporaryDirectory() as tmpdir:
        # Convert to images first
        if HAS_PYMUPDF:
            doc = fitz.open(pdf_path)
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=300)
                img_path = os.path.join(tmpdir, f"page_{i}.png")
                pix.save(img_path)

                # OCR the image
                result = subprocess.run(
                    ['tesseract', img_path, 'stdout', '-l', 'eng+ron'],
                    capture_output=True, text=True
                )
                if result.stdout.strip():
                    text_parts.append(f"--- Page {i+1} ---\n{result.stdout}")
            doc.close()
        else:
            # Use pdftoppm + tesseract
            subprocess.run(['pdftoppm', '-png', '-r', '300', pdf_path, os.path.join(tmpdir, 'page')], check=True)
            for img_path in sorted(Path(tmpdir).glob('*.png')):
                result = subprocess.run(
                    ['tesseract', str(img_path), 'stdout', '-l', 'eng+ron'],
                    capture_output=True, text=True
                )
                if result.stdout.strip():
                    page_num = img_path.stem.split('-')[-1]
                    text_parts.append(f"--- Page {page_num} ---\n{result.stdout}")

    full_text = '\n\n'.join(text_parts)
    full_text = to_ascii(full_text)

    if output:
        Path(output).write_text(full_text, encoding='utf-8')
        print(f"OCR text saved to: {output}")

    return full_text


def parse_page_range(pages: str) -> list:
    """Parse page range like '1-10' or '1,3,5-7' into list of page numbers"""
    result = []
    for part in pages.split(','):
        if '-' in part:
            start, end = map(int, part.split('-'))
            result.extend(range(start, end + 1))
        else:
            result.append(int(part))
    return sorted(set(result))


def print_info(info: dict):
    """Pretty print PDF info"""
    print("\n=== PDF INFO ===")
    print(f"File: {info.get('path', 'N/A')}")
    print(f"Size: {info.get('size_mb', 0):.2f} MB")
    print(f"Pages: {info.get('pages', info.get('pages:', 'N/A'))}")
    print(f"Creator: {info.get('creator', info.get('metadata', {}).get('creator', 'N/A'))}")
    print(f"Producer: {info.get('producer', info.get('metadata', {}).get('producer', 'N/A'))}")
    print(f"Encrypted: {info.get('encrypted', 'N/A')}")
    print(f"Has Text: {info.get('has_text', 'N/A')}")
    print(f"Has Images: {info.get('has_images', 'N/A')}")
    if info.get('likely_scanned'):
        print("WARNING: PDF appears to be scanned (use 'ocr' command for text extraction)")
    print()


def main():
    parser = argparse.ArgumentParser(description='PDF Tools - Work with large PDFs')
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # Info command
    info_parser = subparsers.add_parser('info', help='Get PDF information')
    info_parser.add_argument('pdf', help='PDF file path')

    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract text from PDF')
    extract_parser.add_argument('pdf', help='PDF file path')
    extract_parser.add_argument('--pages', help='Page range (e.g., 1-10, 1,3,5)')
    extract_parser.add_argument('--output', '-o', help='Output text file')

    # Split command
    split_parser = subparsers.add_parser('split', help='Split PDF pages')
    split_parser.add_argument('pdf', help='PDF file path')
    split_parser.add_argument('--pages', required=True, help='Page range to extract')
    split_parser.add_argument('--output', '-o', help='Output PDF file')

    # Merge command
    merge_parser = subparsers.add_parser('merge', help='Merge multiple PDFs')
    merge_parser.add_argument('pdfs', nargs='+', help='PDF files to merge')
    merge_parser.add_argument('--output', '-o', help='Output PDF file')

    # Compress command
    compress_parser = subparsers.add_parser('compress', help='Compress PDF')
    compress_parser.add_argument('pdf', help='PDF file path')
    compress_parser.add_argument('--output', '-o', help='Output PDF file')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search text in PDF')
    search_parser.add_argument('pdf', help='PDF file path')
    search_parser.add_argument('term', help='Search term')

    # To-images command
    images_parser = subparsers.add_parser('to-images', help='Convert PDF to images')
    images_parser.add_argument('pdf', help='PDF file path')
    images_parser.add_argument('--output-dir', '-o', help='Output directory')
    images_parser.add_argument('--dpi', type=int, default=150, help='Image DPI (default: 150)')

    # OCR command
    ocr_parser = subparsers.add_parser('ocr', help='OCR scanned PDF')
    ocr_parser.add_argument('pdf', help='PDF file path')
    ocr_parser.add_argument('--output', '-o', help='Output text file')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    if args.command == 'info':
        info = get_pdf_info(args.pdf)
        print_info(info)

    elif args.command == 'extract':
        text = extract_text(args.pdf, args.pages, args.output)
        if not args.output:
            print(text[:5000] + ('\n... [truncated]' if len(text) > 5000 else ''))

    elif args.command == 'split':
        split_pdf(args.pdf, args.pages, args.output)

    elif args.command == 'merge':
        merge_pdfs(args.pdfs, args.output)

    elif args.command == 'compress':
        compress_pdf(args.pdf, args.output)

    elif args.command == 'search':
        results = search_pdf(args.pdf, args.term)
        if results:
            print(f"\nFound {len(results)} matches for '{args.term}':\n")
            for r in results[:20]:  # Limit output
                print(f"Page {r.get('page', '?')}: {r['context']}")
                print("-" * 50)
        else:
            print(f"No matches found for '{args.term}'")

    elif args.command == 'to-images':
        pdf_to_images(args.pdf, args.output_dir, args.dpi)

    elif args.command == 'ocr':
        text = ocr_pdf(args.pdf, args.output)
        if not args.output:
            print(text[:5000] + ('\n... [truncated]' if len(text) > 5000 else ''))


if __name__ == '__main__':
    main()
