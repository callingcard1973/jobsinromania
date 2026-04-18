# TIKTOK_JOBS — Faceless TikTok Pipeline

**Goal:** Generate multilingual TikTok videos for Romanian job openings. Scale via automation. Drive traffic to interjob.ro/apply.

**Status:** MVP complete. 14 languages. Zero cost, zero tokens, zero signup.

## Stack (all FREE)

| Component | Tool | Location |
|-----------|------|----------|
| Job source | PostgreSQL `job_posts` (EURES+ANOFM) | raspibig |
| Hook text | Template-based (no LLM) | local |
| TTS EU langs | Piper (6 voices) | raspibig venv |
| TTS non-EU | edge-tts (8 voices) | raspibig venv |
| Video render | ffmpeg gradient + drawtext | raspibig |
| Tracking | `tiktok_posts` table | raspibig |
| Upload | Manual queue → phone | user |

## Languages (14)

**Piper (higher quality):** ro, en, fr, es, it, de  
**edge-tts (MS free):** ur, hi, ar, tl, vi, uk, bn, ne

## Flows

- `norway`: EURES Norway jobs → RO audience (Romanian diaspora)
- `romania` (ANOFM): Romania jobs → 13 foreign audiences (pak/ind/bangla/nepal/ukr/etc.)

## Usage

```bash
cd D:\MEMORY\IDEAS\TIKTOK_JOBS\CODE

# 1 Norway job, RO language
python run_pipeline.py norway ro 1

# 3 ANOFM transport jobs × 9 langs = 27 videos
python run_pipeline.py anofm en,fr,ur,hi,ar,tl,vi,uk,bn 3 transport

# List queue for manual upload
python uploader.py
```

## Files (all <250 lines)

- `fetch_jobs.py` — Pull from PostgreSQL via SSH
- `hook_generator.py` — Template-based hooks per (source, lang)
- `templates.json` — 14 langs × 4 hooks × 2 flows
- `tts.py` — Unified Piper+edge-tts wrapper
- `video_render.py` — ffmpeg gradient + text overlay, 1080x1920
- `tracker.py` — Log to `tiktok_posts` table
- `uploader.py` — List pending videos + captions + hashtags
- `run_pipeline.py` — Orchestrator end-to-end

## TikTok Channels (create manually)

Each language = 1 channel:
- @jobs.romania.ro, @jobs.romania.en, @jobs.romania.fr, @jobs.romania.ur,
  @jobs.romania.hi, @jobs.romania.ar, @jobs.romania.tl, @jobs.romania.vi,
  @jobs.romania.uk, @jobs.romania.bn, @jobs.romania.ne, @jobs.romania.es,
  @jobs.romania.it, @jobs.romania.de

Bio link: https://interjob.ro/apply?lang={XX}&src=tt_{source}

## Attribution

Videos use UTM: `?lang=XX&src=tt_SOURCE&jid=JOBID`. PostHog events on /apply capture visits. Conversions tracked in `tiktok_posts.clicks/applications` (join via job_id).

## Scaling

- Current rate: ~15 sec/video (TTS + ffmpeg via SSH)
- 10 jobs × 14 langs = 140 videos ≈ 35 min
- Daily target: 5 jobs × 14 langs = 70 videos/day across all channels

## Next Steps

1. Upload first 10 videos manually to test channels
2. Track which langs convert (apply click)
3. Cron daily: `python run_pipeline.py anofm ro,en,fr,ur,hi,ar,tl,vi,uk 3`
4. Future: TikTok auto-upload via playwright (session cookie)
