import pandas as pd

df = pd.read_csv('cifn_eu_leads_tagged.csv')
summary = df['program_axa'].value_counts()
print('Project count by program/axa:')
print(summary)
print('\nSample projects by program/axa:')
for axa in summary.index[:5]:
    print(f'\n{axa}:')
    print(df[df['program_axa']==axa][['company','project_title']].head(2))
