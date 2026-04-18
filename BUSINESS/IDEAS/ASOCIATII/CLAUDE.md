# ASOCIATII — Romanian NGO Registry & Lead Generation

140,664 active NGOs from Ministry of Justice registry, processed into commercial lead lists with company matching and enrichment.

## Status: OPERATIONAL — Pipeline Complete

**Source**: Ministry of Justice XLSX (weekly updates) | **Last refresh**: 2026-03-12

## Data Assets

| Dataset | Rows | What |
|---------|------|------|
| ONG_REGISTRU_NATIONAL | 150,667 | Full registry (active + inactive) |
| ONG_ACTIVE | 140,664 | Active NGOs only |
| ONG_SHORTLIST_5000 | 5,001 | Priority-scored lead list |
| ong_pe_judete/ | 43 files | One CSV per Romanian county |
| ONG_SUMAR_JUDETE | 176 | Aggregated by county + category |
| ONG_SUMAR_LOCALITATI | 26,739 | Aggregated by city |

**Breakdown**: 118K associations, 19.7K foundations, 1.6K federations, 772 unions, 41 foreign entities.

**Top counties**: Bucuresti (23,675), Cluj (8,417), Timis (5,594), Bihor (4,679), Sibiu (4,631).

## Scripts

| Script | What it does |
|--------|-------------|
| `generate_ong_registry.py` | 5 XLSX -> unified CSV/TSV (150K rows) |
| `generate_ong_shortlist.py` | Scoring algorithm -> 5,000 priority leads |
| `deploy_ong_to_raspibig.py` | SCP + SSH deploy to 192.168.100.21 |
| `raspibig_ong_ingest_remote.py` | PostgreSQL ingest + company matching (exact/fuzzy) |

**Scoring**: County bonus (+40 Bucuresti) + locality density (+24 for 2000+ NGOs) + category bonus (+20 federation) + status bonus (+8 active).

## Enrichment Pipeline

Registry -> raspibig PostgreSQL -> multi-strategy name matching against company DB:
- Exact full-name match (score: 100)
- Exact core-name match (score: 94, removes entity stopwords)
- Fuzzy core-match (threshold: 88-93%, sequence similarity)

Enriched with: CUI, company name, county, city, email, phone, website, CAEN, sector, employees, revenue, ANAF status, lead score.

## Secondary Project: Asociatii de Proprietari

Property owner associations — research phase only. No automated collection yet.
- No single comprehensive open-source registry exists
- Manual collection needed from municipal sources (PDFs, thermal rehab programs, council decisions)
- Priority: Bucuresti -> Ilfov -> Cluj -> Timis -> Iasi -> Constanta

## Business Value

- Campaign targeting: 5,000 scored leads ready for outreach
- NGO partnerships for EU funding proposals
- Property associations: potential for building maintenance/renovation services

## Related

- `D:\MEMORY\DELIVERY\` — email campaign infrastructure
- `D:\MEMORY\IDEAS\EU_FUNDING\` — EU funding opportunities (NGOs are applicants)
- `D:\MEMORY\IDEAS\COOPERATIVA BUSINESS\` — cooperative model applies to NGO aggregation
