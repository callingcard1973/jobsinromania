#!/usr/bin/env python3
"""
Agent 8: Deal Alert — trimite alerte Telegram in timp real pentru chilipiruri.
Combina scorurile din listing_hunter + price_anomaly + cma.

Ruleaza ca ultim pas dupa hunter + anomaly.
Cron: zilnic dupa listing_hunter, sau standalone.

Folosire:
  python3 deal_alert.py                  # alerte noi
  python3 deal_alert.py --min-score 60   # doar scoruri > 60
  python3 deal_alert.py --test           # trimite test alert
"""
import argparse, logging, os, sys
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("deal_alert")

try:
    import psycopg2
    import requests
except ImportError:
    log.error("pip install psycopg2-binary requests")
    sys.exit(1)

DB = {"host": "localhost", "dbname": "interjob_master", "user": "tudor", "password": "tudor"}


def load_telegram_config():
    """Incarca Telegram credentials din .env."""
    env_files = [
        "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env",
        "/opt/ACTIVE/EMAIL/.env.unified",
    ]
    config = {}
    for ef in env_files:
        if os.path.exists(ef):
            with open(ef) as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        config[k.strip()] = v.strip().strip('"').strip("'")
    return config.get("TELEGRAM_BOT_TOKEN", ""), config.get("TELEGRAM_CHAT_ID", "")


def send_telegram(bot_token, chat_id, text):
    """Trimite mesaj Telegram."""
    if not bot_token or not chat_id:
        log.warning("Telegram neconfigurat — afisez local")
        print(text)
        return False
    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        r = requests.post(url, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=10)
        return r.status_code == 200
    except Exception as e:
        log.error(f"Telegram eroare: {e}")
        return False


def get_new_deals(conn, min_score=40, hours=24):
    """Gaseste deal-uri noi din ultimele N ore."""
    cutoff = datetime.now() - timedelta(hours=hours)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, title, price_eur, location, url, urgency_score, urgency_keywords
            FROM terenuri_listings
            WHERE is_deal = TRUE
            AND scraped_at > %s
            AND urgency_score >= %s
            ORDER BY urgency_score DESC
            LIMIT 20
        """, (cutoff, min_score))
        return cur.fetchall()


def format_deal_message(deals):
    """Formateaza mesaj Telegram cu deal-uri."""
    if not deals:
        return None

    lines = [f"🏡 <b>ALERTA TERENURI — {len(deals)} chilipiruri</b>\n"]

    for i, (did, title, price, location, url, score, keywords) in enumerate(deals[:10], 1):
        price_str = f"€{price:,}" if price else "pret necunoscut"
        kw_str = f" [{keywords}]" if keywords else ""
        lines.append(f"<b>{i}. [{score}pts]</b> {title[:60]}")
        lines.append(f"   {price_str} | {location or '?'}{kw_str}")
        if url:
            lines.append(f"   <a href=\"{url}\">Vezi anunt</a>")
        lines.append("")

    if len(deals) > 10:
        lines.append(f"... si inca {len(deals) - 10} deal-uri")

    lines.append(f"\n⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    return "\n".join(lines)


def ensure_alert_log(conn):
    """Creeaza tabela alert log daca nu exista."""
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS terenuri_alerts (
                id SERIAL PRIMARY KEY,
                listing_id INTEGER,
                alert_type VARCHAR(20) DEFAULT 'telegram',
                sent_at TIMESTAMP DEFAULT NOW()
            )
        """)
    conn.commit()


def main():
    parser = argparse.ArgumentParser(description="Deal Alert — alerte Telegram terenuri")
    parser.add_argument("--min-score", type=int, default=40)
    parser.add_argument("--hours", type=int, default=24, help="Cauta deals din ultimele N ore")
    parser.add_argument("--test", action="store_true", help="Trimite mesaj test")
    args = parser.parse_args()

    bot_token, chat_id = load_telegram_config()

    if args.test:
        ok = send_telegram(bot_token, chat_id, "🧪 Test Deal Alert — sistemul functioneaza!")
        print("OK" if ok else "EROARE")
        return

    conn = psycopg2.connect(**DB)
    ensure_alert_log(conn)

    deals = get_new_deals(conn, args.min_score, args.hours)
    log.info(f"Deal-uri noi: {len(deals)}")

    if not deals:
        log.info("Zero deal-uri noi — nicio alerta")
        conn.close()
        return

    msg = format_deal_message(deals)
    if msg:
        ok = send_telegram(bot_token, chat_id, msg)
        if ok:
            # Log alertele trimise
            with conn.cursor() as cur:
                for deal in deals:
                    cur.execute(
                        "INSERT INTO terenuri_alerts (listing_id) VALUES (%s)",
                        (deal[0],)
                    )
            conn.commit()
            log.info(f"Alerta trimisa: {len(deals)} deal-uri")
        else:
            log.error("Alerta NU s-a trimis")

    conn.close()


if __name__ == "__main__":
    main()
