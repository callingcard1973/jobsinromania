#!/usr/bin/env python3
"""
SICAP Monitor Universal — Bogdan Gavra / AgroEvolution
Adaugi un CPV nou în lista CPV_CONFIGS și gata.
Rulare: python sicap_monitor_universal.py [--dry-run]
Cron raspibig: 0 8 * * 1 python3 /opt/ACTIVE/BOGDAN/sicap_monitor_universal.py
"""

import os, json, logging, requests
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════
# CONFIGURARE — ADAUGĂ CPV-URI NOUL AICI
# ══════════════════════════════════════════════════════════════
CPV_CONFIGS = [
    {
        "cpv_id":   14308,
        "cpv_code": "37535200-9",
        "label":    "LOC DE JOACĂ",
        "emoji":    "🛝",
        "keywords": ["loc de joacă", "locuri de joacă", "parc copii", "echipamente joacă"],
    },
    {
        "cpv_id":   None,
        "cpv_code": "45236119-7",
        "label":    "GAZON SINTETIC",
        "emoji":    "⚽",
        "keywords": ["gazon sintetic", "teren sport", "teren fotbal", "multisport", "suprafață sintetică"],
    },
    {
        "cpv_id":   None,
        "cpv_code": "77211400-6",
        "label":    "DEFRIȘARE / ARBORI",
        "emoji":    "🌳",
        "keywords": ["defrișare", "tăiere arbori", "doborâre arbori", "plantare arbori", "copaci"],
    },
    {
        "cpv_id":   None,
        "cpv_code": "45212221-1",
        "label":    "REABILITARE TEREN SPORT",
        "emoji":    "🏟️",
        "keywords": ["reabilitare teren", "teren sport", "teren multisport", "teren fotbal"],
    },
    {
        "cpv_id":   None,
        "cpv_code": "39110000-6",
        "label":    "MOBILIER URBAN",
        "emoji":    "🪑",
        "keywords": ["mobilier urban", "bănci parc", "coșuri gunoi", "stâlpi", "pergolă"],
    },
    {
        "cpv_id":   None,
        "cpv_code": "37440000-4",
        "label":    "FITNESS AER LIBER",
        "emoji":    "🏋️",
        "keywords": ["fitness", "aparate fitness", "stații fitness", "echipamente sport exterior"],
    },
    {
        "cpv_id":   None,
        "cpv_code": "31520000-7",
        "label":    "ILUMINAT LED PARCURI",
        "emoji":    "💡",
        "keywords": ["iluminat", "LED", "stâlpi iluminat", "iluminat public", "solar"],
    },
    {
        "cpv_id":   None,
        "cpv_code": "45112720-8",
        "label":    "AMENAJARE SPAȚII VERZI",
        "emoji":    "🌿",
        "keywords": ["spații verzi", "amenajare parc", "peisagistică", "gazon", "plantare"],
    },
]

# ══════════════════════════════════════════════════════════════
# SETĂRI TELEGRAM
# ══════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID   = os.getenv("BOGDAN_CHAT_ID", os.getenv("TELEGRAM_CHAT_ID", ""))

# ══════════════════════════════════════════════════════════════
# SETĂRI GENERALE
# ══════════════════════════════════════════════════════════════
BASE_DIR  = Path(__file__).parent
SEEN_FILE = BASE_DIR / "sicap_universal_seen.json"
LOG_FILE  = BASE_DIR / "sicap_universal.log"
PAGE_SIZE = 100
API_URL   = "https://e-licitatie.ro/api-pub/NoticeCommon/GetCNoticeList"
HEADERS   = {
    "Content-Type": "application/json",
    "Referer":      "https://e-licitatie.ro/pub/notices/contract-notices/list/1/0",
    "Origin":       "https://e-licitatie.ro",
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"), logging.StreamHandler()],
)
log = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════
# SEEN IDs
# ══════════════════════════════════════════════════════════════
def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    return set()

def save_seen(seen: set) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen)), encoding="utf-8")


# ══════════════════════════════════════════════════════════════
# API FETCH
# ══════════════════════════════════════════════════════════════
def fetch_tenders(cpv_config: dict) -> list[dict]:
    payload = {"pageSize": PAGE_SIZE, "pageIndex": 0}
    if cpv_config.get("cpv_id"):
        payload["cPVId"] = cpv_config["cpv_id"]
    try:
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
        r.raise_for_status()
        items = r.json().get("items", [])
        log.info("[%s] API returned %d items", cpv_config["label"], len(items))
        return items
    except Exception as e:
        log.error("[%s] API fetch failed: %s", cpv_config["label"], e)
        return []


# ══════════════════════════════════════════════════════════════
# RELEVANCE CHECK
# ══════════════════════════════════════════════════════════════
def is_relevant(item: dict, cpv_config: dict) -> bool:
    cpv   = item.get("cpvCodeAndName", "").lower()
    title = item.get("contractTitle", "").lower()
    code  = cpv_config["cpv_code"].split("-")[0]  # "45236119"
    if code in cpv:
        return True
    return any(kw.lower() in title for kw in cpv_config["keywords"])


# ══════════════════════════════════════════════════════════════
# FORMAT ALERT
# ══════════════════════════════════════════════════════════════
def format_alert(item: dict, cpv_config: dict) -> str:
    authority = item.get("contractingAuthorityNameAndFN", "Necunoscut")
    if " - " in authority:
        authority = authority.split(" - ", 1)[1]
    raw_val = item.get("estimatedValueExport") or "N/A"
    value   = raw_val.replace(" RON", "").strip() if raw_val != "N/A" else "N/A"
    title   = item.get("contractTitle", "Fără titlu")[:120]
    dead    = item.get("tenderReceiptDeadlineExport") or "N/A"
    cpv     = item.get("cpvCodeAndName", "")
    nid     = item.get("noticeId") or item.get("id", "")
    url     = f"https://e-licitatie.ro/pub/notices/contract-notices/view/{nid}"
    return (
        f"{cpv_config['emoji']} <b>NOU — {cpv_config['label']}</b>\n"
        f"📍 {authority}\n"
        f"📋 {title}\n"
        f"🔖 CPV: {cpv}\n"
        f"💰 {value} RON\n"
        f"⏰ Termen: {dead}\n"
        f"🔗 {url}"
    )


# ══════════════════════════════════════════════════════════════
# TELEGRAM
# ══════════════════════════════════════════════════════════════
def send_telegram(msg: str) -> bool:
    if not BOT_TOKEN:
        log.warning("TELEGRAM_BOT_TOKEN not set — printing:\n%s", msg)
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg, "parse_mode": "HTML"},
            timeout=15,
        )
        r.raise_for_status()
        return True
    except Exception as e:
        log.error("Telegram send failed: %s", e)
        return False


# ══════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════
def run(dry_run: bool = False) -> None:
    log.info("=== SICAP Universal Monitor — %s (dry=%s) ===",
             datetime.now().strftime("%Y-%m-%d %H:%M"), dry_run)
    seen = load_seen()
    total_new = 0

    for cfg in CPV_CONFIGS:
        items = fetch_tenders(cfg)
        new_for_cpv = 0
        for item in items:
            tid = str(item.get("noticeId") or item.get("id"))
            key = f"{cfg['cpv_code']}_{tid}"
            if key in seen:
                continue
            if not is_relevant(item, cfg):
                continue
            msg = format_alert(item, cfg)
            log.info("[%s] NEW: %s", cfg["label"], item.get("contractTitle", "")[:80])
            if dry_run:
                print(f"\n--- DRY RUN [{cfg['label']}] ---")
                print(msg.encode("ascii", "replace").decode())
            else:
                send_telegram(msg)
            seen.add(key)
            new_for_cpv += 1
            total_new += 1
        log.info("[%s] Done. %d new tenders.", cfg["label"], new_for_cpv)

    save_seen(seen)
    log.info("=== Total new tenders: %d ===", total_new)


if __name__ == "__main__":
    import sys
    run(dry_run="--dry-run" in sys.argv or "-n" in sys.argv)
