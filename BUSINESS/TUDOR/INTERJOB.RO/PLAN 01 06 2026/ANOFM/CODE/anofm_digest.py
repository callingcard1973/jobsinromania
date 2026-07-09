#!/usr/bin/env python3
"""Daily ANOFM funnel digest -> Telegram + log. Shows the whole loop: cold sends
per sender domain, replies (interested/opt-out/bounce), catalogs auto-sent, baskets,
DNC size, and per-domain bounce rate (the deliverability signal)."""
import json
import urllib.parse
import urllib.request
from pathlib import Path

import psycopg2

ANOFM = dict(dbname="anofm", user="tudor", host="localhost", password="tudor")
RASPIBIG = dict(dbname="interjob_master", user="tudor", host="192.168.100.21", password="tudor")
FUNNEL_SENT = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/CATALOG_FUNNEL/sent.json")
DOMAINS = ["factoryjobs.eu", "bppltd.co.uk", "buildjobs.eu", "horecaworkers2026.eu", "warehouseworkers.eu", "electricjobs.eu"]
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
    L = ["📊 ANOFM funnel — digest zilnic", ""]
    ac = psycopg2.connect(**ANOFM)
    cur = ac.cursor()

    cur.execute("SELECT sender, count(*) FILTER (WHERE sent_at::date=current_date) today, count(*) total "
                "FROM send_log WHERE campaign LIKE 'ANOFM_%' AND campaign NOT IN ('ANOFM_ANGAJATORI','ANOFM_APRIL') "
                "GROUP BY sender ORDER BY sender")
    L.append("✉️ Cold trimise (azi / total):")
    sent_today, sent_total = {}, {}
    for sender, today, total in cur.fetchall():
        dom = (sender or "").split("@")[-1]
        sent_today[dom], sent_total[dom] = today, total
        L.append(f"  {dom}: {today} / {total}")

    cur.execute("SELECT count(*) FROM dnc_master")
    dnc = cur.fetchone()[0]
    ac.close()

    # replies + bounce rate from raspibig domain_replies
    L.append("")
    L.append("💬 Replies (azi) + bounce-rate:")
    rc = psycopg2.connect(**RASPIBIG)
    rcur = rc.cursor()
    for dom in DOMAINS:
        rcur.execute("SELECT response_type, count(*) FROM domain_replies "
                     "WHERE domain=%s AND created_at::date=current_date GROUP BY response_type", (dom,))
        by = dict(rcur.fetchall())
        st = sent_today.get(dom, 0)
        rate = (100.0 * by.get("bounce", 0) / st) if st else 0.0   # today's bounces / today's sent
        flag = " ⚠️HIGH" if (rate > 8 and st >= 20) else ""        # ignore noise on tiny samples
        L.append(f"  {dom}: interesat={by.get('interested',0)} opt-out={by.get('opt_out',0)} "
                 f"bounce={by.get('bounce',0)} | bounce-rate={rate:.1f}%{flag}")
    rc.close()

    catalogs = len(json.loads(FUNNEL_SENT.read_text())) if FUNNEL_SENT.exists() else 0
    L.append("")
    L.append(f"📖 Cataloage trimise (total): {catalogs}")
    L.append(f"🚫 DNC: {dnc}")

    msg = "\n".join(L)
    print(msg)
    telegram(msg)


if __name__ == "__main__":
    main()
