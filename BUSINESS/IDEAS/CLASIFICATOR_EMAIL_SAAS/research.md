# Research: CLASIFICATOR EMAIL SAAS (IDEA-045)
Date: 2026-04-16

## Description
API clasificare email (sklearn 94.5%). EUR 29/luna/1000 clasificari. FastAPI + landing page. Sell email classification engine (orders, spam, bounces, applications, autoresponders) as SaaS API.

## Market Size & Demand
- Email management/automation market: USD 2.5B+ globally (2026)
- AI email classification: sub-segment, mostly bundled into larger platforms
- Target customers: recruitment agencies, e-commerce, support teams with high email volume
- Standalone email classification APIs are rare -- most are features within larger products

## Competitors Found

| Competitor | Type | Price/mo | Accuracy | Notes |
|------------|------|----------|----------|-------|
| Mailytica | SaaS | Custom quote | ML per client | German, Outlook/Gmail plugin |
| EmailTree.ai | SaaS | EUR 70-750 | NLP-based | 4 tiers, auto-routing+reply |
| Google Workspace | Built-in | $6-18/user | Good for spam | Not standalone, basic categories |
| Microsoft 365 | Built-in | $6-22/user | Good for spam | Focused inbox only |
| Nylas | API | $0.01/request | N/A | Email platform, classification as feature |
| Custom GPT/Claude | API | $0.001-0.01/call | 90%+ | Any LLM can classify, no moat |

## Our Advantage
- **94.5% accuracy with sklearn** -- lightweight, fast, no LLM costs
- **6-tier cascade proven**: rules->sklearn->Qwen->laptop->z.ai->Claude
- **Domain expertise**: trained on recruitment emails specifically
- **Cost per classification: ~EUR 0** (sklearn on CPU)
- **FastAPI ready**: standard Python stack

## Market Validated?
PARTIALLY -- EmailTree.ai charges EUR 70-750/mo proving demand exists. But standalone email classification is tiny niche. Most businesses use Gmail/Outlook built-in or integrate into CRM/helpdesk.

## Price Point
- EUR 29/mo for 1,000 classifications (proposed)
- EUR 99/mo for 10,000 classifications
- EUR 249/mo for 100,000 classifications
- Comparison: EmailTree starts at EUR 70/mo (but includes auto-reply, routing)
- Risk: LLM APIs do same at $0.001-0.01/call, eroding value

## Risk
- HIGH -- moat is thin
- Any developer can build sklearn email classifier in a weekend
- LLM APIs (OpenAI, Anthropic) offer superior classification cheaply
- EmailTree bundles classification with auto-reply and routing (more value)
- Customer acquisition cost for niche API product is high
- 94.5% accuracy is good but LLMs hit 95-98%

## Recommendation
DO NOT BUILD AS SAAS. Moat too thin -- sklearn classification is trivial to replicate, LLM APIs are better and cheap. Keep as internal tool for 56 IMAP accounts. If monetizing email expertise, bundle as service (email management for recruitment agencies) rather than raw API. The technology is a feature, not a product.

## Sources
- [Mailytica - AI Email Classification](https://mailytica.com/en/ai-e-mail-classification/)
- [EmailTree.ai - Automatic Classification](https://emailtree.ai/automatic-classification/)
- [EmailTree Pricing](https://www.saasworthy.com/product/emailtree-ai/pricing)
- [Medium - NLP Email Intent Classification](https://medium.com/@ashwithashettyyy/from-inbox-chaos-to-order-creating-an-nlp-model-to-classify-email-intent-3f6bcbd3d5cd)
- [SCIMUS - AI Mail Classification Models](https://thescimus.com/blog/ai-powered-mail-classification-models/)
