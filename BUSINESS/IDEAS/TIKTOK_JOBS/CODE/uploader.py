"""List pending videos + captions + hashtags for manual upload via phone."""
import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

QUEUE_DIR = Path(__file__).parent.parent / "OUTPUT" / "queue"
POSTED_DIR = Path(__file__).parent.parent / "OUTPUT" / "posted"

HASHTAGS = {
    "ro": "#joburinorvegia #muncainnorvegia #romaniinstrainate #joburi #salariumare",
    "en": "#jobsineurope #jobsromania #workeurope #workabroad #relocation",
    "fr": "#emploiroumanie #travaileurope #jobsetranger #relocalisation",
    "es": "#empleorumania #trabajoeuropa #trabajoextranjero",
    "it": "#lavororomania #lavoroeuropa #lavoroestero",
    "de": "#jobsrumaenien #arbeiteuropa #ausland",
    "ur": "#pakistanijobs #jobsinromania #europejobs #naukri",
    "hi": "#indianjobs #romaniajobs #europejobs #naukri",
    "ar": "#وظائف_رومانيا #وظائف_أوروبا",
    "tl": "#filipinoabroad #jobsromania #ofwjobs",
    "vi": "#vieclamromania #lamvieceurope #vieclamnuocngoai",
    "uk": "#роботаврумунії #роботаєвропа #вакансії",
    "bn": "#bangladeshjobs #romaniajobs #europejobs",
    "ne": "#nepalijobs #romaniajobs #foreignjobs",
}

APPLY_BASE = "https://interjob.ro/apply"


def list_queue():
    POSTED_DIR.mkdir(parents=True, exist_ok=True)
    items = []
    for mp4 in sorted(QUEUE_DIR.glob("*.mp4")):
        meta = mp4.with_suffix(".json")
        if not meta.exists():
            continue
        data = json.loads(meta.read_text(encoding="utf-8"))
        lang = data.get("lang", "ro")
        src = data.get("source", "norway")
        apply_url = f"{APPLY_BASE}?lang={lang}&src=tt_{src}&jid={data.get('job_id','')}"
        items.append({
            "video": str(mp4),
            "lang": lang,
            "caption": data.get("hook", ""),
            "hashtags": HASHTAGS.get(lang, ""),
            "apply_url": apply_url,
            "channel": data.get("channel", f"@jobs.romania.{lang}"),
        })
    return items


def pretty_print():
    items = list_queue()
    if not items:
        print("Queue empty.")
        return
    for i, it in enumerate(items, 1):
        print(f"\n[{i}] {it['video']}")
        print(f"    Channel: {it['channel']} | Lang: {it['lang']}")
        print(f"    Caption: {it['caption']}")
        print(f"    Tags:    {it['hashtags']}")
        print(f"    Bio URL: {it['apply_url']}")


if __name__ == "__main__":
    pretty_print()
