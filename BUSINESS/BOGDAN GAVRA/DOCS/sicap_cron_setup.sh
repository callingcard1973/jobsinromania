#!/bin/bash
# sicap_cron_setup.sh — Add SICAP monitor to crontab
# Runs every Monday at 08:00

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Add to crontab (edit manually if needed)
# 0 8 * * 1 cd /path/to/script && python3 sicap_monitor.py

echo "Add this line to crontab (crontab -e):"
echo "0 8 * * 1 cd \"${SCRIPT_DIR}\" && python3 sicap_monitor.py >> sicap_monitor.log 2>&1"
