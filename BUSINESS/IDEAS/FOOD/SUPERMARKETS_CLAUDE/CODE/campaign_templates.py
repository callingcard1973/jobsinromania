#!/usr/bin/env python3
"""Campaign email templates and execution checklists.

Static content for tier-based outreach campaigns.
Used by campaign_dashboard.py.
"""


def tier_0_template():
    """SEAP Winners warm outreach template."""
    return """
Subject: Strategic partnership opportunity -- [Your Cooperative Name]

Dear [Recipient name],

I noticed that [Company] recently won a SEAP tender for food supply
to [institution type]. Congratulations on the win!

We work with cooperatives across Romania supplying fresh produce,
dairy, and meat to retailers and institutional buyers. We wondered
if you might be interested in discussing supply partnership for
[product category].

Our advantages:
- Direct supply from our cooperative network
- DSVSA registered + ISO 22000 certified
- Competitive pricing on volume orders
- Local supply = faster delivery + lower costs

Would you be open to a 15-minute call next week?

Best regards,
[Your name]
[Your Cooperative]
[Phone]
"""


def tier_1_template():
    """Supermarket chains two-track approach."""
    return """
TRACK A: DIRECT SUPPLIER PORTAL REGISTRATION
  Target: Kaufland, Lidl, Carrefour, Profi, Penny
  Action: Register cooperative as approved supplier

  Portal links:
    kaufland.ro/furnizori | lidl.ro/furnizori
    carrefour.ro/corporate/furnizori | profi.ro (Furnizori)
    penny.ro/furnizori

TRACK B: BUYER RELATIONSHIP OUTREACH
  Target: Regional chains, independent wholesalers
  Action: Email regional buyer + request meeting

  Sample: "We are a registered food cooperative offering
  [categories] to supermarket chains. Would your team be
  interested in meeting to review our product range?"
"""


def tier_2_template():
    """Regional rollout plan for distributors."""
    return """
Week 1: Bucharest (capital region)
  39+ distributor emails, personal outreach, 3-5 meetings expected

Week 2: Transylvania (Brasov, Bihor)
  43+ logistics emails, regional coordinator approach, 2-4 agreements

Week 3: Moldavia (Northeast)
  20+ emails, fill dairy supply gaps, 1-2 agreements

Ongoing: South (Arges, Dambovita)
  Sparse coverage, phone follow-up, become primary supplier in gaps
"""


def tier_3_template():
    """HoReCa validation strategy."""
    return """
PHASE 1: Validation (Week 1)
  Pick 10 random HoReCa, call first, validate emails

PHASE 2: Small batch (Week 2)
  Send 100 validated Bucharest emails, track bounces/opens

PHASE 3: Regional expansion (Week 3+)
  Only if Phase 2 response >0.5%, expand to Alba, Brasov, Botosani

SAMPLE EMAIL:
  Subject: Fresh produce supplier for your restaurant
  Hi [Business], Fresh [category] direct to your kitchen.
  We supply restaurants, hotels, canteens in Romania.
  Interested? Call [phone] or reply to this email.
"""


def acquisition_template():
    """Acquisition track guidance."""
    return """
WHAT TO BUY FROM FAILING FOOD COMPANIES:
1. CLIENT LISTS (50-200 established accounts each)
2. DISTRIBUTION CONTRACTS (exclusive regional supplier agreements)
3. EQUIPMENT & ASSETS (cold storage, packaging, vehicles)

HOW TO PROCEED:
1. Search ACQUISITION_TARGETS.csv, cross-reference CUI
2. Contact insolvency courts (Tribunalul [County] - Proceduri Insolventa)
3. Negotiate with administrator (client lists, contracts, assets)
4. Integration: transition customers + contracts to cooperative
"""


def execution_checklist():
    """Full campaign execution checklist."""
    return """
PREPARATION (Day 1-2):
  [ ] Review all campaign segment CSV files
  [ ] Customize email templates with cooperative name/phone
  [ ] Test email infrastructure (Brevo)

TIER 0: SEAP WINNERS (Day 3-10):
  [ ] Test 10 manual emails, track 7-10 days
  [ ] If >10% response: full rollout (58 emails)
  [ ] Set follow-up reminders (5-7 days later)

TIER 1: CHAINS (Week 2):
  [ ] Register on 5 chain portals
  [ ] Email 483 in 2 batches (200 + 283)

TIER 2: DISTRIBUTORS (Week 2-4):
  [ ] Bucharest (39), Transylvania (43), Moldavia (20+)
  [ ] Track meetings, LOIs, distribution agreements

TIER 3: HORECA (Week 2-3):
  [ ] Validate 10 random, send 100 batch, monitor bounces
  [ ] Expand only if response >0.5%

ACQUISITION (Ongoing):
  [ ] Search insolvency courts for top 5 targets
  [ ] Negotiate client list + asset purchases

WEEK 4 REVIEW:
  [ ] Compile responses, calculate conversion, go/no-go on scaling
"""
