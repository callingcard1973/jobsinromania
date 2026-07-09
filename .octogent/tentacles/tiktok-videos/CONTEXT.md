# Tentacle: tiktok-videos

## Machine
raspibig — tudor@192.168.100.21 (all rendering here, laptop has no ffmpeg)

## What It Does
Generates multilingual TikTok job videos (1080×1920) — pulls jobs from PostgreSQL,
generates hooks via templates, synthesizes voice (Piper/edge-tts), renders via ffmpeg.
Zero cost. No LLM per render. No paid APIs.

## Code Location (laptop)
D:\MEMORY\IDEAS\TIKTOK_JOBS\CODE\

## Raspibig Paths
- Venv: /opt/ACTIVE/TIKTOK_JOBS/venv/
- Piper voices: /opt/ACTIVE/TIKTOK_JOBS/voices/  (6 EU voices)
- Output queue: OUTPUT/queue/*.mp4 + .json meta

## Run Command
```bash
python run_pipeline.py anofm en,fr,ur 3 transport
# args: source(anofm|norway) | langs(csv) | count | sector
```

## DB
- interjob_master.tiktok_posts (id, job_id, source, lang, channel, hook, views, clicks, applications)
- 79 rows already generated (first batch 2026-04-17)

## Flows
- norway: EURES Norway jobs → Romanian diaspora audience
- romania: ANOFM RO jobs → 13 foreign language audiences (Pakistani/Indian/Ukrainian/etc.)

## 14 Languages
ro, en, fr, es, it, de, ur, hi, ar, tl, vi, uk, bn, ne
RTL langs (ar, ur): ensure dir="rtl" if used in HTML

## Channels (to create)
@jobs.romania.{lang} for each of 14 langs

## UTM Attribution
?lang=XX&src=tt_SOURCE&jid=JOBID on interjob.ro/apply

## Known Constraints
- qwen3 bad at RO hooks — use templates only
- Mixkit/Pexels blocked — pure ffmpeg gradients only
- Laptop has no ffmpeg — all rendering via SSH to raspibig
- Piper runs inside venv on raspibig (PEP 668)
