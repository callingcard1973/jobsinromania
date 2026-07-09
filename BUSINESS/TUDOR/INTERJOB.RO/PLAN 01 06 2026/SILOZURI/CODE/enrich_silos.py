#!/usr/bin/env python3
"""Enrich silos with local ANAF/ROMANIA_DB into silozuri.sqlite."""
import csv
import re
import argparse
from pathlib import Path

from db_silozuri import get_connection, install_schema, ingest_row

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "DATA" / "silozuri.sqlite"
MASTER_CSV = ROOT / "ARCHIVE" / "silos_master.csv"
ENRICHED_CSV = ROOT / "ARCHIVE" / "silos_enriched.csv"
ANAF_STARE = ROOT / "DATA" / "raw" / "ANAF" / "od_stare_firma.csv"
ANAF_CAEN = ROOT / "DATA" / "raw" / "ANAF" / "od_caen_autorizat.csv"
MRC = Path("D:/MEMORY/DATA/ACTIVE/ROMANIA_DB/master_romania_companies.csv")
MRC_CONTACTS = Path("D:/MEMORY/DATA/ACTIVE/ROMANIA_DB/master_romania_contacts.csv")

def build_anaf_indexes():
    stare = {}
    caen = {}
    if ANAF_STARE.exists():
        with open(ANAF_STARE, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter="^")
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    key = row[0].strip()
                    val = row[1].strip()
                    if key and val:
                        stare[key] = val
    if ANAF_CAEN.exists():
        with open(ANAF_CAEN, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.reader(f, delimiter="^")
            next(reader, None)
            for row in reader:
                if len(row) >= 2:
                    key = row[0].strip()
                    code = row[1].strip()
                    if key:
                        caen[key] = code
    return stare, caen

def build_mrc_indexes():
    name_to_cui = {}
    phone_to_cui = {}
    cui_to_contact = {}
    if MRC.exists():
        with open(MRC, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = (row.get("cui") or "").strip()
                name = (row.get("name") or row.get("name_normalized") or "").strip().upper()
                phone = (row.get("phone") or "").strip()
                email = (row.get("email") or "").strip()
                if cui and name and name not in name_to_cui:
                    name_to_cui[name] = cui
                if cui and phone and phone not in phone_to_cui:
                    phone_to_cui[phone] = cui
                if cui:
                    if cui not in cui_to_contact:
                        cui_to_contact[cui] = {"email": email, "phone": phone}
    if MRC_CONTACTS.exists():
        with open(MRC_CONTACTS, "r", encoding="utf-8-sig", errors="replace", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cui = (row.get("cui") or "").strip()
                name = (row.get("company_name") or "").strip().upper()
                email = (row.get("email") or "").strip()
                phone = (row.get("phone") or "").strip()
                if cui and name and name not in name_to_cui:
                    name_to_cui[name] = cui
                if cui and cui not in cui_to_contact:
                    cui_to_contact[cui] = {"email": email, "phone": phone}
    return name_to_cui, phone_to_cui, cui_to_contact

def clean_company_name(name):
    name = str(name).strip()
    name = re.sub(r"^(SC|SRL|SA|PFA|II|I\.I\.)\s+", "", name, flags=re.IGNORECASE).strip()
    name = re.sub(r"\b(SRL|SA|PFA|II|I\.I\.|SC|FILIAL|FILIA)\b.*$", "", name, flags=re.IGNORECASE).strip()
    return name[:50] if name else name

def run(sample=None, skip_anaf=False):
    if not MASTER_CSV.exists():
        raise SystemExit(f"[ERR] Missing master source: {MASTER_CSV}")
    conn = get_connection(DB_PATH)
    install_schema(conn)
    if not skip_anaf:
        print("[LOAD] ANAF indexes...", flush=True)
        stare_index, caen_index = build_anaf_indexes()
        print(f"  stare: {len(stare_index)} | caen: {len(caen_index)}", flush=True)
    print("[LOAD] ROMANIA_DB indexes...", flush=True)
    name_to_cui, phone_to_cui, cui_to_contact = build_mrc_indexes()
    print(f"  name->cui: {len(name_to_cui)} | phone->cui: {len(phone_to_cui)} | cui->contact: {len(cui_to_contact)}", flush=True)
    with open(MASTER_CSV, "r", encoding="utf-8-sig", newline="") as f:
        records = list(csv.DictReader(f))
    if sample:
        records = records[:sample]
    print(f"[LOAD] {len(records)} silos", flush=True)
    enriched = 0
    for i, rec in enumerate(records, 1):
        if i % 100 == 0:
            print(f"  [{i}/{len(records)}]", flush=True)
        email = (rec.get("email") or "").strip()
        cui = (rec.get("cui") or "").strip()
        if email and cui:
            continue
        phone = (rec.get("phone") or "").strip()
        name = clean_company_name(rec.get("name", ""))
        name_up = name.upper()
        lookup_cui = name_to_cui.get(name_up)
        if not lookup_cui and phone:
            lookup_cui = phone_to_cui.get(phone)
        if lookup_cui:
            cui = cui or lookup_cui
        contact = cui_to_contact.get(cui or "")
        if contact:
            email = email or contact.get("email") or ""
            phone = phone or contact.get("phone") or ""
        mapped = {
            "auth_code": (rec.get("auth_code") or "").strip() or None,
            "name": (rec.get("name") or "").strip() or None,
            "phone": phone or None,
            "email": email or None,
            "county": (rec.get("county") or "").strip() or None,
            "city": (rec.get("city") or "").strip() or None,
            "cui": cui or None,
            "caen": (rec.get("caen") or "").strip() or None,
            "capacity_total_t": rec.get("capacity_total_t") or 0,
            "capacity_grains_t": rec.get("capacity_grains_t") or 0,
            "capacity_oilseeds_t": rec.get("capacity_oilseeds_t") or 0,
            "_source": rec.get("_source") or rec.get("source"),
            "_quality_tier": rec.get("_quality_tier") or rec.get("quality_tier"),
            "_issues": rec.get("_issues") or rec.get("issues"),
        }
        ingest_row(conn, mapped)
        enriched += 1
    conn.commit()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM facilities")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM facilities WHERE email IS NOT NULL AND TRIM(email) <> ''")
    with_email = cur.fetchone()[0]
    conn.close()
    print(f"\n[OK] enriched_attempted={enriched} total={total} with_email={with_email}", flush=True)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--sample", type=int, default=None)
    p.add_argument("--skip-anaf", action="store_true")
    args = p.parse_args()
    run(sample=args.sample, skip_anaf=args.skip_anaf)
