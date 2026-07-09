#!/usr/bin/env python3
"""
Worker 4: Registry Bulk Download
Downloads bulk company registry data and filters by export-relevant sectors
Targets: Brazil CNPJ, Chile SII
"""

import argparse
import csv
import gzip
import json
import os
import random
import re
import shutil
import time
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse

import requests

# Import shared utilities
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii, sanitize
except ImportError:
    def to_ascii(text): return text if not text else text.encode('ascii', 'ignore').decode()
    def sanitize(text, *args): return to_ascii(text)[:200] if text else ""

from config import OUTPUT_BASE, REGISTRIES, REQUEST_DELAY, TIMEOUTS, USER_AGENTS

OUTPUT_DIR = OUTPUT_BASE / "registries"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DOWNLOAD_DIR = OUTPUT_DIR / "downloads"
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [registries] {msg}")


def get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": random.choice(USER_AGENTS),
    })
    return session


# CNAE codes for export-relevant sectors (Brazil)
EXPORT_CNAE_CODES = {
    # Agriculture
    "0111": "Rice", "0115": "Soy", "0116": "Coffee",
    # Livestock
    "0151": "Cattle", "0152": "Poultry", "0155": "Pigs",
    # Food Processing
    "1011": "Beef processing", "1012": "Poultry processing",
    "1061": "Grain milling", "1066": "Vegetable oil",
    "1031": "Fruit processing", "1032": "Vegetables",
    # Mining
    "0710": "Iron ore", "0721": "Uranium", "0723": "Copper",
    "0729": "Other metals (lithium/niobium)",
    # Manufacturing
    "2910": "Motor vehicles", "2920": "Auto parts",
    "2811": "Engines", "2822": "Machinery",
}


def download_file(url: str, dest_path: Path) -> bool:
    """Download file with progress"""
    session = get_session()

    try:
        response = session.get(url, stream=True, timeout=TIMEOUTS["request"])
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0))
        downloaded = 0

        with open(dest_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
                downloaded += len(chunk)
                if total and downloaded % (1024 * 1024) == 0:
                    log(f"  Downloaded {downloaded // (1024 * 1024)} MB")

        return True

    except Exception as e:
        log(f"Download error: {e}")
        return False


def extract_archive(archive_path: Path, dest_dir: Path) -> List[Path]:
    """Extract zip or gz archive"""
    extracted = []

    try:
        if archive_path.suffix == ".zip":
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest_dir)
                extracted = [dest_dir / name for name in zf.namelist()]

        elif archive_path.suffix == ".gz":
            output_path = dest_dir / archive_path.stem
            with gzip.open(archive_path, "rb") as f_in:
                with open(output_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            extracted = [output_path]

    except Exception as e:
        log(f"Extract error: {e}")

    return extracted


def process_cnpj_file(file_path: Path, filter_codes: List[str]) -> List[Dict]:
    """Process Brazilian CNPJ data file"""
    results = []
    code_set = set(filter_codes)

    try:
        # CNPJ files are typically CSV with specific encoding
        with open(file_path, "r", encoding="latin-1", errors="ignore") as f:
            reader = csv.reader(f, delimiter=";")

            for row in reader:
                try:
                    if len(row) < 10:
                        continue

                    # CNPJ file structure varies, common positions:
                    # cnpj, razao_social, nome_fantasia, cnae_principal, ...
                    cnae = str(row[3])[:4] if len(row) > 3 else ""

                    if cnae in code_set:
                        company = {
                            "name": sanitize(row[1] if len(row) > 1 else "", "company"),
                            "trade_name": sanitize(row[2] if len(row) > 2 else "", "company"),
                            "cnpj": row[0] if row else "",
                            "cnae": cnae,
                            "sector": EXPORT_CNAE_CODES.get(cnae, ""),
                            "country": "Brazil",
                            "source": "CNPJ Registry",
                            "email": "",
                            "website": "",
                        }

                        # Look for email in remaining columns
                        for col in row[5:]:
                            if "@" in str(col):
                                company["email"] = sanitize(str(col).lower(), "email")
                                break

                        if company["name"]:
                            results.append(company)

                except Exception as e:
                    continue

    except Exception as e:
        log(f"CNPJ processing error: {e}")

    return results


def scrape_brazil_cnpj(registry: Dict) -> List[Dict]:
    """Scrape Brazil CNPJ public data"""
    log("Scraping Brazil CNPJ registry...")

    session = get_session()
    results = []
    filter_codes = registry.get("filter_codes", list(EXPORT_CNAE_CODES.keys()))

    # dados.gov.br API for CNPJ
    api_url = "https://dados.gov.br/api/publico/conjuntos-dados"
    search_url = f"{api_url}?q=cnpj&pagina=1"

    try:
        response = session.get(search_url, timeout=TIMEOUTS["request"])
        if response.status_code == 200:
            data = response.json()

            # Find download links
            for resource in data.get("recursos", []):
                url = resource.get("url", "")
                if "empresa" in url.lower() and url.endswith((".zip", ".csv")):
                    log(f"Found CNPJ resource: {url}")

                    # Check file size before downloading
                    try:
                        head = session.head(url, timeout=10)
                        size_mb = int(head.headers.get("content-length", 0)) / (1024 * 1024)
                        if size_mb > 500:
                            log(f"  Skipping large file ({size_mb:.0f} MB)")
                            continue
                    except:
                        pass

                    # Download sample
                    dest = DOWNLOAD_DIR / Path(urlparse(url).path).name
                    if download_file(url, dest):
                        if dest.suffix == ".zip":
                            extracted = extract_archive(dest, DOWNLOAD_DIR)
                            for f in extracted[:1]:  # Process first file
                                results.extend(process_cnpj_file(f, filter_codes))
                        elif dest.suffix == ".csv":
                            results.extend(process_cnpj_file(dest, filter_codes))

                    break  # Only process first matching file

    except Exception as e:
        log(f"Brazil CNPJ API error: {e}")

    # Alternative: Use web scraping fallback
    if not results:
        log("Trying fallback scraping...")
        # Scrape from portal page
        portal_url = registry.get("url", "")
        try:
            response = session.get(portal_url, timeout=TIMEOUTS["request"])
            if response.status_code == 200:
                # Look for download links
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")

                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if "download" in href.lower() and "empresa" in href.lower():
                        log(f"Found potential download: {href}")
                        break

        except Exception as e:
            log(f"Fallback scraping error: {e}")

    return results[:10000]  # Limit results


def scrape_chile_sii(registry: Dict) -> List[Dict]:
    """Scrape Chile SII exporter data"""
    log("Scraping Chile SII registry...")

    session = get_session()
    results = []

    # Chile SII statistics page
    try:
        response = session.get(registry.get("url", ""), timeout=TIMEOUTS["request"])
        if response.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, "html.parser")

            # Look for Excel/CSV download links
            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.get_text(strip=True).lower()

                if any(x in text for x in ["exportador", "comercio", "empresa"]):
                    if any(href.endswith(ext) for ext in [".xlsx", ".xls", ".csv"]):
                        log(f"Found Chile data: {href}")

                        # Download and process
                        full_url = href if href.startswith("http") else f"https://www.sii.cl{href}"
                        dest = DOWNLOAD_DIR / Path(urlparse(full_url).path).name

                        if download_file(full_url, dest):
                            # Process based on file type
                            if dest.suffix == ".csv":
                                with open(dest, "r", encoding="utf-8", errors="ignore") as f:
                                    reader = csv.DictReader(f)
                                    for row in reader:
                                        company = {
                                            "name": sanitize(row.get("razon_social", row.get("nombre", "")), "company"),
                                            "rut": row.get("rut", ""),
                                            "sector": row.get("actividad", ""),
                                            "country": "Chile",
                                            "source": "Chile SII",
                                            "email": "",
                                            "website": "",
                                        }
                                        if company["name"]:
                                            results.append(company)

                        break

    except Exception as e:
        log(f"Chile SII error: {e}")

    return results[:5000]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--registry", type=str, help="Specific registry")
    parser.add_argument("--test", action="store_true", help="Test mode")
    args = parser.parse_args()

    log("Starting registry bulk downloader")

    all_results = []

    # Process each registry
    for reg_key, registry in REGISTRIES.items():
        if args.registry and args.registry != reg_key:
            continue

        log(f"Processing {registry.get('name', reg_key)}...")

        if "brazil" in reg_key.lower() or "cnpj" in reg_key.lower():
            results = scrape_brazil_cnpj(registry)
        elif "chile" in reg_key.lower() or "sii" in reg_key.lower():
            results = scrape_chile_sii(registry)
        else:
            log(f"No handler for {reg_key}")
            continue

        log(f"  Found {len(results)} companies")
        all_results.extend(results)

        time.sleep(random.uniform(*REQUEST_DELAY))

    # Deduplicate
    seen = set()
    unique_results = []
    for r in all_results:
        key = r.get("name", "").lower()
        if key and key not in seen:
            seen.add(key)
            unique_results.append(r)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    json_file = OUTPUT_DIR / f"registries_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(unique_results, f, indent=2)

    csv_file = OUTPUT_DIR / f"registries_{timestamp}.csv"
    if unique_results:
        with open(csv_file, "w", newline="") as f:
            fieldnames = ["name", "country", "sector", "website", "email", "source"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(unique_results)

    log("=" * 50)
    log("SUMMARY")
    log(f"Total companies: {len(unique_results)}")
    log(f"JSON: {json_file}")
    log(f"CSV: {csv_file}")
    log("=" * 50)


if __name__ == "__main__":
    main()
