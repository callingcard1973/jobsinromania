#!/bin/bash
# Orchestrator terenuri — ruleaza secvential: hunter → anomaly → cma → alert
# Cron: 0 6,18 * * * bash /opt/ACTIVE/AGENTS/TERENURI/run_terenuri.sh
set -e
DIR="/opt/ACTIVE/AGENTS/TERENURI"
LOG="/opt/LOGS/terenuri.log"
TS=$(date +%Y-%m-%d_%H:%M)

echo "[$TS] === TERENURI PIPELINE START ===" >> "$LOG"

# 1. Listing Hunter — scaneaza OLX + Imobiliare
echo "[$TS] Step 1: Listing Hunter" >> "$LOG"
cd "$DIR" && python3 listing_hunter.py --pages 3 >> "$LOG" 2>&1

# 2. Price Anomaly — detecteaza sub-piata
echo "[$TS] Step 2: Price Anomaly" >> "$LOG"
cd "$DIR" && python3 price_anomaly.py --threshold 50 >> "$LOG" 2>&1

# 3. Deal Alert — trimite Telegram
echo "[$TS] Step 3: Deal Alert" >> "$LOG"
cd "$DIR" && python3 deal_alert.py --min-score 30 --hours 24 >> "$LOG" 2>&1

echo "[$TS] === TERENURI PIPELINE DONE ===" >> "$LOG"
