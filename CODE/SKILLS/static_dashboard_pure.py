#!/usr/bin/env python3
"""Static HTML dashboard v2 with AJAX fix buttons, live process status,
email campaign panel, scraper speed tracking, and pipeline separation."""
import os
import json
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT = "/opt/ACTIVE/INFRA/SKILLS/dashboard.html"
FIX_API = "http://192.168.100.21:8089"
ROW_HISTORY_FILE = Path("/opt/ACTIVE/OPENDATA/DATA/scraper_row_history.json")
MAX_HISTORY_ENTRIES = 72

# --- Scraper script filenames for pgrep matching ---
# Maps dashboard scraper name -> script filename (or path fragment) for process detection
SCRAPER_PGREP = {
    'ACHIZITII_PUBLICE': 'scrape_achizitii.py',
    'ANOFM': 'ANOFM/anofm_scraper.py',
    'CQC': 'cqc_scraper.py',
    'DENMARK': 'danish_scraper.py',
    'DSVSA': 'DSVSA/scraper.py',
    'EURES': 'EURES/eures_scraper.py',
    'EURES_AGENCIES': 'eures_agencies_scraper.py',
    'FINLAND': 'duunitori_scraper.py',
    'GERMANY': 'bundesagentur_scraper.py',
    'MALTA': 'malta_accommodation_scraper.py',
    'MOLDOVA': 'scrape_rabota.py',
    'NORTH_MACEDONIA': 'NORTH_MACEDONIA/run_scraper.py',
    'NORWAY': 'arbeidsplassen_scraper.py',
    'POLAND': 'kraz_scraper.py',
    'RECYCLING': 'recycling_jobs_scraper.py',
    'SWEDEN': 'sweden_scraper.py',
    'UK': 'run_uk_scraper.py',
    'ITALY_JOOBLE': 'jooble_italy_scraper.py',
    'ITALY_ANPAL': 'anpal_scraper.py',
    'ITALY_TED': 'ted_api_scraper.py',
    'ITALY_OPENDATA': 'italy_opendata_scraper.py',
}
# Pipeline item classification (non-scraper data directories)
PIPELINE_CLASS = {
    # Active data sources (updated regularly by scripts)
    'EURES_SYNC': 'sync',
    'EMPLOYERS_RO': 'data',
    'CV_INBOX': 'data',
    'EDUCATION': 'data',
    'ROMANIA': 'data',
    # Enrichment pipelines (run periodically to add fields)
    'ENRICHED': 'enrich',
    'GERMANY_ENRICHED': 'enrich',
    'POLAND_ENRICHED': 'enrich',
    # Aggregation outputs (generated from other data)
    'DAILY': 'agg',
    'WEEKLY': 'agg',
    'MONTHLY': 'agg',
    'NORDIC_UNIFIED': 'agg',
    # External databases (one-time or rare imports)
    'EU_AGRI_DATABASE': 'import',
    'EU_DISCOVERY': 'import',
    'EU_EMPLOYMENT': 'import',
    'EU_PROCUREMENT': 'import',
    'EU_REGISTRIES': 'import',
    'EU_SUBSIDY': 'import',
    'EU_TOURISM': 'import',
    'AGENCIES': 'import',
    'LAWYERS': 'import',
    'FRANCE': 'import',
    'IRELAND': 'import',
    'GERMANY_AGENCIES': 'import',
    # Legacy/deprecated
    'BREVO': 'legacy',
    'GOOGLE': 'legacy',
    'SCRAPERS': 'legacy',
    'SCRAPER_CSV': 'legacy',
    'SCRAPER_CONTACTS': 'legacy',
    'TELEGRAM_VERIFIED': 'legacy',
    'CONTRACTOR_MATCHES': 'legacy',
    # Utility
    'LINK_AUDIT': 'util',
    'JOBFAIRS': 'util',
    'SIP_TRUNKING': 'util',
    'ROMANIA_TRANSLATORS': 'util',
}

PIPELINE_LABELS = {
    'sync': 'SYNC',
    'data': 'DATA',
    'enrich': 'ENRICH',
    'agg': 'AGG',
    'import': 'IMPORT',
    'legacy': 'LEGACY',
    'util': 'UTIL',
}




def get_bounce_stats():
    """Get bounce stats from Brevo or local tracking."""
    stats = {"total_sent": 0, "bounces": 0, "rate": 0.0}
    try:
        env_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/.env")
        if env_file.exists():
            for line in env_file.read_text().splitlines():
                if line.startswith("BREVO_BUILDJOBS_API_KEY="):
                    api_key = line.split("=", 1)[1].strip()
                    import requests
                    r = requests.get(
                        "https://api.brevo.com/v3/smtp/statistics/aggregatedReport",
                        headers={"api-key": api_key},
                        params={"days": 1},
                        timeout=5
                    )
                    if r.ok:
                        d = r.json()
                        stats["total_sent"] = d.get("requests", 0)
                        stats["bounces"] = d.get("hardBounces", 0) + d.get("softBounces", 0)
                        if stats["total_sent"] > 0:
                            stats["rate"] = (stats["bounces"] / stats["total_sent"]) * 100
                    break
    except Exception:
        pass
    try:
        bounce_log = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/bounce_tracking.json")
        if bounce_log.exists():
            local = json.loads(bounce_log.read_text())
            today = datetime.now().strftime("%Y-%m-%d")
            if today in local:
                stats["bounces"] += local[today].get("count", 0)
    except Exception:
        pass
    return stats


def get_today_sends():
    """Get total emails sent today from all senders."""
    total = 0
    campaigns_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    if campaigns_dir.exists():
        today = datetime.now().strftime("%Y-%m-%d")
        for state_file in campaigns_dir.glob("*/state.json"):
            try:
                state = json.loads(state_file.read_text())
                for email in state.get("sent", []):
                    if isinstance(email, dict) and email.get("date", "").startswith(today):
                        total += 1
            except Exception:
                pass
    return total


def get_disk():
    try:
        total, used, free = shutil.disk_usage("/")
        return str(int(used * 100 / total))
    except Exception:
        return "0"


def get_memory():
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        total = int([l for l in lines if "MemTotal" in l][0].split()[1])
        avail = int([l for l in lines if "MemAvailable" in l][0].split()[1])
        return str(int((total - avail) * 100 / total))
    except Exception:
        return "0"


def get_load():
    """Get CPU load average."""
    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
        return parts[0]  # 1-min load avg
    except Exception:
        return "?"


def get_cpu_temp():
    """Get CPU temperature."""
    try:
        temp = open('/sys/class/thermal/thermal_zone0/temp').read().strip()
        return f"{int(temp)/1000:.0f}"
    except Exception:
        return "?"


def get_scrapers():
    scrapers = {}
    scan_dirs = [
        Path("/opt/ACTIVE/OPENDATA/DATA"),
        Path("/mnt/hdd/SCRAPER_DATA/csv"),
        Path("/opt/ACTIVE/SCRAPERS/EUROPE/EUROPE"),
    ]
    skip_names = {"ARCHIVE", "BACKUP", "LOGS", "__pycache__", "DOCS", "ARCHIVES", "CLAUDE.md"}

    for data_dir in scan_dirs:
        if not data_dir.exists():
            continue
        for d in data_dir.iterdir():
            if not d.is_dir() or d.name in skip_names or d.name.startswith("."):
                continue
            csvs = list(d.glob("*.csv")) + list(d.glob("*/*.csv"))
            if not csvs:
                continue
            newest = max(csvs, key=lambda x: x.stat().st_mtime)
            mtime = datetime.fromtimestamp(newest.stat().st_mtime)
            try:
                rows = sum(1 for _ in open(newest)) - 1
            except Exception:
                rows = 0
            age_h = (datetime.now() - mtime).total_seconds() / 3600
            status = "ok" if age_h < 24 else "warn" if age_h < 72 else "err"
            name = d.name
            if name not in scrapers or scrapers[name]["age_h"] > age_h:
                scrapers[name] = {
                    "name": name, "rows": rows,
                    "updated": mtime.strftime("%m-%d %H:%M"),
                    "age_h": int(age_h), "status": status
                }
    return sorted(scrapers.values(), key=lambda x: x["name"])


def get_running_scrapers():
    """Check which scrapers are currently running. Single pgrep call."""
    running = {}
    try:
        result = subprocess.run(['pgrep', '-af', 'python3'], capture_output=True, text=True, timeout=5)
        proc_list = result.stdout
        for name, script in SCRAPER_PGREP.items():
            if script in proc_list:
                running[name] = True
    except Exception:
        pass
    return running


def get_campaigns():
    campaigns = []
    camp_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    if not camp_dir.exists():
        return campaigns
    for d in sorted(camp_dir.iterdir()):
        if d.is_dir() and (d / "state.json").exists():
            try:
                state = json.loads((d / "state.json").read_text())
                sent = len(state.get("sent", []))
                contacts = 0
                contacts_dir = d / "contacts"
                if contacts_dir.exists():
                    for csv in contacts_dir.glob("*.csv"):
                        try:
                            contacts += sum(1 for _ in open(csv)) - 1
                        except Exception:
                            pass
                status = "ok" if contacts > 100 else "warn" if contacts > 0 else "err"
                campaigns.append({"name": d.name, "contacts": contacts, "sent": sent, "status": status})
            except Exception:
                pass
    return campaigns


def get_email_status():
    """Get email sending status for the email campaign panel."""
    status = {'campaigns': [], 'running_senders': [], 'next_feed': '08:40, 12:40, 16:40', 'leads': 0, 'global_sent': 0}
    campaigns_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    today = datetime.now().strftime("%Y-%m-%d")

    # Count leads
    leads_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/leads.json")
    if leads_file.exists():
        try:
            leads = json.loads(leads_file.read_text())
            status['leads'] = len(leads)
        except Exception:
            pass

    # Count global sends
    global_log = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/global_send_log.csv")
    if global_log.exists():
        try:
            status['global_sent'] = sum(1 for _ in open(global_log)) - 1
        except Exception:
            pass

    if campaigns_dir.exists():
        for d in sorted(campaigns_dir.iterdir()):
            if not d.is_dir():
                continue
            # Check both state.json and .state.json
            state_file = None
            for name in ['.state.json', 'state.json', 'gmail_yahoo_state.json']:
                if (d / name).exists():
                    state_file = d / name
                    break
            if not state_file:
                continue
            try:
                state = json.loads(state_file.read_text())
                # Handle both formats: sent as dict or list
                sent_data = state.get("sent", state.get("sent_emails", {}))
                if isinstance(sent_data, dict):
                    total_sent = len(sent_data)
                elif isinstance(sent_data, list):
                    total_sent = len(sent_data)
                else:
                    total_sent = 0
                # Count today from daily dict
                daily = state.get("daily", {}).get(today, {})
                today_sent = sum(daily.values()) if isinstance(daily, dict) else 0
                if today_sent == 0:
                    today_sent = state.get("daily_sent", {}).get(today, 0)

                contacts = 0
                contacts_dir = d / "contacts"
                if contacts_dir.exists():
                    for csv_f in contacts_dir.glob("*.csv"):
                        try:
                            contacts += sum(1 for _ in open(csv_f)) - 1
                        except Exception:
                            pass
                queue = max(0, contacts - total_sent)
                paused = (d / "PAUSED").exists()
                if contacts > 0:
                    status['campaigns'].append({
                        'name': d.name, 'today': today_sent,
                        'total_sent': total_sent, 'contacts': contacts,
                        'queue': queue, 'paused': paused
                    })
            except Exception:
                pass

    # Check running sender processes
    for proc_name in ['send_necalificati', 'anofm_sender', 'send_factoryjobs', 'brevo_warmup', 'a2_warmup', 'capacity_maximizer', 'smart_sender', 'safe_email']:
        try:
            r = subprocess.run(['pgrep', '-af', proc_name], capture_output=True, text=True, timeout=3)
            procs = [l for l in r.stdout.strip().split('\n') if l.strip() and 'pgrep' not in l]
            if procs:
                status['running_senders'].append(proc_name)
        except Exception:
            pass
    return status



def get_sender_stats():
    """Get per-sender daily email counts from sent_YYYYMMDD.log files."""
    today = datetime.now().strftime("%Y%m%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    campaigns_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    stats = []

    if not campaigns_dir.exists():
        return stats

    for d in sorted(campaigns_dir.iterdir()):
        if not d.is_dir():
            continue
        logs_dir = d / "logs"
        if not logs_dir.exists():
            continue
        today_log = logs_dir / f"sent_{today}.log"
        yest_log = logs_dir / f"sent_{yesterday}.log"
        today_count = 0
        yest_count = 0
        if today_log.exists():
            try:
                today_count = sum(1 for line in open(today_log) if line.strip())
            except Exception:
                pass
        if yest_log.exists():
            try:
                yest_count = sum(1 for line in open(yest_log) if line.strip())
            except Exception:
                pass
        if today_count > 0 or yest_count > 0:
            stats.append({
                'name': d.name,
                'today': today_count,
                'yesterday': yest_count,
            })

    return stats



def get_sender_scores():
    """Load sender scores from campaign_report.py output."""
    scores_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/sender_scores.json")
    if not scores_file.exists():
        return []
    try:
        scores = json.loads(scores_file.read_text())
        result = []
        for sender, data in sorted(scores.items(), key=lambda x: x[1].get('score', 0), reverse=True):
            # Dynamic delay recommendation
            br = data.get('bounce_rate', 1.0)
            if br == 0:
                delay = 240
            elif br <= 2:
                delay = 300
            else:
                delay = 360
            result.append({
                'name': sender,
                'score': data.get('score', 0),
                'total_sent': data.get('total_sent', 0),
                'bounce_rate': data.get('bounce_rate', 0),
                'delay': delay,
            })
        return result
    except Exception:
        return []


def get_warmup_status():
    """Get warmup progress for active campaigns."""
    from datetime import date
    warmups = []
    # NECALIFICATI
    necal_start = date(2026, 2, 9)
    schedule = {3: 20, 7: 50, 14: 100, 999: 200}
    day_num = (date.today() - necal_start).days + 1
    limit = 200
    for max_day, lim in sorted(schedule.items()):
        if day_num <= max_day:
            limit = lim
            break
    warmups.append({'campaign': 'NECALIFICATI', 'day': day_num, 'limit': limit, 'start': str(necal_start)})

    # ANOFM
    anofm_start = date(2026, 2, 11)
    day_num_a = (date.today() - anofm_start).days + 1
    limit_a = 200
    for max_day, lim in sorted(schedule.items()):
        if day_num_a <= max_day:
            limit_a = lim
            break
    warmups.append({'campaign': 'ANOFM', 'day': day_num_a, 'limit': limit_a, 'start': str(anofm_start)})
    return warmups


def get_followup_status():
    """Get followup campaign status."""
    state_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/NECALIFICATI_FEB_2026/.state.json")
    if not state_file.exists():
        return {'intro_sent': 0, 'followup_sent': 0, 'eligible': 0}
    try:
        state = json.loads(state_file.read_text())
        intro_sent = len(state.get('sent', {}))
        followup_sent = len(state.get('followup', {}))
        # Count eligible (sent 7+ days ago, no followup, not in leads)
        from datetime import date, timedelta
        cutoff = (date.today() - timedelta(days=7)).isoformat()
        eligible = 0
        leads_emails = set()
        leads_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/leads.json")
        if leads_file.exists():
            try:
                leads = json.loads(leads_file.read_text())
                leads_emails = {l.get('from_email', '').lower() for l in leads}
            except Exception:
                pass
        for email, data in state.get('sent', {}).items():
            sent_date = data.get('date', '')[:10] if isinstance(data, dict) else ''
            if sent_date and sent_date <= cutoff:
                if email not in state.get('followup', {}) and email.lower() not in leads_emails:
                    eligible += 1
        return {'intro_sent': intro_sent, 'followup_sent': followup_sent, 'eligible': eligible}
    except Exception:
        return {'intro_sent': 0, 'followup_sent': 0, 'eligible': 0}


def get_paused_campaigns():
    """Get list of paused campaigns with resume dates."""
    paused = []
    camp_dir = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
    if not camp_dir.exists():
        return paused
    for d in sorted(camp_dir.iterdir()):
        if not d.is_dir():
            continue
        for pf in ['PAUSED', '.paused']:
            pause_file = d / pf
            if pause_file.exists():
                try:
                    resume_date = pause_file.read_text().strip()
                except Exception:
                    resume_date = 'unknown'
                paused.append({'name': d.name, 'resume': resume_date})
                break
    return paused


def get_healthcheck_last():
    """Get last health check result from log."""
    log_file = Path("/opt/ACTIVE/INFRA/LOGS/sender_healthcheck.log")
    if not log_file.exists():
        return {'time': 'never', 'passed': None}
    try:
        lines = log_file.read_text().strip().split('\n')
        # Find last "ALL CHECKS PASSED" or failure
        last_time = ''
        passed = None
        for line in reversed(lines):
            if 'ALL CHECKS PASSED' in line:
                passed = True
                break
            if 'NEED ATTENTION' in line:
                passed = False
                break
            if 'EMAIL SENDER HEALTH CHECK' in line:
                last_time = line.strip()
                break
        # Get timestamp from log
        for line in reversed(lines):
            if line.strip() and line[0:4].isdigit():
                last_time = line[:19]
                break
        return {'time': last_time or 'unknown', 'passed': passed}
    except Exception:
        return {'time': 'error', 'passed': None}


def get_global_stats():
    """Get global email statistics."""
    stats = {'total': 0, 'today': 0, 'week': 0, 'leads': 0, 'blacklist': 0}
    from datetime import date, timedelta
    today_str = date.today().isoformat()
    week_cutoff = (date.today() - timedelta(days=7)).isoformat()

    # Global send log
    log = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/global_send_log.csv")
    if log.exists():
        try:
            with open(log) as f:
                next(f, None)
                for line in f:
                    stats['total'] += 1
                    parts = line.strip().split(',')
                    if parts[0] == today_str:
                        stats['today'] += 1
                    if parts[0] >= week_cutoff:
                        stats['week'] += 1
        except Exception:
            pass

    # Leads
    leads_file = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/leads.json")
    if leads_file.exists():
        try:
            stats['leads'] = len(json.loads(leads_file.read_text()))
        except Exception:
            pass

    # Blacklist
    bl = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/master_blacklist.csv")
    if bl.exists():
        try:
            stats['blacklist'] = sum(1 for _ in open(bl)) - 1
        except Exception:
            pass

    return stats


def get_issues(scrapers):
    issues = []
    lock = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/GLOBAL_SEND_LOCK")
    if lock.exists():
        age = (datetime.now() - datetime.fromtimestamp(lock.stat().st_mtime)).days
        issues.append(("SEND_LOCK active", f"{age}d", "err", "clear_lock", "system"))
    for s in scrapers:
        if s["age_h"] > 48:
            if s['name'] in SCRAPER_PGREP:
                issues.append((f"{s['name']} stale", f"{s['age_h']}h", "warn", f"restart_scraper:{s['name']}", "scraper"))
            else:
                if s['age_h'] < 720:  # Only show pipeline items < 30 days old
                    issues.append((f"{s['name']} stale", f"{s['age_h']}h", "info", None, "pipeline"))
    for c in get_campaigns():
        if c["contacts"] < 100:
            issues.append((f"{c['name']} low", f"{c['contacts']}", "warn", "feed_campaigns", "campaign"))
    disk = int(get_disk())
    if disk > 85:
        issues.append(("Disk high", f"{disk}%", "err" if disk > 95 else "warn", "disk_cleanup", "system"))
    return issues


def update_row_history(scrapers):
    """Track scraper row counts over time for speed calculation."""
    try:
        history = json.loads(ROW_HISTORY_FILE.read_text()) if ROW_HISTORY_FILE.exists() else {}
    except Exception:
        history = {}

    now = datetime.now()
    for s in scrapers:
        name = s['name']
        if name not in history:
            history[name] = []
        entries = history[name]
        # Only record if last entry was >10 min ago
        if not entries or (now - datetime.fromisoformat(entries[-1]['ts'])).total_seconds() > 600:
            entries.append({'ts': now.isoformat(), 'rows': s['rows']})
            history[name] = entries[-MAX_HISTORY_ENTRIES:]

    try:
        ROW_HISTORY_FILE.write_text(json.dumps(history, default=str))
    except Exception:
        pass
    return history


def get_scraper_speed(history, name):
    """Calculate rows/hour from recent history."""
    entries = history.get(name, [])
    if len(entries) < 2:
        return None
    latest = entries[-1]
    # Find entry from ~1h ago
    target = datetime.fromisoformat(latest['ts']) - timedelta(hours=1)
    older = None
    for e in entries:
        if datetime.fromisoformat(e['ts']) <= target:
            older = e
    if not older:
        older = entries[0]
    dt_h = (datetime.fromisoformat(latest['ts']) - datetime.fromisoformat(older['ts'])).total_seconds() / 3600
    if dt_h < 0.05:
        return None
    diff = latest['rows'] - older['rows']
    return int(diff / dt_h) if diff > 0 else 0


def make_sparkline(history, name):
    """Create ASCII sparkline from row history."""
    entries = history.get(name, [])
    if len(entries) < 2:
        return ''
    rows = [e['rows'] for e in entries]
    mn, mx = min(rows), max(rows)
    if mx == mn:
        return ''
    blocks = ' \u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588'
    spark = ''
    for v in rows:
        idx = int((v - mn) / (mx - mn) * 7) + 1
        spark += blocks[min(idx, 8)]
    return spark


def generate():
    disk = get_disk()
    mem = get_memory()
    load = get_load()
    temp = get_cpu_temp()
    scrapers = get_scrapers()
    running = get_running_scrapers()
    campaigns = get_campaigns()
    issues = get_issues(scrapers)
    bounce_stats = get_bounce_stats()
    today_sends = get_today_sends()
    email_status = get_email_status()
    row_history = update_row_history(scrapers)
    sender_stats = get_sender_stats()
    sender_scores = get_sender_scores()
    warmup_status = get_warmup_status()
    followup_status = get_followup_status()
    paused_campaigns = get_paused_campaigns()
    healthcheck = get_healthcheck_last()
    global_stats = get_global_stats()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    active_scrapers = len([s for s in scrapers if s["age_h"] < 24])
    critical_issues = len([i for i in issues if i[2] == "err"])
    scraper_issues = len([i for i in issues if i[4] == "scraper"])
    pipeline_issues = len([i for i in issues if i[4] == "pipeline"])
    hidden_pipelines = len([s for s in scrapers if s["age_h"] > 720 and s["name"] not in SCRAPER_PGREP])
    bounce_rate = bounce_stats["rate"]
    bounce_color = "#4ade80" if bounce_rate < 2 else "#ffc107" if bounce_rate < 5 else "#ff6b6b"

    def color(s):
        return "#4ade80" if s == "ok" else "#ffc107" if s == "warn" else "#ff6b6b"

    # --- Scraper table rows ---
    scraper_rows = ""
    for s in scrapers:
        is_running = running.get(s['name'], False)
        is_scraper = s['name'] in SCRAPER_PGREP
        speed = get_scraper_speed(row_history, s['name'])

        # Status badge
        if is_running:
            status_badge = '<span style="color:#4ade80;font-weight:bold">RUNNING</span>'
        else:
            status_badge = ''

        # Speed column with sparkline
        sparkline = make_sparkline(row_history, s['name'])
        if speed and speed > 0 and is_running:
            speed_text = f'<span style="color:#4ade80">+{speed:,}/h</span>'
        elif speed and speed > 0:
            speed_text = f'<span style="color:#888">+{speed:,}/h</span>'
        else:
            speed_text = ''
        if sparkline:
            speed_text += f' <span style="color:#555;font-size:10px;letter-spacing:1px">{sparkline}</span>'

        # Action buttons
        actions = ''
        if is_scraper:
            if is_running:
                actions = f"<a href='#' onclick=\"callFix('kill_scraper:{s['name']}');return false\" class='btn' style='background:#ff6b6b'>KILL</a> "
            elif s['age_h'] > 24:
                actions = f"<a href='#' onclick=\"callFix('restart_scraper:{s['name']}');return false\" class='btn'>START</a> "
            actions += f"<a href='#' onclick=\"callFix('logs:{s['name']}');return false\" class='btn' style='background:#60a5fa'>LOGS</a>"

        scraper_rows += (
            f"<tr>"
            f"<td style=\"color:{color(s['status'])}\">{s['name']}</td>"
            f"<td>{s['rows']:,}</td>"
            f"<td>{s['updated']}</td>"
            f"<td>{s['age_h']}h</td>"
            f"<td>{status_badge}</td>"
            f"<td>{speed_text}</td>"
            f"<td>{actions}</td>"
            f"</tr>"
        )

    # --- Campaign table rows ---
    campaign_rows = ""
    for c in campaigns:
        campaign_rows += f"<tr><td style=\"color:{color(c['status'])}\">{c['name']}</td><td>{c['contacts']:,}</td><td>{c['sent']:,}</td></tr>"

    # --- Email campaign panel rows ---
    email_rows = ""
    for c in email_status['campaigns']:
        paused_badge = ' <span style="color:#ff6b6b">[PAUSED]</span>' if c['paused'] else ''
        email_rows += (
            f"<tr>"
            f"<td>{c['name']}{paused_badge}</td>"
            f"<td>{c['today']}</td>"
            f"<td>{c['total_sent']:,}</td>"
            f"<td>{c['queue']:,}</td>"
            f"</tr>"
        )
    running_senders = ', '.join(email_status['running_senders']) or '<span style="color:#888">None</span>'

    # Sender stats rows
    sender_rows = ""
    total_today = 0
    total_yesterday = 0
    for ss in sender_stats:
        total_today += ss['today']
        total_yesterday += ss['yesterday']
        trend = '\u2197' if ss['today'] > ss['yesterday'] * 0.8 else '\u2198' if ss['today'] < ss['yesterday'] * 0.3 else '\u2192'
        sender_rows += (
            f"<tr>"
            f"<td>{ss['name']}</td>"
            f"<td style='color:#4ade80'>{ss['today']}</td>"
            f"<td style='color:#888'>{ss['yesterday']}</td>"
            f"<td>{trend}</td>"
            f"</tr>"
        )
    if sender_stats:
        sender_rows += (
            f"<tr style='border-top:2px solid #2a2a4a;font-weight:bold'>"
            f"<td>TOTAL</td>"
            f"<td style='color:#4ade80'>{total_today}</td>"
            f"<td style='color:#888'>{total_yesterday}</td>"
            f"<td></td>"
            f"</tr>"
        )

    # --- Sender score rows ---
    sender_score_rows = ""
    for ss in sender_scores:
        score_color = '#4ade80' if ss['score'] >= 90 else '#fbbf24' if ss['score'] >= 70 else '#ff6b6b'
        delay_label = f"{ss['delay']}s"
        if ss['bounce_rate'] == 0:
            delay_label += ' \u2b50'
        sender_score_rows += (
            f"<tr>"
            f"<td>{ss['name']}</td>"
            f"<td style='color:{score_color}'>{ss['score']:.1f}</td>"
            f"<td>{ss['total_sent']:,}</td>"
            f"<td>{ss['bounce_rate']:.2f}%</td>"
            f"<td>{delay_label}</td>"
            f"</tr>"
        )

    # --- Warmup rows ---
    warmup_rows = ""
    for w in warmup_status:
        pct = min(100, (w['day'] / 15) * 100)
        bar = f'<div style="background:#2a2a4a;border-radius:4px;height:12px;width:100px;display:inline-block;vertical-align:middle"><div style="background:#4ade80;height:100%;width:{pct:.0f}%;border-radius:4px"></div></div>'
        warmup_rows += f'<div style="margin-left:12px;margin-bottom:4px">{w["campaign"]}: Day {w["day"]} \u2192 <span style="color:#fbbf24">{w["limit"]}/sender</span> {bar}</div>'

    # --- Paused campaign rows ---
    paused_rows = ""
    for p in paused_campaigns:
        paused_rows += f"<tr><td style='color:#ff6b6b'>{p['name']}</td><td>{p['resume']}</td></tr>"
    if not paused_campaigns:
        paused_rows = "<tr><td colspan='2' style='color:#4ade80;text-align:center'>No paused campaigns</td></tr>"

    # --- Issue rows ---
    issue_rows = ""
    for i, d, lvl, fix, item_type in issues:
        c = "#ff6b6b" if lvl == "err" else "#ffc107" if lvl == "warn" else "#888"
        if fix:
            action = f"<a href='#' onclick=\"callFix('{fix}');return false\" class='btn'>FIX</a>"
        else:
            action = f'<span style="color:#555;font-size:10px">{PIPELINE_LABELS.get(PIPELINE_CLASS.get(i.split()[0], ""), "PIPELINE")}</span>'
        issue_rows += f"<tr><td style=\"color:{c}\">{i}</td><td>{d}</td><td>{action}</td></tr>"
    if not issues:
        issue_rows = "<tr><td colspan='3' style='color:#4ade80;text-align:center;padding:20px'>All systems operational</td></tr>"

    running_count = len(running)

    html = f"""<!DOCTYPE html>
<html>
<head>
<title>Raspibig Dashboard</title>
<meta charset="utf-8">
<meta http-equiv="refresh" content="60">
<style>
body{{font-family:monospace;background:#0a0a1a;color:#eee;padding:20px;margin:0}}
h1{{color:#00d9ff;margin-bottom:5px}}
.u{{color:#666;margin-bottom:20px}}
.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(400px,1fr));gap:15px}}
.c{{background:#12122a;border-radius:8px;padding:12px;border:1px solid #2a2a4a;max-height:600px;overflow-y:auto}}
.c h2{{color:#00d9ff;font-size:13px;margin-bottom:8px;text-transform:uppercase;cursor:pointer}}
.c h2:hover{{color:#fff}}
.c h2::before{{content:'[-] ';font-size:10px}}
.c.collapsed h2::before{{content:'[+] '}}
.c.collapsed table,.c.collapsed .panel-content{{display:none}}
table{{width:100%;border-collapse:collapse;font-size:12px}}
th,td{{padding:5px;text-align:left;border-bottom:1px solid #2a2a4a}}
th{{color:#888;font-size:11px}}
.s{{display:flex;gap:20px;margin-bottom:15px;flex-wrap:wrap}}
.st{{text-align:center;min-width:60px}}
.sv{{font-size:20px;color:#00d9ff}}
.sl{{color:#888;font-size:11px}}
.btn{{background:#00d9ff;color:#000;padding:3px 10px;border-radius:4px;text-decoration:none;font-size:11px;cursor:pointer;display:inline-block}}
.btn:hover{{background:#00b8d4}}
.btns{{margin-top:15px;display:flex;gap:8px;flex-wrap:wrap}}
.btns a{{padding:6px 12px;border-radius:4px;text-decoration:none;font-size:12px;cursor:pointer}}
.btns .g1{{background:#4ade80;color:#000}}
.btns .g2{{background:#fbbf24;color:#000}}
.btns .g3{{background:#60a5fa;color:#000}}
.btns .g4{{background:#f472b6;color:#000}}
.btns .g5{{background:#c084fc;color:#000}}
.summary{{background:linear-gradient(135deg,#1a1a3a 0%,#12122a 100%);border:2px solid #00d9ff;border-radius:12px;padding:20px;margin-bottom:20px}}
.summary h3{{color:#00d9ff;margin:0 0 15px 0;font-size:14px}}
.summary-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:15px}}
.summary-item{{text-align:center;padding:12px;background:#0a0a1a;border-radius:8px}}
.summary-val{{font-size:24px;font-weight:bold}}
.summary-lbl{{color:#888;font-size:10px;margin-top:5px}}
.wide{{grid-column:1/-1}}
#overlay{{display:none;position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.7);z-index:1000;justify-content:center;align-items:center}}
#modal{{background:#1a1a3a;border:1px solid #00d9ff;border-radius:8px;padding:20px;max-width:700px;width:90%;max-height:80vh;overflow-y:auto;position:relative}}
#modal-title{{color:#00d9ff;font-size:14px;font-weight:bold;margin-bottom:10px}}
#modal-body{{color:#eee;font-size:12px;white-space:pre-wrap;word-break:break-word;margin:0;font-family:monospace}}
#modal-close{{position:absolute;top:8px;right:12px;background:none;border:none;color:#888;font-size:18px;cursor:pointer}}
#modal-close:hover{{color:#fff}}
@media(max-width:900px){{.summary-grid{{grid-template-columns:repeat(3,1fr)}}}}
@media(max-width:600px){{.summary-grid{{grid-template-columns:repeat(2,1fr)}}}}
</style>
</head>
<body>
<h1>RASPIBIG DASHBOARD</h1>
<div class="u">Updated: {now}</div>

<div class="summary">
<h3>SYSTEM OVERVIEW</h3>
<div class="summary-grid">
<div class="summary-item"><div class="summary-val" style="color:#4ade80">{today_sends}</div><div class="summary-lbl">EMAILS TODAY</div></div>
<div class="summary-item"><div class="summary-val" style="color:#fbbf24">{global_stats['total']:,}</div><div class="summary-lbl">TOTAL SENDS</div></div>
<div class="summary-item"><div class="summary-val" style="color:{bounce_color}">{bounce_rate:.1f}%</div><div class="summary-lbl">BOUNCE RATE</div></div>
<div class="summary-item"><div class="summary-val" style="color:#c084fc">{global_stats['leads']}</div><div class="summary-lbl">LEADS</div></div>
<div class="summary-item"><div class="summary-val" style="color:#ff6b6b">{global_stats['blacklist']:,}</div><div class="summary-lbl">BLACKLISTED</div></div>
<div class="summary-item"><div class="summary-val" style="color:#00d9ff">{active_scrapers}/{len(scrapers)}</div><div class="summary-lbl">ACTIVE SCRAPERS</div></div>
<div class="summary-item"><div class="summary-val" style="color:#4ade80">{running_count}</div><div class="summary-lbl">RUNNING NOW</div></div>
<div class="summary-item"><div class="summary-val" style="color:{'#ff6b6b' if critical_issues else '#4ade80'}">{critical_issues}</div><div class="summary-lbl">CRITICAL</div></div>
<div class="summary-item"><div class="summary-val">{disk}%</div><div class="summary-lbl">DISK</div></div>
<div class="summary-item"><div class="summary-val">{mem}%</div><div class="summary-lbl">MEMORY</div></div>
<div class="summary-item"><div class="summary-val">{load}</div><div class="summary-lbl">LOAD AVG</div></div>
<div class="summary-item"><div class="summary-val">{temp}C</div><div class="summary-lbl">CPU TEMP</div></div>
<div class="summary-item"><div class="summary-val" style="color:#ffc107">{scraper_issues}</div><div class="summary-lbl">STALE SCRAPERS</div></div>
</div>
</div>

<div class="btns">
<a href="#" onclick="callFix('health_check');return false" class="g1">Health Check</a>
<a href="#" onclick="callFix('feed_campaigns');return false" class="g2">Feed Campaigns</a>
<a href="#" onclick="callFix('restart_all_stale');return false" class="g4">Restart All Stale</a>
<a href="#" onclick="callFix('system_load');return false" class="g3">System Load</a>
<a href="#" onclick="callFix('clear_lock');return false" class="g3">Clear Lock</a>
<a href="#" onclick="callFix('autofix');return false" class="g5">Auto Fix All</a>
<a href="#" onclick="callFix('campaign_report');return false" class="g2">Campaign Report</a>
<a href="#" onclick="callFix('sender_healthcheck');return false" class="g1">Health Check+</a>
<a href="#" onclick="callFix('sender_scores');return false" class="g3">Sender Scores</a>
<a href="#" onclick="callFix('email_status');return false" class="g3">Email Status</a>
<a href="#" onclick="if(confirm('Stop ALL email senders?'))callFix('stop_all_senders');return false" style="background:#ff6b6b;color:#000">Stop Senders</a>
<a href="#" onclick="if(confirm('Start ALL email senders?'))callFix('start_all_senders');return false" style="background:#4ade80;color:#000">Start Senders</a>
<a href="#" onclick="callCampaigns();return false" class="g2">View Campaigns</a>
<a href="#" onclick="callLogs();return false" class="g3">View Logs</a>
</div>

<div class="g" style="margin-top:15px">

<div class="c"><h2 onclick="toggleSection(this)">Issues ({len(issues)} | {scraper_issues} fixable, {pipeline_issues} pipelines, {hidden_pipelines} hidden)</h2>
<table><tr><th>Issue</th><th>Detail</th><th>Action</th></tr>{issue_rows}</table></div>

<div class="c"><h2 onclick="toggleSection(this)">Email Sending ({len(email_status['campaigns'])} campaigns)</h2>
<div class="panel-content">
<div style="font-size:11px;color:#888;margin-bottom:8px">
Active senders: <span style="color:#4ade80">{running_senders}</span> | Leads: <span style="color:#fbbf24">{email_status.get('leads', 0)}</span> | Global sent: {email_status.get('global_sent', 0):,} | Next feed: {email_status['next_feed']}
</div>
<table><tr><th>Campaign</th><th>Today</th><th>Sent</th><th>Queue</th></tr>{email_rows}</table>
</div></div>

<div class="c"><h2 onclick="toggleSection(this)">Sender Tracking ({len(sender_stats)} active)</h2>
<div class="panel-content">
<table><tr><th>Sender</th><th>Today</th><th>Yesterday</th><th>Trend</th></tr>{sender_rows}</table>
</div></div>

<div class="c wide"><h2 onclick="toggleSection(this)">Scrapers ({len(scrapers)} | {running_count} running)</h2>
<table><tr><th>Name</th><th>Rows</th><th>Updated</th><th>Age</th><th>Status</th><th>Speed</th><th>Actions</th></tr>{scraper_rows}</table></div>



<div class="c"><h2 onclick="toggleSection(this)">Sender Scores ({len(sender_scores)} senders)</h2>
<div class="panel-content">
<table><tr><th>Sender</th><th>Score</th><th>Sent</th><th>Bounce%</th><th>Delay</th></tr>{sender_score_rows}</table>
</div></div>

<div class="c"><h2 onclick="toggleSection(this)">Campaign Health</h2>
<div class="panel-content">
<div style="font-size:11px;margin-bottom:8px">
<div style="margin-bottom:6px">Health Check: <span style="color:{'#4ade80' if healthcheck['passed'] else '#ff6b6b' if healthcheck['passed'] is not None else '#888'}">{('PASSED' if healthcheck['passed'] else 'FAILED') if healthcheck['passed'] is not None else 'unknown'}</span> <span style="color:#555">({healthcheck['time']})</span></div>
<div style="margin-bottom:6px">Warmup:</div>{warmup_rows}
<div style="margin-bottom:6px;margin-top:8px">Followup: <span style="color:#4ade80">{followup_status['followup_sent']}</span> sent | <span style="color:#fbbf24">{followup_status['eligible']}</span> eligible | <span style="color:#888">{followup_status['intro_sent']} intro sent</span></div>
</div>
</div></div>

<div class="c"><h2 onclick="toggleSection(this)">Paused Campaigns ({len(paused_campaigns)})</h2>
<div class="panel-content">
<table><tr><th>Campaign</th><th>Resume Date</th></tr>{paused_rows}</table>
</div></div>

<div class="c"><h2 onclick="toggleSection(this)">Campaign Contacts ({len(campaigns)})</h2>
<table><tr><th>Name</th><th>Contacts</th><th>Sent</th></tr>{campaign_rows}</table></div>

</div>

<div id="overlay" onclick="if(event.target===this)this.style.display='none'">
<div id="modal">
<button id="modal-close" onclick="document.getElementById('overlay').style.display='none'">&times;</button>
<div id="modal-title"></div>
<pre id="modal-body"></pre>
</div>
</div>

<script>
function toggleSection(el){{el.parentElement.classList.toggle('collapsed')}}

function callCampaigns(){{
var o=document.getElementById('overlay');
var t=document.getElementById('modal-title');
var b=document.getElementById('modal-body');
o.style.display='flex';
t.textContent='Loading campaigns...';
b.textContent='Please wait...';
fetch('{FIX_API}/campaigns')
.then(function(r){{return r.json()}})
.then(function(d){{
if(d.data){{
var html='';
d.data.forEach(function(c){{
html+=c.name.padEnd(25)+' T:'+String(c.today).padStart(4)+' Y:'+String(c.yesterday).padStart(4)+' Sent:'+String(c.total_sent).padStart(6)+' Q:'+String(c.queue).padStart(6)+' '+String(c.completion_pct)+'%'+(c.paused?' PAUSED':'')+'\n';
}});
t.textContent='Campaign Stats ('+d.data.length+' campaigns)';
t.style.color='#4ade80';
b.textContent=html;
}}else{{
t.textContent=d.fix_name||'Campaigns';
b.textContent=d.output;
}}
}})
.catch(function(e){{t.textContent='ERROR';t.style.color='#ff6b6b';b.textContent=e.message}});
}}

function callLogs(cat){{
cat=cat||'all';
var o=document.getElementById('overlay');
var t=document.getElementById('modal-title');
var b=document.getElementById('modal-body');
o.style.display='flex';
t.textContent='Loading logs...';
b.textContent='Please wait...';
fetch('{FIX_API}/logs_view/'+cat)
.then(function(r){{return r.json()}})
.then(function(d){{
t.textContent=d.fix_name||'Logs';
t.style.color=d.success?'#4ade80':'#ff6b6b';
b.textContent=d.output;
}})
.catch(function(e){{t.textContent='ERROR';t.style.color='#ff6b6b';b.textContent=e.message}});
}}

function callFix(endpoint){{
var o=document.getElementById('overlay');
var t=document.getElementById('modal-title');
var b=document.getElementById('modal-body');
o.style.display='flex';
t.textContent='Running...';
t.style.color='#00d9ff';
b.textContent='Please wait...';
fetch('{FIX_API}/fix/'+endpoint)
.then(function(r){{return r.json()}})
.then(function(d){{
t.textContent=(d.success?'OK':'FAILED')+' - '+(d.fix_name||endpoint);
t.style.color=d.success?'#4ade80':'#ff6b6b';
b.textContent=d.output||'No output';
}})
.catch(function(e){{
t.textContent='ERROR';
t.style.color='#ff6b6b';
b.textContent='Request failed: '+e.message;
}});
}}
</script>
</body>
</html>"""

    Path(OUTPUT).write_text(html)
    print(f"Generated: {OUTPUT}")


if __name__ == "__main__":
    generate()
