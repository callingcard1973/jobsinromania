#!/usr/bin/env python3
"""
Deploy cataloage HTML pe A2 Hosting via cPanel API.
Ruleaza LOCAL (nu pe raspibig) — fisierele HTML trebuie descarcate intai.

Folosire:
  1. Ruleaza generate_catalogs_raspibig.py pe raspibig
  2. scp -r tudor@192.168.100.21:/tmp/output/ ./output/
  3. python deploy_to_a2.py
"""
import os, sys, json, base64, requests
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent / "output"

# cPanel API — A2 Hosting
CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com"
CPANEL_USER = "loaiidil"
CPANEL_PORT = 2083

# Domenii si docroot pe A2 (format: ~/domeniu/)
DOCROOTS = {
    "factoryjobs.eu": "factoryjobs.eu",
    "buildjobs.eu": "buildjobs.eu",
    "careworkers.eu": "careworkers.eu",
    "electricjobs.eu": "electricjobs.eu",
    "farmworkers.eu": "farmworkers.eu",
    "horecaworkers.eu": "horecaworkers.eu",
    "meatworkers.eu": "meatworkers.eu",
    "mechanicjobs.eu": "mechanicjobs.eu",
    "warehouseworkers.eu": "warehouseworkers.eu",
}


def upload_file_cpanel(session, api_token, remote_dir, filename, content):
    """Upload un fisier via cPanel UAPI."""
    url = f"https://{CPANEL_HOST}:{CPANEL_PORT}/execute/Fileman/save_file_content"
    data = {
        "file": filename,
        "dir": remote_dir,
        "content": content,
    }
    headers = {"Authorization": f"cpanel {CPANEL_USER}:{api_token}"}
    r = session.post(url, data=data, headers=headers, timeout=30)
    return r.status_code == 200


def deploy_domain(domain_key, api_token):
    """Deploy toate fisierele unui domeniu pe A2."""
    domain_dir = OUTPUT_DIR / domain_key
    if not domain_dir.exists():
        print(f"  SKIP {domain_key} — nu exista output")
        return 0

    docroot = DOCROOTS.get(domain_key)
    if not docroot:
        print(f"  SKIP {domain_key} — docroot necunoscut")
        return 0

    session = requests.Session()
    uploaded = 0

    for root, dirs, files in os.walk(domain_dir):
        for f in files:
            local_path = Path(root) / f
            # Calculeaza calea relativa pe server
            rel = local_path.relative_to(domain_dir)
            remote_dir = f"/home/{CPANEL_USER}/{docroot}/{rel.parent}"
            if str(rel.parent) == ".":
                remote_dir = f"/home/{CPANEL_USER}/{docroot}"

            content = local_path.read_text(encoding="utf-8")
            ok = upload_file_cpanel(session, api_token, remote_dir, f, content)
            if ok:
                uploaded += 1
            else:
                print(f"    EROARE: {rel}")

    return uploaded


def main():
    if not OUTPUT_DIR.exists():
        print(f"EROARE: {OUTPUT_DIR} nu exista. Ruleaza intai generate pe raspibig.")
        sys.exit(1)

    # Citeste API token din env sau fisier
    api_token = os.environ.get("CPANEL_API_TOKEN", "")
    if not api_token:
        token_file = Path(__file__).parent / ".cpanel_token"
        if token_file.exists():
            api_token = token_file.read_text().strip()
    if not api_token:
        print("EROARE: Seteaza CPANEL_API_TOKEN sau creeaza .cpanel_token")
        print("Genereaza token: cPanel -> Security -> Manage API Tokens")
        sys.exit(1)

    print("Deploy cataloage pe A2 Hosting")
    print(f"Host: {CPANEL_HOST}")
    print(f"User: {CPANEL_USER}")
    print()

    total = 0
    for domain_key in DOCROOTS:
        print(f"Deploy {domain_key}...")
        n = deploy_domain(domain_key, api_token)
        total += n
        print(f"  -> {n} fisiere uploadate")

    print(f"\nTotal: {total} fisiere deployate pe {len(DOCROOTS)} domenii")
    print("Verifica: https://factoryjobs.eu/no/ (exemplu)")


if __name__ == "__main__":
    main()
