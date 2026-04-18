#!/usr/bin/env python3
"""Email campaign dashboard -- shows readiness status and tier details.

Usage:
    python campaign_dashboard.py              # Full dashboard
    python campaign_dashboard.py --status     # Status only
    python campaign_dashboard.py --tier 0     # Specific tier detail
"""

import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from campaign_templates import (tier_0_template, tier_1_template,
                                tier_2_template, tier_3_template,
                                acquisition_template, execution_checklist)

DATA_DIR = Path(__file__).parent.parent / "DATA" / "CAMPAIGN_SEGMENTS"

SEGMENTS = {
    'Tier 0: SEAP Winners': 'TIER0_SEAP_WINNERS.csv',
    'Tier 1: Supermarket Chains': 'TIER1_CHAINS.csv',
    'Tier 2: Distributors + Logistics': 'TIER2_DISTRIBUTORS.csv',
    'Tier 3: HoReCa (Bucharest Sample)': 'TIER3_HORECA_BUCHAREST.csv',
    'Acquisition Targets': 'ACQUISITION_TARGETS.csv',
}


def campaign_status():
    """Show campaign readiness status."""
    print("=" * 80)
    print("CAMPAIGN STATUS DASHBOARD")
    print("=" * 80)
    print(f"\nDate: {datetime.now().strftime('%Y-%m-%d')}\n")
    total_ready = 0
    print("SEGMENT READINESS:")
    print("-" * 80)
    for name, filename in SEGMENTS.items():
        path = DATA_DIR / filename
        if path.exists():
            df = pd.read_csv(path)
            emails = df['email'].notna().sum()
            total_ready += emails
            print(f"{name:45} | {emails:4} emails | {len(df):5} total | READY")
        else:
            print(f"{name:45} | MISSING")
    print("-" * 80)
    print(f"{'TOTAL READY FOR CAMPAIGN':45} | {total_ready:4} emails\n")


def show_tier(tier_num):
    """Show detail for a specific tier."""
    tier_map = {
        0: ('TIER0_SEAP_WINNERS.csv', 'SEAP TENDER WINNERS (WARM LIST)',
            '10-15%', tier_0_template),
        1: ('TIER1_CHAINS.csv', 'SUPERMARKET CHAINS & EN-GROS',
            '3-5%', tier_1_template),
        2: ('TIER2_DISTRIBUTORS.csv', 'DISTRIBUTORS & LOGISTICS (HIGH ROI)',
            '8-12%', tier_2_template),
        3: ('TIER3_HORECA_BUCHAREST.csv', 'HoReCa (VOLUME, LOW CONVERSION)',
            '1-2%', tier_3_template),
    }
    if tier_num not in tier_map:
        print(f"Unknown tier: {tier_num}. Use 0-3.")
        return
    filename, title, response_pct, template_fn = tier_map[tier_num]
    print(f"\n{'=' * 80}")
    print(f"CAMPAIGN TIER {tier_num}: {title}")
    print("=" * 80)
    path = DATA_DIR / filename
    if not path.exists():
        print(f"\nFile missing: {path}")
        return
    df = pd.read_csv(path)
    with_email = df[df['email'].notna()]
    print(f"\nTotal contacts: {len(df)}")
    print(f"With verified email: {len(with_email)}")
    print(f"Expected response: {response_pct}")
    if tier_num == 0:
        print(f"\n{'SAMPLE OUTREACH LIST (First 10):'}")
        print("-" * 80)
        for _, row in with_email.head(10).iterrows():
            company = str(row['company'])[:40].ljust(40)
            email = str(row['email'])[:35].ljust(35)
            print(f"  {company} | {email}")
    elif tier_num == 2 and 'county' in df.columns:
        print("\nRegional breakdown:")
        regional = df[df['county'].notna()].groupby('county').size()
        for county, count in regional.sort_values(ascending=False).head(5).items():
            emails = df[(df['county'] == county) & (df['email'].notna())].shape[0]
            print(f"  {county}: {count} total, {emails} with email")
    print(f"\n{'-' * 80}")
    print(template_fn())


def show_acquisition():
    """Show acquisition track detail."""
    print(f"\n{'=' * 80}")
    print("ACQUISITION TRACK: INSOLVENCY TARGETS")
    print("=" * 80)
    path = DATA_DIR / 'ACQUISITION_TARGETS.csv'
    if not path.exists():
        print(f"\nFile missing: {path}")
        return
    df = pd.read_csv(path)
    with_email = df[df['email'].notna()]
    print(f"\nTotal insolvent distributors/processors: {len(df)}")
    print(f"With email: {len(with_email)}")
    print(acquisition_template())


def main():
    args = sys.argv[1:]
    if "--status" in args:
        campaign_status()
        return
    if "--tier" in args:
        idx = args.index("--tier")
        tier_num = int(args[idx + 1]) if idx + 1 < len(args) else 0
        show_tier(tier_num)
        return
    campaign_status()
    for t in range(4):
        show_tier(t)
    show_acquisition()
    print(f"\n{'=' * 80}")
    print("EXECUTION CHECKLIST")
    print("=" * 80)
    print(execution_checklist())


if __name__ == "__main__":
    main()
