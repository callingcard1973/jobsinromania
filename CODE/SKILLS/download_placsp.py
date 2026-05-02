#!/usr/bin/env python3
"""
Spain PLACSP (Plataforma de Contratacion del Sector Publico) Downloader

Downloads Spanish public procurement data from:
- PLACSP Open Data (contrataciondelestado.es)
- datos.gob.es (Spanish national open data portal)
- Regional portals (Catalonia, Basque Country, etc.)

Output: /opt/ACTIVE/OPENDATA/DATA/SPAIN/PLACSP/
"""

import csv
import json
import os
import requests
import sys
import time
import unicodedata
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except:
    def to_ascii(text):
        if not text:
            return ""
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

OUTPUT_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/SPAIN/PLACSP")

# PLACSP endpoints
PLACSP_BASE = "https://contrataciondelestado.es"
PLACSP_OPENDATA = f"{PLACSP_BASE}/wps/portal/plataforma"
PLACSP_DATOS_ABIERTOS = f"{PLACSP_BASE}/wps/portal/plataforma/datos_abiertos"

# OpenPLACSP documentation
OPENPLACSP_DOC = f"{PLACSP_BASE}/datosabiertos/DGPE_PLACSP_OpenPLACSP_v.2.2.pdf"

# datos.gob.es API
DATOS_GOB_API = "https://datos.gob.es/apidata/catalog/dataset"
DATOS_GOB_BASE = "https://datos.gob.es"

# OCP Data Registry - Spain (reliable fallback)
OCP_SPAIN = "https://data.open-contracting.org/en/publication/89"
OCP_SPAIN_DOWNLOAD = "https://data.open-contracting.org/en/publication/89/download?name=full.csv.tar.gz"

# PLACSP datasets on datos.gob.es
DATOS_GOB_DATASETS = {
    "licitaciones_vigentes": {
        "id": "l01241152-licitaciones",
        "name": "Active Tenders",
        "url": "https://datos.gob.es/en/catalogo/l01241152-licitaciones"
    },
    "contratos_menores": {
        "id": "l01241152-contratos-menores",
        "name": "Minor Contracts (<40K EUR)",
        "url": "https://datos.gob.es/en/catalogo/l01241152-contratos-menores"
    },
    "contratos_adjudicados": {
        "id": "l01241152-contratos-adjudicados",
        "name": "Awarded Contracts",
        "url": "https://datos.gob.es/en/catalogo/l01241152-contratos-adjudicados"
    },
}

# Regional procurement portals
REGIONAL_PORTALS = {
    "catalonia": {
        "name": "Generalitat de Catalunya",
        "url": "https://contractaciopublica.gencat.cat/ecofin_pscp/AppJava/cap.pscp.expedients.csv",
    },
    "basque": {
        "name": "Gobierno Vasco",
        "url": "https://opendata.euskadi.eus/katalogoa/-/contratacion/",
    },
    "madrid": {
        "name": "Comunidad de Madrid",
        "url": "https://datos.madrid.es/egob/catalogo/201410-0-contratos-menores.csv",
    },
    "andalucia": {
        "name": "Junta de Andalucia",
        "url": "https://www.juntadeandalucia.es/datosabiertos/portal/dataset/contratos-menores",
    },
}


def download_file(url, output_path, chunk_size=8192):
    """Download a file with progress."""
    try:
        print(f"  Downloading: {url[:80]}...")
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; ProcurementBot/1.0)",
            "Accept": "*/*"
        }
        response = requests.get(url, stream=True, timeout=300, headers=headers)
        response.raise_for_status()

        total = int(response.headers.get('content-length', 0))
        downloaded = 0

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total:
                        pct = (downloaded * 100) // total
                        print(f"\r    Progress: {pct}% ({downloaded//1024}KB)", end="", flush=True)

        print(f"\n    Saved: {output_path} ({os.path.getsize(output_path)//1024}KB)")
        return True
    except Exception as e:
        print(f"    Error: {e}")
        return False


def query_datos_gob(dataset_id, limit=10000):
    """Query datos.gob.es API for datasets."""
    try:
        url = f"{DATOS_GOB_API}/{dataset_id}"
        response = requests.get(url, timeout=60)
        response.raise_for_status()
        data = response.json()

        # Get distributions (download links)
        distributions = data.get("result", {}).get("distribution", [])
        return distributions
    except Exception as e:
        print(f"    API Error: {e}")
        return []


def download_placsp_xml():
    """Download PLACSP XML feed (CODICE format)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" PLACSP XML/CODICE DOWNLOAD")
    print("="*60)

    # PLACSP provides CODICE (Spanish OCDS variant) XML feeds
    codice_urls = [
        # RSS/Atom feeds for recent tenders
        ("https://contrataciondelestado.es/sindicacion/sindicacion_643/licitacionesPerfilesContratanteComplworwfq.atom",
         "placsp_licitaciones.atom"),

        # CODICE format downloads
        ("https://contrataciondelestado.es/wps/wcm/connect/PLACSP_RAI/77cb5c35-c6b8-4424-bc35-1e5c7f1d8f5b/PlatasformaContratacion.xml",
         "placsp_plataforma.xml"),
    ]

    for url, filename in codice_urls:
        print(f"\n  File: {filename}")
        output_file = OUTPUT_DIR / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def download_from_datos_gob():
    """Download from datos.gob.es national portal."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" datos.gob.es DOWNLOAD")
    print("="*60)

    # Direct CSV download URLs from datos.gob.es
    datos_urls = [
        # State Administration contracts
        ("https://datos.gob.es/sites/default/files/contratos_menores_2024.csv",
         "contratos_menores_2024.csv"),
        ("https://datos.gob.es/sites/default/files/contratos_menores_2023.csv",
         "contratos_menores_2023.csv"),

        # Public sector contracts registry
        ("https://www.hacienda.gob.es/es-ES/CDI/Paginas/SisseguimientContra/Descargars.aspx",
         "registro_contratos_sector_publico.csv"),
    ]

    for url, filename in datos_urls:
        print(f"\n  File: {filename}")
        output_file = OUTPUT_DIR / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def download_regional():
    """Download from regional procurement portals."""
    regional_dir = OUTPUT_DIR / "REGIONAL"
    regional_dir.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" REGIONAL PORTALS DOWNLOAD")
    print("="*60)

    for region, info in REGIONAL_PORTALS.items():
        print(f"\n  Region: {info['name']}")

        if info['url'].endswith('.csv'):
            output_file = regional_dir / f"{region}_contratos.csv"
            download_file(info['url'], output_file)
        else:
            print(f"    Manual download required: {info['url']}")

        time.sleep(2)

    return True


def download_cofece():
    """Download from Spanish competition authority."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" COMPETITION DATA DOWNLOAD")
    print("="*60)

    # CNMC (Comision Nacional de los Mercados y la Competencia)
    cnmc_urls = [
        ("https://www.cnmc.es/sites/default/files/contratos_publicos_datos_abiertos.csv",
         "cnmc_contratos.csv"),
    ]

    for url, filename in cnmc_urls:
        print(f"\n  File: {filename}")
        output_file = OUTPUT_DIR / filename
        download_file(url, output_file)
        time.sleep(2)

    return True


def parse_codice_xml(xml_file):
    """Parse CODICE/PLACSP XML format."""
    records = []

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        # Handle namespaces
        namespaces = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'codice': 'urn:spain:contratacion:scheme',
        }

        for notice in root.findall('.//ContractNotice', namespaces) or root.iter():
            record = {}

            # Extract fields based on CODICE structure
            for elem in notice.iter():
                tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                text = (elem.text or '').strip()

                if tag == 'ID':
                    record['id'] = text
                elif tag == 'ContractFolderID':
                    record['contract_id'] = text
                elif tag == 'IssueDate':
                    record['date'] = text
                elif tag == 'Name' and 'title' not in record:
                    record['title'] = to_ascii(text)[:300]
                elif tag == 'ContractingPartyName':
                    record['authority'] = to_ascii(text)[:200]
                elif tag == 'ElectronicMail':
                    record['email'] = text.lower()
                elif tag == 'Telephone':
                    record['phone'] = text
                elif tag == 'WebsiteURI':
                    record['website'] = text[:200]
                elif tag == 'TotalAmount':
                    try:
                        record['value'] = float(text)
                    except:
                        pass
                elif tag == 'ItemClassificationCode':
                    record['cpv'] = text

            if record.get('id'):
                records.append(record)

    except Exception as e:
        print(f"    Error parsing XML: {e}")

    return records


def extract_contacts():
    """Extract contacts from downloaded PLACSP data."""
    print("\n" + "="*60)
    print(" EXTRACTING CONTACTS")
    print("="*60)

    contacts = []

    # Process CSV files
    for csv_file in OUTPUT_DIR.glob("*.csv"):
        if "contacts" in csv_file.name:
            continue

        print(f"\n  Processing: {csv_file.name}")
        try:
            with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
                # Try different delimiters
                sample = f.read(1024)
                f.seek(0)

                delimiter = ';' if ';' in sample else ','
                reader = csv.DictReader(f, delimiter=delimiter)

                for row in reader:
                    # Spanish column names
                    email = row.get('email', row.get('correo_electronico',
                             row.get('EMAIL', row.get('Email', ''))))
                    phone = row.get('telefono', row.get('TELEFONO',
                             row.get('Telefono', row.get('phone', ''))))
                    company = row.get('nombre_organo', row.get('entidad',
                               row.get('NOMBRE', row.get('Nombre', ''))))

                    if email or phone:
                        contact = {
                            'id': row.get('id', row.get('ID', row.get('expediente', ''))),
                            'company': to_ascii(company)[:200],
                            'city': to_ascii(row.get('localidad', row.get('ciudad', '')))[:100],
                            'province': row.get('provincia', ''),
                            'email': (email or '').lower()[:200],
                            'phone': (phone or '')[:50],
                            'website': row.get('url', row.get('web', ''))[:200],
                            'type': row.get('tipo_contrato', row.get('tipo', '')),
                            'value': row.get('importe', row.get('valor', '')),
                            'cpv': row.get('cpv', ''),
                            'country': 'ES',
                        }
                        contacts.append(contact)

        except Exception as e:
            print(f"    Error: {e}")

    # Process XML files
    for xml_file in OUTPUT_DIR.glob("*.xml"):
        print(f"\n  Processing: {xml_file.name}")
        records = parse_codice_xml(xml_file)
        for r in records:
            if r.get('email') or r.get('phone'):
                contacts.append({
                    'id': r.get('id', ''),
                    'company': r.get('authority', ''),
                    'city': '',
                    'province': '',
                    'email': r.get('email', ''),
                    'phone': r.get('phone', ''),
                    'website': r.get('website', ''),
                    'type': '',
                    'value': str(r.get('value', '')),
                    'cpv': r.get('cpv', ''),
                    'country': 'ES',
                })

    # Deduplicate
    seen_emails = set()
    unique_contacts = []
    for c in contacts:
        if c['email'] and c['email'] not in seen_emails:
            seen_emails.add(c['email'])
            unique_contacts.append(c)
        elif not c['email']:
            unique_contacts.append(c)

    # Save contacts
    if unique_contacts:
        output_file = OUTPUT_DIR / "placsp_contacts.csv"
        fieldnames = ['id', 'company', 'city', 'province', 'email', 'phone',
                      'website', 'type', 'value', 'cpv', 'country']

        with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(unique_contacts)

        print(f"\n  Extracted: {len(unique_contacts):,} contacts")
        print(f"  Saved: {output_file}")

    return unique_contacts


def download_ocp_spain():
    """Download Spain data from OCP Data Registry (most reliable)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n" + "="*60)
    print(" OCP DATA REGISTRY - SPAIN")
    print("="*60)

    ocp_file = OUTPUT_DIR / "spain_ocp_full.csv.tar.gz"
    if not ocp_file.exists():
        print(f"\n  Downloading from OCP Data Registry...")
        if download_file(OCP_SPAIN_DOWNLOAD, ocp_file):
            print("    OCP download successful!")
            return True
    else:
        print(f"    Skipping (exists): {ocp_file.name}")
        return True

    return False


def download_all():
    """Download all PLACSP data."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log_file = OUTPUT_DIR / "download.log"
    with open(log_file, "w") as f:
        f.write(f"PLACSP Download Started: {datetime.now()}\n\n")

    # 1. Download from OCP Registry (most reliable)
    download_ocp_spain()

    # 2. Download PLACSP XML/Atom feeds
    download_placsp_xml()

    # 3. Download from datos.gob.es
    download_from_datos_gob()

    # 4. Download regional data
    download_regional()

    # 5. Download competition data
    download_cofece()

    # 6. Extract contacts
    extract_contacts()

    with open(log_file, "a") as f:
        f.write(f"\nDownload Completed: {datetime.now()}\n")

    print("\n" + "="*60)
    print(" DOWNLOAD COMPLETE")
    print("="*60)
    print(f"\n  Output: {OUTPUT_DIR}")

    return True


def status():
    """Check download status."""
    print("\n" + "="*60)
    print(" PLACSP DOWNLOAD STATUS")
    print("="*60)

    if OUTPUT_DIR.exists():
        files = list(OUTPUT_DIR.rglob("*"))
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        print(f"\n  Directory: {OUTPUT_DIR}")
        print(f"  Files: {len([f for f in files if f.is_file()])}")
        print(f"  Size: {total_size / 1024 / 1024:.1f} MB")

        print("\n  Files:")
        for f in sorted(OUTPUT_DIR.glob("*")):
            if f.is_file():
                size = f.stat().st_size / 1024
                print(f"    {f.name}: {size:.1f} KB")
    else:
        print(f"\n  Directory not found: {OUTPUT_DIR}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Spanish PLACSP Data Downloader")
    parser.add_argument("--all", action="store_true", help="Download all sources")
    parser.add_argument("--xml", action="store_true", help="Download PLACSP XML")
    parser.add_argument("--datos", action="store_true", help="Download from datos.gob.es")
    parser.add_argument("--regional", action="store_true", help="Download regional data")
    parser.add_argument("--extract", action="store_true", help="Extract contacts")
    parser.add_argument("--status", action="store_true", help="Check download status")
    args = parser.parse_args()

    if args.status:
        status()
    elif args.all:
        download_all()
    elif args.xml:
        download_placsp_xml()
    elif args.datos:
        download_from_datos_gob()
    elif args.regional:
        download_regional()
    elif args.extract:
        extract_contacts()
    else:
        parser.print_help()
