---
name: press-social-distribute
description: Fan out the published press review to social channels — Facebook (Expats in Romania page, top-3 article previews + WP link + hashtags), plus Mastodon and Telegram. Best-effort, channel-independent, only runs when a live WP URL exists. Use when broadcasting the review, posting to Facebook/Mastodon/Telegram, or debugging a failed social post. Triggers: "post the review to facebook", "broadcast to social", "share on telegram/mastodon", "why didn't FB post".
---

# press-social-distribute

Stage 4 of the REVISTA PRESEI pipeline. Owned by the `social-distributor` agent.

## What this does
Amplifies the published review across social channels. Each channel is independent and best-effort — one failure never blocks the rest.

## Gate
Run ONLY when wp-publisher produced a real `wp_url` + `wp_post_id`. Posting an empty/dead link wastes reach and looks broken.

## Channels
- **Facebook** — page `102068074657345` (Expats in Romania), token from `/opt/ACTIVE/SCRAPERS/ROMANIA/data/fb_pages.json` via `load_page_tokens()`. Message = short title + top-3 `• title` / `  source` previews + WP link + `#Romania #News #Expats`. Uses `FacebookNewsPublisher`.
- **Mastodon / Telegram** — headline + WP link via the existing `mastodon_publisher.py` / `telegram_news_publisher.py`. Secondary; failures logged not fatal.

## Why best-effort
Tokens expire, APIs rate-limit. Wrap every channel in try/except, log WARN, continue. Never raise out of this stage.

## Output contract
`_workspace/04_social-distributor_result.json`: per-channel `{posted: bool, id}`. Report which channels succeeded. Skip a channel that already posted today's URL (no duplicate broadcasts).
