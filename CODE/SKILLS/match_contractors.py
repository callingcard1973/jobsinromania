#!/usr/bin/env python3
"""Match SEAP contractors with contact data from ANOFM and other sources."""
import pandas as pd
import unicodedata
from pathlib import Path

def to_ascii(text):
    if not text or pd.isna(text):
        return ''
    return unicodedata.normalize('NFKD', str(text)).encode('ascii', 'ignore').decode('ascii').upper().strip()

def main():
    contracts_dir = Path("/opt/ACTIVE/OPENDATA/DATA/ACHIZITII_PUBLICE")
    output_dir = Path("/opt/ACTIVE/OPENDATA/DATA/CONTRACTOR_MATCHES")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all SEAP contracts
    all_contracts = []
    for f in contracts_dir.glob("*_202*.csv"):
        if 'combined' not in f.name:
            df = pd.read_csv(f, low_memory=False)
            all_contracts.append(df)

    if not all_contracts:
        print("No contract files found")
        return

    contracts = pd.concat(all_contracts, ignore_index=True)
    print(f"Loaded {len(contracts):,} contracts")

    # Extract unique contractors with CUI
    contractors = contracts[['OFERTANT_CASTIGATOR', 'CUI_OFERTANT_CASTIGATOR']].drop_duplicates()
    contractors = contractors.dropna(subset=['OFERTANT_CASTIGATOR'])
    contractors['CUI'] = contractors['CUI_OFERTANT_CASTIGATOR'].astype(str).str.extract(r'(\d+)')
    print(f"Unique contractors: {len(contractors):,}")

    # Save all contractors
    contractors.to_csv(output_dir / "all_contractors_2025.csv", index=False)

    # Load ANOFM contacts
    anofm_file = Path("/opt/ACTIVE/OPENDATA/DATA/ANOFM/anofm_merged_20251225_133454.csv")
    if anofm_file.exists():
        anofm = pd.read_csv(anofm_file, low_memory=False)
        anofm_contacts = anofm[['employer', 'employer_tax_code', 'emails', 'phones']].drop_duplicates()
        anofm_contacts = anofm_contacts[anofm_contacts['employer_tax_code'].notna()]
        anofm_contacts['CUI'] = anofm_contacts['employer_tax_code'].astype(str).str.extract(r'(\d+)')
        anofm_contacts = anofm_contacts[anofm_contacts['emails'].notna()]
        print(f"ANOFM contacts with email: {len(anofm_contacts):,}")

        # Match by CUI
        matched = contractors.merge(anofm_contacts[['CUI', 'emails', 'phones']], on='CUI', how='inner')
        matched = matched.drop_duplicates(subset=['OFERTANT_CASTIGATOR'])
        print(f"Matched with contacts: {len(matched):,}")

        # Save matched
        matched.to_csv(output_dir / "contractors_with_contacts.csv", index=False)
        print(f"Saved to {output_dir / 'contractors_with_contacts.csv'}")

    # Top contractors by contract count
    contractor_counts = contracts['OFERTANT_CASTIGATOR'].value_counts().head(1000)
    contractor_counts.to_frame('contract_count').to_csv(output_dir / "top_contractors_2025.csv")
    print(f"Saved top contractors")

if __name__ == "__main__":
    main()
