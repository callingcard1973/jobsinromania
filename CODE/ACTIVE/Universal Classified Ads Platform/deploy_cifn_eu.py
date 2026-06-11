#!/usr/bin/env python3
"""Deploy classified ads platform to cifn.eu domain on A2 Hosting.

Steps:
1. Create ads.cifn.eu subdomain via cPanel API
2. Install WordPress via cPanel WP toolkit (or Softaculous)
3. Generate WP application password
4. Deploy classified-ads-bridge plugin via Claude API
5. Create WP pages (/post-ad/, /my-ads/) with shortcodes
6. Configure Caddy reverse proxy on raspibig for api.cifn.eu → FastAPI

Usage:
    python deploy_cifn_eu.py --setup-subdomain
    python deploy_cifn_eu.py --install-plugin
    python deploy_cifn_eu.py --create-pages
    python deploy_cifn_eu.py --setup-caddy
    python deploy_cifn_eu.py --all
"""
import argparse
import base64
import json
import os
import sys
import requests

CPANEL_HOST = "nl1-cl8-ats1.a2hosting.com:2083"
CPANEL_USER = "loaiidil"
CPANEL_TOKEN = os.environ.get("A2_CPANEL_TOKEN", "K9ATCMHPKVSKUV2M97447JLY45EH29KQ")
CPANEL_BASE = f"https://{CPANEL_USER}:{CPANEL_TOKEN}@{CPANEL_HOST}/execute"

SUBDOMAIN = "ads"
DOMAIN = "cifn.eu"
FULL_DOMAIN = f"{SUBDOMAIN}.{DOMAIN}"
DOCROOT = f"/home/{CPANEL_USER}/{FULL_DOMAIN}"

# WP credentials (set after WP install)
WP_URL = f"https://{FULL_DOMAIN}"
WP_USER = os.environ.get("WP_CIFN_USER", "admin")
WP_PASS = os.environ.get("WP_CIFN_PASS", "")

# Claude API plugin key (shared across all sites)
CLAUDE_KEY = os.environ.get("WP_CLAUDE_KEY", "oipa-claude-2026-xK9mP2vL")

# FastAPI backend URL
API_URL = os.environ.get("CLASSIFIED_API_URL", "https://api.cifn.eu")

# raspibig SSH
RASPIBIG = "192.168.100.21"


def cpanel_api(module, func, params=None):
    """Call cPanel UAPI."""
    url = f"{CPANEL_BASE}/{module}/{func}"
    r = requests.get(url, params=params or {}, timeout=30)
    r.raise_for_status()
    return r.json()


def setup_subdomain():
    """Create ads.cifn.eu subdomain on A2."""
    print(f"Creating subdomain {FULL_DOMAIN}...")
    result = cpanel_api("SubDomain", "addsubdomain", {
        "domain": SUBDOMAIN,
        "rootdomain": DOMAIN,
        "dir": DOCROOT,
    })
    if result.get("status") == 1:
        print(f"  OK: {FULL_DOMAIN} created, docroot={DOCROOT}")
    else:
        print(f"  Result: {result}")
    return result


def install_plugin():
    """Deploy classified-ads-bridge plugin to WP via Claude API."""
    if not WP_PASS:
        print("ERROR: Set WP_CIFN_PASS env var (WP application password)")
        return False

    plugin_dir = os.path.join(os.path.dirname(__file__), "wordpress-plugin", "classified-ads-bridge")
    main_php = os.path.join(plugin_dir, "classified-ads-bridge.php")
    js_file = os.path.join(plugin_dir, "js", "app.js")

    if not os.path.exists(main_php):
        print(f"ERROR: Plugin not found at {plugin_dir}")
        return False

    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "X-Claude-Key": CLAUDE_KEY,
        "Content-Type": "application/json",
    }

    # Upload PHP file via Claude API plugin
    with open(main_php, "r", encoding="utf-8") as f:
        php_content = f.read()

    print(f"Uploading plugin PHP to {WP_URL}...")
    r = requests.post(f"{WP_URL}/?claude_api=upload", headers=headers, json={
        "path": "wp-content/plugins/classified-ads-bridge/classified-ads-bridge.php",
        "content": php_content,
    }, timeout=30)
    print(f"  PHP upload: {r.status_code} {r.text[:100]}")

    # Upload JS file
    with open(js_file, "r", encoding="utf-8") as f:
        js_content = f.read()

    print(f"Uploading plugin JS to {WP_URL}...")
    r = requests.post(f"{WP_URL}/?claude_api=upload", headers=headers, json={
        "path": "wp-content/plugins/classified-ads-bridge/js/app.js",
        "content": js_content,
    }, timeout=30)
    print(f"  JS upload: {r.status_code} {r.text[:100]}")

    # Activate plugin
    print("Activating plugin...")
    r = requests.post(f"{WP_URL}/?claude_api=activate_plugin", headers=headers, json={
        "plugin": "classified-ads-bridge/classified-ads-bridge.php",
    }, timeout=30)
    print(f"  Activate: {r.status_code} {r.text[:100]}")

    return True


def create_pages():
    """Create WP pages with classified ads shortcodes."""
    if not WP_PASS:
        print("ERROR: Set WP_CIFN_PASS env var")
        return False

    auth = base64.b64encode(f"{WP_USER}:{WP_PASS}".encode()).decode()
    headers = {
        "Authorization": f"Basic {auth}",
        "Content-Type": "application/json",
    }

    pages = [
        {"title": "Post Ad", "slug": "post-ad", "content": "[classified_ads_form]"},
        {"title": "My Ads", "slug": "my-ads", "content": "[my_classified_ads]"},
    ]

    for page in pages:
        print(f"Creating page: {page['title']} ({page['slug']})...")
        r = requests.post(f"{WP_URL}/wp-json/wp/v2/pages", headers=headers, json={
            "title": page["title"],
            "slug": page["slug"],
            "content": page["content"],
            "status": "publish",
        }, timeout=15)
        if r.status_code in (200, 201):
            data = r.json()
            print(f"  OK: {data.get('link', data.get('id'))}")
        else:
            print(f"  Error: {r.status_code} {r.text[:200]}")

    # Configure plugin settings via WP options API (using Claude run_php)
    print("Configuring plugin settings...")
    settings_php = f"""
    update_option('cab_api_url', '{API_URL}');
    update_option('cab_fb_app_id', '');
    update_option('cab_fb_app_secret', '');
    update_option('cab_price_cents', 500);
    update_option('cab_currency', 'usd');
    update_option('cab_stripe_pk', '');
    echo 'Settings saved';
    """
    r = requests.post(f"{WP_URL}/?claude_api=run_php", headers={
        "Authorization": f"Basic {auth}",
        "X-Claude-Key": CLAUDE_KEY,
        "Content-Type": "application/json",
    }, json={"code_b64": base64.b64encode(settings_php.encode()).decode()}, timeout=15)
    print(f"  Settings: {r.status_code} {r.text[:100]}")

    return True


def setup_caddy():
    """Print Caddy config for api.cifn.eu reverse proxy on raspibig."""
    config = f"""
# Add to Caddyfile on raspibig (192.168.100.21)
# Reverse proxy api.cifn.eu → classified ads FastAPI on :8000

api.cifn.eu {{
    reverse_proxy localhost:8000
    encode gzip

    # CORS for WP frontend
    @origin header Origin https://ads.cifn.eu
    header @origin Access-Control-Allow-Origin https://ads.cifn.eu
    header @origin Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS"
    header @origin Access-Control-Allow-Headers "Authorization, Content-Type"
}}

# Restart Caddy after editing:
# ssh tudor@192.168.100.21 'sudo systemctl reload caddy'
"""
    print(config)
    print("\nTo apply on raspibig:")
    print(f'  plink -batch -pw "bucare" tudor@{RASPIBIG} "sudo tee -a /etc/caddy/Caddyfile" < caddy_config.txt')
    print(f'  plink -batch -pw "bucare" tudor@{RASPIBIG} "sudo systemctl reload caddy"')
    return True


def main():
    parser = argparse.ArgumentParser(description="Deploy classified ads to cifn.eu")
    parser.add_argument("--setup-subdomain", action="store_true", help="Create ads.cifn.eu on A2")
    parser.add_argument("--install-plugin", action="store_true", help="Deploy WP plugin")
    parser.add_argument("--create-pages", action="store_true", help="Create WP pages with shortcodes")
    parser.add_argument("--setup-caddy", action="store_true", help="Print Caddy config for api.cifn.eu")
    parser.add_argument("--all", action="store_true", help="Run all steps")
    args = parser.parse_args()

    if args.all or args.setup_subdomain:
        setup_subdomain()
    if args.all or args.install_plugin:
        install_plugin()
    if args.all or args.create_pages:
        create_pages()
    if args.all or args.setup_caddy:
        setup_caddy()

    if not any([args.setup_subdomain, args.install_plugin, args.create_pages, args.setup_caddy, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
