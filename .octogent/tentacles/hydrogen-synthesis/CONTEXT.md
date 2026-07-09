# Hydrogen Synthesis Tentacle

## Scope
D:\MEMORY\BUSINESS\IDEAS\HYDROGEN\ — Green hydrogen production + ammonia spinoff initiatives. PNRR Component 2.

## What It Does
Maps municipalities + companies receiving PNRR funding for hydrogen/renewable energy projects. Tracks electrolyzer procurement, renewable capacity partnerships, ammonia synthesis R&D opportunities.

## Key Outputs
- `hydrogen_beneficiaries.csv` — Beneficiaries, allocation amounts, technology focus
- `hydrogen_tender_map.csv` — Real-time SICAP procurement (electrolyzers, fuel cells, renewable power)
- `ammonia_spinoff_prospects.csv` — High-potential partners for ammonia synthesis (Ovidiu's network)

## Strategic Focus
- Component 2 (Green energy transition): €billions allocated
- Hydrogen production: Electrolyzer + renewable power coupling
- Ammonia synthesis: Value-add spinoff (H₂ + N₂ → NH₃ for agriculture/industry)
- Ovidiu partnerships: EU cluster networks, North Africa expansion potential

## Deploy
raspibig: `/opt/ACTIVE/HYDROGEN/`
- Cron: Weekly import (Mon 06:00), weekly enrich (Mon 07:00), daily SICAP detect (11:00)
- Outputs: DATA/ subdirectory
- Logs: /var/log/hydrogen_*.log

## Scrapers
1. `pnrr_hydrogen_importer.py` — PNRR Comp 2 beneficiaries (hydrogen keyword detection)
2. `hydrogen_tender_detector.py` — Real-time SICAP monitoring (electrolyzer CPV codes)
3. `ammonia_spinoff_matcher.py` — Cross-ref with industrial chemistry contacts

## Contact
Ovidiu: EU networks + hydrogen strategy. Tudor: Execution + tender detection.
