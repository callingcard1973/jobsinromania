import pandas as pd
import re

# Load mapping
mapping = {
    'PRNE': 'Program Regional Nord-Est',
    'PRNV': 'Program Regional Nord-Vest',
    'PRC': 'Program Regional Centru',
    'PRSM': 'Program Regional Sud Muntenia',
    'PRSVO': 'Program Regional Sud-Vest Oltenia',
    'PTJ': 'Program Tranziție Justă',
    'PS': 'Program Sănătate',
    'POCU': 'Program Operațional Capital Uman',
    'POC': 'Program Operațional Competitivitate',
    'POR': 'Program Operațional Regional',
    'FSE': 'Fondul Social European',
    'SDS': 'Scoala dupa Scoala',
}

# Compile regex for all codes
pattern = re.compile(r'(' + '|'.join(mapping.keys()) + r')', re.IGNORECASE)

def tag_program_axa(row):
    text = f"{row['company']} {row['project_title']} {row.get('description','')}"
    m = pattern.search(text)
    if m:
        code = m.group(1).upper()
        return mapping.get(code, code)
    return ''

df = pd.read_csv('cifn_eu_leads_clean.csv')
df['program_axa'] = df.apply(tag_program_axa, axis=1)
df.to_csv('cifn_eu_leads_tagged.csv', index=False)
print(df[['company','project_title','program_axa']].head(12))
