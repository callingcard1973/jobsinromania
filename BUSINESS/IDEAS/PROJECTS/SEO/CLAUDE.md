# SEO & AEO Project

## Goal
Optimize all 28 InterJob domains + seicarescu.com for SEO, AEO (Answer Engine Optimization), and Chinese search engines. LLM-referred traffic converts at 30-40% (10x organic). Also target Chinese worker recruitment to Romania via Baidu/Sogou/WeChat.

## Completed (2026-04-09)

### Phase 1: AI Discovery ✅
- **robots.txt** with AI bot rules (GPTBot, ClaudeBot, PerplexityBot, Google-Extended, etc.) deployed on ALL 20 non-WP sites
- **llms.txt** deployed on all 20 non-WP sites
- **Tool**: `A2_SITE_DEPLOYER/deploy_ai_discovery.py`

### Phase 2: Schema Enrichment ✅
- **EmploymentAgency schema** on all 15 job site homepages (full org details, contactPoint, areaServed, knowsAbout)
- **FAQPage schema** on all 15 job sites (5 niche-specific Q&As each = 75 total FAQ entries)
- **BreadcrumbList schema** on all 15 job sites
- **Visible FAQ sections** with expandable Q&As injected before footer on all 15 homepages
- **Tool**: `SEO/deploy_schema_enrichment.py`

### Phase 3: Chinese / Baidu SEO ✅
- **Baiduspider + Sogou + 360 + Yisou** added to robots.txt on all 20 sites
- **15 Chinese homepages** (zh.html) deployed — full niche content, FAQ schema, EmploymentAgency schema
- **150 Chinese subpages** deployed across 15 sites:
  - `/zh/` language index (country selection)
  - `/zh/de/`, `/zh/nl/`, `/zh/be/`, `/zh/at/`, `/zh/dk/`, `/zh/ch/` — 6 country pages with JobPosting schema
  - `/zh/faq/` — 8 Q&As in Chinese
  - `/zh/salary/` — salary comparison table (all 6 countries)
  - `/zh/visa/` — Chinese worker visa guide with document checklist
- **All sitemaps updated** with 10 Chinese URLs each
- **Meta keywords** (Baidu-specific) on all Chinese pages: 罗马尼亚工作, 欧洲招聘, 海外务工, etc.
- **No Google dependencies** on Chinese pages (no Google Fonts/Analytics/reCAPTCHA)
- **Tools**: `SEO/deploy_chinese_pages.py`, `SEO/deploy_chinese_subpages.py`, `SEO/update_sitemaps.py`

### Phase 4: Cross-linking ✅
- **"InterJob European Network"** section injected on all 15 job site homepages
- Dark-themed grid with cards linking to all 14 other sites (excludes self)
- Responsive, mobile-friendly, with hover effects
- **Tool**: `SEO/deploy_crosslinks.py`

### Previously Done
- **SEO injection** via `A2_SITE_DEPLOYER/seo_deploy.py` — JSON-LD WebPage, hreflang (37 langs), OG tags, Twitter Cards, canonical URLs
- **Telegram widgets** on all job sites
- **Sitemaps** on all sites (careworkers 69+10zh, factoryjobs 66+10zh, interjob 640+10zh pages)
- **seicarescu.com**: Yoast SEO, AI bots in robots.txt, Organization schema
- **interjob.ro**: Full AI bot rules, Organization+SearchAction+WebPage schema

## Tools

| Script | Location | What It Does |
|--------|----------|-------------|
| `deploy_ai_discovery.py` | `A2_SITE_DEPLOYER/` | robots.txt (AI+Chinese crawlers) + llms.txt to all 20 non-WP sites |
| `seo_deploy.py` | `A2_SITE_DEPLOYER/` | JSON-LD, hreflang, OG, Twitter, canonical into HTML. Local+remote modes |
| `deploy_schema_enrichment.py` | `SEO/` | EmploymentAgency + FAQPage + BreadcrumbList + visible FAQ on 15 job sites |
| `deploy_chinese_pages.py` | `SEO/` | Chinese homepage (zh.html) with FAQ+Org schema for each job site |
| `deploy_chinese_subpages.py` | `SEO/` | Full zh/ structure: index + 6 countries + FAQ + salary + visa (150 pages) |
| `deploy_crosslinks.py` | `SEO/` | "InterJob European Network" cross-link section on all 15 homepages |
| `update_sitemaps.py` | `SEO/` | Add Chinese page URLs to all 15 sitemaps |

All use cPanel API (token `MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U`, user `loaiidil`).

Skill file: `SEO/SKILL.md` — also deployed to raspibig (`/opt/ACTIVE/INFRA/SKILLS/`) and raspi (`~/MEMORY/`).

## Bing Indexing Audit (2026-04-09)

Most sites have very low Bing coverage (ChatGPT uses Bing):

| Domain | Bing Pages | Notes |
|--------|-----------|-------|
| factoryjobs.eu | 5 | Best — homepage, apply, visa, salary |
| seicarescu.com | 3 | Includes a PDF |
| careworkers.eu | 2 | |
| buildjobs.eu | 1 | |
| interjob.ro | 1 | Only blog, not homepage — possible canonical issue |
| horecaworkers.eu | 1 | |
| electricjobs.eu | 0 | NOT INDEXED AT ALL |

**Action needed**: Register ALL sites in Bing Webmaster Tools, submit sitemaps.

## China SEO Research (2026-04-09)

### Key Findings
- **ICP filing NOT required** for foreign sites — Baidu indexes foreign-hosted sites without ICP
- **Baidu still uses meta keywords** (unlike Google) — add `<meta name="keywords">` with Chinese terms
- **No Chinese server needed** — use Hong Kong/Singapore CDN nodes (no ICP required, good China speeds)
- **Great Firewall blocks**: Google Fonts, Google Analytics, reCAPTCHA, YouTube — must replace with local alternatives on zh-CN pages
- **Baidu spider**: `Baiduspider` user agent — add to robots.txt
- **Static HTML preferred** — Baidu indexes JS-heavy SPAs poorly (our static sites are ideal)

### Chinese Search Engines — Full List

**Tier 1: Webmaster tools, no Chinese entity needed**
| Engine | Webmaster URL | Share | Notes |
|--------|-------------|-------|-------|
| Baidu | ziyuan.baidu.com | ~60% | Need Baidu account (Chinese phone or overseas reg at register.baidu.com) |
| Bing China | webmaster.bing.com | ~24% desktop | Easiest — global Bing WMT works. IndexNow for instant submission |
| 360 Search | zhanzhang.so.com | ~11-20% | Sitemap + URL submission, spider visits within 24h |
| Sogou | zhanzhang.sogou.com | ~8% | Also powers WeChat Search (搜一搜) |
| Shenma | zhanzhang.sm.cn | ~3% (600M UC users) | Covers Quark browser too. Email only, no phone needed |
| Toutiao | zhanzhang.toutiao.com | 300M daily | ByteDance. JS push code auto-submits URLs on page load |

**Tier 2: Content platforms that rank in Baidu SERPs (no Chinese entity)**
| Platform | URL | What To Do |
|----------|-----|-----------|
| Zhihu (知乎) | zhihu.com | Post answers about EU jobs. International phone OK. Heavily indexed by Baidu |
| Douban (豆瓣) | douban.com | Post content with links. Email registration, no Chinese phone |
| Baijiahao (百家号) | baijiahao.baidu.com | Baidu's own content platform. Personal account via overseas Baidu account |
| 58.com (五八同城) | 58.com | China's Craigslist — post blue-collar job listings. Foreign email works |
| Xiaohongshu (RED) | xiaohongshu.com | 600M daily searches. Personal account works internationally |
| Bilibili (哔哩哔哩) | bilibili.com | China's YouTube. Video content ranks in Baidu. Overseas phone OK |

**Tier 3: Requires Chinese entity or agency partner**
| Platform | Cost | Notes |
|----------|------|-------|
| Weibo Official | $1,000 USD | 580M users, Baidu-indexed. Via intl.weibo.com |
| WeChat Official Account | ~$99 | Content indexed by WeChat Search + Sogou |
| Zhaopin (智联招聘) | — | Top 3 job board, 180M users. Chinese entity required |
| 51job (前程无忧) | — | Pioneer job board. Chinese entity required |
| BOSS Zhipin (BOSS直聘) | — | Largest by MAU. Chinese entity required |
| Liepin (猎聘) | — | Executive/premium. Chinese entity required |
| Baidu Tieba (贴吧) | — | China's Reddit. Chinese phone required |

**Not accessible / domestic only:**
- WeChat Search: no external URL submission (content must live inside WeChat)
- 12333.gov.cn: domestic China employers only
- 国聘 (iguopin.com): SOE-only
- MOFCOM labor portal: for Chinese companies sending workers abroad

### Platform Registration Effort (Foreign Company)

**Easy (do now):**
| Platform | Effort | Requirements |
|----------|--------|-------------|
| Bing Webmaster | 1/5 | Microsoft account. Full English. Done in 5 min |
| Xiaohongshu (personal) | 2/5 | Any international phone. Good reach for job content |
| Zhihu | 3/5 | International phone + passport for verification |
| Bilibili | 3/5 | Email + send ID docs by email for full features |

**Hard (needs workaround/partner):**
| Platform | Effort | Blocker |
|----------|--------|---------|
| Sogou Webmaster | 4/5 | Email works but ICP needed for rankings |
| 360 Webmaster | 4/5 | Chinese phone + ICP for ranking benefit |
| Baijiahao | 4/5 | Baidu account needs Chinese +86 phone |
| Xiaohongshu Blue-V | 4/5 | Overseas docs accepted, 600 RMB fee |

**Requires Chinese entity:**
| Platform | Effort | Blocker |
|----------|--------|---------|
| 58.com | 5/5 | Chinese business entity required |
| Shenma | 5/5 | PRC national ID required |
| Toutiao | 5/5 | Face recognition + company seal |
| Douban | 5/5 | Mainland phone mandatory since 2022 |

**Key insight**: Without ICP filing, Baidu/Sogou/360 webmaster submissions produce minimal ranking benefit. Best ROI for foreign sites: Bing (indexes Chinese users) + Xiaohongshu/Zhihu/Bilibili (social, no ICP needed).

### Chinese Labor Export Agencies — ACTIVE FOR ROMANIA

**Top 3 partners (already send workers to Romania):**

1. **富联外经 (Fulian)** — feeeee.net — Dalian. 400-788-6168
   - ACTIVE Romania: chefs 13-15K RMB/mo, factory 10-12K, lumber 8-9K
   - Weekly Romania postings. Also DE, DK, PL, SK
   - Has WeChat/Douyin. Inquiry form on site

2. **大连万国 (Dalian Wanguo)** — wanguoguoji.cn — Dalian
   - Explicitly markets Romania ("5 years = Romanian green card")
   - Construction + multiple sectors
   - Branches: Dalian, Harbin, Qingdao, Beijing, Wuxi, Hefei

3. **辽宁恒志 (Liaoning Hengzhi)** — lnhzgj.com — Shenyang. 400-881-7299
   - Lists Romania + 12 EU countries. Construction, manufacturing, hospitality
   - **Actively seeks foreign partnerships** — offers resource sharing + MOFCOM credentials
   - Email: cp126126126@126.com

**Other agencies with EU reach:**

4. **山东亿泰 (Shandong Yitai)** — shandongyitai.com — Shouguang. 0536-5507888
   - NL, PL, DE, FI, NO, DK, CH, ES, UK, IT. Construction + manufacturing
   - Active since 2007, 30M RMB capital

5. **四川外联 (CSFECO)** — csfeco.com — Chengdu. +86-28-86640299
   - DE, SE, HU. 15,000+ workers dispatched. 30+ industries

6. **中国国际劳务网 (gjlw.cn)** — Aggregator platform
   - Multiple agencies listing Romania/Hungary/Serbia construction jobs
   - HU railway project: 120 workers, 13K+ RMB/month

7. **好出国 (haochuguo.com)** — Aggregator
   - Romania section: haochuguo.com/country/726-330.html
   - Construction 15-18K RMB/month, meals+housing included

**CHINCA contact** (association referrals): +86 10-8113-0071, chinca.org

### Chinese Worker → Romania Pipeline
- **No bilateral labor agreement** — standard work visa required
- **Process**: Employer gets work permit from IGI → worker applies at Romanian embassy (Beijing/Shanghai)
- **Romania has annual non-EU worker quotas** — Chinese compete within this
- **MOFCOM route**: ~2,000 licensed agencies. Registry at chinca.org
- **Best approach**: Contact Fulian (feeeee.net) or Hengzhi (lnhzgj.com) — already active in Romania
- **Key Chinese search terms**: 罗马尼亚工作, 欧洲招聘, 海外务工

## TODO

### Immediate (manual steps needed)
- [ ] **Bing Webmaster Tools** — register all 15 job sites + seicarescu.com (CRITICAL — most sites <5 pages indexed, ChatGPT uses Bing)
- [ ] **Google Search Console** — verify all domains, submit updated sitemaps
- [ ] **Google Rich Results Test** — validate schema on all 15 homepages
- [ ] **Fix interjob.ro Bing canonical issue** — homepage not indexed, only blog
- [x] ~~Cross-linking~~ DONE — "InterJob European Network" section on all 15 homepages
- [x] ~~Add Baiduspider~~ DONE — all 20 sites have Baidu/Sogou/360/Yisou in robots.txt

### China / Baidu (manual steps needed)
**Search engine registration (Tier 1 — do first):**
- [ ] **Bing Webmaster + IndexNow** — webmaster.bing.com — easiest, #2 in China
- [ ] **Baidu account** — register at register.baidu.com (overseas), then ziyuan.baidu.com
- [ ] **360 Webmaster** — zhanzhang.so.com — submit sitemaps
- [ ] **Sogou Webmaster** — zhanzhang.sogou.com — also powers WeChat Search
- [ ] **Shenma Webmaster** — zhanzhang.sm.cn — covers Quark too, email only
- [ ] **Toutiao Webmaster** — zhanzhang.toutiao.com — get JS push code for auto-submission

**Content platforms (Tier 2 — high SEO value):**
- [ ] **Zhihu account** — post answers about EU jobs for Chinese workers
- [ ] **58.com listings** — post blue-collar job listings (foreign email works)
- [ ] **Xiaohongshu personal account** — post EU work/life content
- [ ] **Baijiahao personal account** — via overseas Baidu account, content ranked by Baidu
- [ ] **Bilibili** — create recruitment videos about EU workplaces/salaries

**Business setup (Tier 3 — use agency):**
- [ ] **Partner with MOFCOM-licensed labor agency** — chinca.org registry (~2,000 companies)
- [ ] **Weibo Official Account** — $1,000 via intl.weibo.com
- [ ] **WeChat Service Account** — ~$99, for content distribution
- [ ] **Singapore/HK CDN** — Alibaba Cloud or Tencent Cloud (no ICP needed)

**Already done:**
- [x] ~~zh-CN pages~~ — 165 pages (15 homepages + 150 subpages)
- [x] ~~Chinese meta keywords~~ — Baidu-optimized on all zh pages
- [x] ~~Remove Google deps~~ — zero Google deps on any zh page
- [x] ~~Sitemaps updated~~ — all 15 sitemaps include zh pages
- [x] ~~Baiduspider + Sogou + 360 + Yisou~~ — in robots.txt on all 20 sites

### Content & Authority
- [ ] **Topical authority articles** — 10-15 deep guides on EU labor mobility (English + Chinese)
- [ ] **Person schema** on seicarescu.com — bio, expertise, linked entities
- [ ] **Wikipedia/Wikidata** — create InterJob entity if eligible
- [ ] **seicarescu.com OG tags** — add via Yoast (currently missing)
- [ ] **cifn.info SEO** — fix 6/44 indexed pages, dedup posts

### Technical
- [ ] **CloudFlare CDN** — all 28 domains
- [ ] **Core Web Vitals** — audit LCP, CLS, FID
- [ ] **AI crawler analytics** — parse server logs for GPTBot, ClaudeBot, PerplexityBot, Baiduspider
- [ ] **JobPosting schema** — individual job listing pages (not just homepage)

## Site Inventory

### Job Sites (15) — 37 languages + Chinese, 6 countries
| Domain | Pages | zh Pages | Schema | Crosslinks | AI bots | Baidu |
|--------|-------|----------|--------|------------|---------|-------|
| careworkers.eu | 69+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| factoryjobs.eu | 66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| buildjobs.eu | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| electricjobs.eu | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| farmworkers.eu | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| horecaworkers.eu | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| meatworkers.eu | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| mechanicjobs.eu | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| warehouseworkers.eu | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| aluminumrecyclehub.com | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| expatsinromania.org | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| interjob.ro | 640+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| mivromania.info | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| mivromania.online | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |
| nepalezi.com | ~66+11 | ✅ 11 | EmploymentAgency+FAQ+JobPosting | ✅ | ✅ | ✅ |

### Static Sites (5) — AI discovery deployed
internaltransfers.eu, horecaworkers2026.com/.eu/.online, weddnesday.org

### WordPress Sites (8) — WP plugins
seicarescu.com (Yoast), cumparlegume.com, agroevolution.com, ajwang.org, baneasa39.com, cifn.info, haritina.com, mivromania.com

## Conventions
- WordPress SEO: Yoast/RankMath plugins, not manual injection
- Static sites: seo_deploy.py for HTML injection
- AI discovery: deploy_ai_discovery.py for robots.txt + llms.txt
- Schema enrichment: deploy_schema_enrichment.py for homepage schemas
- Never use cPanel `edit_zone_record` — always delete+add
- All apply links → `https://interjob.ro/apply.html`
- Chinese pages: use zh-CN (simplified), not zh-TW
