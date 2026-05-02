#!/usr/bin/env python3
"""
TED Complete Extraction - Extract ALL data from TED XML files.

Extracts:
- Notice metadata (id, date, type)
- Contracting authority (buyer) with contact
- Contract details (value, CPV, type)
- Contract winners (contractors)
- Addresses, websites, phones, emails

Output: Complete CSV with all fields
"""

import csv
import os
import re
import sys
import tarfile
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
try:
    from skills_common import to_ascii
except:
    def to_ascii(text):
        if not text:
            return ""
        return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').strip()

BASE_DIR = Path("/opt/ACTIVE/OPENDATA/DATA/EU_TENDERS")
RAW_DIR = BASE_DIR / "RAW" / "MONTHLY"
CSV_DIR = BASE_DIR / "CSV"


def parse_eforms(xml_content):
    """Parse eForms XML (2024+ format) and extract all organizations."""
    records = []

    try:
        root = ET.fromstring(xml_content)

        # Define namespaces
        ns = {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'efac': 'http://data.europa.eu/p27/eforms-ubl-extension-aggregate-components/1',
            'efbc': 'http://data.europa.eu/p27/eforms-ubl-extension-basic-components/1',
            'efext': 'http://data.europa.eu/p27/eforms-ubl-extensions/1',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
        }

        # Extract notice metadata
        notice_id = ''
        pub_date = ''
        doc_type = root.tag.split('}')[-1] if '}' in root.tag else root.tag

        # Find publication info
        for pub in root.iter():
            tag = pub.tag.split('}')[-1] if '}' in pub.tag else pub.tag
            if tag == 'NoticePublicationID':
                notice_id = (pub.text or '').strip()
            elif tag == 'PublicationDate' and not pub_date:
                pub_date = (pub.text or '').strip()[:10]  # YYYY-MM-DD

        # Extract all organizations
        for org in root.iter():
            tag = org.tag.split('}')[-1] if '}' in org.tag else org.tag
            if tag != 'Organization':
                continue

            record = {
                'doc_id': notice_id,
                'notice_id': notice_id,
                'pub_date': pub_date,
                'doc_type': doc_type,
            }

            # Find Company element within Organization
            for elem in org.iter():
                etag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                text = (elem.text or '').strip()

                # Organization ID
                if etag == 'ID' and elem.get('schemeName') != 'organization':
                    if not record.get('authority_id'):
                        record['authority_id'] = text

                # Company name
                if etag == 'Name' and text:
                    if not record.get('authority'):
                        record['authority'] = to_ascii(text)[:200]

                # Address
                if etag == 'StreetName':
                    record['authority_address'] = to_ascii(text)[:200]
                if etag == 'CityName':
                    record['city'] = to_ascii(text)
                if etag == 'PostalZone':
                    record['postal_code'] = text
                if etag == 'IdentificationCode' and len(text) <= 3:
                    record['country'] = text[:2].upper()  # DEU -> DE
                if etag == 'CountrySubentityCode':
                    record['nuts'] = text

                # Contact
                if etag == 'ElectronicMail':
                    record['email'] = text.lower()
                if etag == 'Telephone':
                    record['phone'] = re.sub(r'[^\d+]', '', text)
                if etag == 'Telefax':
                    record['fax'] = re.sub(r'[^\d+]', '', text)

                # Company ID
                if etag == 'CompanyID':
                    record['authority_id'] = text

            # Only add if has name and email
            if record.get('authority') and record.get('email'):
                records.append(record)

    except Exception as e:
        pass

    return records


def parse_ted_complete(xml_content):
    """Parse TED XML and extract ALL useful fields."""
    record = {}
    contractors = []

    # Check if this is eForms format (UBL-based)
    if 'urn:oasis:names:specification:ubl' in xml_content[:500] or 'ContractAwardNotice' in xml_content[:500]:
        return parse_eforms(xml_content)

    try:
        root = ET.fromstring(xml_content)
        record['doc_id'] = root.get('DOC_ID', '')
        record['edition'] = root.get('EDITION', '')

        for elem in root.iter():
            tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
            text = (elem.text or '').strip()

            # Notice metadata
            if tag == 'NO_DOC_OJS':
                record['notice_id'] = to_ascii(text)
            elif tag == 'DATE_PUB':
                record['pub_date'] = text
            elif tag == 'LG_ORIG':
                record['language'] = text
            elif tag == 'ISO_COUNTRY':
                if 'country' not in record:
                    record['country'] = elem.get('VALUE', text).upper()[:2]

            # Document type
            elif tag == 'TD_DOCUMENT_TYPE':
                record['doc_type'] = elem.get('CODE', text)
            elif tag == 'NC_CONTRACT_NATURE':
                record['contract_nature'] = elem.get('CODE', text)
            elif tag == 'PR_PROC':
                record['procedure'] = elem.get('CODE', text)

            # Authority info
            elif tag == 'OFFICIALNAME':
                if 'authority' not in record:
                    record['authority'] = to_ascii(text)[:200]
            elif tag == 'NATIONALID':
                if 'authority_id' not in record:
                    record['authority_id'] = text
            elif tag == 'ADDRESS' and 'authority_address' not in record:
                record['authority_address'] = to_ascii(text)[:200]
            elif tag == 'TOWN' and 'city' not in record:
                record['city'] = to_ascii(text)
            elif tag == 'POSTAL_CODE' and 'postal_code' not in record:
                record['postal_code'] = text
            elif tag == 'E_MAIL' and 'email' not in record:
                record['email'] = text.lower()
            elif tag == 'PHONE' and 'phone' not in record:
                record['phone'] = re.sub(r'[^\d+]', '', text)
            elif tag == 'FAX' and 'fax' not in record:
                record['fax'] = re.sub(r'[^\d+]', '', text)
            elif tag == 'URL_GENERAL' and 'website' not in record:
                record['website'] = text[:200]
            elif tag == 'CONTACT_POINT' and 'contact_person' not in record:
                record['contact_person'] = to_ascii(text)[:100]

            # Authority type
            elif tag == 'AA_AUTHORITY_TYPE':
                record['authority_type'] = elem.get('CODE', text)
            elif tag == 'MA_MAIN_ACTIVITIES':
                record['main_activity'] = elem.get('CODE', text)

            # Title (English preferred)
            elif tag == 'ML_TI_DOC' and elem.get('LG') == 'EN':
                for child in elem:
                    ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    if ctag == 'TI_TEXT':
                        for p in child:
                            if p.text:
                                record['title'] = to_ascii(p.text)[:500]

            # CPV codes
            elif tag == 'CPV_CODE':
                code = elem.get('CODE', text)
                if code and 'cpv' not in record:
                    record['cpv'] = code[:8]
            elif tag == 'ORIGINAL_CPV':
                code = elem.get('CODE', '')
                record['cpv_desc'] = to_ascii(text)[:100]
                if code and 'cpv' not in record:
                    record['cpv'] = code[:8]

            # NUTS
            elif tag in ['PERFORMANCE_NUTS', 'CA_CE_NUTS']:
                code = elem.get('CODE', '')
                if code and 'nuts' not in record:
                    record['nuts'] = code

            # Values
            elif tag == 'VAL_TOTAL':
                try:
                    record['value'] = float(text.replace(',', ''))
                    record['currency'] = elem.get('CURRENCY', 'EUR')
                except:
                    pass
            elif tag == 'VAL_ESTIMATED_TOTAL' and 'value' not in record:
                try:
                    record['value'] = float(text.replace(',', ''))
                    record['currency'] = elem.get('CURRENCY', 'EUR')
                except:
                    pass

            # Dates
            elif tag == 'DATE_RECEIPT_TENDERS':
                record['deadline'] = text
            elif tag == 'DATE_DISPATCH_NOTICE':
                record['dispatch_date'] = text
            elif tag == 'DATE_CONCLUSION_CONTRACT':
                record['award_date'] = text

            # Tenders info
            elif tag == 'NB_TENDERS_RECEIVED':
                record['tenders_received'] = text

            # Contractor (winner)
            elif tag == 'CONTRACTOR':
                contractor = {}
                for child in elem.iter():
                    ctag = child.tag.split('}')[-1] if '}' in child.tag else child.tag
                    ctext = (child.text or '').strip()

                    if ctag == 'OFFICIALNAME':
                        contractor['name'] = to_ascii(ctext)[:200]
                    elif ctag == 'TOWN':
                        contractor['city'] = to_ascii(ctext)
                    elif ctag == 'COUNTRY':
                        contractor['country'] = child.get('VALUE', ctext)
                    elif ctag == 'URL':
                        contractor['website'] = ctext[:200]
                    elif ctag == 'ADDRESS':
                        contractor['address'] = to_ascii(ctext)[:200]

                if contractor.get('name'):
                    contractors.append(contractor)

        # Add contractors to record
        if contractors:
            record['contractor_1'] = contractors[0].get('name', '')
            record['contractor_1_city'] = contractors[0].get('city', '')
            record['contractor_1_country'] = contractors[0].get('country', '')
            record['contractor_1_website'] = contractors[0].get('website', '')
            if len(contractors) > 1:
                record['contractor_2'] = contractors[1].get('name', '')
            record['num_contractors'] = len(contractors)

    except Exception as e:
        pass

    return [record] if record.get('doc_id') else []


def process_tar_archive(tar, records, is_nested=True):
    """Process members of a tar archive, handling both nested and flat formats."""
    members = tar.getmembers()

    for member in members:
        # Handle nested tar.gz files (2024+ format: inside subdirectories like 01/)
        if member.name.endswith('.tar.gz') and member.isfile():
            daily_file = tar.extractfile(member)
            if not daily_file:
                continue
            try:
                with tarfile.open(fileobj=daily_file, mode='r:gz') as daily_tar:
                    for xml_member in daily_tar.getmembers():
                        if xml_member.name.endswith('.xml') and xml_member.isfile():
                            xml_file = daily_tar.extractfile(xml_member)
                            if xml_file:
                                content = xml_file.read().decode('utf-8', errors='ignore')
                                parsed = parse_ted_complete(content)
                                if parsed:
                                    records.extend(parsed)
                                    if len(records) % 10000 == 0:
                                        print(f"\r    Records: {len(records):,}", end="", flush=True)
            except Exception as e:
                continue
        # Handle XML files directly (2020-2023 flat format)
        elif member.name.endswith('.xml') and member.isfile():
            xml_file = tar.extractfile(member)
            if xml_file:
                content = xml_file.read().decode('utf-8', errors='ignore')
                parsed = parse_ted_complete(content)
                if parsed:
                    records.extend(parsed)
                    if len(records) % 10000 == 0:
                        print(f"\r    Records: {len(records):,}", end="", flush=True)


def detect_archive_format(monthly_file):
    """Detect if archive is nested (2024+) or flat (2020-2023)."""
    try:
        with tarfile.open(monthly_file, 'r:gz') as tar:
            for member in tar.getmembers():
                # Check for direct XML files (flat format)
                if member.name.endswith('.xml') and member.isfile():
                    return False  # Flat format
                # Check for nested tar.gz (anywhere, including subdirs)
                if member.name.endswith('.tar.gz') and member.isfile():
                    return True   # Nested format
    except:
        pass
    return True  # Default to nested


def extract_year_complete(year):
    """Extract complete data for a year."""
    print(f"\n{'='*60}")
    print(f" EXTRACTING ALL TED DATA FOR {year}")
    print(f"{'='*60}\n")

    records = []
    patterns = sorted(RAW_DIR.glob(f"ted_{year}_*.xml.gz"))

    if not patterns:
        print(f"  No files found for year {year}")
        return []

    for monthly_file in patterns:
        print(f"  Processing {monthly_file.name}...")

        # Detect format
        is_nested = detect_archive_format(monthly_file)
        format_type = "nested" if is_nested else "flat"
        print(f"    Format: {format_type}")

        try:
            with tarfile.open(monthly_file, 'r:gz') as outer_tar:
                process_tar_archive(outer_tar, records, is_nested)

        except Exception as e:
            print(f"    Error: {e}")
            import traceback
            traceback.print_exc()
            continue

        print(f"\r    Records so far: {len(records):,}")

    # Save CSV
    CSV_DIR.mkdir(parents=True, exist_ok=True)
    output_file = CSV_DIR / f"ted_complete_{year}.csv"

    fieldnames = [
        'doc_id', 'notice_id', 'pub_date', 'doc_type', 'contract_nature', 'procedure',
        'country', 'city', 'postal_code', 'nuts',
        'authority', 'authority_id', 'authority_type', 'main_activity',
        'authority_address', 'email', 'phone', 'fax', 'website', 'contact_person',
        'title', 'cpv', 'cpv_desc',
        'value', 'currency', 'deadline', 'dispatch_date', 'award_date',
        'tenders_received', 'num_contractors',
        'contractor_1', 'contractor_1_city', 'contractor_1_country', 'contractor_1_website',
        'contractor_2', 'language', 'edition'
    ]

    with open(output_file, 'w', newline='', encoding='ascii', errors='ignore') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(records)

    print(f"\n  Saved: {output_file}")
    print(f"  Total records: {len(records):,}")

    # Stats
    by_country = Counter(r.get('country', '??') for r in records)
    with_email = sum(1 for r in records if r.get('email'))
    with_contractor = sum(1 for r in records if r.get('contractor_1'))
    total_value = sum(r.get('value', 0) for r in records)

    print(f"\n  Stats:")
    print(f"    With email: {with_email:,} ({with_email*100//len(records) if records else 0}%)")
    print(f"    With contractor: {with_contractor:,}")
    print(f"    Total value: {total_value/1e9:.1f}B EUR")
    print(f"\n  Top countries:")
    for c, cnt in by_country.most_common(10):
        print(f"    {c}: {cnt:,}")

    return records


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("year", type=int, help="Year to extract")
    args = parser.parse_args()

    extract_year_complete(args.year)
