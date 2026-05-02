#!/usr/bin/env python3
"""
ONRC Updater - Downloads latest ONRC data and imports new companies
Run monthly: 0 3 1 * * /opt/venv/bin/python3 /opt/SKILLS/onrc_updater.py --full

Usage:
    python3 onrc_updater.py --check      # Check for updates only
    python3 onrc_updater.py --download   # Download latest
    python3 onrc_updater.py --import     # Import new CUIs
    python3 onrc_updater.py --full       # Full update (download + import)
"""
import os
import sys
import csv
import json
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
from pathlib import Path
import re
import argparse

DATA_DIR = Path("/mnt/hdd/DATA/ONRC")
STATE_FILE = DATA_DIR / "update_state.json"
CKAN_API = "https://data.gov.ro/api/3/action/package_search"

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"last_update": None, "last_dataset": None}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2))

def find_latest_onrc():
    """Find latest ONRC firme dataset on data.gov.ro"""
    log("Searching for latest ONRC dataset...")
    params = {"q": "firme", "fq": "organization:onrc", "rows": 10}
    r = requests.get(CKAN_API, params=params, timeout=30)
    r.raise_for_status()
    
    results = r.json()["result"]["results"]
    for ds in results:
        title_lower = ds["title"].lower()
        if "firme" in title_lower and "registrul" in title_lower:
            # Find od_firme.csv resource
            for res in ds.get("resources", []):
                res_name = res.get("name", "").lower()
                if "od_firme" in res_name or "firme" in res_name:
                    return {
                        "title": ds["title"],
                        "id": ds["id"],
                        "modified": ds["metadata_modified"],
                        "url": res["url"],
                        "size": res.get("size", 0)
                    }
    return None

def download_onrc(dataset):
    """Download ONRC files"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    download_dir = DATA_DIR / date_str
    download_dir.mkdir(parents=True, exist_ok=True)
    
    log(f"Downloading to {download_dir}...")
    
    # Get all resources from dataset
    r = requests.get(f"https://data.gov.ro/api/3/action/package_show?id={dataset["id"]}", timeout=30)
    resources = r.json()["result"]["resources"]
    
    for res in resources:
        name = res["name"]
        url = res["url"]
        filepath = download_dir / name
        
        log(f"  Downloading {name}...")
        with requests.get(url, stream=True, timeout=300) as resp:
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
        log(f"  Done: {filepath.stat().st_size / 1024 / 1024:.1f} MB")
    
    return download_dir

def get_db_cuis():
    """Get all CUIs from database"""
    log("Loading CUIs from database...")
    conn = psycopg2.connect(dbname="romania")
    cur = conn.cursor()
    cur.execute("SELECT cui FROM companies WHERE cui IS NOT NULL")
    cuis = set(str(row[0]) for row in cur.fetchall())
    cur.close()
    conn.close()
    log(f"Database has {len(cuis):,} CUIs")
    return cuis

def parse_date(s):
    """Parse DD/MM/YYYY to YYYY-MM-DD"""
    if not s:
        return None
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", s.strip())
    if not m:
        return None
    d, mo, y = m.groups()
    d, mo = int(d), int(mo)
    if d < 1 or d > 31 or mo < 1 or mo > 12:
        return None
    return f"{y}-{mo:02d}-{d:02d}"

def import_new_companies(download_dir, db_cuis):
    """Import companies not in database"""
    firme_file = None
    for f in download_dir.glob("*irme*.csv"):
        firme_file = f
        break
    
    if not firme_file:
        log("ERROR: Could not find firme CSV file")
        return None
    
    log(f"Reading {firme_file}...")
    
    conn = psycopg2.connect(dbname="romania")
    cur = conn.cursor()
    
    batch = []
    batch_size = 10000
    count = 0
    inserted = 0
    skipped = 0
    source_tag = "RO_ONRC_" + datetime.now().strftime("%Y%m")
    
    with open(firme_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="^")
        for row in reader:
            cui = row.get("CUI", "").strip()
            if not cui or cui in db_cuis:
                skipped += 1
                continue
            
            addr = " ".join(filter(None, [
                row.get("ADR_DEN_STRADA", "").strip(),
                row.get("ADR_NR_STRADA", "").strip(),
                row.get("ADR_BLOC", "").strip()
            ]))
            
            founding_date = parse_date(row.get("DATA_INMATRICULARE", ""))
            name = row.get("DENUMIRE", "").strip()[:500]
            cui_int = int(cui) if cui.isdigit() else None
            
            batch.append((
                cui_int, name, name.upper(),
                row.get("COD_INMATRICULARE", "").strip() or None,
                row.get("FORMA_JURIDICA", "").strip() or None,
                row.get("ADR_JUDET", "").strip() or None,
                row.get("ADR_LOCALITATE", "").strip() or None,
                addr[:500] if addr else None,
                row.get("ADR_COD_POSTAL", "").strip() or None,
                row.get("WEB", "").strip() or None,
                founding_date,
                [source_tag]
            ))
            count += 1
            
            if len(batch) >= batch_size:
                result = execute_values(cur, """
                    INSERT INTO companies (cui, company_name, company_name_normalized, 
                        cod_inmatriculare, forma_juridica, county, city, address, 
                        postal_code, website, founding_date, sources)
                    VALUES %s
                    ON CONFLICT (cui) DO NOTHING
                    RETURNING id
                """, batch, fetch=True)
                inserted += len(result)
                conn.commit()
                log(f"Processed: {count:,} / Inserted: {inserted:,} / Skipped: {skipped:,}")
                batch = []
    
    if batch:
        result = execute_values(cur, """
            INSERT INTO companies (cui, company_name, company_name_normalized, 
                cod_inmatriculare, forma_juridica, county, city, address, 
                postal_code, website, founding_date, sources)
            VALUES %s
            ON CONFLICT (cui) DO NOTHING
            RETURNING id
        """, batch, fetch=True)
        inserted += len(result)
        conn.commit()
    
    cur.close()
    conn.close()
    
    return {"processed": count, "inserted": inserted, "skipped": skipped}

def main():
    parser = argparse.ArgumentParser(description="ONRC Data Updater")
    parser.add_argument("--check", action="store_true", help="Check for updates only")
    parser.add_argument("--download", action="store_true", help="Download latest dataset")
    parser.add_argument("--import", dest="do_import", action="store_true", help="Import new CUIs")
    parser.add_argument("--full", action="store_true", help="Full update (download + import)")
    parser.add_argument("--dir", help="Use existing download directory for import")
    args = parser.parse_args()
    
    if not any([args.check, args.download, args.do_import, args.full]):
        parser.print_help()
        return
    
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    state = load_state()
    
    # Check for updates
    dataset = find_latest_onrc()
    if not dataset:
        log("ERROR: Could not find ONRC dataset")
        return
    
    log(f"Latest: {dataset["title"]}")
    log(f"Modified: {dataset["modified"]}")
    
    if args.check:
        if state.get("last_dataset") == dataset["id"]:
            log("No new updates available")
        else:
            log("NEW UPDATE AVAILABLE!")
        return
    
    download_dir = None
    if args.dir:
        download_dir = Path(args.dir)
    elif args.download or args.full:
        download_dir = download_onrc(dataset)
        state["last_dataset"] = dataset["id"]
        state["last_download"] = str(download_dir)
        save_state(state)
    
    if args.do_import or args.full:
        if not download_dir:
            download_dir = Path(state.get("last_download", ""))
        if not download_dir.exists():
            log(f"ERROR: Download directory not found: {download_dir}")
            return
        
        db_cuis = get_db_cuis()
        result = import_new_companies(download_dir, db_cuis)
        
        if result:
            log(f"\n=== IMPORT COMPLETE ===")
            log(f"Processed: {result[processed]:,}")
            log(f"Inserted:  {result[inserted]:,}")
            log(f"Skipped:   {result[skipped]:,}")
            
            state["last_update"] = datetime.now().isoformat()
            state["last_result"] = result
            save_state(state)

if __name__ == "__main__":
    main()
