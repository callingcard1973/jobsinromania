#!/usr/bin/env python3
"""Reusable WhatsApp notification helper for raspibig.

Reads tudor_number from DATA/whatsapp_internal.json and POSTs to the local
whatsapp.js Express server (127.0.0.1:5523). Fail-safe: never crashes the caller.

Usage:
  from wa_notify import notify
  notify("Deal ready: grau 25t @ 1.25 RON/kg", business="cumparlegume")
"""
import json
import os
import urllib.request
import urllib.error

_CONFIG = None
_SERVER = "http://127.0.0.1:5523/send"


def _load_config():
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    paths = [
        "/opt/ACTIVE/TRADING_ROBOT_FRUIT/DATA/whatsapp_internal.json",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "DATA", "whatsapp_internal.json"),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                _CONFIG = json.load(f)
                return _CONFIG
    _CONFIG = {}
    return _CONFIG


def notify(text, business="default"):
    """Send a WhatsApp message to Tudor. Returns True on success, False on failure."""
    cfg = _load_config()
    to = cfg.get("tudor_number")
    if not to:
        return False
    payload = json.dumps({"to": to, "text": text, "business": business}).encode("utf-8")
    req = urllib.request.Request(
        _SERVER, data=payload,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status == 200
    except (urllib.error.URLError, Exception):
        return False


if __name__ == "__main__":
    import sys
    text = " ".join(sys.argv[1:]) or "wa_notify.py test"
    ok = notify(text, business="test")
    print(f"sent={ok}")
