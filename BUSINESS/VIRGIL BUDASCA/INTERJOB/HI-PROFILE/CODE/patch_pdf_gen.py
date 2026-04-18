#!/usr/bin/env python3
"""Patch generate_all_catalogs.py to use PDF-specific HTML (no JS, all sectors visible)."""
path = "/opt/ACTIVE/WORKFORCE/generate_all_catalogs.py"

PDF_CSS = """*{box-sizing:border-box;margin:0;padding:0}
body{background:#0f0f23;color:#e0e0e0;font-family:Segoe UI,sans-serif;padding:20px}
.c{max-width:1000px;margin:0 auto}
h1{color:#00d4ff;text-align:center;font-size:2em;margin-bottom:5px}
.sub{text-align:center;color:#888;margin-bottom:20px}
.sector-title{font-size:1.3em;font-weight:bold;margin:30px 0 10px 0;padding:8px 15px;border-radius:6px;color:#fff}
.cv{background:#16213e;border-radius:8px;padding:15px;margin:8px 0;border-left:4px solid #00d4ff}
.nm{font-weight:bold;color:#00d4ff;font-size:1.05em}
.ref{color:#888;font-size:.75em;font-weight:normal;margin-left:8px}
.body{color:#ccc;font-size:.85em;margin-top:8px;white-space:pre-line;line-height:1.5}
.contact{margin-top:8px;display:flex;gap:15px;flex-wrap:wrap}
.contact a{color:#00d4ff;font-size:.8em;text-decoration:none}
.stats{display:flex;gap:12px;justify-content:center;margin:15px 0;flex-wrap:wrap}
.st{background:#16213e;padding:10px 18px;border-radius:8px;text-align:center;min-width:100px}
.sn{font-size:1.5em;font-weight:bold;color:#00d4ff}
.sl{color:#888;font-size:.75em}
.cta{background:linear-gradient(135deg,#ff6b35,#ff4500);color:white;padding:18px;border-radius:10px;text-align:center;margin:40px 0}
.cta a{color:white;text-decoration:none;font-size:1.2em;font-weight:bold}
footer{text-align:center;color:#555;margin-top:20px;padding:20px;border-top:1px solid #222;font-size:.8em}"""

NEW_FUNC = r'''
def generate_pdf_html(site, workers):
    """PDF version: no tabs/JS, all sectors visible, all CV bodies expanded."""
    name = site["name"]
    email = site["email"]
    total = sum(len(v) for v in workers.values())
    n_sectors = len(workers)
    sectors_html = ""
    for sector, ws in workers.items():
        if not ws:
            continue
        color = SECTOR_COLORS.get(sector, "#607D8B")
        sectors_html += f'<div class="sector-title" style="background:{color}">{sector} ({len(ws)} candidati)</div>\n'
        prefix = sector[:4].upper()
        start = random.randint(56, 377)
        ref_nums = sorted(random.sample(range(start, start + 300), min(len(ws), 300)))
        for cv, rnum in zip(ws, ref_nums):
            ref = f"{prefix}-{rnum}"
            dname = display_name(cv["name"])
            safe_name = dname.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            text_clean = mask_passport(mask_phone(cv["text"]))
            safe_text = text_clean.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            name_enc = cv["name"].replace(" ", "%20")
            cv_link = f"mailto:{email}?subject=CV%20{ref}%20{name_enc}"
            avail_link = f"mailto:{email}?subject=Disponibilitate%20{ref}%20{name_enc}"
            sectors_html += (
                f'<div class="cv">'
                f'<div class="nm">{safe_name} <span class="ref">#{ref}</span></div>'
                f'<div class="body">{safe_text}</div>'
                f'<div class="contact">'
                f'<a href="{cv_link}">&#9993; CV la cerere</a>'
                f'<a href="{avail_link}" style="color:#ff6b35">&#10003; Verifica disponibilitate</a>'
                f'</div></div>\n'
            )
    return (
        "<!DOCTYPE html>\n<html lang='ro'><head>\n"
        "<meta charset='UTF-8'>\n"
        f"<title>Candidati Disponibili - {name}</title>\n"
        f"<style>{PDF_CSS}</style></head><body><div class='c'>\n"
        f"<h1>Candidati Disponibili</h1>\n"
        f"<p class='sub'>{name} &mdash; {total} CV-uri verificate</p>\n"
        f"<div class='stats'>"
        f"<div class='st'><div class='sn'>{total}</div><div class='sl'>CV-uri</div></div>"
        f"<div class='st'><div class='sn'>{n_sectors}</div><div class='sl'>Categorii</div></div>"
        f"</div>\n"
        f"{sectors_html}\n"
        f"<div class='cta'>"
        f"<a href='https://wa.me/33751171356'>WhatsApp: +33 7 51 17 13 56</a>"
        f"<small style='display:block;margin-top:6px;opacity:.8'>{email} | CV complete la cerere</small>"
        f"</div>\n"
        f"<footer>{name} | Nume afisat. CV complet disponibil la confirmare.</footer>\n"
        "</div></body></html>"
    )

'''

with open(path, encoding="utf-8") as f:
    content = f.read()

if "def generate_pdf_html" in content:
    print("Already patched")
else:
    content = content.replace("\ndef main():", NEW_FUNC + "\ndef main():")
    # Fix PDF generation lines to use generate_pdf_html
    content = content.replace(
        "WH(filename=html_path).write_pdf(pdf_path)",
        "WH(string=generate_pdf_html(site, workers)).write_pdf(pdf_path)"
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("Patched OK")
