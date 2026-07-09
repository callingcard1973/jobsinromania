import pandas as pd
import re

def extract_company(row):
    text = f"{row['company']} {row['project_title']}"
    m = re.search(r'(S\.C\.|SC)?\s*([A-Z0-9][A-Za-z0-9 &\-\.]+?)(?:\s+(S\.R\.L\.|SRL|S\.A\.|SA|SRL-D|SRL D|SRL,|SRL\.|SRL\s|SA\s|SRL$|SA$))', text, re.IGNORECASE)
    if m:
        return (m.group(2) + ' ' + m.group(3)).strip()
    m2 = re.search(r'([A-Z][A-Z0-9 &\-]{2,})', text)
    if m2:
        return m2.group(1).strip()
    return ''

df = pd.read_csv('cifn_eu_leads_clean.csv')
df['company_extracted'] = df.apply(extract_company, axis=1)
df.to_csv('cifn_eu_leads_companyfix.csv', index=False)
print(df[['company','project_title','company_extracted']].head(12))
