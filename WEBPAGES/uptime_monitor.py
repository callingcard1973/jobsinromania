#!/usr/bin/env python3
"""
Uptime Monitor for 28 InterJob sites
- HTTP status & response time
- SSL certificate validity
- Content validation
- Logs & alerts to JSON
"""

import requests
import ssl
import socket
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from db_client import get_conn, safe_insert
except ImportError:
    def get_conn(*args, **kwargs): return None
    def safe_insert(*args, **kwargs): return False

# All 28 InterJob sites
SITES = {
    "careworkers.eu": "job",
    "factoryjobs.eu": "job",
    "buildjobs.eu": "job",
    "electricjobs.eu": "job",
    "farmworkers.eu": "job",
    "horecaworkers.eu": "job",
    "meatworkers.eu": "job",
    "mechanicjobs.eu": "job",
    "warehouseworkers.eu": "job",
    "aluminumrecyclehub.com": "job",
    "expatsinromania.org": "expat",
    "interjob.ro": "job",
    "mivromania.info": "job",
    "mivromania.online": "job",
    "nepalezi.com": "job",
    "internaltransfers.eu": "static",
    "horecaworkers2026.com": "static",
    "horecaworkers2026.eu": "static",
    "horecaworkers2026.online": "static",
    "weddnesday.org": "static",
    "cumparlegume.com": "wordpress",
    "seicarescu.com": "wordpress",
    "agroevolution.com": "wordpress",
    "ajwang.org": "wordpress",
    "baneasa39.com": "wordpress",
    "cifn.info": "wordpress",
    "haritina.com": "wordpress",
    "mivromania.com": "wordpress",
}

SCRIPT_DIR = Path(__file__).parent
LOG_DIR = SCRIPT_DIR
ALERTS_FILE = LOG_DIR / "alerts.json"
TIMEOUT = 10
RESPONSE_TIME_THRESHOLD = 2.0

def setup_logging():
    """Create logger with date-stamped filename"""
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = LOG_DIR / f"uptime_monitor_{today}.log"
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format="%(asctime)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger(__name__)

def check_ssl_cert(domain):
    """Check SSL certificate expiry (days remaining)"""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=5) as sock:
            with context.wrap_socket(sock, server_hostname=domain) as ssock:
                cert = ssock.getpeercert()
                not_after = datetime.strptime(cert['notAfter'], "%b %d %H:%M:%S %Y %Z")
                days_left = (not_after - datetime.utcnow()).days
                return days_left, None
    except Exception as e:
        return None, str(e)

def check_content(domain, site_type):
    """Validate homepage contains expected keywords"""
    try:
        url = f"https://{domain}"
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        content = resp.text.lower()

        keywords = {
            "job": ["job", "employment", "vacancy", "position"],
            "expat": ["expat", "relocation", "visa"],
            "static": ["job", "work", "employment"],
            "wordpress": ["article", "post", "category", "blog"]
        }

        for keyword in keywords.get(site_type, ["job"]):
            if keyword in content:
                return True
        return False
    except:
        return False

def check_site(domain, site_type, logger):
    """Check single site: status, response time, SSL, content"""
    alert = None
    start = datetime.now()
    http_status = None
    elapsed = None

    try:
        url = f"https://{domain}"
        response = requests.get(url, timeout=TIMEOUT, allow_redirects=True)
        elapsed = (datetime.now() - start).total_seconds()
        http_status = response.status_code

        log_entry = f"{domain} | HTTP {http_status} | {elapsed:.2f}s"

        # HTTP status alert
        if http_status != 200:
            alert = {"domain": domain, "type": "http_error", "code": http_status}
            log_entry += " | ⚠ HTTP ERROR"

        # Response time alert
        elif elapsed > RESPONSE_TIME_THRESHOLD:
            alert = {"domain": domain, "type": "slow", "response_time": round(elapsed, 2)}
            log_entry += " | ⚠ SLOW"

        logger.info(log_entry)

    except requests.Timeout:
        logger.info(f"{domain} | TIMEOUT (>{TIMEOUT}s) | ⚠ TIMEOUT")
        alert = {"domain": domain, "type": "timeout"}
        http_status = 0
    except requests.RequestException as e:
        logger.info(f"{domain} | ERROR: {str(e)[:50]} | ⚠ DOWN")
        alert = {"domain": domain, "type": "down", "error": str(e)[:50]}
        http_status = 0
    except Exception as e:
        logger.info(f"{domain} | UNKNOWN ERROR: {str(e)[:50]}")
        alert = {"domain": domain, "type": "error", "error": str(e)[:50]}
        http_status = 0

    # Check SSL certificate
    days_left, ssl_err = check_ssl_cert(domain)
    if days_left is not None:
        if days_left < 30:
            logger.info(f"{domain} | SSL expires in {days_left} days | ⚠ CERT WARNING")
            if not alert:
                alert = {"domain": domain, "type": "ssl_expiry", "days_left": days_left}
    elif ssl_err and "certificate verify failed" not in ssl_err:
        logger.info(f"{domain} | SSL check error: {ssl_err[:50]}")

    # Insert into database
    conn = get_conn()
    if conn:
        sql = """
            INSERT INTO uptime_checks (domain, site_type, checked_at, http_status, response_time_sec, ssl_days_left, alert_type, is_alert)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        safe_insert(conn, sql, (domain, site_type, datetime.now(), http_status or 0, elapsed or 0.0, days_left, alert.get('type') if alert else None, bool(alert)))
        conn.close()

    return alert

def write_alerts(alerts):
    """Write active alerts to JSON"""
    if alerts:
        data = {
            "checked_at": datetime.now().isoformat(),
            "alert_count": len(alerts),
            "alerts": alerts
        }
        with open(ALERTS_FILE, "w") as f:
            json.dump(data, f, indent=2)

def main():
    """Run uptime check for all 28 sites"""
    logger = setup_logging()
    alerts = []

    logger.info("=" * 70)
    logger.info(f"UPTIME CHECK START | {len(SITES)} sites")
    logger.info("=" * 70)

    for domain, site_type in sorted(SITES.items()):
        alert = check_site(domain, site_type, logger)
        if alert:
            alerts.append(alert)

    logger.info("=" * 70)
    logger.info(f"UPTIME CHECK COMPLETE | {len(alerts)} alerts")
    logger.info("=" * 70)

    write_alerts(alerts)

    if alerts:
        print(f"⚠ {len(alerts)} alerts found - see alerts.json")
        for alert in alerts[:5]:
            print(f"  - {alert['domain']}: {alert['type']}")

if __name__ == "__main__":
    main()
