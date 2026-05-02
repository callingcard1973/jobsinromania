#!/usr/bin/env python3
"""
Morning Report - Summary of overnight activity sent at 7am
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from alerting import send_telegram

def get_scraper_summary():
    """Get overnight scraper activity."""
    logs_dir = Path('/opt/ACTIVE/INFRA/LOGS/scrapers')
    today = datetime.now().strftime('%Y%m%d')
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y%m%d')
    
    summary = []
    for pattern in [today, yesterday]:
        for log in logs_dir.glob(f'*{pattern}*.log'):
            size = log.stat().st_size
            name = log.stem.replace(f'_{pattern}', '')
            if size > 100:
                summary.append(f"✓ {name}: {size//1024}KB")
    
    return summary[:10] if summary else ["No scraper activity"]

def get_campaign_summary():
    """Get email sends from overnight."""
    campaigns_dir = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS')
    today = datetime.now().strftime('%Y%m%d')
    
    total = 0
    details = []
    
    for camp in campaigns_dir.iterdir():
        if not camp.is_dir():
            continue
        log = camp / 'logs' / f'sent_{today}.log'
        if log.exists():
            sent = log.read_text().count('| OK |')
            if sent > 0:
                details.append(f"  {camp.name}: {sent}")
                total += sent
    
    return total, details

def check_issues():
    """Check for any current issues."""
    issues = []
    
    # Check global lock
    lock = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK')
    if lock.exists() and lock.read_text().strip():
        issues.append("⚠️ Campaign lock active")
    
    # Check disk
    import subprocess
    result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
    for line in result.stdout.split('\n')[1:]:
        if line:
            usage = int(line.split()[4].replace('%', ''))
            if usage > 80:
                issues.append(f"⚠️ Disk {usage}% full")
    
    return issues

def main():
    msg = f"☀️ MORNING REPORT - {datetime.now():%Y-%m-%d}\n\n"
    
    # Scrapers
    scrapers = get_scraper_summary()
    msg += "📊 SCRAPERS:\n" + "\n".join(scrapers) + "\n\n"
    
    # Campaigns
    total, details = get_campaign_summary()
    msg += f"📧 EMAILS: {total} sent\n"
    if details:
        msg += "\n".join(details) + "\n"
    msg += "\n"
    
    # Issues
    issues = check_issues()
    if issues:
        msg += "⚠️ ISSUES:\n" + "\n".join(issues) + "\n"
    else:
        msg += "✅ No issues detected\n"
    
    print(msg)
    send_telegram(msg)

if __name__ == '__main__':
    main()
