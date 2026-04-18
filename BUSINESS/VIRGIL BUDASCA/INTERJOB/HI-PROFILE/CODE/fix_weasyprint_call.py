#!/usr/bin/env python3
"""Fix weasyprint call to use temp file instead of string= param."""
path = "/opt/ACTIVE/WORKFORCE/generate_all_catalogs.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

old = "WH(string=generate_pdf_html(site, workers)).write_pdf(pdf_path)"
new = (
    "pdf_html_path = pdf_path.replace('.pdf', '_for_pdf.html'); "
    "open(pdf_html_path, 'w', encoding='utf-8').write(generate_pdf_html(site, workers)); "
    "WH(filename=pdf_html_path).write_pdf(pdf_path)"
)

if old in content:
    content = content.replace(old, new)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Fixed weasyprint call")
else:
    print("Pattern not found — checking current call:")
    import re
    for m in re.finditer(r'WH\(.*?\)\.write_pdf', content):
        print(" ", m.group())
