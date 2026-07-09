#!/usr/bin/env python3
"""Connector Facebook — publica pe pagina Cumpar Legume via Graph API.

Citeste configul din PUBLISHING_ROBOT/publish_config.json (facebook).
Complet independent — fara path-uri catre DATA/.
"""

import json
import urllib.parse
import urllib.request
from pathlib import Path

_CFG_PATH = Path(__file__).parent.parent / "publish_config.json"
GRAPH = "https://graph.facebook.com/v21.0"


def publish(title, body):
    if not _CFG_PATH.exists():
        return False, "lipsa publish_config.json"

    c = json.loads(_CFG_PATH.read_text(encoding="utf-8")).get("facebook", {})
    token = c.get("access_token")
    page = c.get("page_id")
    if not token or not page:
        return False, "lipsa facebook.access_token / page_id in publish_config.json"

    text = f"{title}\n\n{body}"[:1000]
    data = urllib.parse.urlencode({"message": text, "access_token": token}).encode()
    req = urllib.request.Request(f"{GRAPH}/{page}/feed", data=data)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
        post_id = res.get("id", "")
        return True, f"https://facebook.com/{post_id}"
    except urllib.error.HTTPError as e:
        return False, e.read().decode("utf-8", "ignore")[:300]
    except Exception as e:
        return False, str(e)[:200]
