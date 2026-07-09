#!/usr/bin/env python3
"""Telegram approval bot — trimite continutul in TG cu butoane si proceseaza raspunsul.

Moduri:
  python publish_bot.py --send    # trimite pending items (one-shot, pentru cron)
  python publish_bot.py           # daemon: long-poll callbacks + trimite pending (la fiecare 10s)

Butoane pe mesaj:
  [Aproba] [Respinge] [Editeaza] [Programeaza]

La Aproba:  status -> approved, workerul publica
La Respinge:  status -> rejected
La Editeaza:  reply cu textul nou
La Programeaza:  reply cu data/ora
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from publish_db import init_db, add_item, get_item, get_pending, update_status, set_message_id

CONFIG = Path(__file__).parent / "publish_config.json"
API = "https://api.telegram.org"
LOG = Path(__file__).parent / "bot.log"

CHANNEL_LABELS = {"tg": "Telegram", "wp": "WordPress", "fb": "Facebook"}

# edit_pending: reply_to_message_id -> item_id (in-memory state)
_edit_pending = {}
_schedule_pending = {}


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _cfg():
    token = os.getenv("PUBLISH_BOT_TOKEN")
    chat = os.getenv("PUBLISH_BOT_CHAT")
    path = os.getenv("PUBLISH_DB_PATH")
    if CONFIG.exists():
        c = json.loads(CONFIG.read_text(encoding="utf-8"))
        token = token or c.get("approval_bot", {}).get("token")
        chat = chat or c.get("approval_bot", {}).get("chat_id")
    if not token or not chat:
        log("LIPSA token/chat_id in publish_config.json sau env PUBLISH_BOT_TOKEN/PUBLISH_BOT_CHAT")
        sys.exit(2)
    return token, chat


def _build_preview(item):
    channels_str = ", ".join(CHANNEL_LABELS.get(ch, ch.upper()) for ch in json.loads(item["channels"]))
    return (
        f"*{item['title']}*\n\n"
        f"{item['body']}\n\n"
        f"---\n"
        f"Canale: {channels_str}"
    ), channels_str


def _inline_keyboard(item_id):
    return json.dumps({
        "inline_keyboard": [[
            {"text": "Aproba", "callback_data": f"approve:{item_id}"},
            {"text": "Respinge", "callback_data": f"reject:{item_id}"},
            {"text": "Editeaza", "callback_data": f"edit:{item_id}"},
            {"text": "Programeaza", "callback_data": f"schedule:{item_id}"},
        ]]
    })


def send_pending(bot_token, chat_id):
    items = get_pending()
    for item in items:
        preview, ch_str = _build_preview(item)
        text = preview
        keyboard = _inline_keyboard(item["id"])
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard,
        }
        data = urllib.parse.urlencode(payload).encode()
        req = urllib.request.Request(f"{API}/bot{bot_token}/sendMessage", data=data)
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                res = json.loads(r.read().decode())
            msg_id = res.get("result", {}).get("message_id")
            set_message_id(item["id"], msg_id, chat_id)
            log(f"TRIMIS {item['id']} ({item['title'][:50]}) -> msg_id={msg_id}")
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", "ignore")[:200]
            log(f"FAIL trimitere {item['id']}: {err}")
        except Exception as e:
            log(f"FAIL trimitere {item['id']}: {e}")


def answer_callback(bot_token, callback_query_id, text=""):
    try:
        data = urllib.parse.urlencode({"callback_query_id": callback_query_id, "text": text}).encode()
        urllib.request.urlopen(f"{API}/bot{bot_token}/answerCallbackQuery", data=data, timeout=10)
    except Exception as e:
        log(f"answerCallbackQuery error: {e}")


def edit_message_text(bot_token, chat_id, msg_id, text, keyboard=None, parse_mode="Markdown"):
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text}
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if keyboard:
        payload["reply_markup"] = keyboard
    data = urllib.parse.urlencode(payload).encode()
    try:
        urllib.request.urlopen(f"{API}/bot{bot_token}/editMessageText", data=data, timeout=10)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "ignore")[:200]
        log(f"editMessageText HTTP {e.code}: {err_body}")
    except Exception as e:
        log(f"editMessageText error: {e}")


def send_message(bot_token, chat_id, text, reply_to=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_to:
        payload["reply_to_message_id"] = reply_to
    data = urllib.parse.urlencode(payload).encode()
    try:
        with urllib.request.urlopen(f"{API}/bot{bot_token}/sendMessage", data=data, timeout=15) as r:
            return json.loads(r.read().decode()).get("result", {}).get("message_id")
    except Exception as e:
        log(f"sendMessage error: {e}")
    return None


def handle_callback(bot_token, callback):
    data = callback.get("data", "")
    msg = callback.get("message", {})
    chat_id = msg.get("chat", {}).get("id")
    msg_id = msg.get("message_id")
    cq_id = callback.get("id")

    action, item_id = data.split(":", 1)
    item = get_item(item_id)
    if not item:
        answer_callback(bot_token, cq_id, "Itemul nu mai exista")
        return

    if action == "approve":
        answer_callback(bot_token, cq_id, "Aprobat! Se publica...")
        update_status(item_id, "approved")
        edit_message_text(bot_token, chat_id, msg_id,
            f"*Aprobat* - in curs de publicare...\n\n{item['title']}")
        log(f"APROBAT {item_id} ({item['title'][:50]})")

    elif action == "reject":
        answer_callback(bot_token, cq_id, "Respins")
        update_status(item_id, "rejected")
        edit_message_text(bot_token, chat_id, msg_id,
            f"*Respins*\n\n{item['title']}")
        log(f"RESPINS {item_id} ({item['title'][:50]})")

    elif action == "edit":
        answer_callback(bot_token, cq_id, "✏️ Trimite textul corectat ca reply la acest mesaj")
        prompt_msg = send_message(bot_token, chat_id,
            f"✏️ Trimite textul corectat ca REPLY la acest mesaj pentru *{item['title']}*",
            reply_to=msg_id)
        if prompt_msg:
            _edit_pending[str(msg_id)] = item_id
        log(f"EDIT cerut {item_id}")

    elif action == "schedule":
        answer_callback(bot_token, cq_id, "📅 Trimite data (ex: 2026-07-02 14:00)")
        prompt_msg = send_message(bot_token, chat_id,
            f"📅 Trimite data si ora ca REPLY (ex: `2026-07-02 14:00`) pentru *{item['title']}*",
            reply_to=msg_id)
        if prompt_msg:
            _schedule_pending[str(msg_id)] = item_id
        log(f"SCHEDULE cerut {item_id}")


def handle_reply(bot_token, update):
    msg = update.get("message", {})
    reply_to = msg.get("reply_to_message", {})
    text = msg.get("text", "").strip()
    chat_id = msg.get("chat", {}).get("id")
    reply_to_msg_id = reply_to.get("message_id")

    if not reply_to_msg_id:
        return

    rid = str(reply_to_msg_id)
    if rid in _edit_pending:
        item_id = _edit_pending.pop(rid)
        item = get_item(item_id)
        if not item:
            return

        from publish_db import _conn, _ts
        c = _conn()
        c.execute("UPDATE queue SET body=?, updated_at=? WHERE id=?", (text, _ts(), item_id))
        c.commit()
        c.close()
        log(f"EDITAT {item_id}: body actualizat")

        answer_callback(bot_token, "?", "Text actualizat!")
        preview, ch_str = _build_preview(item)
        keyboard = _inline_keyboard(item_id)
        # Edit the preview message
        if item.get("message_id") and item.get("chat_id"):
            edit_message_text(bot_token, item["chat_id"], item["message_id"],
                f"*Actualizat*\n\n{preview}", keyboard)
        send_message(bot_token, chat_id, f"Text actualizat pentru {item['title']}")

    elif rid in _schedule_pending:
        item_id = _schedule_pending.pop(rid)
        item = get_item(item_id)
        if not item:
            return

        from publish_db import _conn, _ts
        c = _conn()
        c.execute("UPDATE queue SET scheduled_at=?, status='scheduled', updated_at=? WHERE id=?",
                  (text, _ts(), item_id))
        c.commit()
        c.close()
        log(f"PROGRAMAT {item_id} la {text}")

        send_message(bot_token, chat_id, f"Programat pentru {text}: {item['title']}")
        if item.get("message_id") and item.get("chat_id"):
            edit_message_text(bot_token, item["chat_id"], item["message_id"],
                f"*Programat* pentru {text}\n\n{item['title']}")


def get_updates(bot_token, offset=None):
    params = {"timeout": 30, "limit": 10}
    if offset:
        params["offset"] = offset
    try:
        data = urllib.parse.urlencode(params).encode()
        r = urllib.request.urlopen(f"{API}/bot{bot_token}/getUpdates", data=data, timeout=35)
        return json.loads(r.read().decode()).get("result", [])
    except Exception as e:
        log(f"getUpdates error: {e}")
        return []


def update_published_messages(bot_token):
    """Verifica itemi publicati (notified=0) si actualizeaza mesajul TG cu URL-urile."""
    from publish_db import get_unnotified, mark_notified
    items = get_unnotified()
    for item in items:
        if not item.get("message_id") or not item.get("chat_id"):
            continue
        if item.get("urls"):
            urls = json.loads(item["urls"])
            lines = [f"✅ *Publicat* — {item['title']}"]
            for ch, url in urls.items():
                label = CHANNEL_LABELS.get(ch, ch.upper())
                is_ok = not url.startswith("FAIL")
                if is_ok:
                    lines.append(f"  {label}: {url}")
                else:
                    lines.append(f"  {label}: ❌ {url.replace('FAIL: ','')}")
            edit_message_text(bot_token, item["chat_id"], item["message_id"],
                              "\n".join(lines), keyboard=None, parse_mode=None)
            mark_notified(item["id"])
            log(f"ACTUALIZAT mesaj {item['id']} cu URL-urile")


def daemon_loop():
    init_db()
    bot_token, chat_id = _cfg()
    log(f"Daemon pornit (bot_token={bot_token[:8]}..., chat_id={chat_id})")

    offset = None
    last_send_check = 0
    last_update_check = 0

    while True:
        try:
            now = time.time()

            # Trimite pending items la fiecare 10 sec
            if now - last_send_check >= 10:
                send_pending(bot_token, chat_id)
                last_send_check = now

            # Actualizeaza mesajele publicate la fiecare 5 sec
            if now - last_update_check >= 5:
                update_published_messages(bot_token)
                last_update_check = now

            # Poll callbacks
            updates = get_updates(bot_token, offset)
            for update in updates:
                offset = update["update_id"] + 1

                if "callback_query" in update:
                    handle_callback(bot_token, update["callback_query"])
                elif "message" in update:
                    handle_reply(bot_token, update)

            time.sleep(1)

        except KeyboardInterrupt:
            log("Oprit manual")
            break
        except Exception as e:
            log(f"Eroare bucla principala: {e}")
            time.sleep(5)

    log("Daemon oprit")


def main():
    init_db()
    if "--send" in sys.argv:
        bot_token, chat_id = _cfg()
        send_pending(bot_token, chat_id)
        update_published_messages(bot_token)
    else:
        daemon_loop()


if __name__ == "__main__":
    main()
