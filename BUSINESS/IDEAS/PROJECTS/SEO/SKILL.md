---
name: seo-aeo-deploy
description: Deploy SEO, AEO (Answer Engine Optimization), and Chinese Baidu SEO across all 28 InterJob domains. Use when the user wants to update robots.txt, llms.txt, Schema.org, Chinese pages, FAQ sections, cross-linking, sitemaps, or any SEO/AEO/China optimization. Covers Google, Bing, Baidu, Sogou, 360, Toutiao, and AI crawlers (GPTBot, ClaudeBot, PerplexityBot).
---

# SEO & AEO Deploy Skill

## Purpose

Full SEO/AEO/China management for the InterJob European Recruitment Network — 28 domains, 38 languages (37 + Chinese), targeting Google, Bing, Baidu, and AI engines.

## When to Use

- Update SEO, schema, robots.txt, llms.txt, sitemaps
- Deploy or update Chinese/Baidu pages
- Add FAQ sections or structured data
- Update cross-linking between domains
- Mention Bing, Baidu, Google indexing, AI crawler optimization
- Chinese worker recruitment to Romania/EU

## Scripts (all in `D:\MEMORY\SEO\` or `/opt/ACTIVE/INFRA/SKILLS/`)

| Script | What | Pages |
|--------|------|-------|
| `deploy_chinese_pages.py` | Chinese homepage (zh.html) per job site | 15 |
| `deploy_chinese_subpages.py` | Full /zh/ structure: index + 6 countries + FAQ + salary + visa | 150 |
| `deploy_schema_enrichment.py` | EmploymentAgency + FAQPage + BreadcrumbList on homepages | 15 |
| `deploy_crosslinks.py` | "InterJob European Network" cross-link section | 15 |
| `update_sitemaps.py` | Add Chinese URLs to all sitemaps | 15 |

Also in `D:\MEMORY\CLAUDE\A2_SITE_DEPLOYER\`:
| Script | What |
|--------|------|
| `deploy_ai_discovery.py` | robots.txt (AI + Chinese crawlers) + llms.txt on 20 non-WP sites |
| `seo_deploy.py` | JSON-LD, hreflang, OG, Twitter, canonical on all HTML pages |

## Full Deployment

```bash
# 1. AI + Chinese crawlers in robots.txt + llms.txt
cd D:/MEMORY/CLAUDE/A2_SITE_DEPLOYER && python deploy_ai_discovery.py

# 2. SEO injection (hreflang, OG, schema)
python seo_deploy.py

# 3. Schema enrichment (EmploymentAgency, FAQ, Breadcrumb)
cd D:/MEMORY/SEO && python deploy_schema_enrichment.py

# 4. Chinese homepages (15 pages)
python deploy_chinese_pages.py

# 5. Chinese subpages (150 pages)
python deploy_chinese_subpages.py

# 6. Cross-linking (15 homepages)
python deploy_crosslinks.py

# 7. Update sitemaps with zh pages
python update_sitemaps.py
```

Single site: `python <script>.py factoryjobs.eu`

## Crawlers in robots.txt

**AI**: GPTBot, ChatGPT-User, ClaudeBot, anthropic-ai, Google-Extended, PerplexityBot, Bytespider, CCBot, Applebot-Extended, cohere-ai
**Chinese**: Baiduspider, Sogou web spider, 360Spider, YisouSpider, ToutiaoSpider

## Chinese Platform Registration Priority

**Do now (no Chinese entity needed):**
1. **Bing Webmaster** (webmaster.bing.com) — effort 1/5, Microsoft account
2. **Xiaohongshu** (xiaohongshu.com) — effort 2/5, international phone
3. **Zhihu** (zhihu.com) — effort 3/5, international phone + passport
4. **Bilibili** (bilibili.com) — effort 3/5, email + ID docs

**With partner/agency:**
5. Sogou (zhanzhang.sogou.com), 360 (zhanzhang.so.com), Baijiahao (baijiahao.baidu.com)

**Requires Chinese entity:** 58.com, Shenma, Toutiao, Douban

## Chinese Labor Agencies (Already Active in Romania)

| Agency | Website | Phone | Countries |
|--------|---------|-------|-----------|
| 富联外经 (Fulian) | feeeee.net | 400-788-6168 | RO, DE, DK, PL, SK |
| 大连万国 (Wanguo) | wanguoguoji.cn | — | RO explicitly |
| 辽宁恒志 (Hengzhi) | lnhzgj.com | 400-881-7299 | RO + 12 EU countries |
| 山东亿泰 (Yitai) | shandongyitai.com | 0536-5507888 | NL, PL, DE, FI, NO |
| gjlw.cn | gjlw.cn | — | Aggregator, RO/HU/RS |
| haochuguo.com | haochuguo.com | — | Aggregator, RO section |
| CHINCA | chinca.org | +86-10-8113-0071 | Association referrals |

## cPanel Access
- Host: nl1-cl8-ats1.a2hosting.com:2083
- User: loaiidil
- Token: MK0WQEH59KHVXQ8JRKKZ26LVSMT4LI7U
- Docroot: ~/domainname/ (warehouseworkers.eu → ~/public_html/warehouseworkers.eu)

## Key Facts
- LLM traffic converts 30-40% (10x organic)
- Bing feeds ChatGPT — most sites have <5 pages indexed
- ICP NOT required for Baidu indexing of foreign sites
- Without ICP, Baidu/Sogou/360 ranking benefit is minimal — best ROI is Bing + social platforms
- Chinese pages: no Google Fonts/Analytics/reCAPTCHA (Great Firewall)
- Baidu still uses `<meta name="keywords">` (unlike Google)
- Static HTML preferred by Baidu (our sites are ideal)
