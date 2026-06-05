#!/usr/bin/env python3
"""Generate and deploy candidate catalog HTML for any fw_websites domain."""

import argparse
import logging
import os
import sys
import tempfile
from pathlib import Path

import psycopg2
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger(__name__)

DB_DSN = "host=localhost dbname=interjob_master user=tudor password=bucare"
CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = "K9ATCMHPKVSKUV2M97447JLY45EH29KQ"
MIN_SCORE = 50


CSS = """* {margin:0;padding:0;box-sizing:border-box}
body {font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;background:#f5f5f5;color:#333;line-height:1.6}
.wrap {max-width:900px;margin:0 auto;padding:20px}
.hdr {background:linear-gradient(135deg,#1e3c72,#2a5298);color:#fff;padding:40px;border-radius:8px;margin-bottom:30px}
.hdr h1 {font-size:28px;margin-bottom:8px}
.meta {font-size:14px;margin-top:12px}
.sec {background:#fff;padding:25px;margin-bottom:20px;border-radius:8px;box-shadow:0 1px 3px rgba(0,0,0,.05)}
.sec h2 {font-size:16px;color:#1e3c72;margin-bottom:12px;border-bottom:2px solid #2a5298;padding-bottom:8px}
.badge {display:inline-block;background:#2a5298;color:#fff;padding:4px 10px;border-radius:20px;margin:3px;font-size:12px}
.dim {color:#999;font-size:12px;margin-top:10px;padding-top:10px;border-top:1px solid #eee}"""


def _esc(s: str) -> str:
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _safe(name: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "_", (name or "unknown").lower()).strip("_")[:60]


def candidate_page(c: dict, site_label: str) -> str:
    badges = lambda lst: "".join(f'<span class="badge">{_esc(x)}</span>' for x in (lst or []))
    info = []
    if c.get("location"): info.append(f"<p>📍 {_esc(c['location'])}</p>")
    if c.get("country"):  info.append(f"<p>🌍 {_esc(c['country'])}</p>")
    if c.get("role"):     info.append(f"<p>💼 {_esc(c['role'])}</p>")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_esc(c['name'])} - {_esc(site_label)}</title>
<style>{CSS}</style></head>
<body><div class="wrap">
<div class="hdr"><h1>{_esc(c['name'])}</h1><div class="meta">{"".join(info)}</div></div>
{"<div class='sec'><h2>Skills</h2>" + badges(c.get("skills", "").split(",") if c.get("skills") else []) + "</div>" if c.get("skills") else ""}
{"<div class='sec'><h2>Languages</h2>" + badges(c.get("languages", "").split(",") if c.get("languages") else []) + "</div>" if c.get("languages") else ""}
<div class="sec"><p class="dim">Profile listed on {_esc(site_label)}</p></div>
</div></body></html>"""


def index_page(candidates: list, site_label: str) -> str:
    rows = ""
    for i, c in enumerate(candidates, 1):
        slug = f"{i:03d}_{_safe(c['name'])}.html"
        rows += (f"<tr><td>{i}</td><td><a href='{slug}'>{_esc(c['name'])}</a></td>"
                 f"<td>{_esc(c.get('location',''))}</td><td>{_esc(c.get('country',''))}</td>"
                 f"<td>{_esc(c.get('role',''))}</td><td>{c.get('score',0)}</td></tr>\n")
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Candidates — {_esc(site_label)}</title>
<style>body{{font-family:Arial,sans-serif;max-width:1100px;margin:0 auto;padding:20px}}
h1{{color:#1e3c72;margin-bottom:20px}}table{{width:100%;border-collapse:collapse}}
th,td{{padding:10px 12px;text-align:left;border-bottom:1px solid #ddd}}
th{{background:#1e3c72;color:#fff}}tr:hover{{background:#f5f5f5}}a{{color:#2a5298}}</style></head>
<body><h1>{_esc(site_label)} — Candidates ({len(candidates)})</h1>
<table><thead><tr><th>#</th><th>Name</th><th>Location</th><th>Country</th><th>Role</th><th>Score</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>"""


def deploy_file(content: str, cpanel_path: str, filename: str) -> bool:
    url = f"https://{CPANEL_HOST}:2083/execute/Fileman/save_file_content"
    r = requests.post(url, headers={"Authorization": f"cpanel {CPANEL_USER}:{CPANEL_TOKEN}"},
                      data={"dir": cpanel_path, "filename": filename, "content": content}, timeout=15)
    return r.status_code == 200 and r.json().get("status") == 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--domain", required=True, help="e.g. factoryjobs.eu")
    parser.add_argument("--min-score", type=int, default=MIN_SCORE)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DB_DSN)
    cur = conn.cursor()

    cur.execute("SELECT id, cpanel_path FROM fw_websites WHERE domain=%s", (args.domain,))
    row = cur.fetchone()
    if not row:
        sys.exit(f"Domain {args.domain} not found in fw_websites")
    website_id, cpanel_path = row
    site_label = args.domain.replace(".eu", "").replace(".com", "").replace(".org", "").replace("-", " ").title()

    cur.execute("""
        SELECT c.id, c.name, c.email, c.country, c.location, c.role,
               c.skills, c.languages, s.relevance_score
        FROM fw_candidate_scores s
        JOIN fw_candidates c ON c.id = s.candidate_id
        WHERE s.website_id = %s AND s.relevance_score >= %s
          AND c.name NOT LIKE 'Unknown%%'
        ORDER BY s.relevance_score DESC, c.name
    """, (website_id, args.min_score))
    candidates = [
        {"id": r[0], "name": r[1], "email": r[2], "country": r[3],
         "location": r[4], "role": r[5], "skills": r[6], "languages": r[7], "score": r[8]}
        for r in cur.fetchall()
    ]
    conn.close()

    log.info("Found %d candidates for %s (score>=%d)", len(candidates), args.domain, args.min_score)

    if args.dry_run:
        for c in candidates[:5]:
            log.info("  %s | score=%d | %s", c["name"], c["score"], c["role"])
        return

    candidates_path = f"{cpanel_path}/candidates"
    ok = deployed = 0

    for i, c in enumerate(candidates, 1):
        slug = f"{i:03d}_{_safe(c['name'])}.html"
        html = candidate_page(c, site_label)
        if deploy_file(html, candidates_path, slug):
            deployed += 1
        else:
            log.warning("Failed: %s", slug)

    idx = index_page(candidates, site_label)
    if deploy_file(idx, candidates_path, "index.html"):
        ok += 1

    log.info("Done: %d profiles + index deployed to %s/candidates/", deployed, args.domain)


if __name__ == "__main__":
    main()
