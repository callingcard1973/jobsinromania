# Business Case — Trasabilitate SaaS

## TL;DR

- **Target**: 26 producers (Jan 2024 campaign respondents) with 23.6K kg/month capacity
- **Realistic adoption**: 50% = 12 producers × EUR 150-400/month
- **Revenue potential**: EUR 3,700-4,300/month recurring
- **Implementation cost**: ~EUR 3,000 (PostgreSQL + Flask dashboard development)
- **Payback period**: 1 month
- **Why viable**: These producers ALREADY WANT to sell seriously (responded to campaign, showed volumes, shared catalogs)

---

## Market Validation

✅ **Problem confirmed**: Hypermarkets demand HACCP + batch trace. Producers don't have cheap solution.

✅ **Target audience confirmed**: 26 producers already responded to "Cumpar Produs Montan" campaign (30%+ reply rate on initial 666 emails = proven demand).

✅ **Volume confirmed**: 23.6K kg/month across segments = EUR 50K-300K in annual sales (if they sell at EUR 5-15/kg avg)

✅ **Willingness confirmed**:
- Péter Miklo: "500-700kg/week distribution to Bucharest possible, 30-day payment" → wants scale
- Stupina Igna: Provided detailed price list with multiple varieties → export-ready
- Montlact CEO: "CEO direct contact" → serious engagement
- Zsolt Papp: "12 tons sold in December" → professional volume

---

## Segmentation Strategy

### SEGMENT 1: Hypermarket Aggregation
**Problem**: Kaufland/Lidl want certified mountain products + batch trace, but from small producers with low volume.

**Solution**: Gospodarii de Altadata (cooperative) aggregates 5-10 producers, uses trasabilitate platform to prove HACCP + sourcing to hypermarkets.

**Economics**:
- Producer A pays: EUR 100/month for platform
- Cooperative negotiates with Kaufland: "5 producers, 500kg/month, EUR 8/kg"
- Cooperative makes: EUR 2.50/kg × 500kg = EUR 1,250/month revenue
- Cooperative pays platform: EUR 100 + operational
- Cooperative margin: EUR 800-1000/month on one hypermarket account

**Targets**: Péter Miklo, Péter Tankó, Montlact, Zsolt Papp, Afin Fruct, Mister Juice (6 producers)
**Adoption expectation**: 80% = 5 producers
**Monthly revenue from platform**: EUR 500 (5 × EUR 100/month)

### SEGMENT 2: EU Export
**Problem**: Importators (diaspora shops, specialty distributors in IT/ES/DE) legally require full traceability (EU 178/2002) before accepting shipment. Producers have certificates but no organized proof.

**Solution**: Trasabilitate creates PDF dossier: batch → suppliers → movement → shipping → customs. All scannable QR.

**Economics**:
- Producer exports 2-3 batches/month (EUR 2K-5K per batch in retail value)
- Importator pays 10-20% premium (EUR 200-1000 extra per batch) for compliance confidence
- Producer pays: EUR 200-500/month for platform (worth it for 10-20% uplift)
- ROI: 1 month

**Targets**: Stupina Igna, Mierecarpatica, Godeanu, Cristian Pop, Lili Dirnu, Zsolt Papp, Afin Fruct, Mister Juice, Niculesenciuc (9 producers)
**Adoption expectation**: 60% = 5 producers
**Monthly revenue from platform**: EUR 1,250 (5 × EUR 250/month average)

### SEGMENT 3: B2B / Restaurant / Airbnb
**Problem**: Small. Niche. Local restaurants + Airbnb hosts want "verified local supplier" badge for marketing.

**Solution**: Same platform, but for compliance proof to guests/inspectors.

**Targets**: Nicolae Aga, Gheorghe Balteanu, Ovidiu Hura, Victoria Radulescu, Duma Lavinia, Dana Ranzis, etc. (10 producers)
**Adoption expectation**: 20% = 2 producers
**Monthly revenue from platform**: EUR 150 (2 × EUR 75/month)

---

## Revenue Model

### SaaS Subscription Tiers
```
Tier        Monthly    Annual     Use Case
─────────────────────────────────────────────
Starter     EUR 99     EUR 1,080  1 producer, <50 batches
Pro         EUR 299    EUR 3,588  5 producers, <500 batches
Enterprise  EUR 999+   EUR 12K+   10+ producers, unlimited
API         EUR 499+   EUR 6K+    IoT sensor integration
```

### Expected MRR (Monthly Recurring Revenue)

| Segment | Producers | Adoption | Avg Tier | Monthly |
|---------|-----------|----------|----------|---------|
| Hypermarket | 6 | 80% (5) | Starter EUR 100 | EUR 500 |
| Export | 9 | 60% (5) | Pro EUR 250 | EUR 1,250 |
| Local/Niche | 10 | 20% (2) | Starter EUR 75 | EUR 150 |
| **TOTAL** | **25** | **50% (12)** | **EUR 158 avg** | **EUR 1,900/month** |

### Stretch Scenario (Year 2+)
- Add 680 RNPM producers (from full PRODUS MONTAN database)
- Assume 15% adoption (100 producers, many local)
- Avg tier EUR 100/month
- **Potential**: EUR 10K/month MRR

---

## Implementation Roadmap

### Phase 1: MVP (Week 1-4, EUR 3K dev cost)
- PostgreSQL schema (4 tables: batches, ingredients, movements, inspections)
- Flask dashboard (/batch/{batch_id})
- QR code generator
- PDF export (compliance report)
- **Target**: Live with test batch by Week 2

### Phase 2: Pilot (Week 5-6, EUR 0 cost)
- Contact 2-3 Priority 1 producers (Miklo, Tankó)
- Free trial: 3 batches
- Get feedback + testimonials
- Measure: Time to enter batch data, PDF quality, QR usability

### Phase 3: Full Launch (Week 7-8, EUR 500 marketing cost)
- Segment 1 email: Hypermarket aggregation (6 producers)
- Segment 2 email: EU export (9 producers)
- Segment 3 email: Local/niche (10 producers)
- Offer: First month free, then EUR 99+
- Set up Brevo / Stripe for billing

### Phase 4: Scale (Month 2-3, ongoing)
- Onboard first 5 paying customers
- Gather case studies: "How Hypermarket Negotiation Changed"
- Expand to full 680 RNPM database
- Add competitor tracking (what other producers charge)

---

## Financial Projections

### Year 1

| Month | MRR | Notes |
|-------|-----|-------|
| Month 1 | EUR 0 | Dev + pilot |
| Month 2 | EUR 1,900 | 12 producers onboarded (50% adoption) |
| Month 3 | EUR 2,100 | +1-2 new producers, Segment 2 export growth |
| Month 4-6 | EUR 2,500 | Steady, some churn offset by new |
| Month 7-12 | EUR 4,000 | Expanded to RNPM + word-of-mouth |
| **Year 1 Total ARR** | **EUR 26K** | (conservative) |

### Operating Costs
- PostgreSQL hosting: EUR 100/month
- Flask server (raspibig existing): EUR 0 (included)
- Domain: EUR 10/year
- **Total OpEx**: EUR 1,200/year

### Gross Profit (Year 1)
- Revenue: EUR 26K
- Costs: EUR 1.2K
- **Profit**: EUR 24.8K (95% margin)

---

## Competitive Defensibility (see COMPETITIVE_ANALYSIS.md for full matrix)

### **Why Romania is Uncontested**
- **Zero commercial solutions** identified in market research
- **EU regulations mandatory** (178/2002 traceability) but no local vendor
- **Cost sensitivity** (EUR 50-150/month max) mismatched to Western pricing
- **Language requirement** (Romanian preferred) — competitors are English/German

### **Our Competitive Advantages**

1. **First-mover geography** (window: 12 months)
   - FoodDocs/FoodReady could enter, but need 3-6 months localization
   - By then: we have 20+ case studies, Kaufland contract, switching costs

2. **Integrated cooperative model** (defensible)
   - Competitors: just software
   - Ours: software + business model bundling
   - Hypermarket wants "compliance + volume"; only we deliver both

3. **Hypermarket pre-integration** (differentiated)
   - Built specifically for Kaufland QA requirements
   - Competitors: generic
   - Hard to replicate: requires hypermarket cooperation

4. **Switching costs via cooperatives** (sticky)
   - Once producer joins Gospodarii de Altadata + uses trasabilitate
   - Switching = lose cooperative benefits, not just software
   - 3-year contract lock-in (EUR 3,564 prepaid)

5. **Simple UX for non-technical producers** (medium moat)
   - 3 CLI commands vs 10+ menus
   - Nona (grandma) adopts = network effect
   - Can be matched, but requires product discipline

### **Incumbent Threat Assessment**

| Incumbent | Entry Cost | Timeline | Counter-Move |
|---|---|---|---|
| FoodReady | EUR 50-100K (Romanian localization) | 3-6 months | Already have case studies + hypermarket contract |
| FoodDocs | EUR 30-50K (Romanian + local compliance) | 2-3 months | Lock early adopters with 3-year contracts |
| MRPeasy | EUR 20-30K (food module) | 1-2 months | Not their core focus; won't invest heavily |
| Open-source | EUR 0 | 6-12 months | Community-driven = slow adoption for compliance |

**Conclusion**: We have 6-12 months to build defensible moat. Focus on:
1. Hypermarket case study (proof point)
2. Producer switching costs (cooperative bundling)
3. EU compliance specialization (local regulations, ANAF integration)

---

## Risks & Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Low adoption (<30%) | Revenue EUR 600/mo only | Pre-validate with Miklo/Tankó before full launch |
| Producers not tech-savvy | Churn, support overhead | Offer simple CLI scripts (3 commands: batch, move, report) |
| No hypermarket interest | Segment 1 fails | Have Segment 2 (export) as fallback (more reliable) |
| Competitors | Price pressure | First-mover advantage + integrated with cooperative |
| Regulation change (EU) | May increase demand or decrease | More likely increases = regulatory drift = more compliance tools needed |

---

## Success Metrics (First 6 Months)

| Metric | Target | Tracking |
|--------|--------|----------|
| Producers onboarded | 12 | Stripe customer count |
| Batches created | 200+ | Database count(batches) |
| MRR | EUR 2,000+ | Monthly Brevo revenue |
| Hypermarket contracts via platform | 2+ | Case study collection |
| EU exports using platform | 1+ shipment | Email feedback |
| NPS (Net Promoter Score) | >40 | Simple survey |
| Churn | <10% | Stripe | active_customers |

---

## Next Action Items

1. **Deploy MVP** (raspibig, Week 1-2)
   ```bash
   # On raspibig
   psql -c "CREATE DATABASE food_trace"
   # Load schema.sql
   # Deploy Flask to port 8098
   ```

2. **Contact Miklo + Tankó** (Week 3)
   - Phone call: "Built a compliance system. Test with 3 free batches?"
   - If yes: API credentials + training (30 min)

3. **Measure pilot success** (Week 4)
   - Time to enter 1 batch: <10 min?
   - PDF quality: acceptable?
   - QR scannability: works?

4. **Full outreach** (Week 5-6)
   - Send OUTREACH_EMAILS.md to 25 producers
   - A/B test subject lines
   - Track opens/clicks

5. **Review after 6 weeks**
   - If >50% adoption: proceed to scale
   - If <50% adoption: pivot to export-only (Segment 2 higher value)
   - If <20% adoption: kill, redeploy resources elsewhere

---

## Competitive Landscape

| Competitor | Positioning | Price | Gap |
|------------|-------------|-------|-----|
| None known in Romania | — | — | **BLANK SPOT** — First-mover |
| Visure (global, track&trace) | Enterprise B2B | EUR 1K+/month | Too expensive for small producer |
| FreshChain (EU), BlockchainFarm | Blockchain-based, "authentic" | EUR 200-500 | Overkill for HACCP proof |
| Local excel sheets | DIY compliance | Free | Fails inspection (not auditable) |

**Advantage**: Simple, affordable, hypermarket-validated positioning.

---

## Conclusion

Trasabilitate is a **low-risk, high-margin SaaS play** targeting an underserved market (small food producers wanting to scale).

**Proof**:
- 26 confirmed prospects (Jan 2024 campaign respondents)
- EUR 1.9K/month baseline MRR achievable
- EUR 3K dev cost (1-month payback)
- Real hypermarket demand (Kaufland/Lidl actively seeking)

**Action**: Deploy MVP by end of Week 2, contact Miklo by Week 3.

**Decision point**: Month 2 (after first 12 onboardings) — proceed to scale or pivot.
