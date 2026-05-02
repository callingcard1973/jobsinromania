#!/usr/bin/env python3
"""
Node-RED Watchdog - Ensures Node-RED stays healthy and running

Checks every 5 minutes:
1. Process running
2. Memory under limit (500MB)
3. HTTP responding

Actions:
- Restart if unhealthy
- Alert via Telegram
- Log all events
"""

import sys
sys.path.insert(0, '/opt/ACTIVE/SCRAPERS/EUROPE/SCRIPTS/SHARED')

import os
import subprocess
import requests
from datetime import datetime
from pathlib import Path

NODERED_URL = "http://127.0.0.1:1880"
MEMORY_LIMIT_MB = 500

def log(msg):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"{timestamp} {msg}")

def send_telegram(msg):
    try:
        from alerting import send_telegram as tg_send
        tg_send(f"🔴 NODE-RED: {msg}")
    except Exception as e:
        log(f"Telegram failed: {e}")

def get_nodered_pid():
    try:
        result = subprocess.run(["pgrep", "-f", "node-red"], capture_output=True, text=True)
        pids = result.stdout.strip().split('\n')
        return int(pids[0]) if pids and pids[0] else None
    except:
        return None

def get_memory_mb(pid):
    try:
        result = subprocess.run(["ps", "-o", "rss=", "-p", str(pid)], capture_output=True, text=True)
        return int(result.stdout.strip()) / 1024
    except:
        return 0

def check_http_health():
    try:
        resp = requests.get(NODERED_URL, timeout=10)
        return resp.status_code == 200
    except:
        return False

def restart_nodered():
    log("Restarting Node-RED...")
    try:
        subprocess.run(["sudo", "systemctl", "restart", "nodered"], check=True)
        log("Restarted successfully")
        return True
    except Exception as e:
        log(f"Restart failed: {e}")
        return False

def run_watchdog():
    issues = []
    
    pid = get_nodered_pid()
    if not pid:
        issues.append("Process not running")
    else:
        mem_mb = get_memory_mb(pid)
        if mem_mb > MEMORY_LIMIT_MB:
            issues.append(f"Memory {mem_mb:.0f}MB > {MEMORY_LIMIT_MB}MB")
        
        if not check_http_health():
            issues.append("HTTP not responding")
    
    if issues:
        msg = ", ".join(issues)
        log(f"UNHEALTHY: {msg}")
        send_telegram(f"Unhealthy: {msg} - Restarting...")
        
        if restart_nodered():
            send_telegram("Restarted successfully")
        else:
            send_telegram("RESTART FAILED!")
    else:
        if datetime.now().minute < 5:
            log("OK")

if __name__ == "__main__":
    run_watchdog()
