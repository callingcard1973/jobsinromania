# 06 - Brand & Go-To-Market: HAMBARUL ROMANESC

**Date:** 2026-06-24 | **Author:** brand-marketing agent
**Inputs:** 00_market_study.md (positioning gap) | 02_catalog_summary.md (hero SKUs + private label) | 03_locations.csv (pilot)
**Pilot:** neighborhood store, Bucuresti **Sector 1 (Floreasca/Dorobanti/Aviatiei)** - loc. rank 2, catchment ~225k, highest-income Sector, 3 competitors <500m, est. rent EUR18/m2.

> **Estimate discipline:** every budget, CAC, footfall and benchmark below is labelled **(est.)** unless tied to a sourced input. RO retail norms used where no audited figure exists. Refresh after pilot data.

---

## 1. Brand identity

### Name rationale - Hambarul Romanesc
**Hambar** = the barn / granary - where a household harvest is **stored, kept honest, and shared**. It evokes abundance from your own land, peasant thrift, and the moment produce leaves the farm for the table. **Romanesc** makes the promise explicit and non-negotiable: **100% Romanian producers**. The name is a contract, not a slogan - it pre-commits the brand to the origin-pure model that incumbents (sec.5-6 market study) cannot copy without breaking their import economics.

- **Short form:** Hambarul (oral, app, loyalty card). **Legal/sign:** HAMBARUL ROMANESC.
- **Domain note:** hambarulromanesc.ro exists in infra (flagged external in security memo) - verify control before launch.

### Tone of voice
**Authentic | rustic-modern | trustworthy | proud-not-nationalist.**
- Speak like a trusted producer, not a corporate retailer: plain, warm, specific (Miere de la familia Pop, stupina din Bistrita-Nasaud - not produs natural premium).
- Always **name the human and the place.** Never anonymous local.
- Confident, never defensive about price: the premium is *traceability earned*, not vanity.
- RO-first; EN as secondary layer for expats in Sector 1 (Floreasca/Aviatiei has high expat density).

### Visual cues
- **Palette:** wheat/granary ochre + warm cream, deep forest green (origin/BIO), barn-wood brown, ink-black for traceability data. Avoid flag-tricolor cliche - pride via craft, not kitsch.
- **Logo motif:** stylized hambar/granary roofline or full grain-ear; woodcut/letterpress texture = handmade honesty.
- **Typography:** humanist serif for the wordmark (heritage) + clean grotesque sans for prices/labels (modern, legible).
- **Signature device - the Producer Tag:** every shelf edge + every private-label pack carries a small card with **producer face photo, farm name, county, and a CUI/QR**. This is the visual system, not decoration - it IS the moat made tangible.
- **Photography:** real producers, real hands, real farms (no stock). Daylight, unstyled, documentary.

### Tagline (RO + EN)
- **Primary RO:** De la hambarul lor, pe masa ta. (From their barn, to your table.)
- **EN:** From their barn to your table.
- **Trust line RO:** Fiecare produs are un nume si un sat. (Every product has a name and a village.)
- **EN trust line:** Every product has a name and a village.
- **Pride/PR line RO:** Cumperi romaneste. Platesti fermierul, nu importatorul. (Buy Romanian. You pay the farmer, not the importer.)

---

## 2. The traceability + local-pride story (the moat)

**The single defensible idea (market study sec.5-6):** not produs romanesc as a shelf - but **the whole store is the producer**. Surface the producer at every touchpoint.

**Per-SKU producer surfacing - the system:**
| Layer | What the shopper sees | Where it lives |
|---|---|---|
| Shelf-edge Producer Tag | Face photo, farm name, county, X km de aici | every SKU |
| Pack / jar (private label) | Producer name + **CUI** + batch + QR | 36 HAMBARUL own-brand SKUs (sec.2 catalog) |
| QR -> producer page | Story, farm video, county map pin, other SKUs from same farm | web (see sec.3 SEO) |
| In-store Producatorul lunii | One farmer featured floor-to-ceiling | front-of-store wall |

**Why it is the moat:** incumbents run origin as a marketing layer over an import/private-label base - they *cannot* expose per-SKU traceability without revealing their import mix (sec.4 SWOT). Regional credible players (Annabella/Diana/Unicarm) have origin but no brand/digital traceability system. The Hambarul data spine (producer CUI -> SKU -> shelf -> QR page) is the copy-proof asset.

**Hero SKUs to lead the story (from 02 catalog handoff):**
Salam de Sibiu, Miere de salcam, Magiun de Topoloveni, Pastrama, Telemea de oaie, Tuica de Bistrita.
-> Each gets a flagship producer page + a launch social story (sec.3). Highest-premium, story-richest categories (honey +33%, wine/tuica +36%, traditional +33%, preserves +24%) carry the narrative; fresh staples (produce, eggs, dairy) carry the weekly basket.

**Hard dependency (flag -> supplier-sourcing):** catalog sec.3 - most categories carry **placeholder CUIs**. *Traceability is the entire brand; placeholder CUIs MUST be resolved to real CUIs before launch.* No producer page goes live without a verified CUI. This is a launch gate, not a nice-to-have.

---

## 3. Channel plan

### A. Local SEO - Bucuresti city/category/producer pages
**Reuse the InterJob/AgroEvolution FastAPI SEO generator pattern** (.claude/skills/fastapi-seo-generator/ - the same city x category x entity templated-page engine used for InterJob job pages and AgroEvolution county/land pages). Same data-driven generation, repointed at the catalog.

Page taxonomy (auto-generated from catalog.csv + suppliers_master.csv):
- **City landing:** Magazin cu produse 100% romanesti in Bucuresti - Hambarul Romanesc (Sector 1).
- **City x Category** (10 cat): Miere romaneasca in Bucuresti; Branzeturi de la producatori romani Bucuresti; Zacusca si conserve de casa Bucuresti.
- **Producer pages** (one per verified CUI): Miere de la Stupina [Nume], [Comuna], [Judet] - face, story, farm video, county map pin, SKUs, QR target. **This is the SEO moat** - thousands of long-tail producer/origin queries no competitor indexes.
- **Hero-SKU pages:** Salam de Sibiu autentic; Magiun de Topoloveni; Tuica de Bistrita - origin + producer + where-to-buy.
- **Schema:** LocalBusiness + Product + (producer) Organization + FAQ structured data; QR codes deep-link shelf->producer page (closes offline->online loop, feeds reviews + e-grocery secondary channel from market study sec.5.4).

### B. Social - producer stories (FB / Instagram / TikTok)
**Reuse the fastapi-social-post-generator skill** (the InterJob/AgroEvolution auto social generator) to template producer-story posts from the same catalog data (RO + EN captions, county hashtags, scheduled).
- **Format = the producer, always.** Short documentary reels: farmer + farm + product + the Producer Tag reveal. Cunoaste-l pe [Nume], face telemea de oaie de 30 de ani la [Sat].
- **TikTok/Insta Reels:** farm-to-shelf in 30s; what is behind the QR; harvest/seasonal moments - high organic reach, low cost.
- **FB:** community + events + producatorul saptamanii + Sector 1 neighborhood targeting.
- **Cadence (est.):** 4-5 reels/wk + 1 producer deep-dive/wk; recycle into SEO producer pages.
- **UGC:** shoppers scan QR -> share farm story -> reward loyalty points (closes loop).

### C. In-store experience
- **Producer Tags on every shelf edge** + Producatorul lunii wall.
- **QR everywhere** -> producer page; tasting station for hero SKUs (miere, telemea, salam, tuica) - sampling is the #1 conversion lever for origin-premium.
- **Din lume shelf clearly separated** (catalog sec.4 import long-tail) so it never dilutes the Romanian promise - physically and visually walled off.
- Chalkboard county-of-the-week; printed mini farm-stories at the counter.

### D. Loyalty card - Cardul Hambarul
- Points on basket; **bonus points for buying featured producer-of-the-month SKUs** (drives the story, moves margin-rich shelf-stable lines).
- App + physical card (older Sector 1 demographic still wants plastic).
- Data -> first-party CRM for email/SMS (reuse Brevo/Gmail sender infra already in stack), e-grocery upsell, churn signals.
- Tier perk: early access to seasonal/limited producer batches (tuica noua, miere de mana).

### E. Farmers-market events
- Monthly **Piata Hambarul** in-front-of-store or nearby Sector 1 park: 6-10 featured producers in person, tasting, direct-from-farmer.
- Turns the store into a community anchor + recurring PR + UGC engine; cheap footfall driver.
- Ties to seasonal calendar (recolta, sarbatori) - reuse seasonal-page pattern from AgroEvolution.

### F. PR - supporting Romanian farmers
- Angle: **Singurul magazin unde platesti fermierul, nu importatorul** - the per-producer-CUI traceability is the press hook (it is literally novel; market study sec.5 confirms no chain does this).
- Targets: Progresiv, Retail.ro, ZF, Profit.ro (retail trade press already mapped in market study sources), plus food bloggers + local Bucuresti media + agri associations (CAP cooperatives - existing AgroEvolution network).
- Producer-led human stories travel further than corporate launch PR.

---

## 4. Bucuresti launch campaign (Sector 1 pilot)

> All figures **(est.)** - RO retail / proximity-store norms; refresh with pilot actuals.

### Budget - pilot launch (one store, first 90 days)
| Line | Est. cost (EUR) | Note |
|---|---|---|
| Local SEO build (reuse generator) | 2,000 | mostly internal eng time; reuses existing skill - marginal cost low |
| Social content (producer reels, 90d) | 5,000 | videographer + paid boost; producer travel |
| Paid social + geo-targeted (Sector 1) | 8,000 | FB/Insta/TikTok geo-radius + lookalike |
| In-store: Producer Tags, signage, tasting | 6,000 | tags system, producator-lunii wall, sampling stock |
| Loyalty card setup (app + plastic) | 4,000 | reuse CRM/Brevo infra -> keep low |
| Launch event + farmers-market kit | 5,000 | opening weekend + first Piata Hambarul |
| PR (press kit, outreach, samples) | 3,000 | mostly earned; sample boxes to press/bloggers |
| Contingency (~12%) | 4,000 | |
| **Total pilot launch (est.)** | **~37,000 EUR** | one-store, 90-day. Steady-state mktg ~3-4% of store revenue (est.) thereafter |

### CAC target (est.)
- Blended **CAC ~ EUR4-7 per acquired loyalty member** (est.; proximity grocery norm - high frequency, low per-acquisition spend).
- Effective CAC near **EUR0** for organic/PR/event-driven walk-ins; paid social carries the paid CAC.
- Payback: with avg basket ~EUR18-25 (est., premium-origin) and ~weekly repeat, CAC recovered on **first 1-2 baskets**.

### Expected footfall (est.)
- Sector 1 high-income, 3 competitors <500m -> must win on *differentiation*, not convenience.
- Target steady-state **~400-700 transactions/day** (est.; mid-format urban proximity, premium = lower count than discounter but higher basket - consistent with market study sec.1 per-store anchor).
- Ramp: opening week spike (event + PR) -> dip -> loyalty-driven recovery to steady state by ~month 3.
- Implied annualized turnover **~EUR2-3 M/store** (matches market study SOM per-store anchor).

### Opening tactics
1. **Soft-open week:** invite Sector 1 neighborhood + featured producers present in-store; tasting of all 6 hero SKUs.
2. **Producer parade opening day:** 8-10 farmers behind their own products - the store IS the producers.
3. **Loyalty sign-up offer:** join Cardul Hambarul -> free hero-SKU sample box (data capture from day 1).
4. **QR treasure-trail:** scan 5 producer tags -> discount -> teaches the traceability behavior.
5. **Press + blogger preview** day before, sample boxes mailed (PR sec.3.F).
6. **First Piata Hambarul** market in opening weekend.

### KPIs
| KPI | Target (est.) | Cadence |
|---|---|---|
| Loyalty sign-ups (90d) | 3,000-5,000 members | weekly |
| Transactions/day (steady) | 400-700 | daily |
| Avg basket | EUR18-25 | weekly |
| Blended CAC | EUR4-7 | monthly |
| QR scans / producer-page sessions | rising MoM | weekly |
| % revenue from hero/featured SKUs | track -> grow | monthly |
| Social organic reach + reels views | growth MoM | weekly |
| PR placements (launch) | >=6 (incl. >=2 trade press) | one-off |
| **% SKUs with verified producer CUI** | **100% (launch gate)** | pre-launch + ongoing |
| Repeat-visit rate (loyalty) | >=40% within 4 wks | monthly |

---

## 5. Skill reuse (InterJob / AgroEvolution patterns)

| Need | Reused skill / pattern | Adaptation |
|---|---|---|
| City x category x producer SEO pages | fastapi-seo-generator (InterJob city/category job pages; AgroEvolution county/land pages) | repoint at catalog.csv + suppliers_master.csv; entity = producer-CUI |
| Producer-story social posts (FB/Insta/TikTok, RO+EN) | fastapi-social-post-generator | template from SKU+producer rows; county hashtags; schedule |
| Loyalty CRM email/SMS | existing Brevo / Gmail sender + orchestrator (email-campaigns) | new loyalty + producer-of-the-month segments |
| Seasonal / event pages | AgroEvolution seasonal-page pattern | recolta / sarbatori / Piata Hambarul calendar |
| WordPress publish queue | fastapi-wordpress-queue-orchestrator | publish producer pages + PR articles |
| Admin/KPI dashboard | fastapi-admin-dashboard (port 8096 pattern) | brand KPI dashboard (sign-ups, CAC, QR scans) |

---

## 6. Handoff -> business-plan
- **Pilot launch marketing budget: ~EUR37k (est.)**, one-store / 90-day; steady-state ~3-4% of store revenue (est.).
- **CAC EUR4-7/loyalty member (est.)**, payback within 1-2 baskets.
- **Footfall ~400-700 txns/day (est.)**, basket EUR18-25 (est.) -> ~EUR2-3 M/store annualized (matches market-study SOM anchor).
- **Revenue assumption:** loyalty + producer-story engine drives repeat-rate >=40%/4wk; demand tailwind real but self-reported origin-intent counted conservatively (per market study sec.7).
- **Hard launch gate carried to plan:** 100% verified producer CUIs before opening (traceability = the entire brand) -> blocks on supplier-sourcing.

*Estimates are RO-retail-norm triangulations, not audited. Refresh CAC/footfall/basket with pilot actuals before multi-store rollout.*
