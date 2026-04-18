#!/usr/bin/env python3
"""Solonet Order Pipeline — creates orders from responses, sends after approval, tracks.
Called by response_tracker (auto-creates drafts) and bot commands (approve/send/track)."""
import os, json, smtplib, requests, psycopg2, re
from email.mime.text import MIMEText
from datetime import datetime, timedelta

TOKEN = "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8"
CHAT = "547047851"
DB = {"host": "/var/run/postgresql", "dbname": "interjob_master",
      "user": "tudor", "password": "scraper123"}
LOG = "/home/tudor/.logs/solonet_pipeline.log"

SOLONET_EMAIL = "solonet.vacancy@gmail.com"
SENDER_EMAIL = "manpower.dristor@gmail.com"


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(f"[{ts}] {msg}\n")


def db_conn():
    return psycopg2.connect(**DB)


def alert(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT, "text": msg, "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass


def enrich_employer(email, company):
    """Enrich employer data from companies DB + send_log."""
    data = {"company": company, "city": "", "phone": "", "campaign": ""}
    try:
        conn = db_conn()
        cur = conn.cursor()
        domain = email.split("@")[1] if "@" in email else ""
        if domain:
            cur.execute("SELECT name, city, phone FROM companies WHERE LOWER(email) LIKE %s LIMIT 1",
                (f"%{domain}%",))
            row = cur.fetchone()
            if row:
                data["company"] = data["company"] or (row[0] or "")
                data["city"] = row[1] or ""
                data["phone"] = row[2] or ""
        if company and not data["city"]:
            cur.execute("SELECT city, phone FROM companies WHERE LOWER(name) LIKE %s LIMIT 1",
                (f"%{company.lower()[:20]}%",))
            row = cur.fetchone()
            if row:
                data["city"] = row[0] or ""
                data["phone"] = data["phone"] or (row[1] or "")
        cur.close()
        conn.close()
    except Exception:
        pass
    try:
        import psycopg2 as pg2
        c2 = pg2.connect(host="/var/run/postgresql", dbname="email_sender", user="tudor")
        cc = c2.cursor()
        cc.execute("SELECT campaign FROM send_log WHERE LOWER(email)=%s ORDER BY sent_at_utc DESC LIMIT 1", (email.lower(),))
        r = cc.fetchone()
        if r:
            data["campaign"] = r[0]
        cc.close()
        c2.close()
    except Exception:
        pass
    return data


def create_draft(email, company, contact_name, positions, location,
                 campaign, subject, body, phone=""):
    """Create draft order — auto-enriches from DB."""
    enriched = enrich_employer(email, company)
    company = company or enriched["company"]
    location = location or enriched["city"]
    phone = phone or enriched["phone"]
    campaign = campaign or enriched["campaign"] or "UNKNOWN"
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""INSERT INTO solonet_orders
            (company, contact_email, contact_name, contact_phone, positions,
             location, campaign, original_subject, original_body, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft')
            ON CONFLICT (contact_email, company) DO NOTHING
            RETURNING id""",
            (company, email, contact_name, phone, positions,
             location, campaign, subject[:255], body[:1000]))
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()
        if row:
            oid = row[0]
            alert(f"🏢 <b>NEW ORDER DRAFT</b>\n"
                  f"Company: {company}\n"
                  f"Contact: {email}\n"
                  f"Needs: {positions[:100]}\n"
                  f"Campaign: {campaign}\n\n"
                  f"/send_solonet_{oid} — approve + send to Adrian\n"
                  f"/skip_solonet_{oid} — skip")
            log(f"Draft created: #{oid} {company} ({email})")
            return oid
    except Exception as e:
        log(f"Draft error: {e}")
    return None


def format_solonet_email(order):
    """Format clear request for solonet."""
    return f"""Buna ziua Adrian,

Avem o cerere noua de personal:

COMPANIE: {order['company']}
CONTACT: {order['contact_name'] or order['contact_email']}
EMAIL: {order['contact_email']}
TELEFON: {order['contact_phone'] or 'N/A'}
LOCATIE: {order['location'] or 'Romania'}
POZITII CERUTE: {order['positions'] or 'De discutat cu clientul'}
CAMPANIE SURSA: {order['campaign']}

CONTEXT (ce a scris clientul):
{order['original_body'][:500] if order['original_body'] else 'Raspuns la campania noastra email'}

Te rog sa contactezi clientul si sa discutati detaliile.

Cu stima,
Tudor Seicarescu
InterJob Solutions Europe
+40 722 789 938
"""


def send_to_solonet(order_id):
    """Send approved order to solonet.vacancy@gmail.com."""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM solonet_orders WHERE id=%s", (order_id,))
        cols = [d[0] for d in cur.description]
        row = cur.fetchone()
        if not row:
            return "Order not found"
        order = dict(zip(cols, row))
        if order['status'] not in ('draft', 'approved'):
            return f"Order already {order['status']}"

        env = {}
        with open("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env") as f:
            for l in f:
                if "=" in l and not l.startswith("#"):
                    k, v = l.strip().split("=", 1)
                    env[k] = v

        body = format_solonet_email(order)
        msg = MIMEText(body)
        msg["Subject"] = f"Cerere personal — {order['company']}"
        msg["From"] = f"Tudor InterJob <{SENDER_EMAIL}>"
        msg["To"] = SOLONET_EMAIL
        msg["Bcc"] = SENDER_EMAIL

        password = env.get("GMAIL_MANPOWERDRISTOR_APP_PASSWORD", "")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as smtp:
            smtp.login(SENDER_EMAIL, password)
            smtp.send_message(msg)

        cur.execute("""UPDATE solonet_orders SET status='sent', sent_at=NOW()
            WHERE id=%s""", (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        log(f"Sent to solonet: #{order_id} {order['company']}")
        return f"Sent to Adrian: {order['company']}"
    except Exception as e:
        log(f"Send error: {e}")
        return f"Error: {e}"


def skip_order(order_id):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("UPDATE solonet_orders SET status='skipped' WHERE id=%s", (order_id,))
        conn.commit()
        cur.close()
        conn.close()
        return "Skipped"
    except Exception as e:
        return f"Error: {e}"


def mark_placed(order_id, workers=0, revenue=0):
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""UPDATE solonet_orders SET status='placed',
            placed_workers=%s, revenue_eur=%s WHERE id=%s""",
            (workers, revenue, order_id))
        conn.commit()
        cur.close()
        conn.close()
        return f"Marked placed: {workers} workers, EUR {revenue}"
    except Exception as e:
        return f"Error: {e}"


def get_status():
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""SELECT status, COUNT(*) FROM solonet_orders
            GROUP BY status ORDER BY count DESC""")
        counts = cur.fetchall()
        cur.execute("""SELECT id, company, contact_email, status, positions,
            created_at::date FROM solonet_orders
            ORDER BY created_at DESC LIMIT 10""")
        recent = cur.fetchall()
        cur.execute("SELECT COALESCE(SUM(revenue_eur),0) FROM solonet_orders")
        revenue = cur.fetchone()[0]
        cur.execute("SELECT COALESCE(SUM(placed_workers),0) FROM solonet_orders")
        placed = cur.fetchone()[0]
        cur.close()
        conn.close()
        lines = [f"SOLONET ORDERS:"]
        for s, c in counts:
            lines.append(f"  {s}: {c}")
        lines.append(f"  Total placed: {placed} workers")
        lines.append(f"  Total revenue: EUR {revenue}")
        lines.append(f"\nRecent:")
        for oid, comp, email, st, pos, dt in recent:
            lines.append(f"  #{oid} {comp} [{st}] {(pos or '')[:30]}")
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


def check_followups():
    """Alert if sent orders have no response after 3 days."""
    try:
        conn = db_conn()
        cur = conn.cursor()
        cur.execute("""SELECT id, company, contact_email, sent_at
            FROM solonet_orders
            WHERE status='sent' AND sent_at < NOW() - INTERVAL '3 days'""")
        overdue = cur.fetchall()
        cur.close()
        conn.close()
        for oid, comp, email, sent in overdue:
            alert(f"⏰ <b>FOLLOW UP</b> — solonet hasn't responded\n"
                  f"#{oid} {comp} ({email})\n"
                  f"Sent: {sent.strftime('%Y-%m-%d')}\n"
                  f"/solonet_responded_{oid} — mark responded")
    except Exception:
        pass


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(get_status())
    elif sys.argv[1] == "send" and len(sys.argv) > 2:
        print(send_to_solonet(int(sys.argv[2])))
    elif sys.argv[1] == "skip" and len(sys.argv) > 2:
        print(skip_order(int(sys.argv[2])))
    elif sys.argv[1] == "placed" and len(sys.argv) > 2:
        w = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        r = float(sys.argv[4]) if len(sys.argv) > 4 else 0
        print(mark_placed(int(sys.argv[2]), w, r))
    elif sys.argv[1] == "followups":
        check_followups()
    elif sys.argv[1] == "status":
        print(get_status())
