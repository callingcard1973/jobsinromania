#!/usr/bin/env python3
"""Deliverability guard: if a sender domain's bounce rate exceeds the threshold,
auto-disable that orchestrator segment (enabled=false) and alert Telegram, so a
burning domain stops sending before it tanks reputation. Run on a cron (e.g. 6h)."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import psycopg2

ANOFM = dict(dbname="anofm", user="tudor", host="localhost", password="tudor")
RASPIBIG = dict(dbname="interjob_master", user="tudor", host="192.168.100.21", password="tudor")
CFG = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/ANOFM_ANGAJATORI/anofm_orchestrator.json")
THRESHOLD = 8.0     # % bounce rate
MIN_SENT = 50       # don't act on tiny samples
TG_TOKEN = "8731910997:AAEwRCaZNXKeY-seWZfMOD-gqQclR-xeQBU"
TG_CHAT = "-1003830000766"


def telegram(text):
    data = urllib.parse.urlencode({"chat_id": TG_CHAT, "text": text}).encode()
    try:
        urllib.request.urlopen(
            urllib.request.Request(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data=data),
            timeout=20)
    except Exception as e:
        print(f"telegram failed: {e}")


def main():
    cfg = json.loads(CFG.read_text())
    ac = psycopg2.connect(**ANOFM)
    acur = ac.cursor()
    rc = psycopg2.connect(**RASPIBIG)
    rcur = rc.cursor()
    changed = False

    for seg in cfg["segments"]:
        if not seg.get("enabled"):
            continue
        dom = seg["sender_email"].split("@")[1]
        acur.execute("SELECT count(*) FROM send_log WHERE sender=%s", (seg["sender_email"],))
        sent = acur.fetchone()[0]
        rcur.execute("SELECT count(*) FROM domain_replies WHERE domain=%s AND response_type='bounce'", (dom,))
        bounces = rcur.fetchone()[0]
        rate = (100.0 * bounces / sent) if sent else 0.0
        print(f"[{seg['name']}] {dom}: sent={sent} bounces={bounces} rate={rate:.1f}%")
        if sent >= MIN_SENT and rate > THRESHOLD:
            seg["enabled"] = False
            changed = True
            telegram(f"⚠️ ANOFM GUARD: {dom} bounce-rate {rate:.1f}% (>{THRESHOLD}%) — segment "
                     f"{seg['name']} AUTO-PAUSED. Verifica reputatia inainte de a reactiva.")

    if changed:
        tmp = CFG.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))
        tmp.replace(CFG)
        print("config updated: segment(s) paused")
    ac.close()
    rc.close()


if __name__ == "__main__":
    main()
