#!/usr/bin/env python3
"""
PicoClaw Watchdog — verifica ca Agent 3 + Agent 5 ruleaza pe cron si Node-RED.
Alerteaza daca ceva nu merge. Ruleaza la fiecare ora.

Cron: 0 * * * * python3 /opt/ACTIVE/AGENTS/picoclaw_watchdog.py

Verifica:
1. Cron entries exista pentru catalog + quality
2. Node-RED ruleaza si are tab-ul Agents
3. Ultimul log e recent (nu a sarit cron-ul)
4. Output cataloage exista si e actualizat
"""
import json, os, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path

LOG = "/opt/LOGS/picoclaw_watchdog.log"
PROBLEMS = []


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def check_cron():
    """Verifica ca cron entries exista."""
    result = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    cron = result.stdout

    if "catalog_updater" not in cron and "generate_catalogs" not in cron:
        PROBLEMS.append("CRON: Agent 3 (Catalog) nu e in crontab")
    if "agent_data_quality" not in cron:
        PROBLEMS.append("CRON: Agent 5 (Data Quality) nu e in crontab")


def check_nodered():
    """Verifica ca Node-RED ruleaza si are tab-ul Agents."""
    try:
        import requests
        r = requests.get("http://localhost:1880/flows", timeout=5)
        if r.status_code != 200:
            PROBLEMS.append("NODE-RED: nu raspunde pe /flows")
            return
        flows = r.json()
        tabs = [f.get("label", "") for f in flows if f.get("type") == "tab"]
        if not any("Agent" in t for t in tabs):
            PROBLEMS.append(f"NODE-RED: tab Agents lipseste. Tabs: {tabs}")
    except Exception as e:
        PROBLEMS.append(f"NODE-RED: eroare conexiune — {e}")


def check_logs():
    """Verifica ca logurile recente exista."""
    now = datetime.now()

    # Agent 3: ruleaza duminica — verifica daca ultima duminica a rulat
    catalog_log = Path("/opt/LOGS/catalog_updater.log")
    if catalog_log.exists():
        mtime = datetime.fromtimestamp(catalog_log.stat().st_mtime)
        days_old = (now - mtime).days
        if days_old > 8:
            PROBLEMS.append(f"LOG: catalog_updater.log vechi de {days_old} zile (ar trebui max 7)")
    # Nu alerta daca logul nu exista inca (prima rulare)

    # Agent 5: ruleaza sambata
    quality_logs = list(Path("/opt/ACTIVE/INFRA/LOGS").glob("data_quality_*.txt"))
    if quality_logs:
        newest = max(quality_logs, key=lambda p: p.stat().st_mtime)
        mtime = datetime.fromtimestamp(newest.stat().st_mtime)
        days_old = (now - mtime).days
        if days_old > 8:
            PROBLEMS.append(f"LOG: data_quality vechi de {days_old} zile (ar trebui max 7)")


def check_output():
    """Verifica ca output cataloage exista."""
    output_dir = Path("/opt/ACTIVE/WEB/CATALOGS/output")
    if output_dir.exists():
        domains = [d for d in output_dir.iterdir() if d.is_dir()]
        if len(domains) == 0:
            PROBLEMS.append("OUTPUT: /opt/ACTIVE/WEB/CATALOGS/output/ e gol")
        else:
            # Verifica freshness
            newest = max(domains, key=lambda d: d.stat().st_mtime)
            mtime = datetime.fromtimestamp(newest.stat().st_mtime)
            days_old = (datetime.now() - mtime).days
            if days_old > 10:
                PROBLEMS.append(f"OUTPUT: cataloage vechi de {days_old} zile")


def send_telegram(text):
    """Alerta Telegram doar la probleme."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        # Incearca din .env
        env_file = "/opt/ACTIVE/EMAIL/CAMPAIGNS/.env"
        if os.path.exists(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        bot_token = line.split("=", 1)[1].strip()
                    elif line.startswith("TELEGRAM_CHAT_ID="):
                        chat_id = line.split("=", 1)[1].strip()
    if not bot_token or not chat_id:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": text}, timeout=10
        )
    except Exception:
        pass


def main():
    log("Watchdog scan start")

    check_cron()
    check_nodered()
    check_logs()
    check_output()

    if PROBLEMS:
        msg = "⚠️ PicoClaw Watchdog — PROBLEME:\n" + "\n".join(f"• {p}" for p in PROBLEMS)
        log(msg)
        send_telegram(msg)
    else:
        log("OK — cron + Node-RED + logs + output toate OK")


if __name__ == "__main__":
    main()
