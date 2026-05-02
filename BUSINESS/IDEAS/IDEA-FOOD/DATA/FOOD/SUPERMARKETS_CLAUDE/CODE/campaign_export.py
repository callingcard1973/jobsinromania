#!/usr/bin/env python3
"""Export segmented contact lists for email campaigns.

Creates CAMPAIGN_SEGMENTS/ CSVs for each tier, deduped by email.
Used by segment_and_analyze.py.
"""

from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "DATA"

EXPORT_COLS = ['company', 'email', 'county', 'category', 'phone', 'website']
EXPORT_COLS_SLIM = ['company', 'email', 'county', 'category', 'phone']
ACQUISITION_CATS = ['distributor', 'processor', 'dairy', 'meat']


def _dedup_with_email(df, cols=None):
    """Filter to rows with email, deduplicate, sort by company."""
    cols = cols or EXPORT_COLS
    available = [c for c in cols if c in df.columns]
    return (df[df['email'].notna()][available]
            .drop_duplicates(subset=['email'])
            .sort_values('company'))


def export_campaign_lists(tiers, seap_overlap, insolvent):
    """Export segmented lists for campaigns."""
    print("\n" + "=" * 80)
    print("EXPORTING CAMPAIGN LISTS")
    print("=" * 80)

    output_dir = DATA_DIR / "CAMPAIGN_SEGMENTS"
    output_dir.mkdir(exist_ok=True)

    exports = [
        ("Tier 0 (SEAP)", tiers['tier0'], EXPORT_COLS,
         "TIER0_SEAP_WINNERS.csv"),
        ("Tier 1 (Chains)", tiers['tier1'], EXPORT_COLS,
         "TIER1_CHAINS.csv"),
        ("Tier 2 (Distributors)", tiers['tier2'], EXPORT_COLS,
         "TIER2_DISTRIBUTORS.csv"),
    ]

    for label, df, cols, filename in exports:
        result = _dedup_with_email(df, cols)
        result.to_csv(output_dir / filename, index=False)
        print(f"\n  {label}: {len(result)} with email -> {filename}")

    # Tier 3: HoReCa Bucharest sample only
    tier3_buc = tiers['tier3'][tiers['tier3']['county'] == 'Bucuresti']
    tier3_out = _dedup_with_email(tier3_buc, EXPORT_COLS_SLIM)
    tier3_out.to_csv(output_dir / "TIER3_HORECA_BUCHAREST.csv", index=False)
    print(f"  Tier 3 (HoReCa/Bucharest): {len(tier3_out)} with email"
          f" -> TIER3_HORECA_BUCHAREST.csv")

    # Acquisition targets
    high_value = insolvent[insolvent['category'].isin(ACQUISITION_CATS)][
        ['company', 'email', 'county', 'category']
    ].drop_duplicates(subset=['email'])
    high_value.to_csv(output_dir / "ACQUISITION_TARGETS.csv", index=False)
    print(f"  Acquisition targets: {high_value['email'].notna().sum()}"
          f" with email -> ACQUISITION_TARGETS.csv")

    print(f"\n  All segments exported to {output_dir.name}/")
