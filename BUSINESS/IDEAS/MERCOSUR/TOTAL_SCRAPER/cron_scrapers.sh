#!/bin/bash
# Mercosur scrapers with RANDOM DELAY
# Never runs at exact times - adds 0-59 min jitter

SCRAPER_DIR="/opt/ACTIVE/IDEAS/MERCOSUR/CLAUDE/OPENCODE/scrapers/mercosur"
LOG_DIR="/opt/ACTIVE/IDEAS/MERCOSUR/TOTAL_SCRAPER/logs"
OUTPUT_DIR="/mnt/hdd/GLOBAL_DOWNLOADS/mercosur_data"

mkdir -p "$LOG_DIR" "$OUTPUT_DIR"

# Random delay 0-59 minutes
JITTER=$((RANDOM % 60))
echo "[$(date)] Waiting ${JITTER} minutes before starting..." >> "$LOG_DIR/cron.log"
sleep ${JITTER}m

cd "$SCRAPER_DIR"

case "$1" in
  apex)
    python3 apex_brasil_scraper.py --all-sectors --limit 500 --output "$OUTPUT_DIR/apex_brasil.csv" >> "$LOG_DIR/apex.log" 2>&1
    ;;
  connectamericas)
    python3 connectamericas_scraper.py --all --limit 500 --output "$OUTPUT_DIR/connectamericas.csv" >> "$LOG_DIR/connectamericas.log" 2>&1
    ;;
  brazil)
    python3 brazil_exporters.py --full --limit 500 --output "$OUTPUT_DIR/brazil_exporters.csv" >> "$LOG_DIR/brazil.log" 2>&1
    ;;
  associations)
    for f in associations/*.py; do
      sleep $((RANDOM % 300))  # 0-5 min between each
      python3 "$f" --output "$OUTPUT_DIR/$(basename $f .py).csv" >> "$LOG_DIR/associations.log" 2>&1
    done
    ;;
  government)
    for f in government/*.py; do
      sleep $((RANDOM % 300))
      python3 "$f" --output "$OUTPUT_DIR/$(basename $f .py).csv" >> "$LOG_DIR/government.log" 2>&1
    done
    ;;
  tradeshows)
    for f in tradeshows/*.py; do
      sleep $((RANDOM % 300))
      python3 "$f" --output "$OUTPUT_DIR/$(basename $f .py).csv" >> "$LOG_DIR/tradeshows.log" 2>&1
    done
    ;;
  enrich)
    python3 working/enrich_contacts.py --input "$OUTPUT_DIR" >> "$LOG_DIR/enrich.log" 2>&1
    ;;
  merge)
    python3 working/final_merge.py --input "$OUTPUT_DIR" --output "$OUTPUT_DIR/mercosur_all.csv" >> "$LOG_DIR/merge.log" 2>&1
    ;;
esac
