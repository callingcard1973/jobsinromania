#!/usr/bin/env python3
"""
internaltransfers.eu — Multilingual Pages + ANOFM Jobs PDF Generator

1. Translates 5 HTML pages to Nepali, Urdu, Sinhala, Pashto
2. Generates ANOFM Jobs PDF in 5 languages (en/ne/ur/si/ps)
3. Deploys everything to A2 Hosting via cPanel API

Usage:
    python internaltransfers_deploy.py                    # Everything
    python internaltransfers_deploy.py --html-only        # Only translate + deploy HTML
    python internaltransfers_deploy.py --pdf-only         # Only generate + deploy PDFs
    python internaltransfers_deploy.py --generate-only    # Generate locally, don't deploy
    python internaltransfers_deploy.py --lang ne          # Single language only
"""

import os
import re
import csv
import json
import ssl
import time
import argparse
import subprocess
import urllib.request
import urllib.parse
import unicodedata
from io import StringIO
from datetime import datetime
from job_data import JOB_TRANSLATIONS, COMPANY_NAMES, DEFAULT_DESCRIPTION

def to_ascii(text):
    """Normalize text to ASCII (remove diacritics)."""
    if not text:
        return ""
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii')

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(SCRIPT_DIR, "fonts")
OUTPUT_DIR = os.path.join(SCRIPT_DIR, "output")

CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_PORT = 2083
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
SITE_DOMAIN = "internaltransfers.eu"
DOCROOT = f"/home/{CPANEL_USER}/{SITE_DOMAIN}"

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

LANGUAGES = {
    "en": {"name": "English", "native": "English", "font": "NotoSans", "rtl": False},
    "fr": {"name": "French", "native": "Français", "font": "NotoSans", "rtl": False},
    "ru": {"name": "Russian", "native": "Русский", "font": "NotoSans", "rtl": False},
    "ne": {"name": "Nepali", "native": "नेपाली", "font": "NotoSansDevanagari", "rtl": False},
    "ur": {"name": "Urdu", "native": "اردو", "font": "NotoNaskhArabic", "rtl": True},
    "si": {"name": "Sinhala", "native": "සිංහල", "font": "NotoSansSinhala", "rtl": False},
    "ps": {"name": "Pashto", "native": "پښتو", "font": "NotoNaskhArabic", "rtl": True},
    "sw": {"name": "Swahili", "native": "Kiswahili", "font": "NotoSans", "rtl": False},
}

# Languages that have argostranslate offline packages installed
ARGOS_LANGUAGES = {"fr", "ru", "ur"}

FONT_FILES = {
    "NotoSans": os.path.join(FONTS_DIR, "NotoSans-Regular.ttf"),
    "NotoSansDevanagari": os.path.join(FONTS_DIR, "NotoSansDevanagari-Regular.ttf"),
    "NotoNaskhArabic": os.path.join(FONTS_DIR, "NotoNaskhArabic-Regular.ttf"),
    "NotoSansSinhala": os.path.join(FONTS_DIR, "NotoSansSinhala-Regular.ttf"),
}

PAGES = ["index.html", "hire-workers.html", "find-work.html", "about.html", "contact.html"]

# ANOFM sectors relevant for migrant workers
RELEVANT_SECTORS = {
    "Constructii / Instalatii": "Construction & Installation",
    "Productie / Logistica": "Production & Logistics",
    "RESTAURANTE": "Restaurants",
    "Turism / Alimentatie": "Tourism & Food Service",
    "Servicii transport / curierat": "Transport & Courier",
    "Agricultura / Zootehnie": "Agriculture",
    "Au pair / Babysitter / Curatenie": "Cleaning & Childcare",
    "FABRICAREA ARTICOLELOR DE IMBRACAMINTE": "Garment Manufacturing",
    "SERVICE AUTO": "Auto Service & Mechanics",
    "PRODUCTIE MOBILA": "Furniture Production",
    "COMERT": "Commerce & Retail",
    "Altele": "Other",
}

# Pre-translated labels from eures_translations.py (ne/ur/ps) + manual (si/sw)
LABEL = {
    "company": {"en": "Company", "fr": "Entreprise", "ru": "Компания", "ne": "कम्पनी", "ur": "کمپنی", "si": "සමාගම", "ps": "شرکت", "sw": "Kampuni"},
    "location": {"en": "Location", "fr": "Lieu", "ru": "Место", "ne": "स्थान", "ur": "مقام", "si": "ස්ථානය", "ps": "ځای", "sw": "Eneo"},
    "salary": {"en": "Salary", "fr": "Salaire", "ru": "Зарплата", "ne": "तलब", "ur": "تنخواہ", "si": "වැටුප", "ps": "معاش", "sw": "Mshahara"},
    "positions": {"en": "Positions", "fr": "Postes", "ru": "Позиций", "ne": "पदहरू", "ur": "عہدے", "si": "තනතුරු", "ps": "پوستونه", "sw": "Nafasi"},
    "apply_now": {"en": "APPLY NOW", "fr": "POSTULER", "ru": "ПОДАТЬ ЗАЯВКУ", "ne": "अहिले आवेदन दिनुहोस्", "ur": "ابھی درخواست دیں", "si": "දැන් අයදුම් කරන්න", "ps": "اوس غوښتنه وکړئ", "sw": "OMBA SASA"},
    "description": {"en": "Description", "fr": "Description", "ru": "Описание", "ne": "विवरण", "ur": "تفصیل", "si": "විස්තරය", "ps": "تفصیل", "sw": "Maelezo"},
    "ref": {"en": "Ref #", "fr": "Réf #", "ru": "Ссылка #", "ne": "सन्दर्भ #", "ur": "حوالہ #", "si": "යොමු #", "ps": "حواله #", "sw": "Kumb. #"},
    "sector": {"en": "Sector", "fr": "Secteur", "ru": "Сектор", "ne": "क्षेत्र", "ur": "شعبہ", "si": "අංශය", "ps": "سکتور", "sw": "Sekta"},
}

TODAY = datetime.now().strftime("%Y-%m-%d")
TODAY_DISPLAY = datetime.now().strftime("%d %B %Y")

# =============================================================================
# TRANSLATION
# =============================================================================

CACHE_FILE = os.path.join(SCRIPT_DIR, "translation_cache.json")
_translate_cache = {}


def _load_cache():
    """Load translation cache from disk."""
    global _translate_cache
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                _translate_cache = json.load(f)
            print(f"  Loaded {len(_translate_cache)} cached translations")
        except Exception:
            _translate_cache = {}


def _save_cache():
    """Save translation cache to disk for reuse across runs."""
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(_translate_cache, f, ensure_ascii=False, indent=0)
        print(f"  Saved {len(_translate_cache)} translations to cache")
    except Exception as e:
        print(f"  Cache save error: {e}")


def translate_text(text, target_lang):
    """Translate English text to target language. Prefers argostranslate (offline) when available."""
    if not text or not text.strip() or target_lang == "en":
        return text

    cache_key = f"{target_lang}:{text[:100]}"
    if cache_key in _translate_cache:
        return _translate_cache[cache_key]

    result = text

    # Try argostranslate first (offline, fast) for supported languages
    if target_lang in ARGOS_LANGUAGES:
        try:
            import argostranslate.translate
            result = argostranslate.translate.translate(text, "en", target_lang)
            if result and result != text:
                _translate_cache[cache_key] = result
                return result
        except Exception:
            pass  # Fall through to Google Translate

    # Fallback: Google Translate (online)
    try:
        from deep_translator import GoogleTranslator
        if len(text) > 4500:
            chunks = _split_text(text, 4500)
            translated = []
            for chunk in chunks:
                t = GoogleTranslator(source="en", target=target_lang).translate(chunk)
                translated.append(t or chunk)
                time.sleep(0.3)
            result = "\n".join(translated)
        else:
            result = GoogleTranslator(source="en", target=target_lang).translate(text)
            if not result:
                result = text
            time.sleep(0.15)
    except Exception as e:
        print(f"    Translation error ({target_lang}): {e}")
        result = text

    _translate_cache[cache_key] = result
    return result


def _split_text(text, max_len):
    """Split at paragraph boundaries."""
    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for p in paragraphs:
        if len(current) + len(p) + 2 > max_len and current:
            chunks.append(current)
            current = p
        else:
            current = current + "\n\n" + p if current else p
    if current:
        chunks.append(current)
    return chunks


def translate_batch(texts, target_lang):
    """Translate a list of texts, return list of translations."""
    if target_lang == "en":
        return list(texts)
    results = []
    for text in texts:
        results.append(translate_text(text, target_lang))
    return results


# Pre-translated static strings for PDF
PDF_STRINGS = {
    "en": {
        "title": "Jobs in Romania",
        "date": f"10 February 2026",
        "intro": (
            "These are official job vacancies published by ANOFM (National Agency for Employment) "
            "of the Romanian Government. All positions are verified and legal.\n\n"
            "Workers from Nepal, Sri Lanka, and Pakistan who are already in Romania or Europe "
            "can apply to change their employer legally through Internal Transfers EU."
        ),
        "contact_header": "Apply Now",
        "contact_web": "Website: internaltransfers.eu",
        "contact_wa": "Website: interjob.ro/apply.html",
        "contact_email": "Email: office@internaltransfers.eu",
        "total_fmt": "Total: {jobs} job listings with {positions} available positions",
        "sector_fmt": "{count} jobs, {positions} positions",
        "col_job": "Job Title",
        "col_location": "Location",
        "col_positions": "Pos.",
        "col_salary": "Salary (RON)",
        "apply_cta": "Click the button above to apply for these positions.",
        "apply_sector": "To apply for any position in this section, click APPLY NOW",
        "nationality_notice": "This form is open to all nationalities. Priority is given to candidates already present in Romania.",
        "available_jobs": "Available Jobs",
        "not_specified": "Not specified in government data",
        "final_title": "Apply Now — Change Your Job Legally",
        "final_text": (
            "You have the legal right to change your employer in Europe.\n\n"
            "Under Romanian and EU work permit regulations, internal transfers "
            "between employers are legal and protected.\n\n"
            "Submit your CV and profile through our website. We will match you "
            "with the right employer."
        ),
        "page_footer": "Jobs in Romania — 10 February 2026 — internaltransfers.eu",
    }
}


def get_pdf_strings(lang):
    """Get translated PDF strings for a language."""
    if lang == "en":
        return PDF_STRINGS["en"]
    if lang in PDF_STRINGS:
        return PDF_STRINGS[lang]

    print(f"  Translating PDF strings to {LANGUAGES[lang]['name']}...")
    en = PDF_STRINGS["en"]
    translated = {}
    for key, val in en.items():
        if "{" in val:  # format strings — translate the template
            translated[key] = translate_text(val.replace("{jobs}", "XJOBSX").replace("{positions}", "XPOSX").replace("{count}", "XCOUNTX"), lang)
            translated[key] = translated[key].replace("XJOBSX", "{jobs}").replace("XPOSX", "{positions}").replace("XCOUNTX", "{count}")
        else:
            translated[key] = translate_text(val, lang)
    PDF_STRINGS[lang] = translated
    return translated


# =============================================================================
# CPANEL API
# =============================================================================

def cpanel_request(endpoint, params=None):
    """Make a cPanel UAPI request."""
    url = f"https://{CPANEL_HOST}:{CPANEL_PORT}/execute/{endpoint}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"
    })
    resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=30)
    return json.loads(resp.read())


def cpanel_mkdir(remote_dir):
    """Create directory on A2 via cPanel API."""
    try:
        cpanel_request("Fileman/mkdir", {
            "path": remote_dir,
            "permissions": "0755",
        })
    except Exception:
        pass  # Directory may already exist


def cpanel_upload(remote_path, content, binary=False):
    """Upload file to A2 via cPanel Fileman API."""
    dir_path = os.path.dirname(remote_path)
    file_name = os.path.basename(remote_path)

    if binary:
        # For binary files (PDFs), use multipart upload
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="dir"\r\n\r\n'
            f"{dir_path}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="file-1"; filename="{file_name}"\r\n'
            f"Content-Type: application/pdf\r\n\r\n"
        ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")

        url = f"https://{CPANEL_HOST}:{CPANEL_PORT}/execute/Fileman/upload_files"
        req = urllib.request.Request(url, data=body, headers={
            "Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        })
        resp = urllib.request.urlopen(req, context=SSL_CTX, timeout=60)
        data = json.loads(resp.read())
        return data.get("status") == 1
    else:
        # For text files, use save_file_content
        params = {
            "dir": dir_path,
            "file": file_name,
            "from_charset": "UTF-8",
            "to_charset": "UTF-8",
            "content": content,
        }
        data = cpanel_request("Fileman/save_file_content", params)
        return data.get("status") == 1


def cpanel_get_file(remote_path):
    """Download file from A2 via cPanel API."""
    dir_path = os.path.dirname(remote_path)
    file_name = os.path.basename(remote_path)
    data = cpanel_request("Fileman/get_file_content", {
        "dir": dir_path,
        "file": file_name,
    })
    return data.get("data", {}).get("content", "")


# =============================================================================
# HTML TRANSLATION
# =============================================================================

def fetch_html_pages():
    """Fetch all 5 HTML pages from A2 Hosting."""
    pages = {}
    for page in PAGES:
        print(f"  Fetching {page}...")
        try:
            # Try curl directly (works on both raspibig and Windows)
            result = subprocess.run(
                ["curl", "-sL", f"https://www.{SITE_DOMAIN}/{page}"],
                capture_output=True, text=True, timeout=15
            )
            if result.stdout and len(result.stdout) > 100:
                pages[page] = result.stdout
                print(f"    OK ({len(result.stdout)} chars)")
                continue
        except Exception:
            pass
        # Fallback to cPanel API
        try:
            content = cpanel_get_file(f"{DOCROOT}/{page}")
            if content:
                pages[page] = content
                print(f"    OK via cPanel ({len(content)} chars)")
        except Exception as e:
            print(f"    ERROR: {e}")
    return pages


def translate_html(html, target_lang):
    """Translate visible text in HTML while preserving structure."""
    if target_lang == "en":
        return html

    # Extract text segments between > and <
    # Match text content between tags, excluding scripts/styles
    in_script = False
    result = []
    i = 0
    texts_to_translate = []
    text_positions = []

    # Simple state machine: find text between > and <
    while i < len(html):
        if html[i:i+7].lower() == '<script':
            end = html.find('</script>', i)
            if end == -1:
                result.append(html[i:])
                break
            result.append(html[i:end+9])
            i = end + 9
            continue
        if html[i:i+6].lower() == '<style':
            end = html.find('</style>', i)
            if end == -1:
                result.append(html[i:])
                break
            result.append(html[i:end+8])
            i = end + 8
            continue
        if html[i] == '<':
            end = html.find('>', i)
            if end == -1:
                result.append(html[i:])
                break
            tag = html[i:end+1]
            result.append(tag)
            i = end + 1
            continue
        # Text content
        end = html.find('<', i)
        if end == -1:
            text = html[i:]
            if text.strip():
                texts_to_translate.append(text.strip())
                text_positions.append(len(result))
                result.append(text)  # placeholder
            else:
                result.append(text)
            break
        text = html[i:end]
        if text.strip() and len(text.strip()) > 1:
            # Skip if looks like just whitespace, numbers, or symbols
            clean = text.strip()
            if not re.match(r'^[\d\s\-\+\.\,\;\:\&\#\;]+$', clean) and not clean.startswith('&#'):
                texts_to_translate.append(clean)
                text_positions.append(len(result))
                result.append(text)  # placeholder with original whitespace
            else:
                result.append(text)
        else:
            result.append(text)
        i = end

    # Batch translate
    if texts_to_translate:
        print(f"    Translating {len(texts_to_translate)} text segments...")
        translated = translate_batch(texts_to_translate, target_lang)
        for idx, pos in enumerate(text_positions):
            original = result[pos]
            # Preserve leading/trailing whitespace from original
            leading = original[:len(original) - len(original.lstrip())]
            trailing = original[len(original.rstrip()):]
            result[pos] = leading + translated[idx] + trailing

    translated_html = "".join(result)

    # Fix html lang attribute
    translated_html = re.sub(r'<html\s+lang="[^"]*"', f'<html lang="{target_lang}"', translated_html)

    # Add dir="rtl" for RTL languages
    if LANGUAGES[target_lang]["rtl"]:
        translated_html = translated_html.replace(f'<html lang="{target_lang}"',
                                                   f'<html lang="{target_lang}" dir="rtl"')

    # Fix internal links
    for page in PAGES:
        translated_html = translated_html.replace(f'href="{page}"', f'href="/{target_lang}/{page}"')
        translated_html = translated_html.replace(f"href='{page}'", f"href='/{target_lang}/{page}'")
    translated_html = translated_html.replace('href="/"', f'href="/{target_lang}/index.html"')

    # Fix asset paths to absolute
    translated_html = translated_html.replace('href="css/', 'href="/css/')
    translated_html = translated_html.replace('src="js/', 'src="/js/')
    translated_html = translated_html.replace('src="images/', 'src="/images/')
    translated_html = translated_html.replace("href='css/", "href='/css/")
    translated_html = translated_html.replace("src='js/", "src='/js/")

    return translated_html


def inject_lang_switcher(html, current_lang, current_page):
    """Add language switcher bar after <body> or at top of header."""
    switcher_links = []
    for code, info in LANGUAGES.items():
        if code == "en":
            href = f"/{current_page}"
        else:
            href = f"/{code}/{current_page}"
        if code == current_lang:
            switcher_links.append(f'<span class="lang-active">{info["native"]}</span>')
        else:
            dir_attr = ' dir="rtl"' if info["rtl"] else ''
            switcher_links.append(f'<a href="{href}"{dir_attr}>{info["native"]}</a>')

    switcher_html = f'''<div class="lang-switcher" style="background:#1a1a2e;padding:8px 0;text-align:center;font-size:14px;">
  <div class="container" style="max-width:1200px;margin:0 auto;">
    {' <span style="color:#555;margin:0 3px;">|</span> '.join(switcher_links)}
  </div>
</div>
<style>
.lang-switcher a {{ color: #9ca3af; text-decoration: none; margin: 0 6px; }}
.lang-switcher a:hover {{ color: #fff; }}
.lang-switcher .lang-active {{ color: #10b981; font-weight: bold; margin: 0 6px; }}
</style>'''

    # Insert after <body>
    html = html.replace('<body>', f'<body>\n{switcher_html}', 1)
    return html


def inject_hreflang(html, page_name):
    """Add hreflang tags for all language versions."""
    hreflang_tags = []
    for code in LANGUAGES:
        if code == "en":
            href = f"https://www.{SITE_DOMAIN}/{page_name}"
        else:
            href = f"https://www.{SITE_DOMAIN}/{code}/{page_name}"
        hreflang_tags.append(f'<link rel="alternate" hreflang="{code}" href="{href}">')
    hreflang_tags.append(f'<link rel="alternate" hreflang="x-default" href="https://www.{SITE_DOMAIN}/{page_name}">')
    hreflang_str = "\n    ".join(hreflang_tags)
    html = html.replace('</head>', f'    {hreflang_str}\n</head>')
    return html


def inject_transfer_message(html, lang):
    """Add prominent callout about legal job transfers."""
    msg_en = (
        "You have the legal right to change your employer in Europe. "
        "Under Romanian and EU work permit regulations, you can transfer to a new job legally. "
        "Workers from Nepal, Sri Lanka, and Pakistan already in Romania or Europe can apply now."
    )
    msg = translate_text(msg_en, lang) if lang != "en" else msg_en
    btn_text = translate_text("Apply Now — Send Your CV", lang) if lang != "en" else "Apply Now — Send Your CV"

    dir_attr = ' dir="rtl"' if LANGUAGES[lang]["rtl"] else ''
    callout = f'''<section class="transfer-callout" style="background:linear-gradient(135deg,#065f46,#10b981);padding:40px 20px;text-align:center;color:#fff;"{dir_attr}>
  <div class="container" style="max-width:800px;margin:0 auto;">
    <h2 style="font-size:24px;margin-bottom:15px;">&#9989; {translate_text("Legal Job Transfer", lang) if lang != "en" else "Legal Job Transfer"}</h2>
    <p style="font-size:16px;line-height:1.6;margin-bottom:20px;">{msg}</p>
    <a href="{"find-work.html" if lang == "en" else f"/{lang}/find-work.html"}" style="display:inline-block;background:#fff;color:#065f46;padding:12px 30px;border-radius:8px;font-weight:bold;text-decoration:none;font-size:16px;">{btn_text}</a>
  </div>
</section>'''

    # Insert before footer
    html = html.replace('<!-- Footer -->', f'{callout}\n\n    <!-- Footer -->')
    # If no comment marker, insert before </body>
    if callout not in html:
        html = html.replace('<footer', f'{callout}\n\n<footer')
    return html


def inject_pdf_links(html, lang):
    """Add PDF download links section."""
    pdf_links = []
    for code, info in LANGUAGES.items():
        filename = f"jobs-romania-{TODAY}-{code}.pdf"
        pdf_links.append(f'<a href="/pdf/{filename}" style="color:#1a56db;margin:0 10px;">{info["native"]} PDF</a>')

    dl_title = translate_text("Download Jobs List (PDF)", lang) if lang != "en" else "Download Jobs List (PDF)"
    section = f'''<section style="background:#f0fdf4;padding:25px 20px;text-align:center;">
  <div class="container" style="max-width:800px;margin:0 auto;">
    <h3 style="color:#065f46;margin-bottom:10px;">&#128196; {dl_title}</h3>
    <p>{" | ".join(pdf_links)}</p>
  </div>
</section>'''

    # Insert before the transfer callout or footer
    if '<section class="transfer-callout"' in html:
        html = html.replace('<section class="transfer-callout"', f'{section}\n\n<section class="transfer-callout"')
    elif '<!-- Footer -->' in html:
        html = html.replace('<!-- Footer -->', f'{section}\n\n    <!-- Footer -->')
    elif '<footer' in html:
        html = html.replace('<footer', f'{section}\n\n<footer')
    return html


def inject_rtl_css(html):
    """Add RTL CSS overrides for Urdu/Pashto pages."""
    rtl_css = '''<style>
html[dir="rtl"] body { direction: rtl; text-align: right; }
html[dir="rtl"] .nav-links { flex-direction: row-reverse; }
html[dir="rtl"] .hero-cta { flex-direction: row-reverse; }
html[dir="rtl"] .industry-grid { direction: rtl; }
html[dir="rtl"] .cta-grid { direction: rtl; }
html[dir="rtl"] .trust-badges { direction: rtl; }
html[dir="rtl"] .contact-grid { direction: rtl; }
html[dir="rtl"] .footer-grid { direction: rtl; }
html[dir="rtl"] .footer-col ul { padding-right: 0; padding-left: 0; }
html[dir="rtl"] input, html[dir="rtl"] select, html[dir="rtl"] textarea { text-align: right; }
</style>'''
    html = html.replace('</head>', f'{rtl_css}\n</head>')
    return html


def process_all_html(pages_dict, target_langs, output_dir):
    """Process all HTML pages for all target languages."""
    os.makedirs(output_dir, exist_ok=True)
    results = {}

    for lang in target_langs:
        info = LANGUAGES[lang]
        print(f"\n  [{lang.upper()}] {info['name']}...")
        lang_dir = os.path.join(output_dir, lang) if lang != "en" else output_dir
        os.makedirs(lang_dir, exist_ok=True)

        for page_name, html in pages_dict.items():
            print(f"    {page_name}...")

            if lang != "en":
                translated = translate_html(html, lang)
            else:
                translated = html

            # Inject components
            translated = inject_lang_switcher(translated, lang, page_name)
            translated = inject_hreflang(translated, page_name)

            # Add transfer message to index and find-work
            if page_name in ("index.html", "find-work.html"):
                translated = inject_transfer_message(translated, lang)

            # Add PDF download links to index
            if page_name == "index.html":
                translated = inject_pdf_links(translated, lang)

            # RTL CSS
            if info["rtl"]:
                translated = inject_rtl_css(translated)

            # Save
            out_path = os.path.join(lang_dir, page_name)
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(translated)
            results.setdefault(lang, []).append(page_name)
            print(f"      Saved ({len(translated)} chars)")

    return results


# =============================================================================
# ANOFM PDF GENERATION
# =============================================================================

def fetch_anofm_csv():
    """Fetch ANOFM latest CSV — local file on raspibig or SSH from Windows."""
    local_path = "/opt/ACTIVE/OPENDATA/DATA/ROMANIA/ANOFM/anofm_latest.csv"
    if os.path.exists(local_path):
        print(f"  Reading local {local_path}...")
        with open(local_path, "r", encoding="utf-8") as f:
            data = f.read()
        print(f"  OK ({len(data)} bytes)")
        return data
    print("  Fetching ANOFM data from raspibig via SSH...")
    result = subprocess.run(
        ["ssh", "tudor@192.168.100.21", f"cat {local_path}"],
        capture_output=True, text=True, encoding="utf-8", timeout=30
    )
    if result.returncode != 0:
        raise RuntimeError(f"SSH failed: {result.stderr}")
    print(f"  OK ({len(result.stdout)} bytes)")
    return result.stdout


def parse_anofm_jobs(csv_text):
    """Parse CSV, filter to relevant sectors, enrich with English titles, descriptions, companies, refs."""
    reader = csv.DictReader(StringIO(csv_text))
    jobs_by_sector = {}
    total_jobs = 0
    total_positions = 0
    ref_counter = 10001

    for row in reader:
        sector_ro = row.get("sector", "").strip()
        if sector_ro not in RELEVANT_SECTORS:
            continue

        sector_en = RELEVANT_SECTORS[sector_ro]
        location = row.get("location", "")
        parts = [p.strip() for p in location.split(">")]
        city = parts[-1].title() if len(parts) > 1 else location.title()
        county = parts[0].title() if parts else ""

        positions = 0
        try:
            positions = int(row.get("positions_available", 0))
        except (ValueError, TypeError):
            positions = 1

        # Look up English title + description from job_data.py
        title_ro = row.get("job_title", "").strip()
        title_upper = title_ro.upper().strip()
        title_ascii = to_ascii(title_upper)  # Normalized for matching
        title_en = None
        description = None

        # Try exact match, then uppercase match, then ASCII-normalized match
        if title_ro in JOB_TRANSLATIONS:
            title_en, description = JOB_TRANSLATIONS[title_ro]
        elif title_upper in JOB_TRANSLATIONS:
            title_en, description = JOB_TRANSLATIONS[title_upper]
        else:
            # ASCII-normalized matching (handles diacritics)
            for key, (en, desc) in JOB_TRANSLATIONS.items():
                key_ascii = to_ascii(key.upper())
                if title_ascii == key_ascii:
                    title_en, description = en, desc
                    break
                # Partial match: check if title starts with a known key
                if title_ascii.startswith(key_ascii) or key_ascii.startswith(title_ascii):
                    title_en, description = en, desc
                    break

        if not title_en:
            title_en = title_ro.title()
            description = DEFAULT_DESCRIPTION

        # Assign fake company from sector pool
        company_pool = COMPANY_NAMES.get(sector_en, COMPANY_NAMES["Other"])
        company = company_pool[hash(title_ro + city) % len(company_pool)]

        # Salary
        salary = format_salary_str(row.get("salary_min", ""), row.get("salary_max", ""), row.get("salary", ""))

        # Reference number
        ref = f"IT-26-{ref_counter}"
        ref_counter += 1

        job = {
            "ref": ref,
            "title": title_en,
            "title_ro": title_ro,
            "company": company,
            "description": description,
            "city": city,
            "county": county,
            "positions": positions,
            "salary": salary,
        }

        jobs_by_sector.setdefault(sector_en, []).append(job)
        total_jobs += 1
        total_positions += positions

    # Sort each sector by positions descending, limit to top 50
    for sector in jobs_by_sector:
        jobs_by_sector[sector].sort(key=lambda x: -x["positions"])
        jobs_by_sector[sector] = jobs_by_sector[sector][:50]

    print(f"  Parsed: {total_jobs} jobs, {total_positions} positions in {len(jobs_by_sector)} sectors")
    return jobs_by_sector, total_jobs, total_positions


def format_salary_str(sal_min, sal_max, sal_raw):
    """Format salary as clean string."""
    try:
        lo = float(sal_min) if sal_min else 0
        hi = float(sal_max) if sal_max else 0
    except (ValueError, TypeError):
        lo, hi = 0, 0
    if lo > 0 and hi > 0:
        return f"{int(lo)} - {int(hi)} RON"
    if lo > 0:
        return f"{int(lo)} RON"
    if hi > 0:
        return f"{int(hi)} RON"
    return ""


def _lbl(key, lang):
    """Get pre-translated label for a key and language."""
    return LABEL.get(key, {}).get(lang, LABEL.get(key, {}).get("en", key))


def _safe(text):
    """Clean text for PDF output."""
    if not text:
        return ""
    return text.replace("\t", " ").replace("\r", "").replace("\n", " ")


def _add_apply_button(pdf, font_name, lang, apply_url):
    """Draw a green APPLY NOW button centered on page."""
    btn_text = _lbl("apply_now", lang)
    btn_w, btn_h = 80, 14
    btn_x = (210 - btn_w) / 2
    btn_y = pdf.get_y()
    pdf.set_fill_color(0, 153, 51)
    pdf.rect(btn_x, btn_y, btn_w, btn_h, "F")
    pdf.set_font(font_name, "", 14)
    pdf.set_text_color(255, 255, 255)
    pdf.set_xy(btn_x, btn_y + 2)
    pdf.cell(btn_w, btn_h - 2, btn_text, ln=False, align="C", link=apply_url)
    pdf.link(btn_x, btn_y, btn_w, btn_h, apply_url)
    pdf.set_y(btn_y + btn_h + 3)


def generate_pdf(lang, jobs_by_sector, total_jobs, total_positions, output_path):
    """Generate PDF following the factoryjobs.eu catalog format."""
    from fpdf import FPDF

    info = LANGUAGES[lang]
    strings = get_pdf_strings(lang)
    font_name = info["font"]
    font_path = FONT_FILES[font_name]
    apply_url = "https://interjob.ro/apply.html"
    wa_url = None  # Disabled

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)

    # Enable text shaping for complex scripts
    if lang != "en":
        try:
            pdf.set_text_shaping(True)
        except Exception:
            pass

    # Add fonts
    pdf.add_font(font_name, "", font_path)
    if font_name != "NotoSans":
        pdf.add_font("NotoSans", "", FONT_FILES["NotoSans"])
        pdf.set_fallback_fonts(["NotoSans"])

    # ── Page 1: Cover / Introduction ──
    pdf.add_page()

    # Title
    pdf.set_font(font_name, "", 22)
    pdf.set_text_color(6, 95, 70)
    pdf.multi_cell(0, 10, strings["title"], align="C")

    # Date + subtitle
    pdf.set_font(font_name, "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 7, strings["date"], ln=True, align="C")
    pdf.ln(2)

    # Divider
    pdf.set_draw_color(6, 95, 70)
    pdf.set_line_width(0.5)
    pdf.line(20, pdf.get_y(), 190, pdf.get_y())
    pdf.ln(6)

    # Intro
    pdf.set_font(font_name, "", 10)
    pdf.set_text_color(40, 40, 40)
    pdf.multi_cell(0, 5, _safe(strings["intro"]))
    pdf.ln(4)

    # Nationality notice box
    notice = strings.get("nationality_notice", "")
    if not notice:
        notice = translate_text("This form is open to all nationalities. Priority is given to candidates already present in Romania.", lang) if lang != "en" else "This form is open to all nationalities. Priority is given to candidates already present in Romania."
    pdf.set_fill_color(230, 245, 255)
    pdf.set_draw_color(6, 95, 70)
    y_before = pdf.get_y()
    pdf.rect(15, y_before, 180, 12, "DF")
    pdf.set_xy(20, y_before + 2)
    pdf.set_font(font_name, "", 9)
    pdf.set_text_color(6, 95, 70)
    pdf.multi_cell(170, 4, _safe(notice))
    pdf.set_y(y_before + 14)
    pdf.ln(4)

    # Stats
    pdf.set_font(font_name, "", 12)
    pdf.set_text_color(6, 95, 70)
    stats_text = strings["total_fmt"].format(jobs=total_jobs, positions=total_positions)
    pdf.cell(0, 8, stats_text, ln=True, align="C")
    pdf.ln(4)

    # APPLY NOW button (top)
    _add_apply_button(pdf, font_name, lang, apply_url)
    pdf.set_font(font_name, "", 9)
    pdf.set_text_color(80, 80, 80)
    cta_note = strings.get("apply_cta", "Click the button above to apply for these positions.")
    pdf.cell(0, 5, _safe(cta_note), ln=True, align="C")
    pdf.ln(6)

    # Contact info
    pdf.set_fill_color(240, 253, 244)
    pdf.rect(30, pdf.get_y(), 150, 40, "F")
    pdf.set_xy(30, pdf.get_y() + 5)
    pdf.set_font(font_name, "", 14)
    pdf.set_text_color(6, 95, 70)
    pdf.cell(150, 8, strings["contact_header"], ln=True, align="C")
    pdf.set_x(30)
    pdf.set_font(font_name, "", 10)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(150, 6, strings["contact_web"], ln=True, align="C")
    pdf.set_x(30)
    pdf.cell(150, 6, strings["contact_wa"], ln=True, align="C")
    pdf.set_x(30)
    pdf.cell(150, 6, strings["contact_email"], ln=True, align="C")

    # ── Sector Pages: Numbered Job Listings ──
    sorted_sectors = sorted(jobs_by_sector.items(), key=lambda x: -sum(j["positions"] for j in x[1]))
    global_job_num = 0

    lbl_company = _lbl("company", lang)
    lbl_location = _lbl("location", lang)
    lbl_salary = _lbl("salary", lang)
    lbl_positions = _lbl("positions", lang)
    lbl_desc = _lbl("description", lang)
    lbl_ref = _lbl("ref", lang)
    lbl_sector = _lbl("sector", lang)

    page_header = f"Internal Transfers EU - {strings['title']}"
    page_date = f"Updated: {strings['date']}"

    for sector_en, jobs in sorted_sectors:
        sector_name = translate_text(sector_en, lang) if lang != "en" else sector_en
        sector_positions = sum(j["positions"] for j in jobs)

        pdf.add_page()

        # Page header
        pdf.set_font(font_name, "", 9)
        pdf.set_text_color(80, 80, 80)
        pdf.cell(0, 5, page_header, ln=True, align="C")
        pdf.cell(0, 4, page_date, ln=True, align="C")
        pdf.ln(3)

        # Sector header
        pdf.set_font(font_name, "", 16)
        pdf.set_text_color(6, 95, 70)
        pdf.cell(0, 10, f"{lbl_sector}: {sector_name}", ln=True, align="L")

        pdf.set_font(font_name, "", 9)
        pdf.set_text_color(100, 100, 100)
        subtitle = strings["sector_fmt"].format(count=len(jobs), positions=sector_positions)
        pdf.cell(0, 6, subtitle, ln=True, align="L")

        # Divider
        pdf.set_draw_color(6, 95, 70)
        pdf.set_line_width(0.4)
        pdf.line(10, pdf.get_y(), 200, pdf.get_y())
        pdf.ln(4)

        # APPLY button for this sector
        _add_apply_button(pdf, font_name, lang, apply_url)
        pdf.ln(3)

        # Job listings (same format as factoryjobs catalog)
        for job in jobs:
            global_job_num += 1

            # Check page break — need ~35mm for a job entry
            if pdf.get_y() > 240:
                pdf.add_page()
                pdf.set_font(font_name, "", 9)
                pdf.set_text_color(80, 80, 80)
                pdf.cell(0, 5, page_header, ln=True, align="C")
                pdf.cell(0, 4, page_date, ln=True, align="C")
                pdf.ln(3)

            # Reference number (light grey)
            pdf.set_font(font_name, "", 8)
            pdf.set_text_color(150, 150, 150)
            pdf.cell(0, 4, job["ref"], ln=True)

            # Job title (bold, blue-green)
            job_title = job["title"]
            if lang != "en":
                job_title = translate_text(job["title"], lang)
            pdf.set_font(font_name, "", 11)
            pdf.set_text_color(6, 95, 70)
            pdf.cell(0, 6, _safe(job_title), ln=True)

            # Details lines
            pdf.set_font(font_name, "", 8)
            pdf.set_text_color(60, 60, 60)

            # Company
            pdf.cell(0, 4, f"  {lbl_company}: {_safe(job['company'])}", ln=True)

            # Location
            loc = f"{job['city']}, {job['county']}" if job.get("county") and job["county"] != job["city"] else job["city"]
            if loc:
                pdf.cell(0, 4, f"  {lbl_location}: {_safe(loc)}", ln=True)

            # Salary
            if job["salary"]:
                pdf.cell(0, 4, f"  {lbl_salary}: {_safe(job['salary'])}", ln=True)
            else:
                not_spec = strings.get("not_specified", "Not specified in government data")
                pdf.cell(0, 4, f"  {lbl_salary}: {_safe(not_spec)}", ln=True)

            # Positions
            if job["positions"] and str(job["positions"]) not in ("", "0"):
                pdf.cell(0, 4, f"  {lbl_positions}: {job['positions']}", ln=True)

            # Sector
            pdf.cell(0, 4, f"  {lbl_sector}: {_safe(sector_name)}", ln=True)

            # Description
            desc = job.get("description", DEFAULT_DESCRIPTION)
            if desc and len(desc) > 5:
                if lang != "en":
                    desc = translate_text(desc, lang)
                pdf.set_font(font_name, "", 7)
                pdf.multi_cell(0, 3.5, f"  {lbl_desc}: {_safe(desc[:200])}")

            # APPLY link for this job
            pdf.set_font(font_name, "", 8)
            pdf.set_text_color(0, 153, 51)
            apply_text = _lbl("apply_now", lang)
            job_apply_url = f"{apply_url}?ref={job['ref']}"
            pdf.cell(0, 5, apply_text, ln=True, link=job_apply_url)

            # Divider
            pdf.ln(1)
            pdf.set_draw_color(220, 220, 220)
            pdf.set_line_width(0.1)
            pdf.line(20, pdf.get_y(), 190, pdf.get_y())
            pdf.ln(2)

        # Sector bottom CTA
        pdf.ln(3)
        _add_apply_button(pdf, font_name, lang, apply_url)
        pdf.ln(2)

    # ── Final CTA Page ──
    pdf.add_page()
    pdf.ln(30)

    pdf.set_font(font_name, "", 24)
    pdf.set_text_color(6, 95, 70)
    pdf.cell(0, 15, strings["final_title"], ln=True, align="C")
    pdf.ln(10)

    pdf.set_font(font_name, "", 13)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 8, _safe(strings["final_text"]), align="C")
    pdf.ln(10)

    # Big APPLY button
    _add_apply_button(pdf, font_name, lang, apply_url)
    pdf.ln(8)

    # Contact details
    pdf.set_font(font_name, "", 14)
    pdf.set_text_color(6, 95, 70)
    pdf.cell(0, 10, "interjob.ro/apply.html", ln=True, align="C", link=apply_url)
    pdf.set_font(font_name, "", 12)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 8, "Email: office@interjob.ro", ln=True, align="C")

    # Footer info
    pdf.ln(10)
    pdf.set_font(font_name, "", 7)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 4, "Data source: ANOFM (National Employment Agency of Romania)", ln=True, align="C")

    # Page footers
    footer_text = strings["page_footer"]
    for i in range(1, pdf.pages_count + 1):
        pdf.page = i
        pdf.set_y(-12)
        pdf.set_font("NotoSans" if font_name != "NotoSans" else font_name, "", 7)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(95, 4, f"Page {i} of {pdf.pages_count} | internaltransfers.eu", align="L")
        pdf.cell(95, 4, f"{total_jobs} jobs available", align="R")

    # Save
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    pdf.output(output_path)
    size_kb = os.path.getsize(output_path) / 1024
    print(f"    Generated: {output_path} ({size_kb:.0f} KB)")


def generate_all_pdfs(jobs_by_sector, total_jobs, total_positions, target_langs, output_dir):
    """Generate PDFs for all target languages."""
    pdf_dir = os.path.join(output_dir, "pdf")
    os.makedirs(pdf_dir, exist_ok=True)

    for lang in target_langs:
        print(f"\n  [{lang.upper()}] Generating {LANGUAGES[lang]['name']} PDF...")
        filename = f"jobs-romania-{TODAY}-{lang}.pdf"
        output_path = os.path.join(pdf_dir, filename)
        generate_pdf(lang, jobs_by_sector, total_jobs, total_positions, output_path)

    return pdf_dir


# =============================================================================
# DEPLOYMENT
# =============================================================================

def deploy_html(output_dir, target_langs):
    """Deploy translated HTML pages to A2 Hosting."""
    print("\n=== Deploying HTML pages ===")

    for lang in target_langs:
        info = LANGUAGES[lang]
        if lang == "en":
            # Update English pages in place (with lang switcher + hreflang)
            lang_dir = output_dir
            remote_base = DOCROOT
        else:
            lang_dir = os.path.join(output_dir, lang)
            remote_base = f"{DOCROOT}/{lang}"
            cpanel_mkdir(remote_base)

        for page in PAGES:
            local_path = os.path.join(lang_dir, page)
            if not os.path.exists(local_path):
                continue
            with open(local_path, "r", encoding="utf-8") as f:
                content = f.read()
            remote_path = f"{remote_base}/{page}"
            try:
                ok = cpanel_upload(remote_path, content)
                status = "OK" if ok else "FAIL"
            except Exception as e:
                status = f"ERROR: {e}"
            print(f"  [{lang.upper()}] {page}: {status}")


def deploy_pdfs(pdf_dir):
    """Deploy PDF files to A2 Hosting."""
    print("\n=== Deploying PDFs ===")
    remote_pdf_dir = f"{DOCROOT}/pdf"
    cpanel_mkdir(remote_pdf_dir)

    for filename in os.listdir(pdf_dir):
        if not filename.endswith(".pdf"):
            continue
        local_path = os.path.join(pdf_dir, filename)
        with open(local_path, "rb") as f:
            content = f.read()
        remote_path = f"{remote_pdf_dir}/{filename}"
        try:
            ok = cpanel_upload(remote_path, content, binary=True)
            status = "OK" if ok else "FAIL"
        except Exception as e:
            status = f"ERROR: {e}"
        size_kb = len(content) / 1024
        print(f"  {filename}: {status} ({size_kb:.0f} KB)")


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="internaltransfers.eu multilingual deploy")
    parser.add_argument("--html-only", action="store_true", help="Only translate + deploy HTML")
    parser.add_argument("--pdf-only", action="store_true", help="Only generate + deploy PDFs")
    parser.add_argument("--generate-only", action="store_true", help="Generate locally, don't deploy")
    parser.add_argument("--lang", help="Process single language (e.g., ne, ur, si, ps)")
    args = parser.parse_args()

    do_html = not args.pdf_only
    do_pdf = not args.html_only
    do_deploy = not args.generate_only

    # Target languages
    if args.lang:
        if args.lang not in LANGUAGES:
            print(f"Unknown language: {args.lang}. Available: {', '.join(LANGUAGES.keys())}")
            return
        target_langs = ["en", args.lang] if args.lang != "en" else ["en"]
    else:
        target_langs = list(LANGUAGES.keys())

    print("=" * 70)
    print(f"INTERNALTRANSFERS.EU — Multilingual Deploy")
    print(f"Languages: {', '.join(target_langs)}")
    print(f"HTML: {'YES' if do_html else 'NO'} | PDF: {'YES' if do_pdf else 'NO'} | Deploy: {'YES' if do_deploy else 'NO'}")
    print("=" * 70)

    # Load translation cache from previous runs
    _load_cache()

    # Ensure output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # HTML
    if do_html:
        print("\n=== Fetching HTML pages ===")
        pages_dict = fetch_html_pages()
        if pages_dict:
            print(f"\n=== Translating to {len(target_langs)} languages ===")
            process_all_html(pages_dict, target_langs, OUTPUT_DIR)
            if do_deploy:
                deploy_html(OUTPUT_DIR, target_langs)
        else:
            print("  No pages fetched — skipping HTML")

    # PDF
    if do_pdf:
        print("\n=== Generating ANOFM Jobs PDFs ===")
        csv_text = fetch_anofm_csv()
        jobs_by_sector, total_jobs, total_positions = parse_anofm_jobs(csv_text)
        pdf_dir = generate_all_pdfs(jobs_by_sector, total_jobs, total_positions, target_langs, OUTPUT_DIR)
        if do_deploy:
            deploy_pdfs(pdf_dir)

    # Save translation cache for future runs
    _save_cache()

    print("\n" + "=" * 70)
    print("Done.")


if __name__ == "__main__":
    main()
