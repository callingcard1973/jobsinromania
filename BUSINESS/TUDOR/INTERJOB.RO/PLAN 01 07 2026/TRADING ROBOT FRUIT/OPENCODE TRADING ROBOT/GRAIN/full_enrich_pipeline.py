#!/usr/bin/env python3
"""Full enrichment pipeline for producer/trader list by CAEN.

Phase 1: companies_clean (website, phone, address, email, sector)
Phase 2: scrape company websites + email-domain-guessed URLs for email/phone
Phase 3: verify + dedup + report

Usage:
  python GRAIN/full_enrich_pipeline.py                  # dry-run stats
  python GRAIN/full_enrich_pipeline.py --phase1         # companies_clean only
  python GRAIN/full_enrich_pipeline.py --phase2          # scrape websites (requires phase1 first)
  python GRAIN/full_enrich_pipeline.py --phase3          # verify + dedup
  python GRAIN/full_enrich_pipeline.py --all             # full pipeline
"""
import csv
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date

try:
    import psycopg2
except ImportError:
    psycopg2 = None

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import config as CFG

BASE_DIR = os.path.join(CFG.DATA, "producers_by_caen")
INPUT_CSV = os.path.join(BASE_DIR, "unified_all.csv")
PHASE1_OUT = os.path.join(BASE_DIR, "enriched_phase1.csv")
PHASE2_OUT = os.path.join(BASE_DIR, "enriched_phase2.csv")
FINAL_OUT = os.path.join(BASE_DIR, "enriched_final.csv")
REPORT = os.path.join(BASE_DIR, "enrich_report.md")

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64; cereale-enrich internal)"

GENERIC_EMAIL_PROVIDERS = {
    "gmail.com", "yahoo.com", "yahoo.ro", "yahoo.fr", "hotmail.com",
    "outlook.com", "live.com", "aol.com", "ymail.com", "mail.ru",
    "yandex.ru", "gmx.com", "gmx.net", "gmx.de", "protonmail.com",
    "zoho.com", "icloud.com", "me.com", "msn.com", "mail.com",
    "inbox.com", "fastmail.com", "web.de", "t-online.de", "online.de",
}

GARBAGE_DOMAINS = {
    "1.9.4", "2x-1024x683.webp", "wordpress.com", "blogspot.com",
    "blogspot.ro", "wix.com", "weebly.com",
}

DIRECTORY_DOMAINS = {
    "topfirme.com", "cautarefirme.ro", "firmania.ro", "firmeo.ro",
    "topchecks.ro", "paginiaurii.ro", "agriculturaecologica.ro",
    "yellowpages.com", "cylex.ro", "firme.info",
}



def _conn():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 not available")
    return psycopg2.connect(**CFG.DB)


def load_csv(path):
    rows = []
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def write_csv(rows, path):
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())
    cols = sorted(all_keys)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# PHASE 1: companies_clean enrichment via temp table
# ---------------------------------------------------------------------------

def phase1(input_csv, output_phase1, dry=True):
    """Enrich from companies_clean: website, phone, address, sector, email."""
    rows = load_csv(input_csv)
    cuis = list({r.get("cui", "").strip() for r in rows if r.get("cui")})
    if not cuis:
        print("No CUI found.")
        return rows

    print("\n=== PHASE 1: companies_clean enrichment ===")
    print("  CUI de procesat: %d" % len(cuis))
    conn = _conn()
    cur = conn.cursor()

    # Create temp table for fast JOIN.
    cur.execute("CREATE TEMP TABLE _mc (cui text)")
    for i in range(0, len(cuis), 500):
        batch = cuis[i:i+500]
        vals = ",".join("('%s')" % c.replace("'", "''") for c in batch)
        cur.execute("INSERT INTO _mc VALUES " + vals)
    cur.execute("CREATE INDEX ON _mc (cui)")
    conn.commit()
    print("  Temp table _mc: %d CUI" % len(cuis))

    # --- master_emails enrichment ---
    t0 = time.time()
    print("  Emailuri din master_emails...", end=" ", flush=True)
    cur.execute("""SELECT DISTINCT ON (m.cui) m.cui, m.email
                   FROM master_emails m JOIN _mc t ON m.cui = t.cui
                   WHERE m.email ~ '@' AND (m.is_bounced IS NULL OR m.is_bounced = false)
                   ORDER BY m.cui, m.warmth_score DESC NULLS LAST""")
    emails_found = {}
    for row in cur.fetchall():
        emails_found[row[0]] = row[1]
    print("%d in %.1fs" % (len(emails_found), time.time() - t0))

    new_emails = 0
    for r in rows:
        cui = r.get("cui", "").strip()
        existing = r.get("email", "") or ""
        if (not existing or "@" not in existing) and cui in emails_found:
            r["email"] = emails_found[cui]
            new_emails += 1

    t0 = time.time()
    print("  Telefon + domeniu din master_emails...", end=" ", flush=True)
    cur.execute("""SELECT DISTINCT ON (m.cui)
                          m.cui, m.phone, m.domain, m.industry, m.company
                   FROM master_emails m JOIN _mc t ON m.cui = t.cui
                   WHERE m.phone IS NOT NULL OR m.domain IS NOT NULL
                   ORDER BY m.cui, m.warmth_score DESC NULLS LAST""")
    enrich_data = {}
    for row in cur.fetchall():
        enrich_data[row[0]] = {
            "phone_me": row[1] or "",
            "domain": row[2] or "",
            "industry": row[3] or "",
            "company_name": row[4] or "",
        }
    print("%d in %.1fs" % (len(enrich_data), time.time() - t0))

    # --- companies_clean enrichment (now has cui index) ---
    t0 = time.time()
    print("  Website + adresa din companies_clean...", end=" ", flush=True)
    cur.execute("""SELECT DISTINCT ON (c.cui)
                          c.cui, c.website, c.address, c.sector_name
                   FROM companies_clean c JOIN _mc t ON c.cui = t.cui
                   ORDER BY c.cui""")
    cc_data = {}
    for row in cur.fetchall():
        cc_data[row[0]] = {
            "website_cc": row[1] or "",
            "address": row[2] or "",
            "sector": row[3] or "",
        }
    print("%d in %.1fs" % (len(cc_data), time.time() - t0))

    cur.execute("DROP TABLE IF EXISTS _mc")

    cur.execute("DROP TABLE IF EXISTS _ec")
    cur.close()
    conn.close()

    # Merge into rows.
    enriched = 0
    new_emails = 0
    new_phones = 0
    new_domains = 0
    new_websites = 0
    new_addresses = 0

    for r in rows:
        cui = r.get("cui", "").strip()
        ed = enrich_data.get(cui, {})
        cc = cc_data.get(cui, {})

        # Phone from master_emails if missing.
        existing_phone = r.get("phone", "") or ""
        if not existing_phone and ed.get("phone_me"):
            r["phone"] = ed["phone_me"]
            new_phones += 1

        # Domain -> website candidate.
        domain = ed.get("domain", "") or ""
        if domain and not r.get("website"):
            r["website"] = "https://www." + domain if not domain.startswith("http") else domain
            new_domains += 1

        # Website from companies_clean.
        website_cc = cc.get("website_cc", "") or ""
        if website_cc and not r.get("website"):
            r["website"] = website_cc
            new_websites += 1

        # Address from companies_clean.
        address = cc.get("address", "") or ""
        if address and not r.get("address"):
            r["address"] = address
            new_addresses += 1

        # Industry / sector.
        r["industry"] = ed.get("industry", "") or cc.get("sector", "") or r.get("industry", "")
        r["sector"] = cc.get("sector", "") or r.get("sector", "")

        # Company name from master_emails.
        if ed.get("company_name") and not r.get("name"):
            r["name"] = ed["company_name"]

        if ed or cc:
            enriched += 1

    # Stats.
    total = len(rows)
    has_email = sum(1 for r in rows if r.get("email") and "@" in r["email"])
    has_website = sum(1 for r in rows if r.get("website"))
    has_phone = sum(1 for r in rows if r.get("phone"))

    print("\n  Rezultate Phase 1:")
    print("    Randuri: %d" % total)
    print("    Cu email: %d" % has_email)
    print("    Cu website: %d" % has_website)
    print("    Cu telefon: %d" % has_phone)
    print("    Emailuri noi: %d" % new_emails)
    print("    Telefoane noi: %d" % new_phones)
    print("    Website-uri (domain): %d" % new_domains)
    print("    Website-uri (companies_clean): %d" % new_websites)
    print("    Adrese noi: %d" % new_addresses)

    if not dry:
        write_csv(rows, output_phase1)
        print("    Scris: %s" % output_phase1)
    else:
        print("    Dry-run. Adauga --phase1 sau --all pentru a scrie.")

    return rows


# ---------------------------------------------------------------------------
# PHASE 2: scrape company websites for email/phone (161 sites with known URL)
# termene.ro / listafirme.ro return 403 (anti-bot) -> skip, use owned URLs
# ---------------------------------------------------------------------------

CONTACT_PATTERNS = {
    "email": [
        r'([\w.-]+@[\w.-]+\.\w+)',
        r'mailto:([\w.-]+@[\w.-]+\.\w+)',
    ],
    "phone": [
        r'(?:\+4|0)?7\d{2}[\s.-]?\d{3}[\s.-]?\d{3}',
        r'(?:\+4|0)?2[13]\d{1}[\s.-]?\d{3}[\s.-]?\d{3}',
        r'(?:\+4|0)?3\d{2}[\s.-]?\d{3}[\s.-]?\d{3}',
    ],
}


def scrape_url(url, timeout=15):
    """Scrape one URL for email/phone. Returns dict."""
    result = {"email": "", "phone": "", "_error": ""}
    if not url or url in ("", "http://", "https://"):
        result["_error"] = "empty url"
        return result
    if not url.startswith("http"):
        url = "https://" + url
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            html = r.read().decode("utf-8", "ignore")
    except Exception as e:
        result["_error"] = str(e)[:120]
        return result

    # Extract email.
    for pat in CONTACT_PATTERNS["email"]:
        for m in re.finditer(pat, html):
            email = m.group(1).strip().lower()
            if email.endswith((".png", ".jpg", ".gif", ".css", ".js", ".svg", ".ico")):
                continue
            if "example.com" in email or "domain.com" in email or "@localhost" in email:
                continue
            if email.count("@") == 1 and "." in email.split("@")[1]:
                result["email"] = email
                break
        if result["email"]:
            break

    # Extract phone.
    for pat in CONTACT_PATTERNS["phone"]:
        for m in re.finditer(pat, html):
            ph = re.sub(r"[\s.-]", "", m.group(0))
            if len(ph) >= 10:
                result["phone"] = ph
                break
        if result["phone"]:
            break

    return result


def is_scrapable_domain(domain):
    """Check if an email domain is a real company domain worth scraping."""
    d = domain.strip().lower()
    if not d or "." not in d:
        return False
    if d in GENERIC_EMAIL_PROVIDERS:
        return False
    if d in GARBAGE_DOMAINS:
        return False
    if not d.startswith(("www.",)):
        pass
    # Single-word domains on generic TLDs are suspicious.
    parts = d.split(".")
    if len(parts) == 2 and parts[1] in ("com", "org", "net", "info"):
        if len(parts[0]) <= 3:
            return False
    # Skip IP-like strings.
    if re.match(r"^\d+(\.\d+)+$", d):
        return False
    # Skip file extensions used as domains (garbage).
    if d.endswith((".webp", ".png", ".jpg", ".gif", ".css", ".js", ".svg")):
        return False
    return True


def phase2(rows, output_phase2, dry=True, max_scrape=None):
    """Scrape company websites + email-domain-guessed URLs for missing emails."""
    # Step 1: collect existing websites that lack email.
    known_urls = {}  # url -> row
    for r in rows:
        has_email = r.get("email") and "@" in r["email"]
        url = (r.get("website") or "").strip()
        if url and url not in ("http://", "https://", ""):
            if not has_email:
                known_urls[url] = r

    # Step 2: generate website URLs from email domains.
    # Target: rows with a non-generic email but no website yet.
    domain_urls = {}
    for r in rows:
        has_url = r.get("website") and r["website"] not in ("http://", "https://", "")
        if has_url:
            continue
        email = (r.get("email") or "").strip()
        if email and "@" in email:
            domain = email.split("@")[1].strip().lower()
            if is_scrapable_domain(domain):
                guessed = "https://www.%s" % domain
                if guessed not in known_urls and guessed not in domain_urls:
                    domain_urls[guessed] = r

    # Merge: prefer known URLs first, then guessed.
    to_scrape = list(known_urls.items()) + list(domain_urls.items())

    print("\n=== PHASE 2: scraping company websites ===")
    print("  Website cunoscute fara email: %d" % len(known_urls))
    print("  Website generate din email: %d" % len(domain_urls))
    print("  Total URL de procesat: %d" % len(to_scrape))

    if not to_scrape:
        print("  Niciun URL de procesat.")
        return rows

    if max_scrape:
        to_scrape = to_scrape[:max_scrape]

    found_email = 0
    found_phone = 0
    errors = 0
    t0 = time.time()

    for i, (url, r) in enumerate(to_scrape):
        sys.stderr.write("\r  %d/%d URL (errors: %d)" % (i+1, len(to_scrape), errors))
        sys.stderr.flush()

        result = scrape_url(url)
        if result.get("email"):
            r["email"] = result["email"]
            r["email_source"] = "website"
            found_email += 1
        if result.get("phone") and not r.get("phone"):
            r["phone"] = result["phone"]
            r["phone_source"] = "website"
            found_phone += 1
        if result.get("_error"):
            errors += 1

        if i < len(to_scrape) - 1:
            time.sleep(1.0)

    elapsed = time.time() - t0
    total = len(rows)
    has_email = sum(1 for r in rows if r.get("email") and "@" in r["email"])
    has_phone = sum(1 for r in rows if r.get("phone"))
    has_website = sum(1 for r in rows if r.get("website"))

    print("\n\n  Rezultate Phase 2 (%d URL in %.1fs):" % (len(to_scrape), elapsed))
    print("    Emailuri gasite: %d" % found_email)
    print("    Telefoane gasite: %d" % found_phone)
    print("    Erori HTTP: %d" % errors)
    print("    Total cu email: %d / %d" % (has_email, total))
    print("    Total cu telefon: %d / %d" % (has_phone, total))
    print("    Total cu website: %d / %d" % (has_website, total))

    if not dry:
        write_csv(rows, output_phase2)
        print("    Scris: %s" % output_phase2)
    else:
        print("    Dry-run. Adauga --phase2 sau --all pentru a scrie.")

    return rows


# ---------------------------------------------------------------------------
# PHASE 3: verify + dedup + report
# ---------------------------------------------------------------------------

def is_valid_email(email):
    if not email or "@" not in email:
        return False
    email = email.strip().lower()
    # Reject patterns.
    bad = ["example.com", "domain.com", "test.com", "noreply", "no-reply",
           "donotreply", "info@example", "admin@domain", "@localhost"]
    for b in bad:
        if b in email:
            return False
    # Basic format.
    parts = email.split("@")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return False
    if "." not in parts[1]:
        return False
    if len(parts[1]) < 4:
        return False
    return True


def is_valid_phone(phone):
    if not phone:
        return False
    digits = re.sub(r"\D", "", str(phone))
    return len(digits) >= 10


def is_valid_website(website):
    if not website:
        return False
    website = website.strip().lower()
    if website.startswith("http://") or website.startswith("https://"):
        return True
    if "." in website and not website.startswith("javascript:"):
        return True
    return False


def phase3(rows, output_final, report_path, dry=True):
    """Verify contacts, dedup CUI, generate report."""
    print("\n=== PHASE 3: verify + dedup ===")

    # Verify fields.
    for r in rows:
        email = r.get("email", "") or ""
        phone = r.get("phone", "") or ""
        website = r.get("website", "") or ""
        r["email_valid"] = "1" if is_valid_email(email) else "0"
        r["phone_valid"] = "1" if is_valid_phone(phone) else "0"
        r["website_valid"] = "1" if is_valid_website(website) else "0"

    # Dedup by CUI.
    seen = {}
    for r in rows:
        cui = r.get("cui", "").strip()
        if not cui:
            continue
        if cui not in seen:
            seen[cui] = r
        else:
            # Merge: keep better email.
            existing = seen[cui]
            if not existing.get("email") or "@" not in existing.get("email", ""):
                if r.get("email") and "@" in r.get("email", ""):
                    existing["email"] = r["email"]
                    existing["email_source"] = r.get("email_source", "")
            if not existing.get("phone"):
                if r.get("phone"):
                    existing["phone"] = r["phone"]
            if not existing.get("website"):
                if r.get("website"):
                    existing["website"] = r["website"]

    deduped = list(seen.values())

    # Stats.
    total_orig = len(rows)
    total_dedup = len(deduped)
    n_email = sum(1 for r in deduped if r.get("email_valid") == "1")
    n_email_invalid = sum(1 for r in deduped if r.get("email") and r["email_valid"] == "0")
    n_phone = sum(1 for r in deduped if r.get("phone_valid") == "1")
    n_website = sum(1 for r in deduped if r.get("website_valid") == "1")

    print("  Randuri originale: %d" % total_orig)
    print("  Unique CUI: %d" % total_dedup)
    print("  Cu email valid: %d" % n_email)
    print("  Cu email invalid: %d" % n_email_invalid)
    print("  Cu telefon valid: %d" % n_phone)
    print("  Cu website valid: %d" % n_website)

    # Write report.
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Raport Imbogatire Producatori/Comercianti\n\n")
        f.write("Data: %s\n\n" % date.today())
        f.write("## Statistici\n\n")
        f.write("| Indicator | Valoare |\n")
        f.write("|-----------|--------|\n")
        f.write("| Total randuri originale | %d |\n" % total_orig)
        f.write("| CUI unici | %d |\n" % total_dedup)
        f.write("| Cu email valid | %d |\n" % n_email)
        f.write("| Cu email invalid | %d |\n" % n_email_invalid)
        f.write("| Cu telefon valid | %d |\n" % n_phone)
        f.write("| Cu website valid | %d |\n" % n_website)
        f.write("| Fara niciun contact | %d |\n" % sum(1 for r in deduped if r.get("email_valid") == "0" and r.get("phone_valid") == "0" and r.get("website_valid") == "0"))
        f.write("\n## Surse email\n\n")
        sources = {}
        for r in deduped:
            src = r.get("email_source", "master_romania")
            sources[src] = sources.get(src, 0) + 1
        for src, cnt in sorted(sources.items(), key=lambda x: -x[1]):
            f.write("- %s: %d\n" % (src, cnt))

    print("\n  Raport: %s" % report_path)

    if not dry:
        write_csv(deduped, output_final)
        print("  Scris: %s" % output_final)
    else:
        print("  Dry-run. Adauga --phase3 sau --all pentru a scrie.")

    return deduped


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    do_phase1 = "--phase1" in sys.argv or "--all" in sys.argv
    do_phase2 = "--phase2" in sys.argv or "--all" in sys.argv
    do_phase3 = "--phase3" in sys.argv or "--all" in sys.argv
    dry = "--dry" in sys.argv or not ("--apply" in sys.argv or "--all" in sys.argv)
    max_scrape = None
    for a in sys.argv[1:]:
        if a.startswith("--max="):
            max_scrape = int(a.split("=")[1])

    if not (do_phase1 or do_phase2 or do_phase3):
        print("Utilizare:")
        print("  python GRAIN/full_enrich_pipeline.py --phase1        # companies_clean")
        print("  python GRAIN/full_enrich_pipeline.py --phase2        # scraping company websites")
        print("  python GRAIN/full_enrich_pipeline.py --all           # tot pipeline-ul")
        print("  python GRAIN/full_enrich_pipeline.py --all --apply   # scrie fisierele")
        return 0

    rows = load_csv(INPUT_CSV)
    print("Incarcat: %s (%d randuri)" % (INPUT_CSV, len(rows)))

    if do_phase1:
        rows = phase1(INPUT_CSV, PHASE1_OUT, dry=dry)

    if do_phase2:
        rows = phase2(rows, PHASE2_OUT, dry=dry, max_scrape=max_scrape)

    if do_phase3:
        rows = phase3(rows, FINAL_OUT, REPORT, dry=dry)

    if not dry and do_phase3:
        print("\n=== PIPELINE COMPLETE ===")
        print("  Final: %s" % FINAL_OUT)
        print("  Raport: %s" % REPORT)

    return 0


if __name__ == "__main__":
    sys.exit(main())
