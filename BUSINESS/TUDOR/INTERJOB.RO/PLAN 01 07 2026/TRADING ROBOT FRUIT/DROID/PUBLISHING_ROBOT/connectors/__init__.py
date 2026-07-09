"""Connectors pentru PUBLISHING_ROBOT — complet independenti, fara path-uri externe.

Fiecare connector expune: publish(title, body) -> (success: bool, url_or_error: str)
Configuratia se citeste din PUBLISHING_ROBOT/publish_config.json.
"""

import json
from pathlib import Path

_ROOT = Path(__file__).parent.parent
_CFG_PATH = _ROOT / "publish_config.json"


def load_config():
    c = json.loads(_CFG_PATH.read_text(encoding="utf-8"))
    return c


from .telegram import publish as publish_telegram
from .wordpress import publish as publish_wordpress
from .facebook import publish as publish_facebook
from .linkedin import publish as publish_linkedin
from .x import publish as publish_x

REGISTRY = {
    "tg": publish_telegram,
    "wp": publish_wordpress,
    "fb": publish_facebook,
    "linkedin": publish_linkedin,
    "x": publish_x,
}

REGISTRY_LABELS = {
    "tg": "Telegram",
    "wp": "WordPress",
    "fb": "Facebook",
}
