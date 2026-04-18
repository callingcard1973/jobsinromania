# TERENURI AGENTS SCRIPTS (IDEA-056 scripts)

10 agenti automatizati detectare chilipiruri imobiliare din surse publice romanesti.

## Agenti
- `listing_hunter.py` — scrape OLX + Imobiliare.ro + Storia.ro
- `price_anomaly.py` — detecteaza preturi sub piata (>20% sub median judet)
- `cma_agent.py` — Comparative Market Analysis automat
- `geo_intelligence.py` — harta concentrare oportunitati per judet
- `deal_alert.py` — alert Telegram cand apare chilipir
- `run_terenuri.sh` — orchestrator toate scripturile

## Surse date
OLX, Imobiliare.ro, Storia.ro, BPI licitatii silite, MADR licitatii terenuri.

## Legatura
Alimenteaza IDEA-154 FARM DISTRESSED SALES PLATFORM si IDEA-070 MADR LAND INVESTOR DATA.
