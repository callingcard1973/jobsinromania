#!/usr/bin/env python3
"""Generate factoryjobs.eu candidate catalog locally for preview."""

import csv
import re
from datetime import datetime
from pathlib import Path

MASTER_CSV = Path(__file__).parent / "candidates_master_final.csv"
OUT_DIR = Path(__file__).parent / "factoryjobs_preview"
FACTORY_ROLES = {"factory", "packaging", "logistics", "warehouse", "machinery", "assembly", "production"}
SITE_LABEL = "FactoryJobs EU"
APPLY_URL = "https://interjob.ro/apply.html"

SOURCE_LABELS = {
    "fw_candidates_db": "FarmWorkers DB",
    "interjob.ro": "InterJob.ro",
    "farmworkers.eu": "FarmWorkers.eu",
    "buildjobs.eu": "BuildJobs.eu",
    "horecaworkers2026.eu": "HorecaWorkers",
    "careworkers.eu": "CareWorkers.eu",
    "warehouseworkers.eu": "WarehouseWorkers.eu",
    "meatworkers.eu": "MeatWorkers.eu",
    "mechanicjobs.eu": "MechanicJobs.eu",
    "de_villiers": "De Villiers Agency",
}

EXP_LABELS = {
    "exp:0-1": "Under 1 year",
    "exp:1-3": "1–3 years",
    "exp:3-5": "3–5 years",
    "exp:5-10": "5–10 years",
    "exp:10+": "10+ years",
}

LANG_LEVELS = ["A1", "A2", "B1", "B2", "C1", "C2", "Native", "Fluent", "Basic", "Intermediate", "Advanced"]

CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
       background: #f0f2f5; color: #222; line-height: 1.6; font-size: 15px; }
.navbar { background: #fff; border-bottom: 1px solid #e0e4ea; padding: 14px 28px;
          display: flex; align-items: center; justify-content: space-between; }
.navbar img { height: 44px; }
.navbar a { font-size: 13px; color: #0f2942; text-decoration: none; font-weight: 600; }
.navbar a:hover { color: #f5a000; }
.wrap { max-width: 860px; margin: 0 auto; padding: 28px 20px; }

.hdr { background: #0f2942; color: #fff; padding: 28px 36px 32px; border-radius: 10px;
       margin-bottom: 20px; position: relative; }
.hdr .ref-tag { display: inline-block; background: rgba(245,160,0,.15); color: #f5a000;
                font-family: "SF Mono", Consolas, Monaco, monospace; font-size: 12px;
                font-weight: 700; padding: 4px 10px; border-radius: 4px;
                letter-spacing: .5px; margin-bottom: 14px; }
.hdr h1 { font-size: 28px; font-weight: 700; margin-bottom: 6px; letter-spacing: -.3px; }
.hdr .role { font-size: 13px; color: #f5a000; text-transform: uppercase;
             letter-spacing: 1px; font-weight: 700; }

.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px; }
.card { background: #fff; padding: 22px 24px; border-radius: 8px;
        box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.card h2 { font-size: 11px; font-weight: 700; color: #999; text-transform: uppercase;
           letter-spacing: .9px; margin-bottom: 14px; }
.field { margin-bottom: 10px; }
.field label { display: block; font-size: 11px; color: #aaa; margin-bottom: 2px; }
.field span { font-weight: 600; color: #111; }

.badge { display: inline-block; background: #fff3e0; color: #c77000;
         padding: 4px 12px; border-radius: 4px; margin: 3px 4px 3px 0; font-size: 13px; font-weight: 600; }

.lang-row { display: flex; align-items: center; margin-bottom: 8px; }
.lang-name { width: 90px; font-size: 13px; color: #444; font-weight: 600; }
.lang-bar { display: flex; gap: 3px; }
.lang-dot { width: 10px; height: 10px; border-radius: 2px; background: #dde3ea; }
.lang-dot.on { background: #f5a000; }
.lang-level { font-size: 11px; color: #aaa; margin-left: 8px; }

.about { font-size: 14px; color: #444; line-height: 1.8; }
.source-tag { display: inline-block; font-size: 11px; background: #f0f2f5;
              color: #777; padding: 3px 10px; border-radius: 4px; }
.actions { display: flex; gap: 12px; margin-top: 20px; }
.btn { display: inline-block; padding: 12px 28px; border-radius: 6px;
       font-size: 14px; font-weight: 700; text-decoration: none; }
.btn-primary { background: #f5a000; color: #fff; }
.btn-primary:hover { background: #d98e00; }

.full { grid-column: 1 / -1; }
@media(max-width: 620px) { .grid2 { grid-template-columns: 1fr; } .hdr { padding: 24px; } }
"""

INDEX_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
       background: #f0f2f5; color: #222; display: flex; flex-direction: column; min-height: 100vh; }
.navbar { background: #fff; border-bottom: 1px solid #e0e4ea; padding: 24px 20px;
          display: flex; flex-direction: column; align-items: center; gap: 14px; text-align: center; }
.navbar img { height: 280px; }
.navbar-text h1 { font-size: 24px; font-weight: 800; color: #0f2942; letter-spacing: -.3px; }
.navbar-text h1 span { color: #f5a000; }
.navbar-text p { font-size: 13px; color: #666; margin-top: 4px; max-width: 640px; }
.catbar { background: #0f2942; padding: 0 20px; display: flex; gap: 0;
          justify-content: center; flex-wrap: wrap; }
.catbar button { background: none; border: none; color: rgba(255,255,255,.6);
                 padding: 14px 24px; font-size: 14px; font-weight: 600; cursor: pointer;
                 border-bottom: 3px solid transparent; transition: all .15s; }
.catbar button:hover { color: #fff; }
.catbar button.active { color: #f5a000; border-bottom-color: #f5a000; }
.content { max-width: 1160px; margin: 0 auto; padding: 28px 20px; flex: 1; width: 100%; }
table { width: 100%; border-collapse: collapse; background: #fff;
        border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
th { background: #0f2942; color: #fff; padding: 12px 16px; text-align: left;
     font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .6px; }
td { padding: 12px 16px; border-bottom: 1px solid #eef0f3; font-size: 14px; }
tr:last-child td { border-bottom: none; }
tr:hover td { background: #f7f9fc; }
tr.hidden { display: none; }
a { color: #0f2942; text-decoration: none; font-weight: 600; }
a:hover { color: #f5a000; }
.role-badge { display: inline-block; background: #fff3e0; color: #c77000;
              padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
td.ref { font-family: "SF Mono", Consolas, Monaco, monospace; font-size: 12px;
         color: #0f2942; font-weight: 700; letter-spacing: .3px; white-space: nowrap; }
.count-info { font-size: 13px; color: #999; margin-bottom: 14px; text-align: center; }
footer { background: #0f2942; color: rgba(255,255,255,.6); text-align: center;
         padding: 18px; font-size: 13px; margin-top: auto; }
footer strong { color: #f5a000; }
"""


def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def safe(name):
    return re.sub(r"[^a-z0-9]+", "_", (name or "unknown").lower()).strip("_")[:60]


def parse_skills(raw):
    """Split skills string, separate exp:X-Y tag from actual skills."""
    if not raw:
        return None, []
    parts = [s.strip() for s in raw.split(",") if s.strip()]
    exp = None
    skills = []
    for p in parts:
        if p.startswith("exp:"):
            exp = EXP_LABELS.get(p, p.replace("exp:", "").replace("-", "–") + " yrs")
        else:
            skills.append(p)
    return exp, skills


def parse_languages(raw):
    """Return list of (language_name, level_str) tuples."""
    if not raw:
        return []
    result = []
    for part in re.split(r"[,;]+", raw):
        part = part.strip()
        if not part:
            continue
        level = None
        for lv in LANG_LEVELS:
            if lv.lower() in part.lower():
                level = lv
                part = re.sub(re.escape(lv), "", part, flags=re.IGNORECASE).strip(" :-")
                break
        name = part.strip(" :-") or "Unknown"
        result.append((name, level))
    return result


def level_bar(level):
    """Convert level string to 5-dot bar."""
    mapping = {
        "a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 5,
        "basic": 1, "intermediate": 3, "advanced": 4, "fluent": 5, "native": 5,
    }
    filled = mapping.get((level or "").lower(), 3)
    dots = "".join(
        f'<span class="lang-dot{"  on" if i <= filled else ""}"></span>'
        for i in range(1, 6)
    )
    return f'<div class="lang-bar">{dots}</div><span class="lang-level">{esc(level or "")}</span>'


def candidate_page(c, ref=""):
    exp, skills = parse_skills(c.get("skills"))
    langs = parse_languages(c.get("languages"))
    source_label = SOURCE_LABELS.get(c.get("source", ""), c.get("source", ""))

    # Profile card fields
    profile_fields = ""
    if c.get("country"):
        profile_fields += f'<div class="field"><label>Country</label><span>{esc(c["country"])}</span></div>'
    if c.get("location"):
        profile_fields += f'<div class="field"><label>Location</label><span>{esc(c["location"])}</span></div>'
    if c.get("role"):
        profile_fields += f'<div class="field"><label>Role</label><span>{esc(c["role"].title())}</span></div>'
    if exp:
        profile_fields += f'<div class="field"><label>Experience</label><span>{esc(exp)}</span></div>'

    # Contact card — no personal data shown to clients
    contact_fields = ""
    if source_label:
        contact_fields += f'<div class="field"><label>Source</label><span class="source-tag">{esc(source_label)}</span></div>'

    # Skills
    skills_html = ""
    if skills:
        badges = "".join(f'<span class="badge">{esc(s)}</span>' for s in skills)
        skills_html = f'<div class="card full"><h2>Skills</h2>{badges}</div>'

    # Languages
    langs_html = ""
    if langs:
        rows = "".join(
            f'<div class="lang-row"><span class="lang-name">{esc(name)}</span>{level_bar(level)}</div>'
            for name, level in langs
        )
        langs_html = f'<div class="card"><h2>Languages</h2>{rows}</div>'

    # About
    msg = c.get("message", "")
    about_html = ""
    if msg:
        truncated = msg[:800] + ("…" if len(msg) > 800 else "")
        about_html = f'<div class="card full"><h2>About</h2><p class="about">{esc(truncated)}</p></div>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(c['name'])} — {SITE_LABEL}</title>
  <style>{CSS}</style>
</head>
<body>
<div class="navbar">
  <img src="logo.png" alt="FactoryJobs EU">
  <a href="index.html">Back to Catalog</a>
</div>
<div class="wrap">
  <div class="hdr">
    <div class="ref-tag">Reference: {esc(ref)}</div>
    <h1>{esc(c['name'])}</h1>
    <div class="role">{esc(c.get('role','').title())} Candidate</div>
  </div>

  <div class="grid2">
    <div class="card">
      <h2>Profile</h2>
      {profile_fields or '<span style="color:#ccc">No data</span>'}
    </div>
    <div class="card">
      <h2>Contact</h2>
      {contact_fields or '<span style="color:#ccc">No data</span>'}
    </div>
    {langs_html}
    {skills_html}
    {about_html}
  </div>

  <div class="actions">
    <a class="btn btn-primary" href="{APPLY_URL}">Request Introduction</a>
  </div>
</div>
</body>
</html>"""


CATEGORY_MAP = {
    "packaging": "Packaging",
    "machinery": "Machinery",
    "logistics": "Logistics",
    "warehouse": "Warehouse",
    "factory": "Factory",
    "factory-worker": "Factory",
    "factory|agriculture": "Factory",
    "assembly": "Factory",
    "production": "Factory",
}
CATEGORIES = ["Packaging", "Machinery", "Logistics", "Warehouse", "Factory"]


def normalize_role(raw):
    return CATEGORY_MAP.get((raw or "").lower().strip(), None)


def ref_number(i):
    return f"FJ-2026-{i:04d}"


def index_page(candidates):
    rows = ""
    for i, c in enumerate(candidates, 1):
        slug = f"{i:03d}_{safe(c['name'])}.html"
        exp, _ = parse_skills(c.get("skills"))
        cat = normalize_role(c.get("role", "")) or "Other"
        ref = ref_number(i)
        rows += (f'<tr data-role="{esc(cat)}">'
                 f"<td class='ref'>{ref}</td>"
                 f"<td><a href='{slug}'>{esc(c['name'])}</a></td>"
                 f"<td><span class='role-badge'>{esc(cat)}</span></td>"
                 f"<td>{esc(c.get('country',''))}</td>"
                 f"<td>{esc(c.get('location',''))}</td>"
                 f"<td>{esc(exp or '—')}</td>"
                 f"<td>{esc(c.get('languages','') or '—')}</td>"
                 f"</tr>\n")

    cat_buttons = '<button class="active" onclick="filter(this,\'all\')">All</button>' + "".join(
        f'<button onclick="filter(this,\'{cat}\')">{cat}</button>'
        for cat in CATEGORIES
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Candidates — {SITE_LABEL}</title>
  <style>{INDEX_CSS}</style>
</head>
<body>
  <div class="navbar">
    <img src="logo.png" alt="FactoryJobs EU">
    <div class="navbar-text">
      <h1>FactoryJobs <span>EU</span> — Candidate Catalog</h1>
      <p>Skilled workers across Packaging, Machinery, Logistics, Warehouse, and Factory roles</p>
    </div>
  </div>
  <div class="catbar">
    {cat_buttons}
  </div>
  <div class="content">
    <p class="count-info" id="count-info">{len(candidates)} candidates</p>
    <table>
      <thead>
        <tr><th>Ref</th><th>Name</th><th>Role</th><th>Country</th><th>Location</th><th>Experience</th><th>Languages</th></tr>
      </thead>
      <tbody id="tbody">{rows}</tbody>
    </table>
  </div>
  <footer><strong>FactoryJobs EU</strong> &copy; 2026 — Employers Catalog</footer>
  <script>
    function filter(btn, cat) {{
      document.querySelectorAll('.catbar button').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const rows = document.querySelectorAll('#tbody tr');
      let visible = 0;
      rows.forEach(r => {{
        const show = cat === 'all' || r.dataset.role === cat;
        r.classList.toggle('hidden', !show);
        if (show) visible++;
      }});
      document.getElementById('count-info').textContent = visible + ' candidates';
    }}
  </script>
</body>
</html>"""


def main():
    OUT_DIR.mkdir(exist_ok=True)
    candidates = []
    seen = set()
    with open(MASTER_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("name") or "").strip()
            role = (row.get("role") or "").lower().strip()
            email = (row.get("email") or "").strip().lower()
            if not name or name.startswith("Unknown") or "@" in name:
                continue
            if not any(r in role for r in FACTORY_ROLES):
                continue
            if email and email in seen:
                continue
            if email:
                seen.add(email)
            candidates.append(row)

    for i, c in enumerate(candidates, 1):
        slug = f"{i:03d}_{safe(c['name'])}.html"
        (OUT_DIR / slug).write_text(candidate_page(c, ref_number(i)), encoding="utf-8")

    (OUT_DIR / "index.html").write_text(index_page(candidates), encoding="utf-8")
    print(f"Generated {len(candidates)} profiles + index.html in {OUT_DIR}/")
    print(f"Open: {OUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
