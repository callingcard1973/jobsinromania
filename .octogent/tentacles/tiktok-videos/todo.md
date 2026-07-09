# Todo — tiktok-videos

## Immediate Priority
- [ ] Create 14 TikTok channels: @jobs.romania.ro through @jobs.romania.ne
- [ ] Upload first batch: 70 videos in OUTPUT/queue/ (31 MB, awaiting manual upload)
- [ ] Verify UTM links working: interjob.ro/apply?lang=XX&src=tt_SOURCE&jid=JOBID

## Video Generation (next batch)
- [ ] Run norway flow: `python run_pipeline.py norway ro,en,fr 5 construction`
- [ ] Run anofm flow: `python run_pipeline.py anofm ur,hi,ar 5 factory`
- [ ] Check tiktok_posts table: should grow from 79 rows
- [ ] Verify voice quality per lang before batch (Piper=EU langs, edge-tts=ur/hi/ar/tl/vi/uk/bn/ne)

## Automation
- [ ] Add cron on raspibig: generate N videos/day automatically
- [ ] Add auto-upload script (TikTok API or manual queue tracker)
- [ ] Track conversions: views → clicks → applications in tiktok_posts table

## After Each Run
Report: videos generated, langs, sector, output path, any voice errors.
Stop on ffmpeg error. Never use LLM for hooks — templates only.
