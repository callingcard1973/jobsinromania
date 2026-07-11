#!/usr/bin/env python3
"""Publica ACELASI anunt de legume pe toate canalele: FB + Telegram + WP.

Un singur build_post -> 3 canale simultan:
  - Facebook  : pagina Cumpar Legume (Graph API)          [DATA/fb_cumparlegume.json]
  - Telegram  : canal @cumparlegume (Bot API)             [DATA/telegram_cumparlegume.json]
  - WordPress : articol pe cumparlegume.com (REST)        [DATA/fb_cumparlegume.json wp_*]

Fiecare canal are dedup propriu (nu reposteaza acelasi continut/zi). Dry-run by
default; live cu --post. --force ocoleste dedup. --only fb|tg|wp limiteaza canalele.
ASCII-only, fara preturi. Raport per canal la final.
"""

import base64
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from posteaza_oferte_facebook import build_post, load_ledger  # noqa: E402

DATA = Path(__file__).parent.parent / "DATA"
FB_CFG = DATA / "fb_cumparlegume.json"
TG_CFG = DATA / "telegram_cumparlegume.json"
LOG = DATA / "publish_all_log.json"
GRAPH = "https://graph.facebook.com/v21.0"
TG_API = "https://api.telegram.org"


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _hash(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def load_log():
    return json.loads(LOG.read_text(encoding="utf-8")) if LOG.exists() else {"posts": []}


def save_log(log):
    LOG.write_text(json.dumps(log, indent=2, ensure_ascii=True), encoding="utf-8")


def already(log, channel, h):
    return any(p.get("channel") == channel and p.get("content_hash") == h
               and p.get("status") == "posted" for p in log["posts"])


def _cfg(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def post_fb(text):
    c = _cfg(FB_CFG)
    tok, page = c.get("access_token"), c.get("page_id")
    if not tok or not page:
        return "skip", "lipsa token/page_id"
    data = urllib.parse.urlencode({"message": text, "access_token": tok}).encode()
    req = urllib.request.Request(f"{GRAPH}/{page}/feed", data=data)
    r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    return "posted", r.get("id")


def post_tg(text):
    c = _cfg(TG_CFG)
    tok, chat = c.get("token"), c.get("chat_id")
    if not tok or not chat:
        return "skip", "lipsa token/chat_id"
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"{TG_API}/bot{tok}/sendMessage", data=data)
    r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    return "posted", r.get("result", {}).get("message_id")


def post_wp(text):
    c = _cfg(FB_CFG)
    user, pw = c.get("wp_user"), c.get("wp_app_password")
    site = c.get("wp_site", "https://cumparlegume.com")
    if not user or not pw:
        return "skip", "lipsa wp creds"
    title = "Oferte Gospodarii de Altadata - " + _today()
    slug = "oferte-legume-fructe-" + _today()  # slug curat (evita URL-uri vechi cache-poluate Polylang)
    body = "<pre>" + text.replace("&", "&amp;").replace("<", "&lt;") + "</pre>"
    payload = json.dumps({"title": title, "slug": slug, "content": body, "status": "publish"}).encode()
    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = urllib.request.Request(f"{site.rstrip('/')}/wp-json/wp/v2/posts", data=payload,
                                 headers={"Content-Type": "application/json", "Authorization": f"Basic {auth}"})
    r = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    return "posted", r.get("link") or r.get("id")


CHANNELS = {"fb": post_fb, "tg": post_tg, "wp": post_wp}


def main():
    do_post = "--post" in sys.argv
    force = "--force" in sys.argv
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].split(",")

    text = build_post(load_ledger())
    h = _hash(text)
    log = load_log()

    print("=" * 56, text, "=" * 56, sep="\n")
    targets = [c for c in CHANNELS if (only is None or c in only)]
    print(f"\nCanale: {', '.join(targets)} | hash={h}")

    if not do_post:
        print("[DRY-RUN] adauga --post ca sa publici pe toate canalele.")
        return

    for ch in targets:
        if not force and already(log, ch, h):
            print(f"[{ch.upper()}] SKIP - deja postat azi")
            continue
        entry = {"channel": ch, "date": _today(), "content_hash": h,
                 "ts": datetime.now(timezone.utc).isoformat()}
        try:
            status, ref = CHANNELS[ch](text)
            entry.update({"status": status, "ref": ref})
            print(f"[{ch.upper()}] {status.upper()} - {ref}")
        except Exception as e:
            msg = str(e)
            if hasattr(e, "read"):
                msg = e.read().decode("utf-8", "ignore")[:200]
            entry.update({"status": "failed", "error": msg[:300]})
            print(f"[{ch.upper()}] FAIL - {msg[:200]}")
        if entry["status"] != "skip":
            log["posts"].append(entry)
    save_log(log)


if __name__ == "__main__":
    main()
