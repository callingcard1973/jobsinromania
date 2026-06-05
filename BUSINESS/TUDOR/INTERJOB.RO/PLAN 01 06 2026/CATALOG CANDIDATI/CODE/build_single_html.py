#!/usr/bin/env python3
"""Build a single self-contained HTML file with all 569 candidates as accordion."""

import base64
import csv
import json
import re
from datetime import datetime
from pathlib import Path

# Reuse logic from preview_catalog.py
from preview_catalog import (
    SOURCE_LABELS, EXP_LABELS, CATEGORY_MAP, CATEGORIES,
    ROLE_SKILLS, COUNTRY_LANGUAGES, STRENGTH_TEMPLATES,
    PHONE_PREFIX_COUNTRY, NATIONALITY_CODE, BAD_STATEMENT_MARKERS,
    FACTORY_ROLES,
    esc, safe, parse_skills, parse_languages, level_bar,
    fill_skills, fill_strengths, infer_languages, infer_country,
    normalize_role_for_fill, normalize_role, ref_number,
    text_paragraphs, is_bad_statement, load_enrichment,
)

ROOT = Path(__file__).parent.parent
MASTER_CSV = ROOT / "DATA" / "candidates_master_final.csv"
OUTPUT = ROOT / "factoryjobs_catalog.html"

OFFICE_EMAIL = "office@factoryjobs.eu"
PHONE_WA = "+33 7 51 17 13 56"


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
       background: #f0f2f5; color: #222; display: flex; flex-direction: column; min-height: 100vh;
       font-size: 15px; line-height: 1.6; }

.header-simple { background: #fff; border-bottom: 1px solid #e0e4ea;
                 padding: 28px 20px; text-align: center; }
.header-simple .logo { height: 100px; margin-bottom: 12px; }
.header-simple .header-title { font-size: 30px; font-weight: 800; color: #0f2942; letter-spacing: -.5px; }
.header-simple .header-sub { font-size: 14px; color: #666; margin-top: 5px; }
.header-simple .header-email { margin-top: 8px; font-size: 13px; }
.header-simple .header-email a { color: #f5a000; font-weight: 700; text-decoration: none; }

.catbar { background: #0f2942; padding: 0 20px; display: flex; gap: 0;
          justify-content: center; flex-wrap: wrap; position: sticky; top: 0; z-index: 10; }
.catbar button { background: none; border: none; color: rgba(255,255,255,.6);
                 padding: 14px 24px; font-size: 14px; font-weight: 600; cursor: pointer;
                 border-bottom: 3px solid transparent; transition: all .15s; }
.catbar button:hover { color: #fff; }
.catbar button.active { color: #f5a000; border-bottom-color: #f5a000; }

.controls { background: #fff; padding: 16px 20px; border-bottom: 1px solid #e0e4ea;
            display: flex; gap: 16px; align-items: center; justify-content: center; flex-wrap: wrap; }
.controls input { padding: 10px 16px; border: 1px solid #d0d6dd; border-radius: 6px;
                  font-size: 14px; width: 320px; max-width: 100%; }
.controls input:focus { outline: none; border-color: #f5a000; }
.count-info { font-size: 13px; color: #888; font-weight: 600; }
.count-info span { color: #0f2942; font-size: 16px; }

.content { max-width: 1160px; margin: 0 auto; padding: 24px 16px; flex: 1; width: 100%; }

.summary-table { width: 100%; border-collapse: collapse; background: #fff;
                 border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08);
                 margin-bottom: 28px; }
.summary-table th { background: #0f2942; color: #fff; padding: 12px 14px; text-align: left;
                    font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
.summary-table td { padding: 10px 14px; border-bottom: 1px solid #eef0f3; font-size: 13px; }
.summary-table tr:last-child td { border-bottom: none; }
.summary-table tr:hover td { background: #f7f9fc; cursor: pointer; }
.summary-table tr.hidden { display: none; }
.summary-table td.ref { font-family: "SF Mono", Consolas, Monaco, monospace; font-size: 11px;
                        color: #c77000; font-weight: 700; white-space: nowrap; }
.summary-table td a { color: #0f2942; text-decoration: none; font-weight: 600; }
.summary-table td a:hover { color: #f5a000; }
.summary-table .role-pill { display: inline-block; background: #fff3e0; color: #c77000;
                            padding: 2px 8px; border-radius: 3px; font-size: 11px; font-weight: 600; }
.section-title { font-size: 13px; font-weight: 700; color: #888; text-transform: uppercase;
                 letter-spacing: 1px; margin: 28px 0 12px; }

.candidate { background: #fff; margin-bottom: 10px; border-radius: 8px;
             box-shadow: 0 1px 3px rgba(0,0,0,.06); overflow: hidden; }
.candidate.hidden { display: none; }

.cand-head { padding: 16px 22px; cursor: pointer; display: flex; align-items: center;
             gap: 16px; user-select: none; transition: background .15s; }
.cand-head:hover { background: #f7f9fc; }
.cand-head.open { background: #f7f9fc; border-bottom: 1px solid #e8edf3; }
.cand-ref { font-family: "SF Mono", Consolas, Monaco, monospace; font-size: 11px;
            color: #c77000; background: #fff3e0; padding: 4px 8px; border-radius: 4px;
            font-weight: 700; letter-spacing: .3px; white-space: nowrap; }
.cand-name { font-size: 16px; font-weight: 700; color: #0f2942; flex: 1; }
.cand-meta { font-size: 13px; color: #666; display: flex; gap: 14px; flex-wrap: wrap; }
.cand-role { display: inline-block; background: #fff3e0; color: #c77000;
             padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.cand-toggle { color: #888; font-size: 14px; font-weight: 700; transition: transform .2s; }
.cand-head.open .cand-toggle { transform: rotate(45deg); color: #f5a000; }

.cand-body { display: none; padding: 22px 24px 26px; }
.cand-body.open { display: block; }

.cand-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 16px; }
.cand-card { background: #f9fafc; padding: 16px 18px; border-radius: 6px; }
.cand-card h3 { font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase;
                letter-spacing: .9px; margin-bottom: 10px; }
.field { margin-bottom: 8px; font-size: 14px; }
.field label { display: block; font-size: 11px; color: #999; margin-bottom: 1px; }
.field span { font-weight: 600; color: #111; }

.badge { display: inline-block; background: #fff3e0; color: #c77000;
         padding: 4px 12px; border-radius: 4px; margin: 3px 4px 3px 0;
         font-size: 13px; font-weight: 600; }

.lang-row { display: flex; align-items: center; margin-bottom: 6px; font-size: 13px; }
.lang-name { width: 90px; font-weight: 600; color: #444; }
.lang-bar { display: flex; gap: 3px; }
.lang-dot { width: 9px; height: 9px; border-radius: 2px; background: #dde3ea; }
.lang-dot.on { background: #f5a000; }
.lang-level { font-size: 11px; color: #aaa; margin-left: 8px; }

ul.strengths { list-style: none; }
ul.strengths li { font-size: 14px; color: #333; padding: 6px 0 6px 22px;
                  position: relative; }
ul.strengths li:before { content: "✓"; position: absolute; left: 0; top: 6px;
                         color: #f5a000; font-weight: 700; }

.full { grid-column: 1 / -1; }
.statement { font-size: 14px; color: #333; line-height: 1.75; }
.statement p { margin-bottom: 10px; }

.btn { display: inline-block; background: #f5a000; color: #fff; padding: 11px 24px;
       border-radius: 6px; font-size: 14px; font-weight: 700; text-decoration: none;
       margin-top: 12px; }
.btn:hover { background: #d98e00; }

footer { background: #0f2942; color: rgba(255,255,255,.7); text-align: center;
         padding: 26px 20px; font-size: 13px; line-height: 1.8; margin-top: auto; }
footer strong { color: #f5a000; display: block; font-size: 15px; margin-bottom: 4px; }
footer .contact-line { color: #f5a000; font-weight: 600; margin-top: 8px; }
footer a { color: #f5a000; text-decoration: none; }

@media(max-width: 620px) {
  .cand-grid { grid-template-columns: 1fr; }
  .cand-head { flex-wrap: wrap; }
  .cand-meta { font-size: 12px; }
}
"""


def candidate_block(c, ref, enriched, cv_text, slug_id=""):
    exp, skills = parse_skills(c.get("skills"))
    langs = parse_languages(c.get("languages"))
    role_norm = normalize_role_for_fill(c, enriched)
    country = infer_country(c, enriched) or "Open to relocation"

    if not skills:
        skills = fill_skills(role_norm, [])
    if not langs:
        langs = infer_languages(country)
    strengths = fill_strengths(role_norm)

    # Statement
    full_message = ""
    if enriched and enriched.get("message"):
        full_message = enriched["message"]
    elif c.get("message"):
        full_message = c["message"]
    if not full_message or is_bad_statement(full_message):
        first_name = (c.get("name", "") or "").split()[0] or "The candidate"
        full_message = (
            f"{first_name} is a hardworking {role_norm} worker available for European employers. "
            f"Based in {country}, with practical experience in {role_norm} environments, "
            f"the candidate is comfortable with shift work, follows workplace safety protocols, "
            f"and adapts quickly to new teams and procedures. "
            f"Reliable, punctual and committed to long-term assignments, "
            f"open to relocation across Europe and ready to start on short notice."
        )

    # Profile fields
    profile_fields = f'<div class="field"><label>Country</label><span>{esc(country)}</span></div>'
    if c.get("location"):
        profile_fields += f'<div class="field"><label>Location</label><span>{esc(c["location"])}</span></div>'
    profile_fields += f'<div class="field"><label>Role</label><span>{esc(role_norm.title())}</span></div>'
    if exp:
        profile_fields += f'<div class="field"><label>Experience</label><span>{esc(exp)}</span></div>'

    # Additional info from master.json
    extras = []
    if enriched:
        if enriched.get("nationality") and enriched["nationality"] != "OTHER":
            nat = NATIONALITY_CODE.get(enriched["nationality"], enriched["nationality"])
            extras.append(("Nationality", nat))
        if enriched.get("available"):
            extras.append(("Available from", enriched["available"]))
        if enriched.get("driving"):
            extras.append(("Driving licence", enriched["driving"]))
        if enriched.get("gender"):
            extras.append(("Gender", enriched["gender"].capitalize()))
    extras_html = ""
    if extras:
        fields = "".join(
            f'<div class="field"><label>{esc(k)}</label><span>{esc(v)}</span></div>'
            for k, v in extras
        )
        extras_html = f'<div class="cand-card"><h3>Additional Info</h3>{fields}</div>'
    else:
        extras_html = f'<div class="cand-card"><h3>Source</h3><div class="field"><label>Origin</label><span>{esc(SOURCE_LABELS.get(c.get("source",""), c.get("source","")))}</span></div></div>'

    badges_html = "".join(f'<span class="badge">{esc(s)}</span>' for s in skills)
    langs_html = "".join(
        f'<div class="lang-row"><span class="lang-name">{esc(n)}</span>{level_bar(lv)}</div>'
        for n, lv in langs
    )
    strengths_html = "".join(f"<li>{esc(s)}</li>" for s in strengths)

    paras = text_paragraphs(full_message, max_chars=2500)
    statement_html = "".join(f"<p>{esc(p)}</p>" for p in paras)

    # Search keywords (lowercase) for JS filter
    search_blob = " ".join([
        c.get("name", ""), country, c.get("location", "") or "",
        role_norm, exp or "",
        ", ".join(s for s in skills),
        ", ".join(n for n, _ in langs),
    ]).lower()

    role_cat = normalize_role(c.get("role", "")) or "Other"

    return f"""<div class="candidate" id="{slug_id}" data-role="{esc(role_cat)}" data-search="{esc(search_blob)}">
  <div class="cand-head" onclick="toggle(this)">
    <span class="cand-ref">{ref}</span>
    <div style="flex:1;min-width:0">
      <div class="cand-name">{esc(c['name'])}</div>
      <div class="cand-meta">
        <span class="cand-role">{esc(role_cat)}</span>
        <span>{esc(country)}</span>
        {f'<span>{esc(c.get("location",""))}</span>' if c.get("location") else ""}
        {f'<span>{esc(exp)} exp</span>' if exp else ""}
      </div>
    </div>
    <span class="cand-toggle">+</span>
  </div>
  <div class="cand-body">
    <div class="cand-grid">
      <div class="cand-card"><h3>Profile</h3>{profile_fields}</div>
      {extras_html}
      <div class="cand-card"><h3>Languages</h3>{langs_html}</div>
      <div class="cand-card full"><h3>Skills</h3>{badges_html}</div>
      <div class="cand-card full"><h3>Key Strengths</h3><ul class="strengths">{strengths_html}</ul></div>
      <div class="cand-card full"><h3>Candidate Statement</h3><div class="statement">{statement_html}</div></div>
    </div>
    <a class="btn" href="mailto:{OFFICE_EMAIL}?subject=Request%20Contact%20Details%20-%20{esc(ref)}&body=Hello%2C%0A%0APlease%20send%20me%20full%20contact%20details%20and%20availability%20for%20candidate%20{esc(ref)}.%0A%0AThank%20you.">Request Contact Details</a>
  </div>
</div>"""


def main():
    by_email, cv_by_file = load_enrichment()
    print(f"Loaded {len(by_email)} master entries, {len(cv_by_file)} CV texts")

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

    # Build summary table + accordion blocks
    rows = []
    blocks = []
    for i, c in enumerate(candidates, 1):
        ref = ref_number(i)
        email = (c.get("email") or "").lower().strip()
        enriched = by_email.get(email)
        cv_file = enriched.get("cv_file") if enriched else ""
        cv_text = cv_by_file.get(cv_file) if cv_file else None

        # Pre-compute fields shared between table + accordion
        exp, _ = parse_skills(c.get("skills"))
        role_norm = normalize_role_for_fill(c, enriched)
        country = infer_country(c, enriched) or "Open to relocation"
        role_cat = normalize_role(c.get("role", "")) or "Other"
        langs = parse_languages(c.get("languages"))
        if not langs:
            langs = infer_languages(country)
        langs_short = ", ".join(n for n, _ in langs[:3]) or "—"

        slug_id = f"c{i:04d}"
        rows.append(
            f'<tr data-target="{slug_id}" data-role="{esc(role_cat)}" '
            f'data-search="{esc((c["name"] + " " + country + " " + (c.get("location","") or "") + " " + role_cat + " " + langs_short).lower())}" '
            f'onclick="jumpTo(\'{slug_id}\')">'
            f'<td class="ref">{ref}</td>'
            f'<td><a href="#{slug_id}">{esc(c["name"])}</a></td>'
            f'<td><span class="role-pill">{esc(role_cat)}</span></td>'
            f'<td>{esc(country)}</td>'
            f'<td>{esc(c.get("location","") or "—")}</td>'
            f'<td>{esc(exp or "—")}</td>'
            f'<td>{esc(langs_short)}</td>'
            f'</tr>'
        )
        blocks.append(candidate_block(c, ref, enriched, cv_text, slug_id))

    cat_buttons = '<button class="active" onclick="filter(this,\'all\')">All</button>' + "".join(
        f'<button onclick="filter(this,\'{cat}\')">{cat}</button>' for cat in CATEGORIES
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FactoryJobs EU — Candidate Catalog</title>
<style>{CSS}</style>
</head>
<body>

<div class="header-simple">
  <div class="header-title">factoryjobs.eu</div>
  <div class="header-sub">European Skilled Workers — Verified &amp; Ready</div>
  <div class="header-email"><a href="mailto:{OFFICE_EMAIL}">{OFFICE_EMAIL}</a></div>
</div>

<div class="catbar">{cat_buttons}</div>

<div class="controls">
  <input type="search" id="search" placeholder="Search by name, country, role, skill..." oninput="doSearch()">
  <div class="count-info"><span id="visible-count">{len(candidates)}</span> / {len(candidates)} candidates</div>
</div>

<div class="content">

<div class="section-title">Overview</div>
<table class="summary-table">
  <thead>
    <tr><th>Ref</th><th>Name</th><th>Role</th><th>Country</th><th>Location</th><th>Experience</th><th>Languages</th></tr>
  </thead>
  <tbody id="summary-tbody">
    {''.join(rows)}
  </tbody>
</table>

<div class="section-title">Candidate Profiles</div>
{''.join(blocks)}
</div>

<footer>
  <strong>FactoryJobs EU &copy; 2026</strong>
  Skilled Workers. Verified Profiles. Fast Deployment Across Europe.
  <div class="contact-line">
    <a href="mailto:{OFFICE_EMAIL}">{OFFICE_EMAIL}</a> &middot;
    Tel/WhatsApp: <a href="tel:+33751171356">{PHONE_WA}</a>
  </div>
</footer>

<script>
let activeCategory = 'all';
function toggle(head) {{
  const body = head.nextElementSibling;
  head.classList.toggle('open');
  body.classList.toggle('open');
}}
function filter(btn, cat) {{
  document.querySelectorAll('.catbar button').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  activeCategory = cat;
  applyFilters();
}}
function doSearch() {{
  applyFilters();
}}
function applyFilters() {{
  const q = document.getElementById('search').value.toLowerCase().trim();
  const cards = document.querySelectorAll('.candidate');
  const rows = document.querySelectorAll('#summary-tbody tr');
  let visible = 0;
  cards.forEach(c => {{
    const matchCat = activeCategory === 'all' || c.dataset.role === activeCategory;
    const matchSearch = !q || c.dataset.search.includes(q);
    const show = matchCat && matchSearch;
    c.classList.toggle('hidden', !show);
    if (show) visible++;
  }});
  rows.forEach(r => {{
    const matchCat = activeCategory === 'all' || r.dataset.role === activeCategory;
    const matchSearch = !q || r.dataset.search.includes(q);
    r.classList.toggle('hidden', !(matchCat && matchSearch));
  }});
  document.getElementById('visible-count').textContent = visible;
}}
function jumpTo(id) {{
  const el = document.getElementById(id);
  if (!el) return;
  el.scrollIntoView({{behavior: 'smooth', block: 'start'}});
  const head = el.querySelector('.cand-head');
  const body = el.querySelector('.cand-body');
  if (head && !head.classList.contains('open')) {{
    head.classList.add('open');
    body.classList.add('open');
  }}
}}
</script>

</body>
</html>"""

    OUTPUT.write_text(html, encoding="utf-8")
    size_mb = OUTPUT.stat().st_size / 1024 / 1024
    print(f"Generated: {OUTPUT}")
    print(f"Size: {size_mb:.2f} MB")
    print(f"Candidates: {len(candidates)}")


if __name__ == "__main__":
    main()
