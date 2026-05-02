#!/usr/bin/env python3
"""
Dashboard Configuration - Single source of truth for all dashboard settings.
Edit this file instead of modifying static_dashboard.py.
"""

# ============================================================================
# CAMPAIGN DEFINITIONS
# ============================================================================

# Campaigns on RASPIBIG (Brevo senders)
RASPIBIG_CAMPAIGNS = {
    'GERMANY_AGENCIES': {'display': 'Germany Agencies', 'limit': 290, 'sender': 'BREVO'},
    'ROMANIA_TRANSLATORS': {'display': 'Romania Translators', 'limit': 290, 'sender': 'BREVO'},
    'EU_CONTRACTORS': {'display': 'EU Contractors', 'limit': 290, 'sender': 'BREVO'},
    'NORDIC': {'display': 'Nordic', 'limit': 290, 'sender': 'BREVO'},
}

# Campaigns on RASPI (Brevo + A2 Hosting)
RASPI_CAMPAIGNS = {
    'POLAND': {'display': 'Poland Agencies', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/POLAND', 'limit': 290, 'sender': 'BREVO'},
    'FACTORY_EU': {'display': 'Factory EU', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FACTORY_EU', 'limit': 290, 'sender': 'BREVO'},
    'EUFUNDS2026': {'display': 'EU Funds', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/EUFUNDS2026', 'limit': 290, 'sender': 'BREVO'},
    'CQC': {'display': 'CQC UK', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/CQC', 'limit': 100, 'sender': 'BREVO'},
    'BUILDJOBS_BREVO': {'display': 'Build Jobs', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/BUILDJOBS_BREVO', 'limit': 290, 'sender': 'BREVO'},
    'CAREWORKERS_BREVO': {'display': 'Care Workers', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/CAREWORKERS_BREVO', 'limit': 290, 'sender': 'BREVO'},
    'HORECAWORKERS_A2': {'display': 'Horeca Workers', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/HORECAWORKERS_A2', 'limit': 50, 'sender': 'A2HOSTING', 'domain': 'horecaworkers.eu'},
    'MEATWORKERS_A2': {'display': 'Meat Workers', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/MEATWORKERS_A2', 'limit': 50, 'sender': 'A2HOSTING', 'domain': 'meatworkers.eu'},
    'ELECTRICJOBS_A2': {'display': 'Electric Jobs', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/ELECTRICJOBS_A2', 'limit': 50, 'sender': 'A2HOSTING', 'domain': 'electricjobs.eu'},
    'FARMWORKERS_A2': {'display': 'Farm Workers', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/FARMWORKERS_A2', 'limit': 50, 'sender': 'A2HOSTING', 'domain': 'farmworkers.eu'},
    'MECHANICJOBS_A2': {'display': 'Mechanic Jobs', 'path': '/opt/ACTIVE/EMAIL/CAMPAIGNS/MECHANICJOBS_A2', 'limit': 50, 'sender': 'A2HOSTING', 'domain': 'mechanicjobs.eu'},
}

# ============================================================================
# A2 HOSTING SMTP CONFIGURATION
# ============================================================================

A2_DOMAINS = {
    'horecaworkers.eu': 'Horeca Workers',
    'meatworkers.eu': 'Meat Workers',
    'electricjobs.eu': 'Electric Jobs',
    'mechanicjobs.eu': 'Mechanic Jobs',
    'farmworkers.eu': 'Farm Workers',
    'factoryjobs.eu': 'Factory Jobs',
    'warehouseworkers.eu': 'Warehouse Workers',
}

# A2 Warmup schedule: (start_day, end_day, daily_limit)
A2_WARMUP_SCHEDULE = [
    (1, 3, 20),
    (4, 7, 50),
    (8, 14, 100),
    (15, 21, 200),
    (22, 28, 350),
    (29, 999, 500),
]

A2_WARMUP_START_DATE = '2026-01-15'

# ============================================================================
# BREVO WARMUP CONFIGURATION
# ============================================================================

BREVO_CAMPAIGNS = {
    'FINLAND': 'Finland Jobs',
    'FINLAND_BREVO': 'Finland Jobs',
    'SWEDEN': 'Sweden Jobs',
    'SWEDEN_BREVO': 'Sweden Jobs',
    'NORWAY': 'Norway Jobs',
    'NORWAY_BREVO': 'Norway Jobs',
    'CUMPARLEGUME': 'Cumpar Legume',
    'CUMPARLEGUME_BREVO': 'Cumpar Legume',
    'SEICARESCU': 'Sei Carescu',
    'SEICARESCU_BREVO': 'Sei Carescu',
    'WAREHOUSE': 'Warehouse Workers',
    'WAREHOUSE_BREVO': 'Warehouse Workers',
}

# ============================================================================
# SERVICES TO MONITOR
# ============================================================================

RASPIBIG_SERVICES = [
    ('postgresql', 'systemctl is-active postgresql'),
    ('node-red', 'pgrep -x node-red >/dev/null && echo running || echo stopped'),
    ('telegram-bot', 'systemctl is-active telegram-bot'),
    ('nginx', 'systemctl is-active nginx'),
    ('fail2ban', 'systemctl is-active fail2ban'),
    ('bounce-webhook', 'systemctl is-active bounce-webhook'),
    ('brevo-warmup', 'systemctl is-active brevo-warmup'),
    ('a2-warmup', 'systemctl is-active a2-warmup'),
    ('eures-western', 'systemctl is-active eures-western'),
    ('odoo', 'docker ps -q -f name=odoo | grep -q . && echo running || echo stopped'),
    ('odoo-db', 'docker ps -q -f name=odoo-db | grep -q . && echo running || echo stopped'),
]

RASPI_SERVICES = [
    'nodered',
    'postgresql',
    'nginx',
    'fail2ban',
    'applicant-dashboard',
]

# ============================================================================
# DOCKER CONTAINERS TO MONITOR
# ============================================================================

DOCKER_CONTAINERS = [
    'freescout',
    'signal',
    'portainer',
]

# ============================================================================
# PATHS
# ============================================================================

PATHS = {
    'a2_warmup_state': '/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_warmup_state.json',
    'a2_credentials': '/opt/ACTIVE/EMAIL/CAMPAIGNS/a2_smtp_credentials.json',
    'brevo_warmup_log': '/opt/ACTIVE/INFRA/LOGS/brevo_warmup_daily.log',
    'logs_dir': '/opt/ACTIVE/INFRA/LOGS',
    'scraper_data': '/mnt/hdd/SCRAPER_DATA/csv',
    'dashboard_output': '/tmp/dashboard.html',
    'dashboard_served': '/opt/ACTIVE/OPENDATA/DATA/status.html',
    'sync_state_dir': '/opt/ACTIVE/INFRA/SYNC_STATE',
}

# ============================================================================
# TIMING & THRESHOLDS
# ============================================================================

DASHBOARD_REFRESH_SECONDS = 60
METRICS_STALE_THRESHOLD_SECONDS = 600  # 10 minutes
DISK_WARNING_PERCENT = 80
DISK_CRITICAL_PERCENT = 90
LOG_ERROR_WARNING_THRESHOLD = 5
LOG_ERROR_CRITICAL_THRESHOLD = 20

# ============================================================================
# DISPLAY SETTINGS
# ============================================================================

CSS_COLORS = {
    'background': '#0a0a1a',
    'text': '#eee',
    'ok': '#4ade80',
    'warn': '#ffc107',
    'err': '#ff6b6b',
    'dim': '#666',
    'accent': '#00d9ff',
    'card_bg': '#12122a',
    'card_border': '#2a2a4a',
    'brevo_badge': '#ffc107',
    'a2hosting_badge': '#4ade80',
}
