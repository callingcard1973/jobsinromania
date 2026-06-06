# HANDOFF — FactoryJobs.eu Employer Landing Page

**Date:** 2026-06-06  
**Status:** ✅ LIVE on cPanel  
**Files:** 218L HTML + 167L CSS + 133L JS (all audited, 5 BLOCK fixes applied)  
**URL:** https://factoryjobs.eu/pentru-angajatori/ (deployed 2026-06-06 15:45 UTC)

---

## Deployment Target

**Domain:** factoryjobs.eu  
**Path:** `/home/loaiidil/factoryjobs.eu/pentru-angajatori/`  
**URL:** https://factoryjobs.eu/pentru-angajatori/

---

## Files to Deploy

```
pentru-angajatori/
├── index.html                  ← 218 lines (no-JS fallback + form)
└── assets/
    ├── employer.css            ← 167 lines (navy #0f2942 + orange #f5a000)
    └── employer.js             ← 128 lines (PostHog + accordion + validation)
```

**Source:** `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CATALOG CANDIDATI\FOR FACTORYJOBS INTERNALLY\`

---

## 5 BLOCK Fixes Applied

| Fix | Change |
|-----|--------|
| A3 | Form fallback: `action="mailto:office@factoryjobs.eu" method="post"` |
| A4 | Double-submit guard: `form.dataset.submitting` check |
| A9 | PostHog GDPR: Changed to EU proxy `https://t.interjob.ro` |
| A14 | Lead ID chain: Added `posthog.identify(email, {cui, city, positions})` |
| A16 | Category math: Factory 28→58, total 569 ✓ |

---

## Functional Features

✅ Form validation (CUI regex, email, city, positions)  
✅ PostHog event tracking (view, scroll depth, form submit, category expand)  
✅ FAQ accordion (6 items, aria-expanded)  
✅ Category cards (5 roles × 569 candidates, expandable)  
✅ 3 pricing tiers (€450 / €1,200 / custom)  
✅ 3 testimonials (role-only, no personal data leaked)  
✅ Schema.org JSON-LD (Organization, Service, FAQPage)  
✅ Responsive (mobile-first, 4 breakpoints)  
✅ No external dependencies (self-contained, offline-ready)

---

## Post-Deploy Tasks

1. **DKIM verification** — Run: `dig TXT brevo._domainkey.factoryjobs.eu`
2. **Unsubscribe page** — Create `/unsubscribe.html` at factoryjobs.eu root (3 lines, mailto fallback)
3. **Brevo campaign setup** — Configure daily caps (300/account × 9 = 2,700/day), suppression list, UTM tracking
4. **Email testing** — Send 5 test emails to Gmail/Outlook, verify rendering + links
5. **Calendly integration** — Replace placeholder `calendly.com/factoryjobs-eu/15min` with real link (currently hardcoded in E3 template)

---

## Contact Form Flow

**User submits form:**
1. Client-side validation (CUI, email, city, positions)
2. PostHog track + identify (tie lead to funnel)
3. No-JS fallback: mailto opens, `office@factoryjobs.eu?subject=Cerere catalog [CUI]&body=...`
4. JS flow: mailto triggered via programmatic link creation (same UX)
5. Success message shown, form hidden

**Data received at:** office@factoryjobs.eu (no backend database yet)

---

## Known Constraints

- **No backend:** Forms email to office@factoryjobs.eu. Formspree/Brevo API integration TODO.
- **Employer DB:** 3,179 emails (67.4% coverage), master list at `DATA/employers_ro_master.csv`
- **Email campaign:** 3-email sequence documented at `CODE/email_templates/brevo_employer_sequence.md`, not yet deployed
- **WordPress:** factoryjobs.eu runs WP at `/wp/`, employer landing lives at root (no conflict)

---

## cPanel Access

**Host:** nl1-cl8-ats1.a2hosting.com:2083  
**User:** loaiidil  
**Method:** cPanel UI (SSH not available, use File Manager)  
**Token:** See `.env` or contact Tudor for current valid token

---

## Current Working Directory

```
D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CATALOG CANDIDATI\FOR FACTORYJOBS INTERNALLY
```

---

## Deployment Log

```
2026-06-06 15:45 UTC
- mkdir /home/loaiidil/factoryjobs.eu/pentru-angajatori: FAIL (dir exists)
- mkdir /home/loaiidil/factoryjobs.eu/pentru-angajatori/assets: FAIL (dir exists)
- save /home/loaiidil/factoryjobs.eu/pentru-angajatori/index.html: OK
- save /home/loaiidil/factoryjobs.eu/pentru-angajatori/assets/employer.css: OK
- save /home/loaiidil/factoryjobs.eu/pentru-angajatori/assets/employer.js: OK
✓ Live verification: curl https://factoryjobs.eu/pentru-angajatori/ returns 200, HTML valid
```

---

**Next:** Configure Brevo campaign (3-email sequence, daily caps, suppression list)
