#!/usr/bin/env python3
"""Add unicode sanitizer to generate_pdf_html in generate_all_catalogs.py"""
path = "/opt/ACTIVE/WORKFORCE/generate_all_catalogs.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

SANITIZE_FUNC = '''
def sanitize_text(text):
    """Replace non-ASCII special chars that break weasyprint font rendering."""
    replacements = {
        '\u25cf': '-', '\u2022': '-', '\u25e6': '-', '\u25aa': '-',
        '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
        '\u2013': '-', '\u2014': '-', '\u2026': '...',
        '\u25b6': '>', '\u25ba': '>', '\u2192': '->',
        '\u00b7': '-', '\u2715': 'x', '\u2713': 'ok',
        '\u00a0': ' ',
    }
    for ch, repl in replacements.items():
        text = text.replace(ch, repl)
    # Strip remaining non-latin1 chars that weasyprint can't handle
    return ''.join(c if ord(c) < 256 else '?' for c in text)

'''

if "def sanitize_text" not in content:
    content = content.replace("\ndef generate_pdf_html(", SANITIZE_FUNC + "\ndef generate_pdf_html(")

# Apply sanitize in generate_pdf_html — replace the text_clean line
old = (
    '            text_clean = mask_passport(mask_phone(cv["text"]))\n'
    '            safe_text = text_clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")\n'
)
new = (
    '            text_clean = sanitize_text(mask_passport(mask_phone(cv["text"])))\n'
    '            safe_text = text_clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")\n'
)

if 'sanitize_text(mask' not in content:
    content = content.replace(old, new)

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("Sanitizer added OK")
