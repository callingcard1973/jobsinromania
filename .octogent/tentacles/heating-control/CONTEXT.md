# Heating Control Tentacle

## Scope
D:\MEMORY\BUSINESS\IDEAS\HEATING_CONTROL\ — Remote thermal system control + heating optimization. PNRR Component 5.

## What It Does
Maps municipalities + district heating systems receiving PNRR funding for energy efficiency upgrades. Tracks heating system modernization tenders, thermal sensors, remote control system procurement.

## Key Outputs
- `heating_beneficiaries.csv` — Beneficiaries, allocation amounts, thermal focus
- `heating_tender_map.csv` — Real-time SICAP procurement (boilers, heat exchangers, controls, sensors)
- `heating_bundle_prospects.csv` — Municipalities eligible for Telegestiune + heating control bundle

## Strategic Focus
- Component 5 (Heating): €billions allocated, high-margin segment
- Remote thermal control: District heating + building-level optimization
- Telegestiune bundle: LED lighting + water monitoring + heating control = 3x TAM
- Regional focus: Cold climate regions (Carpathians, North, Moldova) = high heating ROI

## Deploy
raspibig: `/opt/ACTIVE/HEATING_CONTROL/`
- Cron: Weekly import (Mon 06:00), weekly enrich (Mon 07:00), daily SICAP detect (11:00)
- Outputs: DATA/ subdirectory
- Logs: /var/log/heating_*.log

## Scrapers
1. `pnrr_heating_importer.py` — PNRR Comp 5 beneficiaries (heating/thermal keywords)
2. `heating_tender_detector.py` — Real-time SICAP monitoring (heating system CPV codes)
3. `bundle_matcher.py` — Cross-ref with Telegestiune + water leads for triple bundle

## Contact
Ovidiu: Heating utility networks. Tudor: Execution + 3-component bundle strategy.
