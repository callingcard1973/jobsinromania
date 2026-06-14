#!/bin/bash
# Wrapper for memory rsync to raspi — always writes a timestamped line to log
# so monitor_crons.py never sees a stale mtime.
LOG=/opt/ACTIVE/INFRA/LOGS/memory_sync_raspi.log
SRC=/home/tudor/.claude/projects/D--MEMORY/memory
TS="[$(date '+%Y-%m-%d %H:%M')]"
if [ -z "$(ls -A "$SRC" 2>/dev/null)" ]; then
  echo "$TS ABORT: source empty or missing, refusing --delete sync" >> "$LOG"
  exit 2
fi
rsync -az --delete "$SRC/" tudor@192.168.100.20:"$SRC/" >> "$LOG" 2>&1
RC=$?
if [ $RC -eq 0 ]; then
  echo "$TS Memory sync completed" >> "$LOG"
else
  echo "$TS Memory sync FAILED (rc=$RC)" >> "$LOG"
fi
