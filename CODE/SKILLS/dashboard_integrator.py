#!/usr/bin/env python3
"""
Dashboard Integrator Skill

Automatically integrates new campaigns into the pipeline dashboard system.
- Detects new campaign configs in UNIFIED/configs/
- Adds entries to pipeline.json
- Adds nginx redirects for /campaign_name/ -> /pipeline/campaign/campaign_name
- Restarts dashboard service

Usage:
    python3 dashboard_integrator.py --scan           # Show unintegrated campaigns
    python3 dashboard_integrator.py --add norway     # Add specific campaign
    python3 dashboard_integrator.py --add-all        # Add all unintegrated campaigns
    python3 dashboard_integrator.py --nginx          # Generate nginx redirects
    python3 dashboard_integrator.py --restart        # Restart dashboard service
"""

import os
import sys
import json
import argparse
import subprocess
from pathlib import Path

# Paths
CONFIGS_DIR = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/configs")
PIPELINE_JSON = Path("/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/pipeline.json")
NGINX_CONF = Path("/etc/nginx/sites-enabled/raspibig")
DASHBOARD_PORT = 8097

# Default campaign template
DEFAULT_CAMPAIGN = {
    "service": "campaign-unified",
    "db": {
        "host": "localhost",
        "dbname": "interjob_master",
        "user": "tudor",
        "password": "scraper123"
    },
    "tables": {
        "conversions": "conversions"
    },
    "total_contacts": 0,
    "daily_capacity": 100,
    "status_column": "campaign_status"
}


def load_pipeline_json():
    """Load pipeline.json"""
    with open(PIPELINE_JSON, 'r') as f:
        return json.load(f)


def save_pipeline_json(data):
    """Save pipeline.json"""
    with open(PIPELINE_JSON, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"✓ Saved {PIPELINE_JSON}")


def get_config_files():
    """Get all campaign config files"""
    configs = {}
    for f in CONFIGS_DIR.glob("*.json"):
        if f.name.startswith("state"):
            continue
        name = f.stem
        configs[name] = f
    return configs


def get_integrated_campaigns():
    """Get campaigns already in pipeline.json"""
    data = load_pipeline_json()
    return set(data.get("campaigns", {}).keys())


def scan_unintegrated():
    """Find campaigns not yet in pipeline.json"""
    config_files = get_config_files()
    integrated = get_integrated_campaigns()

    unintegrated = []
    for name, path in config_files.items():
        if name not in integrated:
            unintegrated.append((name, path))

    return unintegrated


def parse_config_file(config_path):
    """Parse campaign config file to extract table info"""
    with open(config_path, 'r') as f:
        config = json.load(f)

    tables = config.get("tables", {})
    return {
        "contacts": tables.get("contacts", f"{config_path.stem}_campaign"),
        "send_log": tables.get("send_log", f"{config_path.stem}_send_log"),
        "responses": tables.get("responses", f"{config_path.stem}_responses"),
        "dnc": tables.get("dnc", f"{config_path.stem}_dnc"),
    }


def add_campaign(name, config_path=None):
    """Add a campaign to pipeline.json"""
    data = load_pipeline_json()

    if "campaigns" not in data:
        data["campaigns"] = {}

    if name in data["campaigns"]:
        print(f"⚠ Campaign '{name}' already exists in pipeline.json")
        return False

    # Find config file if not provided
    if config_path is None:
        config_path = CONFIGS_DIR / f"{name}.json"

    if not config_path.exists():
        print(f"✗ Config file not found: {config_path}")
        return False

    # Parse config to get table names
    tables = parse_config_file(config_path)

    # Create campaign entry
    campaign = DEFAULT_CAMPAIGN.copy()
    campaign["config"] = str(config_path)
    campaign["tables"] = {
        "contacts": tables["contacts"],
        "send_log": tables["send_log"],
        "responses": tables["responses"],
        "dnc": tables["dnc"],
        "conversions": "conversions"
    }
    campaign["template"] = f"/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/templates/{name}/template1.txt"

    data["campaigns"][name] = campaign
    save_pipeline_json(data)
    print(f"✓ Added campaign '{name}' to pipeline.json")
    return True


def generate_nginx_redirects():
    """Generate nginx redirect rules for all campaigns"""
    integrated = get_integrated_campaigns()

    lines = []
    lines.append("    # Campaign redirects (auto-generated)")
    for name in sorted(integrated):
        lines.append(f"    location = /{name}/ {{ return 302 /pipeline/campaign/{name}; }}")
        lines.append(f"    location = /{name}  {{ return 302 /pipeline/campaign/{name}; }}")

    print("\n".join(lines))
    print(f"\n# Add these lines to {NGINX_CONF}")
    print("# Then run: sudo nginx -t && sudo systemctl reload nginx")


def restart_dashboard():
    """Restart the pipeline dashboard"""
    try:
        # Kill existing process on port 8097
        subprocess.run(["fuser", "-k", f"{DASHBOARD_PORT}/tcp"],
                      capture_output=True, timeout=5)

        # Start new dashboard
        cmd = [
            "/opt/ACTIVE/INFRA/venv/bin/python3",
            "/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED/pipeline_dashboard.py",
            "--config", str(PIPELINE_JSON),
            "--port", str(DASHBOARD_PORT)
        ]

        subprocess.Popen(cmd,
                        stdout=open("/tmp/pipeline_dashboard.log", "w"),
                        stderr=subprocess.STDOUT,
                        cwd="/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED")

        print(f"✓ Dashboard restarted on port {DASHBOARD_PORT}")
        print(f"  Log: /tmp/pipeline_dashboard.log")
        return True
    except Exception as e:
        print(f"✗ Failed to restart dashboard: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Dashboard Integrator Skill")
    parser.add_argument("--scan", action="store_true", help="Show unintegrated campaigns")
    parser.add_argument("--add", type=str, help="Add specific campaign by name")
    parser.add_argument("--add-all", action="store_true", help="Add all unintegrated campaigns")
    parser.add_argument("--nginx", action="store_true", help="Generate nginx redirects")
    parser.add_argument("--restart", action="store_true", help="Restart dashboard service")
    parser.add_argument("--status", action="store_true", help="Show integration status")

    args = parser.parse_args()

    if args.scan or args.status:
        print("=== Dashboard Integration Status ===\n")

        integrated = get_integrated_campaigns()
        print(f"Integrated campaigns ({len(integrated)}):")
        for name in sorted(integrated):
            print(f"  ✓ {name}")

        unintegrated = scan_unintegrated()
        if unintegrated:
            print(f"\nUnintegrated configs ({len(unintegrated)}):")
            for name, path in unintegrated:
                print(f"  ○ {name} ({path})")
        else:
            print("\n✓ All configs are integrated")

    elif args.add:
        add_campaign(args.add)

    elif args.add_all:
        unintegrated = scan_unintegrated()
        if not unintegrated:
            print("✓ All campaigns already integrated")
            return

        for name, path in unintegrated:
            add_campaign(name, path)

        print(f"\n✓ Added {len(unintegrated)} campaigns")
        print("Run --restart to apply changes")

    elif args.nginx:
        generate_nginx_redirects()

    elif args.restart:
        restart_dashboard()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
