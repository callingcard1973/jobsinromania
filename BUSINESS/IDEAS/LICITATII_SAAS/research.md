# Research: LICITATII SAAS (IDEA-015)
Date: 2026-04-16

## Description
SaaS platform for searching and alerting on 5.1M EU tenders. Users set filters (CPV codes, countries, keywords), receive daily email/Telegram alerts for matching tenders.

## Market Size & Demand
- TED publishes 815B EUR in contracts annually, 3,000+ notices/day
- Romania alone: 16.2B EUR via SEAP (50K+ contracting authorities)
- Proven paying market: multiple SaaS competitors exist and charge 50-1800 EUR/year
- Every company bidding on public contracts needs tender monitoring
- EU has ~250,000 contracting authorities across 27 member states

## Competitors Found

| Competitor | Pricing | Coverage | Notes |
|---|---|---|---|
| Euro-Bidwatch | ~2 GBP/day (~730 GBP/year) | EU (TED) + UK | 30-day free trial, daily email alerts |
| TENDERTRACK (tenders.eu) | <5 EUR/day (~1,800 EUR/year), trial 395 EUR/2mo | EU (TED) | CPV-based search, document purchase 9.95 EUR each |
| tenders.com | 1,295 EUR/year | EU (TED) | Basic alert service |
| TenderAlerts.eu | Unknown (likely freemium) | TED + national portals | Save searches, daily alerts, real-time tracking |
| licitatia.ro | Subscription (undisclosed) | Romania (SEAP) | Mobile app, Romanian market only |
| licitatii.app | Subscription (undisclosed) | Romania (SEAP) | Market analysis, winning strategies |
| Stotles | Enterprise pricing | UK + EU | AI-powered, buyer intelligence |
| Jorpex | Unknown | TED | Automatic monitoring |
| TendersOnTime | Subscription | Global (30K/day) | Multi-country |
| tendersinfo.com | Subscription | Global | Includes Romania |

## Our Advantage
- Already have 5.1M tenders in PostgreSQL (TED data scraped)
- Own email infrastructure (2,560/day capacity)
- Telegram bot capability (existing infrastructure)
- Can undercut competitors: they charge 1,000-1,800 EUR/year, we could offer 99-499 EUR/year
- Romanian market underserved: licitatia.ro and licitatii.app are basic, no one does TED+SEAP combined well
- Can add AI features cheaply (own LLM infrastructure for tender summarization)

## Market Validated?
YES. Multiple competitors charging 730-1,800 EUR/year proves demand. Euro-Bidwatch, TENDERTRACK, and tenders.com have been operating for years. The Romanian niche (SEAP+TED combined) is underserved.

## Price Point
- Starter: 29-49 EUR/month (3 saved searches, daily email)
- Professional: 99 EUR/month (unlimited searches, Telegram alerts, AI summaries)
- Enterprise: 299-499 EUR/month (API access, team features, document download)
- Break-even: ~50 paying customers at 99 EUR/month = 5,000 EUR/month
- Realistic year 1: 20-50 customers = 2,000-5,000 EUR/month

## Risk
- HIGH effort: 80 hours to build MVP (web UI, payment, user management)
- MEDIUM competition: established players with years of head start
- MEDIUM churn: if alerts aren't accurate, users cancel fast
- Need to keep TED data fresh (daily scraping required)
- Support burden: enterprise customers expect phone support

## Recommendation
**PARK** -- Market is validated and lucrative, but 80 hours of dev effort is significant. The competitors are established and well-funded. Better to first extract value from the data via campaigns (IDEA-009) and Telegram channels (IDEA-008) before building a full SaaS. Revisit after IDEA-008 proves Telegram tender alerts have demand.

## Sources
- [Euro-Bidwatch pricing](https://www.euro-bidwatch.com/pricing)
- [TENDERTRACK](https://www.tenders.eu/)
- [tenders.com](https://www.tenders.com/)
- [TenderAlerts.eu](https://tenderalerts.eu/)
- [TED eSenders list](https://ted.europa.eu/en/simap/list-of-ted-esenders)
- [Tender management software Europe (SourceForge)](https://sourceforge.net/software/tender-management/europe/)
- [Apify EU Tender Data](https://apify.com/digital_troubadour/eu-tender-data)
