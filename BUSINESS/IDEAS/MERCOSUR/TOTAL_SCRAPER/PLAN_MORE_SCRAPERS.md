# PLAN: Additional Mercosur Data Sources

## PRIORITY 1 - High Value (implement now)

### 1. Brazilian Customs (SISCOMEX)
- URL: https://www.gov.br/siscomex/
- Data: 50K+ exporters with HS codes
- Method: API + web scrape

### 2. Argentine Exporters (Argentina Trade Net)
- URL: https://www.argentinatradenet.gov.ar/
- Data: 15K+ exporters by sector
- Method: Web scrape catalog

### 3. Chilean Exporters (ProChile Directory)
- URL: https://www.prochile.gob.cl/exportadores/
- Data: 8K+ exporters
- Method: Web scrape + API

### 4. Uruguay Exporters (Uruguay XXI)
- URL: https://www.uruguayxxi.gub.uy/
- Data: 3K+ exporters
- Method: Web scrape

### 5. LinkedIn Sales Navigator
- Search: "exporter" + country + sector
- Data: Decision makers with emails
- Method: Apollo.io or Snov.io API

## PRIORITY 2 - Trade Shows (seasonal)

### 6. APAS Show 2026 (Sao Paulo - May)
- URL: https://www.apasshow.com.br/
- Data: 600+ food exhibitors
- Method: Exhibitor list scrape

### 7. SIAL Paris (October)
- URL: https://www.sialparis.com/
- Data: Latin American exhibitors
- Method: Exhibitor directory

### 8. Anuga (Cologne - October)
- URL: https://www.anuga.com/
- Data: South American food exporters
- Method: Exhibitor search

## PRIORITY 3 - Industry Associations

### 9. CAMEX (Brazilian Chamber of Commerce)
- URL: https://www.camex.gov.br/
- Data: Export companies by sector

### 10. CILEA (Latin American Exporters)
- URL: https://cilea.org/
- Data: Cross-border trade companies

### 11. Mercosur Chamber of Commerce
- URL: https://www.mercosurcamara.com/
- Data: B2B trade contacts

## PRIORITY 4 - Open Data APIs

### 12. UN Comtrade API
- URL: https://comtrade.un.org/api/
- Data: Trade flows by HS code
- Method: REST API

### 13. World Bank WITS
- URL: https://wits.worldbank.org/
- Data: Tariff and trade data
- Method: REST API

### 14. ITC Trade Map
- URL: https://www.trademap.org/
- Data: Export statistics
- Method: Web scrape (login required)

## PRIORITY 5 - Enrichment Sources

### 15. Hunter.io
- Find emails by company domain
- 50 free/month

### 16. Snov.io
- Email finder + verifier
- LinkedIn integration

### 17. Apollo.io
- Company data + contacts
- API access

## EXECUTION ORDER

Week 1:
- [x] Run existing 40 scrapers
- [ ] Brazilian Customs (SISCOMEX)
- [ ] Argentine Exporters
- [ ] UN Comtrade API

Week 2:
- [ ] Chilean ProChile
- [ ] Uruguay XXI
- [ ] Industry associations

Week 3:
- [ ] Trade show exhibitors
- [ ] Enrichment (Hunter/Snov)
- [ ] Data consolidation

## OUTPUT TARGET

| Source | Est. Records | With Email |
|--------|--------------|------------|
| APEX Brasil | 12K | 30% |
| ConnectAmericas | 20K | 40% |
| SISCOMEX | 50K | 20% |
| Argentina Trade | 15K | 25% |
| ProChile | 8K | 35% |
| Associations | 5K | 50% |
| Trade Shows | 2K | 60% |
| TOTAL | 112K | ~30K |
