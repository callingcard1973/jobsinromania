#!/usr/bin/env python3
"""
CV Manager - Convert PDFs to text, parse, and make searchable.

Combines:
- PDF to text extraction (pdftotext, pypdf, pdfplumber, tesseract OCR)
- CV parsing (regex + spacy NER)
- SQLite storage for searching

Usage:
    python3 cv_manager.py --process /path/to/cv.pdf          # Process single CV
    python3 cv_manager.py --batch /path/to/folder            # Process all PDFs in folder
    python3 cv_manager.py --search "welder"                  # Search parsed CVs
    python3 cv_manager.py --stats                            # Show statistics
    python3 cv_manager.py --export /path/to/output.csv       # Export all CVs
    python3 cv_manager.py --reparse                          # Re-parse all stored text
"""

import argparse
import csv
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

try:
    import sys as _sys, os as _os
    for _p in ["/opt/ACTIVE/INFRA", r"D:\MEMORY\CODE\POSTHOG"]:
        if _os.path.exists(_p) and _p not in _sys.path:
            _sys.path.insert(0, _p)
    from posthog_track import track_applicant, track_solonet_order, track_cv_generated, ph_shutdown as _ph_shutdown
    _PH = True
except Exception:
    _PH = False
    def track_applicant(*a, **kw): pass
    def track_solonet_order(*a, **kw): pass
    def track_cv_generated(*a, **kw): pass
    def _ph_shutdown(): pass

# Add shared modules
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/WORKERS/scripts')

# Master database
MASTER_DB = '/opt/ACTIVE/OPENDATA/DATA/master_applicants.db'
CV_TEXT_DIR = '/opt/ACTIVE/OPENDATA/DATA/CV_TEXT'

# ============================================================================
# PDF TO TEXT EXTRACTION
# ============================================================================

def pdf_to_text_pdftotext(pdf_path: str) -> str:
    """Extract using poppler's pdftotext (fastest)."""
    try:
        result = subprocess.run(
            ['pdftotext', '-layout', pdf_path, '-'],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout
    except:
        pass
    return ""

def pdf_to_text_pypdf(pdf_path: str) -> str:
    """Extract using pypdf (pure Python)."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        text_parts = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
        return "\n\n".join(text_parts)
    except:
        return ""

def pdf_to_text_pdfplumber(pdf_path: str) -> str:
    """Extract using pdfplumber (good for tables)."""
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts)
    except:
        return ""

def pdf_to_text_ocr(pdf_path: str) -> str:
    """OCR using tesseract (for scanned PDFs)."""
    import tempfile
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Convert PDF to images
            result = subprocess.run(
                ['pdftoppm', '-png', '-r', '150', pdf_path, f'{tmpdir}/page'],
                capture_output=True, timeout=120
            )
            if result.returncode != 0:
                return ""

            # OCR each page
            text_parts = []
            for img_file in sorted(Path(tmpdir).glob('page-*.png')):
                result = subprocess.run(
                    ['tesseract', str(img_file), 'stdout', '-l', 'eng+ron'],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    text_parts.append(result.stdout)

            return "\n\n".join(text_parts)
    except:
        return ""

def extract_text_from_pdf(pdf_path: str) -> tuple:
    """Extract text using best available method."""
    methods = [
        ('pdftotext', pdf_to_text_pdftotext),
        ('pypdf', pdf_to_text_pypdf),
        ('pdfplumber', pdf_to_text_pdfplumber),
    ]

    for name, func in methods:
        text = func(pdf_path)
        if text and len(text.strip()) > 50:
            return text, name

    # Fallback to OCR
    text = pdf_to_text_ocr(pdf_path)
    if text and len(text.strip()) > 20:
        return text, 'tesseract'

    return "", "failed"

# ============================================================================
# CV PARSING (from cv_parser_fast.py)
# ============================================================================

SKIP_PATTERNS = [
    "curriculum vitae", "resume", "cv", "profile", "objective",
    "education", "experience", "skills", "languages", "contact",
    "personal information", "work experience", "professional",
]

COUNTRIES = {
    "morocco": "Morocco", "nepal": "Nepal", "pakistan": "Pakistan",
    "india": "India", "bangladesh": "Bangladesh", "philippines": "Philippines",
    "romania": "Romania", "turkey": "Turkey", "egypt": "Egypt",
    "sri lanka": "Sri Lanka", "vietnam": "Vietnam", "ukraine": "Ukraine",
    "moldova": "Moldova", "afghanistan": "Afghanistan", "iran": "Iran",
}

JOB_KEYWORDS = {
    "warehouse": ["warehouse", "forklift", "logistics", "packing"],
    "factory": ["factory", "production", "manufacturing", "assembly"],
    "driver": ["driver", "truck", "delivery", "transport"],
    "construction": ["construction", "builder", "welder", "plumber"],
    "nurse": ["nurse", "nursing", "caregiver", "healthcare"],
    "cleaning": ["cleaner", "cleaning", "housekeeping"],
    "agriculture": ["farm", "agriculture", "harvest", "greenhouse"],
    "hospitality": ["hotel", "restaurant", "cook", "chef", "waiter"],
}

def extract_email(text: str) -> Optional[str]:
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w{2,}', text.lower())
    return match.group() if match else None

def extract_phone(text: str) -> Optional[str]:
    text_clean = re.sub(r'[^\d+\-\s()]', ' ', text)
    patterns = [
        r'\+\d{1,3}[\s\-]?\d{2,4}[\s\-]?\d{3,4}[\s\-]?\d{3,4}',
        r'\+\d{10,15}',
        r'\d{10,12}',
    ]
    for pattern in patterns:
        match = re.search(pattern, text_clean)
        if match:
            phone = re.sub(r'[\s\-()]', '', match.group())
            if len(phone) >= 10:
                return phone
    return None

def extract_name_heuristic(text: str) -> Optional[str]:
    lines = text.strip().split('\n')
    for line in lines[:15]:
        line = re.sub(r'\s+', ' ', line.strip())
        if len(line) < 3 or len(line) > 40:
            continue
        if any(p in line.lower() for p in SKIP_PATTERNS):
            continue
        if re.search(r'[0-9@#$%^&*()+=\[\]{}|\\/<>]', line):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if w):
            return line
    return None

def extract_nationality(text: str) -> Optional[str]:
    text_lower = text.lower()
    for pattern, country in COUNTRIES.items():
        if re.search(r'\b' + re.escape(pattern) + r'\b', text_lower):
            return country
    return None

def extract_skills(text: str) -> List[str]:
    skills = []
    skill_patterns = [
        "forklift", "excel", "welding", "electrical", "plumbing",
        "cooking", "machine operator", "quality control", "safety",
        "first aid", "driving license", "ce license"
    ]
    text_lower = text.lower()
    for pattern in skill_patterns:
        if pattern in text_lower:
            skills.append(pattern.title())
    return skills[:10]

def detect_target_jobs(text: str) -> List[str]:
    text_lower = text.lower()
    jobs = []
    for category, keywords in JOB_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                jobs.append(category)
                break
    return list(set(jobs))

def parse_cv_text(cv_text: str) -> dict:
    """Parse CV text and extract fields."""
    email = extract_email(cv_text)
    return {
        "name": extract_name_heuristic(cv_text),
        "email": email,
        "phone": extract_phone(cv_text),
        "nationality": extract_nationality(cv_text),
        "skills": json.dumps(extract_skills(cv_text)),
        "target_jobs": json.dumps(detect_target_jobs(cv_text)),
    }

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def init_db():
    """Initialize database with cv_text table."""
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()

    # Extend applicants table if needed
    c.execute('''CREATE TABLE IF NOT EXISTS applicants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        phone TEXT,
        nationality TEXT,
        location TEXT,
        skills TEXT,
        experience TEXT,
        target_jobs TEXT,
        cv_file TEXT,
        source TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # CV text storage
    c.execute('''CREATE TABLE IF NOT EXISTS cv_texts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        cv_path TEXT,
        raw_text TEXT,
        extraction_method TEXT,
        parsed_at TEXT DEFAULT CURRENT_TIMESTAMP
    )''')

    # Full-text search index
    c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS cv_fts USING fts5(
        email, name, raw_text, skills, target_jobs,
        content='cv_texts',
        content_rowid='id'
    )''')

    conn.commit()
    return conn

def store_cv(conn, cv_path: str, raw_text: str, parsed: dict, method: str):
    """Store CV text and parsed data."""
    c = conn.cursor()
    email = parsed.get('email', '')

    if not email:
        # Generate placeholder email from filename
        email = f"unknown_{Path(cv_path).stem}@placeholder.local"

    # Store raw text
    c.execute('''INSERT OR REPLACE INTO cv_texts
        (email, cv_path, raw_text, extraction_method, parsed_at)
        VALUES (?, ?, ?, ?, ?)''',
        (email, cv_path, raw_text, method, datetime.now().isoformat()))

    # Store/update applicant
    c.execute('''INSERT OR REPLACE INTO applicants
        (name, email, phone, nationality, skills, target_jobs, cv_file, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
        (parsed.get('name'), email, parsed.get('phone'),
         parsed.get('nationality'), parsed.get('skills'),
         parsed.get('target_jobs'), cv_path, 'cv_manager'))

    # Update FTS index
    rowid = c.lastrowid
    c.execute('''INSERT OR REPLACE INTO cv_fts
        (rowid, email, name, raw_text, skills, target_jobs)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (rowid, email, parsed.get('name', ''), raw_text,
         parsed.get('skills', ''), parsed.get('target_jobs', '')))

    conn.commit()

# ============================================================================
# MAIN OPERATIONS
# ============================================================================

def process_pdf(pdf_path: str, save_text: bool = True) -> dict:
    """Process a single PDF: extract text, parse, store."""
    print(f"Processing: {pdf_path}")

    # Extract text
    raw_text, method = extract_text_from_pdf(pdf_path)
    if not raw_text:
        print(f"  ERROR: Could not extract text")
        return {"error": "extraction_failed"}

    print(f"  Extracted: {len(raw_text)} chars using {method}")

    # Parse CV
    parsed = parse_cv_text(raw_text)
    print(f"  Name: {parsed.get('name', 'Unknown')}")
    print(f"  Email: {parsed.get('email', 'Not found')}")
    print(f"  Phone: {parsed.get('phone', 'Not found')}")
    print(f"  Nationality: {parsed.get('nationality', 'Unknown')}")

    # Store in database
    conn = init_db()
    store_cv(conn, pdf_path, raw_text, parsed, method)
    conn.close()
    jobs = json.loads(parsed.get("target_jobs", "[]") or "[]")
    track_cv_generated(sector=jobs[0] if jobs else "unknown")

    # Optionally save text file
    if save_text:
        Path(CV_TEXT_DIR).mkdir(parents=True, exist_ok=True)
        text_file = Path(CV_TEXT_DIR) / f"{Path(pdf_path).stem}.txt"
        with open(text_file, 'w') as f:
            f.write(raw_text)
        print(f"  Saved: {text_file}")

    return parsed

def process_batch(folder_path: str):
    """Process all PDFs in a folder."""
    folder = Path(folder_path)
    pdfs = list(folder.glob('**/*.pdf'))

    print(f"Found {len(pdfs)} PDFs in {folder}")

    success = 0
    failed = 0

    for pdf in pdfs:
        result = process_pdf(str(pdf))
        if "error" in result:
            failed += 1
        else:
            success += 1

    print(f"\nDone: {success} success, {failed} failed")

def search_cvs(query: str, limit: int = 20):
    """Full-text search across all CVs."""
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()

    # FTS search
    results = c.execute('''
        SELECT a.name, a.email, a.phone, a.nationality, a.skills, a.cv_file
        FROM cv_fts f
        JOIN applicants a ON f.email = a.email
        WHERE cv_fts MATCH ?
        LIMIT ?
    ''', (query, limit)).fetchall()

    if not results:
        # Fallback to LIKE search
        q = f'%{query}%'
        results = c.execute('''
            SELECT name, email, phone, nationality, skills, cv_file
            FROM applicants
            WHERE name LIKE ? OR skills LIKE ? OR nationality LIKE ?
            LIMIT ?
        ''', (q, q, q, limit)).fetchall()

    conn.close()

    if not results:
        print(f"No CVs found matching: {query}")
        return

    print(f"\nFound {len(results)} CVs matching '{query}':\n")
    print(f"{'Name':<25} {'Email':<30} {'Phone':<15} {'Country':<12}")
    print("-" * 85)

    for row in results:
        name = (row[0] or '')[:24]
        email = (row[1] or '')[:29]
        phone = (row[2] or '')[:14]
        nat = (row[3] or '')[:11]
        print(f"{name:<25} {email:<30} {phone:<15} {nat:<12}")

def show_stats():
    """Show CV database statistics."""
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()

    total = c.execute('SELECT COUNT(*) FROM applicants WHERE source = "cv_manager"').fetchone()[0]
    with_text = c.execute('SELECT COUNT(*) FROM cv_texts').fetchone()[0]
    by_method = c.execute('SELECT extraction_method, COUNT(*) FROM cv_texts GROUP BY extraction_method').fetchall()
    by_country = c.execute('''
        SELECT nationality, COUNT(*) FROM applicants
        WHERE source = "cv_manager" AND nationality IS NOT NULL
        GROUP BY nationality ORDER BY COUNT(*) DESC LIMIT 10
    ''').fetchall()

    conn.close()

    print("=" * 60)
    print("CV MANAGER STATISTICS")
    print("=" * 60)
    print(f"\nTotal CVs processed: {total}")
    print(f"With stored text: {with_text}")

    print("\nBy extraction method:")
    for method, count in by_method:
        print(f"  {method}: {count}")

    print("\nTop nationalities:")
    for nat, count in by_country:
        print(f"  {nat}: {count}")

def export_cvs(output_path: str):
    """Export all CVs to CSV."""
    conn = sqlite3.connect(MASTER_DB)
    c = conn.cursor()

    results = c.execute('''
        SELECT a.name, a.email, a.phone, a.nationality, a.skills, a.target_jobs, a.cv_file
        FROM applicants a
        WHERE a.source = "cv_manager"
        ORDER BY a.name
    ''').fetchall()

    conn.close()

    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['name', 'email', 'phone', 'nationality', 'skills', 'target_jobs', 'cv_file'])
        writer.writerows(results)

    print(f"Exported {len(results)} CVs to {output_path}")

def import_apply_now():
    """Import Apply Now form submissions from job websites."""
    conn = init_db()
    c = conn.cursor()

    # Sources for Apply Now forms
    sources = [
        '/opt/WORKERS/data/factoryjobs.eu_applications.csv',
        '/opt/WORKERS/data/buildjobs.eu_applications.csv',
        '/opt/WORKERS/data/careworkers.eu_applications.csv',
    ]

    added = 0
    for source in sources:
        if not os.path.exists(source):
            continue

        site = Path(source).stem.replace('_applications', '')
        print(f"Importing from {site}...")

        with open(source) as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get('Email', '').lower().strip()
                if not email:
                    continue

                name = f"{row.get('First_Name', '')} {row.get('Last_Name', '')}".strip()
                phone = row.get('Phone', '')
                nationality = row.get('Nationality', '')
                skills = row.get('Skills', '')
                cv_file = row.get('CV_File', '')

                try:
                    c.execute('''INSERT OR IGNORE INTO applicants
                        (name, email, phone, nationality, skills, cv_file, source)
                        VALUES (?, ?, ?, ?, ?, ?, ?)''',
                        (name, email, phone, nationality, skills, cv_file, f'apply_now_{site}'))
                    if c.rowcount > 0:
                        added += 1
                except:
                    pass

    conn.commit()
    conn.close()
    print(f"Imported {added} new applicants from Apply Now forms")

def main():
    parser = argparse.ArgumentParser(description='CV Manager - PDF to searchable database')
    parser.add_argument('--process', type=str, help='Process single PDF')
    parser.add_argument('--batch', type=str, help='Process all PDFs in folder')
    parser.add_argument('--search', type=str, help='Search CVs')
    parser.add_argument('--stats', action='store_true', help='Show statistics')
    parser.add_argument('--export', type=str, help='Export to CSV')
    parser.add_argument('--reparse', action='store_true', help='Re-parse all stored text')
    parser.add_argument('--import-forms', action='store_true', help='Import Apply Now form submissions')

    args = parser.parse_args()

    if args.process:
        process_pdf(args.process)
    elif args.batch:
        process_batch(args.batch)
    elif args.search:
        search_cvs(args.search)
    elif args.stats:
        show_stats()
    elif args.export:
        export_cvs(args.export)
    elif args.import_forms:
        import_apply_now()
    elif args.reparse:
        print("Re-parsing not implemented yet")
    else:
        show_stats()
    _ph_shutdown()

if __name__ == '__main__':
    main()
