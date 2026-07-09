#!/bin/bash
# Norway CONSTRUCTION warmup ramp, self-healing: tops up to the day's target from
# whatever was already sent today (so an interrupted morning run recovers; never overshoots).
# Ramp: 50/day (d1-10) -> 100 (d11-20) -> 150 (d21-30) -> 200 (d31+).
cd "$(dirname "$0")"
SF=state/construction_ramp_start.txt
[ -f "$SF" ] || date +%Y-%m-%d > "$SF"
START=$(cat "$SF")
DAYS=$(( ( $(date +%s) - $(date -d "$START" +%s) ) / 86400 ))
if   [ $DAYS -lt 10 ]; then LIMIT=50
elif [ $DAYS -lt 20 ]; then LIMIT=100
elif [ $DAYS -lt 30 ]; then LIMIT=150
else LIMIT=200; fi
SENT=$(psql -h 127.0.0.1 -U tudor -d interjob_master -tAc "SELECT count(*) FROM norway_send_log WHERE campaign='NORWAY_CONSTRUCTION' AND sent_at::date=CURRENT_DATE;" 2>/dev/null | tr -d ' ')
SENT=${SENT:-0}
REMAIN=$(( LIMIT - SENT ))
echo "$(date '+%F %T') ramp day=$DAYS target=$LIMIT sent_today=$SENT remaining=$REMAIN"
[ "$REMAIN" -le 0 ] && { echo "daily target already met"; exit 0; }
exec /opt/ACTIVE/INFRA/venv/bin/python3 send_norway.py --sector CONSTRUCTION --limit "$REMAIN"
