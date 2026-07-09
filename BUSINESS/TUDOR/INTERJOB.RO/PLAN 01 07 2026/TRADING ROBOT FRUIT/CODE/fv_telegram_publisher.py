#!/usr/bin/env python3
"""Publica ofertele/cererile de legume pe Telegram (@cumparlegume_bot).

Oglinda lui fv_fb_publisher.py: acelasi build_post + curate/dedup, dar trimite
prin Telegram Bot API sendMessage catre chat_id (canal/grup unde botul e admin).

Dry-run by default; live cu --post. --force ocoleste dedup/cap.
Token + chat_id din DATA/telegram_cumparlegume.json sau env TG_CUMPARLEGUME_TOKEN /
TG_CUMPARLEGUME_CHAT. ASCII-only, fara preturi.
"""

import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from posteaza_oferte_facebook import build_post, load_ledger  # noqa: E402

DATA = Path(__file__).parent.parent / "DATA"
CONFIG = DATA / "telegram_cumparlegume.json"
POST_LOG = DATA / "tg_post_log.json"
API = "https://api.telegram.org"
DAILY_CAP = 1


def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _content_hash(text):
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def load_log():
    return json.loads(POST_LOG.read_text(encoding="utf-8")) if POST_LOG.exists() else {"posts": []}


def save_log(log):
    POST_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=True), encoding="utf-8")


def load_config():
    token = os.getenv("TG_CUMPARLEGUME_TOKEN")
    chat = os.getenv("TG_CUMPARLEGUME_CHAT")
    if CONFIG.exists():
        c = json.loads(CONFIG.read_text(encoding="utf-8"))
        token = token or c.get("token")
        chat = chat or c.get("chat_id")
    return token, chat


def curate(text, log):
    h = _content_hash(text)
    today = _today()
    posted_today = [p for p in log["posts"] if p["date"] == today and p["status"] == "posted"]
    if any(p["content_hash"] == h and p["status"] == "posted" for p in log["posts"]):
        return False, "DUPLICAT: continut deja postat"
    if len(posted_today) >= DAILY_CAP:
        return False, f"CAP ZILNIC atins ({len(posted_today)}/{DAILY_CAP})"
    return True, h


def bot_health(token):
    """getMe ca sa validam tokenul. Nu printeaza tokenul."""
    try:
        with urllib.request.urlopen(f"{API}/bot{token}/getMe", timeout=20) as r:
            d = json.loads(r.read().decode()).get("result", {})
            return True, d.get("username", "?")
    except Exception as e:
        return False, str(e)[:200]


def send_message(token, chat, text):
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    req = urllib.request.Request(f"{API}/bot{token}/sendMessage", data=data)
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
        print("[DRY-RUN] adauga --post ca sa publici pe Telegram.")
        return

    token, chat = load_config()
    if not token or not chat:
        print("\nLIPSA token/chat_id (DATA/telegram_cumparlegume.json). Adauga botul ca admin intr-un canal si pune chat_id. Nu postez.")
        sys.exit(2)
    healthy, who = bot_health(token)
    if not healthy:
        print(f"\n[BOT] TOKEN INVALID - {who}")
        sys.exit(3)
    print(f"[BOT] OK - @{who}")

    entry = {"date": _today(), "content_hash": chash, "ts": datetime.now(timezone.utc).isoformat()}
    try:
        res = send_message(token, chat, text)
        mid = res.get("result", {}).get("message_id")
        entry.update({"status": "posted", "message_id": mid})
        print(f"\n[POST] OK - message_id={mid} (chat {chat})")
    except urllib.error.HTTPError as e:
        entry.update({"status": "failed", "error": e.read().decode("utf-8", "ignore")[:300]})
        print(f"\n[POST] FAIL - {entry['error']}")
    finally:
        log["posts"].append(entry)
        save_log(log)


if __name__ == "__main__":
    main()
