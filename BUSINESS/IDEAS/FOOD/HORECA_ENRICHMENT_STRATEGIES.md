# HORECA Data Enrichment Strategies

## Target: 700K+ European restaurants/hotels without contact info

| Country | Records | Priority |
|---------|---------|----------|
| UK | 446,458 | High (English, rich APIs) |
| France | 160,440 | High (large market) |
| Ireland | 99,722 | Medium (English) |
| Germany | 40,912 | High (strong economy) |
| Czech | 2,331 | Low |
| Others | ~25,000 | Low |

---

## STRATEGY 1: Free Government APIs

### UK - Companies House API
- **URL**: https://developer.company-information.service.gov.uk/
- **Data**: Registered office, officers, filing history
- **Cost**: FREE (1,000 requests/5 min)
- **Match**: Company name + registration number
- **Expected yield**: 60-70% address match

### France - INSEE SIRENE API
- **URL**: https://api.insee.fr/catalogue/
- **Data**: SIRET, address, activity code (NAF)
- **Cost**: FREE (registration required)
- **Match**: SIREN number from fr_companies
- **Expected yield**: 90%+ (official registry)

### Germany - Handelsregister
- **URL**: https://www.handelsregister.de/
- **Data**: Company registry, address
- **Cost**: EUR 4.50/extract (bulk discounts)
- **Match**: Company name + city

### Ireland - CRO
- **URL**: https://core.cro.ie/
- **Data**: Company details, directors
- **Cost**: EUR 2.50/company
- **Match**: Company number

---

## STRATEGY 2: Google Places API

**Best for restaurants** - most have Google Business profiles

```python
# Cost: $17 per 1,000 requests (Place Details)
# Fields: phone, website, email (from website), hours

import googlemaps
gmaps = googlemaps.Client(key='API_KEY')

result = gmaps.find_place(
    input="Restaurant Name, City, Country",
    input_type="textquery",
    fields=["formatted_phone_number", "website", "name"]
)
```

**Estimated costs:**
- 700K records x $0.017 = **$11,900**
- Expected yield: 50-60% with phone/website

**Optimization:**
- Filter to high-value countries first (UK, DE, FR)
- Skip records that already have partial data
- Cache results to avoid duplicate lookups

---

## STRATEGY 3: Web Scraping (FREE but slow)

### Restaurant Directories
| Directory | Countries | Data | Difficulty |
|-----------|-----------|------|------------|
| TripAdvisor | All | Phone, website, address | Medium |
| TheFork | EU | Phone, email, website | Medium |
| Yelp | UK, DE, FR | Phone, website | Hard (anti-bot) |
| OpenTable | UK, US | Phone, email | Medium |
| JustEat/Lieferando | UK, DE | Phone | Easy |

### Hotel Directories
| Directory | Countries | Data |
|-----------|-----------|------|
| Booking.com | All | Phone, email, website |
| Hotels.com | All | Phone |
| Expedia | All | Phone |
| HRS | DE, AT, CH | Phone, email |

**Implementation:**
```python
# Use existing scraper infrastructure
# /opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/

from skills_common import fetch_url, get_http_client
import time

def scrape_tripadvisor(name, city, country):
    # Search + extract contact
    # Rate limit: 1 req/3 sec to avoid blocks
    pass
```

**Estimated time:** 700K / (20/min) = 583 hours = 24 days continuous

---

## STRATEGY 4: Email Pattern Discovery

Most restaurants use predictable email patterns:
- info@domain.com (60%)
- contact@domain.com (15%)
- restaurant@domain.com (10%)
- hello@domain.com (5%)

**Process:**
1. Extract domain from company name or web search
2. Generate candidate emails
3. Verify with email validation API

```python
# Email verification: $0.001-0.005 per email
# Zerobounce, Hunter.io, NeverBounce

patterns = [
    f"info@{domain}",
    f"contact@{domain}",
    f"hello@{domain}",
    f"reservations@{domain}",
    f"booking@{domain}"
]
```

**Cost estimate:** 700K x 5 patterns x $0.002 = **$7,000**
**Expected yield:** 30-40% valid emails

---

## STRATEGY 5: Social Media Extraction

### Facebook Pages
- Search: "{restaurant name} {city}"
- Extract: Phone, email, website from "About"
- Tool: Facebook Graph API or scraping
- Yield: 40-50% of restaurants have pages

### Instagram
- Bio often contains email/phone
- Link in bio to website
- Tool: Instagram scraping (against ToS)

### LinkedIn Company Pages
- Premium data source
- Tool: LinkedIn Sales Navigator API
- Cost: $99/mo + per-search fees

---

## STRATEGY 6: Bulk Data Purchase

### Commercial Providers
| Provider | Coverage | Cost | Quality |
|----------|----------|------|---------|
| Dun & Bradstreet | Global | $0.10-0.50/record | High |
| ZoomInfo | US/EU | $0.05-0.20/record | High |
| Lusha | EU | $0.03-0.10/record | Medium |
| Apollo.io | Global | $0.02-0.05/record | Medium |
| Hunter.io | EU | $0.01-0.03/email | Medium |

**Bulk deal estimate:**
- 100K records x $0.05 = **$5,000**
- Quality: 70-80% accuracy

---

## STRATEGY 7: Crowdsourced/Exchange

### Data Exchange
- Trade Romania data (22K enriched) for UK/FR data
- Partner with food delivery platforms for data share
- B2B data co-ops

### Crowdsourced
- Mechanical Turk: $0.02-0.05 per lookup
- 700K x $0.03 = **$21,000** (expensive but accurate)

---

## RECOMMENDED APPROACH

### Phase 1: Free/Low-Cost (Week 1-2)
1. **INSEE API for France** - 160K records, FREE
2. **Companies House for UK** - 446K records, FREE
3. **Google Places for Germany** - 40K x $0.017 = $680

**Investment:** ~$700
**Expected yield:** 300K+ with addresses

### Phase 2: Email Discovery (Week 3-4)
1. Web search for domains (free, slow)
2. Email pattern generation
3. Email verification

**Investment:** ~$3,000
**Expected yield:** 100K+ with emails

### Phase 3: Scraping (Ongoing)
1. TripAdvisor scraper
2. TheFork scraper
3. Booking.com scraper

**Investment:** Time only (existing infrastructure)
**Expected yield:** 50K+ with phone/email

### Phase 4: Purchase Gap Fill (If needed)
1. Buy remaining high-value records from Apollo/Hunter
2. Focus on Germany, UK premium segments

**Investment:** ~$2,000
**Expected yield:** 30K+ verified

---

## TOTAL INVESTMENT ESTIMATE

| Phase | Cost | Records Enriched | Cost/Record |
|-------|------|------------------|-------------|
| Free APIs | $0 | 300,000 | $0.00 |
| Google Places | $700 | 25,000 | $0.028 |
| Email Discovery | $3,000 | 100,000 | $0.03 |
| Scraping | $0 (time) | 50,000 | $0.00 |
| Data Purchase | $2,000 | 30,000 | $0.067 |
| **TOTAL** | **$5,700** | **505,000** | **$0.011** |

---

## QUICK WINS (Start Today)

1. **France INSEE** - Register API, query 160K SIREN numbers
2. **UK Companies House** - Register API, batch query
3. **Google My Business** - Search top 10K German restaurants
4. **Domain extraction** - Parse company names for website patterns

---

## SCRIPTS TO BUILD

```
/opt/ACTIVE/SCRAPERS/ENRICHMENT/
├── insee_enricher.py      # France SIRENE API
├── companies_house.py     # UK Companies House
├── google_places.py       # Google Places API
├── email_pattern.py       # Email discovery
├── tripadvisor_scraper.py # TripAdvisor contacts
└── bulk_enricher.py       # Orchestrator
```

---
Created: 2026-03-20
