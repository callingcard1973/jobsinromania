# Mercosur Trade Data Sources

## LOCAL DATA (Already Downloaded)

Location: `/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_*/`

| Sector | Suppliers | Buyers | Records |
|--------|-----------|--------|---------|
| Lithium | 24 companies (AR, CL, BO) | - | lithium_suppliers.json |
| Niobium | 8 companies (BR) | 12 EU buyers | niobium_suppliers.json |
| Honey | 20 companies (AR, UY, BR, CL) | 15 EU buyers | honey_exporters.json |
| Beef | 22 companies (BR, AR, UY, PY) | - | beef_exporters.json |

### Data Quality
- All have: name, country, city, sector, website
- Missing: email, phone (need enrichment)
- Enriched files have headers but empty contact columns

---

## OPEN DATA APIs (Free)

### 1. UN Comtrade API
- **URL:** https://comtrade.un.org/
- **Access:** Free tier (rate limited)
- **Data:** Trade flows by HS code, country, year
- **Format:** JSON/CSV
- **Python:** `pip install comtradeapicall`
- **Note:** Aggregate data, NOT company-level

### 2. Brazil ComexStat API
- **URL:** https://comexstat.mdic.gov.br/
- **API Docs:** https://api-comexstat.mdic.gov.br/docs
- **Postman:** https://www.postman.com/jorgeguto/comexstat/
- **Access:** Free, no auth required
- **Data:** Brazilian exports/imports by NCM code
- **Format:** JSON
- **Note:** Aggregate data, company names in bulk only

### 3. Argentina INDEC / AFIP
- **URL:** INDEC statistics portal
- **Data:** Trade statistics
- **Note:** No public company-level API

### 4. World Bank WITS
- **URL:** https://wits.worldbank.org/
- **Access:** Free
- **Data:** Tariffs, trade flows, NTMs
- **Format:** CSV download

### 5. EU TED API (for EU Buyers)
- **URL:** https://api.ted.europa.eu/
- **Docs:** https://docs.ted.europa.eu/api/latest/
- **Data:** 1.57M contract winners (375K emails)
- **Note:** Already have this in interjob_master.ted_winners

---

## COMMERCIAL DATA SOURCES

| Source | Coverage | Price | API |
|--------|----------|-------|-----|
| Volza | 228 countries, company-level | Paid | Yes |
| ImportGenius | Customs data | Paid | Yes |
| TradeAtlas | 20M+ companies | Paid | REST API |
| Tendata | 91 countries customs | Paid | Yes |
| Seair | South America focus | Paid | Yes |

---

## SCRAPING TARGETS (Free)

### B2Brazil.com
- **Records:** ~15,000 companies
- **Data:** Company name, sector, limited contact
- **Rate limit:** Moderate
- **Emails:** Hidden (requires platform contact)

### ConnectAmericas
- **Records:** 20,000+ Brazilian exporters
- **Data:** Name, HS code, state, volume tier
- **Search:** By keyword, HS code, state
- **Emails:** Not public

### APEX Brasil
- **Access:** Supplier list request
- **Data:** Pre-qualified exporters
- **Method:** Form submission, 10 business days

### Trade Shows (Exhibitor Lists)
- APAS (Supermarket expo)
- Fispal (Food expo)
- Expoalimentaria (Latin America food)
- **Method:** Web scrape or purchase lists

---

## ENRICHMENT STRATEGY

### For Mercosur Suppliers
1. Use existing JSON files from /mnt/hdd/GLOBAL_DOWNLOADS/
2. Crawl company websites for contact pages
3. Use MX record + email guessing (info@, contact@)
4. Reverse domain lookup in TED winners

### For EU Buyers
1. TED winners database (have 375K emails)
2. Filter by HS code / CPV code
3. Match sector to supplier sector

---

## PRIORITY ACTIONS

### Immediate (Use Existing Data)
```bash
# Copy to project
cp -r /mnt/hdd/GLOBAL_DOWNLOADS/mercosur_* /opt/ACTIVE/IDEAS/MERCOSUR/OPENCODE/data/

# Enrich with website crawling
python3 scrapers/mercosur/website_enricher.py data/mercosur_lithium/lithium_suppliers.json
```

### Week 1
1. Build website_enricher.py (crawl /contact pages)
2. Build ted_matcher.py (match suppliers to TED buyers by sector)
3. Export matched pairs to CSV for campaign

### Week 2
1. ComexStat API integration (for volume validation)
2. UN Comtrade API (for market sizing)
3. ConnectAmericas scraper (expand supplier list)

---

## API CODE EXAMPLES

### UN Comtrade (Python)
```python
from comtradeapicall import getFinalData

# Get Brazil lithium exports to EU
data = getFinalData(
    reporterCode='076',  # Brazil
    partnerCode='97',    # EU
    period='2024',
    cmdCode='283691',    # Lithium carbonate
    flowCode='X'         # Exports
)
```

### ComexStat (Python)
```python
import requests

url = "https://api-comexstat.mdic.gov.br/general"
params = {
    'year': 2024,
    'type': 'exp',
    'ncm': '28369100'  # Lithium carbonate
}
resp = requests.get(url, params=params, verify=False)
data = resp.json()
```

### TED API (Match EU Buyers)
```python
import psycopg2

conn = psycopg2.connect(database='interjob_master', user='tudor')
cur = conn.cursor()

# Find steel companies (niobium buyers)
cur.execute('''
    SELECT company_name, email, country
    FROM ted_winners
    WHERE cpv_codes LIKE '%14%'  -- Steel related
    AND email IS NOT NULL
    LIMIT 1000
''')
buyers = cur.fetchall()
```
