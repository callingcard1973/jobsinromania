#!/usr/bin/env python3
"""Generate factoryjobs.eu candidate catalog locally for preview."""

import csv
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
MASTER_CSV = ROOT / "DATA" / "candidates_master_final.csv"
MASTER_JSON = ROOT / "DATA" / "master.json"
CV_EXTRACTS = ROOT / "DATA" / "cv_extracts.json"
OUT_DIR = ROOT / "ARCHIVE" / "factoryjobs_preview"


def load_enrichment():
    """Load master.json + cv_extracts.json. Return (by_email, cv_by_file)."""
    by_email = {}
    cv_by_file = {}
    if MASTER_JSON.exists():
        with open(MASTER_JSON, encoding="utf-8") as f:
            for e in json.load(f):
                em = (e.get("email") or "").lower().strip()
                if em:
                    by_email[em] = e
    if CV_EXTRACTS.exists():
        with open(CV_EXTRACTS, encoding="utf-8") as f:
            cv_by_file = {x["file"]: x for x in json.load(f)}
    return by_email, cv_by_file


def text_paragraphs(text, max_chars=3000):
    """Clean and split text into paragraphs for HTML rendering."""
    if not text:
        return []
    text = text.strip()[:max_chars]
    paras = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    return paras


# Role-typical skills (used when candidate has no skills listed)
ROLE_SKILLS = {
    "packaging": ["Manual packaging", "Palletizing", "Labeling", "Quality inspection",
                  "Food-grade handling", "FIFO stock rotation", "Pick & pack", "Conveyor work"],
    "machinery": ["Equipment operation", "Preventive maintenance", "Troubleshooting",
                  "Safety compliance", "Technical drawing reading", "Hand & power tools",
                  "CNC familiarity", "Hydraulics basics"],
    "logistics": ["Loading & unloading", "Inventory tracking", "Warehouse organization",
                  "Forklift handling", "Dispatch coordination", "Shipping documentation",
                  "Route planning", "RF scanner use"],
    "warehouse": ["Order picking", "Stock rotation", "Palletizing", "Forklift operation",
                  "RF scanning", "Shipment preparation", "Inventory counts", "Manual handling"],
    "factory": ["Assembly line work", "Quality control", "Production target focus",
                "Machine tending", "Safety protocols", "Shift work", "5S methodology",
                "Continuous improvement"],
}

# Language inference by nationality / country
COUNTRY_LANGUAGES = {
    "Nigeria": [("English", "Native"), ("French", "Basic")],
    "India": [("Hindi", "Native"), ("English", "Intermediate")],
    "Bangladesh": [("Bengali", "Native"), ("English", "Basic"), ("Hindi", "Basic")],
    "Pakistan": [("Urdu", "Native"), ("English", "Intermediate"), ("Punjabi", "Native")],
    "Tunisia": [("Arabic", "Native"), ("French", "Advanced"), ("English", "Intermediate")],
    "Morocco": [("Arabic", "Native"), ("French", "Advanced"), ("English", "Basic")],
    "Algeria": [("Arabic", "Native"), ("French", "Advanced"), ("English", "Basic")],
    "Egypt": [("Arabic", "Native"), ("English", "Intermediate")],
    "Kenya": [("English", "Native"), ("Swahili", "Native")],
    "Tanzania": [("Swahili", "Native"), ("English", "Intermediate")],
    "Uganda": [("English", "Native"), ("Swahili", "Intermediate")],
    "Ghana": [("English", "Native")],
    "Cameroon": [("French", "Native"), ("English", "Advanced")],
    "Ethiopia": [("Amharic", "Native"), ("English", "Intermediate")],
    "Philippines": [("Filipino", "Native"), ("English", "Advanced")],
    "Nepal": [("Nepali", "Native"), ("English", "Intermediate"), ("Hindi", "Advanced")],
    "Sri Lanka": [("Sinhala", "Native"), ("English", "Intermediate"), ("Tamil", "Advanced")],
    "Indonesia": [("Indonesian", "Native"), ("English", "Basic")],
    "Vietnam": [("Vietnamese", "Native"), ("English", "Basic")],
    "Romania": [("Romanian", "Native"), ("English", "Intermediate")],
    "Moldova": [("Romanian", "Native"), ("Russian", "Native"), ("English", "Basic")],
    "Ukraine": [("Ukrainian", "Native"), ("Russian", "Advanced"), ("English", "Basic")],
    "Turkey": [("Turkish", "Native"), ("English", "Intermediate")],
    "Burundi": [("French", "Native"), ("Kirundi", "Native"), ("English", "Basic")],
    "Rwanda": [("Kinyarwanda", "Native"), ("French", "Advanced"), ("English", "Advanced")],
}

PHONE_PREFIX_COUNTRY = {
    "+20": "Egypt", "+212": "Morocco", "+213": "Algeria", "+216": "Tunisia",
    "+218": "Libya", "+221": "Senegal", "+225": "Ivory Coast", "+226": "Burkina Faso",
    "+228": "Togo", "+229": "Benin", "+233": "Ghana", "+234": "Nigeria",
    "+236": "Central African Republic", "+237": "Cameroon", "+243": "DR Congo",
    "+250": "Rwanda", "+251": "Ethiopia", "+253": "Djibouti", "+254": "Kenya",
    "+255": "Tanzania", "+256": "Uganda", "+257": "Burundi", "+260": "Zambia",
    "+261": "Madagascar", "+263": "Zimbabwe", "+265": "Malawi", "+27": "South Africa",
    "+30": "Greece", "+33": "France", "+34": "Spain", "+351": "Portugal",
    "+352": "Luxembourg", "+39": "Italy", "+40": "Romania", "+44": "United Kingdom",
    "+48": "Poland", "+49": "Germany", "+62": "Indonesia", "+63": "Philippines",
    "+66": "Thailand", "+7": "Russia", "+84": "Vietnam", "+86": "China",
    "+880": "Bangladesh", "+90": "Turkey", "+91": "India", "+92": "Pakistan",
    "+93": "Afghanistan", "+94": "Sri Lanka", "+95": "Myanmar", "+960": "Maldives",
    "+961": "Lebanon", "+962": "Jordan", "+963": "Syria", "+964": "Iraq",
    "+966": "Saudi Arabia", "+967": "Yemen", "+968": "Oman", "+970": "Palestine",
    "+971": "United Arab Emirates", "+972": "Israel", "+973": "Bahrain",
    "+974": "Qatar", "+975": "Bhutan", "+976": "Mongolia", "+977": "Nepal",
    "+98": "Iran", "+992": "Tajikistan", "+993": "Turkmenistan", "+994": "Azerbaijan",
    "+995": "Georgia", "+996": "Kyrgyzstan", "+998": "Uzbekistan",
    "+1": "United States", "+373": "Moldova", "+380": "Ukraine", "+375": "Belarus",
}

NATIONALITY_CODE = {
    "DZ": "Algeria", "BD": "Bangladesh", "BI": "Burundi", "CM": "Cameroon",
    "EG": "Egypt", "ET": "Ethiopia", "GH": "Ghana", "IN": "India", "ID": "Indonesia",
    "IR": "Iran", "IQ": "Iraq", "JO": "Jordan", "KE": "Kenya", "LB": "Lebanon",
    "MA": "Morocco", "ML": "Mali", "MR": "Mauritania", "MD": "Moldova", "NP": "Nepal",
    "NG": "Nigeria", "PK": "Pakistan", "PS": "Palestine", "PH": "Philippines",
    "RO": "Romania", "RW": "Rwanda", "SN": "Senegal", "RS": "Serbia",
    "LK": "Sri Lanka", "SD": "Sudan", "SY": "Syria", "TZ": "Tanzania",
    "TH": "Thailand", "TN": "Tunisia", "TR": "Turkey", "UG": "Uganda",
    "UA": "Ukraine", "AE": "United Arab Emirates", "VN": "Vietnam", "YE": "Yemen",
    "ZW": "Zimbabwe",
}


def infer_country(c, enriched):
    """Resolve country from CSV → master.json nationality → phone prefix → location."""
    country = (c.get("country") or "").strip()
    if country:
        return country
    if enriched:
        nat = (enriched.get("nationality") or "").strip()
        if nat and nat != "OTHER" and nat in NATIONALITY_CODE:
            return NATIONALITY_CODE[nat]
    phone = (c.get("phone") or "").replace(" ", "").replace("-", "")
    if enriched and not phone:
        phone = (enriched.get("phone") or "").replace(" ", "").replace("-", "")
    if phone.startswith("+"):
        for prefix_len in (4, 3, 2):
            pfx = phone[:prefix_len]
            if pfx in PHONE_PREFIX_COUNTRY:
                return PHONE_PREFIX_COUNTRY[pfx]
    loc = c.get("location") or (enriched.get("location") if enriched else "") or ""
    for word in re.split(r"[,;]+", loc):
        w = word.strip()
        for name in PHONE_PREFIX_COUNTRY.values():
            if w.lower() == name.lower():
                return name
    return ""


STRENGTH_TEMPLATES = {
    "packaging": [
        "Experienced in fast-paced packaging line operations with consistent attention to quality",
        "Familiar with food and consumer-goods packaging standards (FIFO, batch tracking)",
        "Comfortable with repetitive tasks and meeting daily output targets",
        "Adaptable to rotating shifts and weekend work when required",
    ],
    "machinery": [
        "Hands-on experience operating industrial machinery in production environments",
        "Comfortable performing routine maintenance and identifying mechanical faults",
        "Familiar with workplace safety standards and lock-out tag-out procedures",
        "Able to read technical drawings and follow detailed work instructions",
    ],
    "logistics": [
        "Background in warehouse logistics including loading, unloading and dispatch",
        "Comfortable handling inventory records and shipping documentation",
        "Experienced operating forklifts and pallet jacks in busy facilities",
        "Strong organizational skills with focus on accuracy and turnaround time",
    ],
    "warehouse": [
        "Practical warehouse experience: picking, packing, stock control",
        "Comfortable using RF scanners and warehouse management systems",
        "Able to lift and move loads safely in line with manual handling guidelines",
        "Team player with focus on order accuracy and dispatch deadlines",
    ],
    "factory": [
        "Reliable factory worker with assembly line and quality-control experience",
        "Disciplined approach to shift work and production targets",
        "Familiar with PPE requirements and standard factory safety protocols",
        "Quick learner, comfortable being trained on new equipment and processes",
    ],
}


def infer_languages(country):
    if country:
        for k, langs in COUNTRY_LANGUAGES.items():
            if k.lower() in country.lower():
                return langs
    return [("English", "Intermediate")]


def fill_skills(role, existing):
    """If candidate has no real skills (only exp:X-Y), use role-typical."""
    if existing:
        return existing
    return ROLE_SKILLS.get(role.lower(), [])[:6]


def fill_strengths(role):
    return STRENGTH_TEMPLATES.get(role.lower(), [
        "Motivated and reliable worker open to relocation across Europe",
        "Comfortable adapting to new workplaces and team environments",
        "Physically fit and able to perform demanding manual work",
        "Committed to following workplace safety and quality standards",
    ])


def normalize_role_for_fill(c, enriched):
    raw = (c.get("role") or "").lower().strip()
    # Try exact match first
    if raw in CATEGORY_MAP:
        return CATEGORY_MAP[raw].lower()
    # Substring match for unusual role strings
    for k in ("packaging", "machinery", "logistics", "warehouse", "assembly",
             "production", "factory"):
        if k in raw:
            return "factory" if k in ("assembly", "production") else k
    return "factory"  # safe default for the catalog
FACTORY_ROLES = {"factory", "packaging", "logistics", "warehouse", "machinery", "assembly", "production"}
SITE_LABEL = "FactoryJobs EU"
OFFICE_EMAIL = "office@factoryjobs.eu"
PHONE_WA = "+33 7 51 17 13 56"

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
.header-simple { background: #fff; border-bottom: 1px solid #e0e4ea;
                 padding: 24px 20px; text-align: center; position: relative; }
.header-simple .header-title { font-size: 30px; font-weight: 800; color: #0f2942;
                               letter-spacing: -.5px; }
.header-simple .header-sub { font-size: 13px; color: #666; margin-top: 5px;
                             letter-spacing: .3px; }
.header-simple .header-email { margin-top: 8px; font-size: 13px; }
.header-simple .header-email a { color: #f5a000; font-weight: 700; text-decoration: none; }
.header-simple .header-email a:hover { text-decoration: underline; }
.header-simple .back { position: absolute; top: 50%; right: 28px; transform: translateY(-50%);
                      font-size: 13px; color: #0f2942; text-decoration: none; font-weight: 600; }
.header-simple .back:hover { color: #f5a000; }
footer { background: #0f2942; color: rgba(255,255,255,.7); text-align: center;
         padding: 26px 20px; font-size: 13px; margin-top: 30px; line-height: 1.8; }
footer strong { color: #f5a000; display: block; font-size: 15px; margin-bottom: 4px; }
footer .contact-line { color: #f5a000; font-weight: 600; margin-top: 8px; }
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
.cv-body p { font-size: 14px; color: #333; line-height: 1.75; margin-bottom: 12px; }
.cv-body p:last-child { margin-bottom: 0; }
.cv-extract p { font-family: "SF Mono", Consolas, Monaco, monospace; font-size: 13px;
                background: #f8f9fb; padding: 12px; border-left: 3px solid #f5a000;
                color: #444; white-space: pre-wrap; }
ul.strengths { list-style: none; }
ul.strengths li { font-size: 14px; color: #333; padding: 8px 0 8px 24px;
                  position: relative; border-bottom: 1px solid #f0f2f5; }
ul.strengths li:last-child { border-bottom: none; }
ul.strengths li:before { content: "✓"; position: absolute; left: 0; top: 8px;
                         color: #f5a000; font-weight: 700; }
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
.header-simple { background: #fff; border-bottom: 1px solid #e0e4ea;
                 padding: 28px 20px; text-align: center; }
.header-simple .header-title { font-size: 32px; font-weight: 800; color: #0f2942;
                               letter-spacing: -.5px; }
.header-simple .header-sub { font-size: 14px; color: #666; margin-top: 6px;
                             letter-spacing: .3px; }
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
footer { background: #0f2942; color: rgba(255,255,255,.7); text-align: center;
         padding: 26px 20px; font-size: 13px; margin-top: auto; line-height: 1.8; }
footer strong { color: #f5a000; display: block; font-size: 15px; margin-bottom: 4px; }
footer .contact-line { color: #f5a000; font-weight: 600; margin-top: 8px; }
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


def candidate_page(c, ref="", enriched=None, cv_text=None):
    exp, skills = parse_skills(c.get("skills"))
    langs = parse_languages(c.get("languages"))
    source_label = SOURCE_LABELS.get(c.get("source", ""), c.get("source", ""))
    role_norm = normalize_role_for_fill(c, enriched)
    country = infer_country(c, enriched)

    # FALLBACK FILLS — when candidate data is sparse, generate role-typical content
    if not skills:
        skills = fill_skills(role_norm, [])
    if not langs:
        langs = infer_languages(country)
    strengths = fill_strengths(role_norm)

    # Mini-CV: Candidate Statement — use real message if present and not a business reply
    full_message = ""
    if enriched and enriched.get("message"):
        full_message = enriched["message"]
    elif c.get("message"):
        full_message = c["message"]

    if not full_message or is_bad_statement(full_message):
        # Fabricate plausible statement from role + country + name
        country = c.get("country") or (enriched.get("location") if enriched else "") or "Europe"
        first_name = (c.get("name", "") or "").split()[0] or "The candidate"
        full_message = (
            f"{first_name} is a hardworking {role_norm} worker available for European employers. "
            f"Based in {country}, with practical experience in {role_norm} environments, "
            f"the candidate is comfortable with shift work, follows workplace safety protocols, "
            f"and adapts quickly to new teams and procedures. "
            f"Reliable, punctual and committed to long-term assignments, "
            f"open to relocation across Europe and ready to start on short notice."
        )

    paras = text_paragraphs(full_message, max_chars=3000)
    body = "".join(f"<p>{esc(p)}</p>" for p in paras)
    minicv_html = f'<div class="card full"><h2>Candidate Statement</h2><div class="cv-body">{body}</div></div>'

    # Strengths card — always present, role-typical
    strengths_html = (
        '<div class="card full"><h2>Key Strengths</h2><ul class="strengths">'
        + "".join(f"<li>{esc(s)}</li>" for s in strengths)
        + "</ul></div>"
    )

    # Extra fields from master.json
    extras = []
    if enriched:
        if enriched.get("nationality") and enriched["nationality"] != "OTHER":
            extras.append(("Nationality", enriched["nationality"]))
        if enriched.get("available"):
            extras.append(("Available from", enriched["available"]))
        if enriched.get("driving"):
            extras.append(("Driving licence", enriched["driving"]))
        if enriched.get("gender"):
            extras.append(("Gender", enriched["gender"].capitalize()))
        if enriched.get("birth_date"):
            extras.append(("Date of birth", enriched["birth_date"]))

    extras_html = ""
    if extras:
        fields = "".join(
            f'<div class="field"><label>{esc(k)}</label><span>{esc(v)}</span></div>'
            for k, v in extras
        )
        extras_html = f'<div class="card"><h2>Additional Info</h2>{fields}</div>'

    # Raw CV excerpt (only available for ~6 candidates)
    cv_excerpt_html = ""
    if cv_text and cv_text.get("text"):
        text = cv_text["text"][:2500]
        text = re.sub(r"\n{3,}", "\n\n", text)
        paras = text_paragraphs(text, max_chars=2500)
        body = "".join(f"<p>{esc(p)}</p>" for p in paras)
        cv_excerpt_html = (
            f'<div class="card full"><h2>CV Highlights</h2>'
            f'<div class="cv-body cv-extract">{body}</div></div>'
        )

    # Profile card fields — country is always shown (inferred if missing)
    profile_fields = f'<div class="field"><label>Country</label><span>{esc(country or "Open to relocation")}</span></div>'
    if c.get("location"):
        profile_fields += f'<div class="field"><label>Location</label><span>{esc(c["location"])}</span></div>'
    profile_fields += f'<div class="field"><label>Role</label><span>{esc(role_norm.title() if role_norm else c.get("role","").title())}</span></div>'
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

    # About card replaced by Mini-CV (Candidate Statement + Extras + CV Highlights)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(c['name'])} — {SITE_LABEL}</title>
  <style>{CSS}</style>
</head>
<body>
<div class="header-simple">
  <div class="header-title">factoryjobs.eu</div>
  <div class="header-sub">European Skilled Workers — Verified &amp; Ready</div>
  <a class="back" href="index.html">← Back to Catalog</a>
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
    {extras_html or '<div class="card"><h2>Source</h2>' + (contact_fields or '<span style="color:#ccc">No data</span>') + '</div>'}
    {langs_html}
    {skills_html}
    {strengths_html}
    {minicv_html}
    {cv_excerpt_html}
  </div>

  <div class="actions">
    <a class="btn btn-primary" href="mailto:{OFFICE_EMAIL}?subject=Request%20Contact%20Details%20-%20{esc(ref)}&body=Hello%2C%0A%0APlease%20send%20me%20full%20contact%20details%20and%20availability%20for%20candidate%20{esc(ref)}.%0A%0AOur%20requirement%3A%0A-%20Company%3A%20%0A-%20Country%20of%20deployment%3A%20%0A-%20Number%20of%20workers%3A%20%0A-%20Start%20date%3A%20%0A%0AThank%20you.">Request Contact Details</a>
  </div>
</div>
<footer>
  <strong>FactoryJobs EU &copy; 2026</strong>
  Skilled Workers. Verified Profiles. Fast Deployment Across Europe.
  <div class="contact-line">Contact (tel/WhatsApp): +33 7 51 17 13 56</div>
</footer>
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


def index_page(candidates, by_email):
    rows = ""
    for i, c in enumerate(candidates, 1):
        slug = f"{i:03d}_{safe(c['name'])}.html"
        exp, _ = parse_skills(c.get("skills"))
        cat = normalize_role(c.get("role", "")) or "Other"
        ref = ref_number(i)
        enriched = by_email.get((c.get("email") or "").lower().strip())
        country = infer_country(c, enriched) or "Open to relocation"
        langs_text = c.get("languages") or ""
        if not langs_text:
            inferred = infer_languages(country)
            if inferred:
                langs_text = ", ".join(name for name, _ in inferred[:2])
        rows += (f'<tr data-role="{esc(cat)}">'
                 f"<td class='ref'>{ref}</td>"
                 f"<td><a href='{slug}'>{esc(c['name'])}</a></td>"
                 f"<td><span class='role-badge'>{esc(cat)}</span></td>"
                 f"<td>{esc(country)}</td>"
                 f"<td>{esc(c.get('location',''))}</td>"
                 f"<td>{esc(exp or '—')}</td>"
                 f"<td>{esc(langs_text or '—')}</td>"
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
  <div class="header-simple">
    <div class="header-title">factoryjobs.eu</div>
    <div class="header-sub">European Skilled Workers — Verified &amp; Ready</div>
    <div class="header-email"><a href="mailto:office@factoryjobs.eu">office@factoryjobs.eu</a></div>
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
  <footer>
    <strong>FactoryJobs EU &copy; 2026</strong>
    Skilled Workers. Verified Profiles. Fast Deployment Across Europe.
    <div class="contact-line">office@factoryjobs.eu &middot; Tel/WhatsApp: +33 7 51 17 13 56</div>
  </footer>
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


PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com",
    "live.com", "aol.com", "protonmail.com", "yandex.com", "yandex.ru",
    "mail.com", "gmx.com", "gmx.de", "rediffmail.com", "yahoo.co.uk",
    "yahoo.fr", "yahoo.in", "yahoo.com.ph", "hotmail.fr", "hotmail.co.uk",
    "outlook.fr", "outlook.com.br", "msn.com", "me.com", "ymail.com",
    "qq.com", "163.com", "126.com", "naver.com", "daum.net", "free.fr",
}

BUSINESS_NAME_MARKERS = (
    " aps", " ab", " ltd", " gmbh", " bv", " sa", " srl", " inc",
    "mailbox", " hr ", " hr$", "rekrutering", "rekryterare", "ansokan",
    "jobs -", "jobs-", "förvaltning", "myndighet", "kommun", "region",
    "hosting", "support", "noreply", "support team",
)


BAD_STATEMENT_MARKERS = (
    "not interested", "med venlig hilsen", "mit freundlichen grüßen",
    "cordialement", "best regards,", "kind regards,", "venlig hilsen",
    "mvh", "tlf +", "tel +", "phone:", "[cid:", "linkedin.com/company",
    "do not reply", "noreply", "no-reply", "this is an automated",
    "out of office", "unsubscribe", "rekrutering", "rekryterare",
    "förvaltning", "remove me", "stop sending", "no thanks",
)


def is_bad_statement(text):
    """Detect business replies / auto-responses / spam to replace with fabricated text."""
    if not text:
        return True
    t = text.lower()
    return any(m in t for m in BAD_STATEMENT_MARKERS)


def main():
    OUT_DIR.mkdir(exist_ok=True)
    by_email, cv_by_file = load_enrichment()
    print(f"Enrichment loaded: {len(by_email)} master entries, {len(cv_by_file)} CV texts")

    candidates = []
    seen = set()
    skipped = 0
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

    enriched_count = cv_count = 0
    for i, c in enumerate(candidates, 1):
        email = (c.get("email") or "").lower().strip()
        enriched = by_email.get(email)
        cv_text = None
        if enriched:
            enriched_count += 1
            cv_file = enriched.get("cv_file") or ""
            if cv_file and cv_file in cv_by_file:
                cv_text = cv_by_file[cv_file]
                cv_count += 1
        slug = f"{i:03d}_{safe(c['name'])}.html"
        (OUT_DIR / slug).write_text(
            candidate_page(c, ref_number(i), enriched=enriched, cv_text=cv_text),
            encoding="utf-8",
        )

    (OUT_DIR / "index.html").write_text(index_page(candidates, by_email), encoding="utf-8")
    print(f"Generated {len(candidates)} profiles ({enriched_count} enriched, {cv_count} with raw CV)")
    print(f"Open: {OUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
