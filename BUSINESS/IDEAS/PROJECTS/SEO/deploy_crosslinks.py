"""Deploy cross-linking section to all 15 InterJob job sites.

Adds a "InterJob European Network" section to each site's index.html
with links to all other sites in the network. Injects before <footer>
or before </body>. Idempotent — checks for id="network-sites" before
injecting to avoid duplicates.
"""
import urllib.request, urllib.parse, json, ssl, sys, time, re

API_TOKEN = "MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U"
HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
HOME = "/home/loaiidil"

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

DOCROOT_OVERRIDES = {
    "warehouseworkers.eu": f"{HOME}/public_html/warehouseworkers.eu",
}

# ── Site definitions ──────────────────────────────────────────────────────────
SITES = {
    "careworkers.eu": {
        "title": "Care Workers EU",
        "desc": "Healthcare & elderly care jobs in Europe",
        "icon": "🏥",
    },
    "factoryjobs.eu": {
        "title": "Factory Jobs EU",
        "desc": "Factory & manufacturing jobs in Europe",
        "icon": "🏭",
    },
    "buildjobs.eu": {
        "title": "Build Jobs EU",
        "desc": "Construction & building jobs in Europe",
        "icon": "🏗️",
    },
    "electricjobs.eu": {
        "title": "Electric Jobs EU",
        "desc": "Electrical & technical jobs in Europe",
        "icon": "⚡",
    },
    "farmworkers.eu": {
        "title": "Farm Workers EU",
        "desc": "Agricultural & farming jobs in Europe",
        "icon": "🌾",
    },
    "horecaworkers.eu": {
        "title": "Horeca Workers EU",
        "desc": "Hotel, restaurant & catering jobs in Europe",
        "icon": "🍽️",
    },
    "meatworkers.eu": {
        "title": "Meat Workers EU",
        "desc": "Meat processing & food industry jobs in Europe",
        "icon": "🥩",
    },
    "mechanicjobs.eu": {
        "title": "Mechanic Jobs EU",
        "desc": "Mechanic & automotive jobs in Europe",
        "icon": "🔧",
    },
    "warehouseworkers.eu": {
        "title": "Warehouse Workers EU",
        "desc": "Warehouse & logistics jobs in Europe",
        "icon": "📦",
    },
    "aluminumrecyclehub.com": {
        "title": "Aluminum Recycle Hub",
        "desc": "Recycling industry jobs in Europe",
        "icon": "♻️",
    },
    "expatsinromania.org": {
        "title": "Expats in Romania",
        "desc": "Jobs and community for expats in Romania",
        "icon": "🌍",
    },
    "interjob.ro": {
        "title": "InterJob Romania",
        "desc": "International job recruitment platform for Europe",
        "icon": "🌐",
    },
    "mivromania.info": {
        "title": "MIV Romania",
        "desc": "Jobs and opportunities in Romania",
        "icon": "🇷🇴",
    },
    "mivromania.online": {
        "title": "MIV Romania Online",
        "desc": "Digital platform for European job seekers",
        "icon": "💻",
    },
    "nepalezi.com": {
        "title": "Nepalezi",
        "desc": "Jobs for Nepali workers in Europe",
        "icon": "🏔️",
    },
}

# ── cPanel helpers ────────────────────────────────────────────────────────────
def cpanel_get_file(remote_path):
    dir_part = remote_path.rsplit("/", 1)[0]
    file_part = remote_path.rsplit("/", 1)[1]
    url = (
        f"{HOST}/execute/Fileman/get_file_content"
        f"?dir={urllib.parse.quote(dir_part)}"
        f"&file={urllib.parse.quote(file_part)}"
    )
    req = urllib.request.Request(
        url, headers={"Authorization": f"cpanel {USER}:{API_TOKEN}"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=30, context=CTX)
        data = json.loads(r.read())
        return data.get("data", {}).get("content", "")
    except Exception as e:
        print(f"  ERR downloading {remote_path}: {e}")
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
        f"Content-Type: text/html\r\n\r\n"
    ).encode("utf-8") + content_bytes + f"\r\n--{boundary}--\r\n".encode("utf-8")

    url = f"{HOST}/execute/Fileman/upload_files"
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"cpanel {USER}:{API_TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    for attempt in range(3):
        try:
            urllib.request.urlopen(req, timeout=30, context=CTX)
            return True
        except Exception as e:
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                print(f"  ERR upload {remote_dir}/{filename}: {e}")
                return False


# ── Cross-link section builder ────────────────────────────────────────────────
def build_network_section(current_site):
    """Build the HTML for the network cross-link section, excluding current site."""
    cards = ""
    for domain, meta in SITES.items():
        if domain == current_site:
            continue
        icon = meta["icon"]
        title = meta["title"]
        desc = meta["desc"]
        cards += f"""
      <a href="https://{domain}/" target="_blank" rel="noopener"
         style="display:block;background:#1e293b;border:1px solid #334155;border-radius:10px;
                padding:16px 18px;text-decoration:none;color:inherit;
                transition:border-color .2s,transform .2s;cursor:pointer"
         onmouseover="this.style.borderColor='#10b981';this.style.transform='translateY(-2px)'"
         onmouseout="this.style.borderColor='#334155';this.style.transform='translateY(0)'">
        <div style="font-size:1.5rem;margin-bottom:6px">{icon}</div>
        <div style="font-weight:700;font-size:.95rem;color:#f1f5f9;margin-bottom:4px">{title}</div>
        <div style="font-size:.82rem;color:#94a3b8;line-height:1.4">{desc}</div>
        <div style="margin-top:8px;font-size:.78rem;color:#10b981;font-weight:600">{domain} →</div>
      </a>"""

    section = f"""
<!-- InterJob Network Cross-Links -->
<section id="network-sites"
  style="background:#0f172a;color:#f1f5f9;padding:50px 20px;margin-top:40px">
  <div style="max-width:1100px;margin:0 auto">
    <h2 style="text-align:center;font-size:1.7rem;font-weight:800;
               color:#f1f5f9;margin:0 0 8px">
      InterJob European Network
    </h2>
    <p style="text-align:center;color:#94a3b8;font-size:.95rem;margin:0 0 32px">
      Explore all our specialized job portals across Europe
    </p>
    <div style="display:grid;
                grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
                gap:14px">
{cards}
    </div>
    <p style="text-align:center;margin-top:28px;font-size:.85rem;color:#64748b">
      <a href="https://interjob.ro/apply.html"
         style="color:#10b981;text-decoration:none;font-weight:600">
        Apply for a job now →
      </a>
    </p>
  </div>
</section>
"""
    return section


# ── Inject into HTML ──────────────────────────────────────────────────────────
def inject_crosslinks(html, site):
    """Inject network section before <footer> or before </body>. Idempotent."""
    if 'id="network-sites"' in html:
        print("  SKIP: network-sites section already present")
        return html, False

    section = build_network_section(site)

    if re.search(r'<footer[\s>]', html, re.I):
        html = re.sub(r'(<footer[\s>])', section + r'\1', html, count=1, flags=re.I)
    elif '</body>' in html:
        html = html.replace('</body>', section + '\n</body>', 1)
    else:
        html = html + '\n' + section

    return html, True


# ── Per-site deploy ───────────────────────────────────────────────────────────
def deploy_site(site):
    meta = SITES[site]
    docroot = DOCROOT_OVERRIDES.get(site, f"{HOME}/{site}")
    print(f"\n=== {site} ({meta['title']}) ===")

    content = cpanel_get_file(f"{docroot}/index.html")
    if content is None:
        print("  SKIP: could not download index.html")
        return 0, 1

    html, changed = inject_crosslinks(content, site)
    if not changed:
        return 1, 0  # already done, count as OK

    if cpanel_upload(html.encode("utf-8"), "index.html", docroot):
        print("  OK: injected network-sites section")
        return 1, 0

    return 0, 1


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    sites = sys.argv[1:] if len(sys.argv) > 1 else list(SITES.keys())
    total_ok = total_err = 0
    for site in sites:
        if site not in SITES:
            print(f"SKIP {site}: not configured")
            continue
        ok, err = deploy_site(site)
        total_ok += ok
        total_err += err
        time.sleep(0.5)
    print(f"\nDone: {total_ok} OK, {total_err} errors across {len(sites)} sites")
