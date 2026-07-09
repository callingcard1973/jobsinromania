# Trade Agreement Arbitrage - Synthesis & Action Plan

## Executive Summary

Tudor has a unique position: Canadian citizen in Romania with 1.57M EU buyer database (TED winners). Best model: broker/matchmaker connecting suppliers with EU buyers for 3-5% commission. No warehousing, no inventory - pure information arbitrage.

---

## OPPORTUNITY RANKING (By Fit with Existing Infrastructure)

### TIER 1: HIGH FIT (Launch in 30 days)

| # | Opportunity | Fit Score | Why |
|---|------------|-----------|-----|
| 1 | **Mercosur Supplier -> EU Buyer Matching** | 95% | Already have 375K EU buyer emails. Just need supplier side. |
| 2 | **Critical Minerals Brokerage (Lithium/Niobium)** | 90% | High-value deals. Brazil controls 90% of niobium. EU desperate for supply. |
| 3 | **Romanian Wine/Spirits to Mercosur** | 85% | 15 Romanian GIs protected. Existing Romania contacts. |

### TIER 2: MEDIUM FIT (Launch in 60 days)

| # | Opportunity | Fit Score | Why |
|---|------------|-----------|-----|
| 4 | **Canada-EU (CETA) Matchmaking** | 75% | Tudor is Canadian. Can register company. Needs Canadian supplier database. |
| 5 | **Honey Import Cooperative** | 70% | Brazil/Argentina are top 5 exporters. 45K tonnes quota. Lower value per deal. |
| 6 | **IT Services Export (Romania -> Mercosur)** | 65% | Romania strong IT sector. Needs different approach than goods. |

### TIER 3: LOWER FIT (Consider after 6 months)

| # | Opportunity | Fit Score | Why |
|---|------------|-----------|-----|
| 7 | **CPTPP-EU Triple Arbitrage** | 50% | Complex rules of origin. Needs Canadian physical presence. |
| 8 | **Beef Import** | 40% | EUDR compliance critical. Only 1,220 farms EU-certified. High risk. |
| 9 | **Physical Trading Company** | 30% | Capital intensive. Not Tudor's strength. |

---

## DATA SOURCES TO SCRAPE/ACQUIRE

### Priority 1: Mercosur Suppliers (Week 1-2)

| Source | URL | Est. Records | Method |
|--------|-----|--------------|--------|
| ConnectAmericas Catalog | connectamericas.com | 20,000 | Search API + scrape |
| Brazilian Exporters Directory | investexportbrasil.gov.br | 10,000 | Bulk access request |
| APEX Brasil Portal | apexbrasil.com.br | 12,000 | Supplier list request |
| Brazil B2B Directory | b2brazil.com | 15,000 | Scrape listings |
| ABEMEL (honey) | abemel.com.br | 500+ | Industry contact |
| CECIEx Catalog | PDF | 2,000+ | PDF extraction |

### Priority 2: Critical Minerals (Week 2-3)

| Source | Company | Contact Method |
|--------|---------|----------------|
| CBMM (niobium) | cbmm.com | Direct B2B contact |
| Sigma Lithium | sigmalithiumcorp.com | Investor relations |
| AMG Brasil | amg-nv.com | Sales department |
| Mining SEE database | miningsee.eu | Scrape |

### Priority 3: EU Buyers (Already Have)

| Source | Records | Status |
|--------|---------|--------|
| TED Winners | 1.57M (375K emails) | HAVE |
| Companies DB | 500K | HAVE |
| EURES contacts | 50K | HAVE |

### Priority 4: Canadian Suppliers (Week 4-6)

| Source | URL | Access |
|--------|-----|--------|
| Trade Commissioner Service | tradecommissioner.gc.ca | Free registration |
| Canadian Importers Database | ised-isde.canada.ca | Public data |
| EDC Client Directory | edc.ca | Partnership request |

---

## RECOMMENDED BUSINESS STRUCTURE

### Option A: Romanian SRL (Recommended First)

```
Tudor Trade SRL (Romania)
- EU-based, leverage Mercosur deal immediately
- Lower setup costs (~EUR 200)
- Bank account in EUR
- Access to all EU FTAs
- Can invoice EU buyers directly
```

### Option B: Canadian Corporation (Phase 2)

```
Tudor Trade Inc. (Canada)
- For CETA/CPTPP opportunities
- Access to Canadian exporters
- Dual invoicing capability (CAD/EUR)
- Setup after proving EU model works
```

### Recommended: Start with Option A, add Option B after 6 months if revenue exceeds EUR 10K/month.

---

## REVENUE MODEL

### Commission Rates

| Deal Size | Commission | Per-Deal Revenue |
|-----------|------------|------------------|
| EUR 50K | 5% | EUR 2,500 |
| EUR 100K | 4% | EUR 4,000 |
| EUR 250K | 3.5% | EUR 8,750 |
| EUR 500K | 3% | EUR 15,000 |
| EUR 1M+ | 2.5% | EUR 25,000+ |

### Revenue Projections (Conservative)

| Month | Deals | Avg Size | Commission | Revenue |
|-------|-------|----------|------------|---------|
| 1-3 | 0 | - | - | EUR 0 (building) |
| 4-6 | 2 | EUR 50K | 5% | EUR 5,000 |
| 7-9 | 5 | EUR 75K | 4% | EUR 15,000 |
| 10-12 | 8 | EUR 100K | 3.5% | EUR 28,000 |
| **Year 1** | **15** | - | - | **EUR 48,000** |
| Year 2 | 40 | EUR 150K | 3% | EUR 180,000 |

---

## 90-DAY ACTION PLAN

### Week 1-2: Database Building

| Day | Action | Output |
|-----|--------|--------|
| 1-3 | Build apex_brasil_scraper.py | 12K exporter records |
| 4-5 | Build connectamericas_scraper.py | 20K exporter records |
| 6-7 | Build brazil_directory_scraper.py | 10K exporter records |
| 8-10 | Deduplicate, enrich with emails | Master supplier list |
| 11-14 | Match suppliers to TED buyers by sector | Opportunity matrix |

### Week 3-4: Sector Focus

| Sector | Suppliers | EU Buyers (TED) | Action |
|--------|-----------|-----------------|--------|
| Critical minerals | 50 | 500 battery/steel | Direct outreach |
| Honey | 200 | 2,000 food processors | Email campaign |
| Machinery | 1,000 | 5,000 manufacturers | Automated matching |

### Week 5-6: Outreach

| Action | Volume | Tool |
|--------|--------|------|
| Email EU buyers | 5,000 | Existing campaign system |
| Email Mercosur suppliers | 2,000 | New templates |
| LinkedIn outreach | 100 | Manual |
| Phone follow-up | 50 | Top prospects |

### Week 7-8: Refine & Close

| Action | Target |
|--------|--------|
| Qualify responses | 200 interested parties |
| Match 1:1 introductions | 50 introductions |
| Negotiate terms | 10 active negotiations |
| Close first deal | 1-2 deals |

### Week 9-12: Scale

| Action | Target |
|--------|--------|
| Expand database | 50K suppliers |
| Automate matching | Algorithm-based |
| Add Canada angle | Canadian supplier database |
| Build reputation | Case studies, testimonials |

---

## EMAIL CAMPAIGN STRATEGY

### Template 1: To EU Buyers (English)

```
Subject: Secure Mercosur supply chain before May 2026

Dear {company},

The EU-Mercosur agreement enters provisional application in May 2026.
91% of tariffs will be eliminated, saving EU importers EUR 4 billion annually.

We connect EU companies with verified Brazilian and Argentine suppliers in:
- Critical minerals (lithium, niobium)
- Agricultural products (honey, specialty foods)
- Industrial goods (machinery, components)

Would you like a shortlist of pre-qualified suppliers in your sector?

Best regards,
Tudor Trade
```

### Template 2: To Mercosur Suppliers (Portuguese/Spanish)

```
Subject: Exportar para a UE - Novo acordo comercial

Prezado {empresa},

O acordo UE-Mercosul entra em vigor em maio de 2026.
Temos compradores europeus qualificados buscando fornecedores brasileiros.

Setores prioritarios:
- Minerais criticos (litio, niobio)
- Mel e produtos agricolas
- Maquinas e equipamentos

Gostaria de receber uma lista de compradores interessados?

Atenciosamente,
Tudor Trade
```

---

## COMPLIANCE CHECKLIST

| Requirement | Status | Action |
|-------------|--------|--------|
| EUDR (deforestation) | Required 2026 | Only certified suppliers |
| Rules of Origin | Required | Documentation templates |
| Food safety (SIF) | Required for food | Verify EU certification |
| GDPR | Required | Privacy policy |
| LGPD (Brazil) | Required | Brazil privacy compliance |
| AML/KYC | Recommended | Basic due diligence process |

---

## RISK MITIGATION

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| CJEU delays full implementation | High | Medium | Focus on provisional application sectors |
| Supplier quality issues | Medium | High | Pre-qualification process |
| Commission disputes | Medium | Medium | Written agreements before introduction |
| Currency volatility | Medium | Low | EUR-denominated contracts |
| Competition from established brokers | Low | Medium | Niche focus, speed advantage |

---

## FIRST MOVE (This Week)

1. **Register domain:** mercosurtrade.eu or similar
2. **Build apex_brasil_scraper.py** - get first 12K exporters
3. **Filter TED winners** - identify 5,000 EU battery/steel/food buyers
4. **Draft email templates** - English and Portuguese
5. **Send 100 test emails** - validate approach

---

## KEY CONTACTS TO ACQUIRE

| Organization | Contact Type | Value |
|--------------|--------------|-------|
| APEX Brasil | Partnership | Official supplier lists |
| ABEMEL | Industry contact | Honey exporters |
| CBMM | Sales | Niobium supply |
| European Battery Alliance | Network | EU battery buyers |
| EUROBAT | Association | Battery manufacturer list |
| CNI Brazil | Trade data | Updated exporter catalog |

---

## SOURCES

### Mercosur Data
- [APEX Brasil Portal](https://apexbrasil.com.br/content/apexbrasil/br/en.html)
- [ConnectAmericas Brazilian Exporters Catalog](https://connectamericas.com/content/brazilian-exporters-catalog)
- [Brazilian Exporters Directory](https://globaledge.msu.edu/global-resources/resource/1255)
- [CBMM Niobium](https://cbmm.com/en)
- [Sigma Lithium](https://sigmalithiumcorp.com/)

### EU Battery/Minerals
- [European Battery Alliance Network](https://www.eba250.com/about-eba250/network/)
- [EUROBAT](https://www.eurobat.org/)
- [Top Battery Manufacturers Europe 2026](https://www.blackridgeresearch.com/blog/latest-list-of-largest-top-battery-manufacturers-manufacturing-companies-in-europe)

### Canada-EU (CETA)
- [CETA Official Portal](https://www.international.gc.ca/trade-commerce/trade-agreements-accords-commerciaux/agr-acc/ceta-aecg/index.aspx?lang=eng)
- [Trade Commissioner Service](https://www.tradecommissioner.gc.ca/en.html)
- [EDC CETA Opportunities](https://www.edc.ca/en/trade-matters/ceta-canada-eu-opportunities.html)

### Romania-Mercosur
- [EU-Mercosur Partnership Agreement: Romania Factsheet](https://policy.trade.ec.europa.eu/eu-trade-relationships-country-and-region/countries-and-regions/mercosur/eu-mercosur-agreement/factsheet-eu-mercosur-partnership-agreement-romania_en)

### EU Procurement
- [TED API Documentation](https://docs.ted.europa.eu/api/latest/index.html)
- [TED CSV Dataset](https://data.europa.eu/data/datasets/ted-csv)

### CPTPP
- [CPTPP Official Portal](https://www.international.gc.ca/trade-commerce/trade-agreements-accords-commerciaux/agr-acc/cptpp-ptpgp/index.aspx?lang=eng)
