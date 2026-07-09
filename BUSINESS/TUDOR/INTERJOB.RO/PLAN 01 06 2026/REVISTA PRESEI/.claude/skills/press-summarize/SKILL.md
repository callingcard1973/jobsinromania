---
name: press-summarize
description: Summarize press-review articles (2-sentence English) via Ollama qwen3-4b, translate Romanian titles/descriptions RO→EN, and build the magazine-style HTML body grouped by 12 topics with a featured Economy story. Use when summarizing articles, translating RO news, regenerating the press-review HTML layout, or debugging Ollama timeouts. Triggers: "summarize the articles", "translate the RO news", "rebuild the press HTML", "fix the magazine layout".
---

# press-summarize

Stage 2 of the REVISTA PRESEI pipeline. Owned by the `content-summarizer` agent.

## What this does
For each article: 2-sentence English summary (Ollama qwen3-4b on raspibig:11434), RO→EN translation of title+desc, then `build_html()` assembles the magazine body.

## Why graceful degradation matters
Ollama can time out (180s/article) and the free Google Translate tier rate-limits. The pipeline must still ship a review. So:
- Ollama timeout/unreachable → fallback = first 2 sentences of the RSS description.
- Translator unavailable → leave RO untranslated, flag it.
- Instantiate `GoogleTranslator` ONCE outside the loop; `sleep(0.5)` between calls.

## HTML layout rules (`build_html`)
- Hero header (title, date, "{n} sources | {m} stories | Updated 08:50 UTC").
- Featured story = first Economy article in a gray bordered box.
- Topic sections in `TOPIC_ORDER`: Economy → Energy → Agriculture → Real Estate → Technology → Labor → Infrastructure → Manufacturing → Legal → Politics → Society → Culture.
- Every topic with articles renders (no silent omission). Links `target="_blank" rel="noopener"`.
- qwen3 output: strip `<think>…</think>`. Temp 0.3, num_predict 120.

## Run a dry pipeline (fetch→summarize→HTML, no WP/DB)
`press_review.py` has no `--dry-run` flag yet; test the summary path directly:
```bash
plink -batch -pw 'REDACTED' tudor@192.168.100.21 \
  "cd /opt/ACTIVE/EVENT_PUBLISHER && python3 -c \"from press_review_rss import fetch_articles; \
from press_review import summarize, build_html; from datetime import date; \
a=fetch_articles(26); [x.__setitem__('summary', summarize(x['desc'], x.get('lang','en'))) for x in a]; \
print(len(build_html(a, date.today())), 'chars HTML')\""
```

## Output contract
- `_workspace/02_content-summarizer_body.html`
- `_workspace/02_content-summarizer_articles.json` (articles enriched with `summary`)
Report article count + number of Ollama fallbacks used.
