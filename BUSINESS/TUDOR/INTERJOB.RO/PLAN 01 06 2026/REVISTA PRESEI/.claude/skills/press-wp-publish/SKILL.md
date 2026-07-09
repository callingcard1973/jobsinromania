---
name: press-wp-publish
description: Publish the daily press review to expatsinromania.org WordPress (ensure "Press Review" category, post via REST), persist to press_review_posts + press_review_articles, build the RSS 2.0 feed (last 30 reviews) and deploy feed.xml to A2 via cPanel. Use when publishing the review, posting to WP, deploying the RSS feed, or debugging a missing/duplicate post. Triggers: "publish the press review", "post to expatsinromania", "deploy the RSS feed", "why didn't the review publish".
---

# press-wp-publish

Stage 3 of the REVISTA PRESEI pipeline. Owned by the `wp-publisher` agent.

## What this does
Idempotent daily publish: WP post → DB persist → RSS feed build + cPanel deploy.

## Why idempotency
`already_posted(today)` gates the whole run. Re-running must NOT create a second post for the same `review_date` — honor the gate. Re-publish requires an explicit `--force` (code edit).

## Steps
1. `already_posted(today)` → skip if present (report existing URL).
2. WP auth = Basic base64(`WP_EXPATSINROMANIA_ORG_USER`:`WP_EXPATSINROMANIA_ORG_PASS`) from `wp_sites.env`. Missing pass → skip WP, still persist DB.
3. `wp_ensure_category("Press Review")` (slug `press-review`).
4. POST `/wp-json/wp/v2/posts` (status publish, Content-Type application/json).
5. Persist `press_review_articles` (executemany, ON CONFLICT DO NOTHING) + `press_review_posts`.
6. Build RSS 2.0 from last 30 reviews → `/tmp/press_review_feed.xml`.
7. Deploy via cPanel UAPI `Fileman/save_file_content` to `/home/loaiidil/expatsinromania.org/press-review/feed.xml`.

## A2 cPanel gotchas
- Send JSON `Content-Type: application/json` (openresty 415 otherwise).
- loaiidil sits behind Imunify360 — automation IP must be whitelisted (86.126.144.222 via cPanel UI). Account also runs near 100% disk quota.
- cPanel upload is flaky and NON-critical: feed exists locally, manual retry is fine. Log WARN and continue.

## Debug: why didn't it publish?
```bash
# WP creds present?
plink -batch -pw 'REDACTED' tudor@192.168.100.21 "grep EXPATSINROMANIA /opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED/wp_sites.env"
# WP reachable?
curl -s https://expatsinromania.org/wp-json/wp/v2/categories | head -20
# Log:
plink -batch -pw 'REDACTED' tudor@192.168.100.21 "tail -40 /opt/ACTIVE/INFRA/LOGS/press_review.log"
```

## Output contract
`_workspace/03_wp-publisher_result.json`: `{wp_post_id, wp_url, rss_deployed}`. Report the live URL. Only signal social-distributor when wp_url + wp_post_id both exist.
