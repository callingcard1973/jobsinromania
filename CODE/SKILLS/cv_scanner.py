#!/usr/bin/env python3
"""
CV Scanner - Extract, parse, and search CVs from PDF/image files.

Usage:
  python cv_scanner.py scan FOLDER [--ocr] [--force] [--lmstudio]
  python cv_scanner.py search QUERY [--nationality X] [--skill X] [--lang X] [--limit N]
  python cv_scanner.py stats
  python cv_scanner.py export output.csv [--query FILTER]
  python cv_scanner.py show ID
  python cv_scanner.py import-workers
  python cv_scanner.py dedupe
"""

import argparse
import csv
import hashlib
import json
import os
import platform
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Platform detection & defaults
# ---------------------------------------------------------------------------
IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"

if IS_LINUX:
    DEFAULT_DB = "/opt/ACTIVE/OPENDATA/DATA/CV/cv_scanner.db"
    WORKERS_DB = "/opt/WORKERS/data/workers.db"
    CV_DIRS = ["/opt/ACTIVE/OPENDATA/DATA/CV_INBOX", "/opt/ACTIVE/OPENDATA/DATA/APPLICATIONS"]
else:
    DEFAULT_DB = r"D:\MEMORY\CV\cv_scanner.db"
    WORKERS_DB = None
    CV_DIRS = []

SUPPORTED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif"}

# ---------------------------------------------------------------------------
# Nationalities dictionary
# ---------------------------------------------------------------------------
NATIONALITIES = {
    "afghan": "Afghanistan", "albanian": "Albania", "algeria": "Algeria",
    "algerian": "Algeria", "american": "United States", "arab": "Arab",
    "argentina": "Argentina", "armenian": "Armenia", "australian": "Australia",
    "austrian": "Austria", "azerbaijani": "Azerbaijan",
    "bangladesh": "Bangladesh", "bangladeshi": "Bangladesh",
    "belgian": "Belgium", "bolivian": "Bolivia", "bosnian": "Bosnia",
    "brazilian": "Brazil", "british": "United Kingdom", "bulgarian": "Bulgaria",
    "cambodian": "Cambodia", "cameroonian": "Cameroon", "canadian": "Canada",
    "chilean": "Chile", "chinese": "China", "colombian": "Colombia",
    "congolese": "Congo", "costa rican": "Costa Rica", "croatian": "Croatia",
    "cuban": "Cuba", "czech": "Czech Republic", "danish": "Denmark",
    "dominican": "Dominican Republic", "dutch": "Netherlands",
    "ecuadorian": "Ecuador", "egypt": "Egypt", "egyptian": "Egypt",
    "eritrean": "Eritrea", "estonian": "Estonia", "ethiopian": "Ethiopia",
    "filipino": "Philippines", "finnish": "Finland", "french": "France",
    "georgian": "Georgia", "german": "Germany", "ghanaian": "Ghana",
    "greek": "Greece", "guatemalan": "Guatemala", "hungarian": "Hungary",
    "india": "India", "indian": "India", "indonesian": "Indonesia",
    "iranian": "Iran", "iraqi": "Iraq", "irish": "Ireland",
    "israeli": "Israel", "italian": "Italy", "ivorian": "Ivory Coast",
    "jamaican": "Jamaica", "japanese": "Japan", "jordanian": "Jordan",
    "kazakh": "Kazakhstan", "kenyan": "Kenya", "korean": "South Korea",
    "kosovan": "Kosovo", "kosovar": "Kosovo", "kuwaiti": "Kuwait",
    "latvian": "Latvia", "lebanese": "Lebanon", "libyan": "Libya",
    "lithuanian": "Lithuania", "macedonian": "North Macedonia",
    "malaysian": "Malaysia", "malian": "Mali", "mexican": "Mexico",
    "moldovan": "Moldova", "mongolian": "Mongolia", "montenegrin": "Montenegro",
    "moroccan": "Morocco", "morocco": "Morocco", "mozambican": "Mozambique",
    "myanmar": "Myanmar", "nepal": "Nepal", "nepalese": "Nepal",
    "nepali": "Nepal", "nigerian": "Nigeria", "norwegian": "Norway",
    "pakistan": "Pakistan", "pakistani": "Pakistan", "palestinian": "Palestine",
    "panamanian": "Panama", "paraguayan": "Paraguay", "peruvian": "Peru",
    "philippines": "Philippines", "polish": "Poland", "polish": "Poland",
    "portuguese": "Portugal", "romanian": "Romania", "romana": "Romania",
    "russia": "Russia", "russian": "Russia", "rwandan": "Rwanda",
    "saudi": "Saudi Arabia", "senegalese": "Senegal", "serbian": "Serbia",
    "singaporean": "Singapore", "slovak": "Slovakia", "slovenian": "Slovenia",
    "somali": "Somalia", "south african": "South Africa",
    "spanish": "Spain", "sri lanka": "Sri Lanka", "sri lankan": "Sri Lanka",
    "sudanese": "Sudan", "swedish": "Sweden", "swiss": "Switzerland",
    "syrian": "Syria", "taiwanese": "Taiwan", "tajik": "Tajikistan",
    "tanzanian": "Tanzania", "thai": "Thailand", "tunisian": "Tunisia",
    "turkey": "Turkey", "turkish": "Turkey", "turkmen": "Turkmenistan",
    "ugandan": "Uganda", "ukraine": "Ukraine", "ukrainian": "Ukraine",
    "uruguayan": "Uruguay", "uzbek": "Uzbekistan", "uzbekistan": "Uzbekistan",
    "venezuelan": "Venezuela", "vietnamese": "Vietnam", "yemeni": "Yemen",
    "zambian": "Zambia", "zimbabwean": "Zimbabwe",
}

# ---------------------------------------------------------------------------
# Known skills for matching
# ---------------------------------------------------------------------------
KNOWN_SKILLS = [
    "welding", "welder", "tig", "mig", "mig/mag", "arc welding",
    "cnc", "cnc operator", "cnc machine", "lathe", "milling",
    "forklift", "stivuitor", "reach truck", "pallet jack",
    "electrician", "electrical", "wiring", "plc", "scada",
    "plumber", "plumbing", "pipefitter", "pipe fitting",
    "carpenter", "carpentry", "woodwork", "joinery",
    "mason", "masonry", "bricklayer", "concrete",
    "painter", "painting", "coating", "sandblasting",
    "warehouse", "logistics", "picking", "packing", "sorting",
    "driver", "truck driver", "delivery", "chauffeur",
    "mechanic", "automotive", "engine repair", "diesel",
    "assembly", "assembly line", "production", "manufacturing",
    "packaging", "food processing", "meat processing", "butcher",
    "cleaning", "housekeeping", "sanitation",
    "caregiver", "care worker", "elderly care", "home care",
    "nurse", "nursing", "healthcare", "medical",
    "cook", "chef", "kitchen", "baker", "pastry",
    "waiter", "waitress", "bartender", "barista", "hospitality",
    "agriculture", "farming", "harvesting", "greenhouse",
    "construction", "scaffolding", "demolition", "excavator",
    "crane operator", "heavy equipment", "bulldozer",
    "quality control", "qc", "inspection",
    "machine operator", "press operator", "injection molding",
    "sewing", "tailor", "textile", "garment",
    "security", "guard", "surveillance",
    "it", "programming", "software", "web development",
    "excel", "word", "autocad", "sap", "erp",
    "sales", "customer service", "receptionist",
    "accounting", "bookkeeping", "finance",
    "translation", "interpreter",
]

# ---------------------------------------------------------------------------
# Known languages
# ---------------------------------------------------------------------------
KNOWN_LANGUAGES = [
    "english", "german", "french", "spanish", "italian", "dutch",
    "portuguese", "romanian", "hindi", "urdu", "arabic", "nepali",
    "bengali", "turkish", "russian", "polish", "czech", "hungarian",
    "swedish", "norwegian", "danish", "finnish", "greek", "chinese",
    "japanese", "korean", "thai", "vietnamese", "indonesian", "malay",
    "persian", "farsi", "pashto", "punjabi", "tamil", "telugu",
    "ukrainian", "serbian", "croatian", "bosnian", "bulgarian",
    "slovak", "slovenian", "albanian", "macedonian", "latvian",
    "lithuanian", "estonian", "georgian", "azerbaijani", "kazakh",
    "uzbek", "tagalog", "amharic", "swahili", "somali", "tigrinya",
    "moldovan", "romana",
]

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
def get_db(db_path=None):
    path = db_path or DEFAULT_DB
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    init_db(conn)
    return conn


def init_db(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cvs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE,
            file_name TEXT,
            file_size INTEGER,
            file_hash TEXT,
            source_folder TEXT,
            name TEXT,
            email TEXT,
            phone TEXT,
            nationality TEXT,
            current_location TEXT,
            date_of_birth TEXT,
            gender TEXT,
            skills TEXT,
            languages TEXT,
            experience_years INTEGER,
            education TEXT,
            certifications TEXT,
            driving_license TEXT,
            target_jobs TEXT,
            raw_text TEXT,
            extraction_method TEXT,
            text_length INTEGER,
            page_count INTEGER,
            parse_confidence REAL,
            parsed_by TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now'))
        );

        CREATE INDEX IF NOT EXISTS idx_cvs_email ON cvs(email);
        CREATE INDEX IF NOT EXISTS idx_cvs_name ON cvs(name);
        CREATE INDEX IF NOT EXISTS idx_cvs_nationality ON cvs(nationality);
        CREATE INDEX IF NOT EXISTS idx_cvs_file_hash ON cvs(file_hash);

        CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT,
            status TEXT,
            message TEXT,
            extraction_method TEXT,
            duration_ms INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)

    # FTS5 table
    try:
        conn.execute("SELECT * FROM cvs_fts LIMIT 0")
    except sqlite3.OperationalError:
        conn.executescript("""
            CREATE VIRTUAL TABLE cvs_fts USING fts5(
                name, email, skills, languages, education,
                raw_text, nationality,
                content=cvs, content_rowid=id,
                tokenize='unicode61 remove_diacritics 2'
            );

            CREATE TRIGGER IF NOT EXISTS cvs_ai AFTER INSERT ON cvs BEGIN
                INSERT INTO cvs_fts(rowid, name, email, skills, languages, education, raw_text, nationality)
                VALUES (new.id, new.name, new.email, new.skills, new.languages, new.education, new.raw_text, new.nationality);
            END;

            CREATE TRIGGER IF NOT EXISTS cvs_ad AFTER DELETE ON cvs BEGIN
                INSERT INTO cvs_fts(cvs_fts, rowid, name, email, skills, languages, education, raw_text, nationality)
                VALUES ('delete', old.id, old.name, old.email, old.skills, old.languages, old.education, old.raw_text, old.nationality);
            END;

            CREATE TRIGGER IF NOT EXISTS cvs_au AFTER UPDATE ON cvs BEGIN
                INSERT INTO cvs_fts(cvs_fts, rowid, name, email, skills, languages, education, raw_text, nationality)
                VALUES ('delete', old.id, old.name, old.email, old.skills, old.languages, old.education, old.raw_text, old.nationality);
                INSERT INTO cvs_fts(rowid, name, email, skills, languages, education, raw_text, nationality)
                VALUES (new.id, new.name, new.email, new.skills, new.languages, new.education, new.raw_text, new.nationality);
            END;
        """)
    conn.commit()


def log_scan(conn, file_path, status, message="", method="", duration_ms=0):
    conn.execute(
        "INSERT INTO scan_log (file_path, status, message, extraction_method, duration_ms) VALUES (?,?,?,?,?)",
        (file_path, status, message, method, duration_ms),
    )
    conn.commit()

# ---------------------------------------------------------------------------
# Text extraction
# ---------------------------------------------------------------------------
def pypdf_extract(pdf_path):
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        parts = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                parts.append(f"--- Page {i+1} ---\n{text}")
        return "\n\n".join(parts)
    except Exception:
        return ""


def pdfplumber_extract(pdf_path):
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text:
                    parts.append(f"--- Page {i+1} ---\n{text}")
                for j, table in enumerate(page.extract_tables() or []):
                    if table:
                        parts.append(f"--- Table {j+1} ---")
                        for row in table:
                            parts.append(" | ".join(str(c) if c else "" for c in row))
        return "\n\n".join(parts)
    except Exception:
        return ""


def pdftotext_extract(pdf_path):
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", pdf_path, "-"],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def pdf_to_images(pdf_path, tmpdir):
    """Convert PDF pages to PNG images for OCR."""
    if IS_LINUX:
        subprocess.run(
            ["pdftoppm", "-png", "-r", "300", pdf_path, os.path.join(tmpdir, "page")],
            capture_output=True, timeout=120,
        )
        return sorted(Path(tmpdir).glob("page-*.png"))
    else:
        try:
            import fitz
            doc = fitz.open(pdf_path)
            images = []
            for i, page in enumerate(doc):
                pix = page.get_pixmap(dpi=300)
                img_path = os.path.join(tmpdir, f"page-{i:03d}.png")
                pix.save(img_path)
                images.append(Path(img_path))
            doc.close()
            return images
        except ImportError:
            return []


def tesseract_ocr_image(image_path, lang="eng+ron"):
    """OCR a single image file."""
    try:
        result = subprocess.run(
            ["tesseract", str(image_path), "stdout", "-l", lang],
            capture_output=True, text=True, timeout=60,
        )
        return result.stdout if result.returncode == 0 else ""
    except Exception:
        return ""


def tesseract_ocr_pdf(pdf_path, lang="eng+ron"):
    """Convert PDF to images then OCR each page."""
    with tempfile.TemporaryDirectory() as tmpdir:
        images = pdf_to_images(pdf_path, tmpdir)
        if not images:
            return ""
        parts = []
        for i, img in enumerate(images):
            text = tesseract_ocr_image(str(img), lang)
            if text.strip():
                parts.append(f"--- Page {i+1} ---\n{text}")
        return "\n\n".join(parts)


def auto_extract(file_path):
    """Try extraction methods in order, return (text, method)."""
    ext = Path(file_path).suffix.lower()

    if ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif"}:
        text = tesseract_ocr_image(file_path)
        return (text, "tesseract") if len(text.strip()) > 20 else ("", "none")

    # PDF extraction cascade
    for name, func in [("pypdf", pypdf_extract), ("pdfplumber", pdfplumber_extract),
                        ("pdftotext", pdftotext_extract)]:
        text = func(file_path)
        if len(text.strip()) > 50:
            return text, name

    # Fallback to OCR
    text = tesseract_ocr_pdf(file_path)
    if len(text.strip()) > 20:
        return text, "tesseract"

    return "", "none"

# ---------------------------------------------------------------------------
# Field parsing — regex heuristics
# ---------------------------------------------------------------------------
def extract_email(text):
    m = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text)
    return m[0].lower() if m else None


def extract_phone(text):
    phones = re.findall(
        r"(?:[\+]?\d[\d\s\-\.\(\)]{6,18}\d)", text
    )
    for p in phones:
        digits = re.sub(r"\D", "", p)
        if 7 <= len(digits) <= 15:
            return p.strip()
    return None


def extract_name(text):
    # Strategy 1: explicit label
    for pattern in [
        r"(?:full\s*name|name|nume|nombre|nom)\s*[:\-]\s*(.+)",
        r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\s*$",
    ]:
        m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if m:
            candidate = m.group(1).strip()
            if 3 < len(candidate) < 60 and not re.search(r"\d|@|www\.|http", candidate):
                return candidate

    # Strategy 2: first non-empty line that looks like a name
    for line in text.splitlines()[:10]:
        line = line.strip()
        if not line or len(line) < 3 or len(line) > 50:
            continue
        if re.search(r"\d|@|www\.|http|phone|email|address|cv|resume|curriculum", line, re.IGNORECASE):
            continue
        words = line.split()
        if 2 <= len(words) <= 4 and all(w[0].isupper() for w in words if len(w) > 1):
            return line
    return None


def extract_nationality(text):
    text_lower = text.lower()
    # Near label
    for pattern in [r"(?:nationality|citizenship|cetatenie|citizen)\s*[:\-]\s*(.+)"] :
        m = re.search(pattern, text_lower)
        if m:
            val = m.group(1).strip().split("\n")[0].strip(" .,;")
            for key, nat in NATIONALITIES.items():
                if key in val.lower():
                    return nat
            if len(val) > 2:
                return val.title()

    # Scan full text
    for key, nat in sorted(NATIONALITIES.items(), key=lambda x: -len(x[0])):
        if re.search(r"\b" + re.escape(key) + r"\b", text_lower):
            return nat
    return None


def extract_skills(text):
    text_lower = text.lower()
    found = []
    for skill in KNOWN_SKILLS:
        if re.search(r"\b" + re.escape(skill) + r"\b", text_lower):
            found.append(skill.title())
    return json.dumps(list(dict.fromkeys(found))) if found else "[]"


def extract_languages(text):
    text_lower = text.lower()
    found = []
    for lang in KNOWN_LANGUAGES:
        if re.search(r"\b" + re.escape(lang) + r"\b", text_lower):
            found.append(lang.title())
    # Deduplicate similar entries
    unique = list(dict.fromkeys(found))
    return json.dumps(unique) if unique else "[]"


def extract_experience(text):
    patterns = [
        r"(\d{1,2})\+?\s*(?:years?|ani|ans|jahre|anos)\s*(?:of\s+)?(?:experience|experienta|exp[eé]rience)",
        r"(?:experience|experienta)\s*[:\-]\s*(\d{1,2})\+?\s*(?:years?|ani)?",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except ValueError:
                pass

    # Count date ranges
    ranges = re.findall(r"(20[012]\d)\s*[\-–]\s*(20[012]\d|present|current|prezent)", text, re.IGNORECASE)
    if ranges:
        total = 0
        for start, end in ranges:
            end_year = datetime.now().year if end.lower() in ("present", "current", "prezent") else int(end)
            total += max(0, end_year - int(start))
        if total > 0:
            return total
    return None


def extract_education(text):
    section_re = re.compile(
        r"(?:education|educatie|formation|studies|studii|academic|qualifications)\s*[:\-]?\s*\n([\s\S]{10,500}?)(?:\n\s*\n|\n[A-Z])",
        re.IGNORECASE,
    )
    m = section_re.search(text)
    if m:
        return m.group(1).strip()[:300]

    # Look for degree keywords
    degrees = re.findall(
        r"(?:bachelor|master|phd|diploma|university|college|licenta|faculta|inginer|doctor|baccalaur)[^\n]{0,80}",
        text, re.IGNORECASE,
    )
    if degrees:
        return "; ".join(d.strip() for d in degrees[:3])[:300]
    return None


def extract_certifications(text):
    certs = re.findall(
        r"(?:certificate|certification|certified|diploma|attestat|calificare|brevet)[^\n]{0,80}",
        text, re.IGNORECASE,
    )
    if certs:
        items = [c.strip() for c in certs[:5]]
        return json.dumps(items)
    return "[]"


def extract_driving_license(text):
    m = re.search(
        r"(?:driving|permis|license|licence|f[uü]hrerschein|carnet)\s*[:\-]?\s*(?:de\s+conducere\s*[:\-]?\s*)?(?:cat(?:egory|egoria)?\s*[:\-]?\s*)?([A-E][0-9E,\s/\+]+)",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().rstrip(",. ")
    # Simpler patterns
    m = re.search(r"\b(cat(?:egory|\.)\s*[A-E][0-9E,\s]+)", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def extract_gender(text):
    m = re.search(r"(?:gender|sex|gen)\s*[:\-]\s*(male|female|masculin|feminin|m|f)\b", text, re.IGNORECASE)
    if m:
        val = m.group(1).lower()
        if val in ("male", "masculin", "m"):
            return "Male"
        if val in ("female", "feminin", "f"):
            return "Female"
    return None


def extract_dob(text):
    patterns = [
        r"(?:date\s*of\s*birth|dob|data\s*nasterii|born)\s*[:\-]\s*([\d]{1,2}[/.\-][\d]{1,2}[/.\-][\d]{2,4})",
        r"(?:date\s*of\s*birth|dob|data\s*nasterii|born)\s*[:\-]\s*(\d{1,2}\s+\w+\s+\d{4})",
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def extract_location(text):
    m = re.search(
        r"(?:address|location|city|oras|localitate|domiciliu|resedinta)\s*[:\-]\s*(.+)",
        text, re.IGNORECASE,
    )
    if m:
        return m.group(1).strip().split("\n")[0].strip()[:100]
    return None


def extract_target_jobs(text):
    m = re.search(
        r"(?:objective|position|target|desired\s*(?:position|job)|post\s*dorit|obiectiv)\s*[:\-]\s*(.+)",
        text, re.IGNORECASE,
    )
    if m:
        val = m.group(1).strip().split("\n")[0].strip()
        return json.dumps([val]) if val else "[]"
    return "[]"


def calculate_confidence(fields):
    weights = {
        "name": 0.20, "email": 0.20, "phone": 0.10,
        "nationality": 0.10, "skills": 0.15, "languages": 0.10,
        "experience_years": 0.05, "education": 0.05,
        "driving_license": 0.025, "certifications": 0.025,
    }
    score = 0.0
    for field, weight in weights.items():
        value = fields.get(field)
        if value and value != "[]" and value != "null":
            score += weight
    return round(score, 2)


def parse_cv_fields(text):
    fields = {
        "name": extract_name(text),
        "email": extract_email(text),
        "phone": extract_phone(text),
        "nationality": extract_nationality(text),
        "current_location": extract_location(text),
        "date_of_birth": extract_dob(text),
        "gender": extract_gender(text),
        "skills": extract_skills(text),
        "languages": extract_languages(text),
        "experience_years": extract_experience(text),
        "education": extract_education(text),
        "certifications": extract_certifications(text),
        "driving_license": extract_driving_license(text),
        "target_jobs": extract_target_jobs(text),
        "parsed_by": "regex",
    }
    fields["parse_confidence"] = calculate_confidence(fields)
    return fields

# ---------------------------------------------------------------------------
# LM Studio integration (Windows)
# ---------------------------------------------------------------------------
def lmstudio_available():
    if IS_LINUX:
        return False
    try:
        import requests as req
        r = req.get("http://localhost:1234/v1/models", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


def parse_with_lmstudio(raw_text):
    import requests as req
    prompt = f"""Extract the following fields from this CV text. Return ONLY valid JSON, no explanation.

Fields:
- name: full name (string)
- email: email address (string)
- phone: phone number with country code (string)
- nationality: country of citizenship (string)
- current_location: current city/country (string)
- skills: list of professional skills (array of strings)
- languages: list of languages spoken (array of strings)
- experience_years: total years of work experience (integer)
- education: highest education level and field (string)
- certifications: list of certifications (array of strings)
- driving_license: driving license categories (string)
- target_jobs: list of desired job positions (array of strings)

CV TEXT:
{raw_text[:3000]}

Return ONLY a JSON object:"""

    resp = req.post(
        "http://localhost:1234/v1/chat/completions",
        json={
            "model": "deepseek/deepseek-r1-0528-qwen3-8b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 1000,
        },
        timeout=120,
    )
    text = resp.json()["choices"][0]["message"]["content"]
    # Strip markdown fences and think tags
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

    data = json.loads(text.strip())
    # Normalize arrays to JSON strings
    for key in ("skills", "languages", "certifications", "target_jobs"):
        if key in data and isinstance(data[key], list):
            data[key] = json.dumps(data[key])
    data["parsed_by"] = "lmstudio"
    data["parse_confidence"] = calculate_confidence(data)
    return data

# ---------------------------------------------------------------------------
# File utilities
# ---------------------------------------------------------------------------
def compute_file_hash(file_path):
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def find_files(folder):
    folder = Path(folder)
    files = []
    for ext in SUPPORTED_EXTENSIONS:
        files.extend(folder.rglob(f"*{ext}"))
        files.extend(folder.rglob(f"*{ext.upper()}"))
    return sorted(set(files))

# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
def cmd_scan(args):
    conn = get_db(args.db)
    files = find_files(args.folder)
    if not files:
        print(f"No supported files found in {args.folder}")
        return

    print(f"Found {len(files)} files in {args.folder}")
    use_lm = args.lmstudio and lmstudio_available()
    if args.lmstudio and not use_lm:
        print("Warning: LM Studio not available, using regex parsing")

    stats = {"new": 0, "updated": 0, "skipped": 0, "errors": 0}

    for i, fpath in enumerate(files, 1):
        fpath_str = str(fpath)
        try:
            file_hash = compute_file_hash(fpath_str)
        except Exception as e:
            print(f"  [{i}/{len(files)}] ERROR: {fpath.name} - {e}")
            stats["errors"] += 1
            continue

        # Check existing
        existing = conn.execute("SELECT id, file_hash FROM cvs WHERE file_path = ?", (fpath_str,)).fetchone()
        if existing and existing["file_hash"] == file_hash and not args.force:
            stats["skipped"] += 1
            continue

        # Check duplicate by hash
        hash_match = conn.execute(
            "SELECT file_path FROM cvs WHERE file_hash = ? AND file_path != ?", (file_hash, fpath_str)
        ).fetchone()
        if hash_match and not args.force:
            log_scan(conn, fpath_str, "duplicate", f"Same as {hash_match['file_path']}")
            stats["skipped"] += 1
            continue

        # Extract text
        start = time.time()
        try:
            if args.ocr:
                ext = fpath.suffix.lower()
                if ext in {".jpg", ".jpeg", ".png", ".tiff", ".tif"}:
                    text = tesseract_ocr_image(fpath_str)
                    method = "tesseract"
                else:
                    text = tesseract_ocr_pdf(fpath_str)
                    method = "tesseract"
            else:
                text, method = auto_extract(fpath_str)
        except Exception as e:
            duration = int((time.time() - start) * 1000)
            log_scan(conn, fpath_str, "error", str(e), "", duration)
            print(f"  [{i}/{len(files)}] ERROR: {fpath.name} - {e}")
            stats["errors"] += 1
            continue

        duration = int((time.time() - start) * 1000)

        if not text or len(text.strip()) < 20:
            log_scan(conn, fpath_str, "error", "No text extracted", method, duration)
            print(f"  [{i}/{len(files)}] EMPTY: {fpath.name} ({method})")
            stats["errors"] += 1
            continue

        # Parse fields
        if use_lm:
            try:
                fields = parse_with_lmstudio(text)
            except Exception:
                fields = parse_cv_fields(text)
        else:
            fields = parse_cv_fields(text)

        # Upsert
        try:
            fsize = fpath.stat().st_size
        except Exception:
            fsize = 0

        page_count = text.count("--- Page ")
        record = {
            "file_path": fpath_str,
            "file_name": fpath.name,
            "file_size": fsize,
            "file_hash": file_hash,
            "source_folder": fpath.parent.name,
            "raw_text": text[:50000],
            "extraction_method": method,
            "text_length": len(text),
            "page_count": page_count if page_count > 0 else 1,
            **fields,
        }

        if existing:
            cols = [k for k in record if k != "file_path"]
            set_clause = ", ".join(f"{k} = ?" for k in cols)
            vals = [record[k] for k in cols] + [fpath_str]
            conn.execute(f"UPDATE cvs SET {set_clause}, updated_at = datetime('now') WHERE file_path = ?", vals)
            action = "updated"
            stats["updated"] += 1
        else:
            cols = list(record.keys())
            placeholders = ", ".join("?" for _ in cols)
            conn.execute(f"INSERT INTO cvs ({', '.join(cols)}) VALUES ({placeholders})", [record[k] for k in cols])
            action = "new"
            stats["new"] += 1

        conn.commit()
        conf = fields.get("parse_confidence", 0)
        name_str = (fields.get("name") or "Unknown")[:30]
        print(f"  [{i}/{len(files)}] {action.upper()}: {fpath.name} -> {name_str} (conf={conf:.0%}, {method}, {duration}ms)")
        log_scan(conn, fpath_str, "success", f"{action}, conf={conf}", method, duration)

    conn.close()
    print(f"\nDone: {stats['new']} new, {stats['updated']} updated, {stats['skipped']} skipped, {stats['errors']} errors")


def cmd_search(args):
    conn = get_db(args.db)
    query = args.query

    # Try FTS5 first
    fts_query = query.replace(" AND ", " ")
    results = []
    try:
        sql = """
            SELECT c.id, c.name, c.email, c.phone, c.nationality,
                   c.skills, c.languages, c.experience_years,
                   c.parse_confidence, c.file_name
            FROM cvs c
            JOIN cvs_fts f ON c.id = f.rowid
            WHERE cvs_fts MATCH ?
        """
        params = [fts_query]

        if args.nationality:
            sql += " AND c.nationality LIKE ?"
            params.append(f"%{args.nationality}%")
        if args.skill:
            sql += " AND c.skills LIKE ?"
            params.append(f"%{args.skill}%")
        if args.lang:
            sql += " AND c.languages LIKE ?"
            params.append(f"%{args.lang}%")

        sql += " ORDER BY rank LIMIT ?"
        params.append(args.limit)
        results = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError:
        pass

    # Fallback to LIKE
    if not results:
        like_q = f"%{query}%"
        sql = """
            SELECT id, name, email, phone, nationality, skills, languages,
                   experience_years, parse_confidence, file_name
            FROM cvs
            WHERE name LIKE ? OR email LIKE ? OR skills LIKE ?
               OR languages LIKE ? OR nationality LIKE ? OR raw_text LIKE ?
        """
        params = [like_q] * 6

        if args.nationality:
            sql += " AND nationality LIKE ?"
            params.append(f"%{args.nationality}%")
        if args.skill:
            sql += " AND skills LIKE ?"
            params.append(f"%{args.skill}%")
        if args.lang:
            sql += " AND languages LIKE ?"
            params.append(f"%{args.lang}%")

        sql += " LIMIT ?"
        params.append(args.limit)
        results = conn.execute(sql, params).fetchall()

    if not results:
        print(f'No CVs matching "{query}"')
        conn.close()
        return

    print(f'\nFound {len(results)} CVs matching "{query}":\n')
    print(f'{"ID":>5} {"Name":<25} {"Email":<30} {"Nationality":<14} {"Skills":<35} {"Conf":>5}')
    print("-" * 118)
    for r in results:
        skills_str = (r["skills"] or "")[:34]
        print(
            f'{r["id"]:>5} {(r["name"] or ""):<25.25} {(r["email"] or ""):<30.30} '
            f'{(r["nationality"] or ""):<14.14} {skills_str:<35} {(r["parse_confidence"] or 0):>4.0%}'
        )
    conn.close()


def cmd_stats(args):
    conn = get_db(args.db)
    total = conn.execute("SELECT COUNT(*) FROM cvs").fetchone()[0]
    if total == 0:
        print("Database is empty. Run 'scan' first.")
        conn.close()
        return

    with_email = conn.execute("SELECT COUNT(*) FROM cvs WHERE email IS NOT NULL").fetchone()[0]
    with_phone = conn.execute("SELECT COUNT(*) FROM cvs WHERE phone IS NOT NULL").fetchone()[0]
    with_name = conn.execute("SELECT COUNT(*) FROM cvs WHERE name IS NOT NULL").fetchone()[0]
    avg_conf = conn.execute("SELECT AVG(parse_confidence) FROM cvs").fetchone()[0] or 0

    print(f"\n=== CV Scanner Database Stats ===\n")
    print(f"Total CVs:        {total}")
    print(f"With name:        {with_name} ({with_name*100//total}%)")
    print(f"With email:       {with_email} ({with_email*100//total}%)")
    print(f"With phone:       {with_phone} ({with_phone*100//total}%)")
    print(f"Avg confidence:   {avg_conf:.0%}")

    # By source folder
    print(f"\n--- By Source Folder ---")
    rows = conn.execute("SELECT source_folder, COUNT(*) as cnt FROM cvs GROUP BY source_folder ORDER BY cnt DESC LIMIT 15").fetchall()
    for r in rows:
        print(f"  {r['source_folder'] or 'unknown':<30} {r['cnt']:>5}")

    # By nationality
    print(f"\n--- By Nationality ---")
    rows = conn.execute(
        "SELECT nationality, COUNT(*) as cnt FROM cvs WHERE nationality IS NOT NULL GROUP BY nationality ORDER BY cnt DESC LIMIT 15"
    ).fetchall()
    for r in rows:
        print(f"  {r['nationality']:<30} {r['cnt']:>5}")

    # By extraction method
    print(f"\n--- By Extraction Method ---")
    rows = conn.execute("SELECT extraction_method, COUNT(*) as cnt FROM cvs GROUP BY extraction_method ORDER BY cnt DESC").fetchall()
    for r in rows:
        print(f"  {r['extraction_method'] or 'unknown':<20} {r['cnt']:>5}")

    # Top skills
    print(f"\n--- Top 15 Skills ---")
    all_skills = conn.execute("SELECT skills FROM cvs WHERE skills != '[]' AND skills IS NOT NULL").fetchall()
    skill_count = {}
    for row in all_skills:
        try:
            for s in json.loads(row["skills"]):
                skill_count[s] = skill_count.get(s, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    for skill, count in sorted(skill_count.items(), key=lambda x: -x[1])[:15]:
        print(f"  {skill:<30} {count:>5}")

    # Top languages
    print(f"\n--- Top 10 Languages ---")
    all_langs = conn.execute("SELECT languages FROM cvs WHERE languages != '[]' AND languages IS NOT NULL").fetchall()
    lang_count = {}
    for row in all_langs:
        try:
            for l in json.loads(row["languages"]):
                lang_count[l] = lang_count.get(l, 0) + 1
        except (json.JSONDecodeError, TypeError):
            pass
    for lang, count in sorted(lang_count.items(), key=lambda x: -x[1])[:10]:
        print(f"  {lang:<30} {count:>5}")

    # Scan log summary
    print(f"\n--- Recent Scan Activity ---")
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM scan_log GROUP BY status ORDER BY cnt DESC"
    ).fetchall()
    for r in rows:
        print(f"  {r['status']:<15} {r['cnt']:>5}")

    conn.close()


def cmd_show(args):
    conn = get_db(args.db)
    row = conn.execute("SELECT * FROM cvs WHERE id = ?", (args.id,)).fetchone()
    if not row:
        print(f"No CV with ID {args.id}")
        conn.close()
        return

    print(f"\n{'='*60}")
    print(f"CV #{row['id']} — {row['file_name']}")
    print(f"{'='*60}")
    print(f"Name:           {row['name'] or '-'}")
    print(f"Email:          {row['email'] or '-'}")
    print(f"Phone:          {row['phone'] or '-'}")
    print(f"Nationality:    {row['nationality'] or '-'}")
    print(f"Location:       {row['current_location'] or '-'}")
    print(f"Date of Birth:  {row['date_of_birth'] or '-'}")
    print(f"Gender:         {row['gender'] or '-'}")
    print(f"Skills:         {row['skills'] or '-'}")
    print(f"Languages:      {row['languages'] or '-'}")
    print(f"Experience:     {row['experience_years'] or '-'} years")
    print(f"Education:      {row['education'] or '-'}")
    print(f"Certifications: {row['certifications'] or '-'}")
    print(f"Driving License:{row['driving_license'] or '-'}")
    print(f"Target Jobs:    {row['target_jobs'] or '-'}")
    print(f"\nFile:           {row['file_path']}")
    print(f"Size:           {row['file_size'] or 0:,} bytes")
    print(f"Source:         {row['source_folder']}")
    print(f"Extraction:     {row['extraction_method']}")
    print(f"Parsed by:      {row['parsed_by']}")
    print(f"Confidence:     {row['parse_confidence']:.0%}")
    print(f"Pages:          {row['page_count']}")
    print(f"Text length:    {row['text_length']:,} chars")
    print(f"Scanned:        {row['created_at']}")
    print(f"Updated:        {row['updated_at']}")
    print(f"\n{'-'*60}")
    print("RAW TEXT (first 2000 chars):")
    print(f"{'-'*60}")
    print((row['raw_text'] or '')[:2000])
    conn.close()


def cmd_export(args):
    conn = get_db(args.db)

    if args.query:
        fts_query = args.query.replace(" AND ", " ")
        try:
            rows = conn.execute(
                """SELECT c.* FROM cvs c JOIN cvs_fts f ON c.id = f.rowid
                   WHERE cvs_fts MATCH ? ORDER BY rank""",
                (fts_query,),
            ).fetchall()
        except sqlite3.OperationalError:
            like_q = f"%{args.query}%"
            rows = conn.execute(
                "SELECT * FROM cvs WHERE name LIKE ? OR email LIKE ? OR skills LIKE ? OR raw_text LIKE ?",
                (like_q, like_q, like_q, like_q),
            ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM cvs ORDER BY id").fetchall()

    if not rows:
        print("No records to export")
        conn.close()
        return

    export_cols = [
        "id", "name", "email", "phone", "nationality", "current_location",
        "skills", "languages", "experience_years", "education", "certifications",
        "driving_license", "target_jobs", "parse_confidence", "extraction_method",
        "parsed_by", "file_name", "file_path", "created_at",
    ]

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=export_cols)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row[col] for col in export_cols})

    print(f"Exported {len(rows)} records to {args.output}")
    conn.close()


def cmd_import_workers(args):
    workers_path = args.workers_db or WORKERS_DB
    if not workers_path or not os.path.exists(workers_path):
        print(f"Workers database not found: {workers_path}")
        return

    wconn = sqlite3.connect(workers_path)
    wconn.row_factory = sqlite3.Row
    workers = wconn.execute("SELECT * FROM workers").fetchall()
    wconn.close()

    if not workers:
        print("No workers found in workers.db")
        return

    conn = get_db(args.db)
    imported = 0
    skipped = 0

    for w in workers:
        # Check if already exists by email
        email = w["email"] if "email" in w.keys() else None
        if email:
            existing = conn.execute("SELECT id FROM cvs WHERE email = ?", (email,)).fetchone()
            if existing:
                skipped += 1
                continue

        cv_path = w["cv_path"] if "cv_path" in w.keys() else None
        record = {
            "file_path": cv_path or f"imported_worker_{w['id']}",
            "file_name": os.path.basename(cv_path) if cv_path else f"worker_{w['id']}",
            "file_size": 0,
            "file_hash": hashlib.sha256((email or str(w["id"])).encode()).hexdigest(),
            "source_folder": "workers_import",
            "name": w["name"] if "name" in w.keys() else None,
            "email": email,
            "phone": w["phone"] if "phone" in w.keys() else None,
            "nationality": w["nationality"] if "nationality" in w.keys() else None,
            "current_location": w["current_location"] if "current_location" in w.keys() else None,
            "skills": w["skills"] if "skills" in w.keys() else "[]",
            "languages": w["languages"] if "languages" in w.keys() else "[]",
            "experience_years": w["experience_years"] if "experience_years" in w.keys() else None,
            "education": w["education"] if "education" in w.keys() else None,
            "raw_text": w["raw_text"] if "raw_text" in w.keys() else "",
            "extraction_method": "imported",
            "text_length": len(w["raw_text"]) if "raw_text" in w.keys() and w["raw_text"] else 0,
            "page_count": 0,
            "parse_confidence": 0.5,
            "parsed_by": "imported",
            "certifications": "[]",
            "driving_license": None,
            "target_jobs": "[]",
            "date_of_birth": None,
            "gender": None,
        }

        try:
            cols = list(record.keys())
            placeholders = ", ".join("?" for _ in cols)
            conn.execute(f"INSERT OR IGNORE INTO cvs ({', '.join(cols)}) VALUES ({placeholders})", [record[k] for k in cols])
            imported += 1
        except Exception as e:
            print(f"  Error importing {email}: {e}")

    conn.commit()
    conn.close()
    print(f"Imported {imported} workers, {skipped} skipped (already exist)")


def cmd_dedupe(args):
    conn = get_db(args.db)

    # Find duplicates by file hash
    dupes = conn.execute("""
        SELECT file_hash, COUNT(*) as cnt, GROUP_CONCAT(id || ':' || file_name, ' | ') as files
        FROM cvs GROUP BY file_hash HAVING cnt > 1
    """).fetchall()

    if not dupes:
        # Try by email
        dupes = conn.execute("""
            SELECT email, COUNT(*) as cnt, GROUP_CONCAT(id || ':' || file_name, ' | ') as files
            FROM cvs WHERE email IS NOT NULL GROUP BY email HAVING cnt > 1
        """).fetchall()
        if dupes:
            print(f"\nFound {len(dupes)} duplicate emails:\n")
            for d in dupes:
                print(f"  {d['email'] or d['file_hash']}: {d['cnt']} copies")
                print(f"    {d['files']}")
        else:
            print("No duplicates found")
    else:
        print(f"\nFound {len(dupes)} duplicate file hashes:\n")
        for d in dupes:
            print(f"  Hash {d['file_hash'][:12]}...: {d['cnt']} copies")
            print(f"    {d['files']}")

    conn.close()

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="CV Scanner - Extract, parse, and search CVs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s scan /opt/ACTIVE/OPENDATA/DATA/CV_INBOX
  %(prog)s scan D:\\CVs --lmstudio
  %(prog)s search "electrician"
  %(prog)s search "welder" --nationality Nepal --limit 10
  %(prog)s stats
  %(prog)s show 42
  %(prog)s export results.csv --query "nurse"
  %(prog)s import-workers
  %(prog)s dedupe
        """,
    )
    parser.add_argument("--db", default=None, help=f"Database path (default: {DEFAULT_DB})")

    sub = parser.add_subparsers(dest="command")

    # scan
    p_scan = sub.add_parser("scan", help="Scan folder for CVs")
    p_scan.add_argument("folder", help="Folder to scan")
    p_scan.add_argument("--ocr", action="store_true", help="Force OCR for all files")
    p_scan.add_argument("--force", action="store_true", help="Rescan existing files")
    p_scan.add_argument("--lmstudio", action="store_true", help="Use LM Studio for field extraction")

    # search
    p_search = sub.add_parser("search", help="Search CVs")
    p_search.add_argument("query", help="Search query")
    p_search.add_argument("--nationality", help="Filter by nationality")
    p_search.add_argument("--skill", help="Filter by skill")
    p_search.add_argument("--lang", help="Filter by language")
    p_search.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")

    # stats
    sub.add_parser("stats", help="Show database statistics")

    # show
    p_show = sub.add_parser("show", help="Show full CV record")
    p_show.add_argument("id", type=int, help="CV ID")

    # export
    p_export = sub.add_parser("export", help="Export to CSV")
    p_export.add_argument("output", help="Output CSV file")
    p_export.add_argument("--query", help="Filter query")

    # import-workers
    p_import = sub.add_parser("import-workers", help="Import from workers.db")
    p_import.add_argument("--workers-db", help=f"Workers DB path (default: {WORKERS_DB})")

    # dedupe
    sub.add_parser("dedupe", help="Find duplicate CVs")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    commands = {
        "scan": cmd_scan,
        "search": cmd_search,
        "stats": cmd_stats,
        "show": cmd_show,
        "export": cmd_export,
        "import-workers": cmd_import_workers,
        "dedupe": cmd_dedupe,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
