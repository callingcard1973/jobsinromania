# FactoryJobs EU Employer Landing Page — Deployment Checklist

**Version:** 2.0 (OUG 32/2026 Compliance + Grammar Fixes)  
**Date:** 2026-06-06  
**URL:** https://factoryjobs.eu/pentru-angajatori/

---

## FILES TO UPLOAD

| File | Size | Destination |
|------|------|-------------|
| `pentru-angajatori.html` | 23.7 KB | `/home/loaiidil/factoryjobs.eu/pentru-angajatori/index.html` |
| `assets/employer.css` | 8.7 KB | `/home/loaiidil/factoryjobs.eu/pentru-angajatori/assets/employer.css` |
| `assets/employer.js` | 4.5 KB | `/home/loaiidil/factoryjobs.eu/pentru-angajatori/assets/employer.js` |

---

## DEPLOYMENT STEPS (cPanel File Manager)

### 1. Access cPanel
- URL: https://nl1-cl8-ats1.a2hosting.com:2083
- User: `loaiidil`
- Password: (your password)

### 2. Create Directory Structure
- Click **File Manager** (left sidebar)
- Navigate to `/home/loaiidil/factoryjobs.eu/`
- **Create folder:** `pentru-angajatori`
- **Inside that folder, create:** `assets`

### 3. Upload Files
#### Index Page
1. In `/pentru-angajatori/`, click **Upload**
2. Select `pentru-angajatori.html`
3. Right-click file → **Rename** → change to `index.html`

#### CSS
1. In `/pentru-angajatori/assets/`, click **Upload**
2. Select `employer.css`
3. Leave name as-is

#### JavaScript
1. In `/pentru-angajatori/assets/`, click **Upload**
2. Select `employer.js`
3. Leave name as-is

### 4. Set Permissions
- All files: **644** (rw-r--r--)
- All folders: **755** (rwxr-xr-x)

(Usually auto-set, but verify if files don't load)

---

## VERIFY DEPLOYMENT

After upload, test in browser:

**Live URL:** https://factoryjobs.eu/pentru-angajatori/

### Visual Checks
- [ ] Page loads with navy (#0f2942) and orange (#f5a000) branding
- [ ] Hero section displays correctly
- [ ] Navigation bar visible and sticky
- [ ] Footer appears at bottom

### Functional Checks
- [ ] FAQ accordion: click question → expands answer → click again → collapses
- [ ] 12 FAQ items visible (scroll through FAQ section)
- [ ] OUG 32/2026 questions (Q9-12) display and expand
- [ ] Category cards clickable (Packaging, Machinery, Logistics, Factory, Warehouse)
- [ ] Contact CTA buttons work:
  - Email link opens mailto handler
  - WhatsApp link opens WhatsApp
  - Internal anchor links scroll smoothly

### Responsive Checks (if possible)
- [ ] Desktop (1440px): 4-column stats strip, 3-column pricing gone
- [ ] Tablet (768px): 2-column stats
- [ ] Mobile (320px): 1-column layout, buttons stack

### Content Checks
- [ ] No pricing tiers visible (removed entirely)
- [ ] No form visible (removed entirely)
- [ ] No "Full-Service" / "Recruit-Only" language
- [ ] New FAQ about OUG 32/2026 present and readable
- [ ] Footer mentions "Agenție autorizată conform OUG 32/2026"

### Browser Console
- [ ] No JavaScript errors (F12 → Console)
- [ ] No CSS loading errors
- [ ] PostHog script loads (check Network tab for t.interjob.ro)

---

## KEY CHANGES IN THIS DEPLOY

### Removed
- ❌ Pricing section (€450, €1,200, Custom packages)
- ❌ Lead form (CUI, email, city, positions fields)
- ❌ Form validation & submission logic
- ❌ All pricing-related CSS

### Added
- ✅ 4 new FAQ items about OUG 32/2026
  - Q9: "Ce este OUG 32/2026 și cum mă afectează?"
  - Q10: "Trebuie să mă autorizez pe workinromania.gov.ro?"
  - Q11: "Cum funcționează verificarea digitală a candidaților?"
  - Q12: "Care sunt avantajele legii noi pentru mine ca angajator?"
- ✅ Romanian grammar fixes
  - "Noi gestionez" → "Noi gestionăm"
  - "pe platform" → "pe platformă"
  - "procesul e" → "procesul este"
  - "Protecție contra fraudei" → "Protecție împotriva fraudei"
- ✅ Footer updated to mention OUG 32/2026 compliance

### Updated
- Schema.org JSON-LD: 8 FAQs → 12 FAQs (SEO)
- Hero CTAs: form submission → email + WhatsApp direct contact
- Nav links: removed "Preț" + "Catalog" → added "Candidați"

---

## TROUBLESHOOTING

**Page shows 404?**
- Check file is named `index.html` (not `.html`)
- Check docroot path is exactly `/home/loaiidil/factoryjobs.eu/pentru-angajatori/`

**CSS/JS not loading?**
- Verify file paths in HTML:
  - CSS: `<link rel="stylesheet" href="assets/employer.css">`
  - JS: `<script defer src="assets/employer.js"></script>`
- Check files exist in `/assets/` subfolder
- Hard refresh browser (Ctrl+Shift+R or Cmd+Shift+R)

**Accordion not expanding?**
- Check JavaScript loads (F12 → Sources, search for `employer.js`)
- Check console for errors (F12 → Console)

**Text looks wrong?**
- Hard refresh (Ctrl+Shift+R)
- Clear browser cache
- Check CSS file loads (F12 → Network → look for employer.css with 200 status)

---

## ROLLBACK

If deployment fails, the previous version is at:
- Backup: N/A (first version, no rollback needed)

Future deployments can save old version before uploading new one.

---

## NEXT STEPS (Post-Deploy)

1. ✅ Test live page thoroughly
2. 📧 Share link with team: https://factoryjobs.eu/pentru-angajatori/
3. 🔍 Monitor PostHog analytics at https://eu.posthog.com (dashboard for events)
4. 📊 Track which FAQ items get clicked most (use PostHog)
5. 🎯 Next iteration: add employer testimonials section (optional)

---

**Deployed by:** Claude Code  
**Deployment method:** cPanel File Manager (manual)  
**Support:** office@factoryjobs.eu
