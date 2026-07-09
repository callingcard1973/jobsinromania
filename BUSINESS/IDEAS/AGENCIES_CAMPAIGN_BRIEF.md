# Agencies Campaign Brief

## Template
File: /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/agencies/template1.txt
Status: DRAFT, awaiting Tudor approval

## Data Source: 18,133 unique recruitment agency emails

### agencies table (interjob_master) — 16,824 unique emails
- **EURES scrape** (14,266 rows): scraped from EURES website, mixed quality — some are employers not agencies, includes JS artifacts as "emails"
- **KRAZ Poland** (~100K rows from 20 daily snapshots, 4,167 unique emails): official Polish government recruitment agency registry. High quality, confirmed agencies.
- **Bulgarian agencies** (2,627 rows, 208 with email): official Bulgarian ЧТП/ПОВР registry. High quality.
- **No-source entries** (29K rows, remainder): origin unclear

### bg_agencies table — 330 extra emails (not in agencies table)
- Separate Bulgarian agencies table with richer schema (type, reg_number, office_address, representative)
- Official government data, high quality

### no_companies_full NACE 78 — 979 extra emails
- Norwegian Brønnøysund register, NACE code 78 = Employment activities
- 4,760 companies total, 1,143 with email, 979 not already in agencies table
- Official government data, high quality

## Country Breakdown
| Country | Emails | Source |
|---------|--------|--------|
| RO | 4,928 | EURES |
| OT (Other) | 3,898 | EURES mixed |
| UNK | 2,558 | No country code |
| PL | 2,140 | KRAZ + EURES |
| NO | 1,692 | Brønnøysund + EURES |
| DE | 1,652 | EURES (10% garbage) |
| SE | 574 | EURES |
| BG | 330 | Official registry |
| FI | 215 | EURES |
| DK | 60 | EURES |
| Other EU | 86 | EURES |

## Campaign Config
- CSV: /opt/ACTIVE/EMAIL/CAMPAIGNS/DATA/recruitment_agencies_campaign.csv
- Config: /opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/recruitment_agencies.json
- Senders: Mailrelay 300/day + Brevo 200/day = 500/day
- Duration: ~36 days to complete
- Expected response rate: 2-5% = 360-900 replies
