#!/usr/bin/env python3
"""Connector Telegram — publica pe canalul @cumparlegume.

Citeste configul din PUBLISHING_ROBOT/publish_config.json (telegram_channel).
Complet independent — fara path-uri catre DATA/.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

_CFG_PATH = Path(__file__).parent.parent / "publish_config.json"
API = "https://api.telegram.org"
MAX_LEN = 4096


def publish(title, body):
    if not _CFG_PATH.exists():
        return False, "lipsa publish_config.json"

    c = json.loads(_CFG_PATH.read_text(encoding="utf-8")).get("telegram_channel", {})
    token = c.get("token")
    chat = c.get("chat_id")
    if not token or not chat:
        return False, "lipsa telegram_channel.token / chat_id in publish_config.json"

    text = f"*{title}*\n\n{body}"[:MAX_LEN]
    data = urllib.parse.urlencode({
        "chat_id": chat,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()

    req = urllib.request.Request(f"{API}/bot{token}/sendMessage", data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
        msg_id = res.get("result", {}).get("message_id")
        chat_str = str(chat).lstrip("@")
        if str(chat).startswith("-100"):
            chat_str = str(chat).replace("-100", "", 1)
            url = f"https://t.me/c/{chat_str}/{msg_id}"
        else:
            url = f"https://t.me/{chat_str}/{msg_id}"
        return True, url
    except urllib.error.HTTPError as e:
        return False, e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return False, str(e)[:200]
