# Research: CV PARSING API (IDEA-063)
Date: 2026-04-16

## Description
Expose existing CV scanner as API. Recruitment agencies pay EUR 0.50-2/CV parsed. Target: 100 CV/day = EUR 50-200/day.

## Market Size & Demand
- Global resume parsing market valued at ~$3.5B (2025), growing 10-15%/year
- Every ATS, staffing agency, job board needs CV parsing
- EU recruitment market is massive: 28K+ agencies in Europe
- Demand is proven -- Sovren, Affinda, RChilli all profitable in this space

## Competitors Found

| Competitor | Price/CV | Min Plan | Accuracy | Notes |
|-----------|---------|----------|----------|-------|
| Textkernel (+ Sovren) | Custom (enterprise) | $500+/mo | 95%+ | Market leader, acquired Sovren |
| Affinda | ~$0.13-0.80/CV | $99/mo (est) | 90%+ | Deep learning, flexible credits |
| RChilli | $0.015-0.15/CV | $75-149/mo | 85-90% | High volume, enterprise focus |
| Daxtra | Custom | Enterprise only | 90%+ | Long-established, custom quotes |
| Eden AI | $0.10/CV (aggregator) | Pay-as-you-go | Varies | Meta-API, routes to multiple parsers |
| Parseur | Free tier + paid | $39/mo | 80-85% | Template-based, simpler |
| Airparser | Free tier + paid | $29/mo | 80% | AI-powered, newer entrant |

## Our Advantage
- Already have working CV scanner (D:\MEMORY\CV\)
- Can run on local LLM (zero API cost per parse)
- Can price aggressively at EUR 0.10-0.50/CV (below Affinda, above RChilli bulk)
- Focus on EU/multilingual CVs (Romanian, Hungarian, etc.) -- underserved niche
- No cloud dependency = GDPR-friendly (on-premise option)

## Market Validated?
YES. Multiple competitors with millions in revenue. RChilli processes 4B+ resumes. Affinda has 1000+ customers. The market clearly pays for this.

## Price Point
EUR 0.50-2/CV is too high for bulk. Market reality:
- Bulk: EUR 0.02-0.15/CV (compete with RChilli)
- Standard: EUR 0.10-0.50/CV (compete with Affinda)
- Premium (multilingual/GDPR): EUR 0.50-1.00/CV
Better model: EUR 49/mo (500 CVs) to EUR 199/mo (5000 CVs)

## Risk
- HIGH. Extremely competitive market with well-funded players.
- Accuracy must be 90%+ to compete -- LLM-based parsing may not match Textkernel.
- Need API infrastructure, documentation, uptime guarantees.
- Support burden for API product is significant.

## Recommendation
**PARK** -- Market is real but crowded with well-funded competitors. Our CV scanner works but is not API-ready. Better to use CV parsing internally for recruitment business rather than sell as standalone API. Revisit if we find a niche (e.g., Romanian/Eastern European CVs only).

## Sources
- [Adeptiq 2026 Comparison](https://adeptiq.be/blog/the-best-cv-parsing-software-for-recruitment-agencies-(2026-comparison))
- [Skima Best Resume Parser APIs](https://skima.ai/blog/industry-trends-and-insights/best-resume-parser-api)
- [Affinda Pricing](https://www.affinda.com/recruitment-ai-pricing)
- [RChilli Pricing](https://www.rchilli.com/pricing)
- [Eden AI Resume Parsers](https://www.edenai.co/post/best-resume-parser-apis)
