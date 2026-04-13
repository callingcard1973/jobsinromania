#!/usr/bin/env python3
"""Night summary email report for website automation tasks."""
import json, re, smtplib, logging
from datetime import datetime
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from db_client import get_conn, safe_insert
except ImportError:
    def get_conn(*args, **kwargs): return None
    def safe_insert(*args, **kwargs): return False

WEBPAGES_DIR = Path(__file__).parent
LOGS_DIR = WEBPAGES_DIR / "logs"
REPORT_EMAIL = "manpower.dristor@gmail.com"
TOTAL_SITES = 28
log_date = datetime.now().strftime("%Y-%m-%d")
log_file = WEBPAGES_DIR / f"send_night_summary_{log_date}.log"
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s",
                   handlers=[logging.FileHandler(log_file), logging.StreamHandler()])
logger = logging.getLogger(__name__)

def load_env():
    env = {}
    path = Path("D:/MEMORY/CLAUDE/OPT/opt/EMAIL/.env")
    if path.exists():
        with open(path) as f:
            for line in f:
                if "=" in line and not line.strip().startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
    return env

def parse_log_count(log_path, keywords):
    if not log_path.exists(): return 0
    try:
        count = 0
        with open(log_path) as f:
            for line in f:
                if all(kw.lower() in line.lower() for kw in keywords):
                    # For "Total X: N" patterns
                    m = re.search(rf'total.*?:\s*(\d+)', line.lower())
                    if m:
                        count = int(m.group(1))
                    else:
                        count += 1  # One per matching line
        return count
    except Exception as e:
        logger.warning(f"Error parsing {log_path}: {e}")
        return 0

def parse_seo_audit(json_path):
    if not json_path.exists(): return 0, []
    try:
        with open(json_path) as f:
            data = json.load(f)
        critical, issues = 0, []
        if isinstance(data, dict):
            for site, findings in data.items():
                if isinstance(findings, dict) and "critical" in findings:
                    critical += len(findings["critical"])
                    issues.extend(findings["critical"][:3])
        return critical, issues[:5]
    except Exception as e:
        logger.warning(f"Error parsing SEO: {e}")
        return 0, []

def load_alerts():
    alerts_path = WEBPAGES_DIR / "alerts.json"
    if not alerts_path.exists(): return []
    try:
        with open(alerts_path) as f:
            data = json.load(f)
        return [s for s in data.get("sites", []) if s.get("status") in ["DOWN", "SLOW"]][:10]
    except Exception as e:
        logger.warning(f"Error loading alerts: {e}")
        return []

def build_html(stats, down_sites, seo_issues):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    alert_html = ""
    if down_sites:
        alert_html = f"<div class='alert'><strong>{len(down_sites)} site(s) DOWN/SLOW:</strong><ul>"
        for site in down_sites[:10]:
            name = site.get('name', 'Unknown') if isinstance(site, dict) else site
            alert_html += f"<li>{name}</li>"
        alert_html += "</ul></div>"

    seo_html = ""
    if seo_issues:
        seo_html = "<div><h2>Top SEO Issues</h2><ol>"
        for issue in seo_issues[:5]:
            seo_html += f"<li>{issue}</li>"
        seo_html += "</ol></div>"

    return f"""<html><head><style>
body{{font-family:Arial;color:#333}}
.header{{background:#1a1a1a;color:white;padding:20px;text-align:center}}
.container{{max-width:800px;margin:20px auto;padding:20px}}
table{{width:100%;border-collapse:collapse;margin:20px 0}}
th{{background:#0066cc;color:white;padding:10px;text-align:left}}
td{{border:1px solid #ddd;padding:10px}}
tr:nth-child(even){{background:#f9f9f9}}
.stat{{font-size:24px;font-weight:bold;color:#0066cc}}
.alert{{background:#fff3cd;border-left:4px solid #ffc107;padding:15px;margin:15px 0}}
    </style></head><body>
    <div class="header"><h1>Website Automation Report</h1><p>{log_date}</p></div>
    <div class="container">
        <h2>Summary</h2>
        <table><tr><th>Metric</th><th>Count</th></tr>
        <tr><td>Articles</td><td class="stat">{stats['articles']}</td></tr>
        <tr><td>Jobs</td><td class="stat">{stats['jobs']}</td></tr>
        <tr><td>FAQs</td><td class="stat">{stats['faqs']}</td></tr>
        <tr><td>WP Fixes</td><td class="stat">{stats['wp']}</td></tr>
        <tr><td>Broken Links</td><td class="stat">{stats['links']}</td></tr>
        <tr><td>Sites Monitored</td><td class="stat">{TOTAL_SITES}</td></tr>
        </table>
        {alert_html}
        {seo_html}
        <div style="text-align:center;color:#999;font-size:12px;margin-top:30px">
            Report: {ts} | Website Automation
        </div>
    </div></body></html>"""

def send_email(html_body, env):
    subject = f"Website Automation Report — {log_date}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["To"] = REPORT_EMAIL
    msg.attach(MIMEText(html_body, "html"))

    # Try Gmail
    if "GMAIL_EMAIL" in env and "GMAIL_APP_PASSWORD" in env:
        try:
            msg["From"] = f"Website Automation <{env['GMAIL_EMAIL']}>"
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(env["GMAIL_EMAIL"], env["GMAIL_APP_PASSWORD"])
                server.sendmail(env["GMAIL_EMAIL"], REPORT_EMAIL, msg.as_string())
            logger.info(f"Email sent via Gmail to {REPORT_EMAIL}")
            return True
        except Exception as e:
            logger.warning(f"Gmail failed: {e}")

    # Try A2 Hosting
    if "SMTP_SERVER" in env and "SMTP_USER" in env:
        try:
            msg["From"] = f"Website Automation <{env['SMTP_USER']}>"
            with smtplib.SMTP(env["SMTP_SERVER"], 587) as server:
                server.starttls()
                server.login(env["SMTP_USER"], env.get("SMTP_PASSWORD", ""))
                server.sendmail(env["SMTP_USER"], REPORT_EMAIL, msg.as_string())
            logger.info(f"Email sent via A2 to {REPORT_EMAIL}")
            return True
        except Exception as e:
            logger.warning(f"A2 failed: {e}")

    logger.error("No SMTP credentials available")
    return False

def main():
    try:
        logger.info("Generating night summary...")
        LOGS_DIR.mkdir(parents=True, exist_ok=True)

        stats = {
            "articles": parse_log_count(LOGS_DIR / f"article_deployment_{log_date}.log", ["article", "deployed"]),
            "jobs": parse_log_count(LOGS_DIR / f"job_listings_{log_date}.log", ["job", "created"]),
            "faqs": parse_log_count(LOGS_DIR / f"faq_deployment_{log_date}.log", ["faq"]),
            "wp": len(list(WEBPAGES_DIR.glob("wp_seo_fix_*.log"))),
            "links": parse_log_count(LOGS_DIR / f"broken_links_fixed_{log_date}.log", ["fixed"]),
        }

        seo_crit, seo_issues = parse_seo_audit(LOGS_DIR / f"seo_audit_{log_date}.json")
        down_sites = load_alerts()

        logger.info(f"Stats: {stats}, Down: {len(down_sites)}, SEO: {seo_crit}")

        # Insert summary into database before sending email
        conn = get_conn()
        if conn:
            try:
                sql = """
                    INSERT INTO night_summary_reports (report_date, articles_deployed, jobs_created, faqs_deployed, wp_fixes_count, broken_links_fixed, sites_down_count, seo_critical_count, email_sent)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (report_date) DO UPDATE SET
                        articles_deployed=EXCLUDED.articles_deployed,
                        jobs_created=EXCLUDED.jobs_created,
                        faqs_deployed=EXCLUDED.faqs_deployed,
                        wp_fixes_count=EXCLUDED.wp_fixes_count,
                        broken_links_fixed=EXCLUDED.broken_links_fixed,
                        sites_down_count=EXCLUDED.sites_down_count,
                        seo_critical_count=EXCLUDED.seo_critical_count,
                        email_sent=EXCLUDED.email_sent
                """
                safe_insert(conn, sql, (
                    datetime.now().date(),
                    stats['articles'],
                    stats['jobs'],
                    stats['faqs'],
                    stats['wp'],
                    stats['links'],
                    len(down_sites),
                    seo_crit,
                    False
                ))
                logger.info("[DB] Night summary inserted")
            except Exception as db_err:
                logger.warning(f"[DB] Error inserting summary: {db_err}")
            finally:
                conn.close()

        html = build_html(stats, down_sites, seo_issues)
        env = load_env()
        email_sent = send_email(html, env)

        # Update email_sent flag if needed
        if email_sent:
            conn = get_conn()
            if conn:
                try:
                    sql = """
                        INSERT INTO night_summary_reports (report_date, articles_deployed, jobs_created, faqs_deployed, wp_fixes_count, broken_links_fixed, sites_down_count, seo_critical_count, email_sent)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (report_date) DO UPDATE SET
                            articles_deployed=EXCLUDED.articles_deployed,
                            jobs_created=EXCLUDED.jobs_created,
                            faqs_deployed=EXCLUDED.faqs_deployed,
                            wp_fixes_count=EXCLUDED.wp_fixes_count,
                            broken_links_fixed=EXCLUDED.broken_links_fixed,
                            sites_down_count=EXCLUDED.sites_down_count,
                            seo_critical_count=EXCLUDED.seo_critical_count,
                            email_sent=EXCLUDED.email_sent
                    """
                    safe_insert(conn, sql, (
                        datetime.now().date(),
                        stats['articles'],
                        stats['jobs'],
                        stats['faqs'],
                        stats['wp'],
                        stats['links'],
                        len(down_sites),
                        seo_crit,
                        True
                    ))
                except Exception as db_err:
                    logger.warning(f"[DB] Error updating email_sent: {db_err}")
                finally:
                    conn.close()

        logger.info("Report sent successfully")
        return 0
    except Exception as e:
        logger.exception(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
