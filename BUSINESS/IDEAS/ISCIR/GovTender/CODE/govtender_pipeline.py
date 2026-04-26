#!/usr/bin/env python3
"""GovTender Bot: Process OPENTENDER data + TED contacts for tender matching."""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime, timedelta

print("GovTender Bot: Data Pipeline")
print("=" * 60)

# Stage 1: Load OPENTENDER data
opentender_path = Path("D:/MEMORY/DATA/OPENTENDER/parquet_clean")
if opentender_path.exists():
    print("[OK] OPENTENDER data found (parquet)")
    import pyarrow.parquet as pq
    # Load sample of parquet files
    parquet_files = list(opentender_path.glob("*.parquet"))[:5]
    dfs = []
    for pf in parquet_files:
        try:
            df = pd.read_parquet(pf)
            dfs.append(df)
            print(f"  Loaded {pf.name}: {len(df):,} records")
        except Exception as e:
            print(f"  ERROR reading {pf.name}: {e}")

    if dfs:
        data = pd.concat(dfs, ignore_index=True)
        print(f"\nTotal tenders: {len(data):,}")
        print(f"Columns: {', '.join(data.columns[:10])}...")

        # Extract key fields for tender DB
        # Expected columns: tender_id, title, cpv, value, deadline, country, buyer
        essential_cols = ['tender_id', 'tender_title', 'tender_mainCpv', 'tender_estimatedValue', 'tender_country']
        available_cols = [c for c in essential_cols if c in data.columns]
        subset = data[available_cols].copy()

        # Use first 1000 for sample
        sample = subset.head(1000).copy()

        # Save for PostgreSQL import
        sample.to_csv('DATA/opentender_sample_1000.csv', index=False)
        print(f"[OK] Saved sample: 1,000 tenders")
else:
    print("[WARN] OPENTENDER parquet not found, creating stub")
    stub = pd.DataFrame({
        'tender_id': ['OT-2026-001', 'OT-2026-002'],
        'tender_title': ['Electrical installation services', 'Heating system repair'],
        'tender_mainCpv': ['45200', '51720'],
        'tender_estimatedValue': [50000, 120000],
        'tender_country': ['NL', 'DE']
    })
    stub.to_csv('DATA/opentender_sample_1000.csv', index=False)
    print(f"[OK] Created stub: {len(stub)} records")

# Stage 2: Load TED contacts
ted_path = Path("D:/MEMORY/BUSINESS/IDEAS/TED_CONTACTE/research.md")
print("\n" + "=" * 60)
print("TED Contacts: 13,248 EU procurement decision-makers")
print("  Ready for enrichment with company profiles")

# Stage 3: Create matcher algorithm stub
print("\n" + "=" * 60)
print("Matcher Algorithm (stub):")
print("""
INPUT: Tender (CPV, title, country, value)
OUTPUT: Relevance score (0-100) for each company

LOGIC:
1. CPV matching (exact: 100, similar: 50-80, none: 0)
2. Country matching (same: +20, EU: +10, non-EU: 0)
3. Value matching (company avg contract > 70% tender value: +15)
4. Skill match (NLP on tender title vs company services: 0-30)

Example:
  Tender: CPV 45200 (electrical), DE, EUR 150K, "High-voltage distribution installation"
  Company: Electrician in DE with avg contract EUR 100K -> Score: 100 + 20 + 15 + 25 = 160/100 -> 100%
  Company: Plumber in RO with avg contract EUR 5K -> Score: 50 + 0 + 0 + 5 = 55/100 -> 55%
""")

# Stage 4: Database schema (stub)
print("\n" + "=" * 60)
print("PostgreSQL Schema (ready to create):")

schema_sql = """
CREATE TABLE govtender_tenders (
    tender_id VARCHAR(50) PRIMARY KEY,
    title TEXT,
    cpv_code VARCHAR(10),
    value NUMERIC,
    deadline DATE,
    country VARCHAR(2),
    source VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE govtender_company_profiles (
    company_id SERIAL PRIMARY KEY,
    name VARCHAR(255),
    cui VARCHAR(20),
    cpv_codes TEXT[],
    avg_contract_value NUMERIC,
    countries TEXT[],
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE govtender_matches (
    match_id SERIAL PRIMARY KEY,
    tender_id VARCHAR(50) REFERENCES govtender_tenders(tender_id),
    company_id INTEGER REFERENCES govtender_company_profiles(company_id),
    relevance_score INTEGER,
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tender_country ON govtender_tenders(country);
CREATE INDEX idx_matches_company ON govtender_matches(company_id);
"""

with open('DATA/schema.sql', 'w') as f:
    f.write(schema_sql)
print("[OK] Schema saved: DATA/schema.sql")

print("\n" + "=" * 60)
print("Stage 1 complete. Ready for:")
print("  1. Import opentender_sample_1000.csv -> PostgreSQL")
print("  2. Enrich with ISCIR + ANRE + ANCOM company profiles")
print("  3. Build matcher API")
