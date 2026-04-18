#!/usr/bin/env python3
path = "/opt/ACTIVE/WORKFORCE/generate_all_catalogs.py"
with open(path, encoding="utf-8") as f:
    content = f.read()

if "PDF_CSS" in content:
    print("Already present")
else:
    pdf_css = (
        'PDF_CSS = ('
        '"*{box-sizing:border-box;margin:0;padding:0}"'
        '"body{background:#0f0f23;color:#e0e0e0;font-family:Segoe UI,sans-serif;padding:20px}"'
        '".c{max-width:1000px;margin:0 auto}"'
        '"h1{color:#00d4ff;text-align:center;font-size:2em;margin-bottom:5px}"'
        '".sub{text-align:center;color:#888;margin-bottom:20px}"'
        '".sector-title{font-size:1.3em;font-weight:bold;margin:30px 0 10px 0;padding:8px 15px;border-radius:6px;color:#fff}"'
        '".cv{background:#16213e;border-radius:8px;padding:15px;margin:8px 0;border-left:4px solid #00d4ff}"'
        '".nm{font-weight:bold;color:#00d4ff;font-size:1.05em}"'
        '".ref{color:#888;font-size:.75em;font-weight:normal;margin-left:8px}"'
        '".body{color:#ccc;font-size:.85em;margin-top:8px;white-space:pre-line;line-height:1.5}"'
        '".contact{margin-top:8px;display:flex;gap:15px;flex-wrap:wrap}"'
        '".contact a{color:#00d4ff;font-size:.8em;text-decoration:none}"'
        '".stats{display:flex;gap:12px;justify-content:center;margin:15px 0;flex-wrap:wrap}"'
        '".st{background:#16213e;padding:10px 18px;border-radius:8px;text-align:center;min-width:100px}"'
        '".sn{font-size:1.5em;font-weight:bold;color:#00d4ff}"'
        '".sl{color:#888;font-size:.75em}"'
        '".cta{background:linear-gradient(135deg,#ff6b35,#ff4500);color:white;padding:18px;border-radius:10px;text-align:center;margin:40px 0}"'
        '".cta a{color:white;text-decoration:none;font-size:1.2em;font-weight:bold}"'
        '"footer{text-align:center;color:#555;margin-top:20px;padding:20px;border-top:1px solid #222;font-size:.8em}"'
        ')\n\n'
    )
    content = content.replace("CSS = ", pdf_css + "CSS = ")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("PDF_CSS added OK")
