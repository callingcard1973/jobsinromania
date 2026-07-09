# Telegestiune Tentacle

## Scope
D:\MEMORY\BUSINESS\IDEAS\TELEGESTIUNE\ — Smart city LED lighting management system project

## What It Does
Remote management platform for municipal public lighting. Centralized control, 25–40% energy savings, EU-fundable (PNRR Component 8, Horizon Europe).

## Market
Municipalities + regional authorities. Typical deal: €50K–€500K system + installation. 3–5 year ROI.

## Channels
- SICAP tenders (CPV 31520000 LED + 77310000 management)
- PNRR green space beneficiaries  
- Cold outreach to 100–200 primării with old lighting infrastructure
- Framework agreements (EU GSA, national supplier lists)

## Run
1. Monitor SICAP for LED management tenders (weekly)
2. Identify PNRR-funded municipalities + ROI calculate
3. Send cold outreach + pitch via WhatsApp

## Key Files
CLAUDE.md — context + roles
README.md — product overview + market positioning
procurement_guide.md — SEAP/SICAP response checklist
roi_calculator.py — ROI model generator
sicap_monitor_telegestiune.py — LED management tender scraper
leads_scoring.py — municipality scoring/ranking

## Partners
Ovidiu Pacala (strategy + networks + EU grants)
Tudor (proposals + implementation)

## Deploy
raspibig: /opt/ACTIVE/TELEGESTIUNE/
- sicap_monitor_telegestiune.py (cron: weekly)
- roi_calculator.py (on-demand per lead)
- leads_scoring.py (monthly refresh)
