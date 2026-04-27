# VAMALI — Direcția Generală a Vămilor (Authorized Customs Operators)

VAMALI = General Directorate of Customs (Ministry of Finance).
Data: companies authorized as AEO (Authorized Economic Operators) and customs brokers/agents.

## What We Have (Public Lists)

| Registry | URL | Estimated Volume | Type |
|----------|-----|------------------|------|
| Operatori Economici Autorizati (AEO) | https://www.customs.ro/e-customs/aeo/lista-operatorilor-economici-autorizati | ~800-1000 | Web table, searchable |
| Agenti Vamali (Customs Brokers) | ANAF website or Customs subsite | TBD | May require API/scraping |
| Certificate Digitale (Digital Certificates) | idem | TBD | Legal rep auth |

Source: https://www.customs.ro/ (E-Customs section, AEO subsection)

## Data Structure per Company

**AEO (Authorized Economic Operators):**
- `company_name` — legal entity name
- `cui` — fiscal code (Romanian tax ID)
- `adresa` — company address
- `localitate` — city
- `judet` — county
- `tip_autorizatie` — authorization type (AEO-C, AEO-S, AEO-F)
  - AEO-C: Customs simplification
  - AEO-S: Security & safety
  - AEO-F: Full (both)
- `nr_autorizatie` — authorization number
- `data_acordare` — date authorized
- `data_expirare` — expiry date
- `stare` — status (Activ, Suspendat, Anulat)
- `email` — contact email (if available on page)
- `telefon` — contact phone (if available on page)

**Customs Brokers:**
- `agent_name` — individual or company name
- `cui` — fiscal code (if company)
- `nr_licenta` — broker license number
- `specialitati` — specializations (import/export/etc.)

## CSS/Web Scraping Strategy

1. **Main list:** https://www.customs.ro/e-customs/aeo/lista-operatorilor-economici-autorizati
   - Page structure: Likely table or modal-based list (paginable)
   - Parser: BeautifulSoup for table rows → extract name, CUI, status

2. **Detail page (per company):** Click company link → extract full address, phone, email
   - If available in modal: parse from JavaScript data
   - If separate page: follow link and scrape

3. **Post-scrape enrichment:** CUI → ONRC (D:\DATABASES\companies.db) to get email/phone if not on Customs page

## Output Target

```
DATA/
  vamali_aeo_combined.csv       — name, CUI, judet, tip_autorizatie, stare
  vamali_enriched.csv           — + email, telefon, adresa din ONRC
```

## Usage

```bash
cd D:\MEMORY\BUSINESS\IDEAS\ISCIR\VAMALI
python CODE/scrape_vamali.py
# Output: DATA/vamali_aeo_combined.csv
```

## Dependencies

```
pip install requests beautifulsoup4 lxml
```

## Campaign Potential

~800 AEO-authorized companies = B2B logistics/import-export SMEs:
- Job postings (customs brokers, logistics, compliance officers)
- Customs software/compliance tools (tariff codes, e-customs support)
- EU grants for logistics (Component 6 PNRR digitalization)
- Legal services (import/export compliance, tariff appeals)
- Freight forwarding services
- Insurance brokers specialized in cargo

## Business Angles

### 1. Lead Gen (QUICK WIN)
- 800 active AEOs = customs-reliant importers/exporters
- Many need compliance training, tariff management software
- Cold outreach: compliance consulting, tariff classification advisory

### 2. Customs Automation Services
- EU e-customs systems (NCTS6, ICS2, AES) rollout → implementation needs
- Custom software to auto-populate e-customs forms
- API-driven compliance checking

### 3. Broker Directory
- Database of licensed customs brokers for re-sale to international logistics companies
- Price: €100-300 one-time

### 4. Compliance Monitoring
- AEO status changes (suspensions, expirations) = early warning
- Notify subscribers of risk events
- Subscription: €50/month

## Files

```
VAMALI/
├── CLAUDE.md
├── CODE/
│   └── scrape_vamali.py
└── DATA/
    ├── vamali_aeo_combined.csv    (extracted output)
    └── vamali_enriched.csv        (with email/phone from ONRC)
```

## Update Cadence

Customs Directorate updates AEO list continuously (new authorizations, suspensions).
Re-scrape weekly. Compare with previous version → delta = new contacts + status changes.

## Known Issues

- Some AEOs may not have email/phone on customs.ro → fallback to ONRC lookup by CUI
- SSL/TLS issues on customs.ro reported historically → use requests with verify=False if needed
- List may be paginable or JavaScript-rendered → use Selenium if BeautifulSoup fails
