"""Update sitemaps on all 15 job sites to include Chinese (zh) pages.

Appends zh.html and zh/* subpages to existing sitemap.xml files.
"""
import urllib.request, urllib.parse, json, ssl, sys, time, re
from datetime import date

API_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
HOME = "/home/loaiidil"
TODAY = date.today().isoformat()

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

DOCROOT_OVERRIDES = {
    "warehouseworkers.eu": f"{HOME}/public_html/warehouseworkers.eu",
}

SITES = [
    "careworkers.eu", "factoryjobs.eu", "buildjobs.eu", "electricjobs.eu",
    "farmworkers.eu", "horecaworkers.eu", "meatworkers.eu", "mechanicjobs.eu",
    "warehouseworkers.eu", "aluminumrecyclehub.com", "expatsinromania.org",
    "interjob.ro", "mivromania.info", "mivromania.online", "nepalezi.com",
]

COUNTRIES = ["de", "nl", "be", "at", "dk", "ch"]
SUBPAGES = ["faq", "salary", "visa"]

def cpanel_get_file(remote_path):
    import base64
    dir_part = remote_path.rsplit("/", 1)[0]
    file_part = remote_path.rsplit("/", 1)[1]
    url = f"{HOST}/execute/Fileman/get_file_content?dir={urllib.parse.quote(dir_part)}&file={urllib.parse.quote(file_part)}"
    req = urllib.request.Request(url, headers={"Authorization": f"cpanel {USER}:{API_TOKEN}"})
    try:
        r = urllib.request.urlopen(req, timeout=30, context=CTX)
        data = json.loads(r.read())
        content = data.get("data", {}).get("content", "")
        # cPanel returns base64-encoded content for binary/xml files
        if content and not content.strip().startswith("<?xml") and not content.strip().startswith("<"):
            padded = content + "=" * (4 - len(content) % 4) if len(content) % 4 else content
            try:
                content = base64.b64decode(padded).decode("utf-8", errors="replace")
            except Exception:
                pass
        return content
    except Exception:
        return None

def cpanel_upload(content_bytes, filename, remote_dir):
    boundary = "----FormBound7MA4YWxk"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="dir"\r\n\r\n'
        f"{remote_dir}\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="overwrite"\r\n\r\n'
        f"1\r\n"
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file-1"; filename="{filename}"\r\n'
        f"Content-Type: application/xml\r\n\r\n"
    ).encode("utf-8") + content_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")
    url = f"{HOST}/execute/Fileman/upload_files"
    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Authorization": f"cpanel {USER}:{API_TOKEN}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    })
    for attempt in range(3):
        try:
            urllib.request.urlopen(req, timeout=30, context=CTX)
            return True
        except Exception as e:
            if attempt < 2:
                time.sleep(3 * (attempt + 1))
            else:
                print(f"  ERR {remote_dir}/{filename}: {e}")
                return False

LANGS_ALL = ["am","ar","bg","bn","cs","da","de","el","en","es","et","fi","fr","hi","hr","hu",
             "id","ig","it","ln","lt","lv","mk","ne","nl","no","om","pa","pl","ps","pt","ro",
             "ru","sk","sl","so","sq","sr","sv","sw","ta","te","th","ti","tl","uk","ur","uz","vi","wo","yo","zh"]

def gen_fresh_sitemap(site):
    """Generate a complete sitemap.xml with all existing lang pages + zh pages."""
    urls = []
    urls.append(f'  <url><loc>https://{site}/</loc><lastmod>{TODAY}</lastmod><priority>1.0</priority></url>')
    for lang in LANGS_ALL:
        if lang == "zh":
            continue  # zh pages added separately below
        urls.append(f'  <url><loc>https://{site}/{lang}.html</loc><lastmod>{TODAY}</lastmod><priority>0.8</priority></url>')
    # Add zh pages
    urls.append(f'  <url><loc>https://{site}/zh.html</loc><lastmod>{TODAY}</lastmod><priority>0.8</priority></url>')
    urls.append(f'  <url><loc>https://{site}/zh/</loc><lastmod>{TODAY}</lastmod><priority>0.7</priority></url>')
    for cc in COUNTRIES:
        urls.append(f'  <url><loc>https://{site}/zh/{cc}/</loc><lastmod>{TODAY}</lastmod><priority>0.7</priority></url>')
    for sp in SUBPAGES:
        urls.append(f'  <url><loc>https://{site}/zh/{sp}/</loc><lastmod>{TODAY}</lastmod><priority>0.6</priority></url>')

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{chr(10).join(urls)}
</urlset>
"""

def gen_zh_entries(site):
    """Generate sitemap XML entries for all Chinese pages."""
    entries = []
    # Homepage zh.html
    entries.append(f"  <url><loc>https://{site}/zh.html</loc><lastmod>{TODAY}</lastmod><priority>0.8</priority></url>")
    # Language index
    entries.append(f"  <url><loc>https://{site}/zh/</loc><lastmod>{TODAY}</lastmod><priority>0.7</priority></url>")
    # Country pages
    for cc in COUNTRIES:
        entries.append(f"  <url><loc>https://{site}/zh/{cc}/</loc><lastmod>{TODAY}</lastmod><priority>0.7</priority></url>")
    # Info pages
    for sp in SUBPAGES:
        entries.append(f"  <url><loc>https://{site}/zh/{sp}/</loc><lastmod>{TODAY}</lastmod><priority>0.6</priority></url>")
    return "\n".join(entries)

def update_sitemap(site):
    docroot = DOCROOT_OVERRIDES.get(site, f"{HOME}/{site}")
    print(f"\n=== {site} ===")

    content = cpanel_get_file(f"{docroot}/sitemap.xml")
    if content is None:
        print("  SKIP: no sitemap.xml found")
        return 0, 1

    # Check if zh pages already in sitemap
    if f"/{site}/zh" in content or "/zh.html" in content:
        print("  SKIP: zh pages already in sitemap")
        return 1, 0

    zh_entries = gen_zh_entries(site)

    # Insert before </urlset> (handle whitespace variations)
    if "</urlset>" in content:
        content = content.replace("</urlset>", f"\n{zh_entries}\n</urlset>")
    else:
        # If we can't parse the existing sitemap, generate a fresh one with zh pages
        print("  WARN: generating fresh sitemap (couldn't parse existing)")
        content = gen_fresh_sitemap(site)
        if not content:
            print("  ERR: couldn't generate sitemap")
            return 0, 1

    if cpanel_upload(content.encode("utf-8"), "sitemap.xml", docroot):
        print(f"  OK: added 10 zh pages to sitemap")
        return 1, 0
    return 0, 1

if __name__ == "__main__":
    sites = sys.argv[1:] if len(sys.argv) > 1 else SITES
    total_ok = total_err = 0
    for site in sites:
        ok, err = update_sitemap(site)
        total_ok += ok
        total_err += err
        time.sleep(0.3)
    print(f"\nTotal: {total_ok} OK, {total_err} errors")
