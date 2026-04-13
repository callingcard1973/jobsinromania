#!/usr/bin/env python3
"""
Broken Link Fixer: Detect, fix, and reupload broken links in 28 InterJob sites.
1. Reads latest seo_audit_YYYY-MM-DD.json
2. Extracts broken links (404, 500, timeout)
3. Queries Qwen 2.5 on raspibig for replacement URLs
4. Downloads HTML from A2 cPanel, replaces hrefs, reuploads
5. Updates audit status, logs before/after
"""
import json, requests, re, ssl, urllib.request, urllib.parse, os
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from db_client import get_conn, safe_insert
except ImportError:
    def get_conn(*args, **kwargs): return None
    def safe_insert(*args, **kwargs): return False

CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
QWEN_URL = "http://192.168.100.20:11434/api/generate"
SCRIPT_DIR = Path(__file__).parent

def log(msg, level="INFO"):
    ts = datetime.now().isoformat()
    print(f"[{ts}] {level}: {msg}")
    with open(SCRIPT_DIR / f"broken_links_fixed_{datetime.now().strftime('%Y-%m-%d')}.log", "a") as f:
        f.write(f"[{ts}] {level}: {msg}\n")

def find_latest_audit():
    """Find most recent seo_audit_YYYY-MM-DD.json"""
    audits = sorted(SCRIPT_DIR.glob("seo_audit_*.json"), reverse=True)
    if not audits:
        log("No audit files found. Run seo_audit.py first.", "ERROR")
        return None
    return audits[0]

def load_audit(audit_file):
    """Load audit JSON"""
    try:
        with open(audit_file) as f:
            return json.load(f)
    except Exception as e:
        log(f"Failed to load audit: {e}", "ERROR")
        return None

def extract_broken_links(audit):
    """Extract domain->broken_links from audit results"""
    broken = {}
    for result in audit.get("results", []):
        domain = result.get("domain")
        broken_match = [i for i in result.get("issues", []) if "Broken links" in i]
        if broken_match:
            broken[domain] = broken_match[0]
    return broken

def qwen_find_replacement(broken_url, domain, retries=3):
    """Use Qwen 2.5 to find replacement URL for broken link"""
    prompt = f"""Given a broken link: {broken_url}
Domain: {domain}
Suggest 1 replacement URL as JSON {{"url": "..."}}.
Priority: 1) Search same domain first 2) External similar content 3) Homepage.
Return only valid JSON, no explanation."""

    for attempt in range(retries):
        try:
            r = requests.post(QWEN_URL, json={
                "model": "qwen2.5:7b-instruct",
                "prompt": prompt,
                "stream": False
            }, timeout=30)
            if r.status_code == 200:
                resp = r.json().get("response", "").strip()
                match = re.search(r'"url":\s*"([^"]+)"', resp)
                if match:
                    return match.group(1)
        except Exception as e:
            log(f"Qwen error attempt {attempt+1}/{retries}: {e}", "WARN")
            if attempt < retries - 1:
                import time; time.sleep(2)
    return f"https://{domain}/"  # Fallback to homepage

def cpanel_get_file(domain, file_path, retries=3):
    """Download file from cPanel"""
    url = f"https://{CPANEL_HOST}:2083/execute/Fileman/get_file_content"
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE

    for attempt in range(retries):
        try:
            data = urllib.parse.urlencode({"dir": f"/{domain}", "file": file_path}).encode()
            req = urllib.request.Request(url, data=data)
            req.add_header('Authorization', f'cpanel {CPANEL_USER}:{CPANEL_TOKEN}')
            with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
                result = json.loads(r.read().decode())
                if result.get("status") == 1:
                    return result.get("content")
        except Exception as e:
            log(f"cPanel get {file_path} attempt {attempt+1}/{retries}: {e}", "WARN")
            if attempt < retries - 1:
                import time; time.sleep(2)
    return None

def cpanel_put_file(domain, file_path, content, retries=3):
    """Upload fixed HTML to cPanel"""
    url = f"https://{CPANEL_HOST}:2083/execute/Fileman/save_file"
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE

    for attempt in range(retries):
        try:
            data = urllib.parse.urlencode({
                "dir": f"/{domain}",
                "file": file_path,
                "content": content
            }).encode()
            req = urllib.request.Request(url, data=data)
            req.add_header('Authorization', f'cpanel {CPANEL_USER}:{CPANEL_TOKEN}')
            with urllib.request.urlopen(req, context=ctx, timeout=20) as r:
                result = json.loads(r.read().decode())
                if result.get("status") == 1:
                    return True
        except Exception as e:
            log(f"cPanel put {file_path} attempt {attempt+1}/{retries}: {e}", "WARN")
            if attempt < retries - 1:
                import time; time.sleep(2)
    return False

def find_broken_hrefs(html):
    """Parse HTML, find all href values that might be broken"""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        return [a.get('href') for a in soup.find_all('a', href=True)]
    except:
        return []

def replace_href(html, old_url, new_url):
    """Replace broken href with fixed URL in HTML"""
    return html.replace(f'href="{old_url}"', f'href="{new_url}"')

def fix_domain_links(domain, broken_issue, audit):
    """Fix all broken links for one domain"""
    log(f"Processing {domain}: {broken_issue}")

    # Parse out broken count
    match = re.search(r"(\d+)/(\d+)", broken_issue)
    if not match:
        return

    broken_count = int(match.group(1))
    log(f"  Found {broken_count} broken links, attempting fixes...")

    # Download homepage HTML
    html = cpanel_get_file(domain, "index.html")
    if not html:
        log(f"  Failed to get index.html, skipping {domain}", "ERROR")
        return

    hrefs = find_broken_hrefs(html)
    if not hrefs:
        log(f"  No hrefs found in HTML, skipping")
        return

    fixes = 0
    fixed_links = []

    for href in hrefs[:broken_count]:  # Only check reported broken count
        if not href.startswith('http'):
            continue

        # Test if still broken (quick check)
        try:
            r = requests.head(href, timeout=5, allow_redirects=True)
            if r.status_code in [200, 301, 302]:
                continue  # Link is fine
        except:
            pass

        # Link is broken, find replacement
        replacement = qwen_find_replacement(href, domain)
        html = replace_href(html, href, replacement)
        fixed_links.append({"old": href, "new": replacement})
        fixes += 1
        log(f"  Fixed {fixes}: {href[:50]}... -> {replacement[:50]}...")

    if fixes == 0:
        log(f"  No fixes applied for {domain}")
        return

    # Reupload fixed HTML
    if cpanel_put_file(domain, "index.html", html):
        log(f"  Uploaded fixed HTML to {domain} ({fixes} fixes)")
        audit_entry = next((r for r in audit.get("results", []) if r.get("domain") == domain), None)
        if audit_entry:
            audit_entry["links_fixed"] = fixes
            audit_entry["fixed_links"] = fixed_links

        # Write each fix to database
        conn = get_conn()
        if conn:
            for link in fixed_links:
                sql = """
                    INSERT INTO broken_link_fixes (domain, old_url, new_url, applied, fix_date, audit_file)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT DO NOTHING
                """
                safe_insert(conn, sql, (domain, link['old'], link['new'], True, datetime.now().date(), 'index.html'))
            conn.close()
            log(f"[DB] Recorded {fixes} link fixes for {domain}")
    else:
        log(f"  Failed to upload fixed HTML for {domain}", "ERROR")

def main():
    """Main workflow: audit -> extract broken -> fix -> upload -> log"""
    audit_file = find_latest_audit()
    if not audit_file:
        sys.exit(1)

    log(f"Processing audit: {audit_file.name}")
    audit = load_audit(audit_file)
    if not audit:
        sys.exit(1)

    broken = extract_broken_links(audit)
    if not broken:
        log("No broken links found in audit")
        return

    log(f"Found {len(broken)} domains with broken links")

    for domain, issue in broken.items():
        fix_domain_links(domain, issue, audit)

    # Save updated audit with fixes
    with open(audit_file) as f:
        updated = json.load(f)

    # Merge fixes back
    for result in audit.get("results", []):
        if "links_fixed" in result:
            updated_result = next((r for r in updated.get("results", []) if r.get("domain") == result.get("domain")), None)
            if updated_result:
                updated_result["links_fixed"] = result.get("links_fixed")
                updated_result["fixed_links"] = result.get("fixed_links")

    with open(audit_file, "w") as f:
        json.dump(updated, f, indent=2)

    log("Broken link fixer complete")

if __name__ == "__main__":
    main()
