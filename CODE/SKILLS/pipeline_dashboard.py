#!/usr/bin/env python3
"""
Unified Pipeline Dashboard - End-to-end view of scrapers, data, campaigns, and sending.

Combines:
- Scraper health (from scraper_monitor.py)
- Campaign stats (from campaign_stats.py)
- Sender capacity (from sender_dashboard.py)
- Global sent tracker (from global_sent_tracker.py)
- Data source inventory

Usage:
    python3 pipeline_dashboard.py           # Full dashboard
    python3 pipeline_dashboard.py --summary # Quick summary only
    python3 pipeline_dashboard.py --json    # JSON output
    python3 pipeline_dashboard.py --section scrapers|data|campaigns|sending
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')
sys.path.insert(0, '/opt/ACTIVE/EMAIL/CAMPAIGNS/SCRIPTS')
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')

from skills_common import to_ascii

import os
import glob
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ============================================================
# CONFIGURATION
# ============================================================

DATA_SOURCES = {
    'MASTER_ALL': '/opt/ACTIVE/OPENDATA/DATA/MASTER_ALL.csv',
    'DSVSA': '/opt/ACTIVE/OPENDATA/DATA/SCRAPERS/DSVSA/DSVSA_MASTER.csv',
    'CQC': '/opt/ACTIVE/OPENDATA/DATA/CQC_MASTER.csv',
    'EU_AGRI': '/opt/ACTIVE/OPENDATA/DATA/EU_AGRI_DATABASE/eu_agri_coops_contacts.csv',
    'DENMARK': '/opt/ACTIVE/OPENDATA/DATA/SCRAPERS/DENMARK/Denmark_MASTER_50.csv',
    'ANOFM': '/opt/ACTIVE/OPENDATA/DATA/ANOFM/anofm_employers.csv',
}

CAMPAIGNS_DIR = '/opt/ACTIVE/EMAIL/CAMPAIGNS'
GLOBAL_SENT_DB = '/opt/ACTIVE/OPENDATA/DATA/global_sent.db'
BREVO_STATE_DIR = '/opt/ACTIVE/OPENDATA/DATA/brevo_state'

# ANOFM Brevo campaigns with their sector assignments (32 sectors -> 7 campaigns, 3 excluded)
ANOFM_CAMPAIGNS = {
    'WAREHOUSEWORKERS': {'script': 'brevo_warehouseworkers.py', 'sender': 'warehouseworkers.eu', 'sectors': ['COMERT', 'Retail', 'Vanzari']},
    'FACTORYJOBS': {'script': 'brevo_factoryjobs.py', 'sender': 'factoryjobs.eu', 'sectors': ['Productie', 'FABRICAREA', 'MOBILA']},
    'BUILDJOBS': {'script': 'brevo_buildjobs.py', 'sender': 'buildjobs.eu', 'sectors': ['Constructii']},
    'CUMPARLEGUME': {'script': 'brevo_cumparlegume.py', 'sender': 'cumparlegume.com', 'sectors': ['Agricultura', 'Turism', 'RESTAURANTE']},
    'CAREWORKERS': {'script': 'brevo_careworkers.py', 'sender': 'careworkers.eu', 'sectors': ['Medicina', 'Sociala']},
    'CIFN': {'script': 'brevo_cifn.py', 'sender': 'cifn.info', 'sectors': ['Transport', 'Paza']},
    'MIVROMANIA': {'script': 'brevo_mivromania.py', 'sender': 'mivromania.info', 'sectors': ['AUTO', 'Altele', '+8 misc']},
}

SENDER_LIMITS = {
    "brevo_interjob": 290,
    "brevo_interjob_horeca": 290,
    "brevo_nepalezi": 290,
    "brevo_agroevolution": 290,
    "brevo_cumparlegume": 290,
    "brevo_seicarescu": 290,
    "brevo_expatsinromania": 290,
    "brevo_mivromania": 290,
    "brevo_mivromania_online": 290,
    "brevo_aluminumrecyclehub": 290,
    "brevo_baneasa39": 290,
    "brevo_haritina": 290,
    "brevo_cifn": 290,
    "brevo_factoryjobs": 290,
    "brevo_warehouseworkers": 290,
    "gmail_manpowerdristor": 100,
    "gmail_elenamanpowerdristor": 100,
    "gmail_expatsinromania": 100,
    "gmail_cumparlegume": 100,
    "gmail_casafaurbucuresti": 50,
    "yahoo_secretariatagentieasia": 30,
}

# ============================================================
# DATA COLLECTION FUNCTIONS
# ============================================================

def count_csv_rows(csv_path: str) -> int:
    """Count rows in CSV (excluding header)."""
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='ignore') as f:
            return max(0, sum(1 for _ in f) - 1)
    except:
        return 0


def get_file_age_days(path: str) -> Optional[float]:
    """Get file age in days."""
    try:
        mtime = os.path.getmtime(path)
        return (datetime.now().timestamp() - mtime) / 86400
    except:
        return None


def get_scraper_stats() -> Dict:
    """Get scraper statistics."""
    from scraper_monitor import get_all_status

    try:
        statuses = get_all_status()
    except:
        statuses = []

    healthy = sum(1 for s in statuses if s.get('health') == 'healthy')
    stale = sum(1 for s in statuses if s.get('health') == 'stale')
    dead = sum(1 for s in statuses if s.get('health') == 'dead')
    missing = sum(1 for s in statuses if s.get('health') in ['missing', 'no_output'])

    total_rows_24h = sum(s.get('last_output_rows', 0) for s in statuses if s.get('outputs_24h', 0) > 0)

    return {
        'total': len(statuses),
        'healthy': healthy,
        'stale': stale,
        'dead': dead,
        'missing': missing,
        'rows_24h': total_rows_24h,
        'details': statuses,
    }


def get_data_source_stats() -> Dict:
    """Get data source statistics."""
    sources = {}
    total_records = 0

    for name, path in DATA_SOURCES.items():
        if os.path.exists(path):
            rows = count_csv_rows(path)
            age = get_file_age_days(path)
            sources[name] = {
                'path': path,
                'rows': rows,
                'age_days': round(age, 1) if age else None,
                'size_mb': round(os.path.getsize(path) / 1024 / 1024, 1),
            }
            total_records += rows
        else:
            sources[name] = {'path': path, 'rows': 0, 'exists': False}

    return {
        'sources': sources,
        'total_records': total_records,
        'source_count': len([s for s in sources.values() if s.get('rows', 0) > 0]),
    }


def get_campaign_stats() -> Dict:
    """Get campaign statistics."""
    exclude = {"SCRIPTS", "ARCHIVE", "campaigns"}
    campaigns = []
    total_leads = 0
    total_sent = 0

    for item in Path(CAMPAIGNS_DIR).iterdir():
        if item.is_dir() and item.name not in exclude and not item.name.startswith("."):
            campaign = {
                'name': item.name,
                'leads': 0,
                'sent': 0,
                'segments': 0,
            }

            # Count CSV rows (check root, segments/, and contacts/)
            csv_files = list(item.glob("*.csv")) + list(item.glob("segments/*.csv")) + list(item.glob("contacts/*.csv"))
            for csv_file in csv_files:
                if not csv_file.name.startswith("."):
                    campaign['leads'] += count_csv_rows(str(csv_file))
                    campaign['segments'] += 1

            # Get sent count from state files
            state_files = list(item.glob(".*.json")) + list(item.glob("state.json"))
            for state_file in state_files:
                try:
                    with open(state_file) as f:
                        state = json.load(f)
                    sent_emails = state.get("sent_emails", {})
                    if isinstance(sent_emails, dict):
                        campaign['sent'] = len(sent_emails)
                    elif isinstance(sent_emails, list):
                        campaign['sent'] = len(sent_emails)
                except:
                    pass

            campaign['remaining'] = max(0, campaign['leads'] - campaign['sent'])
            campaigns.append(campaign)
            total_leads += campaign['leads']
            total_sent += campaign['sent']

    return {
        'campaigns': sorted(campaigns, key=lambda c: -c['leads']),
        'total_campaigns': len(campaigns),
        'total_leads': total_leads,
        'total_sent': total_sent,
        'total_remaining': total_leads - total_sent,
    }


def get_sending_stats() -> Dict:
    """Get sender capacity statistics."""
    today = datetime.now().strftime("%Y-%m-%d")
    usage = {}

    # Scan campaign state files for today's usage
    state_patterns = [
        "/opt/ACTIVE/EMAIL/CAMPAIGNS/*/.*.json",
        "/opt/ACTIVE/EMAIL/CAMPAIGNS/*/state.json",
    ]

    for pattern in state_patterns:
        for state_file in glob.glob(pattern):
            try:
                with open(state_file) as f:
                    state = json.load(f)

                # Check daily_counts
                if "daily_counts" in state:
                    day_counts = state["daily_counts"].get(today, {})
                    if isinstance(day_counts, dict):
                        for sender, count in day_counts.items():
                            usage[sender] = usage.get(sender, 0) + count

                # Check sent_emails for today
                sent_emails = state.get("sent_emails", {})
                if isinstance(sent_emails, dict):
                    for key, val in sent_emails.items():
                        if isinstance(val, dict) and val.get("date") == today:
                            sender = val.get("sender", "unknown")
                            usage[sender] = usage.get(sender, 0) + 1
            except:
                pass

    total_used = sum(usage.values())
    total_limit = sum(SENDER_LIMITS.values())

    return {
        'date': today,
        'senders_active': len(usage),
        'senders_total': len(SENDER_LIMITS),
        'used_today': total_used,
        'capacity_total': total_limit,
        'remaining': total_limit - total_used,
        'percent_used': round(100 * total_used / total_limit, 1) if total_limit > 0 else 0,
        'usage_by_sender': usage,
    }


def get_global_tracker_stats() -> Dict:
    """Get global sent tracker statistics."""
    if not os.path.exists(GLOBAL_SENT_DB):
        return {'exists': False, 'total': 0, 'today': 0}

    try:
        with sqlite3.connect(GLOBAL_SENT_DB) as conn:
            total = conn.execute("SELECT COUNT(*) FROM sent_emails").fetchone()[0]
            today = datetime.now().strftime("%Y-%m-%d")
            today_count = conn.execute(
                "SELECT COUNT(*) FROM sent_emails WHERE sent_date = ?", (today,)
            ).fetchone()[0]

            # Get last 7 days
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            week_count = conn.execute(
                "SELECT COUNT(*) FROM sent_emails WHERE sent_date >= ?", (week_ago,)
            ).fetchone()[0]

            # By campaign
            by_campaign = dict(conn.execute("""
                SELECT campaign, COUNT(*) FROM sent_emails
                GROUP BY campaign ORDER BY COUNT(*) DESC LIMIT 5
            """).fetchall())

        return {
            'exists': True,
            'total': total,
            'today': today_count,
            'week': week_count,
            'by_campaign': by_campaign,
        }
    except Exception as e:
        return {'exists': True, 'error': str(e)}


def get_anofm_campaign_stats() -> Dict:
    """Get ANOFM Brevo campaign statistics from state files (optimized - no subprocess)."""
    campaigns = []
    total_sent = 0
    total_remaining = 0
    today = datetime.now().strftime("%Y-%m-%d")

    # Estimate remaining based on source file sizes (fast)
    source_counts = {}
    try:
        anofm_dir = Path("/mnt/hdd/SCRAPER_DATA/csv/ANOFM")
        anofm_files = list(anofm_dir.glob("anofm_*.csv"))
        if anofm_files:
            latest = max(anofm_files, key=lambda f: f.name)
            with open(latest, 'r') as f:
                source_counts['anofm'] = sum(1 for _ in f) - 1
    except:
        source_counts['anofm'] = 5000  # Fallback estimate

    for name, info in ANOFM_CAMPAIGNS.items():
        state_file = Path(BREVO_STATE_DIR) / f"{name}_state.json"
        campaign = {
            'name': name,
            'sender': info['sender'],
            'sectors': info['sectors'],
            'sent': 0,
            'sent_today': 0,
            'remaining': 0,
        }

        if state_file.exists():
            try:
                with open(state_file) as f:
                    state = json.load(f)
                sent_list = state.get('sent', [])
                campaign['sent'] = len(sent_list)
                campaign['sent_today'] = state.get('sent_today', 0)
                if state.get('last_send') != today:
                    campaign['sent_today'] = 0
                # Estimate remaining (total source / num_campaigns - sent)
                est_share = source_counts.get('anofm', 5000) // len(ANOFM_CAMPAIGNS)
                campaign['remaining'] = max(0, est_share - campaign['sent'])
            except:
                pass

        total_sent += campaign['sent']
        total_remaining += campaign['remaining']
        campaigns.append(campaign)

    return {
        'campaigns': sorted(campaigns, key=lambda c: -c['remaining']),
        'total_campaigns': len(campaigns),
        'total_sent': total_sent,
        'total_remaining': total_remaining,
        'capacity_daily': len(campaigns) * 290,
    }


# ============================================================
# OUTPUT FUNCTIONS
# ============================================================

def print_section_header(title: str, char: str = "="):
    """Print section header."""
    width = 70
    print(f"\n{char * width}")
    print(f" {title}")
    print(f"{char * width}")


def print_summary(stats: Dict):
    """Print quick summary."""
    print_section_header("PIPELINE SUMMARY", "=")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    scraper = stats.get('scrapers', {})
    data = stats.get('data', {})
    campaign = stats.get('campaigns', {})
    sending = stats.get('sending', {})
    tracker = stats.get('tracker', {})

    print(f"\n  STAGE           COUNT      STATUS")
    print(f"  {'-'*50}")

    # Scrapers
    scraper_status = f"{scraper.get('healthy', 0)}/{scraper.get('total', 0)} healthy"
    print(f"  Scrapers        {scraper.get('total', 0):>6}      {scraper_status}")

    # Data sources
    print(f"  Data Sources    {data.get('source_count', 0):>6}      {data.get('total_records', 0):,} records")

    # Campaigns
    pct = round(100 * campaign.get('total_sent', 0) / campaign.get('total_leads', 1), 1)
    print(f"  Campaigns       {campaign.get('total_campaigns', 0):>6}      {campaign.get('total_leads', 0):,} leads ({pct}% sent)")

    # Sending
    print(f"  Senders         {sending.get('senders_total', 0):>6}      {sending.get('used_today', 0)}/{sending.get('capacity_total', 0)} used today")

    # Tracker
    print(f"  Global Tracker  {tracker.get('total', 0):>6}      {tracker.get('today', 0)} today, {tracker.get('week', 0)} this week")

    # Pipeline health
    print(f"\n  PIPELINE FLOW:")
    scraped = scraper.get('rows_24h', 0)
    available = data.get('total_records', 0)
    leads = campaign.get('total_leads', 0)
    sent = campaign.get('total_sent', 0)
    capacity = sending.get('remaining', 0)

    print(f"  Scraped (24h) --> Data Sources --> Campaigns --> Sent")
    print(f"       {scraped:>6}        {available:>6}        {leads:>6}      {sent:>6}")
    print(f"\n  Daily capacity remaining: {capacity:,} emails")


def print_scrapers_section(stats: Dict):
    """Print scrapers section."""
    print_section_header("SCRAPERS", "-")

    scraper = stats.get('scrapers', {})
    print(f"  Total: {scraper.get('total', 0)} | Healthy: {scraper.get('healthy', 0)} | "
          f"Stale: {scraper.get('stale', 0)} | Dead: {scraper.get('dead', 0)}")

    details = scraper.get('details', [])
    if details:
        print(f"\n  {'SCRAPER':<18} {'HEALTH':<10} {'LAST RUN':<12} {'ROWS':>8}")
        print(f"  {'-'*52}")

        health_order = {'healthy': 0, 'stale': 1, 'dead': 2, 'no_output': 3, 'missing': 4}
        for s in sorted(details, key=lambda x: health_order.get(x.get('health', 'missing'), 5))[:10]:
            health = s.get('health', 'unknown')[:8]
            last = ''
            if s.get('last_output'):
                if isinstance(s['last_output'], str):
                    last = s['last_output'][:10]
                else:
                    age = datetime.now() - s['last_output']
                    last = f"{age.days}d ago" if age.days > 0 else f"{int(age.total_seconds()/3600)}h"
            rows = s.get('last_output_rows', 0)
            print(f"  {s['name']:<18} {health:<10} {last:<12} {rows:>8}")


def print_data_section(stats: Dict):
    """Print data sources section."""
    print_section_header("DATA SOURCES", "-")

    data = stats.get('data', {})
    sources = data.get('sources', {})

    print(f"  Total: {data.get('source_count', 0)} sources | {data.get('total_records', 0):,} records")
    print(f"\n  {'SOURCE':<15} {'ROWS':>10} {'SIZE':>8} {'AGE':>8}")
    print(f"  {'-'*45}")

    for name, info in sorted(sources.items(), key=lambda x: -x[1].get('rows', 0)):
        if info.get('rows', 0) > 0:
            rows = f"{info['rows']:,}"
            size = f"{info.get('size_mb', 0):.1f}MB"
            age = f"{info.get('age_days', 0):.0f}d" if info.get('age_days') else "?"
            print(f"  {name:<15} {rows:>10} {size:>8} {age:>8}")


def print_campaigns_section(stats: Dict):
    """Print campaigns section."""
    print_section_header("CAMPAIGNS", "-")

    campaign = stats.get('campaigns', {})
    campaigns = campaign.get('campaigns', [])

    print(f"  Total: {campaign.get('total_campaigns', 0)} | Leads: {campaign.get('total_leads', 0):,} | "
          f"Sent: {campaign.get('total_sent', 0):,} | Remaining: {campaign.get('total_remaining', 0):,}")

    if campaigns:
        print(f"\n  {'CAMPAIGN':<18} {'LEADS':>10} {'SENT':>8} {'REMAIN':>10} {'%':>6}")
        print(f"  {'-'*56}")

        for c in campaigns[:8]:
            pct = round(100 * c['sent'] / c['leads'], 1) if c['leads'] > 0 else 0
            print(f"  {c['name']:<18} {c['leads']:>10,} {c['sent']:>8,} {c['remaining']:>10,} {pct:>5.1f}%")


def print_sending_section(stats: Dict):
    """Print sending section."""
    print_section_header("SENDING CAPACITY", "-")

    sending = stats.get('sending', {})

    print(f"  Date: {sending.get('date', 'N/A')}")
    print(f"  Used: {sending.get('used_today', 0)}/{sending.get('capacity_total', 0)} "
          f"({sending.get('percent_used', 0)}%)")
    print(f"  Remaining: {sending.get('remaining', 0):,} emails")
    print(f"  Active senders: {sending.get('senders_active', 0)}/{sending.get('senders_total', 0)}")

    usage = sending.get('usage_by_sender', {})
    if usage:
        print(f"\n  Top senders today:")
        for sender, count in sorted(usage.items(), key=lambda x: -x[1])[:5]:
            limit = SENDER_LIMITS.get(sender, 290)
            print(f"    {sender}: {count}/{limit}")


def print_full_dashboard(stats: Dict):
    """Print full dashboard."""
    print(f"\n{'=' * 70}")
    print(f" UNIFIED PIPELINE DASHBOARD")
    print(f" Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'=' * 70}")

    print_summary(stats)
    print_scrapers_section(stats)
    print_data_section(stats)
    print_campaigns_section(stats)
    print_sending_section(stats)

    print(f"\n{'=' * 70}\n")


# ============================================================
# MAIN
# ============================================================

def collect_all_stats() -> Dict:
    """Collect all pipeline statistics."""
    return {
        'generated': datetime.now().isoformat(),
        'scrapers': get_scraper_stats(),
        'data': get_data_source_stats(),
        'campaigns': get_campaign_stats(),
        'sending': get_sending_stats(),
        'tracker': get_global_tracker_stats(),
        'anofm': get_anofm_campaign_stats(),
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Unified Pipeline Dashboard")
    parser.add_argument("--summary", action="store_true", help="Show summary only")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--section", choices=['scrapers', 'data', 'campaigns', 'sending'],
                        help="Show specific section only")
    args = parser.parse_args()

    stats = collect_all_stats()

    if args.json:
        # Clean up non-serializable objects
        def clean_for_json(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return obj

        for scraper in stats.get('scrapers', {}).get('details', []):
            if 'last_modified' in scraper and scraper['last_modified']:
                scraper['last_modified'] = scraper['last_modified'].isoformat() if hasattr(scraper['last_modified'], 'isoformat') else str(scraper['last_modified'])
            if 'last_output' in scraper and scraper['last_output']:
                scraper['last_output'] = scraper['last_output'].isoformat() if hasattr(scraper['last_output'], 'isoformat') else str(scraper['last_output'])

        print(json.dumps(stats, indent=2, default=str))
    elif args.section:
        if args.section == 'scrapers':
            print_scrapers_section(stats)
        elif args.section == 'data':
            print_data_section(stats)
        elif args.section == 'campaigns':
            print_campaigns_section(stats)
        elif args.section == 'sending':
            print_sending_section(stats)
    elif args.summary:
        print_summary(stats)
    else:
        print_full_dashboard(stats)


if __name__ == '__main__':
    main()
