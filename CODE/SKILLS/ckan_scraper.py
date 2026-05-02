#!/usr/bin/env python3
"""
CKAN Scraper Skill - Generic CKAN API client for European open data portals.

Supports:
- Dataset search and discovery
- Resource download (CSV, JSON, XML)
- Datastore queries (if enabled)
- Multiple EU country portals

Usage:
    python3 ckan_scraper.py --portal SI --search "podjetja"
    python3 ckan_scraper.py --portal SI --list-datasets
    python3 ckan_scraper.py --portal SI --download DATASET_ID
    python3 ckan_scraper.py --list-portals
"""

import argparse
import csv
import json
import os
import sys
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin, quote

# Add shared path
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

try:
    from skills_common import to_ascii, fetch_url, send_telegram
except ImportError:
    # Fallback implementations
    def to_ascii(text: str) -> str:
        if not text:
            return text
        normalized = unicodedata.normalize('NFKD', str(text))
        return normalized.encode('ascii', 'ignore').decode('ascii')

    def fetch_url(url: str, **kwargs) -> str:
        import urllib.request
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode('utf-8')

    def send_telegram(msg: str) -> None:
        print(f"[TELEGRAM] {msg}")

# =============================================================================
# CKAN Portal Configurations
# =============================================================================

CKAN_PORTALS = {
    # Slovenia
    "SI": {
        "name": "OPSI - Slovenia",
        "url": "https://podatki.gov.si",
        "api_url": "https://podatki.gov.si/api/3/action/",
        "language": "sl",
        "country": "SLOVENIA",
        "datasets": {
            "companies": ["prs", "ajpes", "podjetja", "firme"],
            "employers": ["delodajalci", "zaposlovanje"],
        }
    },
    # Portugal
    "PT": {
        "name": "dados.gov.pt - Portugal",
        "url": "https://dados.gov.pt",
        "api_url": "https://dados.gov.pt/api/3/action/",
        "language": "pt",
        "country": "PORTUGAL",
        "datasets": {
            "companies": ["empresas", "sociedades", "nif"],
        }
    },
    # Greece
    "GR": {
        "name": "data.gov.gr - Greece",
        "url": "https://data.gov.gr",
        "api_url": "https://data.gov.gr/api/3/action/",
        "language": "el",
        "country": "GREECE",
        "datasets": {
            "companies": ["epicheiriseis", "etaireies"],
        }
    },
    # Hungary
    "HU": {
        "name": "data.gov.hu - Hungary",
        "url": "https://data.gov.hu",
        "api_url": "https://data.gov.hu/api/3/action/",
        "language": "hu",
        "country": "HUNGARY",
        "datasets": {
            "companies": ["cegek", "vallalkozasok"],
        }
    },
    # Slovakia
    "SK": {
        "name": "data.gov.sk - Slovakia",
        "url": "https://data.gov.sk",
        "api_url": "https://data.gov.sk/api/3/action/",
        "language": "sk",
        "country": "SLOVAKIA",
        "datasets": {
            "companies": ["firmy", "podniky", "obchodny-register"],
        }
    },
    # Estonia
    "EE": {
        "name": "opendata.riik.ee - Estonia",
        "url": "https://opendata.riik.ee",
        "api_url": "https://opendata.riik.ee/api/3/action/",
        "language": "et",
        "country": "ESTONIA",
        "datasets": {
            "companies": ["ettevotted", "ariregister"],
        }
    },
    # Latvia
    "LV": {
        "name": "data.gov.lv - Latvia",
        "url": "https://data.gov.lv",
        "api_url": "https://data.gov.lv/api/3/action/",
        "language": "lv",
        "country": "LATVIA",
        "datasets": {
            "companies": ["uznemumi", "komersanti"],
        }
    },
    # Lithuania
    "LT": {
        "name": "data.gov.lt - Lithuania",
        "url": "https://data.gov.lt",
        "api_url": "https://data.gov.lt/api/3/action/",
        "language": "lt",
        "country": "LITHUANIA",
        "datasets": {
            "companies": ["imones", "juridiniai-asmenys"],
        }
    },
    # EU-wide
    "EU": {
        "name": "data.europa.eu - EU Open Data",
        "url": "https://data.europa.eu",
        "api_url": "https://data.europa.eu/api/hub/search/",
        "language": "en",
        "country": "EU27",
        "datasets": {
            "companies": ["company", "business", "enterprise"],
            "employers": ["employer", "employment"],
        }
    },
}


# =============================================================================
# CKAN API Client
# =============================================================================

class CKANClient:
    """Generic CKAN API client."""

    def __init__(self, portal_code: str):
        """Initialize client for a specific portal."""
        if portal_code not in CKAN_PORTALS:
            raise ValueError(f"Unknown portal: {portal_code}. Use --list-portals to see available.")

        self.portal = CKAN_PORTALS[portal_code]
        self.portal_code = portal_code
        self.api_url = self.portal["api_url"]
        self.country = self.portal["country"]
        self.output_dir = Path(f"/opt/ACTIVE/OPENDATA/DATA/{self.country}")

        # Ensure output directories exist
        for subdir in ["COMPANIES", "JOBS", "AGENCIES", "EMPLOYERS", "RAW"]:
            (self.output_dir / subdir).mkdir(parents=True, exist_ok=True)

    def _api_call(self, action: str, params: Optional[Dict] = None) -> Dict:
        """Make CKAN API call."""
        url = urljoin(self.api_url, action)

        if params:
            query_string = "&".join(f"{k}={quote(str(v))}" for k, v in params.items())
            url = f"{url}?{query_string}"

        try:
            response = fetch_url(url)
            data = json.loads(response)

            if not data.get("success", False):
                error = data.get("error", {})
                raise Exception(f"CKAN API error: {error}")

            return data.get("result", {})
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response from {url}: {e}")
        except Exception as e:
            raise Exception(f"API call failed: {e}")

    def search_datasets(self, query: str, rows: int = 100) -> List[Dict]:
        """Search for datasets."""
        result = self._api_call("package_search", {
            "q": query,
            "rows": rows
        })
        return result.get("results", [])

    def list_datasets(self, limit: int = 100) -> List[str]:
        """List all dataset IDs."""
        result = self._api_call("package_list", {"limit": limit})
        return result if isinstance(result, list) else []

    def get_dataset(self, dataset_id: str) -> Dict:
        """Get dataset details."""
        return self._api_call("package_show", {"id": dataset_id})

    def get_resource(self, resource_id: str) -> Dict:
        """Get resource details."""
        return self._api_call("resource_show", {"id": resource_id})

    def datastore_search(self, resource_id: str, limit: int = 1000,
                         filters: Optional[Dict] = None) -> Dict:
        """Query datastore directly (if enabled)."""
        params = {"resource_id": resource_id, "limit": limit}
        if filters:
            params["filters"] = json.dumps(filters)
        return self._api_call("datastore_search", params)

    def download_resource(self, resource_url: str, output_path: Path) -> bool:
        """Download a resource file."""
        try:
            import urllib.request

            headers = {'User-Agent': 'Mozilla/5.0 (CKAN Scraper)'}
            req = urllib.request.Request(resource_url, headers=headers)

            with urllib.request.urlopen(req, timeout=120) as resp:
                content = resp.read()

                with open(output_path, 'wb') as f:
                    f.write(content)

            return True
        except Exception as e:
            print(f"Download failed: {e}")
            return False

    def find_company_datasets(self) -> List[Dict]:
        """Find datasets related to companies/businesses."""
        keywords = self.portal.get("datasets", {}).get("companies", [])
        all_results = []

        for keyword in keywords:
            results = self.search_datasets(keyword)
            all_results.extend(results)

        # Deduplicate by ID
        seen = set()
        unique = []
        for r in all_results:
            if r.get("id") not in seen:
                seen.add(r.get("id"))
                unique.append(r)

        return unique

    def extract_csv_resources(self, dataset: Dict) -> List[Dict]:
        """Extract CSV resources from a dataset."""
        resources = dataset.get("resources", [])
        csv_resources = []

        for r in resources:
            fmt = r.get("format", "").upper()
            if fmt in ["CSV", "TEXT/CSV", "APPLICATION/CSV"]:
                csv_resources.append(r)

        return csv_resources

    def download_dataset(self, dataset_id: str,
                         target_subdir: str = "RAW") -> List[Path]:
        """Download all CSV resources from a dataset."""
        dataset = self.get_dataset(dataset_id)
        csv_resources = self.extract_csv_resources(dataset)

        downloaded = []
        target_dir = self.output_dir / target_subdir

        for resource in csv_resources:
            url = resource.get("url")
            name = resource.get("name", resource.get("id", "unknown"))
            name = to_ascii(name).replace(" ", "_").replace("/", "_")

            # Add timestamp
            timestamp = datetime.now().strftime("%Y%m%d")
            filename = f"{name}_{timestamp}.csv"
            output_path = target_dir / filename

            print(f"Downloading: {name}")
            if self.download_resource(url, output_path):
                downloaded.append(output_path)
                print(f"  Saved to: {output_path}")

        return downloaded

    def process_company_data(self, csv_path: Path) -> Tuple[int, Path]:
        """Process raw CSV into standard 50-column format."""
        # Read raw CSV
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        if not rows:
            return 0, csv_path

        # Standard columns
        standard_cols = [
            "company", "country", "county", "city", "address", "postal_code",
            "category", "subcategory", "type", "registration_id",
            "email", "email2", "email3", "phone", "phone2", "phone3",
            "website", "contact_person", "contact_dept", "contact_title",
            "products", "services", "activity", "employees", "revenue",
            "founded", "vat_id", "cui", "status", "notes",
            "anofm_email", "anofm_phone", "anofm_address", "web_email",
            "web_phone", "web_website", "best_email", "best_phone",
            "best_address", "verified",
            "source_file", "source_system", "scrape_date", "update_date",
            "export_date", "priority", "score", "tags", "campaign_id", "notes2"
        ]

        # Field mapping (common CKAN field names to standard)
        field_map = {
            # Company name variants
            "naziv": "company", "ime": "company", "name": "company",
            "firma": "company", "podjetje": "company", "naziv_podjetja": "company",
            "company_name": "company", "business_name": "company",

            # Address variants
            "naslov": "address", "ulica": "address", "address": "address",
            "street": "address", "location": "address",

            # City variants
            "kraj": "city", "mesto": "city", "city": "city",
            "settlement": "city", "obcina": "county",

            # Postal code
            "posta": "postal_code", "postna_stevilka": "postal_code",
            "zip": "postal_code", "postal_code": "postal_code",

            # Registration ID
            "maticna_stevilka": "registration_id", "maticna": "registration_id",
            "registration_number": "registration_id", "reg_number": "registration_id",
            "company_id": "registration_id",

            # VAT / Tax ID
            "davcna_stevilka": "vat_id", "davcna": "vat_id",
            "vat": "vat_id", "tax_id": "vat_id", "nif": "vat_id",

            # Contact
            "email": "email", "e_mail": "email", "e-mail": "email",
            "telefon": "phone", "phone": "phone", "tel": "phone",
            "spletna_stran": "website", "website": "website", "web": "website",

            # Activity
            "dejavnost": "activity", "activity": "activity",
            "nace": "category", "sic": "category",

            # Status
            "status": "status", "stanje": "status",

            # Employees
            "zaposleni": "employees", "stevilo_zaposlenih": "employees",
            "employees": "employees", "employee_count": "employees",
        }

        # Process rows
        processed = []
        for row in rows:
            new_row = {col: "" for col in standard_cols}
            new_row["country"] = self.portal_code
            new_row["source_system"] = f"CKAN:{self.portal['name']}"
            new_row["scrape_date"] = datetime.now().strftime("%Y-%m-%d")
            new_row["source_file"] = csv_path.name

            # Map fields
            for old_key, value in row.items():
                old_key_lower = old_key.lower().strip()
                if old_key_lower in field_map:
                    target = field_map[old_key_lower]
                    new_row[target] = to_ascii(str(value).strip())

            # Only add if we have a company name
            if new_row.get("company"):
                processed.append(new_row)

        # Write to COMPANIES directory
        output_path = self.output_dir / "COMPANIES" / f"companies_{datetime.now().strftime('%Y%m%d')}.csv"

        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=standard_cols)
            writer.writeheader()
            writer.writerows(processed)

        return len(processed), output_path


# =============================================================================
# CLI
# =============================================================================

def list_portals():
    """List all available CKAN portals."""
    print("=== Available CKAN Portals ===\n")
    for code, portal in CKAN_PORTALS.items():
        print(f"{code:4} | {portal['name']}")
        print(f"     | URL: {portal['url']}")
        print(f"     | Language: {portal['language']}")
        print()


def main():
    parser = argparse.ArgumentParser(
        description="CKAN Scraper - European Open Data Portal Client"
    )

    parser.add_argument("--portal", "-p", help="Portal code (SI, PT, GR, etc.)")
    parser.add_argument("--list-portals", action="store_true", help="List available portals")
    parser.add_argument("--search", "-s", help="Search datasets by keyword")
    parser.add_argument("--list-datasets", action="store_true", help="List all datasets")
    parser.add_argument("--download", "-d", help="Download dataset by ID")
    parser.add_argument("--find-companies", action="store_true",
                        help="Find company-related datasets")
    parser.add_argument("--download-companies", action="store_true",
                        help="Download and process company datasets")
    parser.add_argument("--info", help="Show dataset info")
    parser.add_argument("--limit", type=int, default=100, help="Result limit")
    parser.add_argument("--output-dir", "-o", help="Override output directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done")

    args = parser.parse_args()

    if args.list_portals:
        list_portals()
        return

    if not args.portal:
        print("Error: --portal required. Use --list-portals to see options.")
        sys.exit(1)

    try:
        client = CKANClient(args.portal)
        print(f"Connected to: {client.portal['name']}")
        print(f"Output dir: {client.output_dir}")
        print()

        if args.search:
            print(f"Searching for: {args.search}")
            results = client.search_datasets(args.search, rows=args.limit)
            print(f"Found {len(results)} datasets:\n")
            for r in results:
                print(f"  ID: {r.get('id')}")
                print(f"  Title: {r.get('title', 'N/A')}")
                print(f"  Resources: {len(r.get('resources', []))}")
                print()

        elif args.list_datasets:
            print("Listing datasets...")
            datasets = client.list_datasets(limit=args.limit)
            print(f"Found {len(datasets)} datasets:\n")
            for ds in datasets[:50]:  # Show first 50
                print(f"  - {ds}")
            if len(datasets) > 50:
                print(f"  ... and {len(datasets) - 50} more")

        elif args.info:
            print(f"Dataset info: {args.info}")
            dataset = client.get_dataset(args.info)
            print(f"\nTitle: {dataset.get('title')}")
            print(f"ID: {dataset.get('id')}")
            print(f"Notes: {dataset.get('notes', 'N/A')[:200]}...")
            print(f"\nResources ({len(dataset.get('resources', []))}):")
            for r in dataset.get("resources", []):
                print(f"  - {r.get('name')} ({r.get('format')})")
                print(f"    URL: {r.get('url')}")

        elif args.find_companies:
            print("Finding company-related datasets...")
            datasets = client.find_company_datasets()
            print(f"Found {len(datasets)} company datasets:\n")
            for ds in datasets:
                csv_count = len(client.extract_csv_resources(ds))
                print(f"  ID: {ds.get('id')}")
                print(f"  Title: {ds.get('title', 'N/A')}")
                print(f"  CSV resources: {csv_count}")
                print()

        elif args.download:
            if args.dry_run:
                print(f"[DRY RUN] Would download dataset: {args.download}")
                dataset = client.get_dataset(args.download)
                for r in client.extract_csv_resources(dataset):
                    print(f"  Would download: {r.get('name')} ({r.get('format')})")
            else:
                print(f"Downloading dataset: {args.download}")
                downloaded = client.download_dataset(args.download)
                print(f"\nDownloaded {len(downloaded)} files")

        elif args.download_companies:
            print("Finding and downloading company datasets...")
            datasets = client.find_company_datasets()

            if not datasets:
                print("No company datasets found.")
                return

            if args.dry_run:
                print(f"[DRY RUN] Would download {len(datasets)} datasets:")
                for ds in datasets:
                    print(f"  - {ds.get('title', ds.get('id'))}")
                return

            total_files = 0
            total_records = 0

            for ds in datasets:
                print(f"\nProcessing: {ds.get('title', ds.get('id'))}")
                downloaded = client.download_dataset(ds.get("id"))
                total_files += len(downloaded)

                # Process each downloaded CSV
                for csv_path in downloaded:
                    count, output = client.process_company_data(csv_path)
                    total_records += count
                    if count > 0:
                        print(f"  Processed {count} companies -> {output}")

            print(f"\n=== Summary ===")
            print(f"Downloaded: {total_files} files")
            print(f"Processed: {total_records} company records")
            print(f"Output: {client.output_dir / 'COMPANIES'}")

        else:
            parser.print_help()

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
