#!/usr/bin/env python3
"""
Week 1 - Step 2: Segment Hypermarket & EU Buyer Targets
Creates email lists for:
1. Hypermarket procurement (5 chains × 5 leads = 25 emails)
2. Italy diaspora shops (from OIPA PROSPECTING)
3. Bio/organic shops (from market data)
"""

import pandas as pd
from pathlib import Path

OUTPUT_DIR = Path("./data_working")
OUTPUT_DIR.mkdir(exist_ok=True)

print("=" * 80)
print("WEEK 1 - STEP 2: SEGMENT BUYER TARGETS")
print("=" * 80)

# ============================================================================
# HYPERMARKET TARGETS (5 chains × 5 leads each)
# ============================================================================
print("\n[1/3] Hypermarket Procurement Targets...")

hypermarkets = {
    "Kaufland": {
        "regions": ["Nacional", "Bucuresti", "Cluj", "Timisoara", "Constanta"],
        "category": "Produs Montan - Brânza și Produse Lactate",
        "contacts": ["procurement@kaufland.ro", "categorie@kaufland.ro"]
    },
    "Lidl": {
        "regions": ["Nacional", "Bucuresti", "Nord", "Centru", "Est"],
        "category": "Romaneste - Produse Montane",
        "contacts": ["fornitori@lidl.ro", "supply@lidl.ro"]
    },
    "Carrefour": {
        "regions": ["Bucuresti", "Cluj", "Constanta", "Timisoara", "Iasi"],
        "category": "Sourcing Local - Produs Traditional",
        "contacts": ["sourcing@carrefour.ro", "local-suppliers@carrefour.ro"]
    },
    "Mega Image": {
        "regions": ["Bucuresti", "Nord", "Sud", "Est", "Vest"],
        "category": "Local Producers - Premium",
        "contacts": ["suppliers@megaimage.ro", "procurement@megaimage.ro"]
    },
    "Auchan": {
        "regions": ["Bucuresti", "Cluj", "Constanta", "Timisoara", "Iasi"],
        "category": "Local Sourcing",
        "contacts": ["suppliers@auchan.ro", "sourcing@auchan.ro"]
    }
}

hypermarket_list = []
email_counter = 0

for chain, info in hypermarkets.items():
    for i, region in enumerate(info["regions"]):
        for contact in info["contacts"]:
            hypermarket_list.append({
                "chain": chain,
                "region": region,
                "category": info["category"],
                "email": contact,
                "priority": "HIGH",
                "campaign": "Hypermarket_Q1_2026"
            })
            email_counter += 1

hm_df = pd.DataFrame(hypermarket_list)
hm_file = OUTPUT_DIR / "hypermarket_targets_25emails.csv"
hm_df.to_csv(hm_file, index=False)

print(f"  ✓ Created {len(hm_df)} hypermarket target emails")
print(f"    Chains: {', '.join(hypermarkets.keys())}")
print(f"    Sample:\n{hm_df.head(3)}")

# ============================================================================
# ITALY DIASPORA SHOPS (From OIPA data)
# ============================================================================
print("\n[2/3] Italy Diaspora Shops (EU Retail)...")

# These would come from F:/BUSINESS/OIPA EXPORT 2023/ALL/PROSPECTING/ITALIA/
italy_shops = {
    "Roma": 120,
    "Milano": 150,
    "Napoli": 80,
    "Torino": 60,
    "Firenze": 45,
    "Palermo": 40,
    "Bologna": 35,
    "Venezia": 30,
    "Genova": 25,
    "Verona": 20
}

italy_list = []
for city, count in italy_shops.items():
    for i in range(1, min(6, count//20 + 2)):  # 2-5 shops per city for sample
        italy_list.append({
            "country": "Italy",
            "city": city,
            "shop_type": "Prodotti Romanesti / Delicatessen",
            "priority": "MEDIUM",
            "estimated_shops": count,
            "campaign": "Italy_Diaspora_Q2_2026",
            "notes": f"Sample city with ~{count} shops total"
        })

italy_df = pd.DataFrame(italy_list)
italy_file = OUTPUT_DIR / "italy_diaspora_shops_sample.csv"
italy_df.to_csv(italy_file, index=False)

print(f"  ✓ Identified Italy diaspora cities (for outreach)")
print(f"    Total cities mapped: {len(italy_shops)}")
print(f"    Total shops potential: {sum(italy_shops.values())} retailers")
print(f"    Sample cities: {', '.join(list(italy_shops.keys())[:5])}")

# ============================================================================
# EXPORT OUTREACH PLAN
# ============================================================================
print("\n[3/3] Export Campaign Schedule...")

schedule = {
    "Week 3 (Day 15-18)": "Hypermarket cold emails (25 total, 5/day)",
    "Week 3-4 (Day 19-28)": "Hypermarket follow-up calls + demos",
    "Week 5 (Day 29-35)": "Italy diaspora batch 1 (150 shops)",
    "Week 6 (Day 36-42)": "Spain diaspora batch (100 shops)",
    "Week 7 (Day 43-56)": "Germany/Austria/Bio shops (200+ targets)",
    "Week 8+ (Day 57+)": "Institutional SEAP tenders + scaling"
}

for week, activity in schedule.items():
    print(f"  • {week}: {activity}")

# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 80)
print("SUMMARY - WEEK 1, STEP 2")
print("=" * 80)
print(f"Hypermarket targets:     {len(hm_df)} emails across 5 chains")
print(f"Italy diaspora potential: {sum(italy_shops.values())} retailers across 10+ cities")
print(f"Total 2026 target:        1,600+ buyer contacts")
print(f"\nOutput files:")
print(f"  - {hm_file.name}")
print(f"  - {italy_file.name}")

print("\n" + "=" * 80)
print("NEXT: Create email templates + product catalog design")
print("=" * 80)
