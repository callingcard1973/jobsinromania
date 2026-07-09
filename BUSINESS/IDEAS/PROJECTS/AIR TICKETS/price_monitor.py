#!/usr/bin/env python3
"""
Flight Price Monitor for InterJob ethnic worker routes.
Checks top routes via Kiwi Tequila API, stores in PostgreSQL,
sends alerts when prices drop >15%.

Deploy: /opt/ACTIVE/FLIGHTS/price_monitor.py on raspibig
Cron:   0 */6 * * * python3 /opt/ACTIVE/FLIGHTS/price_monitor.py
Max 250 lines (project convention).
"""

import os
import json
import time
import smtplib
import logging
import requests
from datetime import datetime, timedelta
from email.mime.text import MIMEText

# --- Config ---
TEQUILA_KEY = os.environ.get("TEQUILA_API_KEY", "YOUR_API_KEY_HERE")
TEQUILA_URL = "https://api.tequila.kiwi.com/v2/search"
DB_ENABLED = os.environ.get("FLIGHTS_DB_ENABLED", "false") == "true"
ALERT_EMAIL = os.environ.get("ALERT_EMAIL", "manpower.dristor@gmail.com")
ALERT_THRESHOLD = 0.15  # 15% drop triggers alert
LOG_FILE = "/opt/ACTIVE/FLIGHTS/logs/price_monitor.log"
PRICES_FILE = "/opt/ACTIVE/FLIGHTS/data/prices.json"

# Ethnic worker routes: (from, to, label)
ROUTES = [
    ("OTP", "AMS", "Bucharest-Amsterdam"),
    ("OTP", "BER", "Bucharest-Berlin"),
    ("OTP", "OSL", "Bucharest-Oslo"),
    ("OTP", "CPH", "Bucharest-Copenhagen"),
    ("OTP", "HEL", "Bucharest-Helsinki"),
    ("OTP", "MXP", "Bucharest-Milan"),
    ("KTM", "OTP", "Kathmandu-Bucharest"),
    ("SOF", "AMS", "Sofia-Amsterdam"),
    ("MNL", "OTP", "Manila-Bucharest"),
    ("OTP", "LJU", "Bucharest-Ljubljana"),
]

os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
os.makedirs(os.path.dirname(PRICES_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE, level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)
log = logging.getLogger("price_monitor")


def load_previous_prices():
    if os.path.exists(PRICES_FILE):
        with open(PRICES_FILE) as f:
            return json.load(f)
    return {}


def save_prices(prices):
    with open(PRICES_FILE, "w") as f:
        json.dump(prices, f, indent=2)


def search_route(fly_from, fly_to, days_ahead=14):
    """Search cheapest flight on a route, looking 14 days ahead."""
    date_from = datetime.now() + timedelta(days=1)
    date_to = datetime.now() + timedelta(days=days_ahead)
    params = {
        "fly_from": fly_from,
        "fly_to": fly_to,
        "date_from": date_from.strftime("%d/%m/%Y"),
        "date_to": date_to.strftime("%d/%m/%Y"),
        "adults": 1,
        "curr": "EUR",
        "locale": "en",
        "limit": 5,
        "sort": "price",
        "max_stopovers": 2,
    }
    headers = {"apikey": TEQUILA_KEY}
    try:
        resp = requests.get(TEQUILA_URL, params=params, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if data.get("data"):
            best = data["data"][0]
            return {
                "price": best["price"],
                "airline": ", ".join(set(best["airlines"])),
                "stops": len(best["route"]) - 1,
                "deep_link": best["deep_link"],
                "departure": best["local_departure"],
                "checked_at": datetime.now().isoformat(),
            }
    except Exception as e:
        log.error(f"Search failed {fly_from}->{fly_to}: {e}")
    return None


def store_in_db(route_key, result):
    """Optional: store in PostgreSQL interjob_master.flight_prices."""
    if not DB_ENABLED:
        return
    try:
        import psycopg2
        conn = psycopg2.connect(
            host="localhost", dbname="interjob_master",
            user="tudor", password=os.environ.get("PG_PASSWORD", "")
        )
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flight_prices (
                id SERIAL PRIMARY KEY,
                route TEXT NOT NULL,
                price NUMERIC(10,2),
                airline TEXT,
                stops INTEGER,
                deep_link TEXT,
                departure TIMESTAMP,
                checked_at TIMESTAMP DEFAULT NOW()
            )
        """)
        cur.execute(
            """INSERT INTO flight_prices
               (route, price, airline, stops, deep_link, departure)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (route_key, result["price"], result["airline"],
             result["stops"], result["deep_link"], result["departure"])
        )
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        log.error(f"DB store failed: {e}")


def send_alert(drops):
    """Send email alert for price drops. Uses Gmail SMTP."""
    if not drops:
        return
    subject = f"Flight Price Alert: {len(drops)} route(s) dropped!"
    body = "Price drops detected:\n\n"
    for d in drops:
        body += (
            f"  {d['route']}: EUR {d['old']:.0f} -> EUR {d['new']:.0f} "
            f"({d['drop_pct']:.0f}% drop)\n"
            f"  Book: {d['link']}\n\n"
        )
    body += "-- InterJob Flight Monitor\n"
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = ALERT_EMAIL
    msg["To"] = ALERT_EMAIL
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(ALERT_EMAIL, os.environ.get("GMAIL_APP_PASSWORD", ""))
            s.send_message(msg)
        log.info(f"Alert sent: {len(drops)} drops")
    except Exception as e:
        log.error(f"Alert email failed: {e}")


def main():
    log.info("=== Price monitor run started ===")
    previous = load_previous_prices()
    current = {}
    drops = []

    for fly_from, fly_to, label in ROUTES:
        route_key = f"{fly_from}-{fly_to}"
        log.info(f"Checking {label} ({route_key})")
        result = search_route(fly_from, fly_to)

        if result:
            current[route_key] = result
            store_in_db(route_key, result)
            log.info(f"  {route_key}: EUR {result['price']} ({result['airline']})")

            # Check for price drop
            if route_key in previous:
                old_price = previous[route_key]["price"]
                new_price = result["price"]
                if old_price > 0 and new_price < old_price:
                    drop_pct = (old_price - new_price) / old_price
                    if drop_pct >= ALERT_THRESHOLD:
                        drops.append({
                            "route": label,
                            "old": old_price,
                            "new": new_price,
                            "drop_pct": drop_pct * 100,
                            "link": result["deep_link"],
                        })
        else:
            # Keep previous price if search failed
            if route_key in previous:
                current[route_key] = previous[route_key]
        time.sleep(2)  # Rate limiting between requests

    save_prices(current)

    if drops:
        log.info(f"Price drops found: {len(drops)}")
        send_alert(drops)
    else:
        log.info("No significant price drops.")

    # Print summary
    print(f"\n{'Route':<25} {'Price':>8} {'Airline':<20} {'Stops':>5}")
    print("-" * 65)
    for fly_from, fly_to, label in ROUTES:
        key = f"{fly_from}-{fly_to}"
        if key in current:
            r = current[key]
            print(f"{label:<25} EUR {r['price']:>5} {r['airline']:<20} {r['stops']:>5}")
        else:
            print(f"{label:<25} {'N/A':>8}")

    log.info("=== Price monitor run complete ===")


if __name__ == "__main__":
    main()
