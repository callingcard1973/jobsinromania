"""End-to-end: fetch jobs → hooks → TTS → render → queue → log.
Usage:
    python run_pipeline.py norway ro,en,fr 3        # 3 Norway jobs in 3 langs
    python run_pipeline.py anofm ur,hi,ar 2          # 2 ANOFM jobs in 3 langs
    python run_pipeline.py anofm ro,en,fr,ur,hi,ar,tl,vi,uk 1  # 1 job × 9 langs
"""
import sys
import io
import json
import re
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.path.insert(0, str(Path(__file__).parent))

import fetch_jobs
import hook_generator
import tts
import video_render
import tracker

QUEUE = Path(__file__).parent.parent / "OUTPUT" / "queue"
QUEUE.mkdir(parents=True, exist_ok=True)

SOURCE_FLOW = {"norway": "norway", "anofm": "romania"}
COUNTRY_OVERLAY = {"norway": "NORVEGIA", "anofm": "ROMANIA"}


def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", (s or "").lower())[:40].strip("_")


def process(source, langs, limit, sector=None):
    jobs = fetch_jobs.fetch(source, limit, sector)
    if not jobs:
        print(f"No jobs for {source}")
        return
    country = COUNTRY_OVERLAY.get(source, source.upper())
    flow = SOURCE_FLOW.get(source, source)
    valid_langs = hook_generator.supported_langs(flow)
    count = 0
    for job in jobs:
        jid = job.get("job_id", f"unknown_{count}")
        for lang in langs:
            if lang not in valid_langs:
                print(f"SKIP {lang}: not in {flow} flow")
                continue
            if lang not in tts.supported_langs():
                print(f"SKIP {lang}: no TTS voice")
                continue
            hook = hook_generator.generate_hook(job, flow, lang)
            base = f"{source}_{slug(jid)}_{lang}"
            wav = QUEUE / f"{base}.wav"
            mp4 = QUEUE / f"{base}.mp4"
            meta = QUEUE / f"{base}.json"

            if mp4.exists():
                print(f"SKIP {base}: already rendered")
                continue

            print(f">> {base}: {hook[:70]}...")
            try:
                tts.synth(hook, lang, wav)
                video_render.render(wav, hook, mp4, country)
                meta.write_text(json.dumps({
                    "job_id": jid,
                    "source": source,
                    "lang": lang,
                    "channel": f"@jobs.romania.{lang}",
                    "hook": hook,
                    "job_title": job.get("job_title"),
                    "company": job.get("company"),
                    "location": job.get("location"),
                    "salary": job.get("salary"),
                }, ensure_ascii=False, indent=2), encoding="utf-8")
                tracker.log_post(jid, source, lang, f"@jobs.romania.{lang}", hook, str(mp4))
                count += 1
                print(f"   DONE {mp4.name}")
            except Exception as e:
                print(f"   FAIL {base}: {e}")
    print(f"\nTotal: {count} videos generated in {QUEUE}")


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "norway"
    langs = (sys.argv[2] if len(sys.argv) > 2 else "ro").split(",")
    limit = int(sys.argv[3]) if len(sys.argv) > 3 else 1
    sector = sys.argv[4] if len(sys.argv) > 4 else None
    process(source, langs, limit, sector)
