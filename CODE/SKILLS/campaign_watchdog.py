#!/usr/bin/env python3
"""Campaign Watchdog v2 - Auto-discover and monitor all campaigns for 24h+ stalls."""
import sys
sys.stdout.reconfigure(line_buffering=True)
import os
import json
import subprocess
import smtplib
import glob
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import psycopg2

# --
ALERT_EMAIL = "manpowerdristor@gmail.com"
SMTP_CONFIG = {
    'server': 'smtp-relay.brevo.com',
    'port': 587,
    'user': '9deb7f001@smtp-brevo.com',  # Brevo SMTP user
    'password': 'xsmtpsib-3fbf722e3f56fc99dfcafc94bd8416d528a98d7fa235f8319802c099a19068b1-ARzbFWZh34RZOCzU',  # Brevo SMTP key
    'sender': 'office@mivromania.info',  # Verified sender
    'sender_name': 'InterJob Campaign Monitor'
}

def check_file_age(file_path, hours=24):
    """Check if file was modified more than X hours ago."""
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"

    modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
    age_hours = (datetime.now() - modified_time).total_seconds() / 3600

    if age_hours > hours:
        return f"Stalled {age_hours:.1f}h ago (last: {modified_time.strftime('%Y-%m-%d %H:%M')})"
    return None

def check_process_running(process_name):
    """Check if process is running."""
    try:
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if process_name in line and 'python' in line and 'grep' not in line:
                return True
        return False
    except:
        return False

def discover_campaigns():
    """Auto-discover active campaigns by scanning for state files and logs."""
    campaigns = []

    # Key scrapers to monitor
    scrapers = [
        {
            'name': 'EBRD_SCRAPER',
            'process': 'ebrd_psd_scraper',
            'log': '/opt/ACTIVE/SCRAPERS/EBRD/data/scrape.log'
        },
        {
            'name': 'BULGARIA_SCRAPER',
            'process': 'bulgaria',
            'log': '/opt/ACTIVE/SCRAPERS/EUROPE/BULGARIA/scrape.log'
        }
    ]

    for scraper in scrapers:
        campaigns.append({
            'name': scraper['name'],
            'type': 'scraper',
            'files': [scraper['log']],
            'process': scraper['process']
        })

    # Auto-discover email campaigns by finding state files
    state_patterns = [
        '/opt/ACTIVE/EMAIL/CAMPAIGNS/*/state*.json',
        '/opt/ACTIVE/EMAIL/CAMPAIGNS/*/*/state*.json',
        '/opt/ACTIVE/EMAIL/CAMPAIGNS/*/*/*/state*.json',
        '/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/*/state*.json'
    ]

    discovered_states = set()
    for pattern in state_patterns:
        for state_file in glob.glob(pattern):
            discovered_states.add(state_file)

    # Group by campaign directory
    campaign_dirs = {}
    for state_file in discovered_states:
        # Extract campaign name from path
        parts = state_file.split('/')
        if 'CAMPAIGNS' in parts:
            idx = parts.index('CAMPAIGNS')
            if idx + 1 < len(parts):
                campaign_name = parts[idx + 1]
                campaign_dir = '/'.join(parts[:idx+2])

                if campaign_name not in campaign_dirs:
                    campaign_dirs[campaign_name] = {
                        'name': f'EMAIL_{campaign_name}',
                        'type': 'email',
                        'files': [],
                        'dir': campaign_dir
                    }
                campaign_dirs[campaign_name]['files'].append(state_file)

    # Add discovered email campaigns
    campaigns.extend(campaign_dirs.values())

    # Add known active services
    services = [
        {
            'name': 'INTERJOB_MASTER_BOT',
            'type': 'service',
            'files': ['/opt/ACTIVE/TELEGRAM/interjob_master_bot.log'],
            'process': 'interjob_master_bot'
        },
        {
            'name': 'EVENT_PUBLISHER',
            'type': 'service',
            'files': ['/opt/ACTIVE/event_publisher/event_publisher.log'],
            'process': 'event_publisher'
        }
    ]

    campaigns.extend(services)
    return campaigns

def check_campaign_status(campaign):
    """Check individual campaign status."""
    issues = []

    # Check process if specified
    if 'process' in campaign and campaign['process']:
        if not check_process_running(campaign['process']):
            issues.append(f"Process '{campaign['process']}' not running")

    # Check file ages
    for file_path in campaign.get('files', []):
        if file_path:  # Only check non-empty paths
            file_issue = check_file_age(file_path, 24)
            if file_issue:
                issues.append(f"File {os.path.basename(file_path)}: {file_issue}")

    return issues

def get_database_stats():
    """Get quick database stats for the alert."""
    try:
        conn = psycopg2.connect(
            host='localhost',
            database='interjob_master',
            user='tudor',
            password='tudor'
        )
        cur = conn.cursor()

        # Get campaign send counts from last 24h
        cur.execute("""
            SELECT campaign, COUNT(*) as sent_24h
            FROM email_campaigns
            WHERE sent_at >= NOW() - INTERVAL '24 hours'
            GROUP BY campaign
            ORDER BY sent_24h DESC
            LIMIT 10
        """)
        recent_sends = dict(cur.fetchall())

        # Get total companies
        cur.execute("SELECT COUNT(*) FROM companies")
        total_companies = cur.fetchone()[0]

        conn.close()
        return recent_sends, total_companies
    except Exception as e:
        return {}, f"DB Error: {e}"

def send_alert_email(stalled_campaigns, db_stats):
    """Send email alert about stalled campaigns."""
    recent_sends, total_companies = db_stats

    subject = f"🚨 CAMPAIGN ALERT: {len(stalled_campaigns)} Stalled Campaign(s)"

    body = f"""Campaign Watchdog Alert - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

STALLED CAMPAIGNS (>24h inactive):
{'='*50}
"""

    for campaign_name, issues in stalled_campaigns.items():
        body += f"\n❌ {campaign_name}:\n"
        for issue in issues:
            body += f"   • {issue}\n"

    body += f"""
DATABASE STATS (Last 24h):
{'='*30}
"""
    if isinstance(recent_sends, dict):
        if recent_sends:
            for campaign, count in recent_sends.items():
                body += f"✅ {campaign}: {count:,} emails sent\n"
        else:
            body += "⚠️  No emails sent in last 24h\n"

        # Fix the formatting issue with total_companies
        if isinstance(total_companies, (int, float)):
            body += f"\nTotal companies in DB: {total_companies:,}\n"
        else:
            body += f"\nTotal companies in DB: {total_companies}\n"
    else:
        body += f"Database connection issue: {recent_sends}\n"

    body += f"""
ACTIONS TO TAKE:
{'='*20}
1. SSH to raspibig: ssh tudor@192.168.100.21
2. Check processes: ps aux | grep -E "(campaign|scraper|bot)"
3. Check logs: tail /opt/ACTIVE/*/logs/*.log
4. Restart services: systemctl restart interjob-master-bot
5. Check Node-RED: http://192.168.100.21:1880

Generated by: {os.path.basename(__file__)} on raspibig
Time: {datetime.now().isoformat()}
"""

    # Send email
    try:
        msg = MIMEMultipart()
        msg['From'] = f"{SMTP_CONFIG['sender_name']} <{SMTP_CONFIG['sender']}>"
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(SMTP_CONFIG['server'], SMTP_CONFIG['port'])
        server.starttls()
        server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
        server.send_message(msg)
        server.quit()

        print(f"✅ Alert email sent to {ALERT_EMAIL}")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

def main():
    print(f"Campaign Watchdog v2 starting - {datetime.now()}")

    # Auto-discover campaigns
    campaigns = discover_campaigns()
    print(f"📊 Monitoring {len(campaigns)} campaigns/services")

    stalled_campaigns = {}
    healthy_count = 0

    for campaign in campaigns:
        issues = check_campaign_status(campaign)
        if issues:
            stalled_campaigns[campaign['name']] = issues
            print(f"❌ {campaign['name']}: {'; '.join(issues)}")
        else:
            healthy_count += 1
            print(f"✅ {campaign['name']}: OK")

    print(f"\n📈 Summary: {healthy_count} healthy, {len(stalled_campaigns)} stalled")

    if stalled_campaigns:
        print(f"\n🚨 {len(stalled_campaigns)} campaigns stalled - sending alert!")
        db_stats = get_database_stats()
        if send_alert_email(stalled_campaigns, db_stats):
            print("✅ Alert sent successfully")
        else:
            print("❌ Failed to send alert email")
    else:
        print("✅ All campaigns healthy")

if __name__ == "__main__":
    main()