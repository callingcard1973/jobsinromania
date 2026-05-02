#!/usr/bin/env python3
"""
Metrics Collector - Runs locally on each machine, writes metrics to JSON.
Replaces SSH-based metric collection with local file writes + rsync.

Usage:
    python3 metrics_collector.py          # Collect and write metrics
    python3 metrics_collector.py --debug  # Print metrics without writing

Schedule: Every 5 minutes via cron on BOTH machines
Output: /opt/ACTIVE/INFRA/SYNC_STATE/{hostname}_metrics.json
"""

import json
import logging
import os
import socket
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Setup logging
LOG_FILE = '/opt/ACTIVE/INFRA/LOGS/metrics_collector.log'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler() if '--debug' in sys.argv else logging.NullHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import config
sys.path.insert(0, '/opt/ACTIVE/INFRA/SKILLS')
try:
    from dashboard_config import (
        RASPI_CAMPAIGNS, RASPIBIG_CAMPAIGNS, A2_DOMAINS,
        A2_WARMUP_SCHEDULE, A2_WARMUP_START_DATE,
        RASPIBIG_SERVICES, RASPI_SERVICES, DOCKER_CONTAINERS, PATHS
    )
except ImportError:
    logger.warning("dashboard_config.py not found, using defaults")
    RASPI_CAMPAIGNS = {}
    RASPIBIG_CAMPAIGNS = {}
    A2_DOMAINS = {}
    A2_WARMUP_SCHEDULE = [(1, 3, 20), (4, 7, 50), (8, 14, 100), (15, 21, 200), (22, 28, 350), (29, 999, 500)]
    A2_WARMUP_START_DATE = '2026-01-15'
    RASPIBIG_SERVICES = []
    RASPI_SERVICES = []
    DOCKER_CONTAINERS = []
    PATHS = {'sync_state_dir': '/opt/ACTIVE/INFRA/SYNC_STATE'}

OUTPUT_DIR = Path(PATHS.get('sync_state_dir', '/opt/ACTIVE/INFRA/SYNC_STATE'))


def run(cmd, timeout=10):
    """Execute shell command with timeout."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() or r.stderr.strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Command timeout: {cmd[:50]}")
        return ""
    except Exception as e:
        logger.error(f"Command error: {cmd[:50]} - {e}")
        return ""


def get_hostname():
    """Get machine hostname."""
    return socket.gethostname()


def get_cpu_percent():
    """Get CPU usage percentage."""
    try:
        output = run("top -bn1 | grep 'Cpu' | awk '{print $2}'")
        return float(output.replace(',', '.')) if output else 0.0
    except:
        return 0.0


def get_memory():
    """Get memory usage."""
    try:
        line = run("free -b | grep Mem")
        if line:
            parts = line.split()
            total = int(parts[1])
            used = int(parts[2])
            return {
                'used_gb': round(used / (1024**3), 2),
                'total_gb': round(total / (1024**3), 2),
                'percent': round(used / total * 100, 1) if total > 0 else 0
            }
    except Exception as e:
        logger.error(f"Memory error: {e}")
    return {'used_gb': 0, 'total_gb': 0, 'percent': 0}


def get_disk_usage():
    """Get disk usage for key mount points."""
    disks = {}
    try:
        output = run("df -h / /mnt/* 2>/dev/null | grep -v tmpfs | tail -n +2")
        for line in output.split('\n'):
            if line.strip():
                parts = line.split()
                if len(parts) >= 6:
                    mount = parts[5]
                    percent = int(parts[4].replace('%', ''))
                    free = parts[3]
                    disks[mount] = {'percent': percent, 'free': free}
    except Exception as e:
        logger.error(f"Disk error: {e}")
    return disks


def get_uptime():
    """Get system uptime."""
    return run("uptime -p").replace("up ", "")


def get_services_status(hostname):
    """Get status of monitored services."""
    services = {}

    if hostname == 'raspibig':
        for name, cmd in RASPIBIG_SERVICES:
            result = run(cmd)
            services[name] = result in ['active', 'running']
    else:
        for name in RASPI_SERVICES:
            result = run(f"systemctl is-active {name}")
            services[name] = result == 'active'

    return services


def get_docker_status():
    """Get Docker container status."""
    containers = {}
    try:
        filter_args = ' '.join([f"--filter 'name={c}'" for c in DOCKER_CONTAINERS])
        output = run(f"docker ps -a {filter_args} --format '{{{{.Names}}}}|{{{{.Status}}}}' 2>/dev/null")
        for line in output.split('\n'):
            if '|' in line:
                name, status = line.split('|', 1)
                containers[name] = {
                    'running': status.startswith('Up'),
                    'status': status[:30]
                }
    except Exception as e:
        logger.error(f"Docker error: {e}")
    return containers


def get_campaign_stats(hostname):
    """Get email campaign statistics."""
    campaigns = {}
    today = datetime.now().strftime('%Y%m%d')
    today_iso = datetime.now().strftime('%Y-%m-%d')

    campaign_list = RASPI_CAMPAIGNS if hostname == 'raspi' else RASPIBIG_CAMPAIGNS

    for name, config in campaign_list.items():
        sent = 0

        if config['sender'] == 'A2HOSTING' and 'domain' in config:
            # Read from A2 warmup state
            try:
                state_file = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_warmup_state.json')
                if state_file.exists():
                    state = json.loads(state_file.read_text())
                    domain_state = state.get(config['domain'], {})
                    if domain_state.get('last_send_date') == today_iso:
                        sent = domain_state.get('sent_today', 0)
            except Exception as e:
                logger.error(f"A2 state error for {name}: {e}")
        else:
            # Read from campaign log
            path = config.get('path', f'/opt/ACTIVE/EMAIL/CAMPAIGNS/{name}')
            log_path = f'{path}/logs/sent_{today}.log'
            try:
                count = run(f"grep -c '| OK |' {log_path} 2>/dev/null || echo 0")
                sent = int(count)
            except:
                pass

            # Also check state.json
            if sent == 0:
                try:
                    state_path = f'{path}/state.json'
                    if Path(state_path).exists():
                        state = json.loads(Path(state_path).read_text())
                        sent = state.get('sent_today', state.get('daily_sent', 0))
                except:
                    pass

        campaigns[name] = {
            'display': config['display'],
            'sent_today': sent,
            'limit': config['limit'],
            'sender': config['sender']
        }

    return campaigns


def get_a2_warmup_status():
    """Get A2 SMTP warmup status."""
    warmup = {}
    today = datetime.now().strftime('%Y-%m-%d')

    # Calculate warmup day
    try:
        start = datetime.strptime(A2_WARMUP_START_DATE, '%Y-%m-%d')
        day = max(1, (datetime.now() - start).days + 1)
    except:
        day = 1

    # Get limit for current day
    limit = 500
    for s, e, l in A2_WARMUP_SCHEDULE:
        if s <= day <= e:
            limit = l
            break

    # Read state file
    try:
        state_file = Path('/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_warmup_state.json')
        if state_file.exists():
            state = json.loads(state_file.read_text())
            for domain, display in A2_DOMAINS.items():
                domain_state = state.get(domain, {})
                sent = 0
                if domain_state.get('last_send_date') == today:
                    sent = domain_state.get('sent_today', 0)
                warmup[domain] = {
                    'display': display,
                    'sent_today': sent,
                    'limit': limit,
                    'day': day
                }
    except Exception as e:
        logger.error(f"A2 warmup error: {e}")

    return warmup


def get_scraper_stats():
    """Get scraper statistics."""
    stats = {
        'running': 0,
        'recent_logs': [],
        'rows_today': 0
    }

    try:
        count = run("ps aux | grep -E 'python.*scraper' | grep -v grep | wc -l")
        stats['running'] = int(count) if count.isdigit() else 0
    except:
        pass

    try:
        recent = run("ls -t /opt/ACTIVE/INFRA/LOGS/*scraper*.log 2>/dev/null | head -5")
        stats['recent_logs'] = [Path(f).name for f in recent.split('\n') if f.strip()]
    except:
        pass

    try:
        rows = run("find /mnt/hdd/SCRAPER_DATA/csv -name '*.csv' -mtime -1 2>/dev/null | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}'")
        stats['rows_today'] = int(rows) if rows.isdigit() else 0
    except:
        pass

    return stats


def get_log_errors():
    """Count recent log errors."""
    try:
        count = run("grep -l -i 'error\\|fail\\|exception' /opt/ACTIVE/INFRA/LOGS/*.log 2>/dev/null | wc -l")
        return int(count) if count.isdigit() else 0
    except:
        return 0


def collect_metrics():
    """Collect all metrics for this machine."""
    hostname = get_hostname()
    logger.info(f"Collecting metrics for {hostname}")

    metrics = {
        'hostname': hostname,
        'timestamp': datetime.now().isoformat(),
        'epoch': time.time(),
        'uptime': get_uptime(),
        'cpu_percent': get_cpu_percent(),
        'memory': get_memory(),
        'disk_usage': get_disk_usage(),
        'services': get_services_status(hostname),
        'campaigns': get_campaign_stats(hostname),
        'log_errors': get_log_errors(),
    }

    # Add machine-specific metrics
    if hostname == 'raspibig':
        metrics['docker'] = get_docker_status()
        metrics['scrapers'] = get_scraper_stats()
    else:
        metrics['a2_warmup'] = get_a2_warmup_status()

    return metrics


def write_metrics(metrics):
    """Write metrics to JSON file."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = OUTPUT_DIR / f"{metrics['hostname']}_metrics.json"

    try:
        with open(output_file, 'w') as f:
            json.dump(metrics, f, indent=2, default=str)
        logger.info(f"Wrote metrics to {output_file}")
        return True
    except Exception as e:
        logger.error(f"Failed to write metrics: {e}")
        return False


def main():
    debug = '--debug' in sys.argv

    metrics = collect_metrics()

    if debug:
        print(json.dumps(metrics, indent=2, default=str))
    else:
        write_metrics(metrics)


if __name__ == '__main__':
    main()
