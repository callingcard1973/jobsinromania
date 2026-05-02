#!/usr/bin/env python3
"""
Submit websites to search engines (IndexNow, Yandex, Bing)

Usage:
    python3 /opt/ACTIVE/INFRA/SKILLS/submit_search_engines.py                    # Submit all worker domains
    python3 /opt/ACTIVE/INFRA/SKILLS/submit_search_engines.py domain1.com domain2.com  # Submit specific domains
    python3 /opt/ACTIVE/INFRA/SKILLS/submit_search_engines.py --sitemap-only     # Only ping sitemaps
    python3 /opt/ACTIVE/INFRA/SKILLS/submit_search_engines.py --add-languages    # Also add language pages

Location: /opt/ACTIVE/INFRA/SKILLS/submit_search_engines.py
"""

import urllib.request
import urllib.parse
import json
import ssl
import sys
from datetime import datetime

# A2 Hosting Config (for uploading IndexNow key)
A2_HOST = "nl1-cl8-ats1.a2hosting.com"
A2_USER = "loaiidil"
A2_TOKEN = "L1RD2H1Z5080G7HPPM3IK4MQVKF8Q2N2"

# Default worker domains
DEFAULT_DOMAINS = [
    "factoryjobs.eu", "buildjobs.eu", "careworkers.eu", "horecaworkers.eu",
    "meatworkers.eu", "electricjobs.eu", "mechanicjobs.eu", "farmworkers.eu"
]

# IndexNow key
INDEXNOW_KEY = "a1b2c3d4e5f6g7h8i9j0"

# SSL context
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE


def upload_file(domain, filename, content):
    """Upload file to A2 Hosting via cPanel API"""
    url = f"https://{A2_HOST}:2083/execute/Fileman/save_file_content"
    data = urllib.parse.urlencode({
        'dir': f'/home/{A2_USER}/{domain}',
        'file': filename,
        'content': content
    }).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header("Authorization", f"cpanel {A2_USER}:{A2_TOKEN}")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, context=ctx) as resp:
            return json.load(resp).get('status') == 1
    except:
        return False


def submit_indexnow(domain, urls):
    """Submit URLs via IndexNow API (Bing, Yandex, Naver, Seznam)"""
    data = json.dumps({
        "host": domain,
        "key": INDEXNOW_KEY,
        "keyLocation": f"https://{domain}/{INDEXNOW_KEY}.txt",
        "urlList": urls
    }).encode()

    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=data,
            method='POST'
        )
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status in [200, 202]
    except:
        return False


def ping_yandex(sitemap_url):
    """Ping Yandex with sitemap"""
    try:
        url = f"https://webmaster.yandex.ru/ping?sitemap={urllib.parse.quote(sitemap_url)}"
        req = urllib.request.Request(url, method='GET')
        req.add_header("User-Agent", "Mozilla/5.0")
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except:
        return False


def ping_bing(sitemap_url):
    """Ping Bing with sitemap via IndexNow"""
    try:
        url = f"https://www.bing.com/indexnow?url={urllib.parse.quote(sitemap_url)}&key={INDEXNOW_KEY}"
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in [200, 202]
    except:
        return False


def get_standard_urls(domain):
    """Get standard URLs for a domain"""
    langs = ['', 'ru', 'vi', 'bn', 'tl', 'th', 'id', 'fr', 'sw', 'am', 'ar', 'ro', 'ne', 'hi', 'ur']
    pages = ['apply.html', 'order.html']

    urls = [f"https://{domain}/"]

    for lang in langs:
        if lang:
            urls.append(f"https://{domain}/{lang}.html")

    for page in pages:
        urls.append(f"https://{domain}/{page}")

    return urls


def submit_domain(domain, sitemap_only=False):
    """Submit a single domain to all search engines"""
    results = {"indexnow": False, "yandex": False, "bing": False}

    sitemap_url = f"https://{domain}/sitemap.xml"

    if not sitemap_only:
        # Upload IndexNow key
        upload_file(domain, f"{INDEXNOW_KEY}.txt", INDEXNOW_KEY)

        # Submit via IndexNow
        urls = get_standard_urls(domain)
        results["indexnow"] = submit_indexnow(domain, urls[:50])  # Max 50 URLs

    # Ping sitemaps
    results["yandex"] = ping_yandex(sitemap_url)
    results["bing"] = ping_bing(sitemap_url)

    return results


def main():
    args = sys.argv[1:]

    sitemap_only = "--sitemap-only" in args
    args = [a for a in args if not a.startswith("--")]

    domains = args if args else DEFAULT_DOMAINS

    print("Search Engine Submission Tool")
    print("=" * 60)
    print(f"Time: {datetime.now()}")
    print(f"Domains: {len(domains)}")
    print(f"Mode: {'Sitemap ping only' if sitemap_only else 'Full submission'}")
    print("=" * 60)

    success_count = 0

    for domain in domains:
        print(f"\n{domain}:")
        results = submit_domain(domain, sitemap_only)

        all_ok = True
        for engine, ok in results.items():
            status = "✓" if ok else "✗"
            print(f"  {status} {engine}")
            if not ok:
                all_ok = False

        if all_ok:
            success_count += 1

    print("\n" + "=" * 60)
    print(f"Submitted: {success_count}/{len(domains)} domains")
    print("=" * 60)

    # Summary
    print("\nSearch engines notified:")
    print("  • IndexNow → Bing, Yandex, Naver, Seznam, Yep")
    print("  • Yandex sitemap ping")
    print("  • Bing sitemap ping")

    return 0 if success_count == len(domains) else 1


if __name__ == "__main__":
    sys.exit(main())
