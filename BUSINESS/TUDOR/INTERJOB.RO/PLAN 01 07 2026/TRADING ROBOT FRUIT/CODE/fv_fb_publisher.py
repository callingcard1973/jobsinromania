#!/usr/bin/env python3
"""Publica ofertele/cererile de legume pe pagina FB Cumpar Legume via Graph API.

Ca posterul de joburi InterJob (fb_poster.py): POST direct pe /{page}/feed cu
Page Access Token. Ciclu: curate (exclude internal_only + request din OFERIM) ->
dedup pe continut (fb_post_log.json, cap 1/zi) -> token health -> post.

Dry-run by default; live cu --post. --force ocoleste dedup/cap (test).
Token + page_id din DATA/fb_cumparlegume.json sau env FB_CUMPARLEGUME_TOKEN /
FB_CUMPARLEGUME_PAGE_ID. ASCII-only, fara preturi (negociere privata).
"""

import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from posteaza_oferte_facebook import build_post, load_ledger, load_config  # noqa: E402

DATA = Path(__file__).parent.parent / "DATA"
POST_LOG = DATA / "fb_post_log.json"
GRAPH = "https://graph.facebook.com/v21.0"
DAILY_CAP = 1  # o postare/zi pe pagina (anti-spam)


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _content_hash(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def load_log():
    if POST_LOG.exists():
        return json.loads(POST_LOG.read_text(encoding="utf-8"))
    return {"posts": []}


def save_log(log):
    POST_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=True), encoding="utf-8")


def curate(text, log):
    """Dedup pe continut + cap zilnic. Ret (ok, hash|motiv)."""
    h = _content_hash(text)
    today = _today()
    posted_today = [p for p in log["posts"] if p["date"] == today and p["status"] == "posted"]
    if any(p["content_hash"] == h and p["status"] == "posted" for p in log["posts"]):
        return False, "DUPLICAT: continut deja postat"
    if len(posted_today) >= DAILY_CAP:
        return False, f"CAP ZILNIC atins ({len(posted_today)}/{DAILY_CAP})"
    return True, h


def token_health(token):
    """GET /me ca sa validam tokenul. Nu printeaza tokenul."""
    try:
        url = f"{GRAPH}/me?fields=id,name&access_token={urllib.parse.quote(token)}"
        with urllib.request.urlopen(url, timeout=20) as r:
            return True, json.loads(r.read().decode()).get("name", "?")
    except urllib.error.HTTPError as e:
        return False, e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return False, str(e)[:200]


def post_to_fb(text, token, page):
    data = urllib.parse.urlencode({"message": text, "access_token": token}).encode()
    req = urllib.request.Request(f"{GRAPH}/{page}/feed", data=data)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def main():
    do_post = "--post" in sys.argv
    text = build_post(load_ledger())
    log = load_log()

    print("=" * 56, text, "=" * 56, sep="\n")

    ok, info = curate(text, log)
    if "--force" in sys.argv and not ok:
        print(f"\n[CURATE] override --force (era: {info})")
        ok, info = True, _content_hash(text)
    if not ok:
        print(f"\n[CURATE] SKIP - {info}")
        return
    chash = info
    print(f"\n[CURATE] OK - continut nou (hash={chash})")

    if not do_post:
        print("[DRY-RUN] adauga --post ca sa publici pe FB Cumpar Legume.")
        return

    token, page = load_config()
    if not token or not page:
        print("\nLIPSA token/page_id (DATA/fb_cumparlegume.json). Nu postez.")
        sys.exit(2)
    healthy, who = token_health(token)
    if not healthy:
        print(f"\n[TOKEN] INVALID/EXPIRAT - {who}\nRegenereaza tokenul paginii Cumpar Legume.")
        sys.exit(3)
    print(f"[TOKEN] OK - {who}")

    entry = {"date": _today(), "content_hash": chash, "ts": datetime.now(timezone.utc).isoformat()}
    try:
        res = post_to_fb(text, token, page)
        entry.update({"status": "posted", "post_id": res.get("id")})
        print(f"\n[POST] OK - post_id={res.get('id')} (pagina Cumpar Legume)")
    except urllib.error.HTTPError as e:
        entry.update({"status": "failed", "error": e.read().decode("utf-8", "ignore")[:300]})
        print(f"\n[POST] FAIL - {entry['error']}")
    finally:
        log["posts"].append(entry)
        save_log(log)


if __name__ == "__main__":
    main()
