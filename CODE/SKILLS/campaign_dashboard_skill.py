#!/usr/bin/env python3
"""
Campaign Dashboard Skill — generate a replicable Flask dashboard for any country campaign.

Creates a full campaign dashboard (Flask app, systemd service, nginx config)
from a config.json. Used for Norway, Denmark, and future country campaigns.

Usage:
    # Check what exists
    python3 campaign_dashboard_skill.py --status

    # Generate dashboard for a new country
    python3 campaign_dashboard_skill.py --create --country DENMARK --port 8091 --prefix /denmark

    # Verify a running dashboard
    python3 campaign_dashboard_skill.py --verify --country NORWAY

Location: /opt/ACTIVE/INFRA/SKILLS/campaign_dashboard_skill.py
Created: 2026-03-01
"""

import os
import sys
import json
import shutil
import argparse
import subprocess
from pathlib import Path

CAMPAIGNS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS")
SKILLS_DIR = Path("/opt/ACTIVE/INFRA/SKILLS")
DASHBOARD_TEMPLATE = "dashboard.py"  # the replicable dashboard from Norway

# Country flag HTML entities
COUNTRY_FLAGS = {
    "NORWAY": "&#127475;&#127476;",
    "DENMARK": "&#127465;&#127472;",
    "SWEDEN": "&#127480;&#127466;",
    "FINLAND": "&#127467;&#127470;",
    "ICELAND": "&#127470;&#127480;",
    "POLAND": "&#127477;&#127473;",
    "GERMANY": "&#127465;&#127466;",
    "ROMANIA": "&#127479;&#127476;",
    "BULGARIA": "&#127463;&#127468;",
}

# Default regulated sectors (Norway-specific, override per country)
REGULATED_SECTORS = {
    "NORWAY": {
        "CONSTRUCTION": {"order":1,"min_wage":"234.60 NOK/h"},
        "HEALTHCARE":   {"order":2,"min_wage":"N/A"},
        "HORECA":       {"order":3,"min_wage":"196.50 NOK/h"},
        "AGRICULTURE":  {"order":4,"min_wage":"158.00 NOK/h"},
        "LOGISTICS":    {"order":5,"min_wage":"204.10 NOK/h"},
        "MANUFACTURING":{"order":6,"min_wage":"209.70 NOK/h"},
        "SHIPYARD":     {"order":7,"min_wage":"222.00 NOK/h"},
        "MANUAL":       {"order":8,"min_wage":"196.50 NOK/h"},
        "STAFFING":     {"order":9,"min_wage":"Varies"},
    },
    "DENMARK": {
        "CONSTRUCTION": {"order":1,"min_wage":"~180 DKK/h"},
        "HEALTHCARE":   {"order":2,"min_wage":"N/A"},
        "HORECA":       {"order":3,"min_wage":"~145 DKK/h"},
        "AGRICULTURE":  {"order":4,"min_wage":"~130 DKK/h"},
        "LOGISTICS":    {"order":5,"min_wage":"~160 DKK/h"},
        "MANUFACTURING":{"order":6,"min_wage":"~155 DKK/h"},
        "STAFFING":     {"order":7,"min_wage":"Varies"},
    },
}


def get_status():
    """Show status of all campaign dashboards."""
    print(f"\n{'='*80}")
    print(f"  CAMPAIGN DASHBOARDS STATUS")
    print(f"{'='*80}")

    for d in sorted(CAMPAIGNS_DIR.iterdir()):
        cfg_file = d / "config.json"
        dash_file = d / "dashboard.py"
        if not cfg_file.exists():
            continue

        try:
            with open(cfg_file) as f:
                cfg = json.load(f)
        except Exception:
            continue

        name = cfg.get("campaign_name", d.name)
        port = cfg.get("dashboard_port", "?")
        prefix = cfg.get("url_prefix", "?")
        has_dash = dash_file.exists()
        sectors = len(cfg.get("sectors", {}))
        db_name = cfg.get("db", {}).get("dbname", "?")
        gmail = len(cfg.get("gmail_senders", []))

        # Check if service is running
        svc_name = f"{name.lower()}-dashboard"
        running = False
        try:
            r = subprocess.run(["systemctl", "is-active", svc_name],
                             capture_output=True, text=True, timeout=5)
            running = r.stdout.strip() == "active"
        except Exception:
            pass

        status = "RUNNING" if running else ("STOPPED" if has_dash else "NO DASHBOARD")
        color = "\033[92m" if running else ("\033[93m" if has_dash else "\033[91m")
        reset = "\033[0m"

        print(f"  {color}{name:12s}{reset} | port {port} | {prefix:12s} | {sectors} sectors | DB: {db_name} | Gmail: {gmail} | {status}")

    print(f"{'='*80}\n")


def create_dashboard(country, port, prefix):
    """Create a new campaign dashboard by copying from Norway template."""
    country = country.upper()
    target_dir = CAMPAIGNS_DIR / country
    source_dash = CAMPAIGNS_DIR / "NORWAY" / DASHBOARD_TEMPLATE

    if not target_dir.exists():
        print(f"ERROR: Campaign directory {target_dir} does not exist")
        print(f"  Create it first with config.json, sectors, templates, etc.")
        return False

    cfg_file = target_dir / "config.json"
    if not cfg_file.exists():
        print(f"ERROR: {cfg_file} does not exist")
        return False

    # Update config.json with dashboard fields
    with open(cfg_file) as f:
        cfg = json.load(f)

    cfg["campaign_name"] = country
    cfg["dashboard_port"] = port
    cfg["url_prefix"] = prefix
    cfg["country_flag"] = COUNTRY_FLAGS.get(country, "&#127760;")

    if "gmail_senders" not in cfg:
        cfg["gmail_senders"] = [
            {"email": "manpower.dristor@gmail.com", "env_pass": "GMAIL_MANPOWERDRISTOR_APP_PASSWORD", "name": "InterJob Solutions Europe", "limit": 50},
            {"email": "elena.manpower.dristor@gmail.com", "env_pass": "GMAIL_ELENA_PASSWORD", "name": "InterJob Recruitment", "limit": 50},
            {"email": "pamintstrabun@gmail.com", "env_pass": "GMAIL_PAMINTSTRABUN_PASSWORD", "name": "InterJob Solutions", "limit": 50},
            {"email": "manpowersearchromania@gmail.com", "env_pass": "GMAIL_MANPOWERSEARCH_PASSWORD", "name": "InterJob Manpower", "limit": 20},
        ]

    with open(cfg_file, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"  Updated {cfg_file} with dashboard config")

    # Copy dashboard.py from Norway (it's config-driven, no code changes needed)
    if not source_dash.exists():
        print(f"ERROR: Source dashboard {source_dash} not found")
        return False

    target_dash = target_dir / DASHBOARD_TEMPLATE
    shutil.copy2(source_dash, target_dash)
    os.chmod(target_dash, 0o755)
    print(f"  Copied dashboard.py to {target_dash}")

    # Create directories
    (target_dir / "state").mkdir(exist_ok=True)
    (target_dir / "templates").mkdir(exist_ok=True)
    (target_dir / "logs").mkdir(exist_ok=True)

    # Generate systemd service
    svc_name = f"{country.lower()}-dashboard"
    svc_content = f"""[Unit]
Description={country} Campaign Dashboard
After=network.target postgresql.service

[Service]
Type=simple
User=tudor
WorkingDirectory={target_dir}
ExecStart=/opt/ACTIVE/INFRA/venv/bin/python3 {target_dash}
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
"""
    svc_path = f"/etc/systemd/system/{svc_name}.service"
    print(f"\n  Systemd service file ({svc_path}):")
    print(f"  ---")
    for line in svc_content.strip().split("\n"):
        print(f"    {line}")
    print(f"  ---")
    print(f"\n  To install:")
    print(f"    sudo tee {svc_path} << 'EOF'\n{svc_content}EOF")
    print(f"    sudo systemctl daemon-reload")
    print(f"    sudo systemctl enable --now {svc_name}")

    # Nginx config
    print(f"\n  Nginx location block (add to /etc/nginx/sites-enabled/raspibig):")
    print(f"    location {prefix}/ {{")
    print(f"        proxy_pass http://127.0.0.1:{port};")
    print(f"        proxy_set_header Host $host;")
    print(f"        proxy_set_header X-Real-IP $remote_addr;")
    print(f"    }}")
    print(f"\n    sudo nginx -t && sudo systemctl reload nginx")

    print(f"\n  Dashboard ready at: http://raspibig:{port}{prefix}/")
    return True


def verify_dashboard(country):
    """Verify a running dashboard."""
    country = country.upper()
    target_dir = CAMPAIGNS_DIR / country
    cfg_file = target_dir / "config.json"

    if not cfg_file.exists():
        print(f"ERROR: {cfg_file} not found")
        return False

    with open(cfg_file) as f:
        cfg = json.load(f)

    port = cfg.get("dashboard_port", 8090)
    prefix = cfg.get("url_prefix", f"/{country.lower()}")
    checks = []

    # Check files
    checks.append(("config.json", cfg_file.exists()))
    checks.append(("dashboard.py", (target_dir / "dashboard.py").exists()))
    checks.append(("state/", (target_dir / "state").is_dir()))
    checks.append(("templates/", (target_dir / "templates").is_dir()))

    # Check service
    svc_name = f"{country.lower()}-dashboard"
    try:
        r = subprocess.run(["systemctl", "is-active", svc_name],
                         capture_output=True, text=True, timeout=5)
        checks.append((f"systemd {svc_name}", r.stdout.strip() == "active"))
    except Exception:
        checks.append((f"systemd {svc_name}", False))

    # Check HTTP
    import urllib.request
    endpoints = [
        (f"http://localhost:{port}{prefix}/", "Overview"),
        (f"http://localhost:{port}{prefix}/api/status", "API Status"),
        (f"http://localhost:{port}{prefix}/schedule", "Schedule"),
    ]
    for url, label in endpoints:
        try:
            r = urllib.request.urlopen(url, timeout=5)
            checks.append((f"HTTP {label}", r.status == 200))
        except Exception:
            checks.append((f"HTTP {label}", False))

    # Print results
    print(f"\n  {country} Dashboard Verification:")
    all_ok = True
    for label, ok in checks:
        icon = "PASS" if ok else "FAIL"
        print(f"    [{icon}] {label}")
        if not ok:
            all_ok = False

    if all_ok:
        print(f"\n  ALL CHECKS PASSED")
    else:
        print(f"\n  SOME CHECKS FAILED")
    return all_ok


def main():
    p = argparse.ArgumentParser(description="Campaign Dashboard Skill")
    p.add_argument("--status", action="store_true", help="Show all dashboards status")
    p.add_argument("--create", action="store_true", help="Create new dashboard")
    p.add_argument("--verify", action="store_true", help="Verify running dashboard")
    p.add_argument("--country", type=str, help="Country name (e.g., DENMARK)")
    p.add_argument("--port", type=int, default=8091, help="Dashboard port")
    p.add_argument("--prefix", type=str, help="URL prefix (e.g., /denmark)")
    args = p.parse_args()

    if args.status:
        get_status()
        return

    if args.create:
        if not args.country:
            p.error("--country required for --create")
        prefix = args.prefix or f"/{args.country.lower()}"
        create_dashboard(args.country, args.port, prefix)
        return

    if args.verify:
        if not args.country:
            p.error("--country required for --verify")
        verify_dashboard(args.country)
        return

    p.print_help()


if __name__ == "__main__":
    main()
