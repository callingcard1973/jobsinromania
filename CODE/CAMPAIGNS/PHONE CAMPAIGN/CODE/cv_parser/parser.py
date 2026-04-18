"""CV text extraction and LLM parsing logic."""
import io, json, os, re, requests, datetime, sqlite3
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5:1.5b"

EXTRACT_PROMPT = """Extract structured CV data from the text below. Return ONLY valid JSON, no explanation.

Schema:
{{
  "name": "string",
  "email": "string",
  "phone": "string",
  "title": "string",
  "summary": "string",
  "experience": [{{"company": "string", "role": "string", "start": "string", "end": "string", "description": "string"}}],
  "education": [{{"institution": "string", "degree": "string", "field": "string", "start": "string", "end": "string"}}],
  "skills": ["string"],
  "languages": [{{"language": "string", "level": "string"}}]
}}

CV TEXT:
{text}

Return only the JSON object."""


def extract_pdf(file_bytes: bytes) -> str:
    import pdfplumber
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        pages = [p.extract_text() or "" for p in pdf.pages]
    text = "\n".join(pages).strip()
    if len(text) < 50:
        return _ocr_pdf(file_bytes)
    return text


def _ocr_pdf(file_bytes: bytes) -> str:
    from pdf2image import convert_from_bytes
    import pytesseract
    images = convert_from_bytes(file_bytes)
    return "\n".join(pytesseract.image_to_string(img) for img in images)


def extract_docx(file_bytes: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def extract_image(file_bytes: bytes) -> str:
    import pytesseract
    from PIL import Image
    img = Image.open(io.BytesIO(file_bytes))
    return pytesseract.image_to_string(img)


def extract_html(file_bytes: bytes) -> str:
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(file_bytes, "html.parser")
    return soup.get_text(separator="\n")


def extract_text(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8", errors="replace")


def extract_linkedin(url: str) -> str:
    """Fetch public LinkedIn profile page and extract visible text."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; CVParser/1.0)"}
    try:
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(r.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator="\n")
    except Exception as e:
        raise ValueError(f"Could not fetch LinkedIn URL: {e}")


def text_from_file(filename: str, file_bytes: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return extract_pdf(file_bytes)
    elif ext == ".docx":
        return extract_docx(file_bytes)
    elif ext in (".jpg", ".jpeg", ".png", ".webp"):
        return extract_image(file_bytes)
    elif ext in (".html", ".htm"):
        return extract_html(file_bytes)
    else:
        return extract_text(file_bytes)


def llm_parse(text: str) -> dict:
    """Send text to Ollama (streaming) and return structured CV dict."""
    prompt = EXTRACT_PROMPT.format(text=text[:3000])
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {"temperature": 0.1, "num_predict": 800}
    }
    try:
        raw = ""
        with requests.post(OLLAMA_URL, json=payload, stream=True, timeout=(10, 300)) as r:
            r.raise_for_status()
            for line in r.iter_lines():
                if line:
                    chunk = json.loads(line)
                    raw += chunk.get("response", "")
                    if chunk.get("done"):
                        break
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not match:
            raise ValueError(f"No JSON in LLM response: {raw[:200]}")
        cv_data = json.loads(match.group())
        save_to_vault(cv_data)
        return cv_data
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}")
    except requests.RequestException as e:
        raise ValueError(f"Ollama request failed: {e}")


def save_to_vault(cv: dict):
    """Save parsed CV to SQLite cv_leads table. Never raises."""
    DB_PATH = "/opt/ACTIVE/OPENDATA/DATA/master_applicants.db"
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("""CREATE TABLE IF NOT EXISTS cv_leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT,
            phone TEXT,
            title TEXT,
            skills TEXT,
            created_at TEXT,
            UNIQUE(email, phone)
        )""")
        skills_str = ", ".join((cv.get("skills") or [])[:10])
        cur.execute(
            """INSERT OR IGNORE INTO cv_leads
               (name, email, phone, title, skills, created_at)
               VALUES (?,?,?,?,?,?)""",
            (
                cv.get("name", ""),
                cv.get("email", ""),
                cv.get("phone", ""),
                cv.get("title", ""),
                skills_str,
                datetime.datetime.utcnow().isoformat(),
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass  # Never break main flow
