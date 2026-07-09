# HORECA Database Summary

Created: 2026-03-20

## Actionable Data (With Email)

**Database:** `horeca` (PostgreSQL)
**Export:** `/opt/ACTIVE/IDEAS/FOOD/HORECA_28K_UNIQUE_EMAILS.csv` (2.6 MB)

| Country | Unique Emails | Phones | Top Sources |
|---------|---------------|--------|-------------|
| Romania | 20,296 | 4,963 | horeca_ro, lucian_horeca, romania_emails |
| Norway | 5,637 | 3,665 | norway_emails, companies |
| Bulgaria | 819 | 780 | bg_business_catalog |
| Denmark | 355 | 198 | dk_contacts, denmark_emails |
| Moldova | 130 | - | companies |
| France | 61 | - | companies |
| Others | 522 | - | agencies, companies |
| **TOTAL** | **27,820** | **9,600+** | |

## Data Sources Used

| Source | Database | Records | Emails |
|--------|----------|---------|--------|
| horeca_ro | food_distribution | 18,301 | 18,284 |
| lucian_horeca | norway_emails | 16,261 | 16,261 |
| norway_emails (NACE 55-56) | norway_emails | 4,360 | 4,360 |
| romania_emails (CAEN 55-56) | romania_emails | 2,737 | 2,737 |
| bg_business_catalog | interjob_master | 1,177 | 1,127 |
| bg_horeca_campaign | interjob_master | 516 | 516 |
| dk_contacts | interjob_master | 219 | 219 |
| denmark_emails | denmark_emails | 208 | 208 |
| companies table | interjob_master | 7,868 | ~2,000 |
| agencies | interjob_master | 155 | 155 |
| insolvency (liquidators) | interjob_master | 63 | 63 |

## Bulk Data (Needs Enrichment)

| Country | HORECA Records | With Email | Source |
|---------|----------------|------------|--------|
| France | 1,389,000 | 0 | fr_companies (NAF codes) |
| UK | 750,067 | ~100 | companies table |
| Ireland | 188,643 | 0 | companies table |
| Germany | 99,459 | ~20 | companies, de_companies |
| Others | ~100,000 | ~500 | companies table |
| **TOTAL** | **~2,500,000** | **~600** | |

## France HORECA by NAF Code

| NAF | Category | Count |
|-----|----------|-------|
| 56.10 | Restaurants | 588,371 |
| 55.20 | Holiday accommodation | 144,381 |
| 55.3A | Camping sites | 143,308 |
| 56.30 | Bars/Pubs | 104,714 |
| 55.10 | Hotels | 65,391 |
| 56.21 | Event catering | 62,564 |
| Others | Various | ~280,000 |

## Market Intelligence

| Data | Count | Source |
|------|-------|--------|
| Bankrupt HORECA (Romania) | 10,980 | insolvency table |
| Supermarkets (suppliers) | 15,133 | food_distribution |
| SEAP food winners | 30 | food_distribution |

## Query Examples

```sql
-- Connect to database
psql -U tudor -d horeca

-- All contacts
SELECT * FROM contacts LIMIT 10;

-- By country
SELECT * FROM contacts WHERE country = 'Norway';

-- With phone
SELECT * FROM contacts WHERE phone IS NOT NULL AND phone != '';

-- Export specific country
\copy (SELECT * FROM contacts WHERE country = 'Romania') TO 'romania_horeca.csv' CSV HEADER
```

## Enrichment Scripts

Location: `/opt/ACTIVE/SCRAPERS/ENRICHMENT/`

| Script | API | Cost | Data |
|--------|-----|------|------|
| insee_enricher.py | INSEE SIRENE | FREE | France addresses |
| pappers_enricher.py | Pappers.fr | 100 free | France phone/email |
| google_places_enricher.py | Google Places | $200/mo free | All countries |

### Setup

```bash
# INSEE (France - FREE)
python3 insee_enricher.py --setup

# Pappers (France - 100 free credits)
python3 pappers_enricher.py --setup

# Google Places (All countries)
python3 google_places_enricher.py --setup
```

## Files

| File | Size | Content |
|------|------|---------|
| HORECA_28K_UNIQUE_EMAILS.csv | 2.6 MB | 27,820 unique emails |
| HORECA_ENRICHMENT_STRATEGIES.md | - | Enrichment plan |
| EEATINGH_EUROPEAN_HORECA_DATA.md | - | Initial inventory |

## Use Cases

1. **eeatingh.ro** - Food delivery platform expansion
2. **Email campaigns** - B2B outreach to restaurants/hotels
3. **Market research** - HORECA industry analysis
4. **Lead generation** - Hospitality sector contacts
