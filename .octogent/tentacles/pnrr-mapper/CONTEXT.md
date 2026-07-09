# PNRR Component Mapper Tentacle

## Scope
D:\MEMORY\BUSINESS\IDEAS\PNRR_MAPPER\ — Intelligence layer for PNRR-funded municipalities by component (1-14 sectors).

## What It Does
Maps which Romanian municipalities are receiving EU PNRR funding for which components (water, heating, green spaces, digital, etc.) + cross-refs with real-time SICAP procurement activity.

## Key Outputs
- `pnrr_municipalities_enriched.csv` — All 3K+ primării, enriched with contact data + PNRR allocations
- `leads_by_component.csv` — Sorted by sector + allocation amount (for outreach)
- `pnrr_tender_map.csv` — Real-time SICAP matches (daily)

## 14 Components
1. Green transition (€billions) | 4. Water | 5. Heating | 8. Green spaces (Telegestiune)
2. Hydrogen | 6. Pollution | 7. Biodiversity | 9. Social housing | 10. Education
3. Rail | 11. Healthcare | 12. Digital | 13. Competitiveness | 14. Social + employment

## Deploy
raspibig: /opt/ACTIVE/PNRR_MAPPER/
- Cron: Weekly import (Mon 06:00), weekly enrich (Mon 07:00), daily SICAP detect (10:00), monthly score (1st month 08:00)
- Outputs: DATA/ subdirectory
- Logs: /var/log/pnrr_*.log

## Scrapers
1. `pnrr_beneficiary_importer.py` — data.gov.ro PNRR payments → component detection
2. `pnrr_municipality_enricher.py` — Cross-ref with primarii_export.csv
3. `leads_scorer_by_component.py` — Rank by allocation + activity
4. `sicap_pnrr_detector.py` — Real-time SICAP monitoring (all components)

## Strategic Use
- Telegestieu cold outreach (Component 8: green urban spaces, €allocation tracking)
- Cross-sell (water monitoring, heating systems, digital/IoT)
- Market intelligence (which components are active, when budgets release)
