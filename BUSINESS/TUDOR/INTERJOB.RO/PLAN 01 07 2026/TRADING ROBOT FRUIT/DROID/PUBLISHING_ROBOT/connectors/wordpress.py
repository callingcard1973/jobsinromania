#!/usr/bin/env python3
"""Connector WordPress — publica articol pe cumparlegume.com (sau alt site).

Citeste configul din PUBLISHING_ROBOT/publish_config.json (wordpress).
Complet independent — fara path-uri catre DATA/.
"""

import base64
import json
import urllib.request
from pathlib import Path

_CFG_PATH = Path(__file__).parent.parent / "publish_config.json"


def publish(title, body):
    if not _CFG_PATH.exists():
        return False, "lipsa publish_config.json"

    c = json.loads(_CFG_PATH.read_text(encoding="utf-8")).get("wordpress", {})
    site = c.get("site", "https://cumparlegume.com")
    user = c.get("user")
    pw = c.get("app_password")
    if not user or not pw:
        return False, "lipsa wordpress.user / app_password in publish_config.json"

    body_html = body.replace("&", "&amp;").replace("<", "&lt;").replace("\n", "<br>")
    payload = json.dumps({
        "title": title,
        "content": body_html,
        "status": "publish",
    }).encode()

    auth = base64.b64encode(f"{user}:{pw}".encode()).decode()
    req = urllib.request.Request(
        f"{site.rstrip('/')}/wp-json/wp/v2/posts",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode())
        link = res.get("link") or f"{site}/?p={res.get('id')}"
        return True, link
    except urllib.error.HTTPError as e:
        return False, e.read().decode("utf-8", "ignore")[:300]
    except Exception as e:
        return False, str(e)[:200]
