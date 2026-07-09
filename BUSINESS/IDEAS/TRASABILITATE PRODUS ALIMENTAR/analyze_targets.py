#!/usr/bin/env python3
import csv
from collections import defaultdict

def analyze_targets():
    targets = defaultdict(list)
    products = defaultdict(int)
    total_capacity = 0

    with open('TARGET_CLIENTS.csv') as f:
        reader = csv.DictReader(f)
        for row in reader:
            priority = row['Priority']
            targets[priority].append(row)
            products[row['Category']] += int(row['Volume_kg_month'])
            total_capacity += int(row['Volume_kg_month'])

    # Report
    print("=" * 70)
    print("TRASABILITATE CLIENTS ANALYSIS — Jan 2024 Campaign Respondents")
    print("=" * 70)

    print(f"\nTOTAL CAPACITY: {total_capacity:,} kg/month across {sum(len(v) for v in targets.values())} producers\n")

    # By priority
    for p in sorted(targets.keys()):
        print(f"PRIORITY {p} ({len(targets[p])} producers)")
        for prod in targets[p]:
            print(f"  • {prod['Producer']:35} | {prod['Product']:30} | "
                  f"{prod['Volume_kg_month']:>5}kg/mo | {prod['Hypermarket_Potential']:>6} HM | {prod['Export_Potential']:>6} EXP")
        print()

    # By category
    print("\nBY PRODUCT CATEGORY:")
    for cat in sorted(products, key=lambda x: products[x], reverse=True):
        print(f"  • {cat:20} {products[cat]:>6,} kg/month")

    # Quick wins (Priority 1-2, high hypermarket potential)
    print("\n" + "=" * 70)
    print("QUICK WIN TARGETS (Priority 1-2, Hypermarket Ready)")
    print("=" * 70)
    quick_wins = []
    for p in ['1', '2']:
        for prod in targets[p]:
            if prod['Hypermarket_Potential'] in ['HIGH', 'MEDIUM']:
                quick_wins.append(prod)

    for prod in sorted(quick_wins, key=lambda x: int(x['Volume_kg_month']), reverse=True):
        print(f"\n{prod['Producer']}")
        print(f"  Volume: {prod['Volume_kg_month']} kg/month")
        print(f"  Product: {prod['Product']}")
        print(f"  Contact: {prod['Contact_Method']}")
        print(f"  Why ready: {prod['Notes']}")

    # Export high potential
    print("\n" + "=" * 70)
    print("EU EXPORT HIGH POTENTIAL")
    print("=" * 70)
    export_ready = []
    for p in targets.values():
        for prod in p:
            if prod['Export_Potential'] == 'HIGH':
                export_ready.append(prod)

    for prod in sorted(export_ready, key=lambda x: int(x['Volume_kg_month']), reverse=True)[:10]:
        print(f"{prod['Producer']:35} | {prod['Product']:30} | "
              f"{prod['Volume_kg_month']:>5}kg/mo | {prod['Notes'][:50]}")

    # Summary email outreach
    print("\n" + "=" * 70)
    print("OUTREACH STRATEGY")
    print("=" * 70)
    print("""
SEGMENT 1: Hypermarket Aggregation (Priority 1-2, HIGH HM)
  Producers: Miklo, Tankó, Montlact, Papp, AfirFruct, Mister Juice
  Message: "Join cooperative, we handle Kaufland/Lidl negotiation. Trasabilitate = proof."
  Expected: 80% adoption (EUR 100-300/mo each) = EUR 1,800-5,400/mo

SEGMENT 2: EU Export (HIGH EXP)
  Producers: Stupina Igna, Mierecarpatica, Godeanu, Papp, Afin Fruct, Mister Juice
  Message: "Export to EU shops + wholesalers. Trasabilitate = mandatory compliance."
  Expected: 60% adoption (EUR 200-500/mo each) = EUR 2,400-6,000/mo

SEGMENT 3: Local + Seasonal (Priority 4-5)
  Producers: Balteanu, Aga, Hura, Martinovici
  Message: "Optional. Trasabilitate adds value for restaurant/Airbnb suppliers."
  Expected: 20% adoption = EUR 0-800/mo
    """)

if __name__ == "__main__":
    analyze_targets()
