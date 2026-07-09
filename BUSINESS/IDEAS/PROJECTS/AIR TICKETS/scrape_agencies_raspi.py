#!/usr/bin/env python3
"""
Scrape 2,968 Romanian travel agencies from SITUR list.
No tokens. Pure HTTP. 30 parallel workers. ~10 min.

What it extracts from each agency website:
- Services: flights, vacations, corporate, tours, transfers, insurance, car rental
- Capabilities: online booking form, API/B2B/affiliate/reseller mentions, GDS integration
- Technical: RSS feeds, sitemaps, tech stack (WordPress/Wix/Shopify/GDS)
- Contact: phone numbers, extra emails beyond SITUR, social media links
- Meta: page title, HTTP status, final URL after redirects

Run: python3 /opt/ACTIVE/FLIGHTS/scrape_agencies.py
Input: /opt/ACTIVE/FLIGHTS/agentii_turistice_clean.csv (2,968 agencies)
Output: /opt/ACTIVE/FLIGHTS/agentii_scraped.csv (28 columns)
"""
import csv
import re
import time
import logging
import requests
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor, as_completed

SRC = "/opt/ACTIVE/FLIGHTS/agentii_turistice_clean.csv"
DST = "/opt/ACTIVE/FLIGHTS/agentii_scraped.csv"
LOG = "/opt/ACTIVE/FLIGHTS/logs/scrape.log"
TIMEOUT = 8
MAX_WORKERS = 30
UA = "Mozilla/5.0 (X11; Linux aarch64) AppleWebKit/537.36 Chrome/125.0"
HDRS = {"User-Agent": UA, "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8"}

logging.basicConfig(filename=LOG, level=logging.INFO,
                    format="%(asctime)s %(message)s")

# Service detection patterns
PATTERNS = {
    "flights":    re.compile(r"bilete?\s*(?:de\s*)?avion|flight|airline|zbor|charter", re.I),
    "vacations":  re.compile(r"vacan[tț][aă]|sejur|all\s*inclusive|litoral|exotic", re.I),
    "corporate":  re.compile(r"corporate|business\s*travel|mice|teambuilding", re.I),
    "tours":      re.compile(r"circuit|excursie|tour|ghid|guide|city.?break", re.I),
    "transfers":  re.compile(r"transfer|airport|shuttle|transport", re.I),
    "insurance":  re.compile(r"asigur[aă]r|insurance|travel.protect", re.I),
    "car_rental": re.compile(r"rent.?a.?car|[iî]nchiri|car.?rental|auto", re.I),
}
PAT_BOOKING = re.compile(r"rezer[vw]|book(?:ing)?|cump[aă]r|checkout", re.I)
PAT_API = re.compile(r"\bapi\b|affiliate|afiliere|partener|partner|b2b|reseller|distributor", re.I)
PAT_GDS = re.compile(r"amadeus|sabre|galileo|travelport|worldspan|\bgds\b|\biata\b", re.I)
PAT_RSS = re.compile(r'(?:href|src)=["\x27]([^"\x27]*(?:rss|feed|atom)[^"\x27]*)["\x27]', re.I)
PAT_SOCIAL = re.compile(r'href=["\x27]([^"\x27]*(?:facebook|instagram|linkedin|youtube|tiktok|twitter|x)\.com[^"\x27]*)["\x27]', re.I)
PAT_PHONE = re.compile(r"(?:0|\+40)\s*[237]\d[\d\s\-.]{6,12}")
PAT_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PAT_TITLE = re.compile(r"<title[^>]*>([^<]+)</title>", re.I)

TECH_MARKERS = [
    ("wp-content", "WordPress"), ("woocommerce", "WooCommerce"),
    ("shopify", "Shopify"), ("wix.com", "Wix"),
    ("joomla", "Joomla"), ("squarespace", "Squarespace"),
    ("amadeus", "GDS-Amadeus"), ("travelport", "GDS-Travelport"),
    ("sabre", "GDS-Sabre"),
]

FIELDS = [
    "nr_licenta", "operator", "agentie", "email", "judet", "tip",
    "site_web", "status", "http_code", "final_url", "page_title",
    "flights", "vacations", "corporate", "tours", "transfers",
    "insurance", "car_rental", "has_booking", "has_api_b2b", "has_gds",
    "tech_stack", "rss_feeds", "has_sitemap", "robots_sitemaps",
    "social_media", "phones", "extra_emails",
]


def norm_url(url):
    if not url or not url.strip():
        return None
    url = url.strip().rstrip("/")
    if not url.startswith("http"):
        url = "https://" + url
    return url


def extract(html):
    low = html.lower()
    r = {}
    for k, pat in PATTERNS.items():
        r[k] = bool(pat.search(low))
    r["has_booking"] = bool(PAT_BOOKING.search(low))
    r["has_api_b2b"] = bool(PAT_API.search(low))
    r["has_gds"] = bool(PAT_GDS.search(low))
    r["rss_feeds"] = "; ".join(set(PAT_RSS.findall(html)[:3]))
    r["has_sitemap"] = "/sitemap" in low
    r["social_media"] = "; ".join(set(PAT_SOCIAL.findall(html)[:5]))
    techs = [name for marker, name in TECH_MARKERS if marker in low]
    r["tech_stack"] = ", ".join(techs)
    phones = PAT_PHONE.findall(html)
    r["phones"] = "; ".join(set(p.strip() for p in phones[:3]))
    emails = PAT_EMAIL.findall(html)
    r["extra_emails"] = "; ".join(
        set(e for e in emails[:5] if "wix" not in e and "sentry" not in e))
    title = PAT_TITLE.search(html)
    r["page_title"] = title.group(1).strip()[:120] if title else ""
    return r


def check_robots(base):
    try:
        x = requests.get(base + "/robots.txt", headers=HDRS, timeout=5)
        if x.ok:
            sm = re.findall(r"Sitemap:\s*(\S+)", x.text, re.I)
            return "; ".join(sm[:3])
    except Exception:
        pass
    return ""


def scrape(row):
    url = norm_url(row.get("site_web", ""))
    info = {
        "nr_licenta": row.get("nr_licenta", ""),
        "operator": row.get("operator_economic", ""),
        "agentie": row.get("denumire_agentie", ""),
        "email": row.get("email", ""),
        "judet": row.get("judet", ""),
        "tip": row.get("tip_agentie", ""),
        "site_web": url or "",
        "status": "no_url",
        "http_code": "",
    }
    if not url:
        return info
    try:
        r = requests.get(url, headers=HDRS, timeout=TIMEOUT,
                         allow_redirects=True)
        info["http_code"] = r.status_code
        info["final_url"] = r.url
        info["status"] = "ok" if r.ok else "http_%d" % r.status_code
        if r.ok and len(r.text) > 500:
            info.update(extract(r.text))
            base = "%s://%s" % (urlparse(r.url).scheme, urlparse(r.url).netloc)
            info["robots_sitemaps"] = check_robots(base)
        else:
            info["status"] = "empty"
    except requests.exceptions.Timeout:
        info["status"] = "timeout"
    except requests.exceptions.SSLError:
        info["status"] = "ssl_error"
        try:
            r = requests.get(url.replace("https:", "http:"),
                             headers=HDRS, timeout=TIMEOUT)
            if r.ok:
                info["status"] = "ok_http"
                info["http_code"] = r.status_code
                info.update(extract(r.text))
        except Exception:
            pass
    except Exception as e:
        info["status"] = "err_%s" % type(e).__name__
    return info


def main():
    with open(SRC, encoding="utf-8") as f:
        agencies = list(csv.DictReader(f))
    total = len(agencies)
    print("Scraping %d agencies with %d workers..." % (total, MAX_WORKERS))

    done = ok = api = gds = bk = fl = 0
    with open(DST, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            futs = {pool.submit(scrape, row): row for row in agencies}
            for fut in as_completed(futs):
                res = fut.result()
                w.writerow(res)
                done += 1
                s = res.get("status", "")
                if s.startswith("ok"): ok += 1
                if res.get("has_api_b2b") is True: api += 1
                if res.get("has_gds") is True: gds += 1
                if res.get("has_booking") is True: bk += 1
                if res.get("flights") is True: fl += 1
                if done % 100 == 0:
                    f.flush()
                    print("  [%d/%d] %d%% | OK:%d Flights:%d Book:%d API:%d GDS:%d"
                          % (done, total, done*100//total, ok, fl, bk, api, gds))
                    logging.info("%d/%d ok=%d api=%d gds=%d" % (done, total, ok, api, gds))

    print("\nDONE: %d scraped -> %s" % (done, DST))
    print("Reachable: %d | Flights: %d | Booking: %d | API/B2B: %d | GDS: %d"
          % (ok, fl, bk, api, gds))


if __name__ == "__main__":
    main()
