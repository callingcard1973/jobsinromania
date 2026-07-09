#!/bin/bash
# Setup cron job for daily roundup orchestrator
# Run on raspibig as: bash setup_cron.sh

CRON_TIME="0 9 * * *"  # 09:00 UTC daily
EVENT_PUB_DIR="/opt/ACTIVE/EVENT_PUBLISHER"
LOG_DIR="/opt/ACTIVE/INFRA/LOGS"
CRONTAB_TMP=$(mktemp)

# Ensure directories exist
mkdir -p "$EVENT_PUB_DIR" "$LOG_DIR"

# Generate cron entry
CRON_ENTRY="$CRON_TIME cd $EVENT_PUB_DIR && python3 orchestrator.py >> $LOG_DIR/daily_roundup.log 2>&1"

# Backup current crontab
crontab -l > "$CRONTAB_TMP.backup" 2>/dev/null || true

# Add new entry if not already present
if ! crontab -l 2>/dev/null | grep -q "daily_roundup.orchestrator"; then
    (crontab -l 2>/dev/null || true; echo "# Daily roundup orchestrator — 09:00 UTC"; echo "$CRON_ENTRY") | crontab -
    echo "✅ Cron entry added:"
    echo "   $CRON_ENTRY"
else
    echo "⚠️  Cron entry already exists"
fi

# Verify
echo ""
echo "Current cron jobs:"
crontab -l | grep -v "^#" | grep "daily_roundup\|orchestrator" || echo "  (none found)"

echo ""
echo "Log file: $LOG_DIR/daily_roundup.log"
echo "Backup: $CRONTAB_TMP.backup"
