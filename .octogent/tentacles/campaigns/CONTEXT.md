# Campaigns Tentacle

## Scope
D:\MEMORY\CODE\CAMPAIGNS\ — email/phone outreach pipelines

## Key files
- CODE\CAMPAIGNS\CODE\ — send_campaign.py, orchestrator.py
- CODE\CAMPAIGNS\EMAIL PERSONAL\CODE\ — step*.sql, step*.py (enrichment pipeline, steps 1-46+)
- CODE\CAMPAIGNS\HARGHITA\ — 770-company RO regional campaign
- CODE\CAMPAIGNS\EMAIL_BRAIN\ — 19-inbox classifier

## DB
PostgreSQL 18, port 5433, interjob_master, user tudor/tudor
companies_clean (33M rows), master_emails (1.03M), ted_awards (6.2M)

## Active campaigns on raspibig (192.168.100.21)
DELIVERY_RO_2026, HARGHITA phases 1-3, FI_TED_CONSTRUCTION, ANOFM sectors (16 active)

## Rules
- Never delete CSVs without confirming DB backup
- Never push live sends without checking Brevo bounce rate < 30%
- Daily limit per sender: 290 (Brevo), 235 (Gmail), 250 (Zoho)
