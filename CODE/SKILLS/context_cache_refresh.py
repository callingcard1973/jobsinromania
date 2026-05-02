#!/usr/bin/env python3
"""
Context Cache Refresh - Pre-populates /tmp/claude_context for any Claude session
Run on boot or manually to reduce Claude token usage.
"""
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

CACHE_DIR = Path('/tmp/claude_context')
CSV_SUMMARIES = CACHE_DIR / 'csv_summaries'

def ensure_dirs():
    """Create cache directories."""
    CACHE_DIR.mkdir(exist_ok=True)
    CSV_SUMMARIES.mkdir(exist_ok=True)

def write_paths():
    """Write key paths."""
    content = """# Key Paths - Pre-loaded context
PYTHON=/opt/ACTIVE/INFRA/venv/bin/python3
SKILLS=/opt/ACTIVE/INFRA/SKILLS
SCRAPERS=/opt/ACTIVE/SCRAPERS/EUROPE
DATA=/opt/ACTIVE/OPENDATA/DATA
CAMPAIGNS=/opt/ACTIVE/EMAIL/CAMPAIGNS
SHARED=/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED
LOGS=/opt/ACTIVE/INFRA/LOGS
EMAIL_ENV=/opt/ACTIVE/EMAIL/CAMPAIGNS/.env
MASTER_ENV=/opt/.env.master
APPLICANTS=/opt/APPLICANTS
"""
    (CACHE_DIR / 'paths.txt').write_text(content)

def write_senders():
    """Write email sender reference."""
    content = """# Email Senders - Pre-loaded context
# A2 SMTP (500/day each, dedicated IP)
a2_factoryjobs=office@factoryjobs.eu
a2_warehouseworkers=office@warehouseworkers.eu
a2_horecaworkers=office@horecaworkers.eu
a2_meatworkers=office@meatworkers.eu
a2_electricjobs=office@electricjobs.eu
a2_mechanicjobs=office@mechanicjobs.eu
a2_farmworkers=office@farmworkers.eu

# Brevo API (290/day each, shared IP)
brevo_buildjobs=office@buildjobs.eu
brevo_factoryjobs=office@factoryjobs.eu
brevo_careworkers=office@careworkers.eu
brevo_warehouseworkers=office@warehouseworkers.eu
brevo_mivromania=office@mivromania.info
brevo_mivromania_online=office@mivromania.online
brevo_cifn=office@cifn.info
brevo_interjob=office@interjob.ro
brevo_nepalezi=office@nepalezi.com
brevo_expatsinromania=office@expatsinromania.org

# Totals
A2_DAILY=3500
BREVO_DAILY=2600
"""
    (CACHE_DIR / 'senders.txt').write_text(content)

def write_machines():
    """Write machine reference."""
    hostname = subprocess.getoutput('hostname').strip()

    if hostname == 'raspibig':
        content = """# Machine: RASPIBIG (PRIMARY)
THIS_MACHINE=raspibig
THIS_IP=192.168.100.21
THIS_ROLE=PRIMARY - all operations (16GB RAM)

OTHER_MACHINE=raspi
OTHER_IP=192.168.100.20
OTHER_ROLE=BACKUP - archive & failover (4GB RAM)

# SSH to other
ssh_other=ssh raspi

# Sync (we push to raspi)
sync_cmd=rsync -avz /opt/ACTIVE/OPENDATA/DATA/ raspi:/opt/ACTIVE/OPENDATA/DATA/
"""
    else:
        content = """# Machine: RASPI (BACKUP)
THIS_MACHINE=raspi
THIS_IP=192.168.100.20
THIS_ROLE=BACKUP - archive & failover (4GB RAM)

OTHER_MACHINE=raspibig
OTHER_IP=192.168.100.21
OTHER_ROLE=PRIMARY - all operations (16GB RAM)

# SSH to other
ssh_other=ssh raspibig

# Sync (we pull from raspibig)
sync_cmd=rsync -avz raspibig:/opt/ACTIVE/OPENDATA/DATA/ /opt/ACTIVE/OPENDATA/DATA/
"""
    (CACHE_DIR / 'machines.txt').write_text(content)

def write_typo_domains():
    """Write typo domain mappings."""
    content = """# Typo Domains - Auto-fix mapping
gamil.com=gmail.com
gmial.com=gmail.com
gmal.com=gmail.com
gnail.com=gmail.com
gmai.com=gmail.com
gmail.ro=gmail.com
gmail.co=gmail.com
hotmal.com=hotmail.com
hotmai.com=hotmail.com
hotmial.com=hotmail.com
outlok.com=outlook.com
outloo.com=outlook.com
yaho.com=yahoo.com
yahooo.com=yahoo.com
yhoo.com=yahoo.com
"""
    (CACHE_DIR / 'typo_domains.txt').write_text(content)

def write_skills_index():
    """Write quick skills lookup."""
    content = """# Quick Skills Index - Pre-loaded context
# Format: task=script

csv_analyze=csv_summarizer.py
csv_dedupe=contact_dedup.py
csv_quality=data_quality_checker.py
typo_fix=fix_typo_emails.py
health=health_monitor.py
campaigns=email_campaign_tracker.py
bounce=bounce_manager.py
feed_campaigns=scraper_to_campaigns.py
capacity=system_capacity.py
brevo_warmup=brevo_warmup.py
a2_warmup=a2_warmup.py
scraper_watch=scraper_watchdog.py
backup=backup_restore.py
sync=sync_manager.py
anaf=anaf_api.py
onrc=onrc_filter.py
enrich=fuzzy_enrich.py
normalize=normalize_export.py
"""
    (CACHE_DIR / 'skills_index.txt').write_text(content)

def write_websites():
    """Write websites context."""
    content = """# Websites Context - Pre-loaded
BASE=/opt/ACTIVE/WEB/WEBSITES

# Active Sites
factoryjobs.eu=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu
weddnesday.org=/opt/ACTIVE/WEB/WEBSITES/weddnesday.org

# Factoryjobs Structure
factoryjobs_jobs=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/jobs
factoryjobs_data=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/jobs/data
factoryjobs_fetched=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/fetched
factoryjobs_articles=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/articles
factoryjobs_ukcodes=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/uk-codes

# Key Files
translations_json=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/jobs/data/translations.json
jobs_seen_db=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/fetched/jobs_seen.db
north_macedonia_db=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/fetched/north_macedonia.db

# Deploy Scripts
deploy_a2=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/jobs/deploy_to_a2.sh
upload_cpanel=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/jobs/upload_cpanel.py
generate_pages=/opt/ACTIVE/WEB/WEBSITES/factoryjobs.eu/jobs/generate_pages.py

# Backups (24 domains)
backups=/opt/ACTIVE/WEB/WEBSITES/.backups
backup_domains=buildjobs.eu,careworkers.eu,electricjobs.eu,factoryjobs.eu,farmworkers.eu,horecaworkers.eu,interjob.ro,meatworkers.eu,mechanicjobs.eu,warehouseworkers.eu,cifn.info,expatsinromania.org,mivromania.com,mivromania.info,mivromania.online,nepalezi.com,cumparlegume.com,haritina.com,seicarescu.com,baneasa39.com,agroevolution.com,ajwang.org,aluminumrecyclehub.com,weddnesday.org

# Landing Pages (factoryjobs.eu)
landing_pages=ig.html,ln.html,om.html,so.html,ta.html,te.html,ti.html,wo.html,yo.html,jobs.html
"""
    (CACHE_DIR / 'websites.txt').write_text(content)

def write_status():
    """Write current system status."""
    status = {
        'refreshed': datetime.now().isoformat(),
        'machine': subprocess.getoutput('hostname'),
        'disk_free_gb': int(subprocess.getoutput("df -BG /opt | tail -1 | awk '{print $4}'").replace('G', '')),
    }
    (CACHE_DIR / 'status.json').write_text(json.dumps(status, indent=2))

def main():
    """Refresh all context files."""
    ensure_dirs()
    write_paths()
    write_senders()
    write_machines()
    write_typo_domains()
    write_skills_index()
    write_websites()
    write_status()
    print(f"Context cache refreshed: {CACHE_DIR}")

if __name__ == '__main__':
    main()
