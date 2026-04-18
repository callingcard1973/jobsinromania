"""
Step 30: Email template auto-selector
Maps standard_sector -> best template from raspibig campaigns.
Outputs campaign package: CSV + template path + send command.

Usage: python step30_template_selector.py --csv campaign_NO_construction_5000.csv
"""

import csv
import argparse
from pathlib import Path
import subprocess

TEMPLATES = {
    "construction": "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/harghita_phase1_construction.txt",
    "manufacturing": "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/manufacturing_template.txt",
    "hospitality":  "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/hospitality_template.txt",
    "transport":    "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/curierat/tudor_template1.txt",
    "healthcare":   "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/careworkers_template.txt",
    "agriculture":  "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/farmworkers_template.txt",
    "it":           "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/it_template.txt",
    "retail":       "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/generic_template.txt",
    "facility":     "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/generic_template.txt",
    "trades":       "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/harghita_phase1_construction.txt",
    "other":        "/opt/ACTIVE/EMAIL/CAMPAIGNS/templates/generic_template.txt",
}

SENDER = "office@mivromania.info"
REPLY_TO = "manpower.dristor@gmail.com"


def detect_sector(csv_path: Path) -> str:
    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        sectors = [r.get("standard_sector","other") for r in reader if r.get("standard_sector")]
    if not sectors:
        return "other"
    return max(set(sectors), key=sectors.count)


def generate_package(csv_path: Path):
    sector = detect_sector(csv_path)
    template = TEMPLATES.get(sector, TEMPLATES["other"])
    campaign_name = csv_path.stem.upper()

    pkg = csv_path.parent / f"{csv_path.stem}_SEND_PACKAGE.txt"
    pkg.write_text(f"""# Campaign Send Package
# Generated: auto

CSV: {csv_path}
TEMPLATE: {template}
CAMPAIGN: {campaign_name}
SECTOR: {sector}
SENDER: {SENDER}
REPLY_TO: {REPLY_TO}
DAILY_LIMIT: 100

# Deploy to raspibig:
# scp "{csv_path}" tudor@192.168.100.21:/opt/ACTIVE/EMAIL/CAMPAIGNS/
# ssh tudor@192.168.100.21 'python3 /opt/ACTIVE/EMAIL/CAMPAIGNS/brevo_send.py \\
#   --csv /opt/ACTIVE/EMAIL/CAMPAIGNS/{csv_path.name} \\
#   --template {template} \\
#   --campaign {campaign_name} \\
#   --daily-limit 100'
""", encoding="utf-8")

    print(f"Package -> {pkg.name}")
    print(f"  Sector: {sector}")
    print(f"  Template: {template}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--csv", required=True)
    args = p.parse_args()
    generate_package(Path(args.csv))
