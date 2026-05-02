#!/usr/bin/env python3
"""
EU Funds Romania - Search and export beneficiaries

Usage:
    python search.py                          # Show stats
    python search.py --industry construction  # Filter by industry
    python search.py --county Cluj            # Filter by county
    python search.py --min-budget 1000000     # Min budget EUR
    python search.py --type large             # Company size
    python search.py --export leads.csv       # Export to file
    python search.py --email office@x.com     # Send summary email
"""

import argparse
import pandas as pd
import unicodedata
import sys
import os

DATA_FILE = "/opt/ACTIVE/OPENDATA/DATA/FONDURIEUROPENE/ro/fonduri-ue/financing_contracts_clean.csv"
HOT_LEADS = "/opt/ACTIVE/OPENDATA/DATA/FONDURIEUROPENE/ro/fonduri-ue/hot_leads_eu_funds.csv"

CAEN_MAP = {
    'construction': ['41', '42', '43'],
    'manufacturing': [str(i) for i in range(10, 34)],
    'it': ['62', '63'],
    'transport': ['49', '50', '51', '52'],
    'hospitality': ['55', '56'],
    'energy': ['35'],
    'wholesale': ['46'],
    'retail': ['47'],
    'agriculture': ['01', '02', '03'],
}

SIZE_MAP = {
    'micro': 'microintreprindere',
    'small': 'intreprindere mica',
    'medium': 'intreprindere mijlocie',
    'large': 'intreprindere mare',
}

def to_ascii(text):
    if pd.isna(text):
        return ''
    normalized = unicodedata.normalize('NFKD', str(text))
    return normalized.encode('ascii', 'ignore').decode('ascii')

def load_data():
    return pd.read_csv(DATA_FILE, low_memory=False)

def filter_private(df):
    private_types = ['microintreprindere', 'intreprindere mica', 'intreprindere mijlocie', 
                     'intreprindere mare', 'persoana juridica de drept privat']
    return df[df['TIP_BENEFICIAR'].str.lower().str.contains('|'.join(private_types), na=False)]

def filter_industry(df, industry):
    if industry not in CAEN_MAP:
        print(f"Unknown industry: {industry}")
        print(f"Available: {', '.join(CAEN_MAP.keys())}")
        return df
    codes = CAEN_MAP[industry]
    mask = df['CAEN_CODE'].astype(str).str[:2].isin(codes)
    return df[mask]

def filter_size(df, size):
    if size not in SIZE_MAP:
        print(f"Unknown size: {size}")
        print(f"Available: {', '.join(SIZE_MAP.keys())}")
        return df
    return df[df['TIP_BENEFICIAR'].str.lower().str.contains(SIZE_MAP[size], na=False)]

def filter_county(df, county):
    return df[df['JUDETUL'].str.lower().str.contains(county.lower(), na=False)]

def filter_budget(df, min_budget):
    return df[df['BUG_TOTAL'] >= min_budget]

def export_leads(df, filename):
    cols = {
        'BENEFICIAR': 'company',
        'EMAIL': 'email', 
        'PHONE': 'phone',
        'ADDRESS': 'address',
        'LOCALITATEA': 'city',
        'JUDETUL': 'county',
        'TIP_BENEFICIAR': 'company_type',
        'CAEN_CODE': 'caen',
        'TITLU_PROIECT': 'project_title',
        'BUG_TOTAL': 'budget_eur',
        'STARE': 'status',
        'COD_SMIS': 'smis_code'
    }
    
    export = df[list(cols.keys())].rename(columns=cols)
    export = export[export['email'].notna() & (export['email'] != '')]
    export = export.drop_duplicates(subset=['email'], keep='first')
    
    for col in export.columns:
        if export[col].dtype == object:
            export[col] = export[col].apply(to_ascii)
    
    export = export.sort_values('budget_eur', ascending=False)
    export.to_csv(filename, index=False)
    print(f"Exported {len(export)} leads to {filename}")
    return export

def send_email(recipient, subject, body):
    import requests
    
    with open('/opt/SHARED_CONFIG/credentials/brevo.env') as f:
        for line in f:
            if line.startswith('BREVO_API_KEY='):
                api_key = line.split('=', 1)[1].strip()
            elif line.startswith('BREVO_SENDER='):
                from_email = line.split('=', 1)[1].strip()
            elif line.startswith('BREVO_SENDER_NAME='):
                from_name = line.split('=', 1)[1].strip()
    
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"api-key": api_key, "Content-Type": "application/json"}
    data = {
        "sender": {"name": from_name, "email": from_email},
        "to": [{"email": recipient}],
        "subject": subject,
        "textContent": body
    }
    
    r = requests.post(url, json=data, headers=headers, timeout=30)
    return r.status_code == 201

def show_stats(df):
    print(f"\n=== EU FUNDS ROMANIA ===\n")
    print(f"Total projects: {len(df):,}")
    print(f"With email: {df['EMAIL'].notna().sum():,}")
    print(f"Total budget: {df['BUG_TOTAL'].sum()/1e9:.1f}B EUR")
    
    print(f"\nBy company type:")
    for t, count in df['TIP_BENEFICIAR'].value_counts().head(8).items():
        print(f"  {t[:40]:40} {count:>6}")

def main():
    parser = argparse.ArgumentParser(description="EU Funds Romania - Search beneficiaries")
    parser.add_argument('--industry', help='Filter by industry (construction, manufacturing, it, etc.)')
    parser.add_argument('--county', help='Filter by county')
    parser.add_argument('--min-budget', type=float, help='Minimum budget EUR')
    parser.add_argument('--type', help='Company size (micro, small, medium, large)')
    parser.add_argument('--private', action='store_true', help='Only private companies')
    parser.add_argument('--export', help='Export to CSV file')
    parser.add_argument('--email', help='Send summary to email')
    parser.add_argument('--limit', type=int, default=500, help='Max leads to export')
    args = parser.parse_args()
    
    df = load_data()
    
    if args.private:
        df = filter_private(df)
    if args.industry:
        df = filter_industry(df, args.industry)
    if args.county:
        df = filter_county(df, args.county)
    if args.min_budget:
        df = filter_budget(df, args.min_budget)
    if args.type:
        df = filter_size(df, args.type)
    
    show_stats(df)
    
    if args.export:
        export_leads(df.head(args.limit * 3), args.export)
    
    if args.email:
        body = f"""EU Funds Romania - Query Results

Total matches: {len(df):,}
With email: {df['EMAIL'].notna().sum():,}
Total budget: {df['BUG_TOTAL'].sum()/1e9:.2f}B EUR

Filters applied:
- Industry: {args.industry or 'all'}
- County: {args.county or 'all'}
- Min budget: {args.min_budget or 'none'}
- Company type: {args.type or 'all'}

Top 10 by budget:
"""
        for _, r in df.nlargest(10, 'BUG_TOTAL').iterrows():
            body += f"- {r['BENEFICIAR'][:40]} | {r['BUG_TOTAL']/1e6:.1f}M EUR\n"
        
        if send_email(args.email, "EU Funds Romania - Query Results", body):
            print(f"\nSent summary to {args.email}")

if __name__ == "__main__":
    main()
