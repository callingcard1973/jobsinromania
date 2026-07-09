#!/usr/bin/env python3
"""Extract electrician contacts from ANRE for ElectroSafe outreach."""

import pandas as pd
from pathlib import Path
import re

# Load ANRE electricians
anre_path = Path("../../ANRE/DATA/electricieni_enriched.csv")
if not anre_path.exists():
    anre_path = Path("D:/MEMORY/BUSINESS/IDEAS/ISCIR/ANRE/DATA/electricieni_enriched.csv")

print("Loading ANRE electricians...")
df = pd.read_csv(anre_path, encoding='utf-8-sig')
print(f"  Total rows: {len(df):,}")

# Filter: active (expiry > today), has email
df['DataExpirare'] = pd.to_datetime(df['DataExpirare'], errors='coerce')
today = pd.Timestamp.now()
active = df[df['DataExpirare'] > today].copy()
print(f"  Active (not expired): {len(active):,}")

# Get email (prioritize email_db over email2_db)
active['email'] = active['email_db'].fillna(active['email2_db'])
has_email = active[active['email'].notna() & (active['email'] != '')].copy()
print(f"  With email: {len(has_email):,}")

# Clean phone numbers (valid RO format: 10-13 digits starting with 0)
def clean_phone(p):
    if pd.isna(p):
        return None
    p = str(p).strip()
    digits = re.sub(r'\D', '', p)
    if len(digits) >= 10 and digits.startswith('0'):
        return p
    return None

has_email['phone_clean'] = has_email['TelefonFax'].apply(clean_phone)

# Output
output = has_email[['NumePrenume', 'Localitate', 'Judet', 'email', 'phone_clean']].copy()
output.columns = ['name', 'city', 'county', 'email', 'phone']
output = output.drop_duplicates(subset=['email'])

output_path = Path("DATA/electricians_1000_ready.csv")
output.head(1000).to_csv(output_path, index=False, encoding='utf-8')

print(f"\nExtracted: {min(1000, len(output)):,} electricians")
print(f"  Email coverage: {(output['email'].notna().sum() / len(output) * 100):.1f}%")
print(f"  Phone coverage: {(output['phone'].notna().sum() / len(output) * 100):.1f}%")
print(f"  Saved: {output_path}")

# Summary by county
print("\nTop counties:")
for county, count in output['county'].value_counts().head(10).items():
    print(f"  {county}: {count}")
