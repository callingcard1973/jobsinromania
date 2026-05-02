#!/usr/bin/env python3
"""SEAP food tender alert dispatcher -- cron-ready.

Checks for new food tenders since last run, cross-matches with
cooperative member categories, sends email alerts via Brevo.

Usage:
    python seap_alert_dispatcher.py              # Check + send alerts
    python seap_alert_dispatcher.py --dry-run    # Preview without sending
    python seap_alert_dispatcher.py --reset      # Reset last-run timestamp
"""

import json
import os
import sys
from datetime import datetime, timedelta

try:
    import psycopg2
except ImportError:
    print("pip install psycopg2-binary")
    sys.exit(1)

try:
    import sib_api_v3_sdk
    from sib_api_v3_sdk.rest import ApiException
    HAS_BREVO = True
except ImportError:
    HAS_BREVO = False

from shared_utils import DB_MASTER, DB_FOOD, normalize

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_FILE = os.path.join(PROJECT_DIR, "DATA", "seap_dispatcher_state.json")

# -- CPV subcategories mapped to cooperative product categories
CPV_TO_CATEGORY = {
    "151": "meat", "152": "fish", "153": "fruit-veg",
    "154": "oils-fats", "155": "dairy", "156": "grain-starch",
    "158": "misc-food", "159": "beverages",
    "031": "crops", "032": "cereals-veg", "033": "fruit-nuts",
}

# -- Alert recipients (cooperative coordinators)
ALERT_RECIPIENTS = [
    {"email": "cumparlegume@agroevolution.com", "name": "Cooperative HQ"},
]


def load_state():
    """Load last-run timestamp."""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"last_run": None, "total_alerts_sent": 0}


def save_state(state):
    """Save state with current timestamp."""
    state["last_run"] = datetime.now().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def fetch_new_tenders(conn, since):
    """Get food tenders published since last run."""
    cur = conn.cursor()
    cur.execute("""
        SELECT ted_id, title, buyer_name, winner_name,
               value, currency, date_published, cpv_code
        FROM tenders
        WHERE country = 'RO'
        AND (cpv_code LIKE '15%%' OR cpv_code LIKE '03%%')
        AND date_published >= %s
        ORDER BY date_published DESC
    """, (since,))
    rows = cur.fetchall()
    headers = [d[0] for d in cur.description]
    return [dict(zip(headers, r)) for r in rows]


def match_to_members(tenders, conn_food):
    """Match tenders to cooperative member categories."""
    cur = conn_food.cursor()
    cur.execute("""
        SELECT DISTINCT category FROM contacts
        WHERE email IS NOT NULL AND email != ''
    """)
    member_categories = {r[0] for r in cur.fetchall() if r[0]}

    matched = []
    for t in tenders:
        cpv3 = str(t.get("cpv_code", ""))[:3]
        cat = CPV_TO_CATEGORY.get(cpv3, "other")
        if cat in member_categories or cat == "other":
            t["matched_category"] = cat
            matched.append(t)
    return matched


def build_alert_body(tenders):
    """Build HTML email body from matched tenders."""
    lines = [
        "<h2>New SEAP Food Tenders</h2>",
        f"<p>Found {len(tenders)} new food procurement tenders.</p>",
        "<table border='1' cellpadding='5' cellspacing='0'>",
        "<tr><th>Buyer</th><th>Title</th><th>Value</th>"
        "<th>Category</th><th>Date</th></tr>",
    ]
    for t in tenders[:50]:
        buyer = str(t.get("buyer_name", ""))[:60]
        title = str(t.get("title", ""))[:80]
        value = t.get("value")
        val_str = f"{value:,.0f} {t.get('currency', 'RON')}" if value else "N/A"
        cat = t.get("matched_category", "other")
        date = str(t.get("date_published", ""))[:10]
        lines.append(
            f"<tr><td>{buyer}</td><td>{title}</td>"
            f"<td>{val_str}</td><td>{cat}</td><td>{date}</td></tr>"
        )
    if len(tenders) > 50:
        lines.append(
            f"<tr><td colspan='5'>... and {len(tenders) - 50} more</td></tr>"
        )
    lines.append("</table>")
    lines.append("<p><em>Automated alert from SEAP Food Tender Dispatcher</em></p>")
    return "\n".join(lines)


def send_alert(subject, body, dry_run=False):
    """Send alert email via Brevo."""
    if dry_run:
        print(f"\n[DRY RUN] Would send: {subject}")
        print(f"  To: {[r['email'] for r in ALERT_RECIPIENTS]}")
        print(f"  Body length: {len(body)} chars")
        return True

    if not HAS_BREVO:
        print("WARNING: sib_api_v3_sdk not installed, cannot send. pip install sib-api-v3-sdk")
        return False

    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        print("WARNING: BREVO_API_KEY not set in environment")
        return False

    config = sib_api_v3_sdk.Configuration()
    config.api_key["api-key"] = api_key
    api = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(config))

    msg = sib_api_v3_sdk.SendSmtpEmail(
        subject=subject,
        html_content=body,
        sender={"name": "SEAP Alert", "email": "cumparlegume@agroevolution.com"},
        to=ALERT_RECIPIENTS,
    )
    try:
        api.send_transac_email(msg)
        print(f"Alert sent to {len(ALERT_RECIPIENTS)} recipients")
        return True
    except ApiException as e:
        print(f"Brevo API error: {e}")
        return False


def main():
    args = sys.argv[1:]
    dry_run = "--dry-run" in args

    state = load_state()

    if "--reset" in args:
        state["last_run"] = None
        save_state(state)
        print("State reset. Next run will check last 7 days.")
        return

    if state["last_run"]:
        since = state["last_run"][:10]
    else:
        since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")

    print(f"Checking food tenders since: {since}")

    conn_master = psycopg2.connect(**DB_MASTER)
    conn_food = psycopg2.connect(**DB_FOOD)

    tenders = fetch_new_tenders(conn_master, since)
    print(f"New food tenders found: {len(tenders)}")

    if not tenders:
        print("No new tenders. Done.")
        if not dry_run:
            save_state(state)
        conn_food.close()
        conn_master.close()
        return

    matched = match_to_members(tenders, conn_food)
    print(f"Matched to member categories: {len(matched)}")

    conn_food.close()
    conn_master.close()

    if matched:
        subject = f"SEAP Alert: {len(matched)} new food tenders ({since})"
        body = build_alert_body(matched)
        sent = send_alert(subject, body, dry_run=dry_run)
        if sent and not dry_run:
            state["total_alerts_sent"] = state.get("total_alerts_sent", 0) + 1

    if not dry_run:
        save_state(state)

    print("Done.")


if __name__ == "__main__":
    main()
