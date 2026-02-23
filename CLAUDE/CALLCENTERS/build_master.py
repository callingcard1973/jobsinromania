#!/usr/bin/env python3
"""
Call Centers Master Database Builder
Consolidates call center / BPO companies from 18+ CSV sources.
Outputs: master, romania_frank, europe, insolvent.
"""

import csv
import re
import sys
from pathlib import Path
from collections import defaultdict
import glob as globmod

BASE = Path(r"D:\MEMORY\CLAUDE")

OUTPUT_COLS = [
    "company", "cui", "caen", "country", "city", "address",
    "email", "email2", "phone", "phone2", "website",
    "contact_person", "employees", "revenue", "profit",
    "positions", "sector", "status", "source", "notes"
]

# --- Matching ---
TEXT_PATTERNS = re.compile(
    r"call.?cent|contact.?cent|\bbpo\b|outsourc|telemarket",
    re.IGNORECASE
)
CAEN_CODES = {"8220"}
# Use regex word boundaries to avoid partial matches (e.g. "transcom" in "intertranscom")
KNOWN_COMPANIES_RE = re.compile(
    r"\b(?:concentrix|teleperformance|foundever|webhelp|majorel"
    r"|sitel group|alorica|convergys|genpact|conectys|arvato"
    r"|comdata|transcom worldwide|conduent|ttec|sykes"
    r"|telus international|taskus|liveops|sutherland|startek"
    r"|css corp)\b",
    re.IGNORECASE
)

COUNTRY_MAP = {
    "ro": "Romania", "romania": "Romania",
    "de": "Germany", "germany": "Germany",
    "fr": "France", "france": "France",
    "es": "Spain", "spain": "Spain",
    "it": "Italy", "italy": "Italy",
    "uk": "United Kingdom", "united kingdom": "United Kingdom", "gb": "United Kingdom",
    "nl": "Netherlands", "be": "Belgium", "belgium": "Belgium",
    "at": "Austria", "austria": "Austria",
    "ch": "Switzerland", "switzerland": "Switzerland",
    "se": "Sweden", "sweden": "Sweden",
    "no": "Norway", "norway": "Norway",
    "dk": "Denmark", "denmark": "Denmark",
    "fi": "Finland", "finland": "Finland",
    "pl": "Poland", "poland": "Poland",
    "cz": "Czech Republic", "hu": "Hungary", "hungary": "Hungary",
    "bg": "Bulgaria", "hr": "Croatia", "si": "Slovenia",
    "ie": "Ireland", "ireland": "Ireland",
    "pt": "Portugal", "gr": "Greece",
    "cy": "Cyprus", "lt": "Lithuania", "lv": "Latvia", "ee": "Estonia",
    "lu": "Luxembourg", "mt": "Malta", "sk": "Slovakia",
    "bosnia": "Bosnia", "ba": "Bosnia",
    "rs": "Serbia", "mk": "North Macedonia", "md": "Moldova",
}


def clean(val):
    if val is None: return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "n/a", "null", "") else s

def norm_country(val):
    s = clean(val).strip()
    return COUNTRY_MAP.get(s.lower(), s) if s else ""

def norm_cui(val):
    s = clean(val)
    s = re.sub(r"^RO\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"[^0-9]", "", s)
    return s.lstrip("0") if s else ""

def norm_phone(val):
    s = clean(val)
    if not s: return ""
    has_plus = s.startswith("+")
    digits = re.sub(r"[^0-9]", "", s)
    return ("+" + digits) if (has_plus and digits) else digits

def norm_email(val):
    s = clean(val).lower().strip()
    return s if "@" in s else ""


def is_callcenter(company_name="", caen_val="", sector="", description=""):
    """Match on company name, CAEN, sector, description only."""
    if str(caen_val).strip().replace(".", "") in CAEN_CODES:
        return True
    text = f"{company_name} {sector} {description}".lower()
    if TEXT_PATTERNS.search(text):
        return True
    if KNOWN_COMPANIES_RE.search(company_name):
        return True
    return False


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


def g(row, *cols):
    """Get first non-empty value from candidate column names."""
    for c in cols:
        for key in row:
            if key and key.strip().lower() == c.lower():
                val = clean(row[key])
                if val: return val
    return ""


def rec(**kw):
    """Create standardized record."""
    return {
        "company": clean(kw.get("company", "")),
        "cui": norm_cui(kw.get("cui", "")),
        "caen": clean(kw.get("caen", "")),
        "country": norm_country(kw.get("country", "")),
        "city": clean(kw.get("city", "")),
        "address": clean(kw.get("address", "")),
        "email": norm_email(kw.get("email", "")),
        "email2": norm_email(kw.get("email2", "")),
        "phone": norm_phone(kw.get("phone", "")),
        "phone2": norm_phone(kw.get("phone2", "")),
        "website": clean(kw.get("website", "")),
        "contact_person": clean(kw.get("contact_person", "")),
        "employees": clean(kw.get("employees", "")),
        "revenue": clean(kw.get("revenue", "")),
        "profit": clean(kw.get("profit", "")),
        "positions": clean(kw.get("positions", "")),
        "sector": clean(kw.get("sector", "")) or "Call center / BPO",
        "status": clean(kw.get("status", "")) or "active",
        "source": clean(kw.get("source", "")),
        "notes": clean(kw.get("notes", "")),
    }


# ===== EXTRACTORS (each returns list of records) =====

def extract_delivery():
    path = BASE / "DELIVERY" / "companies_enriched.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        sector = g(r, "sector")
        caen = g(r, "anaf_caen", "caen")
        company = g(r, "company")
        if is_callcenter(company, caen, sector):
            results.append(rec(company=company, cui=g(r,"cui"), caen=caen, country="Romania",
                city=g(r,"city"), address=g(r,"address","anaf_address"),
                email=g(r,"best_email","email_enriched","anofm_email"),
                email2=g(r,"anofm_email"), phone=g(r,"best_phone","phone_enriched","anofm_phone"),
                phone2=g(r,"anaf_phone2"), website=g(r,"best_website","website","anofm_website"),
                contact_person=g(r,"anofm_contact_person"), positions=g(r,"total_positions"),
                sector=sector, status="active" if g(r,"is_active")!="False" else "inactive",
                source="DELIVERY"))
    print(f"  DELIVERY: {len(results)}")
    return results

def extract_anofm_deep():
    path = BASE / "OPT" / "ANOFM COMPANIES" / "companies_deep_enriched.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        caen = g(r, "anaf_caen", "caen")
        company = g(r, "company")
        sector = g(r, "sector")
        if is_callcenter(company, caen, sector):
            results.append(rec(company=company, cui=g(r,"cui"), caen=caen, country="Romania",
                city=g(r,"city"), address=g(r,"address","anaf_address"),
                email=g(r,"best_email","email_enriched"), email2=g(r,"email2","anofm_email"),
                phone=g(r,"best_phone","phone_enriched"), phone2=g(r,"phone2","anaf_phone2"),
                website=g(r,"best_website","website_found","website"),
                contact_person=g(r,"anofm_contact_person","contact_person_found"),
                employees=g(r,"employees"), revenue=g(r,"revenue"), profit=g(r,"profit"),
                positions=g(r,"total_positions"), sector=sector,
                status="active" if g(r,"is_active")!="False" else "inactive",
                source="ANOFM_DEEP"))
    print(f"  ANOFM_DEEP: {len(results)}")
    return results

def extract_ccib():
    path = BASE / "OPT" / "DATA" / "ROMANIA" / "CCIB" / "ccib_companies.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "name")
        desc = g(r, "description")
        if is_callcenter(company, description=desc):
            results.append(rec(company=company, country="Romania",
                email=g(r,"email"), phone=g(r,"phone_1"), phone2=g(r,"phone_2"),
                website=g(r,"website"), notes=desc, source="CCIB"))
    print(f"  CCIB: {len(results)}")
    return results

def extract_website_contacts():
    path = BASE / "OPT" / "DATA" / "ROMANIA" / "WEBSITE_CONTACTS" / "extracted_20260120.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "company_name")
        if is_callcenter(company):
            results.append(rec(company=company, cui=g(r,"cui"), country="Romania",
                email=g(r,"email_1"), email2=g(r,"email_2"),
                phone=g(r,"phone_1"), phone2=g(r,"phone_2"),
                website=g(r,"domain"), source="WEBSITE_CONTACTS"))
    print(f"  WEBSITE_CONTACTS: {len(results)}")
    return results

def extract_bilant():
    path = BASE / "OPT" / "DATA" / "ROMANIA" / "BILANT" / "segment_lunch.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        caen = g(r, "caen")
        company = g(r, "nume_firma")
        sector = g(r, "sector")
        if is_callcenter(company, caen, sector):
            results.append(rec(company=company, cui=g(r,"cui"), caen=caen, country="Romania",
                city=g(r,"localitate"), address=g(r,"adresa"), phone=g(r,"telefon"),
                employees=g(r,"nr_angajati"), revenue=g(r,"cifra_afaceri"),
                profit=g(r,"profit_net"), sector=sector, source="BILANT"))
    print(f"  BILANT: {len(results)}")
    return results

def extract_buc_ilfov():
    for d in ["BUCHAREST_ILFOV", "BUCHAREST_ILFOV_ESTABLISHED"]:
        path = BASE / "OPT" / "DATA" / "ROMANIA" / d / "buc_ilfov_active_sorted.csv"
        if path.exists(): break
    else: return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "denumire")
        if is_callcenter(company):
            results.append(rec(company=company, cui=g(r,"cui"), country="Romania",
                city=g(r,"localitate"),
                address=" ".join(filter(None, [g(r,"strada"), g(r,"nr_strada"), g(r,"sector")])),
                website=g(r,"website"), source="BUC_ILFOV"))
    print(f"  BUC_ILFOV: {len(results)}")
    return results

def extract_master_all():
    path = BASE / "MR ANUP" / "ROMANIA" / "MASTER_ALL.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "employer", "employer_normalized")
        sector = g(r, "sector", "industry")
        if is_callcenter(company, sector=sector):
            results.append(rec(company=company, cui=g(r,"employer_tax_code"),
                country=g(r,"country") or "Romania", city=g(r,"city"), address=g(r,"address"),
                email=g(r,"email1"), email2=g(r,"email2"),
                phone=g(r,"phone1"), phone2=g(r,"phone2"),
                website=g(r,"company_website"), contact_person=g(r,"contact_person"),
                positions=g(r,"positions"), sector=sector, source="MASTER_ALL"))
    print(f"  MASTER_ALL: {len(results)}")
    return results

def extract_faliment():
    path = BASE / "MR ANUP" / "ENRICHED" / "faliment_master_20260222.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        caen = g(r, "caen")
        company = g(r, "company_name")
        sector = g(r, "sector")
        desc = g(r, "caen_description")
        if is_callcenter(company, caen, sector, desc):
            results.append(rec(company=company, cui=g(r,"cui"), caen=caen, country="Romania",
                city=g(r,"city"), address=g(r,"address_full","street"),
                email=g(r,"email"), phone=g(r,"phone"), website=g(r,"website"),
                employees=g(r,"employees"), revenue=g(r,"revenue"), sector=sector,
                status="insolvent",
                notes=f"Procedure: {g(r,'bpi_procedure_type')} | Liquidator: {g(r,'bpi_liquidator')}".strip(" |"),
                source="FALIMENT"))
    print(f"  FALIMENT: {len(results)}")
    return results

def extract_ted(year):
    path = BASE / "DATA" / "TED" / f"ted_winners_{year}.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "contractor")
        cpv = g(r, "cpv")
        if is_callcenter(company, description=cpv):
            results.append(rec(company=company,
                country=g(r,"contractor_country"), city=g(r,"contractor_city"),
                address=g(r,"contractor_address"), email=g(r,"contractor_email"),
                website=g(r,"contractor_website"),
                notes=f"TED {year} | CPV: {cpv} | Value: {g(r,'value')}",
                source=f"TED_{year}"))
    print(f"  TED_{year}: {len(results)}")
    return results

def extract_twisted_olives():
    path = BASE / "OPT" / "EMAIL" / "campaigns" / "TWISTED_OLIVES" / "contacts" / "contacts.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "denumire")
        if is_callcenter(company):
            results.append(rec(company=company, country="Romania",
                email=g(r,"email"), phone=g(r,"anaf_phone"), source="TWISTED_OLIVES"))
    print(f"  TWISTED_OLIVES: {len(results)}")
    return results

def extract_germany_openregister():
    pattern = str(BASE / "PLASARE 400 MUNCITORI" / "GERMANY" / "openregister_temp_agencies*.csv")
    files = globmod.glob(pattern)
    if not files: return []
    results = []
    for fpath in files:
        for r in read_csv_safe(fpath):
            company = g(r, "company_name")
            if is_callcenter(company):
                results.append(rec(company=company, country="Germany",
                    city=g(r,"city"), address=g(r,"address"),
                    contact_person=" ".join(filter(None, [g(r,"officer_firstname"), g(r,"officer_lastname")])),
                    notes=f"State: {g(r,'federal_state')}", source="GERMANY/openregister"))
    print(f"  GERMANY/openregister: {len(results)}")
    return results

def extract_switzerland():
    for sub in ["PLASARE 400 MUNCITORI/SWITZERLAND/data/seco_agencies_ALL.csv",
                 "PLASARE 400 MUNCITORI/SWITZERLAND/seco_agencies_ALL.csv"]:
        path = BASE / sub
        if path.exists(): break
    else: return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "firmenbezeichnung")
        if is_callcenter(company):
            results.append(rec(company=company, country="Switzerland",
                city=g(r,"ort"), address=g(r,"strasse"), phone=g(r,"telefon"),
                notes=f"Kanton: {g(r,'kanton')}", source="SWITZERLAND/seco"))
    print(f"  SWITZERLAND/seco: {len(results)}")
    return results

def extract_nordic():
    path = BASE / "OPT" / "EMAIL" / "campaigns" / "CAREWORKERS" / "segments" / "segment_nordic.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "employer")
        job = g(r, "job_title")
        if is_callcenter(company, description=job):
            results.append(rec(company=company, country=g(r,"country"),
                city=g(r,"location"), email=g(r,"email"), phone=g(r,"phone"),
                contact_person=g(r,"contact_person"), positions=job,
                source="NORDIC"))
    print(f"  NORDIC: {len(results)}")
    return results

def extract_germany_campaigns():
    path = BASE / "OPT" / "EMAIL" / "campaigns" / "GERMANY" / "segments" / "general.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "company_name")
        industry = g(r, "company_industry")
        desc = g(r, "company_description", "job_description")
        if is_callcenter(company, sector=industry, description=desc):
            results.append(rec(company=company, country="Germany",
                city=g(r,"location_city"), address=g(r,"location_address"),
                email=g(r,"contact_email"), phone=g(r,"contact_phone"),
                website=g(r,"company_website"), contact_person=g(r,"contact_name"),
                employees=g(r,"company_size"), source="GERMANY/campaigns"))
    print(f"  GERMANY/campaigns: {len(results)}")
    return results

def extract_sweden():
    path = BASE / "OPT" / "CSV" / "sweden.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "Company name")
        job = g(r, "job_title")
        if is_callcenter(company, description=job):
            results.append(rec(company=company, country="Sweden",
                city=g(r,"location_name"), email=g(r,"email"), phone=g(r,"phone"),
                website=g(r,"website"), positions=g(r,"position"), source="SWEDEN"))
    print(f"  SWEDEN: {len(results)}")
    return results

def extract_eu_funds():
    path = BASE / "FONDURI EUROPENE ROMANIA" / "hot_leads_eu_funds.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        caen = g(r, "caen")
        company = g(r, "company")
        if is_callcenter(company, caen):
            results.append(rec(company=company, caen=caen, country="Romania",
                city=g(r,"city"), address=g(r,"address"), email=g(r,"email"), phone=g(r,"phone"),
                notes=f"EU: {g(r,'project_title')} | {g(r,'budget_eur')} EUR",
                source="EU_FUNDS"))
    print(f"  EU_FUNDS: {len(results)}")
    return results

def extract_eures():
    path = BASE / "CONSTRUCTION PROJECTS" / "AGENCIES" / "eures_romania_4928.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "company_name")
        if is_callcenter(company):
            results.append(rec(company=company, country=g(r,"country") or "Romania",
                email=g(r,"email"), phone=g(r,"phone"), website=g(r,"website"),
                source="EURES"))
    print(f"  EURES: {len(results)}")
    return results

def extract_bosnia():
    path = BASE / "MR ANUP" / "BOSNIA" / "DATA" / "opensanctions_bih_enriched.csv"
    if not path.exists(): return []
    results = []
    for r in read_csv_safe(path):
        company = g(r, "company_name")
        if is_callcenter(company):
            results.append(rec(company=company, country="Bosnia",
                city=g(r,"city"), address=g(r,"address"), source="BOSNIA"))
    print(f"  BOSNIA: {len(results)}")
    return results


# ===== DEDUP =====

def dedup_records(records):
    by_cui = {}
    by_name = {}
    for r in records:
        cui = r["cui"]
        name = r["company"].lower().strip()
        country = r["country"].lower().strip()
        if cui:
            if cui in by_cui:
                for k in OUTPUT_COLS:
                    if not by_cui[cui][k] and r[k]:
                        by_cui[cui][k] = r[k]
                if r["source"] not in by_cui[cui]["source"]:
                    by_cui[cui]["source"] += " | " + r["source"]
            else:
                by_cui[cui] = r
        elif name:
            key = (name, country)
            if key in by_name:
                for k in OUTPUT_COLS:
                    if not by_name[key][k] and r[k]:
                        by_name[key][k] = r[k]
                if r["source"] not in by_name[key]["source"]:
                    by_name[key]["source"] += " | " + r["source"]
            else:
                by_name[key] = r

    final = list(by_cui.values())
    for key, r in by_name.items():
        matched = False
        for ex in final:
            if ex["company"].lower().strip() == key[0] and ex["country"].lower() == key[1]:
                for k in OUTPUT_COLS:
                    if not ex[k] and r[k]: ex[k] = r[k]
                matched = True
                break
        if not matched:
            final.append(r)
    return final


# ===== MAIN =====

def main():
    print("=" * 60)
    print("CALL CENTERS MASTER DATABASE BUILDER")
    print("=" * 60)

    all_records = []
    extractors = [
        extract_delivery, extract_anofm_deep, extract_ccib,
        extract_website_contacts, extract_bilant, extract_buc_ilfov,
        extract_master_all, extract_faliment,
        lambda: extract_ted(2021), lambda: extract_ted(2022),
        extract_twisted_olives, extract_germany_openregister,
        extract_switzerland, extract_nordic, extract_germany_campaigns,
        extract_sweden, extract_eu_funds, extract_eures, extract_bosnia,
    ]

    print("\n--- Extracting ---")
    for ext in extractors:
        try:
            all_records.extend(ext())
        except Exception as e:
            print(f"  ERROR: {e}")

    print(f"\nRaw records: {len(all_records)}")

    print("\n--- Deduplicating ---")
    deduped = dedup_records(all_records)
    deduped.sort(key=lambda r: (r["country"].lower(), r["company"].lower()))
    print(f"Unique companies: {len(deduped)}")

    outdir = BASE / "CALLCENTERS"
    outdir.mkdir(exist_ok=True)

    romania_active = [r for r in deduped if r["country"] == "Romania" and r["status"] != "insolvent"]
    europe = [r for r in deduped if r["country"] != "Romania"]
    insolvent = [r for r in deduped if r["status"] == "insolvent"]

    def write_csv(filename, records):
        with open(outdir / filename, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=OUTPUT_COLS).writeheader()
            csv.DictWriter(f, fieldnames=OUTPUT_COLS).writerows(records)
        print(f"  {filename}: {len(records)} records")

    print("\n--- Output ---")
    write_csv("callcenters_master.csv", deduped)
    write_csv("callcenters_romania_frank.csv", romania_active)
    write_csv("callcenters_europe.csv", europe)
    write_csv("callcenters_insolvent.csv", insolvent)

    # Stats
    print(f"\n{'='*60}")
    print(f"Total: {len(deduped)} | Romania (Frank): {len(romania_active)} | Europe: {len(europe)} | Insolvent: {len(insolvent)}")
    for label, sub in [("Master", deduped), ("Frank", romania_active)]:
        t = len(sub) or 1
        print(f"\n  {label}: email={sum(1 for r in sub if r['email'])}/{t} ({100*sum(1 for r in sub if r['email'])//t}%) "
              f"phone={sum(1 for r in sub if r['phone'])}/{t} ({100*sum(1 for r in sub if r['phone'])//t}%) "
              f"website={sum(1 for r in sub if r['website'])}/{t}")

    countries = defaultdict(int)
    for r in deduped: countries[r["country"] or "?"] += 1
    print("\n  Countries:", " | ".join(f"{c}:{n}" for c,n in sorted(countries.items(), key=lambda x:-x[1])))

    cuis = [r["cui"] for r in deduped if r["cui"]]
    dupes = len(cuis) - len(set(cuis))
    print(f"\n  CUI check: {len(set(cuis))} unique" + (f" WARNING: {dupes} dupes!" if dupes else " OK"))
    print("\nDone!")


if __name__ == "__main__":
    main()
