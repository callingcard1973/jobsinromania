---
name: daily-publisher
description: Publish RO+EN articles to WordPress REST API with Yoast SEO metadata, category management, retry logic, deduplication checks. Handles WP auth, error recovery, logging.
---

# Daily Publisher Skill

## Prerequisites

- WordPress site: https://interjob.ro
- REST API enabled (should be default in modern WP)
- Yoast SEO plugin installed (for metadata patching)
- Admin credentials: WP_USER, WP_PASS (from environment or config)
- Database: interjob_master on localhost with wp_roundup_log table (created by data-validator if missing)

## Authorization Setup

### WordPress Basic Auth
```bash
# Get credentials from environment
export WP_INTERJOB_USER="apaminerala"
export WP_INTERJOB_PASS="<password_from_wp_sites.env>"

# Test endpoint
curl -u "${WP_INTERJOB_USER}:${WP_INTERJOB_PASS}" \
  "https://interjob.ro/wp-json/wp/v2/users/me"
```

### HTTP Headers
```python
import base64

def get_auth_header(user, password):
    credentials = f"{user}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {
        "Authorization": f"Basic {encoded}",
        "Content-Type": "application/json"
    }
```

## Pre-Publish Checks

### 1. Deduplication Check
**Query:** Has this language already been published today?
```bash
psql -h localhost -U tudor -d interjob_master -c "
SELECT post_id FROM wp_roundup_log 
WHERE roundup_date = CURRENT_DATE AND lang = 'ro';"
```
- If exists: **Skip publish** (unless --force flag passed)
- If not exists: **Proceed to publish**

### 2. Category Existence
```bash
curl -s -u "$WP_USER:$WP_PASS" \
  "https://interjob.ro/wp-json/wp/v2/categories?search=Piata%20Muncii"
```
- If found: Use existing category ID
- If not found: Create category via POST

## Publishing Flow

### Step 1: Ensure Categories Exist
```bash
# GET existing categories
curl -s -u "$WP_USER:$WP_PASS" \
  "https://interjob.ro/wp-json/wp/v2/categories?search=Piata%20Muncii" \
  | jq '.[0].id'

# If empty, CREATE category
curl -s -u "$WP_USER:$WP_PASS" -X POST \
  "https://interjob.ro/wp-json/wp/v2/categories" \
  -H "Content-Type: application/json" \
  -d '{"name": "Piata Muncii", "slug": "piata-muncii"}'
```

### Step 2: Publish RO Article
```bash
curl -s -u "$WP_USER:$WP_PASS" -X POST \
  "https://interjob.ro/wp-json/wp/v2/posts" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Piața muncii 23 iunie 2026: 5,795 locuri de muncă în România și Europa",
    "slug": "piata-muncii-2026-06-23",
    "content": "<p>Azi, 23 iunie 2026...</p>...",
    "status": "publish",
    "categories": [7]
  }' | jq '.id'
```
- **Expected response:** JSON with `"id": 12345` (the post_id)
- **Status codes:**
  - 201 Created: Success
  - 400 Bad Request: Slug conflict or validation error
  - 401 Unauthorized: Auth failed
  - 500 Internal Server Error: WP crash (retry)

### Step 3: Retry Logic (Exponential Backoff)
```python
def publish_with_retry(url, headers, payload, max_retries=3):
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code in [200, 201]:
                return response.json().get("id")
            elif response.status_code in [500, 502, 503]:
                wait = 2 ** attempt  # 1s, 2s, 4s
                time.sleep(wait)
                continue
            else:
                return None  # 4xx errors don't retry
        except requests.Timeout:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return None
    return None
```

### Step 4: Slug Conflict Handling
If WordPress returns 400 with "slug already exists":
```python
# Append timestamp to slug
original_slug = "piata-muncii-2026-06-23"
new_slug = f"{original_slug}-0923"  # -HHMM timestamp
```

### Step 5: Yoast Metadata Patching
After article is published, immediately PATCH metadata:
```bash
curl -s -u "$WP_USER:$WP_PASS" -X POST \
  "https://interjob.ro/wp-json/wp/v2/posts/12345" \
  -H "Content-Type: application/json" \
  -d '{
    "meta": {
      "_yoast_wpseo_focuskw": "locuri de munca 23 iunie 2026",
      "_yoast_wpseo_metadesc": "Piața muncii 23 iunie 2026: 5,795 posturi active..."
    }
  }'
```
- **Expected response:** 200 OK
- **If fails (404/403):** Warn but don't fail (article already published, SEO just incomplete)

### Step 6: Record in wp_roundup_log
```bash
psql -h localhost -U tudor -d interjob_master -c "
INSERT INTO wp_roundup_log (roundup_date, lang, wp_post_id) 
VALUES (CURRENT_DATE, 'ro', 12345)
ON CONFLICT DO NOTHING;"
```
- **Purpose:** Track which posts were published today, enable deduplication

## Error Scenarios

| Error | HTTP | Recovery | Action |
|-------|------|----------|--------|
| WP auth invalid | 401 | Don't retry | Return credential error, ABORT |
| WP server error | 500 | Retry 3x (1s, 2s, 4s) | If persists: WARN, skip that article |
| Slug already exists | 400 | Append timestamp | Retry with new slug |
| EURES CSV missing | - | N/A | Publisher still publishes RO; EN skipped |
| DB logging fails | - | Non-blocking | Article published, warn "not tracked in log" |
| Yoast PATCH fails | 404/403 | Non-blocking | Article published, warn "Yoast metadata incomplete" |

## Logging

### Success Case
```
✅ [RO] Published post_id=12345
   URL: https://interjob.ro/piata-muncii-2026-06-23/
   Yoast: ✅ focuskw + metadesc set
   DB log: ✅ recorded in wp_roundup_log

✅ [EN] Published post_id=12346
   URL: https://interjob.ro/job-market-2026-06-23/
   Yoast: ✅ focuskw + metadesc set
   DB log: ✅ recorded in wp_roundup_log
```

### Partial Failure
```
✅ [RO] Published post_id=12345
⚠️  [EN] WP returned 500 on first POST attempt, retrying...
   Attempt 2 (2s): 500 again
   Attempt 3 (4s): 201 Created, post_id=12346
   Yoast: ⚠️  PATCH failed (403), article published without SEO metadata
```

### Full Failure
```
❌ [ABORT] Already published today (lang=ro)
   wp_roundup_log shows post_id=12340 published on 2026-06-23
   Action: Use --force flag to override, or check if today's run already completed
```

## Output JSON

### Success
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
  "db_log_recorded": true
}
```

### Partial Failure
```json
{
  "status": "partial",
  "results": {
    "ro": {
      "post_id": 12345,
      "published_at": "2026-06-23T09:15:22Z"
    },
    "en": {
      "post_id": null,
      "error": "WP PATCH yoast failed (403), article published without SEO metadata",
      "action": "Article accessible; SEO incomplete. Manually update Yoast in WP admin."
    }
  }
}
```

## Success Criteria

✅ Both RO and EN post_ids returned (integers > 0)  
✅ URLs accessible (HTTP 200 when fetched)  
✅ Both rows inserted in wp_roundup_log  
✅ Yoast metadata set (or warned if missing)  
✅ No WP errors remaining (4xx/5xx resolved or acceptable)
