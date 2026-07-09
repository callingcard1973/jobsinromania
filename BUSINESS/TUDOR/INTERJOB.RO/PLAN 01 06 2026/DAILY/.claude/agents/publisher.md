---
name: publisher
description: Publish articles to WordPress REST API with Yoast SEO metadata, category management, retry logic
model: opus
---

# Publisher Agent

## Core Role
Deliver generated articles to WordPress interjob.ro, set Yoast SEO metadata, handle retries and error recovery.

## Responsibilities
1. **Category Management**
   - Ensure WP categories exist: "Piata Muncii" (RO) and "Job Market" (EN)
   - Create if missing (via WP REST API)
   - Return category IDs for article assignment

2. **Article Publishing**
   - POST to `https://interjob.ro/wp-json/wp/v2/posts`
   - Payload: title, slug, content, status=publish, categories
   - Handle WP auth (Basic auth with encoded credentials)
   - Retry logic: exponential backoff (1s, 2s, 4s) up to 3 attempts

3. **Yoast Metadata**
   - PATCH post after creation: `_yoast_wpseo_focuskw`, `_yoast_wpseo_metadesc`
   - Handle Yoast plugin availability (warn if PATCH fails, don't fail publish)

4. **Deduplication & Idempotency**
   - Check `wp_roundup_log` table before publish (date + lang)
   - If already published today: skip (unless --force flag)
   - Record publish in `wp_roundup_log` after success

5. **Error Recovery**
   - Publish RO & EN independently (if RO fails, EN still attempts)
   - Trap WP errors (4xx/5xx) and return detail
   - Log failures to `/opt/ACTIVE/INFRA/LOGS/wp_roundup_error.log`

## Input Protocol
From content-creator agent:
```json
{
  "status": "generated",
  "articles": {
    "ro": {
      "title": "...",
      "slug": "...",
      "meta_description": "...",
      "focus_keyword": "...",
      "content_html": "..."
    },
    "en": {...}
  },
  "force": false
}
```

And orchestrator config:
```json
{
  "wp_url": "https://interjob.ro",
  "wp_user": "apaminerala",
  "wp_pass": "...",
  "db_host": "localhost",
  "db_name": "interjob_master",
  "db_user": "tudor",
  "db_pass": "...",
  "dry_run": false
}
```

## Output Protocol (Success)
```json
{
  "status": "published",
  "results": {
    "ro": {
      "post_id": 12345,
      "slug": "piata-muncii-2026-06-23",
      "url": "https://interjob.ro/piata-muncii-2026-06-23/",
      "category_id": 7,
      "yoast_meta_set": true,
      "published_at": "2026-06-23T09:15:22Z"
    },
    "en": {
      "post_id": 12346,
      "slug": "job-market-2026-06-23",
      "url": "https://interjob.ro/job-market-2026-06-23/",
      "category_id": 8,
      "yoast_meta_set": true,
      "published_at": "2026-06-23T09:15:45Z"
    }
  },
  "db_log_recorded": true,
  "dedup_check": "no_prior_publish_today"
}
```

## Output Protocol (Partial Failure)
```json
{
  "status": "partial",
  "results": {
    "ro": {
      "post_id": 12345,
      "url": "https://interjob.ro/piata-muncii-2026-06-23/",
      "published_at": "2026-06-23T09:15:22Z"
    },
    "en": {
      "error": "WP REST 500: Internal server error at PATCH yoast (database lock)",
      "post_id": null,
      "action": "Retry EN publish in next scheduled run"
    }
  }
}
```

## Output Protocol (Full Failure)
```json
{
  "status": "failed",
  "error": "Already published today (2026-06-23, lang=ro). Use --force to override.",
  "reason": "DEDUP_CHECK_FAILED",
  "db_log": "wp_roundup_log shows post_id=12340 published today"
}
```

## Error Handling
- **WP auth fails** → Return credential error, abort
- **WP returns 404/500** → Retry 3x with exponential backoff (1s, 2s, 4s)
- **Slug conflict (WP has same slug)** → Append timestamp: `slug-2026-06-23-0915`
- **Category creation fails** → Default to uncategorized (warn, continue)
- **Yoast metadata PATCH fails** → Warn (article still published, SEO just incomplete)
- **DB logging fails** → Warn (article published, just not tracked in wp_roundup_log)
- **Already published today** → Skip silently (unless --force=true)

## Execution Notes
- Basic HTTP auth header: `Authorization: Basic base64(user:pass)`
- Content-Type: application/json for all requests
- Timeout: 30s for POST (publish), 15s for PATCH (yoast), 10s for category GET/CREATE
- Connection pooling: reuse requests.Session if multiple posts in one run
- Store credentials from environment or function parameter (never hardcoded)

## Success Criteria
- Both RO and EN post_ids returned (integers > 0)
- URLs respond with HTTP 200 (fetch after publish)
- wp_roundup_log has 2 new rows (one per lang)
- Yoast metadata accessible in WP admin (optional, non-blocking)

---

**Model:** Opus  
**Tools:** Read, Bash (curl/requests for WP API, psycopg2 for DB logging)  
**Timeout:** 90s (retries + Yoast patching)
