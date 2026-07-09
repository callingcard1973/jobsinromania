---
name: press-rss-fetch
description: Fetch and classify the daily Romania press-review RSS feeds (10 RO/EN sources), strip invalid XML, dedup by URL hash, classify into 12 topics, cap at 15 articles. Use when fetching press-review articles, testing RSS sources, adding/removing a source, adjusting topic keywords, or re-running the fetch stage. Triggers: "fetch press review sources", "test RSS", "add a news source", "fix topic classification".
---

# press-rss-fetch

Stage 1 of the REVISTA PRESEI pipeline. Owned by the `rss-fetcher` agent.

## What this does
Reads `RSS_SOURCES` + `TOPIC_KEYWORDS` from `city_news_config.py`, fetches via `press_review_rss.fetch_articles()`, returns ≤15 fresh, deduped, topic-classified articles.

## Why the config is shared
`press_review_rss.py` imports the source list and keywords from `city_news_config.py`. If you edit the list anywhere else, the two drift and a source silently stops fetching. Always edit `city_news_config.py` only.

## Run it (dry fetch, no DB write)
The deployed `press_review_rss.py` has no CLI flag — call `fetch_articles` directly:
```bash
plink -batch -pw 'REDACTED' tudor@192.168.100.21 \
  "cd /opt/ACTIVE/EVENT_PUBLISHER && python3 -c \"from press_review_rss import fetch_articles; \
import collections; a=fetch_articles(hours_back=26); print('TOTAL',len(a)); \
[print(s,n) for s,n in collections.Counter(x['source'] for x in a).items()]\""
```
Expected: ~15 articles; a dead source (e.g. Nine O'Clock 415, AGERPRES timeout) logs `[WARN]` and is skipped, never aborts.

## Add a source
1. Append a dict to `RSS_SOURCES` in `city_news_config.py` (name, url, lang).
2. Re-run `--test-sources`; confirm it appears with a topic.
3. Deploy `city_news_config.py` to raspibig `/opt/ACTIVE/EVENT_PUBLISHER/`. No cron change.

## Adjust topics
Edit `TOPIC_KEYWORDS` in `city_news_config.py`; classification is keyword match on title+desc, fallback "Society". Deploy the config; effect is immediate.

## Output contract
Write `_workspace/01_rss-fetcher_articles.json`: list of `{id, source, title, link, desc, topic, lang}`. Report per-source counts + total.

## Failure rules
- Per-source failure is tolerated (try/except + regex-strip invalid XML). Never abort on one dead feed.
- 0 total articles → FAIL the stage; downstream must not run on empty.
