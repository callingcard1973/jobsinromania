# SEO & AEO Project — Handoff (2026-04-09)

## What Was Done Today

### Deployed (zero errors, all live)

| Action | Pages | Tool |
|--------|-------|------|
| robots.txt with AI + Chinese crawlers | 20 sites | deploy_ai_discovery.py |
| llms.txt (LLM site descriptions) | 20 sites | deploy_ai_discovery.py |
| EmploymentAgency + FAQPage + BreadcrumbList schema | 15 homepages | deploy_schema_enrichment.py |
| Visible FAQ sections (75 Q&As total) | 15 homepages | deploy_schema_enrichment.py |
| Chinese homepages (zh.html) | 15 pages | deploy_chinese_pages.py |
| Chinese subpages (/zh/ + countries + FAQ + salary + visa) | 150 pages | deploy_chinese_subpages.py |
| Cross-linking ("InterJob European Network") | 15 homepages | deploy_crosslinks.py |
| Sitemaps updated with zh URLs | 15 sitemaps | update_sitemaps.py |
| **Total** | **235 pages/files** | |

### Crawlers now in robots.txt (all 20 non-WP sites)
AI: GPTBot, ChatGPT-User, ClaudeBot, anthropic-ai, Google-Extended, PerplexityBot, Bytespider, CCBot, Applebot-Extended, cohere-ai
Chinese: Baiduspider, Sogou web spider, 360Spider, YisouSpider, ToutiaoSpider

### Research completed
- Bing indexing audit (most sites <5 pages indexed)
- Full Chinese search engine landscape (6 search engines + 10 content platforms)
- Platform registration effort evaluation (what needs Chinese entity vs not)
- 13 Chinese labor export agencies identified (3 already active in Romania)

## Files Created

All in `D:\MEMORY\SEO\`:
```
CLAUDE.md                    — Full project doc with status, research, TODO
SKILL.md                     — Skill definition for all 3 machines
HANDOFF.md                   — This file
deploy_schema_enrichment.py  — EmploymentAgency + FAQPage + BreadcrumbList
deploy_chinese_pages.py      — Chinese homepages (zh.html)
deploy_chinese_subpages.py   — Full /zh/ structure (150 pages)
deploy_crosslinks.py         — Network cross-link section
update_sitemaps.py           — Add zh URLs to sitemaps
claude.odt                   — Original brief (VentureBeat article reference)
```

Modified in `D:\MEMORY\CLAUDE\A2_SITE_DEPLOYER\`:
```
deploy_ai_discovery.py       — Added Baiduspider, Sogou, 360, Yisou, ToutiaoSpider
```

All files synced to:
- **Laptop**: `D:\MEMORY\SEO\`
- **raspibig**: `/opt/ACTIVE/INFRA/SKILLS/`
- **raspi**: `~/MEMORY/`

## What To Do Next (Manual Steps)

### Priority 1 — Bing (10 minutes, huge impact)
1. Go to webmaster.bing.com
2. Sign in with Microsoft account
3. Add all 15 job sites + seicarescu.com
4. Submit sitemaps for each
5. Enable IndexNow for instant URL submission
**Why**: ChatGPT uses Bing's index. Most sites have <5 pages indexed. This is the single highest-ROI action.

### Priority 2 — Google Search Console (15 minutes)
1. Go to search.google.com/search-console
2. Verify all domains not yet verified
3. Submit updated sitemaps (now include zh pages)
4. Check for crawl errors

### Priority 3 — Xiaohongshu Account (10 minutes)
1. Download RED app (international app stores)
2. Register with any international phone number
3. Start posting content about European jobs for Chinese workers
4. Use hashtags: #欧洲工作 #海外务工 #罗马尼亚 #欧洲招聘
**Why**: 600M daily searches, no Chinese entity needed, best reach for under-35 workers

### Priority 4 — Zhihu Account (15 minutes)
1. Go to zhihu.com/signin
2. Register with international phone
3. Verify with passport
4. Answer questions about working in Europe
5. Include links to interjob.ro/zh/
**Why**: Heavily indexed by Baidu, Q&A format perfect for recruitment

### Priority 5 — Contact Chinese Labor Agencies
**Already active in Romania — email/call directly:**

1. **辽宁恒志 (Hengzhi)** — ACTIVELY SEEKS FOREIGN PARTNERS
   - Phone: 400-881-7299
   - Email: cp126126126@126.com
   - Web: lnhzgj.com
   - Pitch: "Romanian employer network, 770+ companies, ANOFM-approved quotas, need construction/factory/hospitality workers"

2. **富联外经 (Fulian)** — ALREADY POSTING ROMANIA JOBS WEEKLY
   - Phone: 400-788-6168
   - Web: feeeee.net
   - They already know Romania — just propose partnership

3. **大连万国 (Wanguo)** — MARKETS ROMANIA EXPLICITLY
   - Web: wanguoguoji.cn
   - Branches in 6 Chinese cities

### Priority 6 — Google Rich Results Test
1. Go to search.google.com/test/rich-results
2. Test each homepage: careworkers.eu, factoryjobs.eu, etc.
3. Verify FAQPage, EmploymentAgency, BreadcrumbList schemas validate
4. Fix any errors

## Architecture Overview

```
User searches "European factory jobs" (Google/Bing/ChatGPT/Baidu)
    │
    ├─ Google/Bing → finds pages via sitemap + schema + hreflang
    ├─ ChatGPT → cites from Bing index + llms.txt
    ├─ Claude/Perplexity → reads llms.txt + crawls pages
    ├─ Baidu → finds /zh.html and /zh/* pages via meta keywords
    │
    ▼
Homepage (index.html)
    ├─ EmploymentAgency schema (org details, contact, area served)
    ├─ FAQPage schema (5 niche-specific Q&As)
    ├─ BreadcrumbList schema
    ├─ Visible FAQ section (expandable)
    ├─ Cross-link section (14 other InterJob sites)
    ├─ Telegram widget
    ├─ OG + Twitter tags
    ├─ hreflang (37 languages)
    │
    ├─ /en/, /de/, /ro/, ... (37 language subpages)
    │   └─ /en/de/, /en/nl/, ... (6 country pages per language)
    │
    └─ /zh.html (Chinese homepage)
        └─ /zh/ (language index)
            ├─ /zh/de/ — Germany (JobPosting schema)
            ├─ /zh/nl/ — Netherlands
            ├─ /zh/be/ — Belgium
            ├─ /zh/at/ — Austria
            ├─ /zh/dk/ — Denmark
            ├─ /zh/ch/ — Switzerland
            ├─ /zh/faq/ — FAQ in Chinese
            ├─ /zh/salary/ — Salary comparison
            └─ /zh/visa/ — Visa guide for Chinese workers
```

## Key Numbers
- **28 domains** in the InterJob network
- **15 job sites** with full SEO + Chinese pages
- **38 languages** (37 original + Chinese)
- **~1,200 total pages** across all job sites
- **165 Chinese pages** deployed today
- **75 FAQ entries** in English + **120 FAQ entries** in Chinese
- **6 JobPosting schemas** per site (Chinese country pages)
- **LLM conversion**: 30-40% (vs 3-4% organic)

## Verify It's Working
```bash
# Check robots.txt has AI + Chinese crawlers
curl -s https://factoryjobs.eu/robots.txt | head -40

# Check Chinese page is live
curl -s https://factoryjobs.eu/zh.html | head -5

# Check schema on homepage
curl -s https://meatworkers.eu/ | grep -o '"@type":"[^"]*"' | sort -u

# Check cross-links
curl -s https://careworkers.eu/ | grep "network-sites"

# Check sitemap has zh pages
curl -s https://factoryjobs.eu/sitemap.xml | grep zh
```
