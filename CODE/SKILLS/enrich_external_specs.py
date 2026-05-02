#!/usr/bin/env python3
"""Enrich EU funding records with external spec links (Google Drive, Dropbox)."""
# --
import psycopg2
import re
import os
import tempfile
import subprocess
import requests

requests.packages.urllib3.disable_warnings()
DB = {"dbname": "european_funds", "user": "tudor", "host": "/var/run/postgresql", "port": 5432}

# --
def to_ascii(t):
    import unicodedata
    if not t: return ''
    return unicodedata.normalize('NFKD', str(t)).encode('ascii', 'ignore').decode('ascii')

def extract_pdf_text(path):
    try:
        r = subprocess.run(["pdftotext", "-layout", path, "-"],
                           capture_output=True, text=True, timeout=30)
        return r.stdout[:5000] if r.returncode == 0 else ""
    except Exception:
        return ""

def extract_docx_text(path):
    try:
        from docx import Document
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs)[:5000]
    except Exception:
        return ""

# --
def gdrive_download(url):
    """Download from Google Drive, handling virus scan confirmation."""
    m = re.search(r"/file/d/([^/]+)", url)
    if not m:
        return b""
    fid = m.group(1)
    dl_url = f"https://drive.google.com/uc?export=download&id={fid}"
    sess = requests.Session()
    r = sess.get(dl_url, timeout=30, allow_redirects=True)
    if b"confirm" in r.content[:5000]:
        token = re.search(r'confirm=([^&"]+)', r.text)
        if token:
            r = sess.get(dl_url + "&confirm=" + token.group(1), timeout=60)
    if len(r.content) > 100 and b"<html" not in r.content[:50].lower():
        return r.content
    return b""

def gdrive_folder_files(url):
    """List files in a public Google Drive folder (scrape HTML)."""
    try:
        r = requests.get(url, timeout=30)
        ids = re.findall(r'/file/d/([^/"]+)', r.text)
        return [f"https://drive.google.com/uc?export=download&id={fid}" for fid in set(ids)]
    except Exception:
        return []

def extract_from_bytes(data):
    """Extract text from raw file bytes (PDF or DOCX)."""
    if data[:5] == b"%PDF-":
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(data)
            tmp = f.name
        text = extract_pdf_text(tmp)
        os.unlink(tmp)
        return text
    if data[:2] == b"PK" and b"word/" in data[:2000]:
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
            f.write(data)
            tmp = f.name
        text = extract_docx_text(tmp)
        os.unlink(tmp)
        return text
    return ""

def download_and_extract(url):
    """Download a file and extract text based on type."""
    try:
        r = requests.get(url, timeout=60, allow_redirects=True)
        if r.status_code != 200 or len(r.content) < 100:
            return ""
        data = r.content
        cd = r.headers.get("content-disposition", "")
        filename = ""
        m = re.search(r'filename[*]?=(?:UTF-8\'\')?(.+)', cd)
        if m:
            filename = m.group(1).strip().strip('"')
        # Detect type
        if data[:5] == b"%PDF-" or filename.lower().endswith(".pdf"):
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
                f.write(data)
                tmp = f.name
            text = extract_pdf_text(tmp)
            os.unlink(tmp)
            return text
        if filename.lower().endswith(".docx") or (data[:2] == b"PK" and b"word/" in data[:2000]):
            with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as f:
                f.write(data)
                tmp = f.name
            text = extract_docx_text(tmp)
            os.unlink(tmp)
            return text
        return ""
    except Exception:
        return ""

# --
def extract_urls(text):
    """Extract Google Drive and Dropbox URLs from text."""
    urls = []
    # Google Drive file
    for m in re.finditer(r'https?://drive\.google\.com/file/d/[^\s,)]+', text):
        urls.append(("gdrive_file", m.group()))
    # Google Drive folder
    for m in re.finditer(r'https?://drive\.google\.com/drive/folders/[^\s,)]+', text):
        urls.append(("gdrive_folder", m.group()))
    # Dropbox
    for m in re.finditer(r'https?://(?:www\.)?dropbox\.com/[^\s,)]+', text):
        urls.append(("dropbox", m.group()))
    return urls

# --
def main():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor()
    cur.execute("""SELECT id, descriere FROM beneficiari_privati
        WHERE (descriere LIKE '%%drive.google%%' OR descriere LIKE '%%dropbox%%')
        AND (spec_text IS NULL OR spec_text = '')""")
    rows = cur.fetchall()
    print(f"Found {len(rows)} records with external links to enrich")

    enriched = 0
    for rid, descriere in rows:
        urls = extract_urls(descriere)
        if not urls:
            continue
        texts = []
        spec_urls = []
        for utype, url in urls:
            spec_urls.append(url)
            if utype == "gdrive_file":
                data = gdrive_download(url)
                if data:
                    t = extract_from_bytes(data)
                    if t:
                        texts.append(t)
            elif utype == "gdrive_folder":
                file_urls = gdrive_folder_files(url)
                for fu in file_urls[:5]:
                    data = gdrive_download(fu)
                    if data:
                        t = extract_from_bytes(data)
                        if t:
                            texts.append(t)
            elif utype == "dropbox":
                pass  # Dropbox requires auth, skip

        if texts:
            spec_text = to_ascii("\n---\n".join(texts))[:5000]
            spec_url = " | ".join(spec_urls)
            cur.execute("UPDATE beneficiari_privati SET spec_text = %s, spec_url = %s WHERE id = %s",
                        (spec_text, spec_url, rid))
            conn.commit()
            enriched += 1
            print(f"  {rid}: {len(spec_text)} chars from {len(texts)} files")
        else:
            print(f"  {rid}: no text extracted from {len(urls)} URLs")

    conn.close()
    print(f"\nDone: {enriched}/{len(rows)} enriched")

if __name__ == "__main__":
    main()
