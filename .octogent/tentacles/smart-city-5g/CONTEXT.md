# Smart City 5G Tentacle

## Scope
D:\MEMORY\BUSINESS\IDEAS\SMART_CITY_5G\ — 5G backbone + IoT sensor platform. PNRR Component 12.

## What It Does
Maps municipalities + telecom operators receiving PNRR funding for 5G rollout + digital infrastructure. Tracks network deployment, edge computing, smart city sensor networks, IoT platform procurement.

## Key Outputs
- `digital_5g_beneficiaries.csv` — Beneficiaries, allocation amounts, infrastructure focus
- `digital_5g_tender_map.csv` — Real-time SICAP procurement (5G equipment, edge servers, sensors)
- `smart_city_platform_prospects.csv` — Municipalities with 5G backbone ready for IoT/sensor deployment

## Strategic Focus
- Component 12 (Digital): €billions for 5G + digital transformation
- Smart City OS: Central control platform for Telegestiune + water + heating + traffic + utilities
- High-margin recurring: Software licenses, cloud services, monitoring dashboards
- EU expansion: 5G deployment coordination across member states

## Deploy
raspibig: `/opt/ACTIVE/SMART_CITY_5G/`
- Cron: Weekly import (Mon 06:00), weekly enrich (Mon 07:00), daily SICAP detect (11:00)
- Outputs: DATA/ subdirectory
- Logs: /var/log/5g_*.log

## Scrapers
1. `pnrr_digital_importer.py` — PNRR Comp 12 beneficiaries (5G/digital/IoT keywords)
2. `digital_tender_detector.py` — Real-time SICAP monitoring (telecom equipment, edge servers)
3. `smart_city_platform_matcher.py` — Link to Telegestiune + water + heating for OS consolidation

## Contact
Ovidiu: Telecom partnerships + EU digital networks. Tudor: Execution + platform strategy.
