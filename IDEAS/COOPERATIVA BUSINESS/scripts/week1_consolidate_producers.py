#!/usr/bin/env python3
"""
Gospodarii de Altadata — Week 1 Data Consolidation
Consolidates 680 RNPM producers + 2,727 cooperatives into master database
Identifies top 50 producers for immediate outreach
"""

import pandas as pd
import os
from pathlib import Path

# Paths
DATA_DIR = Path("d:/MEMORY/IDEAS/PRODUS MONTAN/DATA")
OIPA_DIR = Path("d:/BUSINESS/OIPA EXPORT 2023/ALL/PRODUCATORI")
OUTPUT_DIR = Path("./data_working")
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 80)
print("GOSPODARII DE ALTADATA — WEEK 1 DATA CONSOLIDATION")
print("=" * 80)

# ============================================================================
# STEP 1: Load RNPM Producer Data (680 producers)
# ============================================================================
print("\n[1/5] Loading RNPM Producer Data...")
try:
    rnpm_producers = pd.read_csv(DATA_DIR / "PRODUS MONTAN PRODUCATORI.csv")
    print(f"  ✓ Loaded {len(rnpm_producers)} RNPM producers")
    print(f"    Columns: {list(rnpm_producers.columns)}")
    print(f"    Sample:\n{rnpm_producers.head(3)}")
except Exception as e:
    print(f"  ✗ Error loading RNPM: {e}")
    rnpm_producers = pd.DataFrame()

# ============================================================================
# STEP 2: Load Cooperatives Data (2,727 cooperatives)
# ============================================================================
print("\n[2/5] Loading Cooperatives Data...")
try:
    # Try the enriched top 50 first
    coop_enriched = pd.read_csv(DATA_DIR / "cooperative_top50_enriched.csv")
    print(f"  ✓ Loaded {len(coop_enriched)} enriched cooperatives (top 50)")
    
    # Try full list
    if (DATA_DIR / "Registrul-National-al-Cooperativelor-Agricole-din-Romania-2018-2023.xlsx").exists():
        coops_full = pd.read_excel(DATA_DIR / "Registrul-National-al-Cooperativelor-Agricole-din-Romania-2018-2023.xlsx")
        print(f"  ✓ Loaded {len(coops_full)} total cooperatives from RNCA registry")
    else:
        coops_full = coop_enriched
        
except Exception as e:
    print(f"  ✗ Error loading cooperatives: {e}")
    coops_full = pd.DataFrame()

# ============================================================================
# STEP 3: Load Specialized Producer Data
# ============================================================================
print("\n[3/5] Loading Specialized Producer Data...")

# Meat producers
try:
    meat_producers = pd.read_csv(DATA_DIR / "RNPM 10.07.2023 CARNE FISIER LUCRU.csv")
    print(f"  ✓ Loaded {len(meat_producers)} meat producers (CARNE)")
except Exception as e:
    print(f"  ✗ Error loading meat producers: {e}")
    meat_producers = pd.DataFrame()

# Email contacts
try:
    emails = pd.read_csv(DATA_DIR / "DATE EXTRASE/rnpm email.csv")
    print(f"  ✓ Loaded {len(emails)} email contacts")
except Exception as e:
    print(f"  ✗ Error loading emails: {e}")
    emails = pd.DataFrame()

# ============================================================================
# STEP 4: Create Master Producer Database
# ============================================================================
print("\n[4/5] Creating Master Producer Database...")

# Start with RNPM producers
master_producers = rnpm_producers.copy()
master_producers['source'] = 'RNPM'
master_producers['category'] = 'general'

# Add meat producers if available
if not meat_producers.empty:
    meat_producers['source'] = 'RNPM-CARNE'
    meat_producers['category'] = 'meat'
    # Try to merge by email
    if 'Email' in meat_producers.columns:
        master_producers = pd.concat([master_producers, meat_producers[['Email', 'source', 'category']]], 
                                      ignore_index=True)
        print(f"  ✓ Added {len(meat_producers)} meat producers")

print(f"  ✓ Master producer database: {len(master_producers)} producers")

# ============================================================================
# STEP 5: Save Consolidated Data
# ============================================================================
print("\n[5/5] Saving Consolidated Data...")

# Save master producers
master_file = OUTPUT_DIR / "master_producers_consolidated.csv"
master_producers.to_csv(master_file, index=False)
print(f"  ✓ Saved: {master_file}")

# Save cooperatives
coops_file = OUTPUT_DIR / "cooperatives_full.csv"
coops_full.to_csv(coops_file, index=False)
print(f"  ✓ Saved: {coops_file}")

# ============================================================================
# Summary Statistics
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)
print(f"Master Producers:        {len(master_producers)} total")
print(f"  - General:             {len(master_producers[master_producers['source']=='RNPM'])}")
print(f"  - Meat specialized:    {len(master_producers[master_producers['source']=='RNPM-CARNE'])}")
print(f"\nCooperatives (partners): {len(coops_full)} total")
print(f"Cooperatives (enriched): {len(coop_enriched)} (top tier)")

print(f"\nOutput files saved to: {OUTPUT_DIR}")
print(f"  - {master_file.name}")
print(f"  - {coops_file.name}")

print("\n" + "=" * 80)
print("NEXT STEPS (Week 1):")
print("=" * 80)
print("1. Analyze top 50 producers by volume/certification")
print("2. Segment hypermarket targets (5 chains × 5 leads each)")
print("3. Extract Italy diaspora shop contacts from F:/BUSINESS/OIPA")
print("4. Design product catalog template")
print("5. Prepare email templates (EN, DE, FR, IT)")
print("\nEstimated completion: 2-3 days | Next milestone: Week 2 (Day 7)")
print("=" * 80)
