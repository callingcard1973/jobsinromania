#!/bin/bash
# Wrapper for git pull from remote — always writes a timestamped line to log
# so monitor_crons.py never sees a stale mtime.
LOG=/opt/ACTIVE/INFRA/LOGS/memory_pull.log
TS="[$(date '+%Y-%m-%d %H:%M')]"
cd /home/tudor/.claude/projects/D--MEMORY/memory || { echo "$TS FAILED: dir missing" >> "$LOG"; exit 1; }
git pull origin main --quiet >> "$LOG" 2>&1
RC=$?
if [ $RC -eq 0 ]; then
  echo "$TS Memory pull completed" >> "$LOG"
else
  echo "$TS Memory pull FAILED (rc=$RC)" >> "$LOG"
fi
