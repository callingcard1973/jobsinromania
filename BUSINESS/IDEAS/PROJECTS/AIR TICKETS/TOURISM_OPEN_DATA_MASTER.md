# Tourism Open Data — MASTER LIST (2026-04-12)

> Travel agencies, hotels, accommodations — every downloadable government list found.

---

## WHAT YOU ALREADY HAVE (in D:\MEMORY)

| Data | Location | Records |
|------|----------|---------|
| Romania SITUR agencies (fresh, today) | `AIR TICKETS/agentii_turistice_clean.csv` | 2,968 |
| Romania SITUR agencies (Jan 2026) | `CLAUDE/OPT/DATA/ROMANIA/TOURISM_AGENCIES_RO_NEW.csv` | 2,405 |
| Romania SITUR xlsx | `CLAUDE/OPT/DATA/ROMANIA/SITUR_agentii_turism_20260105.xlsx` | — |
| Romania SITUR restaurante | `CLAUDE/OPT/DATA/ROMANIA/SITUR_restaurante_20260105.xlsx` | — |
| France hebergements classés | `CLAUDE/OPT/DATA/EU_TOURISM/france_hebergements_20251220.csv` | 21,156 |
| Malta hotels | `CLAUDE/OPT/DATA/EU_TOURISM/malta_hotels_only_20251220.csv` | 12 |
| EU tourism registries guide | `CLAUDE/OPT/DATA/EU_TOURISM/EU_TOURISM_REGISTRIES.md` | 27 countries |
| EU tourism scraper | `CLAUDE/OPT/SCRAPERS/EUROPE/TOURISM/eu_tourism_scraper.py` | Production ready |
| Tourism campaign scripts | `CLAUDE/OPT/EMAIL/campaigns/TOURISM_RO/` | send_tourism.py etc. |

---

## TRAVEL AGENCY LISTS — DOWNLOADABLE NOW

### Direct Download (Excel/CSV, no scraping):

| Country | URL | Format | ~Records | Notes |
|---------|-----|--------|----------|-------|
| **Romania** | https://se.situr.gov.ro/OpenData/ExportToExcel?type=listaAgentii | Excel | 2,968 | DONE — already downloaded |
| **Italy (national)** | https://www.infotrav.it/allegati/Infotrav_elenco_agenzie.xlsx | Excel | ~11,000 | National INFOTRAV register |
| **Italy (Umbria)** | https://dati.regione.umbria.it/dataset/agenzie-di-viaggio-e-turismo | CSV/JSON | ~500 | Open data portal |
| **UK ATOL holders** | https://www.caa.co.uk/media/3ybn1oqx/historic-atolholders-combined-data-authorisation-report-2009-2025.xlsx | Excel | ~1,616 | Licensed tour operators |
| **Slovakia incoming** | http://files.slovakia.travel/PDF%20zoznamy/Incoming/Incoming_EN.pdf | PDF | ~200 | Incoming operators only |

### Scrapable (structured HTML tables, no captcha):

| Country | URL | ~Records | Difficulty |
|---------|-----|----------|------------|
| **France ROVS** | https://registre-operateurs-de-voyages.atout-france.fr/web/rovs/rechercheavancee | ~5,000 | Medium (pagination) |
| **Czech Republic** | https://mmr.gov.cz/cs/ministerstvo/cestovni-ruch/seznam-cestovnich-kancelari/ | ~1,500 | Easy (HTML table) |
| **Bulgaria NTR** | http://tourism.egov.bg/registers/TORegister.aspx | ~3,000 | Medium (ASP.NET) |
| **Turkey TURSAB** | https://www.tursab.org.tr/agency-search | ~4,500 | Medium (search API) |
| **Poland** | https://turystyka.gov.pl/CRZ.aspx | ~3,000 | Medium (ASP.NET) |
| **Portugal RNAVT** | https://rnt.turismodeportugal.pt/rnt/Pesquisa_AVT.aspx | ~2,000 | Medium |

### Not Available:
Germany, Spain (fragmented by region), Netherlands, Hungary, Cyprus, Slovenia, Croatia (agencies)

---

## HOTEL / ACCOMMODATION LISTS — DOWNLOADABLE NOW

### Direct Download (CSV/Excel, free):

| Source | URL / How | Format | ~Records | Coverage |
|--------|-----------|--------|----------|----------|
| **OpenStreetMap** (global) | overpass-turbo.eu query: `node["tourism"="hotel"];out;` | CSV/JSON | ~500,000 | Worldwide |
| **France** | data.gouv.fr/fr/datasets/hebergements-classes-en-france/ | CSV | ~18,000 | Classified hotels |
| **Croatia** | data.gov.hr search "smjestaj" | CSV | ~65,000 | All accommodation |
| **Portugal RNET** | dados.gov.pt search "alojamento" | CSV | ~7,000 | Licensed properties |
| **Greece** | data.gov.gr search "ξενοδοχεία" | CSV | ~10,000 | Licensed hotels |
| **Spain Catalonia** | analisi.transparenciacatalunya.cat — Establiments turístics | CSV/JSON | ~16,000 | Catalonia |
| **Spain Andalusia** | datosabiertos.juntadeandalucia.es — Alojamientos turísticos | CSV | ~8,000 | Andalusia |
| **Spain Valencia** | dadesobertes.gva.es — Registro establecimientos turísticos | CSV | ~12,000 | Valencia |
| **Spain Basque** | opendata.euskadi.eus — Alojamientos turísticos | CSV/JSON | ~2,000 | Basque Country |
| **Italy South Tyrol** | daten.buergernetz.bz.it | CSV | ~10,000 | South Tyrol |
| **Wikidata** (global) | query.wikidata.org SPARQL: `?hotel wdt:P31 wd:Q27686` | CSV/JSON | ~25,000 | Worldwide |
| **UK FSA ratings** | ratings.food.gov.uk/open-data (filter hotels/B&Bs) | CSV/XML | ~50,000 | UK |
| **USA Hawaii** | data.hawaii.gov — licensed accommodations | CSV | ~2,000 | Hawaii |
| **USA New York** | data.ny.gov — hotel/motel listings | CSV | varies | New York State |

### Scrapable:

| Source | URL | ~Records |
|--------|-----|----------|
| **Turkey** | yigm.ktb.gov.tr | ~4,500 |
| **data.europa.eu** | search "accommodation" "hotel" | dozens of datasets |

---

## TOTAL AVAILABLE (free, downloadable)

| Category | Records Available | Best Sources |
|----------|-------------------|-------------|
| **Travel agencies** | ~35,000 | Romania 2,968 + Italy 11K + UK 1.6K + France 5K scrapable + Czech+Bulgaria+Turkey |
| **Hotels/accommodation** | ~700,000+ | OSM 500K + Croatia 65K + Spain 38K + France 18K + Greece 10K + Wikidata 25K + others |
| **TOTAL** | **~735,000** | All free government/crowdsource data |

---

## PRIORITY DOWNLOADS (highest value for travel reselling)

### Immediate (direct download, 30 min):
1. **Italy INFOTRAV** — 11,000 travel agencies with contact → https://www.infotrav.it/allegati/Infotrav_elenco_agenzie.xlsx
2. **UK ATOL** — 1,616 licensed tour operators → CAA xlsx link above
3. **Croatia accommodations** — 65,000 → data.gov.hr
4. **France hotels** — 18,000 → data.gouv.fr (you already have 21K from Dec!)
5. **Portugal** — 7,000 → dados.gov.pt
6. **Greece** — 10,000 → data.gov.gr
7. **Spain regions** — 38,000 combined → 4 regional portals

### Week 1 (scraping needed):
8. **France ROVS** agencies — 5,000
9. **Czech Republic** agencies — 1,500
10. **Bulgaria NTR** agencies — 3,000
11. **Turkey TURSAB** agencies — 4,500
12. **OpenStreetMap global hotels** — 500,000

### Existing scraper to extend:
`CLAUDE/OPT/SCRAPERS/EUROPE/TOURISM/eu_tourism_scraper.py` — already covers Sweden, Portugal, Italy, Ireland, France, Malta, Bulgaria. Add the new sources above.

---

## USE CASE FOR TRAVEL RESELLING

All this data enables:
1. **Email campaigns to agencies** — partner proposals (already doing with Romania 1,448)
2. **Hotel partnership outreach** — "list your rooms on our platform, we bring workers"
3. **Accommodation affiliate** — Booking.com deeplinks for each hotel found
4. **Price comparison** — cross-reference government lists with Booking.com/Expedia for coverage gaps
5. **B2B lead generation** — every agency/hotel = potential customer for flight tickets
