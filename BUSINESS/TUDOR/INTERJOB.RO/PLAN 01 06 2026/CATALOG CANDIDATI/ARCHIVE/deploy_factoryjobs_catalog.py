#!/usr/bin/env python3
"""Generate and deploy factoryjobs.eu candidate catalog from master CSV."""

import csv
import logging
import re
import time
from datetime import datetime
from pathlib import Path

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

MASTER_CSV = Path(__file__).parent / "candidates_master_final.csv"
CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = "K9ATCMHPKVSKUV2M97447JLY45EH29KQ"
CPANEL_PATH = "/home/loaiidil/factoryjobs.eu/candidates"
SITE_LABEL = "FactoryJobs EU"
SITE_URL = "https://factoryjobs.eu"

FACTORY_ROLES = {"factory", "packaging", "logistics", "warehouse", "machinery", "assembly", "production"}

CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:#f4f6f9;color:#333;line-height:1.6}
.wrap{max-width:860px;margin:0 auto;padding:24px}
.hdr{background:linear-gradient(135deg,#0f2942,#1a4a7a);color:#fff;padding:36px;border-radius:10px;margin-bottom:24px}
.hdr h1{font-size:26px;margin-bottom:6px}
.hdr .sub{font-size:14px;opacity:.8}
.sec{background:#fff;padding:22px;margin-bottom:16px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,.07)}
.sec h2{font-size:15px;color:#0f2942;margin-bottom:10px;border-bottom:2px solid #1a4a7a;padding-bottom:6px}
.badge{display:inline-block;background:#1a4a7a;color:#fff;padding:3px 10px;border-radius:20px;margin:2px;font-size:12px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:14px}
.dim{color:#aaa;font-size:11px;margin-top:12px}
@media(max-width:600px){.grid{grid-template-columns:1fr}.hdr{padding:20px}}"""


def _esc(s) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _safe(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", (name or "unknown").lower()).strip("_")[:60]


def candidate_page(c: dict) -> str:
    info = []
    if c.get("country"):  info.append(f"<div>🌍 <strong>Country:</strong> {_esc(c['country'])}</div>")
    if c.get("location"): info.append(f"<div>📍 <strong>Location:</strong> {_esc(c['location'])}</div>")
    if c.get("role"):     info.append(f"<div>💼 <strong>Role:</strong> {_esc(c['role'])}</div>")
    if c.get("languages"):info.append(f"<div>🗣 <strong>Languages:</strong> {_esc(c['languages'])}</div>")

    skills_html = ""
    if c.get("skills"):
        badges = "".join(f'<span class="badge">{_esc(s.strip())}</span>' for s in c["skills"].split(",") if s.strip())
        skills_html = f'<div class="sec"><h2>Skills</h2>{badges}</div>'

    msg_html = ""
    if c.get("message"):
        msg_html = f'<div class="sec"><h2>About</h2><p style="font-size:14px">{_esc(c["message"][:600])}{"…" if len(c.get("message",""))>600 else ""}</p></div>'

    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(c['name'])} — {SITE_LABEL}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<div class="hdr">
  <h1>{_esc(c['name'])}</h1>
  <div class="sub">{_esc(c.get('role','').title())} candidate</div>
</div>
<div class="sec"><h2>Profile</h2><div class="grid">{"".join(info)}</div></div>
{skills_html}
{msg_html}
<div class="sec"><p class="dim">Listed on {SITE_LABEL} · {datetime.now().strftime('%Y-%m-%d')}</p></div>
</div></body></html>"""


def index_page(candidates: list) -> str:
    rows = ""
    for i, c in enumerate(candidates, 1):
        slug = f"{i:03d}_{_safe(c['name'])}.html"
        rows += (f"<tr><td>{i}</td>"
                 f"<td><a href='{slug}'>{_esc(c['name'])}</a></td>"
                 f"<td>{_esc(c.get('role','').title())}</td>"
                 f"<td>{_esc(c.get('country',''))}</td>"
                 f"<td>{_esc(c.get('location',''))}</td>"
                 f"<td>{_esc(c.get('languages',''))}</td></tr>\n")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Candidates — {SITE_LABEL}</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:0 auto;padding:20px;color:#333}}
h1{{color:#0f2942;margin-bottom:6px}}
.sub{{color:#666;margin-bottom:20px;font-size:14px}}
table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #e0e0e0}}
th{{background:#0f2942;color:#fff;font-weight:600}}
tr:hover{{background:#f0f4f8}}
a{{color:#1a4a7a;text-decoration:none}}a:hover{{text-decoration:underline}}
.dim{{color:#aaa;font-size:12px;margin-top:20px}}</style></head>
<body>
<h1>{SITE_LABEL} — Available Candidates</h1>
<p class="sub">{len(candidates)} candidates in factory, packaging, logistics, warehouse and related roles</p>
<table><thead><tr><th>#</th><th>Name</th><th>Role</th><th>Country</th><th>Location</th><th>Languages</th></tr></thead>
<tbody>{rows}</tbody></table>
<p class="dim">Updated {datetime.now().strftime('%Y-%m-%d %H:%M')} · <a href="{SITE_URL}">Back to {SITE_LABEL}</a></p>
</body></html>"""


def deploy(filename: str, content: str) -> bool:
    r = requests.post(
        f"https://{CPANEL_HOST}:2083/execute/Fileman/save_file_content",
        headers={"Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"},
        data={"dir": CPANEL_PATH, "filename": filename, "content": content},
        timeout=20,
    )
    if r.status_code != 200:
        return False
    return r.json().get("status") == 1


def load_candidates() -> list:
    candidates = []
    seen_emails = set()
    with open(MASTER_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            name = (row.get("name") or "").strip()
            role = (row.get("role") or "").lower().strip()
            email = (row.get("email") or "").strip().lower()
            if not name or name.startswith("Unknown"):
                continue
            if "@" in name:  # skip emails-as-names
                continue
            if not any(r in role for r in FACTORY_ROLES):
                continue
            if email and email in seen_emails:
                continue
            if email:
                seen_emails.add(email)
            candidates.append(row)
    return candidates


def main():
    candidates = load_candidates()
    log.info("Loaded %d factory candidates from master CSV", len(candidates))

    deployed = 0
    failed = 0
    for i, c in enumerate(candidates, 1):
        slug = f"{i:03d}_{_safe(c['name'])}.html"
        html = candidate_page(c)
        if deploy(slug, html):
            deployed += 1
        else:
            log.warning("Failed: %s", slug)
            failed += 1
        if i % 50 == 0:
            log.info("Progress: %d/%d", i, len(candidates))
            time.sleep(0.5)  # rate limit

    idx = index_page(candidates)
    if deploy("index.html", idx):
        log.info("Index deployed: %s/candidates/", SITE_URL)
    else:
        log.error("Index deploy FAILED")

    log.info("Done: %d deployed, %d failed", deployed, failed)
    log.info("URL: %s/candidates/", SITE_URL)


if __name__ == "__main__":
    main()
