import requests, json, os, logging
from datetime import datetime

LOG = "/opt/ACTIVE/SICAP/gazon.log"
SEEN_FILE = "/opt/ACTIVE/SICAP/gazon_seen.json"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("BOGDAN_CHAT_ID", "")
KEYWORDS = ["gazon sintetic", "teren sport", "teren fotbal", "gazon artificial", "suprafata sintetica"]

logging.basicConfig(filename=LOG, level=logging.INFO, format="%(asctime)s %(message)s")

def send_telegram(msg):
    if not BOT_TOKEN or not CHAT_ID: return
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"}, timeout=10)

def load_seen():
    try: return set(json.load(open(SEEN_FILE)))
    except: return set()

def save_seen(seen):
    json.dump(list(seen), open(SEEN_FILE, "w"))

def fetch(keyword, page=0):
    r = requests.post("https://e-licitatie.ro/api-pub/NoticeCommon/GetCNoticeList",
        headers={"Referer": "https://e-licitatie.ro/pub/notices/contract-notices/list/1/0",
                 "Content-Type": "application/json"},
        json={"pageSize": 50, "pageIndex": page, "keyword": keyword, "sysNoticeState": 5},
        timeout=15)
    return r.json().get("items", [])

seen = load_seen()
new_count = 0
for kw in KEYWORDS:
    for item in fetch(kw):
        nid = str(item.get("noticeNo", ""))
        if not nid or nid in seen: continue
        seen.add(nid)
        new_count += 1
        authority = item.get("contractingAuthorityNameRo") or item.get("contractingAuthorityName", "?")
        value = item.get("estimatedValueRon", 0)
        deadline = (item.get("responseDeadline") or "")[:10]
        url = f"https://sicap.pro/anunturi/{nid}"
        msg = f"⚽ NOU LICITAȚIE GAZON/TEREN SPORT\n📍 {authority}\n💰 {value:,.0f} RON\n⏰ Termen: {deadline}\n🔗 {url}"
        logging.info(f"NEW | {nid} | {authority} | {value}")
        send_telegram(msg)
        print(msg)

save_seen(seen)
logging.info(f"Run complete. {new_count} new. Total seen: {len(seen)}")
print(f"Done. {new_count} new leads.")
