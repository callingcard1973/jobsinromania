#!/usr/bin/env python3
"""
SICAP Monitor — CPV 37535200 (echipamente locuri de joacă)
Polls e-licitatie.ro API for new playground equipment tenders.
Sends Telegram alerts to Bogdan on new finds.
"""

import os, json, logging, requests
from datetime import datetime
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
SEEN_FILE     = BASE_DIR / "sicap_seen.json"
LOG_FILE      = BASE_DIR / "sicap_monitor.log"

BOT_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
CHAT_ID       = os.getenv("TELEGRAM_CHAT_ID", "-1001234567890")

CPV_ID        = 14308          # numeric ID for 37535200-9 in SEAP DB
CPV_CODE      = "37535200-9"
PAGE_SIZE     = 50
KEYWORDS      = ["loc de joacă", "locuri de joacă", "echipamente joacă",
                 "parc copii", "loc joaca", "locuri joaca", "echipamente joaca",
                 "37535200"]

API_URL       = "https://e-licitatie.ro/api-pub/NoticeCommon/GetCNoticeList"
HEADERS       = {
    "Content-Type": "application/json",
    "Referer":      "https://e-licitatie.ro/pub/notices/contract-notices/list/1/0",
    "Origin":       "https://e-licitatie.ro",
    "User-Agent":   "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
}

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE, encoding="utf-8"),
              logging.StreamHandler()],
)
log = logging.getLogger(__name__)

# ── Seen IDs persistence ──────────────────────────────────────────────────────
def load_seen() -> set:
    if SEEN_FILE.exists():
        return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    return set()

def save_seen(seen: set) -> None:
    SEEN_FILE.write_text(json.dumps(sorted(seen)), encoding="utf-8")

# ── SEAP API fetch ────────────────────────────────────────────────────────────
def fetch_tenders() -> list[dict]:
    """Fetch open tenders filtered by CPV 37535200 from e-licitatie.ro API."""
    payload = {"pageSize": PAGE_SIZE, "pageIndex": 0, "cPVId": CPV_ID}
    try:
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=30)
        r.raise_for_status()
        items = r.json().get("items", [])
        log.info("API returned %d items (total in DB: %s)",
                 len(items), r.json().get("total"))
        return items
    except Exception as e:
        log.error("API fetch failed: %s", e)
        return []

# ── Relevance check ───────────────────────────────────────────────────────────
def is_relevant(item: dict) -> bool:
    """Accept tenders with exact CPV match OR title keyword match."""
    cpv = item.get("cpvCodeAndName", "").lower()
    title = item.get("contractTitle", "").lower()
    if "37535200" in cpv:
        return True
    return any(kw.lower() in title for kw in KEYWORDS)

# ── Telegram alert ────────────────────────────────────────────────────────────
def send_telegram(msg: str) -> bool:
    if BOT_TOKEN in ("YOUR_BOT_TOKEN", ""):
        log.warning("Telegram not configured — printing alert:\n%s", msg)
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": CHAT_ID, "text": msg,
                                     "parse_mode": "HTML"}, timeout=15)
        r.raise_for_status()
        return True
    except Exception as e:
        log.error("Telegram send failed: %s", e)
        return False

def build_notice_url(item: dict) -> str:
    nid = item.get("noticeId") or item.get("id", "")
    return f"https://e-licitatie.ro/pub/notices/contract-notices/view/{nid}"

def format_alert(item: dict) -> str:
    authority = item.get("contractingAuthorityNameAndFN", "Necunoscut")
    # Strip leading CUI number if present (e.g. "4404605 - Municipiul X")
    if " - " in authority:
        authority = authority.split(" - ", 1)[1]
    raw_val = item.get("estimatedValueExport") or "N/A"
    # Remove trailing " RON" duplicate if present (field sometimes already has it)
    value  = raw_val.replace(" RON", "").strip() if raw_val != "N/A" else "N/A"
    title  = item.get("contractTitle", "Fără titlu")[:120]
    dead   = item.get("tenderReceiptDeadlineExport") or "N/A"
    cpv    = item.get("cpvCodeAndName", "")
    url    = build_notice_url(item)
    return (
        f"🏗 <b>NOU LICITAȚIE LOC DE JOACĂ</b>\n"
        f"📍 {authority}\n"
        f"📋 {title}\n"
        f"🔖 CPV: {cpv}\n"
        f"💰 {value} RON\n"
        f"⏰ Termen: {dead}\n"
        f"🔗 {url}"
    )

# ── Main ──────────────────────────────────────────────────────────────────────
def run(dry_run: bool = False) -> None:
    log.info("=== SICAP Monitor run started (dry_run=%s) ===", dry_run)
    seen = load_seen()
    items = fetch_tenders()

    new_count = 0
    for item in items:
        tid = str(item.get("noticeId") or item.get("id"))
        if tid in seen:
            continue
        if not is_relevant(item):
            log.debug("Skip irrelevant tender %s: %s", tid,
                      item.get("contractTitle", "")[:60])
            continue

        log.info("NEW tender %s: %s", tid, item.get("contractTitle", "")[:80])
        msg = format_alert(item)
        if dry_run:
            print("\n--- DRY RUN ALERT ---")
            print(msg.encode("ascii", "replace").decode())
        else:
            if send_telegram(msg):
                log.info("Alert sent for tender %s", tid)
        seen.add(tid)
        new_count += 1

    save_seen(seen)
    log.info("Run complete. New tenders found: %d / %d checked", new_count, len(items))

if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv or "-n" in sys.argv
    run(dry_run=dry)
