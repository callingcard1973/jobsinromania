# Next Actions: 3-Week Launch Plan

## Week 1: ElectroSafe Validation & Setup

### Day 1-2: Pain Point Validation
- Interview 15 electricians (ANRE list)
  - Who has lost training certificates? (expect 80%+ yes)
  - What's the cost of license lapse/re-certification? (expect €500-2000)
  - Would they pay €150 + €30/mo to avoid that? (expect 60%+ yes)
- Create Google Form survey (3 mins)
- Send via Brevo to random 500 from electricieni.csv (collect emails from DATA/electricieni_enriched.csv)

### Day 3-4: Landing Page
- Shopify store: `electrosafe.ro`
- Copy: "Electricians who lost their credentials wasted 6 months and €2000. You won't."
- Hero image: Binder + phone showing credentials
- Video: 90-second "What's in the kit?"
- CTA: "Reserve your ElectroSafe" (early bird €120)
- FAQ: License renewal calendar, job portal, team management

### Day 5: Outreach Campaign
- Email 1,000 electricians (from enriched list, segment by county)
- Subject: "Keep your certificates organized (+ 5 EU job matches)"
- Lead magnet: Free training calendar (PDF) to 2,000
- WhatsApp: "ElectroSafe 20% early bird" (manual to 50 contacts to start viral)

### Milestones:
- ✓ 100 survey responses validating pain
- ✓ 20 landing page signups
- ✓ 5 kit pre-orders

---

## Week 2: SaaS Prototype + NetVault Outreach

### Day 8-9: SaaS MVP
- Credential upload form (PDF + OCR → searchable)
- Training calendar (API to sync with Google Calendar)
- License renewal alerts (email 30/60/90 days)
- Public profile (QR code linkable)
- Deploy to `app.electrosafe.ro` (Vercel or A2)

### Day 10-11: NetVault Launch Email
- Target: All 568 ANCOM telecom companies with email
- Subject: "Your compliance audit took 3 weeks. It should take 3 minutes."
- Offer: Free 7-day trial + €50 discount on Year 1 subscription
- Webinar: "How telecom operators passed ANCOM audit in 8 hours" (record + send)

### Day 12: ANRE Tender Matching
- Run CPV matching for electricians (install tenders, licensing tenders)
- Export: DATA/ANRE_TENDER_MATCHES.csv
- Email top 500 electricians: "5 EU tenders matching your skills + credential profile"

### Milestones:
- ✓ SaaS live with 50 test users
- ✓ 10 NetVault demo requests
- ✓ Electrician tender emails sent

---

## Week 3: Scale + Analytics

### Day 15-16: Scale Campaigns
- Move ElectroSafe to Brevo (full automation)
- A/B test subject lines (2 variants × 5,000 each)
- Launch on electricjobs.eu homepage ("Organize your credentials → get EU jobs")
- Create TikTok: "3 electricians who got EU jobs w/ ElectroSafe" (15 sec each)

### Day 17-18: Bundle Campaign
- Identify 500-1000 companies in BOTH ISCIR + ANRE (SQL cross-ref)
- Create COMBO offer: "Pressure equipment + electrical = full industrial safety stack"
- Email to ISCIR customers: "We found 200 co-certified ANRE electricians — bundle with their data?"

### Day 19-20: Analytics
- Conversion rate by channel (email / WhatsApp / TikTok)
- CAC vs LTV by product
- Churn rate on SaaS (target: <3% monthly)
- Adjust messaging based on data

### Milestones:
- ✓ ElectroSafe: 100+ kit sales
- ✓ NetVault: 20+ trials
- ✓ Bundle: 50+ combo kits ordered
- ✓ Product-market fit confirmed

---

## Key Data Files to Use

**Electricians outreach:**
- D:\MEMORY\BUSINESS\IDEAS\ISCIR\ANRE\DATA\electricieni_enriched.csv (phone + email if available)
- Filter: Active (expiry date > today)
- Deduplicate by email

**Telecom outreach:**
- D:\MEMORY\BUSINESS\IDEAS\ISCIR\ANCOM\DATA\ancom_final.csv (has websites + emails)
- Pre-enriched with contact data

**Tender data:**
- ANRE: Need to generate like ISCIR tender_matcher.py
  - CPV 45100 (electrical installation)
  - CPV 45200 (electrical repairs/maintenance)
  - CPV 45300 (heating installation)
- ANCOM: Need to search network service tenders (CPV 64200-64300)

---

## Budget Estimate (3 weeks)

| Item | Cost |
|------|------|
| Shopify store (3 mo) | €45 |
| Brevo email blasts (10K) | €50 |
| Landing page design (contractor) | €200 |
| SaaS hosting (Vercel/A2) | €50 |
| Webinar platform (Zoom) | €0 (free tier) |
| **TOTAL** | **€345** |

**Expected ROI Week 3:** 100 kits × €160 = €16,000 revenue, 47x ROAS

---

## Success Metrics

| Metric | Target | Reality Check |
|--------|--------|-------|
| Interview pain validation | 80% say lost certs | Electricians = blue-collar, high pain |
| Landing page conversion | 2% signups | +/- 0.5% normal for B2B |
| Email open rate | 25% | Romanian prof. lists = 20-30% |
| Kit pre-orders | 5 | Proof of concept, not scale |
| SaaS activation rate | 60% of kit buyers | High if job portal works |
| NetVault trial conversion | 10% → paid | B2B = lower, but €100/mo SaaS works |

---

## Risk Mitigation

1. **Email deliverability:** Split test ANRE list (1000 first), monitor bounces
2. **Product-market fit delay:** ElectroSafe validation critical — if <50% pain, pivot to NetVault
3. **SaaS complexity:** MVP = credential upload + calendar + alerts only. Defer job portal to Week 2.
4. **Competitor overlap:** Search "profil electrician Romania" + "license tracker" — none found (good signal)

---

## Ownership

- **Product:** You (roadmap decisions)
- **Outreach:** Claude (email campaigns + landing page copy)
- **Data:** Extract from ANRE/ANCOM CSVs, cross-reference ISCIR
- **Operations:** Weekly sync on metrics + next 7-day plan
