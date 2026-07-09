"""
Segmentation & Heatmap Analysis
Builds campaign tiers, geographic distribution, and acquisition targets from existing data.
"""

import pandas as pd
from pathlib import Path

from campaign_export import export_campaign_lists

DATA_DIR = Path(__file__).parent.parent / "DATA"

def load_data():
    """Load main datasets."""
    print("Loading data...")
    contacts = pd.read_csv(DATA_DIR / "ROMANIA_FOOD_DISTRIBUTION_CONTACTS.csv")
    seap_overlap = pd.read_csv(DATA_DIR / "seap_food_overlap.csv")
    insolvent = pd.read_csv(DATA_DIR / "insolvent_contacts_flagged.csv")
    return contacts, seap_overlap, insolvent

def build_tiers(contacts, seap_overlap, insolvent):
    """Segment contacts into campaign tiers."""
    print("\n" + "="*80)
    print("TIER SEGMENTATION")
    print("="*80)
    
    # Remove insolvent contacts
    insolvent_emails = set(insolvent['email'].dropna())
    contacts_clean = contacts[~contacts['email'].isin(insolvent_emails)].copy()
    
    print(f"\nTotal contacts: {len(contacts)}")
    print(f"Insolvent to remove: {len(insolvent)} (unique emails: {len(insolvent_emails)})")
    print(f"Clean contacts: {len(contacts_clean)}")
    
    # Tier 0: SEAP winners already in database
    seap_winners_set = set(seap_overlap['fd_company'].dropna().str.upper())
    tier0 = contacts_clean[contacts_clean['company'].str.upper().isin(seap_winners_set)].copy()
    
    # Tier 1: Supermarket chains + en-gros
    tier1 = contacts_clean[contacts_clean['category'].isin(['supermarket', 'en-gros'])].copy()
    
    # Tier 2: Distributors + logistics
    tier2 = contacts_clean[contacts_clean['category'].isin(['distributor', 'logistics'])].copy()
    
    # Tier 3: HoReCa (hotels, restaurants, catering)
    tier3 = contacts_clean[contacts_clean['category'] == 'horeca'].copy()
    
    # Tier 4: Processors + dairy + meat
    tier4 = contacts_clean[contacts_clean['category'].isin(['processor', 'dairy', 'meat'])].copy()
    
    # Calculate email coverage per tier
    tier_stats = [
        ("Tier 0: SEAP Winners (Warm List)", tier0),
        ("Tier 1: Supermarket Chains + En-Gros", tier1),
        ("Tier 2: Distributors + Logistics", tier2),
        ("Tier 3: HoReCa", tier3),
        ("Tier 4: Processors + Dairy + Meat", tier4),
    ]
    
    for name, df in tier_stats:
        with_email = df['email'].notna().sum()
        total = len(df)
        coverage = (with_email / total * 100) if total > 0 else 0
        print(f"\n{name}")
        print(f"  Total: {total:,} | With email: {with_email:,} ({coverage:.1f}%)")
    
    return {
        'tier0': tier0,
        'tier1': tier1,
        'tier2': tier2,
        'tier3': tier3,
        'tier4': tier4,
        'all_clean': contacts_clean
    }

def geographic_heatmap(tiers, contacts):
    """Build county-level heatmaps by category."""
    print("\n" + "="*80)
    print("GEOGRAPHIC HEATMAPS (Top 10 counties by category)")
    print("="*80)
    
    categories = contacts['category'].unique()
    
    heatmaps = {}
    
    for cat in sorted([c for c in categories if pd.notna(c)]):
        df = contacts[contacts['category'] == cat]
        county_counts = df['county'].value_counts().head(10)
        county_emails = df.groupby('county')['email'].apply(lambda x: x.notna().sum()).sort_values(ascending=False).head(10)
        
        heatmaps[cat] = {
            'total_by_county': county_counts,
            'emails_by_county': county_emails
        }
        
        print(f"\n{cat.upper()}")
        print("  County | Total Contacts | With Email")
        print("  " + "-"*45)
        for county in county_counts.index[:10]:
            total = county_counts[county]
            emails = county_emails.get(county, 0)
            print(f"  {county:15} | {total:4} | {emails:4}")
    
    return heatmaps

def segmentation_by_region(tiers):
    """Break down Tier 3 (HoReCa) by region for email campaigns."""
    print("\n" + "="*80)
    print("TIER 3 (HoReCa) REGIONAL BREAKDOWN - Campaign Batches")
    print("="*80)
    
    tier3 = tiers['tier3']
    
    # Remove empty counties
    tier3_with_county = tier3[tier3['county'].notna()]
    
    county_stats = tier3_with_county.groupby('county').agg({
        'company': 'count',
        'email': lambda x: x.notna().sum()
    }).rename(columns={'company': 'total', 'email': 'with_email'}).sort_values('total', ascending=False)
    
    print("\nTop 15 HoReCa regions:")
    print("County | Total | With Email | Email %")
    print("-" * 50)
    
    total_contacts = 0
    total_emails = 0
    
    for county, row in county_stats.head(15).iterrows():
        total = int(row['total'])
        emails = int(row['with_email'])
        pct = (emails / total * 100) if total > 0 else 0
        total_contacts += total
        total_emails += emails
        print(f"{county:20} | {total:5} | {emails:5} | {pct:5.1f}%")
    
    print(f"\nSubtotal (top 15): {total_contacts:,} contacts, {total_emails:,} with email")
    
    # Identify gaps (counties with HoReCa contacts but no distributors)
    all_counties = set(tier3_with_county['county'].unique())
    distributor_counties = set(tiers['tier2'][tiers['tier2']['county'].notna()]['county'].unique())
    gaps = sorted(all_counties - distributor_counties)
    
    if gaps:
        print(f"\n  GEOGRAPHIC GAPS (HoReCa but no distributors in DB):")
        print(f"   {', '.join(gaps[:10])}" + ("..." if len(gaps) > 10 else ""))
    
    return county_stats

def acquisition_targets(insolvent, contacts):
    """Analyze insolvency data for acquisition opportunities."""
    print("\n" + "="*80)
    print("ACQUISITION TARGETS (Insolvent companies)")
    print("="*80)
    
    # Category breakdown
    print("\nInsolvent contacts by category:")
    category_counts = insolvent['category'].value_counts()
    for cat, count in category_counts.head(10).items():
        with_email = insolvent[insolvent['category'] == cat]['email'].notna().sum()
        print(f"  {cat:20} | {count:4} | {with_email:4} with email")
    
    # Geographic concentration
    print("\nTop 10 counties with insolvent companies:")
    county_counts = insolvent['county'].value_counts().head(10)
    for county, count in county_counts.items():
        print(f"  {county:20} | {count:4}")
    
    # High-value targets: distributors and processors going under
    high_value = insolvent[insolvent['category'].isin(['distributor', 'processor', 'dairy', 'meat'])]
    with_email = high_value['email'].notna().sum()
    
    print(f"\nHIGH-VALUE ACQUISITION TARGETS:")
    print(f"   Distributors/Processors failing: {len(high_value)}")
    print(f"   With email contact: {with_email}")
    print(f"   -> Potential to acquire distribution networks, client lists, assets")
    
    return high_value

def seap_analysis(seap_overlap, tier2, tier4):
    """Analyze SEAP winners in your database."""
    print("\n" + "="*80)
    print("SEAP TENDER WINNERS IN DATABASE (Tier 0 - Warm List)")
    print("="*80)
    
    print(f"\nTotal overlaps: {len(seap_overlap)}")
    
    # Which are distributors/processors (likely to buy from us)?
    seap_with_email = seap_overlap['email'].notna().sum()
    print(f"With email: {seap_with_email}")
    
    # Subcategory breakdown
    print("\nSEAP winners by category:")
    cat_counts = seap_overlap['category'].value_counts()
    for cat, count in cat_counts.items():
        with_email = seap_overlap[seap_overlap['category'] == cat]['email'].notna().sum()
        print(f"  {cat:20} | {count:4} | {with_email:4} with email")
    
    # These are proven buyers
    print("\nKEY INSIGHT:")
    print("   SEAP winners have:")
    print("   - Proven they can supply at scale")
    print("   - Institutional buyer relationships")
    print("   - Your contact info")
    print("   -> START EMAIL CAMPAIGN HERE (warm list, highest conversion)")
    
    return seap_overlap


def main():
    contacts, seap_overlap, insolvent = load_data()
    tiers = build_tiers(contacts, seap_overlap, insolvent)
    heatmap = geographic_heatmap(tiers['all_clean'], contacts)
    regional = segmentation_by_region(tiers)
    targets = acquisition_targets(insolvent, contacts)
    seap = seap_analysis(seap_overlap, tiers['tier2'], tiers['tier4'])
    export_campaign_lists(tiers, seap_overlap, insolvent)
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nNext steps:")
    print("1. Review TIER0_SEAP_WINNERS.csv (108 warm list)")
    print("2. Draft 3 email templates (Tier 0/1, Tier 2, Tier 3)")
    print("3. Start with TIER0 as test campaign")
    print("4. If response > 10%, scale to TIER1 and TIER2")
    print("5. Investigate high-value acquisition targets")

if __name__ == "__main__":
    main()
