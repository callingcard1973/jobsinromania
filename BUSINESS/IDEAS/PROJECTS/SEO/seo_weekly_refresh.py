#!/usr/bin/env python3
"""SEO Weekly Refresh — re-deploys sitemaps with fresh dates + verifies schema + crosslinks.
Runs on raspibig every Sunday at 06:00.

Idempotent — safe to re-run. Only updates sitemap lastmod dates.
Schema and crosslinks are verified, not re-deployed unless missing.

Usage:
    python3 seo_weekly_refresh.py          # Full refresh
    python3 seo_weekly_refresh.py --dry-run # Preview only
"""

import urllib.request, urllib.parse, json, ssl, sys, re
from datetime import date, datetime

API_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
HOME = "/home/loaiidil"
TODAY = date.today().isoformat()

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

SITES = [
    "careworkers.eu", "factoryjobs.eu", "buildjobs.eu", "electricjobs.eu",
    "farmworkers.eu", "horecaworkers.eu", "meatworkers.eu", "mechanicjobs.eu",
    "warehouseworkers.eu", "aluminumrecyclehub.com", "expatsinromania.org",
    "interjob.ro", "mivromania.info", "mivromania.online", "nepalezi.com",
]

DRY_RUN = "--dry-run" in sys.argv
LOG_FILE = "/opt/LOGS/seo_refresh.log"

def log(msg):
    line = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def cpanel_call(endpoint, params=None):
    url = f"{HOST}/execute/{endpoint}"
    if params:
        qs = "&".join(f"{k}={urllib.parse.quote(str(v))}" for k, v in params.items())
        url += f"?{qs}"
    req = urllib.request.Request(url, headers={"Authorization": f"cpanel {USER}:{API_TOKEN}"})
    with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
        return json.loads(r.read())


def get_docroot(site):
    overrides = {"warehouseworkers.eu": f"{HOME}/public_html/warehouseworkers.eu"}
    return overrides.get(site, f"{HOME}/public_html/{site}")


def get_file(path):
    d, f = path.rsplit("/", 1)
    r = cpanel_call("Fileman/get_file_content", {"dir": d, "file": f})
    if r.get("status") == 1:
        return r["data"][0]["content"]
    return None


def save_file(path, content):
    d, f = path.rsplit("/", 1)
    r = cpanel_call("Fileman/save_file_content", {
        "dir": d, "file": f,
        "content": content,
    })
    return r.get("status") == 1


def refresh_sitemap(site):
    """Update all lastmod dates in sitemap.xml to today."""
    docroot = get_docroot(site)
    sitemap_path = f"{docroot}/sitemap.xml"
    content = get_file(sitemap_path)
    if not content:
        log(f"  {site}: NO sitemap.xml found")
        return False

    # Count URLs before
    url_count = content.count("<url>")
    # Update all lastmod dates
    updated = re.sub(r"<lastmod>\d{4}-\d{2}-\d{2}</lastmod>", f"<lastmod>{TODAY}</lastmod>", content)

    if updated == content:
        log(f"  {site}: sitemap OK ({url_count} URLs, dates current)")
        return True

    if DRY_RUN:
        log(f"  {site}: [DRY] would update {url_count} URL dates to {TODAY}")
        return True

    if save_file(sitemap_path, updated):
        log(f"  {site}: sitemap refreshed ({url_count} URLs -> {TODAY})")
        return True
    else:
        log(f"  {site}: FAILED to save sitemap")
        return False


def check_schema(site):
    """Quick check that homepage has EmploymentAgency schema."""
    docroot = get_docroot(site)
    content = get_file(f"{docroot}/index.html")
    if not content:
        log(f"  {site}: NO index.html")
        return False
    has_org = "EmploymentAgency" in content or "Organization" in content
    has_faq = "FAQPage" in content
    has_network = "network-sites" in content
    status = "OK" if (has_org and has_faq and has_network) else "MISSING"
    details = []
    if not has_org: details.append("schema")
    if not has_faq: details.append("FAQ")
    if not has_network: details.append("crosslinks")
    if details:
        log(f"  {site}: schema check MISSING {'+'.join(details)}")
    return has_org and has_faq and has_network


def ping_search_engines(site):
    """Ping Google and Bing with updated sitemap."""
    sitemap_url = f"https://{site}/sitemap.xml"
    for engine, url in [
        ("Google", f"https://www.google.com/ping?sitemap={sitemap_url}"),
        ("Bing", f"https://www.bing.com/ping?sitemap={sitemap_url}"),
    ]:
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=15, context=CTX) as r:
                log(f"  {site}: pinged {engine} ({r.status})")
        except Exception as e:
            log(f"  {site}: ping {engine} failed: {e}")


def main():
    log(f"=== SEO Weekly Refresh (dry_run={DRY_RUN}) ===")
    ok_sitemap = 0
    ok_schema = 0

    for site in SITES:
        log(f"Checking {site}...")
        if refresh_sitemap(site):
            ok_sitemap += 1
        if check_schema(site):
            ok_schema += 1
        if not DRY_RUN:
            ping_search_engines(site)

    log(f"=== Done: {ok_sitemap}/{len(SITES)} sitemaps OK, {ok_schema}/{len(SITES)} schema OK ===")


if __name__ == "__main__":
    main()
