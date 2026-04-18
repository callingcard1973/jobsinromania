# Expat Relocation Service — Handoff

## What Was Done (2026-04-12)

### 1. Provider Outreach Campaign — READY TO SEND
- **1,166 contacts** extracted from raspibig DB, deduplicated, major Romanian cities
- **Categories:** consultanti fiscali (746), auditori financiari (225), firme audit (125), avocati (70)
- **Sender:** office@expatsinromania.org (Brevo, 300 credits, API verified working)
- **Reply-to:** office@expatsinromania.org (forward internally)
- **Daily limit:** 50/day, 65s delay (Tudor's config)
- **Duration:** ~23 days to complete
- **DMARC fixed:** Added `rua=mailto:rua@dmarc.brevo.com` to expatsinromania.org DNS

### 2. Services Landing Page — LIVE
- **URL:** https://expatsinromania.org/services/ (WP page ID 46878)
- **Packages:** Landing Pack EUR 500, Legal Stay EUR 800, Full Relocation EUR 2,500
- **Individual services:** 8 items (EUR 15–400)
- **Contact:** office@expatsinromania.org, LinkedIn, Facebook group (77K)
- **Links to:** /directory/ (existing Directorist plugin)

---

## File Locations

### Raspibig (192.168.100.21)

| What | Path |
|------|------|
| Campaign data (CSVs) | `/opt/ACTIVE/OUTREACH_RO/EXPAT_PROVIDERS/DATA/` |
| Active campaign CSV | `/opt/ACTIVE/OUTREACH_RO/EXPAT_PROVIDERS/DATA/campaign_providers.csv` |
| Email template | `/opt/ACTIVE/OUTREACH_RO/EXPAT_PROVIDERS/templates/expat_partner.txt` |
| Dashboard config | `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs/expat_providers.json` |
| Unified orchestrator | `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/orchestrator.py` (PID 2690, 5min interval) |
| Unified send engine | `/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/send_campaign.py` |
| Dashboard | `http://192.168.100.21:8096/expat_providers/` |

### Database (interjob_master on raspibig)

| Table | Records | Purpose |
|-------|---------|---------|
| `expat_providers_campaign` | 1,166 | Contacts with status tracking |
| `expat_providers_send_log` | 0 | Send history |
| `expat_providers_responses` | 0 | Response tracking |

### Source DB tables used for extraction

| Table | Records | With Email |
|-------|---------|-----------|
| `consultanti_fiscali` | 1,074 | 998 |
| `auditori_financiari` | 1,850 | 1,634 |
| `firme_audit` | 995 | 995 |
| `experti_contabili` | 17,080 | 0 (phone only) |
| `anevar_evaluatori` | 3,554 | 1,750 |
| `executori` | 836 | 768 |
| Lawyers CSV | 2,209 | 353 |

### Local (D:\MEMORY\)

| What | Path |
|------|------|
| Business plan | `EXPAT RELOCATION SERVICE PLAN/Expat Relocation Service Project Plan.txt` |
| Services page HTML | `EXPAT RELOCATION SERVICE PLAN/services_content.html` |
| This handoff | `EXPAT RELOCATION SERVICE PLAN/HANDOFF.md` |

---

## Campaign Config Summary

```json
{
  "campaign_name": "EXPAT_PROVIDERS",
  "sender": "office@expatsinromania.org (Brevo)",
  "reply_to": "office@expatsinromania.org",
  "daily_limit": 50,
  "delay": "65-300s",
  "business_hours": "Mon-Fri 8:00-18:00",
  "enabled": true
}
```

## Email Template

```
Subject: Partnership - US expat clients needing local services

Hi,

I run a platform targeting expats relocating to Romania:
https://expatsinromania.org

We also manage a Facebook community of 77,000+ expats and repats:
https://www.facebook.com/groups/expatsinromania

We are generating inbound requests for:
- residency
- company setup
- relocation support

I'm looking for a reliable partner to handle execution locally.

Can you handle English-speaking clients and fixed-price packages?
If yes, I'd like to discuss sending you clients regularly.

Best,
Tudor

office@expatsinromania.org
https://www.linkedin.com/in/seicarescu/
```

---

## DNS Changes Made

- **_dmarc.expatsinromania.org** TXT: `v=DMARC1; p=none; rua=mailto:rua@dmarc.brevo.com`
- Changed via cPanel API v2 (delete line 66 + add new record)
- Brevo IP whitelisted: `2a02:2f0f:8019:800:c5ec:7b7e:41cd:fefe` (raspibig IPv6)

---

## Services Page (WordPress)

- **Page ID:** 46878
- **Slug:** /services/
- **Status:** published
- **WP credentials:** English Jobs Romania / Rm8CvZfZuJwk53qqdnS5RHFt
- **Site:** WordPress with Yoast SEO, Directorist, Google Site Kit

### Existing site structure (relevant pages):
- /directory/ — Directorist provider directory (empty listings)
- /lawyers-legal/ — placeholder
- /accountants-tax/ — placeholder
- /healthcare/ — placeholder
- /real-estate-relocation/ — placeholder
- /moving-to-romania-guide/ — SEO content
- /cost-of-living-romania/ — SEO content
- /romania-digital-nomad-visa/ — SEO content
- /starting-business-romania/ — SEO content

---

## What's NOT Done Yet

1. **Response workflow** — no system to track provider replies and manage partnerships
2. **Demand side** — no Facebook group post to validate expat demand
3. **Pricing model** — how Tudor makes money (referral fee vs commission vs markup) not decided
4. **Directorist directory** — existing plugin with empty listings, needs populated with signed partners
5. **WhatsApp** — no WhatsApp number on services page (only email + LinkedIn)
6. **Stripe/payments** — no online payment system
7. **Campaign not launched** — configured and ready, waiting for Tudor's go

---

## To Launch Campaign

The unified orchestrator is already running and reads the config. To send:
1. Go to `http://192.168.100.21:8096/expat_providers/send`
2. Click send — it will send up to 50 emails using Brevo

Or the orchestrator will pick it up automatically on its next cycle if the sector is enabled (it is).
