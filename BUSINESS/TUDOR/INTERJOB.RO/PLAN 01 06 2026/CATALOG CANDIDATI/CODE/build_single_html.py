#!/usr/bin/env python3
"""Build a single self-contained HTML catalog. Use --internal to include phone/email."""

import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path

# Reuse logic from preview_catalog.py
from preview_catalog import (
    SOURCE_LABELS,
    NATIONALITY_CODE,
    esc, parse_skills, parse_languages, level_bar,
    fill_skills, fill_strengths, infer_languages, infer_country,
    normalize_role_for_fill, ref_number,
    text_paragraphs, is_bad_statement, load_enrichment,
)

ROOT = Path(__file__).parent.parent
MASTER_CSV = ROOT / "DATA" / "candidates_master_final.csv"
OUTPUT_CLIENT = ROOT / "FOR CLIENTS" / "catalog_ocupatii_deficitare.html"
OUTPUT_INTERNAL = ROOT / "FOR FACTORYJOBS INTERNALLY" / "catalog_ocupatii_deficitare_intern.html"

OFFICE_EMAIL = "office@interjob.ro"
PHONE_WA = "+33 7 51 17 13 56"

# InterJob neutral branding — logo embedded as a data URI so the HTML stays
# self-contained (single file, works offline).
LOGO_PATH = Path(r"D:\MEMORY\BUSINESS\ACTIVE\INTERJOB.RO\branding\interjob-logo-rosu-pe-alb.jpg")


def logo_data_uri():
    import base64
    if LOGO_PATH.exists():
        b64 = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        return f"data:image/jpeg;base64,{b64}"
    return ""

INTERNAL = False  # set in main()

# Construction is detected by keyword across role+skills+message (not just the
# exact role "construction"), so trades logged as mason/welder/rebar/etc. on
# CVs are all surfaced under one tab. Matches the ~328 construction candidates.
CONSTRUCTION_KW = (
    "constr", "mason", "zid", "dulgher", "carpenter", "fierar", "weld", "sudor",
    "instalator", "plumb", "tiler", "faiant", "plaster", "tencu", "scaffold",
    "schela", "ouvrier", "bauarbeiter", "betonist", "rebar", "steel fix", "electric",
)

# One unified catalog for ALL trades. Order = how tabs appear (busiest first).
CATALOG_CATEGORIES = [
    "Construction", "Agriculture", "Care", "Hospitality", "Packaging",
    "Logistics", "Machinery", "Factory", "Warehouse", "Driver",
]

# role/skills keyword -> category, evaluated in order (first hit wins). Keep
# stems general and multi-language so CV variants all resolve.
ROLE_KEYWORDS = [
    ("farm", "Agriculture"), ("agri", "Agriculture"),
    ("nurs", "Care"), ("care", "Care"), ("health", "Care"), ("caregiv", "Care"),
    ("hospitality", "Hospitality"), ("chef", "Hospitality"), ("cook", "Hospitality"),
    ("waiter", "Hospitality"), ("horeca", "Hospitality"), ("restaurant", "Hospitality"),
    ("hotel", "Hospitality"), ("kitchen", "Hospitality"),
    ("packag", "Packaging"),
    ("logistic", "Logistics"),
    ("machin", "Machinery"), ("cnc", "Machinery"),
    ("warehouse", "Warehouse"), ("depozit", "Warehouse"),
    ("driver", "Driver"), ("driving", "Driver"), ("sofer", "Driver"),
    ("factory", "Factory"), ("production", "Factory"), ("assembly", "Factory"),
]


# ANOFM official deficit occupations (workinromania.gov.ro) — COR + multilingual
# keywords (CVs are international). Order = tab order. Used in --deficit mode.
DEFICIT_OCCUPATIONS = [
    ("Bucătar", "751101", ("bucatar", "bucătar", "cook", "chef", "cuisinier", "koch", "cocinero", "kitchen")),
    ("Electrician", "741301", ("electric", "elektr", "electricista", "électric")),
    ("Mecanic utilaje", "721201", ("mecanic", "mechanic", "machinery", "utilaje", "mechaniker", "fitter")),
    ("Șofer", "832203", ("sofer", "șofer", "driver", "chauffeur", "driving", "fahrer")),
    ("Sudor", "722106", ("sudor", "weld", "soudeur", "schweiss", "schweiß", "saldator")),
    ("Tâmplar", "752201", ("tamplar", "tâmplar", "carpenter", "dulgher", "menuisier", "schreiner", "joiner")),
    ("Zidar", "711201", ("zidar", "mason", "bricklay", "maurer", "macon", "maçon")),
]
DEFICIT_CATEGORIES = [name for name, _, _ in DEFICIT_OCCUPATIONS]
DEFICIT = False  # set in main() via --deficit


def deficit_occupation_of(c):
    blob = " ".join((
        c.get("role", "") or "", c.get("skills", "") or "", c.get("message", "") or "",
    )).lower()
    for name, _cor, kws in DEFICIT_OCCUPATIONS:
        if any(k in blob for k in kws):
            return name
    return None


def is_construction(c):
    blob = " ".join((
        c.get("role", "") or "", c.get("skills", "") or "", c.get("message", "") or "",
    )).lower()
    return any(k in blob for k in CONSTRUCTION_KW)


def category_of(c):
    """Category for a candidate, or None when no trade is identifiable.
    Cached on the candidate dict — it is consulted ~7x per render."""
    cached = c.get("_cat", False)
    if cached is not False:
        return cached
    c["_cat"] = cat = _classify(c)
    return cat


def _classify(c):
    if DEFICIT:
        return deficit_occupation_of(c)
    # Construction wins over everything so a welder logged as "production"
    # still lands under the Construction tab.
    if is_construction(c):
        return "Construction"
    role = (c.get("role", "") or "").lower()
    for kw, cat in ROLE_KEYWORDS:
        if kw in role:
            return cat
    # Role gave nothing (often "unknown"/blank): classify from skills + CV text.
    blob = " ".join((c.get("skills", "") or "", c.get("message", "") or "")).lower()
    for kw, cat in ROLE_KEYWORDS:
        if kw in blob:
            return cat
    return None


CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
       background: #f0f2f5; color: #222; display: flex; flex-direction: column; min-height: 100vh;
       font-size: 15px; line-height: 1.6; }

.header-simple { background: #fff; border-bottom: 1px solid #e0e4ea;
                 padding: 28px 20px; text-align: center; }
.header-simple .logo { height: 100px; margin-bottom: 12px; }
.header-simple .header-title { font-size: 30px; font-weight: 800; color: #2c2f36; letter-spacing: -.5px; }
.header-simple .header-sub { font-size: 14px; color: #666; margin-top: 5px; }
.header-simple .header-email { margin-top: 8px; font-size: 13px; }
.header-simple .header-email a { color: #9E2B2B; font-weight: 700; text-decoration: none; }

.catbar { background: #2c2f36; padding: 0 20px; display: flex; gap: 0;
          justify-content: center; flex-wrap: wrap; position: sticky; top: 0; z-index: 10; }
.catbar button { background: none; border: none; color: rgba(255,255,255,.6);
                 padding: 14px 24px; font-size: 14px; font-weight: 600; cursor: pointer;
                 border-bottom: 3px solid transparent; transition: all .15s; }
.catbar button:hover { color: #fff; }
.catbar button.active { color: #9E2B2B; border-bottom-color: #9E2B2B; }

.controls { background: #fff; padding: 16px 20px; border-bottom: 1px solid #e0e4ea;
            display: flex; gap: 16px; align-items: center; justify-content: center; flex-wrap: wrap; }
.controls input { padding: 10px 16px; border: 1px solid #d0d6dd; border-radius: 6px;
                  font-size: 14px; width: 320px; max-width: 100%; }
.controls input:focus { outline: none; border-color: #9E2B2B; }
.count-info { font-size: 13px; color: #888; font-weight: 600; }
.count-info span { color: #2c2f36; font-size: 16px; }

.content { max-width: 1160px; margin: 0 auto; padding: 24px 16px; flex: 1; width: 100%; }

/* shopping cart */
.cart-btn { background: #fff; border: 1.5px solid #9E2B2B; color: #9E2B2B; font-weight: 700;
            font-size: 12px; padding: 6px 12px; border-radius: 6px; cursor: pointer;
            white-space: nowrap; transition: all .15s; }
.cart-btn:hover { background: #f5e6e6; }
.cart-btn.added { background: #9E2B2B; color: #fff; }
.cart-btn.btn { display: inline-block; margin-top: 14px; padding: 11px 22px; font-size: 14px; }
.cart-bar { position: fixed; right: 20px; bottom: 20px; z-index: 50; background: #2c2f36;
            color: #fff; padding: 14px 18px; border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,.3);
            display: flex; align-items: center; gap: 14px; font-size: 14px; }
.cart-bar #cart-count { color: #ff9b9b; font-size: 18px; }
.cart-bar-btn { background: rgba(255,255,255,.12); color: #fff; border: none; padding: 9px 14px;
                border-radius: 7px; font-weight: 600; font-size: 13px; cursor: pointer; }
.cart-bar-btn.primary { background: #9E2B2B; }
.cart-bar-btn:hover { background: rgba(255,255,255,.25); }
.cart-bar-btn.primary:hover { background: #b83434; }
.cart-modal { position: fixed; inset: 0; z-index: 60; background: rgba(20,20,30,.55);
              display: flex; align-items: center; justify-content: center; padding: 20px; }
.cart-box { background: #fff; border-radius: 14px; max-width: 540px; width: 100%; max-height: 80vh;
            overflow-y: auto; padding: 28px 30px; box-shadow: 0 20px 60px rgba(0,0,0,.4); }
.cart-box h2 { font-size: 20px; color: #2c2f36; margin-bottom: 6px; }
.cart-hint { font-size: 13px; color: #666; margin-bottom: 16px; }
.cart-list { list-style: none; margin: 0 0 18px; padding: 0; }
.cart-list li { display: flex; justify-content: space-between; align-items: center;
                padding: 9px 12px; border: 1px solid #eef0f3; border-radius: 7px; margin-bottom: 6px;
                font-size: 13px; }
.cart-x { background: none; border: none; color: #9E2B2B; font-size: 15px; cursor: pointer; font-weight: 700; }
.cart-actions { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
.hidden { display: none !important; }

.intro { background: #fff; border-radius: 10px; padding: 30px 34px; margin-bottom: 26px;
         box-shadow: 0 1px 3px rgba(0,0,0,.08); border-top: 4px solid #9E2B2B; }
.intro h1 { font-size: 26px; color: #2c2f36; font-weight: 800; letter-spacing: -.4px; margin-bottom: 14px; }
.intro p { font-size: 15px; color: #444; margin-bottom: 12px; }
.intro .intro-how { font-size: 13px; color: #555; background: #faf5f5; border-radius: 6px;
                    padding: 12px 16px; margin-top: 8px; }
.intro code { background: #f5e6e6; color: #9E2B2B; padding: 1px 6px; border-radius: 4px;
              font-family: Consolas, monospace; font-size: 12px; }
.intro-table { border-collapse: collapse; margin: 8px 0 18px; min-width: 280px; }
.intro-table th { background: #2c2f36; color: #fff; text-align: left; padding: 8px 16px;
                  font-size: 11px; text-transform: uppercase; letter-spacing: .5px; }
.intro-table td { padding: 7px 16px; border-bottom: 1px solid #eef0f3; font-size: 14px; }
.intro-table td:last-child { font-weight: 700; color: #9E2B2B; text-align: right; }

.summary-table { width: 100%; border-collapse: collapse; background: #fff;
                 border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.08);
                 margin-bottom: 28px; }
.summary-table th { background: #2c2f36; color: #fff; padding: 12px 14px; text-align: left;
                    font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: .5px; }
.summary-table td { padding: 10px 14px; border-bottom: 1px solid #eef0f3; font-size: 13px; }
.summary-table tr:last-child td { border-bottom: none; }
.summary-table tr:hover td { background: #f7f9fc; cursor: pointer; }
.summary-table tr.hidden { display: none; }
.summary-table td.ref { font-family: "SF Mono", Consolas, Monaco, monospace; font-size: 11px;
                        color: #9E2B2B; font-weight: 700; white-space: nowrap; }
.summary-table td a { color: #2c2f36; text-decoration: none; font-weight: 600; }
.summary-table td a:hover { color: #9E2B2B; }
.summary-table .role-pill { display: inline-block; background: #f5e6e6; color: #9E2B2B;
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
            color: #9E2B2B; background: #f5e6e6; padding: 4px 8px; border-radius: 4px;
            font-weight: 700; letter-spacing: .3px; white-space: nowrap; }
.cand-name { font-size: 16px; font-weight: 700; color: #2c2f36; flex: 1; }
.cand-meta { font-size: 13px; color: #666; display: flex; gap: 14px; flex-wrap: wrap; }
.cand-role { display: inline-block; background: #f5e6e6; color: #9E2B2B;
             padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.cand-toggle { color: #888; font-size: 14px; font-weight: 700; transition: transform .2s; }
.cand-head.open .cand-toggle { transform: rotate(45deg); color: #9E2B2B; }

.cand-body { display: none; padding: 22px 24px 26px; }
.cand-body.open { display: block; }

.cand-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-bottom: 16px; }
.cand-card { background: #f9fafc; padding: 16px 18px; border-radius: 6px; }
.cand-card h3 { font-size: 11px; font-weight: 700; color: #888; text-transform: uppercase;
                letter-spacing: .9px; margin-bottom: 10px; }
.field { margin-bottom: 8px; font-size: 14px; }
.field label { display: block; font-size: 11px; color: #999; margin-bottom: 1px; }
.field span { font-weight: 600; color: #111; }

.badge { display: inline-block; background: #f5e6e6; color: #9E2B2B;
         padding: 4px 12px; border-radius: 4px; margin: 3px 4px 3px 0;
         font-size: 13px; font-weight: 600; }

.lang-row { display: flex; align-items: center; margin-bottom: 6px; font-size: 13px; }
.lang-name { width: 90px; font-weight: 600; color: #444; }
.lang-bar { display: flex; gap: 3px; }
.lang-dot { width: 9px; height: 9px; border-radius: 2px; background: #dde3ea; }
.lang-dot.on { background: #9E2B2B; }
.lang-level { font-size: 11px; color: #aaa; margin-left: 8px; }

ul.strengths { list-style: none; }
ul.strengths li { font-size: 14px; color: #333; padding: 6px 0 6px 22px;
                  position: relative; }
ul.strengths li:before { content: "✓"; position: absolute; left: 0; top: 6px;
                         color: #9E2B2B; font-weight: 700; }

.full { grid-column: 1 / -1; }
.statement { font-size: 14px; color: #333; line-height: 1.75; }
.statement p { margin-bottom: 10px; }

.btn { display: inline-block; background: #9E2B2B; color: #fff; padding: 11px 24px;
       border-radius: 6px; font-size: 14px; font-weight: 700; text-decoration: none;
       margin-top: 12px; }
.btn:hover { background: #d98e00; }

footer { background: #2c2f36; color: rgba(255,255,255,.7); text-align: center;
         padding: 26px 20px; font-size: 13px; line-height: 1.8; margin-top: auto; }
footer strong { color: #9E2B2B; display: block; font-size: 15px; margin-bottom: 4px; }
footer .contact-line { color: #9E2B2B; font-weight: 600; margin-top: 8px; }
footer a { color: #9E2B2B; text-decoration: none; }

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

    # Contact card (internal version only)
    contact_card = ""
    if INTERNAL:
        cf = ""
        email = c.get("email") or (enriched.get("email") if enriched else "")
        phone = c.get("phone") or (enriched.get("phone") if enriched else "")
        if email:
            cf += f'<div class="field"><label>Email</label><span><a href="mailto:{esc(email)}">{esc(email)}</a></span></div>'
        if phone:
            wa = re.sub(r"[^\d+]", "", phone)
            cf += f'<div class="field"><label>Phone</label><span><a href="tel:{esc(wa)}">{esc(phone)}</a></span></div>'
            cf += f'<div class="field"><label>WhatsApp</label><span><a href="https://wa.me/{esc(wa.lstrip("+"))}" target="_blank">Open chat</a></span></div>'
        if cf:
            contact_card = f'<div class="cand-card"><h3>Contact</h3>{cf}</div>'

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

    role_cat = category_of(c)

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
    <button type="button" class="cart-btn" data-ref="{esc(ref)}" data-name="{esc(c['name'])}" onclick="event.stopPropagation();toggleCart(this)">+ Coș</button>
    <span class="cand-toggle">+</span>
  </div>
  <div class="cand-body">
    <div class="cand-grid">
      <div class="cand-card"><h3>Profile</h3>{profile_fields}</div>
      {contact_card if INTERNAL else extras_html}
      {extras_html if (INTERNAL and contact_card) else ""}
      <div class="cand-card"><h3>Languages</h3>{langs_html}</div>
      <div class="cand-card full"><h3>Skills</h3>{badges_html}</div>
      <div class="cand-card full"><h3>Key Strengths</h3><ul class="strengths">{strengths_html}</ul></div>
      <div class="cand-card full"><h3>Candidate Statement</h3><div class="statement">{statement_html}</div></div>
    </div>
    {"" if INTERNAL else f'<button type="button" class="btn cart-btn" data-ref="{esc(ref)}" data-name="{esc(c["name"])}" onclick="toggleCart(this)">+ Adaugă în coș</button>'}
  </div>
</div>"""


def main():
    global INTERNAL
    parser = argparse.ArgumentParser()
    parser.add_argument("--internal", action="store_true",
                        help="Build internal version with phone/email/WhatsApp visible.")
    parser.add_argument("--all", action="store_true",
                        help="Build both client and internal versions.")
    parser.add_argument("--full", action="store_true",
                        help="Build the full all-trades catalog instead of the "
                             "default 7-occupation deficit catalog.")
    args = parser.parse_args()

    # Deficit catalog (7 ANOFM occupations) is the canonical default since
    # 2026-06-25. Pass --full for the legacy all-trades catalog.
    global DEFICIT, CATALOG_CATEGORIES
    out_client, out_internal = OUTPUT_CLIENT, OUTPUT_INTERNAL
    if not args.full:
        DEFICIT = True
        CATALOG_CATEGORIES = DEFICIT_CATEGORIES

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
            # Keep only candidates with an identifiable trade (None = no trade in
            # full mode / not one of the 7 deficit occupations in --deficit mode).
            if category_of(row) is None:
                continue
            if email and email in seen:
                continue
            if email:
                seen.add(email)
            candidates.append(row)

    # ref -> candidate, split by trust boundary so the auto-responder *cannot*
    # leak contacts: the public index (no email/phone) is what process_requests.py
    # loads; contacts live in a separate gated file for the human-release step only.
    funnel = ROOT / "FUNNEL"
    funnel.mkdir(exist_ok=True)
    public, contacts = {}, {}
    for i, c in enumerate(candidates, 1):
        ref = ref_number(i)
        public[ref] = {
            "name": c.get("name", ""), "occupation": category_of(c),
            "country": c.get("country", ""), "location": c.get("location", ""),
        }
        contacts[ref] = {"email": c.get("email", ""), "phone": c.get("phone", "")}
    (funnel / "catalog_index.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=1), encoding="utf-8")
    (funnel / "catalog_contacts.json").write_text(
        json.dumps(contacts, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(public)} public + {len(contacts)} gated-contact entries to {funnel}")

    def build_rows_blocks():
        rows, blocks = [], []
        for i, c in enumerate(candidates, 1):
            ref = ref_number(i)
            em = (c.get("email") or "").lower().strip()
            enriched = by_email.get(em)
            cv_file = enriched.get("cv_file") if enriched else ""
            cv_text = cv_by_file.get(cv_file) if cv_file else None

            exp, _ = parse_skills(c.get("skills"))
            normalize_role_for_fill(c, enriched)
            country = infer_country(c, enriched) or "Open to relocation"
            role_cat = category_of(c)
            langs = parse_languages(c.get("languages"))
            if not langs:
                langs = infer_languages(country)
            langs_short = ", ".join(n for n, _ in langs[:3]) or "—"

            slug_id = f"c{i:04d}"
            extra_cells = ""
            search_extra = ""
            if INTERNAL:
                phone = c.get("phone") or (enriched.get("phone") if enriched else "") or "—"
                email_disp = c.get("email") or (enriched.get("email") if enriched else "") or "—"
                extra_cells = (
                    f'<td>{esc(email_disp)}</td>'
                    f'<td>{esc(phone)}</td>'
                )
                search_extra = f' {email_disp} {phone}'
            rows.append(
                f'<tr data-target="{slug_id}" data-role="{esc(role_cat)}" '
                f'data-search="{esc((c["name"] + " " + country + " " + (c.get("location","") or "") + " " + role_cat + " " + langs_short + search_extra).lower())}" '
                f'onclick="jumpTo(\'{slug_id}\')">'
                f'<td class="ref">{ref}</td>'
                f'<td><a href="#{slug_id}">{esc(c["name"])}</a></td>'
                f'<td><span class="role-pill">{esc(role_cat)}</span></td>'
                f'<td>{esc(country)}</td>'
                f'<td>{esc(c.get("location","") or "—")}</td>'
                f'<td>{esc(exp or "—")}</td>'
                f'<td>{esc(langs_short)}</td>'
                f'{extra_cells}'
                f'</tr>'
            )
            blocks.append(candidate_block(c, ref, enriched, cv_text, slug_id))
        return rows, blocks

    def render(output_path):
        cat_buttons = '<button class="active" onclick="filter(this,\'all\')">All</button>' + "".join(
            f'<button onclick="filter(this,\'{cat}\')">{cat}</button>' for cat in CATALOG_CATEGORIES
        )
        rows, blocks = build_rows_blocks()
        title_tag = "INTERN — InterJob.ro" if INTERNAL else "InterJob.ro — Catalog Candidați"
        logo_uri = logo_data_uri()
        logo_img = f'<img class="logo" src="{logo_uri}" alt="InterJob.ro">' if logo_uri else ""
        n = len(candidates)
        sub_label = ("Ocupații deficitare ANOFM — 7 meserii"
                     if DEFICIT else "Catalog de candidați — toate domeniile")
        intro_lead = ("<strong>InterJob.ro</strong> — candidați pentru cele 7 ocupații deficitare "
                      "oficiale (ANOFM, WorkinRomania.gov.ro)."
                      if DEFICIT else
                      "<strong>InterJob.ro</strong> conectează angajatorii din România și Europa "
                      "cu candidați din toate domeniile — într-un singur catalog.")
        cat_counts = Counter(category_of(c) for c in candidates)
        intro_rows = "".join(
            f"<tr><td>{esc(cat)}</td><td>{cat_counts[cat]}</td></tr>"
            for cat in CATALOG_CATEGORIES if cat_counts.get(cat)
        )
        internal_banner = ('<div style="background:#c62828;color:#fff;text-align:center;padding:8px;'
                           'font-weight:700;letter-spacing:.5px;font-size:13px">'
                           'INTERNAL — Contains personal contact details · Do not share externally</div>'
                           ) if INTERNAL else ""
        extra_th = "<th>Email</th><th>Phone</th>" if INTERNAL else ""
        html = f"""<!DOCTYPE html>
<html lang="ro">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_tag}</title>
<style>{CSS}</style>
</head>
<body>
{internal_banner}
<div class="header-simple">
  {logo_img}
  <div class="header-title">InterJob.ro</div>
  <div class="header-sub">{sub_label}</div>
  <div class="header-email"><a href="mailto:{OFFICE_EMAIL}">{OFFICE_EMAIL}</a></div>
</div>

<div class="catbar">{cat_buttons}</div>

<div class="controls">
  <input type="search" id="search" placeholder="Caută după nume, țară, meserie, competență...">
  <div class="count-info"><span id="visible-count">{n}</span> / {n} candidați</div>
</div>

<div class="content">

<div class="intro">
  <p>{intro_lead}</p>
  <p>În acest catalog: <strong>{n} candidați</strong>. Filtrați pe ocupație sau
  căutați direct în pagină.</p>
  <table class="intro-table"><thead><tr><th>Ocupație</th><th>Candidați</th></tr></thead>
  <tbody>{intro_rows}</tbody></table>
  <p class="intro-how"><strong>Cum funcționează:</strong> notați referința candidatului
  (ex. <code>IJ-2026-0142</code>) → apăsați „Solicită date de contact" → vă trimitem CV-urile
  complete și organizăm interviuri. Datele de contact se transmit doar la cererea dumneavoastră.</p>
</div>

<div class="section-title">Overview</div>
<table class="summary-table">
  <thead>
    <tr><th>Ref</th><th>Name</th><th>Role</th><th>Country</th><th>Location</th><th>Experience</th><th>Languages</th>{extra_th}</tr>
  </thead>
  <tbody id="summary-tbody">
    {''.join(rows)}
  </tbody>
</table>

<div class="section-title">Candidate Profiles</div>
{''.join(blocks)}
</div>

<div id="cart-bar" class="cart-bar hidden">
  <span><strong id="cart-count">0</strong> candidați în coș</span>
  <button class="cart-bar-btn primary" onclick="openCart()">Vezi coșul & trimite cererea</button>
  <button class="cart-bar-btn" onclick="clearCart()">Golește</button>
</div>

<div id="cart-modal" class="cart-modal hidden" onclick="if(event.target===this)closeCart()">
  <div class="cart-box">
    <h2>Coșul tău — <span id="cart-count2">0</span> candidați</h2>
    <p class="cart-hint">Trimitem o singură cerere cu toți candidații selectați. Date de contact și disponibilitate.</p>
    <ul id="cart-list" class="cart-list"></ul>
    <div class="cart-actions">
      <a id="cart-send" class="btn" href="#" onclick="return sendRequest()">Trimite cererea prin email</a>
      <button class="cart-bar-btn" onclick="copyList()">Copiază lista</button>
      <button class="cart-bar-btn" onclick="closeCart()">Închide</button>
    </div>
  </div>
</div>

<footer>
  <strong>InterJob.ro &copy; 2026</strong>
  Conectăm oameni cu locuri de muncă.
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

/* ---- Shopping cart ---- */
let cart = JSON.parse(localStorage.getItem('ij_cart') || '{{}}');
function saveCart() {{ localStorage.setItem('ij_cart', JSON.stringify(cart)); }}
function toggleCart(btn) {{
  const ref = btn.dataset.ref, name = btn.dataset.name;
  if (cart[ref]) delete cart[ref]; else cart[ref] = name;
  saveCart(); refreshCart();
}}
function refreshCart() {{
  const keys = Object.keys(cart);
  document.querySelectorAll('.cart-btn').forEach(b => {{
    const inc = !!cart[b.dataset.ref];
    b.classList.toggle('added', inc);
    b.textContent = b.classList.contains('btn')
      ? (inc ? '✓ Adăugat în coș' : '+ Adaugă în coș')
      : (inc ? '✓ În coș' : '+ Coș');
  }});
  const cc = document.getElementById('cart-count');
  if (cc) cc.textContent = keys.length;
  const cc2 = document.getElementById('cart-count2');
  if (cc2) cc2.textContent = keys.length;
  document.getElementById('cart-bar').classList.toggle('hidden', keys.length === 0);
  const list = document.getElementById('cart-list');
  list.innerHTML = '';
  keys.forEach(r => {{
    const li = document.createElement('li');
    li.innerHTML = '<span>' + r + ' — ' + cart[r] + '</span>' +
      '<button class="cart-x" onclick="removeFromCart(\\'' + r + '\\')">✕</button>';
    list.appendChild(li);
  }});
}}
function removeFromCart(ref) {{ delete cart[ref]; saveCart(); refreshCart(); }}
function clearCart() {{ cart = {{}}; saveCart(); refreshCart(); closeCart(); }}
function openCart() {{ document.getElementById('cart-modal').classList.remove('hidden'); }}
function closeCart() {{ document.getElementById('cart-modal').classList.add('hidden'); }}
function cartText() {{ return Object.keys(cart).map(r => r + ' - ' + cart[r]).join('\\n'); }}
function sendRequest() {{
  const keys = Object.keys(cart);
  if (!keys.length) {{ alert('Coșul este gol.'); return false; }}
  const lines = keys.map(r => encodeURIComponent(r + ' - ' + cart[r])).join('%0A');
  const body = 'Buna ziua,%0A%0ADoresc date de contact si disponibilitate pentru urmatorii candidati:%0A%0A'
    + lines + '%0A%0AMultumesc.';
  window.location.href = 'mailto:{OFFICE_EMAIL}?subject='
    + encodeURIComponent('Cerere candidati InterJob (' + keys.length + ')') + '&body=' + body;
  return false;
}}
function copyList() {{
  navigator.clipboard.writeText(cartText())
    .then(() => alert('Lista a fost copiata.'))
    .catch(() => alert(cartText()));
}}
document.addEventListener('DOMContentLoaded', refreshCart);
</script>

</body>
</html>"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        size_mb = output_path.stat().st_size / 1024 / 1024
        mode_lbl = "INTERNAL" if INTERNAL else "CLIENT"
        print(f"[{mode_lbl}] {output_path}  ({size_mb:.2f} MB, {len(candidates)} candidates)")

    # Decide which mode(s) to build
    if args.all:
        INTERNAL = False; render(out_client)
        INTERNAL = True;  render(out_internal)
    elif args.internal:
        INTERNAL = True; render(out_internal)
    else:
        INTERNAL = False; render(out_client)


if __name__ == "__main__":
    main()
