# Research: LANDING A/B TEST (IDEA-050)
Date: 2026-04-16

## Description
Generator automat variante landing page + tracking conversii pe 28 domenii. Self-hosted, Qwen generates variants, tracks clicks/conversions via access logs.

## Market Size
- Global A/B testing software market: ~$1-1.5B in 2026, CAGR 11-14%
- Projected $4.4B by 2035
- Landing page builder market overlaps significantly

## Competitors

| Tool | Price/mo | A/B Testing | AI | Notes |
|------|----------|-------------|-----|-------|
| Unbounce | $99-249 | Yes (Smart Traffic AI) | Yes | Market leader, auto-routes visitors |
| Instapage | $79-199 | Yes + heatmaps | Limited | Enterprise-grade, collaboration |
| Leadpages | $49+ | Basic | No | Budget option, payment processing |
| Landingi | Free-$65 | Yes | No | Free tier with A/B |
| VWO | $49+ | Advanced MVT | Yes | Pure testing tool |
| Carrd | $19/yr | No | No | Ultra-cheap, no testing |
| involve.me | Free-$49 | Yes | Yes | AI builder, 50 free submissions |

## Our Advantage
- Zero cost: self-hosted on A2, Qwen generates variants locally
- 28 domains = instant deployment scale no competitor offers
- Access log analysis = no JS tracking needed (GDPR-friendly)
- Already have cPanel API deployer + HTML templates
- No monthly fees vs $99-249/mo for competitors

## Validated?
YES -- Google Optimize shutdown (2023) left gap for self-hosted A/B testing. Market growing 11%+ CAGR. Every competitor charges $50-250/mo.

## Price
Internal tool (saves $100-250/mo vs buying Unbounce). Could sell as SaaS later at $29-49/mo.

## Risk
- LOW: Building for own use, no external dependency
- Variant generation quality depends on Qwen output
- Conversion tracking via logs less precise than JS-based

## Recommendation
BUILD -- High ROI internal tool. Already have all infrastructure (28 domains, cPanel deployer, LLM). Start with 3 domains, measure lift, expand.

## Sources
- [Prismic: 9 Best Unbounce Alternatives 2026](https://prismic.io/blog/best-unbounce-alternatives-for-personalized-landing-pages)
- [LanderLab: 10 Best Landing Page Builders 2026](https://landerlab.io/blog/best-landing-page-builders)
- [Future Market Insights: A/B Testing Market](https://www.futuremarketinsights.com/reports/ab-testing-software-market)
