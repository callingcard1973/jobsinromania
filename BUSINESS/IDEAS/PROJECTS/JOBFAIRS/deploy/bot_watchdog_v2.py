#!/usr/bin/env python3
"""Bot Watchdog v2 — full autoheal for raspibig. Runs every 15 min via cron.
Checks: services, bot conflicts, dashboard, orchestrator, disk, Ollama,
response tracker, Caddy. Auto-restarts anything broken. Alerts only on failure."""
import subprocess, os, shutil, requests
from datetime import datetime
from pathlib import Path

TOKEN = "8546618948:AAG0neoQA-kNq0M2GrZX7J-dGXNvEJEOK9w"
CHAT = "547047851"
LOG = "/home/tudor/.logs/bot_watchdog.log"

SERVICES = [
    "telegram-unified-controller", "telegram-moderation",
    "telegram-order-approval", "interjob-nanoclaw",
    "interjob-governor", "interjob-watchdog",
    "campaign-dashboard", "postgresql", "redis-server",
    "ollama", "caddy",
]

BOT_TOKENS = {
    "telegram-unified-controller": "8628341440:AAG-dLC-9A5qVL2B_FA4K_c09fvD7622Mv8",
    "telegram-moderation": "8212960227:AAF_9d-4e_reI4har-HYvRqFzNNKulXWEQI",
}


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
            json={"chat_id": CHAT, "text": f"🔴 WATCHDOG: {msg}", "parse_mode": "HTML"},
            timeout=10)
    except Exception:
        pass


def run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
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

    # 1. SERVICES — restart any that are down
    for svc in SERVICES:
        if not check_service(svc):
            log(f"{svc} DOWN — restarting")
            if restart_service(svc):
                healed.append(svc)
            else:
                dead.append(svc)
        else:
            log(f"{svc} OK")

    # 2. BOT CONFLICTS — detect 409 rate >80%, deleteWebhook + restart
    for svc, token in BOT_TOKENS.items():
        try:
            _, lines = run(f"journalctl -u {svc} --since '10 min ago' --no-pager", 10)
            c409 = lines.count("409 Conflict")
            c200 = lines.count("200 OK")
            total = c409 + c200
            if total > 0 and c409 / total > 0.8:
                log(f"{svc} 409 rate {c409}/{total} — healing")
                requests.get(f"https://api.telegram.org/bot{token}/deleteWebhook?drop_pending_updates=true", timeout=5)
                restart_service(svc)
                healed.append(f"{svc}(409)")
            elif total > 0:
                log(f"{svc} 409: {c409}/{total} ({c409/total*100:.0f}%)")
        except Exception:
            pass

    # 3. DASHBOARD — check port 8096
    _, code = run("curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8096/")
    if code not in ("200", "301", "302"):
        log("Dashboard 8096 DOWN — restarting")
        run("pkill -f 'dashboard.py.*8096'")
        subprocess.Popen(
            ["/opt/ACTIVE/INFRA/venv/bin/python3", "dashboard.py", "--port", "8096", "--configs", "configs"],
            cwd="/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        healed.append("dashboard:8096")
    else:
        log("Dashboard OK")

    # 4. ORCHESTRATOR — check if running
    ok, _ = run("pgrep -f 'orchestrator.py.*configs'")
    if not ok:
        log("Orchestrator DOWN — restarting")
        subprocess.Popen(
            ["/opt/ACTIVE/INFRA/venv/bin/python3", "-u", "orchestrator.py",
             "--configs", "configs", "--interval", "300", "--workers", "6"],
            cwd="/opt/ACTIVE/EMAIL/CAMPAIGNS/UNIFIED",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        healed.append("orchestrator")
    else:
        log("Orchestrator OK")

    # 5. DISK — warn at 75%, clean logs at 85%
    disk = shutil.disk_usage("/")
    pct = disk.used / disk.total * 100
    if pct > 85:
        log(f"Disk {pct:.0f}% CRITICAL — cleaning logs")
        run("find /opt/ACTIVE/INFRA/LOGS -name '*.log' -mtime +7 -delete")
        run("find /home/tudor/.logs -name '*.log' -mtime +14 -delete")
        run("journalctl --vacuum-time=3d")
        healed.append(f"disk({pct:.0f}%→cleaned)")
    elif pct > 75:
        log(f"Disk {pct:.0f}% WARNING")
    else:
        log(f"Disk {pct:.0f}% OK")

    # 6. OLLAMA — check if responding
    try:
        r = requests.get("http://127.0.0.1:11434/api/tags", timeout=5)
        if r.status_code == 200:
            log("Ollama OK")
        else:
            log("Ollama unhealthy — restarting")
            restart_service("ollama")
            healed.append("ollama")
    except Exception:
        log("Ollama DOWN — restarting")
        restart_service("ollama")
        healed.append("ollama")

    # 7. RESPONSE TRACKER — check cron exists
    ok, out = run("crontab -l | grep -c response_tracker")
    if out == "0":
        log("Response tracker cron MISSING — reinstalling")
        run("(crontab -l; echo '*/5 * * * * /usr/bin/python3 /opt/ACTIVE/INFRA/SKILLS/response_tracker.py >> /home/tudor/.logs/response_tracker.log 2>&1') | crontab -")
        healed.append("response_tracker_cron")
    else:
        log("Response tracker cron OK")

    # 8. NANOCLAW HEARTBEAT — check if alive
    hb = Path("/tmp/interjob_heartbeats/nanoclaw.heartbeat")
    if hb.exists():
        age = (datetime.now() - datetime.fromisoformat(hb.read_text().strip())).total_seconds()
        if age > 300:
            log(f"NanoClaw heartbeat stale ({age:.0f}s) — restarting")
            restart_service("interjob-nanoclaw")
            healed.append("nanoclaw(stale)")
        else:
            log(f"NanoClaw heartbeat OK ({age:.0f}s)")
    else:
        log("NanoClaw heartbeat MISSING — restarting")
        restart_service("interjob-nanoclaw")
        healed.append("nanoclaw(no_hb)")

    # 9. CADDY — check HTTPS
    _, code = run("curl -sk -o /dev/null -w '%{http_code}' https://127.0.0.1/")
    if code not in ("200", "301", "302"):
        log(f"Caddy HTTPS failing ({code}) — restarting")
        restart_service("caddy")
        healed.append("caddy")
    else:
        log("Caddy HTTPS OK")

    # 10. SOLONET FOLLOW-UPS (check once per hour)
    from datetime import datetime as dt
    if dt.now().minute < 15:
        try:
            run("python3 /opt/ACTIVE/INFRA/SKILLS/solonet_pipeline.py followups", 10)
        except Exception:
            pass

    # REPORT
    if dead:
        alert(f"DEAD (restart failed): {', '.join(dead)}")
    if healed:
        alert(f"AUTO-HEALED: {', '.join(healed)}")
        log(f"Healed: {', '.join(healed)}")
    if not dead and not healed:
        log("All systems healthy")


if __name__ == "__main__":
    main()
