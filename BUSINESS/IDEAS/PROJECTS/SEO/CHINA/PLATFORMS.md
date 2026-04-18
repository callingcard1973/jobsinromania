# Chinese Platform Registration Guide

## Tier 1 — Do Now (no Chinese entity needed)

### Bing Webmaster Tools
- **URL**: webmaster.bing.com
- **Effort**: 1/5
- **Requirements**: Microsoft/Google/Facebook account + site ownership verification
- **English**: Yes, full English UI
- **Why**: #2 search engine in China (~24% desktop). IndexNow for instant submission
- **IndexNow API**: `https://www.bing.com/indexnow?url=YOUR_URL&key=YOUR_KEY`
- **Bulk API**: Up to 10,000 URLs/day

### Xiaohongshu / RED (小红书)
- **URL**: xiaohongshu.com / app: "RED"
- **Effort**: 2/5 (personal) / 4/5 (Blue-V business)
- **Requirements**: Any international phone number
- **English**: No, Chinese only
- **Why**: 600M daily searches. Became China's default search for lifestyle/jobs
- **Blue-V business**: Overseas docs accepted + 600 RMB fee
- **Hashtags**: #欧洲工作 #海外务工 #罗马尼亚 #欧洲招聘

### Zhihu (知乎) — China's Quora
- **URL**: zhihu.com/signin
- **Effort**: 3/5
- **Requirements**: International phone + passport for verification
- **English**: No
- **Why**: Heavily indexed by Baidu. Q&A format perfect for recruitment
- **Note**: Enterprise accounts (机构号) need Chinese business license

### Bilibili (哔哩哔哩) — China's YouTube
- **URL**: bilibili.com
- **Effort**: 3/5
- **Requirements**: Email or international phone. Full features: email rz@bilibili.com with foreign ID docs
- **English**: Partial
- **Why**: Video content ranks in Baidu SERPs. Great for workplace/salary videos

## Tier 2 — Search Engine Webmaster Tools (limited value without ICP)

### Baidu Webmaster
- **URL**: ziyuan.baidu.com
- **Account**: register.baidu.com (overseas) or passport.baidu.com/v2/?reg&overseas=1
- **Blocker**: Chinese +86 phone number for Baidu account
- **Without ICP**: Can submit but ranking benefit minimal
- **Spider**: Baiduspider

### Sogou Webmaster
- **URL**: zhanzhang.sogou.com
- **Effort**: 4/5
- **Requirements**: Email works, but ICP needed for rankings
- **Contact**: zzpt@tencent.com
- **Also powers**: WeChat Search (搜一搜)

### 360 Search Webmaster
- **URL**: zhanzhang.so.com
- **Effort**: 4/5
- **Requirements**: Chinese phone for SMS OTP + ICP recommended
- **Share**: ~11% mobile, ~20% desktop
- **Spider**: 360Spider

### Shenma Webmaster
- **URL**: zhanzhang.sm.cn
- **Effort**: 5/5
- **Requirements**: PRC national ID (real-name verification)
- **Covers**: Shenma + Quark browser (Alibaba)
- **Spider**: YisouSpider

### Toutiao / ByteDance Webmaster
- **URL**: zhanzhang.toutiao.com
- **Effort**: 5/5
- **Requirements**: Chinese phone + business license + company seal + face recognition
- **Feature**: JS push code auto-submits URLs on page load
- **Spider**: ToutiaoSpider, Bytespider

## Tier 3 — Content Platforms (need Chinese entity/partner)

### Baijiahao (百家号) — Baidu's Content Platform
- **URL**: baijiahao.baidu.com
- **Effort**: 4/5
- **Blocker**: Baidu account needs +86 phone
- **Value**: Articles get priority ranking in Baidu SERPs
- **Workaround**: Personal account via passport.baidu.com overseas

### Weibo (微博) Official Account
- **URL**: intl.weibo.com (international portal)
- **Cost**: $1,000 USD (includes doc translation + notarization)
- **Email**: vhelper@vip.sina.com
- **Process**: 10-15 days
- **Value**: 580M users, posts indexed by Baidu

### WeChat Official Account (公众号)
- **URL**: mp.weixin.qq.com
- **Cost**: ~$99 registration
- **Requirements**: Overseas business docs through Tencent process
- **Note**: No external URL submission to WeChat Search — content must be native inside WeChat

### 58.com (五八同城) — China's Craigslist
- **URL**: 58.com
- **Effort**: 5/5
- **Blocker**: Chinese business entity required for employer posting
- **Value**: 500M users, perfect for blue-collar job listings

### Douban (豆瓣)
- **URL**: douban.com
- **Effort**: 5/5
- **Blocker**: Mainland Chinese phone mandatory since April 2022
- **Note**: Previously accessible internationally, now locked down

### Baidu Tieba (百度贴吧) — China's Reddit
- **URL**: tieba.baidu.com
- **Effort**: 5/5
- **Blocker**: Chinese phone required
- **Value**: Forum posts natively indexed by Baidu

## Key Insight

**Without ICP filing**: Baidu/Sogou/360 webmaster tool submissions produce minimal ranking benefit for foreign-hosted sites.

**Best ROI for foreign recruitment sites**:
1. Bing Webmaster (Chinese users on Bing desktop — 24% share)
2. Xiaohongshu content (600M daily searches, no ICP)
3. Zhihu answers (Baidu-indexed Q&A)
4. Bilibili videos (Baidu-indexed video)
5. Our zh.html pages (already deployed, will get organic Baidu crawls over time even without ICP)
