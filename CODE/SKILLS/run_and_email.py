#!/usr/bin/env python3
"""
Run a skill script and email results via Brevo
Usage: python3 run_and_email.py <script_name> [args...]
"""
import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
from skills_common import to_ascii, sanitize, FIELD_LIMITS

import subprocess
import os
from datetime import datetime
import requests

BREVO_API_KEY = os.getenv("BREVO_BUILDJOBS_API_KEY", "")
TO_EMAIL = "office@interjob.ro"
FROM_EMAIL = "noreply@buildjobs.eu"
FROM_NAME = "RaspiBig Skills"

SCRIPTS = {
    # Analytics (automated)
    'master_contacts': ('/opt/ACTIVE/INFRA/SKILLS/master_contacts.py', ['--full']),
    'campaign_analytics': ('/opt/ACTIVE/INFRA/SKILLS/campaign_analytics.py', ['/mnt/hdd/SCRAPER_DATA/csv/Norway_MASTER_50.csv']),
    'scraper_quality': ('/opt/ACTIVE/INFRA/SKILLS/scraper_quality.py', ['/mnt/hdd/SCRAPER_DATA/csv/Poland_contacts_50.csv']),
    'email_health': ('/opt/ACTIVE/INFRA/SKILLS/email_health.py', ['30']),
    'contact_dedup': ('/opt/ACTIVE/INFRA/SKILLS/contact_dedup.py', []),
    # Code analysis (automated)
    'code_audit': ('/opt/ACTIVE/INFRA/SKILLS/code_execution.py', ['audit', '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE']),
    'unused_imports': ('/opt/ACTIVE/INFRA/SKILLS/code_execution.py', ['find-unused', '/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE']),
    # Brainstorming (use --country or --name for non-interactive)
    'brainstorm_scraper': ('/opt/ACTIVE/INFRA/SKILLS/brainstorm_scraper.py', ['--country', 'template']),
    'brainstorm_campaign': ('/opt/ACTIVE/INFRA/SKILLS/brainstorm_campaign.py', ['--name', 'template']),
}

# For scripts needing file args, find latest CSVs dynamically
def get_latest_csv(pattern_dir, prefix=None):
    """Find most recent CSV in directory"""
    import glob
    from pathlib import Path
    csvs = glob.glob(f"{pattern_dir}/*.csv")
    if prefix:
        csvs = [c for c in csvs if Path(c).name.startswith(prefix)]
    if csvs:
        return max(csvs, key=os.path.getmtime)
    return None

def send_email(subject, body):
    """Send email via Brevo API"""
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": BREVO_API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "sender": {"name": FROM_NAME, "email": FROM_EMAIL},
        "to": [{"email": TO_EMAIL}],
        "subject": subject,
        "textContent": body
    }
    try:
        r = requests.post(url, json=data, headers=headers, timeout=30)
        return r.status_code == 201
    except Exception as e:
        print(f"Email error: {e}")
        return False

def run_script(name, extra_args=None):
    """Run a skill script and capture output"""
    if name not in SCRIPTS:
        return f"Unknown script: {name}", False

    script_path, default_args = SCRIPTS[name]

    # Special handling for contact_dedup - find top CSV files
    if name == 'contact_dedup' and not extra_args:
        import glob
        csvs = glob.glob('/mnt/hdd/SCRAPER_DATA/csv/*MASTER*.csv')
        if not csvs:
            csvs = glob.glob('/mnt/hdd/SCRAPER_DATA/csv/*.csv')[:5]
        args = csvs[:5]  # Top 5 master CSVs
    else:
        args = extra_args if extra_args else default_args

    cmd = ['/opt/ACTIVE/INFRA/venv/bin/python3', script_path] + args

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        output = result.stdout + result.stderr
        success = result.returncode == 0
        return output, success
    except subprocess.TimeoutExpired:
        return "Script timed out after 30 minutes", False
    except Exception as e:
        return f"Error: {e}", False

def generate_proposals(name, output):
    """Generate proposals based on script output"""
    proposals = []

    if name == 'master_contacts':
        if 'Unique emails:' in output:
            proposals.append("- Consider running contact_dedup to merge duplicates")
        if 'CROSS-FILE DUPLICATES:' in output:
            proposals.append("- Review cross-file duplicates for data consolidation")
        if 'Corporate:' in output:
            proposals.append("- Focus campaigns on corporate emails for better engagement")

    elif name == 'email_health':
        if 'BOUNCE RATE:' in output:
            try:
                rate = int(output.split('BOUNCE RATE:')[1].split('%')[0].strip())
                if rate > 10:
                    proposals.append(f"- High bounce rate ({rate}%) - clean email lists")
                if rate > 20:
                    proposals.append("- URGENT: Bounce rate critical, pause campaigns")
            except: pass

    elif name == 'scraper_quality':
        if 'invalid' in output.lower():
            proposals.append("- Review invalid entries in scraper output")
        if 'DUPLICATE ROWS:' in output and 'DUPLICATE ROWS: 0' not in output:
            proposals.append("- Deduplicate scraper output before using")

    elif name == 'code_audit':
        if 'health_score:' in output:
            try:
                score = int(output.split('health_score:')[1].split()[0])
                if score < 50:
                    proposals.append(f"- Code health score is low ({score}) - review complex functions")
                if score < 30:
                    proposals.append("- URGENT: Major refactoring needed")
            except: pass
        if 'complex_functions_count:' in output:
            try:
                count = int(output.split('complex_functions_count:')[1].split()[0])
                if count > 10:
                    proposals.append(f"- {count} complex functions detected - consider breaking them down")
            except: pass
        if 'large_files_count:' in output:
            try:
                count = int(output.split('large_files_count:')[1].split()[0])
                if count > 5:
                    proposals.append(f"- {count} large files (>500 lines) - consider splitting")
            except: pass

    elif name == 'unused_imports':
        if 'Files with unused imports:' in output:
            try:
                count = int(output.split('Files with unused imports:')[1].split()[0])
                if count > 20:
                    proposals.append(f"- {count} files have unused imports - run cleanup")
                if count > 50:
                    proposals.append("- High number of unused imports affecting code quality")
            except: pass

    if not proposals:
        proposals.append("- No immediate actions required")

    return "\n".join(proposals)

def main():
    if len(sys.argv) < 2:
        print("Usage: run_and_email.py <script_name> [args...]")
        print(f"Available: {', '.join(SCRIPTS.keys())}")
        sys.exit(1)

    name = sys.argv[1]
    extra_args = sys.argv[2:] if len(sys.argv) > 2 else None

    print(f"Running {name}...")
    output, success = run_script(name, extra_args)

    # Generate proposals
    proposals = generate_proposals(name, output)

    # Build email
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    status = "SUCCESS" if success else "FAILED"
    subject = f"[RaspiBig] {name} - {status} - {timestamp}"

    body = f"""SKILL: {name}
STATUS: {status}
TIME: {timestamp}
HOST: raspibig

{'='*60}
OUTPUT:
{'='*60}

{output[:15000]}

{'='*60}
PROPOSALS:
{'='*60}

{proposals}

---
Automated report from /opt/ACTIVE/INFRA/SKILLS/
"""

    # Send email
    if send_email(subject, body):
        print(f"Email sent to {TO_EMAIL}")
    else:
        print("Failed to send email")

    print(output)

if __name__ == '__main__':
    main()
