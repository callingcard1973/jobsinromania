# CLAUDE.md — InterJob Multi-Domain Web Platform

**v2.0 | 2026-06-18** — Comprehensive Web Architecture

## Mission

**InterJob ecosystem**: 10+ domains + WordPress multisite + job orchestration + buyer networks. Single-page applications for recruitment: farmers, factories, construction, hoteliers, mechanics, electricians, careworkers, warehouse/meat processors, internal transfers.

---

## Directory Structure

```
WEB/
├── CUMPARLEGUME.COM/              # ✅ Wholesale buyer marketplace (lead capture)
├── CIFN.EU/                       # Company API (interjob data source)
├── CATALOG JOBURI/                # Job catalog generation engine (PDF + HTML)
├── DEPLOY_PACKAGES/               # Release archives
├── mu-plugins/                    # WordPress multisite plugins (shared)
├── V2/                            # Next-gen platform code
├── BACKUPS/                       # Archive (claude_api removal Sept 2026)
│
├── JOB DOMAINS (10 sites):
│   ├── BUILDJOBS.EU/              # Construction jobs
│   ├── CAREWORKERS.EU/            # Care & healthcare workers
│   ├── ELECTRICJOBS.EU/           # Electricians
│   ├── FACTORYJOBS.EU/            # Factory workers
│   ├── FARMWORKERS.EU/            # Agricultural workers
│   ├── HORECAWORKERS.EU/          # Hospitality workers
│   ├── INTERNALTRANSFERS.EU/      # Internal EU transfers
│   ├── MEATWORKERS.EU/            # Meat processing
│   ├── MECHANICJOBS.EU/           # Mechanics
│   └── WAREHOUSEWORKERS.EU/       # Warehouse & logistics
│
└── (Each domain has: BUILD/, DATA/, DEPLOY/, PAGES/)
```

---

## Live Domains (10 Job Sites + 1 Land Site)

| Domain | Status | WordPress | Plugins | Category | Target |
|--------|--------|-----------|---------|----------|--------|
| agroevolution.eu | Ready | n/a (land site) | n/a | Agri-land (EN) | EU buyers/investors — land catalogs, NEVER job posts |
| buildjobs.eu | Ready | /wp ✅ | 26+ | Construction | Builders, masons, carpenters |
| careworkers.eu | Ready | /wp ✅ | 26+ | Care | Nurses, elderly care, childcare |
| electricjobs.eu | Ready | /wp ✅ | 26+ | Trades | Electricians, maintenance |
| factoryjobs.eu | Ready | /wp ✅ | Core | Manufacturing | Assembly, machine ops, QA |
| farmworkers.eu | Ready | /wp ✅ | Core | Agriculture | Harvest, stable, machinery |
| horecaworkers.eu | Ready | /wp ✅ | 26+ | Hospitality | Chefs, servers, bartenders |
| internaltransfers.eu | Ready | /wp ✅ | 26+ | EU Mobility | Cross-border workers |
| meatworkers.eu | Ready | /wp ✅ | Core | Food | Slaughter, processing, butchers |
| mechanicjobs.eu | Ready | /wp ✅ | 26+ | Trades | Car, truck, heavy machinery |
| warehouseworkers.eu | Not set | /wp ❌ | Missing | Logistics | Forklift, inventory, shipping |

**Note**: All job sites except `warehouseworkers.eu` have WordPress installed and ready for job posts. `agroevolution.eu` is a land/agri site (EN), static catalogs only — no WordPress, no job posts.

---

## Core Services

### 1. Job Publisher (`/opt/ACTIVE/EVENT_PUBLISHER/wordpress_publisher.py`)
- **Pushes** jobs from ANOFM + EURES databases to WordPress sites
- **Credentials**: `wp_sites.env` with REST API tokens
- **Status**: Ready (10/11 sites configured)
- **Next**: Complete `warehouseworkers.eu` setup

### 2. Catalog Engine (`CATALOG JOBURI/`)
- Generates PDF + single-file HTML job catalogs
- **Output**: Beautiful, printable, self-contained
- **Examples**: factoryjobs.eu (PDF 5.6MB, 350 jobs)
- **Reusable scripts**: build_catalog.py (ready for 8 more domains)
- **Schedule**: Weekly PDFs for print distribution

### 3. Multisite WordPress (`mu-plugins/`)
- Shared plugins for all 10 sites
- **Security**: No claude-api (removed June 2026)
- **Stack**: Yoast SEO, Complianz GDPR, LiteSpeed Cache, UpdateDraftPlus
- **Theme**: Astra (consistent UX)

### 4. Email Orchestrator (`raspibig:/opt/ACTIVE/EMAIL/`)
- **ANOFM_ANGAJATORI** campaign: 2904 mayors
- **PRIMARII**: Cold outreach (bounce cleaning active)
- **FACTORY_RO**: 728 factories (pending approval)
- **SILOZURI**: 971 grain silos (cumparlegume.com sender)
- **Status**: 50/day gentle send, auto DNC suppression

---

## Domain Setup (Typical Pattern)

Each job domain follows this structure:

```
DOMAIN.EU/
├── BUILD/                    # Local build scripts
│   ├── build_catalog.py     # Generate PDF/HTML
│   └── config.json          # Domain settings (jobs/day, category, etc.)
├── DATA/                     # Local copy of job data
│   └── jobs_*.csv           # Latest export from DB
├── DEPLOY/                   # Deployment artifacts
│   └── catalog_*.pdf        # Generated files
├── PAGES/                    # Static landing pages (optional)
│   └── index.html           # Or served via WordPress
└── CLAUDE.md                # Domain-specific notes
```

**A2 Hosting**: Each domain deployed as `~/domain.eu/` with WordPress `/wp` subfolder.

---

## Key Features (All Sites)

✅ **SEO Ready**: Yoast XML sitemaps, structured data (Schema.org JobPosting)  
✅ **Mobile First**: Astra responsive design  
✅ **Analytics**: PostHog event tracking (apply clicks, job views)  
✅ **GDPR**: Complianz consent banner + cookie management  
✅ **Performance**: LiteSpeed cache, auto image optimization  
✅ **Security**: HTTPS enforced, no hardcoded credentials  

❌ **Missing**: Candidate chat/messaging (Phase 4)  
❌ **Missing**: Premium listings (Phase 3 feature)  
❌ **Missing**: Job alerts via SMS (future)

---

## Deployment Checklist

### Before Adding a New Domain

1. **Create folder** in WEB/ (YOURDOMAIN.EU/)
2. **DNS setup**: A record → nl1-cl8-ats1.a2hosting.com (cPanel)
3. **SSL**: Auto-provision via A2 (valid within 48h)
4. **WordPress**: Install via cPanel (Softaculous)
5. **Plugins**: Copy mu-plugins/ → wp-content/mu-plugins/
6. **Publisher**: Add credentials to wp_sites.env
7. **Catalog**: Add domain to build_catalog.py config
8. **Test**: Post 1 job manually, verify WP REST API works

**Time**: 2 hours per domain (mostly cPanel + waiting for SSL)

---

## Job Publishing Workflow

```
ANOFM/EURES DB
    ↓
raspibig:/opt/ACTIVE/DATABASE/ (enrichment + dedup)
    ↓
wordpress_publisher.py (daily 09:00 UTC)
    ↓
Send to /wp-json/wp/v2/posts via REST API
    ↓
Published → Public landing pages (domain/job/position-name-region/)
    ↓
Apply → interjob.ro/apply.html (central application form)
```

**Frequency**: Daily (ANOFM updates at 06:00 UTC)  
**Batch size**: 50-200 jobs/day per domain  
**Scope**: ANOFM (Romania) + EURES (EU-wide)

---

## Security Hardening (Completed June 2026)

✅ **Removed**: claude-api must-use plugin (RCE backdoor) from all domains  
✅ **Added**: Complianz GDPR compliance  
✅ **Enforced**: HTTPS only, no HTTP fallback  
✅ **Verified**: No hardcoded credentials in commits  
✅ **Tested**: 10/11 sites functional (warehouseworkers.eu needs setup)

---

## Content Strategy (By Vertical)

| Domain | Message | Target | Volume | Notes |
|--------|---------|--------|--------|-------|
| **buildjobs.eu** | "Build your career" | Young craftspeople | 50/day | Skills progression: apprentice → master |
| **careworkers.eu** | "Care jobs in EU" | Nurses, assistants | 40/day | Visa pathways, live-in roles |
| **electricjobs.eu** | "Certified electricians needed" | Licensed trades | 30/day | Licensing + salary highlights |
| **factoryjobs.eu** | "Factory shifts, quick pay" | Assembly workers | 80/day | Fastest hiring path |
| **farmworkers.eu** | "Seasonal & year-round farm work" | Agricultural | 60/day | Links to AgroEvolution land data |
| **horecaworkers.eu** | "Hospitality jobs across EU" | Service industry | 50/day | Visa sponsorship info |
| **internaltransfers.eu** | "Internal EU mobility" | Professionals | 30/day | Relocation packages |
| **meatworkers.eu** | "Meat industry careers" | Food processing | 40/day | Certifications + facilities |
| **mechanicjobs.eu** | "Mechanics & technicians" | Technical trades | 35/day | Salary tiers by specialization |
| **warehouseworkers.eu** | "Warehouse jobs, high pay" | Logistics | 25/day | Forklift cert → premium roles |

---

## Missing Pieces (Phase 3-4)

1. **Candidate Chat**: Real-time messaging between candidates + employers
2. **Premium Listings**: Employers pay €50-200/mo for featured jobs
3. **SMS Alerts**: Job notifications via Viber/Telegram
4. **Skill Matching**: AI ranking of candidates vs job requirements
5. **Video Profiles**: Candidates post intro videos (TikTok style)
6. **Direct Hire**: Bypass employer → direct contract with InterJob

---

## Infrastructure

| Component | Location | Status |
|-----------|----------|--------|
| **WordPress** | A2 Hosting (10 domains) | Live ✅ |
| **Job DB** | raspibig:PostgreSQL | 10K+ active ✅ |
| **Publisher** | raspibig:cron (daily) | Live ✅ |
| **Analytics** | PostHog cloud | Live ✅ |
| **Email** | raspibig:orchestrator | Live ✅ |
| **Apply form** | interjob.ro/apply.html | Live ✅ |

---

## Performance Metrics (Target)

| Metric | Current | Target |
|--------|---------|--------|
| **Homepage TTFB** | <500ms | <300ms |
| **Job listing load** | <1s | <500ms |
| **Mobile score** | 80+ | 95+ |
| **Jobs indexed** | 10K | 50K |
| **Monthly visitors** | ? | 100K |

---

## Revenue Model (Year 1)

- **Premium listings**: €50-200 per job × 100 jobs/mo = €5-20K/mo
- **Sponsor jobs**: Company logo + featured slot = €500-1000/mo
- **Candidate CV access**: €10 per view × 1000/mo = €10K/mo
- **Direct hire**: 10% fee on first month salary
- **Landing page ads**: €1-3 CPM × 1M impressions/mo = €1-3K/mo

**Year 1 target**: €360K-500K

---

## Quick Links

| Topic | Where to Read |
|-------|---------------|
| CUMPARLEGUME details | CUMPARLEGUME.COM/CLAUDE.md |
| Campaign orchestration | D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\EMAIL_CAMPAIGNS/ |
| ANOFM integration | D:\MEMORY\BUSINESS\TUDOR\INTERJOB.RO\ANOFM/ |
| Job catalog builder | CATALOG JOBURI/CLAUDE.md |
| Server status | raspibig:/opt/ACTIVE/INFRA/ |
| Database schema | D:\MEMORY\DATA\DB/ |

---

## Next 30 Days

1. **Week 1**: Complete warehouseworkers.eu setup (2h)
2. **Week 2**: Optimize job publisher for EURES (add EU job sources)
3. **Week 3**: Add premium listing CTA to all homepages
4. **Week 4**: Launch candidate CV access (pay per view model)

**Owner**: Tudor  
**Team**: Claude (infrastructure), Raspi (scrapers), PostgreSQL (data)

---

## Execution Notes

- **Do not touch**: WordPress core, Astra theme (use child themes only)
- **Always backup** before plugin updates
- **Test on staging** (domain.eu-staging.test) before live deploy
- **Monitor**: PostHog dashboard daily for anomalies
- **Escalate**: SSL renewal (30d warning), cPanel quota warnings

---

**Last updated**: 2026-06-18  
**Reviewed by**: Claude Code  
**Next review**: 2026-07-18
