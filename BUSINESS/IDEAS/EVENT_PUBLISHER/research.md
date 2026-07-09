# Research: EVENT PUBLISHER (IDEA-037)
Date: 2026-04-16

## Description
Auto-publicare multi-platforma (Telegram 6 canale + FB + LinkedIn). One-click scheduling and cross-posting for recruitment events across Telegram channels, Facebook pages, and LinkedIn.

## Market Size & Demand
- Global social media management market: ~USD 39-40 billion in 2026 (Fortune Business Insights, MarketsandMarkets)
- CAGR 22-25% through 2033
- Market is massive but dominated by incumbents; niche Telegram-focused tools are rare

## Competitors Found

| Competitor | Telegram Support | Price/mo | Notes |
|------------|-----------------|----------|-------|
| Buffer | No | $6/channel | Free for 3 channels. No Telegram. |
| Hootsuite | No | $99+/user | Enterprise-focused. No Telegram. |
| Sendible | No | $29+ (6 profiles) | Good multi-platform, no Telegram |
| Metricool | No | $25+ | Free plan available, no Telegram |
| PostEverywhere | No | $19 | 8 networks, no Telegram |
| Planable | No | $33/workspace | Approval workflows, no Telegram |
| GeeLark | Yes | Unknown | Cloud phone approach, includes Telegram+WhatsApp |
| Eclincher | No | ~$65+ | Analytics focus, no Telegram |
| Publer | Partial | $12+ | Has Telegram integration (rare) |

## Our Advantage
- **Telegram-first**: Almost no competitor supports Telegram natively; we already run 6 Telegram channels
- **Recruitment niche**: Event publishing for job fairs, placement campaigns -- not generic social media
- **Zero cost infrastructure**: Already have Node-RED, raspibig automation, Brevo integration
- **Multilingual**: 11 languages already supported in article pipeline

## Market Validated?
YES -- the social media scheduling market is proven ($39B). But the Telegram sub-niche is underserved. Competitors charge $6-99/mo for scheduling. The gap is Telegram + recruitment events specifically.

## Price Point
- Internal tool: EUR 0 (already building for own use)
- If sold as SaaS: EUR 15-29/mo per user (undercut Buffer/Sendible on Telegram-specific features)
- Revenue potential as SaaS: low unless targeting Telegram-heavy markets (CIS, Middle East, recruitment agencies)

## Risk
- LOW as internal tool (saves time, no cost)
- MEDIUM as SaaS product (small addressable market for Telegram-specific scheduling)
- Buffer/Hootsuite could add Telegram support anytime
- Telegram Bot API changes could break integrations

## Recommendation
BUILD AS INTERNAL TOOL. Use Node-RED + Telegram Bot API + Facebook Graph API + LinkedIn API. Do NOT build as SaaS -- market is too crowded and margins too thin. Focus on automating your own 6 Telegram channels + FB + LinkedIn for recruitment events. Time to build: 2-3 days.

## Sources
- [Zapier - 9 Best Social Media Management Tools 2026](https://zapier.com/blog/best-social-media-management-tools/)
- [Buffer - Social Media Scheduling Tools](https://buffer.com/resources/social-media-scheduling-tools/)
- [Eclincher - 12 Best Social Media Schedulers 2026](https://www.eclincher.com/articles/12-best-social-media-schedulers-in-2026-features-and-pricing)
- [MarketsandMarkets - Social Media Management Market $41.6B](https://www.prnewswire.com/news-releases/social-media-management-market-worth-41-6-billion-by-2026--exclusive-report-by-marketsandmarkets-301346880.html)
- [Fortune Business Insights - Market Size Report](https://www.fortunebusinessinsights.com/industry-reports/social-media-management-market-100638)
