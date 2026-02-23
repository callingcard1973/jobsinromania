#!/usr/bin/env python3
"""
Local enrichment - TARGETED approach.
Only scan known useful files, not all 7K CSVs.
"""

import csv
import re
from pathlib import Path
from collections import defaultdict

BASE = Path(r"D:\MEMORY\CLAUDE")
FRANK = BASE / "CALLCENTERS" / "callcenters_romania_frank.csv"
OUTPUT = BASE / "CALLCENTERS" / "callcenters_romania_frank_enriched.csv"

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_RE = re.compile(r"(?:\+?40|0)[2-9]\d{7,8}")

# Only scan these known-useful files for contacts
SOURCE_FILES = [
    "DELIVERY/companies_enriched.csv",
    "OPT/ANOFM COMPANIES/companies_deep_enriched.csv",
    "OPT/DATA/ROMANIA/CCIB/ccib_companies.csv",
    "OPT/DATA/ROMANIA/WEBSITE_CONTACTS/extracted_20260120.csv",
    "OPT/DATA/ROMANIA/BILANT/segment_lunch.csv",
    "OPT/EMAIL/campaigns/TWISTED_OLIVES/contacts/contacts.csv",
    "OPT/EMAIL/campaigns/CAREWORKERS/segments/segment_nordic.csv",
    "OPT/EMAIL/campaigns/GERMANY/segments/general.csv",
    "FONDURI EUROPENE ROMANIA/hot_leads_eu_funds.csv",
    "CONSTRUCTION PROJECTS/AGENCIES/eures_romania_4928.csv",
    "MR ANUP/ROMANIA/MASTER_ALL.csv",
    "MR ANUP/ENRICHED/faliment_master_20260222.csv",
    "FACTORYJOBS/companies_deep_enriched.csv",
]

# Also glob these patterns
GLOB_PATTERNS = [
    "OPT/EMAIL/campaigns/*/contacts/*.csv",
    "OPT/EMAIL/campaigns/*/segments/*.csv",
    "OPT/CSV/*.csv",
    "OPT/DATA/ROMANIA/*/*.csv",
    "DELIVERY/*.csv",
    "AUTOREPLY/*.csv",
    "MR ANUP/*/*.csv",
    "MR ANUP/ENRICHED/*.csv",
]

CUI_COLS = ["cui", "employer_tax_code", "company_id"]
NAME_COLS = ["company", "company_name", "name", "denumire", "nume_firma",
             "employer", "employer_normalized", "contractor"]
EMAIL_COLS = ["email", "best_email", "email_1", "email_enriched", "anofm_email",
              "email1", "contact_email", "email_2", "email2", "email_3"]
PHONE_COLS = ["phone", "best_phone", "phone_1", "phone_enriched", "anofm_phone",
              "phone1", "contact_phone", "phone_2", "phone2", "anaf_phone",
              "anaf_phone2", "telefon"]
WEB_COLS = ["website", "best_website", "website_found", "company_website",
            "anofm_website", "domain"]


def clean(v):
    if v is None: return ""
    s = str(v).strip()
    return "" if s.lower() in ("nan", "none", "n/a", "null", "") else s

def norm_cui(val):
    s = clean(val)
    s = re.sub(r"^RO\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^0-9]", "", s)
    return s.lstrip("0") if s else ""

def norm_name(val):
    s = clean(val).upper()
    for suf in [" S.R.L.", " SRL", " S.A.", " SA", " S.C.", " SC"]:
        s = s.replace(suf, "")
    s = re.sub(r"[^A-Z0-9 ]", "", s)
    return re.sub(r"\s+", " ", s).strip()

def extract_emails(text):
    return [e.lower() for e in EMAIL_RE.findall(str(text))
            if e.split("@")[1] not in {"example.com","test.com","domain.com"} and len(e)<60]

def extract_phones(text):
    return [re.sub(r"[^0-9+]","",p) for p in PHONE_RE.findall(str(text))]

def g(row, *cols):
    for c in cols:
        for key in row:
            if key and key.strip().lower() == c.lower():
                val = clean(row[key])
                if val: return val
    return ""

def read_csv_safe(path):
    for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                sample = f.read(4096)
                f.seek(0)
                try:
                    dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
                    reader = csv.DictReader(f, dialect=dialect)
                except csv.Error:
                    reader = csv.DictReader(f)
                return list(reader)
        except Exception:
            continue
    return []


def stream_csv(path, target_cuis):
    """Stream large CSV, only extracting contacts for target CUIs."""
    hits = {}
    for enc in ["utf-8", "utf-8-sig", "latin-1"]:
        try:
            with open(path, "r", encoding=enc, errors="replace") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    cui = ""
                    for c in CUI_COLS:
                        cui = cui or norm_cui(g(row, c))
                    if not cui or cui not in target_cuis:
                        continue
                    emails = set()
                    for c in EMAIL_COLS:
                        val = g(row, c)
                        if "@" in val: emails.update(extract_emails(val))
                    phones = set()
                    for c in PHONE_COLS:
                        val = g(row, c)
                        if val: phones.update(extract_phones(val))
                    websites = set()
                    for c in WEB_COLS:
                        val = g(row, c)
                        if val and "." in val and " " not in val: websites.add(val)
                    if emails or phones or websites:
                        if cui not in hits:
                            hits[cui] = {"emails": set(), "phones": set(), "websites": set()}
                        hits[cui]["emails"].update(emails)
                        hits[cui]["phones"].update(phones)
                        hits[cui]["websites"].update(websites)
            break
        except Exception:
            continue
    return hits


def build_index(target_cuis):
    print("Building contact index (targeted)...", flush=True)

    cui_data = defaultdict(lambda: {"emails": set(), "phones": set(), "websites": set()})
    name_data = defaultdict(lambda: {"emails": set(), "phones": set(), "websites": set()})

    # Collect unique file paths
    files = set()
    for sf in SOURCE_FILES:
        p = BASE / sf
        if p.exists(): files.add(p)
    for gp in GLOB_PATTERNS:
        for p in BASE.glob(gp):
            if p.stat().st_size < 10_000_000 and "callcenters_" not in p.name:
                files.add(p)

    print(f"  {len(files)} targeted files to scan", flush=True)

    for i, fpath in enumerate(sorted(files)):
        if fpath.stat().st_size > 10_000_000:
            # Stream large files - CUI only
            print(f"  Streaming {fpath.name} ({fpath.stat().st_size//1_000_000}MB)...", flush=True)
            hits = stream_csv(fpath, target_cuis)
            for cui, data in hits.items():
                cui_data[cui]["emails"].update(data["emails"])
                cui_data[cui]["phones"].update(data["phones"])
                cui_data[cui]["websites"].update(data["websites"])
            continue

        try:
            rows = read_csv_safe(str(fpath))
        except Exception:
            continue
        if not rows:
            continue

        for row in rows:
            cui = ""
            for c in CUI_COLS: cui = cui or norm_cui(g(row, c))
            company = ""
            for c in NAME_COLS: company = company or g(row, c)

            emails = set()
            for c in EMAIL_COLS:
                val = g(row, c)
                if "@" in val: emails.update(extract_emails(val))
            phones = set()
            for c in PHONE_COLS:
                val = g(row, c)
                if val: phones.update(extract_phones(val))
            websites = set()
            for c in WEB_COLS:
                val = g(row, c)
                if val and "." in val and " " not in val: websites.add(val)

            if not (emails or phones or websites): continue

            if cui:
                cui_data[cui]["emails"].update(emails)
                cui_data[cui]["phones"].update(phones)
                cui_data[cui]["websites"].update(websites)
            if company:
                nn = norm_name(company)
                if nn and len(nn) >= 4:
                    name_data[nn]["emails"].update(emails)
                    name_data[nn]["phones"].update(phones)
                    name_data[nn]["websites"].update(websites)

        if (i+1) % 20 == 0:
            print(f"  Scanned {i+1}/{len(files)}...", flush=True)

    print(f"  CUI index: {len(cui_data)} | Name index: {len(name_data)}", flush=True)
    return cui_data, name_data


def enrich(records, cui_data, name_data):
    e = defaultdict(int)
    name_keys = list(name_data.keys())

    for r in records:
        cui, company = r["cui"], r["company"]

        # CUI match
        if cui and cui in cui_data:
            d = cui_data[cui]
            if not r["email"] and d["emails"]:
                el = sorted(d["emails"])
                r["email"] = el[0]
                if len(el) > 1 and not r["email2"]: r["email2"] = el[1]
                e["cui_email"] += 1
            if not r["phone"] and d["phones"]:
                pl = sorted(d["phones"])
                r["phone"] = pl[0]
                if len(pl) > 1 and not r["phone2"]: r["phone2"] = pl[1]
                e["cui_phone"] += 1
            if not r["website"] and d["websites"]:
                r["website"] = sorted(d["websites"])[0]
                e["cui_web"] += 1

        # Name match
        if (not r["email"] or not r["phone"]) and company:
            nn = norm_name(company)
            matched = False
            # Exact normalized
            if nn in name_data:
                d = name_data[nn]
                matched = True
            else:
                # Fuzzy: word overlap >= 75%
                for nk in name_keys:
                    if len(nn) < 6: break
                    w1 = nn.split()[0] if nn.split() else ""
                    if w1 and w1 not in nk: continue
                    wa, wb = set(nn.split()), set(nk.split())
                    if len(wa) >= 2 and len(wb) >= 2 and len(wa & wb) / max(len(wa), len(wb)) >= 0.75:
                        d = name_data[nk]
                        matched = True
                        break

            if matched:
                if not r["email"] and d["emails"]:
                    r["email"] = sorted(d["emails"])[0]
                    e["name_email"] += 1
                if not r["phone"] and d["phones"]:
                    r["phone"] = sorted(d["phones"])[0]
                    e["name_phone"] += 1
                if not r["website"] and d["websites"]:
                    r["website"] = sorted(d["websites"])[0]
                    e["name_web"] += 1

    print(f"\n  CUI:  +{e['cui_email']} emails, +{e['cui_phone']} phones, +{e['cui_web']} web")
    print(f"  Name: +{e['name_email']} emails, +{e['name_phone']} phones, +{e['name_web']} web")
    print(f"  TOTAL: +{e['cui_email']+e['name_email']} emails, +{e['cui_phone']+e['name_phone']} phones")
    return records


def main():
    print("=" * 60)
    print("LOCAL ENRICHMENT - Frank Call Centers")
    print("=" * 60, flush=True)

    with open(FRANK, encoding="utf-8") as f:
        records = list(csv.DictReader(f))

    total = len(records)
    b_e = sum(1 for r in records if r["email"])
    b_p = sum(1 for r in records if r["phone"])
    b_w = sum(1 for r in records if r["website"])
    print(f"Loaded {total} | Before: email={b_e} phone={b_p} web={b_w}\n", flush=True)

    target_cuis = {r["cui"] for r in records if r["cui"]}
    cui_data, name_data = build_index(target_cuis)
    records = enrich(records, cui_data, name_data)

    a_e = sum(1 for r in records if r["email"])
    a_p = sum(1 for r in records if r["phone"])
    a_w = sum(1 for r in records if r["website"])

    fnames = list(records[0].keys())
    for path in [OUTPUT, FRANK]:
        with open(path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fnames)
            w.writeheader()
            w.writerows(records)

    print(f"\n{'='*60}")
    print(f"BEFORE: email={b_e}/{total} phone={b_p}/{total} web={b_w}/{total}")
    print(f"AFTER:  email={a_e}/{total} ({100*a_e//total}%) phone={a_p}/{total} ({100*a_p//total}%) web={a_w}/{total}")
    print(f"GAINED: +{a_e-b_e} emails, +{a_p-b_p} phones, +{a_w-b_w} websites")
    print("Done!")

if __name__ == "__main__":
    main()
