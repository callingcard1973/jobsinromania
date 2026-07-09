#!/usr/bin/env python3
"""Bot Watchdog for RASPI (192.168.100.20). Runs every 15 min via cron.
Checks: services, campaign API, orchestrator, disk, DB, Node-RED, Caddy."""
import subprocess, os, shutil, requests
from datetime import datetime
from pathlib import Path

TOKEN = "8546618948:AAG0neoQA-kNq0M2GrZX7J-dGXNvEJEOK9w"
CHAT = "547047851"
LOG = "/home/tudor/.logs/bot_watchdog.log"

SERVICES = [
    "interjob-master-bot", "telegram-bot", "campaign-api",
    "postgresql", "redis-server", "caddy", "nodered",
]


def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def alert(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": CHAT, "text": f"🔴 RASPI WATCHDOG: {msg}",
                  "parse_mode": "HTML"}, timeout=10)
    except Exception:
        pass


def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return r.returncode == 0, r.stdout.strip()
    except Exception:
        return False, "TIMEOUT"


def check_service(name):
    ok, out = run(f"systemctl is-active {name}")
    return out == "active"


def restart_service(name):
    ok, _ = run(f"sudo systemctl restart {name}")
    return ok


def main():
    dead, healed = [], []

    # 1. SERVICES
    for svc in SERVICES:
        if not check_service(svc):
            log(f"{svc} DOWN — restarting")
            if restart_service(svc):
                healed.append(svc)
            else:
                dead.append(svc)
        else:
            log(f"{svc} OK")

    # 2. CAMPAIGN ORCHESTRATOR — check if ran in last 5 min
    ok, out = run("find /opt/EMAIL/CAMPAIGNS/logs/orchestrator.log -mmin -5 2>/dev/null | wc -l")
    if out == "0":
        log("Orchestrator stale (>5 min) — cron should handle")
    else:
        log("Orchestrator active")

    # 3. DISK
    disk = shutil.disk_usage("/")
    pct = disk.used / disk.total * 100
    if pct > 85:
        log(f"Disk {pct:.0f}% CRITICAL — cleaning")
        run("find /opt/EMAIL/CAMPAIGNS/logs -name '*.log' -mtime +7 -delete")
        run("journalctl --vacuum-time=3d")
        healed.append(f"disk({pct:.0f}%)")
    elif pct > 75:
        log(f"Disk {pct:.0f}% WARNING")
    else:
        log(f"Disk {pct:.0f}% OK")

    # 4. POSTGRESQL
    ok, _ = run("psql -d interjob_master -c 'SELECT 1' 2>/dev/null")
    if ok:
        log("PostgreSQL OK")
    else:
        log("PostgreSQL query FAILED — restarting")
        restart_service("postgresql")
        healed.append("postgresql")

    # 5. NODE-RED
    _, code = run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:1880/")
    if code in ("200", "301"):
        log("Node-RED OK")
    else:
        log("Node-RED DOWN — restarting")
        restart_service("nodered")
        healed.append("nodered")

    # 6. CADDY HTTPS
    _, code = run("curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/")
    if code in ("200", "301", "302"):
        log("Caddy OK")
    else:
        log("Caddy HTTPS failing — restarting")
        restart_service("caddy")
        healed.append("caddy")

    # 7. BOT CONFLICT CHECK
    for svc in ["interjob-master-bot", "telegram-bot"]:
        try:
            _, lines = run(f"journalctl -u {svc} --since '10 min ago' --no-pager", 10)
            c409 = lines.count("409 Conflict")
            c200 = lines.count("200 OK")
            total = c409 + c200
            if total > 0 and c409 / total > 0.8:
                log(f"{svc} 409 rate {c409}/{total} — restarting")
                restart_service(svc)
                healed.append(f"{svc}(409)")
            elif total > 0:
                log(f"{svc} 409: {c409}/{total}")
        except Exception:
            pass

    # 8. RASPIBIG REACHABLE
    ok, _ = run("ping -c1 -W2 192.168.100.21")
    if ok:
        log("Raspibig reachable")
    else:
        log("Raspibig UNREACHABLE")
        alert("Raspibig (192.168.100.21) unreachable from raspi!")

    # REPORT
    if dead:
        alert(f"DEAD: {', '.join(dead)}")
    if healed:
        alert(f"RASPI AUTO-HEALED: {', '.join(healed)}")
        log(f"Healed: {', '.join(healed)}")
    if not dead and not healed:
        log("All systems healthy")


if __name__ == "__main__":
    main()
