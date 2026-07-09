# Research: POLONIA KRAZ (IDEA-010)
Date: 2026-04-16

## Description
Download CSV of ~9,175 Polish recruitment agencies from KRAZ (Krajowy Rejestr Agencji Zatrudnienia), the government-mandated registry. Use for partnership outreach or data enrichment (feeds into IDEA-004 agency database).

## Market Size & Demand
- Poland is the #1 staffing market in Central/Eastern Europe
- KRAZ is mandatory: every legal recruitment agency in Poland must register
- Registry at stor.praca.gov.pl is publicly accessible, browsable online
- Polish agencies recruit heavily from Ukraine, Nepal, India, Philippines -- and Romania
- New law effective June 2025 updated registration requirements (1000 PLN fee)

## Competitors Found

| Competitor | Type | Data Access | Notes |
|---|---|---|---|
| stor.praca.gov.pl/kraz | Official registry | Free, web browsable | No bulk CSV download button |
| eurokadra.com | Polish staffing agency | Uses KRAZ for verification | Explains KRAZ to workers |
| Transparent Data (medium.com) | Polish company data API | API access to KRS/REGON | Not KRAZ-specific |
| Savesta Consulting | KRS data extraction guide | Manual download guides | General company data |
| TargetPoland | Recruitment agency | No data product | Uses KRAZ internally |

## Our Advantage
- Scraping KRAZ is trivial (public data, no auth, standard HTML/API)
- 9,175 agencies = massive partnership database for cross-border placements
- Can enrich with emails/phones via pattern matching + web scraping
- Feeds directly into existing agency database (IDEA-004: 18K agencies)
- Polish agencies are natural partners: they need RO/UA workers, we supply them

## Market Validated?
YES for the use case (partnership outreach to Polish agencies). The data itself is free/public -- the value is in having it structured and enriched for outreach. No one sells a "KRAZ database" because it's public, but no one has it in a clean enriched CSV either.

## Price Point
- Internal use: partnership with even 1 Polish agency = 10-50 worker placements/year
- At 500-1000 EUR per placement fee: 5,000-50,000 EUR per active partnership
- If resold as data product: 50-200 EUR per enriched CSV (low margin, not recommended)
- Best ROI: use for outreach campaigns, not data sales

## Risk
- VERY LOW: 0.5 hours to scrape, public data, no legal issues
- Scraping may need pagination handling on stor.praca.gov.pl
- Data quality: some agencies may be inactive/dissolved (KRAZ includes historical entries)

## Recommendation
**LAUNCH** -- 30 minutes of work, zero cost, feeds into the agency partnership pipeline. Scrape KRAZ, clean the data, enrich with emails, add to IDEA-004 master agency database. Then run an outreach campaign offering Romanian workers to Polish agencies.

## Sources
- [KRAZ official portal](https://stor.praca.gov.pl/portal/kraz)
- [KRAZ browse page](https://stor.praca.gov.pl/portal/kraz/kraz-przeglad)
- [Poland employment agency certificate (gov.pl)](https://www.gov.pl/web/your-europe/acquiring-employment-agency-certificate)
- [Eurokadra - what is KRAZ](https://www.eurokadra.com/en/advices/national-register-of-employment-agencies/)
- [Polish companies API (Transparent Data)](https://medium.com/transparent-data-eng/polish-companies-api-meet-business-registers-of-poland-a75c2f223b34)
