---
name: monitor
description: Track post-publication performance (TTFB, load time, HTTP status), generate alerts (slow pages, 404s, indexing issues), compile engagement report. Non-blocking observability.
---

# Daily Monitor Skill

## Monitoring Window
- **Start:** Immediately after publication (post_ids returned by publisher)
- **Duration:** ~5-10 seconds per post
- **Timing:** Wait ~30-60 seconds after WP POST before measuring (allow WordPress cache to settle)

## Measurements Taken

### 1. HTTP Status & Availability
```bash
curl -s -o /dev/null -w "%{http_code}\n" \
  "https://interjob.ro/piata-muncii-2026-06-23/"
```
- **Expected:** 200 (page accessible)
- **200-399:** ✅ OK
- **400-403:** ⚠️ Access issue (but recoverable, likely auth)
- **404:** ❌ CRITICAL (post not found — publish failed?)
- **500-503:** ⚠️ Server error (temporary?)

### 2. Time-to-First-Byte (TTFB)
```bash
curl -s -w "%{time_connect}\n" -o /dev/null \
  "https://interjob.ro/piata-muncii-2026-06-23/"
```
Or more accurately:
```bash
curl -s -w "TTFB: %{time_starttransfer}s\n" -o /dev/null \
  "https://interjob.ro/piata-muncii-2026-06-23/"
```
- **Expected:** < 500ms (excellent), < 1s (good)
- **500ms-1s:** ✅ OK
- **1s-2s:** ⚠️ WARN (slow)
- **> 2s:** ⚠️ WARN (very slow, check server load)
- **timeout (>5s):** ❌ CRITICAL

### 3. Full Page Load Time
```bash
curl -s -w "%{time_total}\n" -o /tmp/page.html \
  "https://interjob.ro/piata-muncii-2026-06-23/"
wc -c /tmp/page.html  # Content size
```
- **Expected:** < 2s (good), < 5s (acceptable)
- **< 2s:** ✅ OK
- **2s-5s:** ⚠️ WARN
- **> 5s:** ⚠️ WARN (performance issue)

### 4. Content Size
```bash
# Measured above via wc -c
# Expected: 8-15 KB for typical roundup article
```
- **< 5 KB:** ⚠️ Warn (may be incomplete)
- **5-20 KB:** ✅ OK
- **> 50 KB:** ⚠️ Warn (too large, slow load)

### 5. Crawlability / Indexing
```bash
curl -s -I "https://interjob.ro/piata-muncii-2026-06-23/" | \
  grep -i "x-robots-tag\|content-type"
```
- **x-robots-tag: noindex:** ❌ CRITICAL (SEO blocked!)
- **x-robots-tag: index, follow:** ✅ OK
- **No x-robots-tag:** ✅ OK (default allow)
- **content-type: text/html:** ✅ OK

### 6. Yoast SEO Status (Optional)
Query WordPress REST API for post metadata:
```bash
curl -s "https://interjob.ro/wp-json/wp/v2/posts/12345" | \
  jq '.meta._yoast_wpseo_focuskw, .meta._yoast_wpseo_metadesc'
```
- **Both present:** ✅ OK
- **One missing:** ⚠️ WARN (SEO incomplete)
- **Both missing:** ⚠️ WARN

### 7. Comment Count (Engagement)
```bash
curl -s "https://interjob.ro/wp-json/wp/v2/posts/12345" | \
  jq '.comment_count'
```
- **Expected:** 0-2 (new post)
- **Track over time** for engagement trending

## Alert Rules

| Condition | Level | Code | Action |
|-----------|-------|------|--------|
| HTTP 200 | OK | - | Continue monitoring |
| HTTP 404 | **CRITICAL** | POST_NOT_FOUND | Alert immediately; investigate WP publish |
| HTTP 5xx | **WARN** | SERVER_ERROR | Retry after 60s |
| TTFB > 2s | **WARN** | SLOW_TTFB | Check WordPress server load |
| Load time > 5s | **WARN** | SLOW_LOAD | Check network/asset delivery |
| Page size > 50KB | **WARN** | LARGE_CONTENT | Review post HTML for bloat |
| x-robots-tag: noindex | **CRITICAL** | ROBOTS_NOINDEX | Post hidden from search; urgent! |
| Yoast meta missing | **INFO** | YOAST_INCOMPLETE | SEO data incomplete, manual update needed |
| Content size < 5KB | **INFO** | SUSPICIOUSLY_SMALL | May be cache issue or post incomplete |

## Monitoring Report Output

### Success (All Green)
```
✅ Monitoring Report — 2026-06-23 09:20:00Z

[RO] piata-muncii-2026-06-23
  • URL: https://interjob.ro/piata-muncii-2026-06-23/
  • Status: 200 OK
  • TTFB: 412ms ✅
  • Load: 1.8s ✅
  • Size: 9.2 KB ✅
  • Yoast: ✅ focuskw + metadesc
  • Robots: index, follow ✅

[EN] job-market-2026-06-23
  • URL: https://interjob.ro/job-market-2026-06-23/
  • Status: 200 OK
  • TTFB: 398ms ✅
  • Load: 1.9s ✅
  • Size: 9.8 KB ✅
  • Yoast: ✅ focuskw + metadesc
  • Robots: index, follow ✅

📊 Summary: Both posts live and performing well
```

### With Warnings
```
⚠️  Monitoring Report — 2026-06-23 09:20:00Z

[RO] piata-muncii-2026-06-23
  • Status: 200 OK
  • TTFB: 2341ms ⚠️ SLOW
  • Load: 4.2s ⚠️ SLOW
  • Recommendation: Check WP server load; may need optimization

[EN] job-market-2026-06-23
  • Status: 200 OK
  • ✅ All metrics normal
```

### With Critical Alerts
```
❌ Monitoring Report — 2026-06-23 09:20:00Z

[RO] piata-muncii-2026-06-23
  • Status: 404 NOT FOUND ❌ CRITICAL
  • Action: WP publication may have failed; check WordPress admin
  • Fallback: Re-publish with --force flag

[EN] job-market-2026-06-23
  • Status: 200 OK
  • x-robots-tag: noindex ❌ CRITICAL
  • Action: Check WP SEO plugin settings; post is hidden from search
```

## Output JSON

### Success
```json
{
  "status": "monitored",
  "monitoring_timestamp": "2026-06-23T09:20:00Z",
  "results": {
    "ro": {
      "post_id": 12345,
      "url": "https://interjob.ro/piata-muncii-2026-06-23/",
      "http_status": 200,
      "metrics": {
        "ttfb_ms": 412,
        "page_load_time_ms": 1856,
        "content_size_bytes": 9156,
        "is_indexed": true,
        "comment_count": 0
      },
      "alerts": [],
      "yoast_status": "complete"
    },
    "en": {
      "post_id": 12346,
      "url": "https://interjob.ro/job-market-2026-06-23/",
      "http_status": 200,
      "metrics": {
        "ttfb_ms": 398,
        "page_load_time_ms": 1923,
        "content_size_bytes": 9856,
        "is_indexed": true,
        "comment_count": 0
      },
      "alerts": [],
      "yoast_status": "complete"
    }
  },
  "summary": "Both posts live, performing normally, fully indexed",
  "recommendations": []
}
```

### With Alerts
```json
{
  "status": "monitored_with_alerts",
  "results": {
    "ro": {
      "http_status": 200,
      "alerts": [
        {
          "level": "WARN",
          "code": "SLOW_TTFB",
          "message": "TTFB 2341ms exceeds 2s threshold"
        }
      ]
    }
  },
  "recommendations": [
    "Check WP server load (dmesg for CPU throttling)",
    "Consider enabling WordPress object cache (Redis/Memcached)"
  ]
}
```

## Non-Blocking Philosophy
Monitoring is **observability only** — if monitoring fails or returns warnings, the run is still considered successful. The articles are already published. Monitoring just helps debug performance issues after the fact.

**Why non-blocking?**
- Publishing happened successfully (orchestrator already moved on)
- Monitoring is optional observability, not a hard requirement
- We don't want to ABORT the run if monitoring has a transient failure

## Success Criteria

✅ Both posts return HTTP 200  
✅ TTFB measured (< 5s)  
✅ Page load time measured (< 10s)  
✅ No CRITICAL alerts  
✅ Yoast metadata accessible  
✅ Posts are indexed (robots allow)  
✅ Report JSON valid
