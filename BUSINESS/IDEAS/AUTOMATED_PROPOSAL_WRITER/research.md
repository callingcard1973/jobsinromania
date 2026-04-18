# Research: AUTOMATED PROPOSAL WRITER (IDEA-135)
Date: 2026-04-16

## Description
Company sees SEAP/TED tender, LLM writes draft proposal. EUR 50-200/proposal. 100/month automated = EUR 5K-20K. Qwen can do this.

## Market Size
- Global procurement/bid management software: ~$8B (2025)
- EU public procurement: EUR 2 trillion/year
- Romania SEAP: ~100,000 tenders/year
- AI proposal writing is fastest-growing segment in procurement tech

## Competitors
| Competitor | Price | Notes |
|-----------|-------|-------|
| AutogenAI | Custom (enterprise) | FedRAMP authorized, full lifecycle, raised $153M |
| DeepRFP | $75/user/mo | RFP analysis + draft generation |
| mytender.io | Custom | UK-focused, bid management + AI writing |
| Tenderbolt | Custom | EU public tenders, AI analysis + response |
| Brainial | Custom | EU tender management, AI-assisted |
| Thornton & Lowe | Custom | UK bid consultancy + AI tools |
| Procurement Sciences | Custom | US government contracting veterans |

## Our Advantage
- Romania-specific: SEAP templates, Romanian language, local legal requirements
- Already monitor SEAP (existing scrapers) and TED (EBRD system)
- Qwen 2.5 on raspibig can generate drafts at zero API cost
- Can bundle with IDEA-128 (monitoring: "we alert you + write the bid")
- EUR 50-200 is 10x cheaper than hiring a bid consultant (EUR 500-2,000)
- Know Romanian construction sector deeply (23K ISC contacts, 4,176 EBRD projects)

## Validated?
Yes. AutogenAI raised $153M, DeepRFP charges $75/mo, Tenderbolt exists for EU. Market is real and growing. Romania-specific gap exists.

## Price
- Per proposal: EUR 50 (simple/direct purchase), EUR 100 (standard), EUR 200 (complex/EU tender)
- Subscription: EUR 299/mo for 5 proposals + monitoring
- Bundle with IDEA-128: EUR 199/mo (monitoring + 2 proposals/mo)

## Risk
Medium. Proposal quality must be high enough to be useful. Legal responsibility if proposal has errors. Need deep SEAP template knowledge. Qwen 2.5 may not handle complex Romanian legal language (needs testing).

## Recommendation
GO. Build MVP for SEAP direct purchases first (simpler, standardized format). Test with 10 construction companies from existing campaigns. Iterate on quality. Then expand to full SEAP tenders and TED. Realistic revenue: EUR 30K-60K/year in year 1.

## Sources
- [AutogenAI](https://autogenai.com/)
- [DeepRFP Pricing](https://deeprfp.com/)
- [mytender.io](https://mytender.io)
- [Tenderbolt](https://www.tenderbolt.ai/en/responses-to-public-tenders-using-ai)
- [AI in Tender Management 2025](https://altura.io/en/blog/ai-tendermanagement)
