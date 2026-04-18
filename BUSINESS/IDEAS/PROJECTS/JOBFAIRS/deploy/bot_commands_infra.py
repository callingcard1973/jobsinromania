#!/usr/bin/env python3
"""Infrastructure commands for Telegram controller — no LLM, pure shell.
Covers: raspibig, raspi, laptop, minipc. Run from phone."""
import subprocess
import psutil
import json
from datetime import datetime
from pathlib import Path
from telegram import Update
from telegram.ext import ContextTypes

MACHINES = {
    "raspibig": {"host": "localhost", "ssh": None},
    "raspi": {"host": "192.168.100.20", "ssh": "tudor@192.168.100.20"},
    "laptop": {"host": "192.168.100.25", "ssh": None},
    "minipc": {"host": "192.168.100.30", "ssh": "tudor@192.168.100.30"},
}

def _run(cmd, timeout=10):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip()[:3000]
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

def _ssh(host, cmd, timeout=10):
    return _run(f"ssh -o ConnectTimeout=3 {host} '{cmd}'", timeout)

def _reply(text):
    return f"<pre>{text[:4000]}</pre>"


async def cmd_q(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Quick status — all machines, campaigns, disk, services."""
    lines = []
    # raspibig
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    lines.append(f"🖥 RASPIBIG: CPU {cpu}% | RAM {mem.used//1024//1024}M/{mem.total//1024//1024}M | Disk {disk.percent}%")
    # raspi
    r = _ssh("tudor@192.168.100.20", "uptime -p && df -h / | tail -1 | awk '{print $5}'")
    lines.append(f"🍓 RASPI: {r or 'OFFLINE'}")
    # laptop
    r = _run("ping -c1 -W2 192.168.100.25 2>/dev/null | grep -c '1 received'")
    lines.append(f"💻 LAPTOP: {'ONLINE' if r.strip()=='1' else 'OFFLINE'}")
    # minipc
    r = _run("ping -c1 -W2 192.168.100.30 2>/dev/null | grep -c '1 received'")
    lines.append(f"🖥 MINIPC: {'ONLINE' if r.strip()=='1' else 'OFFLINE'}")
    # campaigns
    r = _run("ps aux | grep orchestrator.py | grep -v grep | wc -l")
    lines.append(f"📧 Orchestrator: {'RUNNING' if r.strip()!='0' else 'DOWN'}")
    r = _run("psql -d interjob_master -t -c \"SELECT COUNT(*) FROM norway_virgil_send_log\"")
    lines.append(f"🇳🇴 NORWAY_VIRGIL sent: {r.strip()}")
    await update.message.reply_text(_reply('\n'.join(lines)), parse_mode="HTML")


async def cmd_disk(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Disk usage all machines."""
    lines = ["📀 DISK USAGE:"]
    lines.append("RASPIBIG: " + _run("df -h / /mnt/hdd 2>/dev/null | tail -2"))
    lines.append("RASPI: " + _ssh("tudor@192.168.100.20", "df -h / | tail -1"))
    await update.message.reply_text(_reply('\n'.join(lines)), parse_mode="HTML")


async def cmd_mem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Memory usage."""
    await update.message.reply_text(_reply(_run("free -h")), parse_mode="HTML")


async def cmd_top(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Top 10 processes by CPU."""
    r = _run("ps aux --sort=-%cpu | head -11 | awk '{printf \"%-8s %5s %5s %s\\n\", $1,$3,$4,$11}'")
    await update.message.reply_text(_reply(f"🔥 TOP CPU:\n{r}"), parse_mode="HTML")


async def cmd_topmem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Top 10 processes by memory."""
    r = _run("ps aux --sort=-%mem | head -11 | awk '{printf \"%-8s %5s %5s %s\\n\", $1,$3,$4,$11}'")
    await update.message.reply_text(_reply(f"🧠 TOP MEM:\n{r}"), parse_mode="HTML")


async def cmd_svc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """All systemd services status."""
    svcs = ["interjob-nanoclaw", "interjob-governor", "interjob-watchdog",
            "telegram-unified-controller", "telegram-moderation", "telegram-order-approval",
            "campaign-dashboard", "postgresql", "redis-server", "ollama", "caddy", "nodered"]
    lines = ["🔧 SERVICES:"]
    for s in svcs:
        r = _run(f"systemctl is-active {s} 2>/dev/null").strip()
        icon = "✅" if r == "active" else "❌"
        lines.append(f"{icon} {s}: {r}")
    await update.message.reply_text(_reply('\n'.join(lines)), parse_mode="HTML")


async def cmd_restart(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Restart a service. Usage: /restart <service_name>"""
    if not ctx.args:
        await update.message.reply_text("Usage: /restart <service_name>")
        return
    svc = ctx.args[0]
    r = _run(f"sudo systemctl restart {svc} 2>&1 && systemctl is-active {svc}")
    await update.message.reply_text(_reply(f"🔄 {svc}: {r}"), parse_mode="HTML")


async def cmd_logs(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Recent logs. Usage: /logs <service> [lines]"""
    svc = ctx.args[0] if ctx.args else "interjob-nanoclaw"
    n = int(ctx.args[1]) if len(ctx.args) > 1 else 20
    r = _run(f"journalctl -u {svc} --no-pager -n {n}", timeout=15)
    await update.message.reply_text(_reply(f"📋 {svc} (last {n}):\n{r}"), parse_mode="HTML")


async def cmd_errors(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Recent errors across all services."""
    r = _run("journalctl --since '1 hour ago' --no-pager | grep -i 'error\\|fail\\|exception' | grep -v 'Conflict' | tail -20", timeout=15)
    await update.message.reply_text(_reply(f"🔴 ERRORS (1h):\n{r or 'None'}"), parse_mode="HTML")


async def cmd_campaigns(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Campaign stats from orchestrator."""
    r = _run("curl -s http://127.0.0.1:8096/api/campaigns/stats 2>/dev/null | python3 -m json.tool 2>/dev/null | head -50", timeout=15)
    await update.message.reply_text(_reply(f"📧 CAMPAIGNS:\n{r or 'Dashboard unavailable'}"), parse_mode="HTML")


async def cmd_norway(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """NORWAY_VIRGIL campaign status."""
    r = _run("psql -d interjob_master -t -c \"SELECT 'Pending: ' || COUNT(*) FILTER (WHERE campaign_status='pending') || ' | Sent: ' || COUNT(*) FILTER (WHERE campaign_status='sent') || ' | Total: ' || COUNT(*) FROM norway_virgil\"")
    r2 = _run("psql -d interjob_master -t -c \"SELECT COUNT(*) || ' emails sent' FROM norway_virgil_send_log\"")
    r3 = _run("psql -d interjob_master -t -c \"SELECT email || ' → ' || company FROM norway_virgil_send_log ORDER BY created_at DESC LIMIT 5\"")
    await update.message.reply_text(_reply(f"🇳🇴 NORWAY_VIRGIL:\n{r.strip()}\n{r2.strip()}\n\nLast 5:\n{r3.strip()}"), parse_mode="HTML")


async def cmd_db(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Database status."""
    r = _run("psql -d interjob_master -t -c \"SELECT pg_size_pretty(pg_database_size('interjob_master'))\"")
    r2 = _run("psql -d interjob_master -t -c \"SELECT COUNT(*) || ' tables' FROM information_schema.tables WHERE table_schema='public'\"")
    r3 = _run("psql -d interjob_master -t -c \"SELECT relname || ': ' || n_live_tup FROM pg_stat_user_tables ORDER BY n_live_tup DESC LIMIT 10\"")
    await update.message.reply_text(_reply(f"🗄 DB:\nSize: {r.strip()}\n{r2.strip()}\n\nTop tables:\n{r3.strip()}"), parse_mode="HTML")


async def cmd_bounce(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Check Brevo bounce rates."""
    r = _run("python3 -c \"\nimport requests, json\nenv={}\nwith open('/opt/ACTIVE/EMAIL/CAMPAIGNS/.env') as f:\n  for l in f:\n    if '=' in l and not l.startswith('#'): k,v=l.strip().split('=',1); env[k]=v\nfor name in ['BREVO_BUILDJOBS_API_KEY','BREVO_SEICARESCU_API_KEY','BREVO_MIVROMANIA_API_KEY']:\n  key=env.get(name,'')\n  if not key: continue\n  r=requests.get('https://api.brevo.com/v3/smtp/statistics/aggregatedReport',headers={'api-key':key},params={'days':7},timeout=10)\n  if r.status_code==200:\n    d=r.json(); t=d.get('requests',0); h=d.get('hardBounces',0); s=d.get('softBounces',0)\n    print(f'{name}: {t} sent, {h}H+{s}S, {(h+s)/t*100:.1f}%' if t else f'{name}: 0 sent')\n\"", timeout=20)
    await update.message.reply_text(_reply(f"📬 BOUNCE RATES:\n{r}"), parse_mode="HTML")


async def cmd_ollama(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Ollama LLM status."""
    r = _run("curl -s http://127.0.0.1:11434/api/tags | python3 -c \"import json,sys; [print(f'{m[\\\"name\\\"]} ({round(m[\\\"size\\\"]/1e9,1)}GB)') for m in json.load(sys.stdin).get('models',[])]\"")
    await update.message.reply_text(_reply(f"🧠 OLLAMA MODELS:\n{r or 'DOWN'}"), parse_mode="HTML")


async def cmd_cron(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """List active cron jobs."""
    r = _run("crontab -l 2>/dev/null | grep -v '^#' | grep -v '^$'")
    await update.message.reply_text(_reply(f"⏰ CRON:\n{r}"), parse_mode="HTML")


async def cmd_net(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Network: open ports, connections."""
    r = _run("ss -tlnp | grep LISTEN | awk '{printf \"%-6s %s\\n\", $4, $6}' | head -20")
    await update.message.reply_text(_reply(f"🌐 LISTENING PORTS:\n{r}"), parse_mode="HTML")


async def cmd_temp(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """CPU temperature."""
    r = _run("cat /sys/class/thermal/thermal_zone0/temp 2>/dev/null")
    try:
        t = int(r) / 1000
        await update.message.reply_text(f"🌡 CPU: {t:.1f}°C")
    except Exception:
        await update.message.reply_text("🌡 Temperature unavailable")


async def cmd_uptime(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """System uptime."""
    r = _run("uptime -p")
    await update.message.reply_text(f"⏱ {r}")


async def cmd_ping(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Ping all machines."""
    lines = []
    for name, info in MACHINES.items():
        r = _run(f"ping -c1 -W2 {info['host']} 2>/dev/null | grep 'time='")
        lines.append(f"{'✅' if r else '❌'} {name}: {r.split('time=')[1] if 'time=' in r else 'OFFLINE'}")
    await update.message.reply_text(_reply('\n'.join(lines)), parse_mode="HTML")


async def cmd_wake(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Wake laptop via WoL."""
    r = _run("wakeonlan 00:e0:4c:68:00:00 2>/dev/null || etherwake 00:e0:4c:68:00:00 2>/dev/null || echo 'WoL not available'")
    await update.message.reply_text(f"💻 Wake sent: {r}")


async def cmd_kill(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Kill process by PID. Usage: /kill <pid>"""
    if not ctx.args:
        await update.message.reply_text("Usage: /kill <pid>")
        return
    pid = ctx.args[0]
    r = _run(f"kill {pid} 2>&1 && echo 'Killed {pid}' || echo 'Failed'")
    await update.message.reply_text(f"☠️ {r}")


async def cmd_backup(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Backup status."""
    r = _run("ls -lhrt /opt/ACTIVE/INFRA/BACKUPS/ 2>/dev/null | tail -5")
    r2 = _run("pg_dump --version 2>/dev/null && echo 'pg_dump available'")
    await update.message.reply_text(_reply(f"💾 BACKUPS:\n{r}\n{r2}"), parse_mode="HTML")


async def cmd_ssl(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """SSL cert expiry."""
    r = _run("openssl x509 -in /etc/caddy/ssl/raspibig.crt -noout -enddate 2>/dev/null || echo 'No cert'")
    await update.message.reply_text(f"🔒 SSL: {r}")


async def cmd_watchdog(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Run watchdog now."""
    r = _run("python3 /opt/ACTIVE/INFRA/SKILLS/bot_watchdog.py 2>&1", timeout=30)
    await update.message.reply_text(_reply(f"🐕 WATCHDOG:\n{r}"), parse_mode="HTML")


# Command registry for easy import
INFRA_COMMANDS = {
    "q": cmd_q, "disk": cmd_disk, "mem": cmd_mem, "top": cmd_top,
    "topmem": cmd_topmem, "svc": cmd_svc, "restart": cmd_restart,
    "logs": cmd_logs, "errors": cmd_errors, "campaigns": cmd_campaigns,
    "norway": cmd_norway, "db": cmd_db, "bounce": cmd_bounce,
    "ollama": cmd_ollama, "cron": cmd_cron, "net": cmd_net,
    "temp": cmd_temp, "uptime": cmd_uptime, "ping": cmd_ping,
    "wake": cmd_wake, "kill": cmd_kill, "backup": cmd_backup,
    "ssl": cmd_ssl, "watchdog": cmd_watchdog,
}
