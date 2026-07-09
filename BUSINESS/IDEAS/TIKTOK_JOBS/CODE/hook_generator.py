"""Template-based TikTok hooks. Deterministic, <1s. Templates keyed by (source, lang)."""
import random
import sys
import io
import json
import re
from pathlib import Path

if __name__ == "__main__" and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TEMPLATES = json.loads((Path(__file__).parent / "templates.json").read_text(encoding="utf-8"))


def clean_title(title):
    t = re.sub(r"\([^)]*\)", "", title or "")
    t = re.sub(r"\s+", " ", t).strip(" -:?!.")
    return t[:60]


def generate_hook(job, source="norway", lang="ro"):
    src = TEMPLATES.get(source)
    if not src:
        raise ValueError(f"Unknown source: {source}")
    t = src.get(lang)
    if not t:
        raise ValueError(f"Lang {lang} not supported for source {source}")
    template = random.choice(t["hooks"])
    return template.format(
        amount=random.choice(t["amounts"]),
        currency=t.get("currency", ""),
        positions=job.get("positions") or random.randint(5, 50),
        job_clean=clean_title(job.get("job_title", "")),
    )


def supported_langs(source="norway"):
    src = TEMPLATES.get(source, {})
    return [k for k in src.keys() if not k.startswith("_")]


def country_native(source, lang):
    return TEMPLATES.get(source, {}).get(lang, {}).get("country_native", source.upper())


if __name__ == "__main__":
    source = sys.argv[1] if len(sys.argv) > 1 else "norway"
    lang = sys.argv[2] if len(sys.argv) > 2 else "ro"
    job_arg = sys.argv[3] if len(sys.argv) > 3 else "Vi soker byggarbeidere"
    job = json.loads(job_arg) if job_arg.startswith("{") else {"job_title": job_arg}
    print(generate_hook(job, source, lang))
