# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

**v1.0 | 2026-06-06 | FactoryJobs EU — Employer Landing Page (OUG 32/2026 Compliant)**

---

## PURPOSE

Build **employer attraction landing page** at `https://factoryjobs.eu/pentru-angajatori/` — pure marketing page with no transactional elements. Convert recruiting managers into leads via direct contact (email, WhatsApp, phone).

**Not a job board. Not a form-based lead capture. Not pricing display.** Just value prop + proof + contact.

---

## CANONICAL CONTEXT

- **Parent:** `D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\PLAN 01 06 2026\CLAUDE.md` — full InterJob architecture, DB schema, WordPress integration
- **Sibling:** `D:\MEMORY\...\WEB\CATALOG JOBURI\CLAUDE.md` — job PDF/HTML generation (separate pipeline)
- **Sibling:** `D:\MEMORY\...\WEB\FACTORYJOBS.EU\CLAUDE.md` — broader employer pages architecture

Core references:
- **OUG 32/2026:** Mandatory digitalization of non-EU worker hiring via workinromania.gov.ro
- **Brand:** Navy #0f2942 + Orange #f5a000
- **Language:** Bilingual RO/EN (RO primary)
- **Deploy:** A2 Hosting cPanel only (no SSH, no FTP)
- **Compliance:** Operează conform Legii 156/2000, OUG 25/2014, OUG 32/2026

---

## PROJECT STRUCTURE

```
FOR FACTORYJOBS INTERNALLY/
  CLAUDE.md                              this file
  DEPLOY_CHECKLIST.md                    step-by-step cPanel upload guide
  HANDOFF.md                             2026-06-06 deployment notes + post-deploy tasks
  deploy_a2.py                           (reference; cPanel API unreliable — use UI)
  pentru-angajatori.html                 main landing page (23.7 KB, 218L)
  assets/
    employer.css                         styling (8.7 KB, 102L)
    employer.js                          tracking + interactivity (4.5 KB, 128L)
  factoryjobs_catalog_internal.html      candidate portfolio (separate; not deployed here)
```

---

## KEY FILES

### pentru-angajatori.html (Index)
- **Lines:** 218
- **Content:** Hero + pain points + 4-step process + 5 candidate categories + 3 testimonials + 12 FAQ items + contact band + footer
- **Features:**
  - Schema.org JSON-LD (Organization, Service, FAQPage) for SEO
  - Meta tags (og:image, og:title, twitter:card) for social sharing
  - 12 FAQ items (Q1-8 general, Q9-12 OUG 32/2026 compliance)
  - Sticky nav with anchor links
  - Category accordion (expandable cards showing candidate distribution by country/language/experience)
  - No forms, no pricing tiers, no email capture
  - PostHog tracking via EU proxy (t.interjob.ro)

### assets/employer.css
- **Lines:** 102
- **Content:** CSS variables for brand colors + responsive grid layout
- **Colors:**
  - Navy: #0f2942 (primary), #1a3a5c (secondary)
  - Orange: #f5a000 (accent), #d98e00 (hover)
  - Gray: #f5f5f5, #5a6878, #e3e8ef
- **Breakpoints:** 980px (tablet), 780px (mobile nav), 620px (mobile layout)
- **No external CDNs** — all self-contained, offline-ready

### assets/employer.js
- **Lines:** 128
- **Content:** PostHog analytics + accordion interactivity + click tracking
- **Events tracked:**
  - `view_employer_landing` (page load)
  - `scroll_25`, `scroll_50`, `scroll_75`, `scroll_100` (depth)
  - Click events via `data-track` attributes
  - `expand_category` (category accordion)
  - `click_faq_question` (FAQ accordion)
- **No form validation** (forms removed)
- **No external dependencies** — vanilla JS, PostHog snippet only

---

## CONTENT RULES

### ✅ ALLOWED
- Value propositions for employers (speed, legal safety, verification)
- Proof: testimonials (anonymized by role/company size)
- Process explanation (4 clear steps)
- FAQ addressing employer concerns
- Candidate categories (5 sectors, 569 total verified workers)
- Contact CTAs (email, WhatsApp, phone)
- Legal compliance statements (OUG 32/2026, Law 156/2000, OUG 25/2014)
- Candidate distribution data (countries, languages, experience)
- Company branding (logo, colors, footer info)

### ❌ NOT ALLOWED
- Pricing tiers, packages, or cost comparisons
- Lead capture forms (removed 2026-06-06)
- Personal data (names, phone numbers, addresses) — only anonymized roles/companies
- Calls-to-action to external services without context
- Email campaign signup forms
- Job listings (those go on the job board, not here)
- Candidate CVs or detailed profiles (only high-level categories)

### ⚠️ SPECIAL RULES
- **OUG 32/2026 language:** Must be accurate. FactoryJobs is "authorized agency" (agenție autorizată), not just service provider.
- **No false claims:** "569 verified candidates" must match DB count at deployment time.
- **Bilingual:** Every major heading and CTA should have RO + EN versions (currently RO-primary, EN in schema/footer).
- **No external forms:** All lead capture removed. Contact = direct mailto/WhatsApp/phone.
- **Compliance first:** OUG 32/2026 FAQ must be present and accurate before deployment.

---

## DEPLOYMENT

### Files to Deploy
| File | Size | Destination |
|------|------|-------------|
| pentru-angajatori.html | 23.7 KB | /home/loaiidil/factoryjobs.eu/pentru-angajatori/index.html |
| assets/employer.css | 8.7 KB | /home/loaiidil/factoryjobs.eu/pentru-angajatori/assets/employer.css |
| assets/employer.js | 4.5 KB | /home/loaiidil/factoryjobs.eu/pentru-angajatori/assets/employer.js |

### Method
**cPanel File Manager** (manual UI upload — API unreliable per A2 docs)
- Host: nl1-cl8-ats1.a2hosting.com:2083
- User: loaiidil
- Token: K9ATCMHPKVSKUV2M97447JLY45EH29KQ (for API if needed)

### Steps
1. Login to cPanel
2. File Manager → `/home/loaiidil/factoryjobs.eu/`
3. Create folder: `pentru-angajatori`
4. Create subfolder: `pentru-angajatori/assets`
5. Upload 3 files to correct paths
6. Set permissions: files=644, dirs=755
7. Verify: curl https://factoryjobs.eu/pentru-angajatori/ returns 200 + HTML content

See **DEPLOY_CHECKLIST.md** for detailed steps.

---

## TESTING

### Pre-Deploy (Local)
```powershell
# Open in browser
start file:///D:/MEMORY/.../FACTORYJOBS%20INTERNALLY/pentru-angajatori.html

# Check no console errors (F12 → Console)
# Check all links work (click each anchor)
# Check accordion expands/collapses
# Check responsive (F12 → Device mode)
```

### Post-Deploy (Live)
Visit: https://factoryjobs.eu/pentru-angajatori/

**Visual tests:**
- Header loads (nav sticky on scroll)
- Colors correct (navy + orange)
- Layout responsive (mobile = 1-column, tablet = 2-column, desktop = full)
- Footer visible at bottom

**Functional tests:**
- FAQ accordion: Q1 click → expands → Q1 click again → collapses
- Category cards: click "Packaging" → detail section appears below
- Contact buttons: email/WhatsApp/phone all clickable
- Internal links: anchor links (#faq, #contact) scroll smoothly
- External schema: check with schema.org validator

**Content tests:**
- No pricing visible ✓
- No forms visible ✓
- OUG 32/2026 FAQs present (Q9-Q12) ✓
- Footer mentions OUG 32/2026 authorization ✓

**Analytics tests:**
- F12 → Network → search "t.interjob.ro" → PostHog script loads
- F12 → Console → no errors
- Click tracking works: scroll page → check PostHog dashboard for scroll events

---

## COMMON EDITS

### Add FAQ Item
1. Add `<div class="faq-item">` in HTML (update data-idx)
2. Add Q&A to Schema.org JSON-LD
3. Update h2 count ("12 întrebări" → "13 întrebări" etc.)
4. Test accordion expand/collapse

### Update Testimonial
1. Find `.testi` block in HTML
2. Edit blockquote, name, role, meta
3. Keep anonymized (role + company size only, no personal names)
4. Test responsive layout

### Change Contact Details
1. Update `office@factoryjobs.eu` in 3 places:
   - nav-cta button (hero)
   - contact band (middle)
   - footer
2. Update WhatsApp: `+33 7 51 17 13 56` (3 places)
3. Update phone in footer schema

### Update Candidate Count
1. `<div class="n">569</div>` in stats strip
2. Schema.org Service description: "569 candidați verificați"
3. Category counts: if total changes, update each sector count
4. Test: Packaging + Machinery + Logistics + Factory + Warehouse = total ✓

---

## EDITS LOG

**2026-06-06:**
- ✅ Removed pricing section (3 tiers: €450, €1,200, Custom)
- ✅ Removed lead form (CUI, email, city, positions)
- ✅ Added 4 FAQ items about OUG 32/2026 compliance (Q9-Q12)
- ✅ Fixed Romanian grammar: "gestionez" → "gestionăm", "platform" → "platformă", "e" → "este", "contra" → "împotriva"
- ✅ Updated footer to mention "Agenție autorizată conform OUG 32/2026"
- ✅ Updated nav CTAs from form → email + WhatsApp
- ✅ Removed all CSS/JS for form validation and pricing tier logic
- ✅ Updated Schema.org FAQPage: 8 → 12 questions

**2026-06-05:**
- Initial deployment with pricing tiers, lead form, 8 FAQ items

---

## FUTURE ITERATIONS

### Next (Optional)
1. Add video testimonial section (employer case study)
2. Add "Why FactoryJobs" comparison (vs. ANOFM, traditional agencies)
3. Add blog/news section on OUG 32/2026 changes
4. Bilingual toggle (currently RO-primary, EN in footer only)

### Not In Scope (Separate Projects)
- Job board for workers (separate domain)
- Candidate portfolio (separate folder: factoryjobs_catalog_internal.html)
- Admin dashboard (separate project)
- Email campaigns (separate project: Brevo)

---

## QUESTIONS / SUPPORT

**Contact:** office@factoryjobs.eu  
**Compliance:** Legal review by [TBD] before 2026-06-30 (OUG 32/2026 official launch)  
**Analytics:** PostHog dashboard at https://eu.posthog.com → project: factoryjobs.eu

---

## REFERENCE FILES

- **HANDOFF.md** — Deployment log, post-deploy tasks, known constraints
- **DEPLOY_CHECKLIST.md** — Step-by-step cPanel upload + verification
- **PARENT CLAUDE.md** — Full InterJob architecture, DB schema, WordPress sites
- **CATALOG JOBURI CLAUDE.md** — Job PDF generation (separate pipeline)

---

*Last updated: 2026-06-06 by Claude Code*
