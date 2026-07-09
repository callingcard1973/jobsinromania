# EBRD Tentacle

## Scope
D:\MEMORY\DATA\BERD EBRD\ — 42 country project files
D:\MEMORY\DATA\EBRD\ — processed data
D:\MEMORY\DATA\OPENTENDER\ — EU tender data

## DB (interjob_master on raspibig)
- ebrd_projects: 4,176 projects, 42 countries
- tenders: 5.1M EU tenders
- ted_awards: 6.2M EU procurement winners
- seap_ro_awards: RO SEAP (growing)

## Active Campaigns
- EBRD A: 100/day (subcontractors)
- EBRD B: 50/day (workers)
- EBRD C: pending
- Scripts: /opt/ACTIVE/EBRD/ on raspibig
- Cron: 10:00 daily

## Key Files
DATA\BERD EBRD\CAMPAIGN_CSV\ — per-country CSVs
DATA\BERD EBRD\CAMPAIGNS\ — campaign configs
