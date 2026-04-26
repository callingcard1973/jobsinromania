# 6-Week Parallel Build: ElectroSafe + GovTender Bot + InsolvencyVault

**Status:** PLANNING ONLY — No emails sent, no campaigns launched until approval.

---

## Wave 1: Foundation (Week 1-2)

### Track A: ElectroSafe
**Goal:** Landing page + validation interviews

**Build:**
- `electrosafe.ro` Shopify store (hero, video, FAQ, signup form)
- Landing page copy: "Electricians who lost certificates wasted 6 months. You won't."
- Google Form: 3-min survey (lost certs? Cost? Would pay €150+€30/mo?)
- Email list: Extract 1,000 electricians from ANRE/electricieni_enriched.csv

**Deliverables:**
- Landing page live (localhost or test domain)
- Survey template ready
- Email list CSV ready (WITH APPROVAL BEFORE SEND)

**Owner:** Claude (frontend) + you (approval)

---

### Track B: GovTender Bot
**Goal:** Data pipeline + backend scaffold

**Build:**
- Parse OPENTENDER (6.3GB) → extract company profiles, tender history
- Parse TED data (13K contacts) → enrich with CIFN company lookup
- Build tender-to-company matcher (CPV codes → ISCIR/ANRE/ANCOM skills)
- Redis cache for fast matching

**Deliverables:**
- `CODE/govtender_data_pipeline.py` — OPENTENDER processor
- `CODE/govtender_matcher.py` — AI routing logic (LLM: match tender to electrician skills)
- PostgreSQL table: `govtender_tenders` (tender_id, company, cpv, value, deadline)
- PostgreSQL table: `govtender_matches` (tender_id, user_id, relevance_score, notified)

**Owner:** Claude (code) + you (DB approval)

---

### Track C: InsolvencyVault
**Goal:** Data layer + product spec

**Build:**
- Query CIFN: 770K active insolvencies, pull liquidator contacts
- `CODE/insolvency_data_pipeline.py` — Extract insolvency state, case status, executor info
- Product spec: Physical binder kit (laminated case documents), SaaS (case timeline, deadlines)
- Market validation: Check if liquidators have email (estimate coverage %)

**Deliverables:**
- `DATA/INSOLVENCIES_LIQUIDATORS.csv` (name, email, phone, cases_active, region)
- `PRODUCT_INSOLVENCY_SPEC.md` (pricing, kit contents, SaaS features)
- Email list ready (WITH APPROVAL BEFORE SEND)

**Owner:** Claude (data) + you (approval)

---

## Wave 2: MVP Builds (Week 3-4)

### Track A: ElectroSafe SaaS
**Build:**
- FastAPI backend: `/api/upload-cert` (PDF → OCR → searchable)
- Frontend: Credential gallery, training calendar, renewal alerts
- Mobile: QR code linking to public profile
- Job portal API stub (not live, just structure)

**Deploy:** `app.electrosafe.ro` (A2 Hosting or Vercel)

---

### Track B: GovTender Bot Web
**Build:**
- Landing page: "Find EU tenders matching your skills in 30 seconds"
- Sign-up form: Company name + skills (multi-select: electrician, pressure equipment, gas, etc.)
- Subscription modal: €19/mo, €49/mo, €99/mo tiers
- Dashboard stub: "Your matches" (admin-only, seeded data for demo)

**Deploy:** `govtender.ro` (A2 or Vercel)

---

### Track C: InsolvencyVault SaaS
**Build:**
- Liquidator sign-up: Email + name + region
- SaaS dashboard: Case timeline, deadline alerts, document upload
- Email triggers: "3 cases expiring in 30 days" (alert system)
- Pricing: €50/mo, €100/mo, €200/mo (B2B)

**Deploy:** `insolvencyvault.ro` (A2)

---

## Wave 3: Testing & Validation (Week 5)

### Track A: ElectroSafe
- Deploy landing page
- Send survey to 100 electricians (WITH YOUR APPROVAL)
- Target: 50+ responses validating pain (80%+ lost certs)

### Track B: GovTender Bot
- Load 1,000 sample tenders into PostgreSQL
- Test matcher: Run 100 ISCIR + ANRE companies through algorithm
- Verify relevance scores make sense (manual spot-check)

### Track C: InsolvencyVault
- Extract liquidator contact list
- Validate email coverage (goal: >40%)
- Test case timeline extraction from CIFN data

---

## Wave 4: Pre-Launch Review (Week 6)

**Deliverables to Show You:**

1. **ElectroSafe:**
   - Landing page screenshot
   - Sample survey responses (if 50+)
   - Email list ready to send

2. **GovTender Bot:**
   - Dashboard screenshot (seeded data)
   - Sample matcher output: "Electrician XYZ matches 12 EU tenders worth €5M"
   - Code review

3. **InsolvencyVault:**
   - Sample SaaS dashboard
   - Liquidator email list (count + coverage %)
   - Product spec document

**Wait for your approval before:** Sending ANY emails, launching ANY campaigns, publishing ANY data

---

## Files to Create (No External Action Yet)

```
ISCIR/
├── PARALLEL_3_PRODUCT_PLAN.md (this file)
├── ElectroSafe/
│   ├── CODE/
│   │   ├── landing_page.html
│   │   └── survey_form.py
│   └── DATA/
│       └── electricians_1000.csv (ready to send, NOT sent)
├── GovTender/
│   ├── CODE/
│   │   ├── govtender_data_pipeline.py
│   │   ├── govtender_matcher.py
│   │   └── govtender_web.py (FastAPI)
│   └── DATA/
│       └── opentender_processed.parquet (6.3GB → cleaned)
└── InsolvencyVault/
    ├── CODE/
    │   ├── insolvency_data_pipeline.py
    │   └── insolvencyvault_web.py (FastAPI)
    └── DATA/
        └── liquidators_770k.csv (ready to send, NOT sent)
```

---

## Success Metrics (Week 6)

| Product | Success = |
|---------|-----------|
| **ElectroSafe** | Landing page live + 50+ survey responses + 80%+ pain validation |
| **GovTender Bot** | Dashboard shows 100+ tenders matched to 50 test companies + <2s query time |
| **InsolvencyVault** | 770K liquidator list extracted + >40% email coverage + case timeline working |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| ElectroSafe low survey response | Offer €5 discount coupon for survey completion |
| GovTender Bot matching too slow | Cache tenders in Redis, batch-process matches at night |
| Insolvency data quality issues | Manual validation on 100 samples before bulk load |
| Context switching across 3 projects | Assign each track one dedicated day per week |

---

## Approval Gates (BEFORE EXECUTION)

- [ ] **Gate 1 (End of Week 2):** You review Wave 1 deliverables → approve Track B DB schema + Track A survey copy
- [ ] **Gate 2 (End of Week 4):** You review Wave 2 MVPs → approve landing pages + pricing
- [ ] **Gate 3 (End of Week 5):** You review validation results → decide which product to launch first
- [ ] **Gate 4 (Week 6):** Final approval before ANY email/campaign

**No sends, posts, or publishes until you sign off at each gate.**

---

## Timeline

```
Week 1-2: DATA + FOUNDATION (research, templates, lists ready but not sent)
Week 3-4: BUILD (web UIs, APIs, dashboards)
Week 5:   TEST (validate assumptions, run internal trials)
Week 6:   REVIEW (show you everything, get final approval)
Week 7+:  LAUNCH (only after your final approval)
```

Ready to start?
