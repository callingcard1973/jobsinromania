# SITUR — Sistema Informațională Turismului (Tourism Registry)

SITUR = Ministry of Economy, Tourism Authority. Public registry of accredited tourism operators in Romania.
Data: hotels, guesthouses, travel agencies, tour guides, information centers, mountain resorts.

## What We Have (XLSX Files)

| File | Companies | Description |
|------|-----------|-------------|
| listaAgentii.xlsx | ~1,000 | Travel agencies, tour operators — legal entities |
| listaCazari.xlsx | ~8,000+ | Hotels, guesthouses, bed & breakfast accommodations |
| listaGhizi.xlsx | ~1,500 | Accredited tour guides (ATESTAT) |
| listaStatiuni.xlsx | ~50 | Mountain/seaside resorts and official resort status |
| listaCentreInformare.xlsx | ~100 | Tourist information centers by county |

Source: https://www.turism.gov.ro/ → Download links in public section

## Data Structure per Record

**Travel Agencies (listaAgentii):**
- `company_name` — legal entity name
- `cui` — fiscal code
- `adresa` — full address
- `localitate` — city
- `judet` — county
- `tip` — type (agentie_turism)
- `email` — contact email
- `phone` — contact phone (in extra field)
- `operator` — company operator name

**Accommodations (listaCazari):**
- `company_name` — hotel/guesthouse name
- `cui` — fiscal code
- `tip_unitate` — accommodation type (hotel, pension, motel, etc.)
- `categorie` — star rating or classification
- `adresa` — address
- `localitate` — city
- `judet` — county
- `email` — contact email
- `operator` — operator name

**Tour Guides, Resorts, Info Centers:**
- Stored as `extra` JSONB with minimal contact fields (most have no email)

## CSV Output

All records → `DATA/situr_combined.csv` with columns:
- `source_file` — which XLSX file (listaAgentii, listaCazari, etc.)
- `company_name`
- `cui`
- `adresa`
- `localitate`
- `judet`
- `tip` — type code
- `email`
- `extra_json` — phone, operator, rating, etc. as JSON

## Usage

```bash
cd D:\MEMORY\BUSINESS\IDEAS\ISCIR\SITUR
python CODE/scrape_situr.py
# Output: DATA/situr_combined.csv
```

## Dependencies

```
pip install openpyxl
```

## Campaign Potential

~10,000+ tourism businesses with email addresses = B2B outreach targets:
- Job postings (hotel staff, guides, customer service)
- Tourism software (booking systems, property management)
- EU grants (Component 11 PNRR tourism digitalization)
- Training programs (hospitality, guide certifications)
- Insurance, accounting, legal services for tourism sector

## Files

```
SITUR/
├── CLAUDE.md
├── CODE/
│   └── scrape_situr.py
└── DATA/
    ├── listaAgentii.xlsx       (cached, re-download if >30 days old)
    ├── listaCazari.xlsx
    ├── listaGhizi.xlsx
    ├── listaStatiuni.xlsx
    ├── listaCentreInformare.xlsx
    └── situr_combined.csv      (extracted output)
```

## Update Cadence

SITUR updates files monthly. Re-run scraper monthly.
Check Last-Modified header on turism.gov.ro before re-downloading.
