#!/usr/bin/env python3
"""
PDF Anonymizer - Extract text from PDFs and anonymize company/personal data.

Anonymizes:
- Company names (SRL, SA, PFA entities)
- CUI/VAT numbers (Romanian tax IDs)
- J numbers (trade registry numbers)
- Addresses (streets, buildings, postal codes)
- Person names (directors, representatives)
- License numbers
- Emails and phone numbers

Usage:
    python3 pdf_anonymizer.py /path/to/file.pdf
    python3 pdf_anonymizer.py /path/to/*.pdf
    python3 pdf_anonymizer.py /path/to/file.pdf --output custom_output.txt

Reuses existing code from:
- pdf_extractor.py: extract_pdf()
- exec_runtime.py: PIIMasker
- fuzzy_matcher.py: LEGAL_FORMS, to_ascii()
"""
import sys
import os
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Tuple
from collections import OrderedDict

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')

from pdf_extractor import extract_pdf
from exec_runtime import PIIMasker


# === LEGAL FORMS (from fuzzy_matcher.py) ===
LEGAL_FORMS = [
    'S\\.?R\\.?L\\.?', 'S\\.?A\\.?', 'S\\.?C\\.?', 'S\\.?C\\.?S\\.?',
    'S\\.?N\\.?C\\.?', 'S\\.?C\\.?A\\.?', 'P\\.?F\\.?A\\.?', 'I\\.?I\\.?',
    'O\\.?N\\.?G\\.?', 'COOP', 'R\\.?A\\.?', 'S\\.?P\\.?',
    'IMPEX', 'GRUP', 'GROUP', 'HOLDING', 'INTERNATIONAL',
    'LTD', 'LIMITED', 'GMBH', 'AG', 'BV', 'NV',
]


def to_ascii(text: str) -> str:
    """Convert text to ASCII, removing diacritics."""
    if not text:
        return ''
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii')


class CompanyDataAnonymizer:
    """Anonymizes Romanian company and personal data in text."""

    def __init__(self):
        # Counters for unique replacements
        self.company_counter = 0
        self.person_counter = 0
        self.address_counter = 0
        self.cui_counter = 0
        self.j_counter = 0
        self.license_counter = 0

        # Track already replaced values to use consistent tags
        self.company_map = OrderedDict()
        self.person_map = OrderedDict()
        self.address_map = OrderedDict()

        # Romanian-specific patterns
        self.patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile all regex patterns."""
        # Legal form suffix pattern
        legal_suffix = '|'.join(LEGAL_FORMS)

        patterns = {
            # CUI/CIF - Romanian tax ID (6-10 digits, optionally prefixed with RO)
            'cui': re.compile(
                r'\b(?:CUI|C\.U\.I\.|CIF|C\.I\.F\.|cod\s+fiscal|cod\s+unic)[:\s]*'
                r'(?:RO\s*)?(\d{6,10})\b',
                re.IGNORECASE
            ),
            'cui_standalone': re.compile(
                r'\b(?:RO\s*)?(\d{8})\b'  # 8-digit numbers are likely CUIs
            ),

            # J number - Trade registry number J{judet}/{nr}/{year}
            'j_number': re.compile(
                r'\bJ\s*\d{1,2}\s*/\s*\d{1,6}\s*/\s*(?:19|20)\d{2}\b',
                re.IGNORECASE
            ),
            'j_number_alt': re.compile(
                r'\b(?:nr\.\s*)?(?:inmatr(?:iculare)?|ORC)[:\s]*'
                r'J\s*\d{1,2}\s*/\s*\d{1,6}\s*/\s*(?:19|20)\d{2}',
                re.IGNORECASE
            ),
            # J number concatenated format: J16118372017
            'j_number_concat': re.compile(
                r'\bJ\d{2}\d{3,6}(?:19|20)\d{2}\b',
                re.IGNORECASE
            ),

            # Company names - Word(s) followed by legal form suffix
            'company': re.compile(
                rf'(?:S\.?C\.?\s+)?([A-Z][A-Za-z0-9\s&\-\.\']+?)\s*'
                rf'(?:{legal_suffix})\b',
                re.IGNORECASE
            ),

            # Addresses - Street patterns
            'address_str': re.compile(
                r'(?:str(?:ada)?\.?\s*|'
                r'bd\.?\s*|bulevardul\s*|'
                r'calea\s*|sos(?:eaua)?\.?\s*|'
                r'aleea\s*|piata\s*|'
                r'drumul\s*)'
                r'[A-Za-z0-9\s\.,\-]+?'
                r'(?:,?\s*nr\.?\s*\d+[A-Za-z]?)?'
                r'(?:,?\s*(?:bl\.?\s*[A-Za-z0-9]+))?'
                r'(?:,?\s*(?:sc\.?\s*[A-Za-z0-9]+))?'
                r'(?:,?\s*(?:et\.?\s*\d+))?'
                r'(?:,?\s*(?:ap\.?\s*\d+))?',
                re.IGNORECASE
            ),

            # Postal codes (Romanian: 6 digits)
            'postal_code': re.compile(r'\b\d{6}\b'),

            # Person names - After titles/roles
            'person_director': re.compile(
                r'(?:director|administrator|reprezentant|asociat|'
                r'actionar|manager|responsabil|dl\.?|dna\.?|d-l|d-na|'
                r'numitul|numita|cu\s+domiciliul)[:\s]+'
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})',
                re.IGNORECASE
            ),

            # License numbers (Romanian and English variants)
            'license': re.compile(
                r'(?:licen[tț][aă]|license|autorizat|certificat|aviz|atestat|slbfe)'
                r'(?:\s*(?:nr\.?|no\.?|numar|number|de\s+functionare))?\s*'
                r'[:\s\-]*\d+[a-zA-Z]?(?:[/-]\d+)*',
                re.IGNORECASE
            ),

            # IBAN - Romanian bank accounts
            'iban': re.compile(
                r'\bRO\d{2}[A-Z]{4}\d{16}\b',
                re.IGNORECASE
            ),

            # CNP - Romanian personal ID (13 digits starting with 1-6)
            'cnp': re.compile(r'\b[1-6]\d{12}\b'),
        }

        return patterns

    def _get_company_tag(self, company_name: str) -> str:
        """Get consistent tag for a company name."""
        normalized = company_name.strip().upper()
        if normalized not in self.company_map:
            self.company_counter += 1
            self.company_map[normalized] = f'[COMPANY_{self.company_counter}]'
        return self.company_map[normalized]

    def _get_person_tag(self, person_name: str) -> str:
        """Get consistent tag for a person name."""
        normalized = person_name.strip().upper()
        if normalized not in self.person_map:
            self.person_counter += 1
            self.person_map[normalized] = f'[PERSON_{self.person_counter}]'
        return self.person_map[normalized]

    def _get_address_tag(self, address: str) -> str:
        """Get consistent tag for an address."""
        # Simplify for deduplication
        normalized = re.sub(r'\s+', ' ', address.strip().upper())
        if normalized not in self.address_map:
            self.address_counter += 1
            self.address_map[normalized] = f'[ADDRESS_{self.address_counter}]'
        return self.address_map[normalized]

    def anonymize(self, text: str) -> str:
        """
        Anonymize all sensitive data in text.

        Order matters - process in this sequence:
        1. Emails and phones (PIIMasker handles these)
        2. IBANs
        3. CNP
        4. Company names (longest first)
        5. CUI numbers
        6. J numbers
        7. Addresses
        8. License numbers
        9. Person names (last - most prone to false positives)
        """
        if not text:
            return text

        # === PHASE 1: PIIMasker for emails/phones ===
        # Use exec_runtime PIIMasker patterns
        text = re.sub(
            PIIMasker.PATTERNS['email'],
            '[EMAIL_MASKED]',
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(
            PIIMasker.PATTERNS['phone_intl'],
            '[PHONE_MASKED]',
            text,
            flags=re.IGNORECASE
        )
        text = re.sub(
            PIIMasker.PATTERNS['phone_local'],
            '[PHONE_MASKED]',
            text,
            flags=re.IGNORECASE
        )

        # === PHASE 2: IBAN ===
        text = self.patterns['iban'].sub('[IBAN_MASKED]', text)

        # === PHASE 3: CNP ===
        text = self.patterns['cnp'].sub('[CNP_MASKED]', text)

        # === PHASE 4: Company names ===
        # Find all companies first, then replace longest matches first
        company_matches = []
        for match in self.patterns['company'].finditer(text):
            full_match = match.group(0)
            company_matches.append((match.start(), match.end(), full_match))

        # Sort by length (longest first) to avoid partial replacements
        company_matches.sort(key=lambda x: len(x[2]), reverse=True)

        for start, end, match in company_matches:
            tag = self._get_company_tag(match)
            # Use the exact match to replace
            text = text.replace(match, tag, 1)

        # === PHASE 5: CUI numbers ===
        text = self.patterns['cui'].sub(r'CUI [CUI_MASKED]', text)
        text = self.patterns['cui_standalone'].sub('[CUI_MASKED]', text)

        # === PHASE 6: J numbers ===
        text = self.patterns['j_number'].sub('[J_NUMBER_MASKED]', text)
        text = self.patterns['j_number_alt'].sub('[J_NUMBER_MASKED]', text)
        text = self.patterns['j_number_concat'].sub('[J_NUMBER_MASKED]', text)

        # === PHASE 7: Addresses ===
        for match in self.patterns['address_str'].finditer(text):
            address = match.group(0)
            if len(address) > 10:  # Avoid false positives
                tag = self._get_address_tag(address)
                text = text.replace(address, tag, 1)

        # === PHASE 8: License numbers ===
        text = self.patterns['license'].sub('[LICENSE_MASKED]', text)

        # === PHASE 9: Person names ===
        for match in self.patterns['person_director'].finditer(text):
            person = match.group(1)
            if person and len(person) > 3:
                tag = self._get_person_tag(person)
                # Replace the person name only, keep the title
                text = text.replace(match.group(0), match.group(0).replace(person, tag), 1)

        # === PHASE 10: Postal codes (last, high false positive risk) ===
        # Only replace if near address context
        text = re.sub(
            r'(?:cod\s*postal|CP)[:\s]*(\d{6})',
            r'cod postal [POSTAL_MASKED]',
            text,
            flags=re.IGNORECASE
        )

        return text

    def get_stats(self) -> Dict[str, int]:
        """Return anonymization statistics."""
        return {
            'companies_found': self.company_counter,
            'persons_found': self.person_counter,
            'addresses_found': self.address_counter,
        }


def process_pdf(pdf_path: str, output_path: str = None) -> Dict:
    """
    Process a PDF file: extract text and anonymize.

    Args:
        pdf_path: Path to input PDF
        output_path: Optional output path (default: same name with _anonymized.txt)

    Returns:
        Dict with stats and paths
    """
    pdf_path = Path(pdf_path)

    if not pdf_path.exists():
        return {'error': f'File not found: {pdf_path}'}

    # Default output path
    if not output_path:
        output_path = pdf_path.parent / f"{pdf_path.stem}_anonymized.txt"
    else:
        output_path = Path(output_path)

    print(f"Processing: {pdf_path.name}")

    # Step 1: Extract text
    result = extract_pdf(str(pdf_path))

    if result.get('error'):
        return {'error': result['error']}

    text = result.get('text', '')
    if not text:
        return {'error': 'No text extracted from PDF'}

    print(f"  Extracted {len(text)} chars from {result.get('pages', 0)} pages")

    # Step 2: Convert to ASCII (remove diacritics)
    text_ascii = to_ascii(text)

    # Step 3: Anonymize
    anonymizer = CompanyDataAnonymizer()
    anonymized_text = anonymizer.anonymize(text_ascii)

    stats = anonymizer.get_stats()
    print(f"  Anonymized: {stats['companies_found']} companies, "
          f"{stats['persons_found']} persons, {stats['addresses_found']} addresses")

    # Step 4: Write output
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(f"# Anonymized from: {pdf_path.name}\n")
        f.write(f"# Pages: {result.get('pages', 0)}\n")
        f.write(f"# Companies masked: {stats['companies_found']}\n")
        f.write(f"# Persons masked: {stats['persons_found']}\n")
        f.write(f"# Addresses masked: {stats['addresses_found']}\n")
        f.write("#" + "=" * 59 + "\n\n")
        f.write(anonymized_text)

    print(f"  Output: {output_path}")

    return {
        'input': str(pdf_path),
        'output': str(output_path),
        'pages': result.get('pages', 0),
        'chars_original': len(text),
        'chars_anonymized': len(anonymized_text),
        'stats': stats,
    }


def main():
    """CLI entry point."""
    args = sys.argv[1:]

    if not args or '-h' in args or '--help' in args:
        print("""
PDF ANONYMIZER - Extract and anonymize company data from PDFs

Usage:
    pdf_anonymizer.py <file.pdf>              Anonymize single file
    pdf_anonymizer.py <file.pdf> --output X   Custom output path
    pdf_anonymizer.py *.pdf                   Batch process multiple PDFs

Output: <filename>_anonymized.txt in same directory

Anonymizes:
    - Company names (SRL, SA, PFA, etc.)
    - CUI/VAT numbers (Romanian tax IDs)
    - J numbers (trade registry numbers)
    - Addresses (streets, buildings)
    - Person names (directors, representatives)
    - License/permit numbers
    - Emails, phones, IBANs, CNPs
""")
        return

    # Parse arguments
    pdf_files = []
    output_path = None

    i = 0
    while i < len(args):
        if args[i] == '--output' and i + 1 < len(args):
            output_path = args[i + 1]
            i += 2
        elif args[i].endswith('.pdf') or args[i].endswith('.PDF'):
            pdf_files.append(args[i])
            i += 1
        else:
            i += 1

    if not pdf_files:
        print("Error: No PDF files specified")
        return

    print(f"\n{'='*60}")
    print("PDF ANONYMIZER")
    print(f"{'='*60}\n")

    results = []
    for pdf_file in pdf_files:
        # For batch, don't use custom output path
        out = output_path if len(pdf_files) == 1 else None
        result = process_pdf(pdf_file, out)
        results.append(result)
        print()

    # Summary
    if len(results) > 1:
        print(f"\n{'='*60}")
        print("BATCH SUMMARY")
        print(f"{'='*60}")
        total_pages = sum(r.get('pages', 0) for r in results if 'error' not in r)
        total_companies = sum(r.get('stats', {}).get('companies_found', 0) for r in results if 'error' not in r)
        errors = sum(1 for r in results if 'error' in r)
        print(f"Files processed: {len(results) - errors}/{len(results)}")
        print(f"Total pages: {total_pages}")
        print(f"Total companies anonymized: {total_companies}")
        if errors:
            print(f"Errors: {errors}")

    print(f"\n{'='*60}\n")


if __name__ == '__main__':
    main()
