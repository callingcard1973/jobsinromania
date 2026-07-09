# CLAUDE.md - Trade Agreement Arbitrage Implementation

| category | status | owner | updated |
| other | active | tudor | 2026-03-21 |

## Purpose

Scripts and tools to execute trade agreement profit opportunities. Core model: broker/matchmaker connecting EU buyers (existing TED winners DB) with Mercosur/Canada suppliers (to be acquired).

## Parent Context

- Business context: `../CLAUDE.md` (agreement status, winners/losers, opportunities)
- Research brief: `EXPLORE_TRADE_OPPORTUNITIES.md` (5 research tasks)

## Assets Available

| Asset | Location | Records |
| TED winners | interjob_master.ted_winners | 1.57M (375K emails) |
| Companies | interjob_master.companies | 500K (42 countries) |
| Enrichment | /opt/ACTIVE/INFRA/SKILLS/ | 45+ scripts |
| Email system | /opt/ACTIVE/EMAIL/CAMPAIGNS/ | 10+ domains |

## Implementation Tasks

### Phase 1: Data Acquisition (Mercosur Suppliers)

Scripts needed:

| Script | Target | Est. Records |
| apex_brasil_scraper.py | APEX Brasil exporter directory | 12K+ |
| brazil_exporters_scraper.py | Brazilian exporters portal | 10K+ |
| argentina_exporta_scraper.py | Argentina Exporta | 5K+ |
| trade_show_scraper.py | APAS, Fispal, Expoalimentaria exhibitors | 3K+ |

### Phase 2: Data Acquisition (Canadian)

| Script | Target | Est. Records |
| canada_exporters_scraper.py | Canadian Trade Commissioner | TBD |
| edc_scraper.py | Export Development Canada | TBD |
| canada_registry_scraper.py | Canadian company registries | TBD |

### Phase 3: Matching Engine

| Script | Purpose |
| sector_matcher.py | Match EU buyers by sector to Mercosur suppliers |
| opportunity_scorer.py | Score matches by tariff savings potential |
| campaign_generator.py | Generate targeted email campaigns |

### Phase 4: Outreach
