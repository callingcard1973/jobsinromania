#!/usr/bin/env python3
"""Fix baneasa39.com .htaccess: clean corruption + add 301 redirects for broken links."""
import requests
import urllib.parse
requests.packages.urllib3.disable_warnings()

HOST = "https://nl1-cl8-ats1.a2hosting.com:2083"
USER = "loaiidil"
TOKEN = "T7ZV9TZJZ22E0YCEOUST8AAGQGQTZVU1"
H = {"Authorization": f"cpanel {USER}:{TOKEN}"}
DIR = f"/home/{USER}/baneasa39.com"

# Read current .htaccess
r = requests.get(f"{HOST}/execute/Fileman/get_file_content?dir={DIR}&file=.htaccess", headers=H, verify=False)
old = r.json().get("data", {}).get("content", "")

# Keep everything before the corruption (find last valid line)
lines = old.split("\n")
clean_lines = []
for line in lines:
    try:
        line.encode("ascii")
        clean_lines.append(line)
    except UnicodeEncodeError:
        break  # Stop at first corrupted line

# Add redirects for broken pages
redirects = """
# BEGIN BROKEN LINK REDIRECTS
RewriteEngine On
RewriteRule ^teren-1628-mp-strada-baneasa-bucuresti-zona-urbanism-l2a-2-4-mil-eur/?$ / [R=301,L]
RewriteRule ^reincadrare-urbanistica-favorabila-dezvoltari-de-tip-p5-6e/?$ / [R=301,L]
RewriteRule ^indicatori-pentru-constructii-cut-pot/?$ / [R=301,L]
RewriteRule ^pasaj_baneasa_2025/?$ / [R=301,L]
RewriteRule ^for-sale-2-land-lots-totaling-2400-sqm-with-a-frontage-of-60m-60x40/?$ / [R=301,L]
RewriteRule ^propunere-de-vanzare-etaj-bloc-in-orasul-motru-jud-gorj/?$ / [R=301,L]
RewriteRule ^alte-investitii/?$ / [R=301,L]
RewriteRule ^teren-652-mp-e-strada-baneasa-bucuresti-786-000-euro/?$ / [R=301,L]
RewriteRule ^vand-teren-2400-mp-linga-phoenicia-grand-hotel/?$ / [R=301,L]
RewriteRule ^terrain-a-vendre-a-baneasa-bucarest-ideal-pour-lotissement-association-ou-developpement/?$ / [R=301,L]
RewriteRule ^category/indicatori-urbanistici/?$ / [R=301,L]
RewriteRule ^category/indicatori-urbanistici-cut/?$ / [R=301,L]
RewriteRule ^category/pot/?$ / [R=301,L]
RewriteRule ^category/romaneste/?$ / [R=301,L]
RewriteRule ^category/ro/?$ / [R=301,L]
RewriteRule ^category/sectorul-1/?$ / [R=301,L]
RewriteRule ^category/english/?$ / [R=301,L]
RewriteRule ^category/oportunitate/?$ / [R=301,L]
RewriteRule ^category/francais/?$ / [R=301,L]
# END BROKEN LINK REDIRECTS

# BEGIN WordPress
<IfModule mod_rewrite.c>
RewriteEngine On
RewriteRule .* - [E=HTTP_AUTHORIZATION:%{HTTP:Authorization}]
RewriteBase /
RewriteRule ^index\\.php$ - [L]
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_FILENAME} !-d
RewriteRule . /index.php [L]
</IfModule>
# END WordPress
"""

new_htaccess = "\n".join(clean_lines) + "\n" + redirects

# Write back via cPanel API
payload = {
    "dir": DIR,
    "file": ".htaccess",
    "content": new_htaccess,
}
r = requests.post(f"{HOST}/execute/Fileman/save_file_content", headers=H, data=payload, verify=False)
print(f"Save: {r.status_code}")
if r.status_code == 200:
    result = r.json()
    if result.get("errors"):
        print(f"Errors: {result['errors']}")
    else:
        print("htaccess fixed!")
        print(f"Clean lines: {len(clean_lines)}, added {redirects.count('RewriteRule')} redirects")
